"""Gerador Schemathesis: os cinco cenários da Conformidade do ADR-005, mais RN-04."""

import copy
import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from urllib.parse import urlsplit

import httpx
import pytest

from app.adapters.outbound.generator.gerador_schemathesis import GeradorSchemathesis
from app.application.portas import SpecInvalida
from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado

pytestmark = pytest.mark.integration

SEED = 20261110
LIMITE = 5
ENDPOINTS_DA_API_ALVO = {
    ("/saude", "GET"),
    ("/tarefas", "GET"),
    ("/tarefas", "POST"),
    ("/tarefas/{id}", "GET"),
    ("/tarefas/{id}", "PUT"),
    ("/tarefas/{id}", "DELETE"),
}


@pytest.fixture
def gerador() -> GeradorSchemathesis:
    return GeradorSchemathesis(limite_de_casos=LIMITE, timeout_s=5.0)


def _spec(base_url: str) -> dict[str, Any]:
    spec: dict[str, Any] = httpx.get(f"{base_url}/openapi.json").json()
    return spec


def _por_endpoint(resultados: list[ResultadoDoTeste]) -> dict[tuple[str, str], ResultadoDoTeste]:
    return {(r.endpoint, r.metodo): r for r in resultados}


# Servidor local que grava as requisições e responde o que o teste mandar.
# Usado onde a API alvo não produz o cenário (500 documentado) ou não expõe o que chegou.


class _Servidor(ThreadingHTTPServer):
    def __init__(self, respostas: dict[tuple[str, str], tuple[int, bytes]]) -> None:
        super().__init__(("127.0.0.1", 0), _Gravador)
        self.respostas = respostas
        self.requisicoes: list[tuple[str, str, bytes]] = []


class _Gravador(BaseHTTPRequestHandler):
    def _responder(self) -> None:
        servidor = cast(_Servidor, self.server)
        corpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        servidor.requisicoes.append((self.command, self.path, corpo))
        chave = (self.command, urlsplit(self.path).path)
        status, resposta = servidor.respostas.get(chave, (200, b"{}"))
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resposta)))
        self.end_headers()
        self.wfile.write(resposta)

    do_GET = do_POST = do_PUT = do_DELETE = _responder

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def servidor_falso() -> Iterator[_Servidor]:
    servidor = _Servidor(respostas={})
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        yield servidor
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=5)


def _url(servidor: _Servidor) -> str:
    host, porta = servidor.server_address[:2]
    return f"http://{host!s}:{porta}"


def test_us06_c4_api_conforme_tem_um_resultado_passou_por_endpoint_e_metodo(
    api_alvo: str, gerador: GeradorSchemathesis
) -> None:
    resultados = gerador.gerar_e_executar(_spec(api_alvo), api_alvo, SEED)

    # Um resultado por par, mesmo com vários casos gerados por endpoint (RN-03).
    assert len(resultados) == len(ENDPOINTS_DA_API_ALVO)
    assert set(_por_endpoint(resultados)) == ENDPOINTS_DA_API_ALVO
    for resultado in resultados:
        assert resultado.status == StatusResultado.PASSOU, resultado
        assert resultado.mensagem_erro is None
        assert resultado.duracao_ms >= 0


def test_us03_c2_modo_falha_e_detectado_por_status_e_por_schema(
    api_alvo_com_falha: str, gerador: GeradorSchemathesis
) -> None:
    resultados = _por_endpoint(
        gerador.gerar_e_executar(_spec(api_alvo_com_falha), api_alvo_com_falha, SEED)
    )

    listagem = resultados[("/tarefas", "GET")]
    assert listagem.status == StatusResultado.FALHOU
    assert listagem.mensagem_erro is not None
    assert "Undocumented status code: Received: 500" in listagem.mensagem_erro

    busca = resultados[("/tarefas/{id}", "GET")]
    assert busca.status == StatusResultado.FALHOU
    assert busca.mensagem_erro is not None
    assert 'Response violates schema: "talvez" is not of type "boolean"' in busca.mensagem_erro

    # O MODO_FALHA só afeta as duas rotas acima.
    afetados = {("/tarefas", "GET"), ("/tarefas/{id}", "GET")}
    outros = [r for chave, r in resultados.items() if chave not in afetados]
    assert len(outros) == len(ENDPOINTS_DA_API_ALVO) - 2
    assert {r.status for r in outros} == {StatusResultado.PASSOU}


def test_us03_c2_so_status_e_schema_sao_verificados(
    servidor_falso: _Servidor, gerador: GeradorSchemathesis
) -> None:
    # 500 documentado e 400 documentado para dado válido: conformes em status e schema.
    # Com as checagens padrão do Schemathesis, not_a_server_error e
    # positive_data_acceptance reprovariam os dois.
    servidor_falso.respostas.update(
        {("GET", "/quebra"): (500, b'{"erro": "x"}'), ("POST", "/recusa"): (400, b"{}")}
    )
    objeto = {"application/json": {"schema": {"type": "object"}}}
    spec: dict[str, object] = {
        "openapi": "3.0.3",
        "info": {"title": "falso", "version": "1"},
        "paths": {
            "/quebra": {"get": {"responses": {"500": {"description": "x", "content": objeto}}}},
            "/recusa": {
                "post": {
                    "requestBody": {"required": True, "content": objeto},
                    "responses": {"400": {"description": "x", "content": objeto}},
                }
            },
        },
    }

    resultados = gerador.gerar_e_executar(spec, _url(servidor_falso), SEED)

    assert {r.status for r in resultados} == {StatusResultado.PASSOU}
    # Prova de que as respostas 500 e 400 chegaram mesmo ao gerador.
    chamados = {
        (metodo, urlsplit(caminho).path) for metodo, caminho, _ in servidor_falso.requisicoes
    }
    assert chamados == {("GET", "/quebra"), ("POST", "/recusa")}


def test_us03_c3_endpoint_sem_schema_de_resposta_verifica_so_o_status(
    api_alvo_com_falha: str, gerador: GeradorSchemathesis
) -> None:
    spec = copy.deepcopy(_spec(api_alvo_com_falha))
    del spec["paths"]["/tarefas/{id}"]["get"]["responses"]["200"]["content"]

    resultados = _por_endpoint(gerador.gerar_e_executar(spec, api_alvo_com_falha, SEED))

    # Mesma resposta com tipos errados do teste anterior: sem schema, só o status 200 conta.
    assert resultados[("/tarefas/{id}", "GET")].status == StatusResultado.PASSOU
    # O status continua verificado: o 500 não documentado ainda reprova a listagem.
    assert resultados[("/tarefas", "GET")].status == StatusResultado.FALHOU


def test_us03_c4_mesma_spec_e_mesma_seed_geram_as_mesmas_requisicoes(
    servidor_falso: _Servidor, gerador: GeradorSchemathesis
) -> None:
    spec: dict[str, object] = {
        "openapi": "3.0.3",
        "info": {"title": "falso", "version": "1"},
        "paths": {
            "/itens/{id}": {
                "put": {
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        },
                        {"name": "q", "in": "query", "schema": {"type": "string"}},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }

    def requisicoes(seed: int) -> list[tuple[str, str, bytes]]:
        servidor_falso.requisicoes.clear()
        gerador.gerar_e_executar(spec, _url(servidor_falso), seed)
        return list(servidor_falso.requisicoes)

    primeira = requisicoes(SEED)
    segunda = requisicoes(SEED)
    outra_seed = requisicoes(SEED + 1)

    assert 1 < len(primeira) <= LIMITE
    assert primeira == segunda
    # Sem isto, o teste passaria também com um gerador que ignora a seed e repete casos fixos.
    assert outra_seed != primeira


def test_rn03_t1_api_alvo_inacessivel_faz_cada_endpoint_falhar_com_o_erro(
    api_alvo: str, gerador: GeradorSchemathesis
) -> None:
    spec = _spec(api_alvo)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta_fechada = s.getsockname()[1]

    resultados = gerador.gerar_e_executar(spec, f"http://127.0.0.1:{porta_fechada}", SEED)

    assert set(_por_endpoint(resultados)) == ENDPOINTS_DA_API_ALVO
    for resultado in resultados:
        assert resultado.status == StatusResultado.FALHOU
        assert resultado.mensagem_erro is not None
        assert resultado.mensagem_erro.startswith("Erro ao chamar a API alvo:")
        assert "Connection refused" in resultado.mensagem_erro


_RESPOSTA_OK = {"200": {"description": "ok"}}


def _spec_com(operacao_quebrada: dict[str, Any], openapi: str = "3.0.3") -> dict[str, Any]:
    # A operação válida vem antes: prova que nenhuma requisição sai se outra está quebrada.
    return {
        "openapi": openapi,
        "info": {"title": "x", "version": "1"},
        "paths": {
            "/ok": {"get": {"responses": _RESPOSTA_OK}},
            "/quebrada": {"get": {**operacao_quebrada, "responses": _RESPOSTA_OK}},
        },
    }


@pytest.mark.parametrize(
    ("spec", "motivo"),
    [
        pytest.param(_spec_com({}, openapi="9.9"), "Open API 9.9", id="versao-nao-suportada"),
        pytest.param(
            _spec_com({"parameters": [{"$ref": "#/components/parameters/Inexistente"}]}),
            "Inexistente",
            id="ref-quebrado",
        ),
        pytest.param(
            _spec_com({"parameters": [{"name": "q", "in": "query", "schema": {"type": "nada"}}]}),
            "Invalid `type` definition",
            id="schema-invalido",
        ),
    ],
)
def test_us02_c2_spec_que_o_schemathesis_nao_interpreta_levanta_spec_invalida_com_motivo(
    spec: dict[str, Any],
    motivo: str,
    gerador: GeradorSchemathesis,
    servidor_falso: _Servidor,
) -> None:
    with pytest.raises(SpecInvalida, match="Schemathesis não conseguiu interpretar") as erro:
        gerador.gerar_e_executar(spec, _url(servidor_falso), SEED)

    assert motivo in str(erro.value)
    assert servidor_falso.requisicoes == []
