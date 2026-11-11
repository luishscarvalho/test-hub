"""Caso de uso de execução da run pelo worker (US-04, US-05, RN-06, RN-12, RN-13 e RN-15)."""

from datetime import timedelta

import pytest

from app.application.executar_run import ExecutarRun, SpecDoCadastroAusente
from app.application.portas import ApiNaoEncontrada, RunNaoEncontrada, SpecInvalida
from app.application.spec_normalizada import calcular_hash
from app.domain.api_alvo import ApiAlvo
from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado
from app.domain.run import Run
from app.domain.spec_versao import OrigemSpec, SpecVersao
from app.domain.status_run import StatusRun, TransicaoInvalida
from tests.unit.application.fakes import (
    INICIO_DO_RELOGIO,
    CarregadorDeSpecFalso,
    GeradorDeTestesFalso,
    RelogioFalso,
    RepositorioDeApisFalso,
    RepositorioDeRunsFalso,
    RepositorioDeSpecsFalso,
)

pytestmark = pytest.mark.unit

URL = "http://alvo:8000/openapi.json"
BASE_URL = "http://alvo:8000"
SEED = 20261111
SPEC_V1: dict[str, object] = {"openapi": "3.1.0", "paths": {"/tarefas": {"get": {}}}}
SPEC_V2: dict[str, object] = {"openapi": "3.1.0", "paths": {"/tarefas": {"post": {}}}}
OK = ResultadoDoTeste("/tarefas", "GET", StatusResultado.PASSOU, 12, None)
ERRO = ResultadoDoTeste("/tarefas/{id}", "GET", StatusResultado.FALHOU, 30, "schema")

# Ids nos falsos: API por URL é a 1, por arquivo é a 2. A run de cada uma tem o mesmo id.
API_URL = 1
API_ARQUIVO = 2


class Cenario:
    def __init__(self) -> None:
        self.apis = RepositorioDeApisFalso()
        self.specs = RepositorioDeSpecsFalso()
        self.runs = RepositorioDeRunsFalso()
        self.carregador = CarregadorDeSpecFalso()
        self.gerador = GeradorDeTestesFalso([OK])

        cadastro = SpecVersao(0, {}, "0" * 64, OrigemSpec.URL, INICIO_DO_RELOGIO)
        self.apis.adicionar(ApiAlvo("por url", BASE_URL, INICIO_DO_RELOGIO, URL), cadastro)
        self.apis.adicionar(ApiAlvo("por arquivo", BASE_URL, INICIO_DO_RELOGIO), cadastro)
        self.carregador.por_url[URL] = SPEC_V1
        self.runs.adicionar(Run(API_URL, SEED, INICIO_DO_RELOGIO))
        self.runs.adicionar(Run(API_ARQUIVO, SEED, INICIO_DO_RELOGIO))

    def versao(self, api_alvo_id: int, conteudo: dict[str, object], horas: int = 0) -> int:
        criado_em = INICIO_DO_RELOGIO - timedelta(hours=10 - horas)
        origem = OrigemSpec.URL if api_alvo_id == API_URL else OrigemSpec.ARQUIVO
        spec = SpecVersao(api_alvo_id, conteudo, calcular_hash(conteudo), origem, criado_em)
        gravada = self.specs.adicionar(spec)
        assert gravada.id is not None
        return gravada.id

    def executar(self, run_id: int) -> Run:
        ExecutarRun(
            apis=self.apis,
            specs=self.specs,
            runs=self.runs,
            carregador=self.carregador,
            gerador=self.gerador,
            relogio=RelogioFalso(),
        ).executar(run_id)
        return self.runs.runs[run_id]


@pytest.fixture
def cenario() -> Cenario:
    return Cenario()


@pytest.mark.parametrize(
    ("resultados", "status"),
    [([OK, OK], StatusRun.PASSOU), ([OK, ERRO], StatusRun.FALHOU)],
    ids=["todos-passam", "um-falha"],
)
def test_us04_c3_ao_final_a_run_tem_status_geral(
    cenario: Cenario, resultados: list[ResultadoDoTeste], status: StatusRun
) -> None:
    cenario.gerador.resposta = resultados

    assert cenario.executar(API_URL).status == status


def test_us05_c3_status_totais_e_resultados_sao_gravados_juntos(cenario: Cenario) -> None:
    cenario.gerador.resposta = [OK, ERRO]

    cenario.executar(API_URL)

    final, resultados = cenario.runs.gravacoes[-1]
    assert final.status == StatusRun.FALHOU
    assert (final.total_passou, final.total_falhou) == (1, 1)
    assert resultados == [OK, ERRO]


def test_rn11_t1_run_e_gravada_em_execucao_antes_de_gerar_os_testes(cenario: Cenario) -> None:
    cenario.executar(API_URL)

    primeira, resultados = cenario.runs.gravacoes[0]
    assert primeira.status == StatusRun.EM_EXECUCAO
    assert primeira.inicio is not None
    assert resultados == []


def test_us05_c1_run_finalizada_registra_inicio_e_fim(cenario: Cenario) -> None:
    run = cenario.executar(API_URL)

    assert run.inicio is not None and run.fim is not None
    assert run.inicio < run.fim


def test_rn14_t1_gerador_recebe_a_spec_a_base_url_e_a_seed_da_run(cenario: Cenario) -> None:
    cenario.executar(API_URL)

    assert cenario.gerador.chamadas == [(SPEC_V1, BASE_URL, SEED)]


def test_us02_c5_spec_por_url_e_baixada_e_validada_no_inicio_da_run(cenario: Cenario) -> None:
    cenario.executar(API_URL)

    assert cenario.carregador.urls_baixadas == [URL]


@pytest.mark.parametrize(
    "motivo",
    [
        "Falha ao baixar a spec: http://alvo:8000/openapi.json respondeu 404",
        "Spec inválida em raiz",
    ],
)
def test_us04_c5_spec_inacessivel_ou_invalida_termina_falhou_sem_resultados_e_sem_versao(
    cenario: Cenario, motivo: str
) -> None:
    cenario.carregador.por_url[URL] = SpecInvalida(motivo)

    run = cenario.executar(API_URL)

    assert run.status == StatusRun.FALHOU
    assert run.mensagem_erro == motivo
    assert run.spec_versao_id is None
    assert run.fim is not None
    assert cenario.runs.resultados[API_URL] == []
    assert cenario.gerador.chamadas == []


def test_rn02_t1_spec_sem_endpoints_baixada_na_run_termina_falhou(cenario: Cenario) -> None:
    motivo = "Spec inválida: nenhum endpoint declarado em paths (RN-02)"
    cenario.carregador.por_url[URL] = SpecInvalida(motivo)

    run = cenario.executar(API_URL)

    assert (run.status, run.mensagem_erro) == (StatusRun.FALHOU, motivo)


def test_us04_c5_spec_que_o_gerador_nao_interpreta_termina_falhou_sem_versao(
    cenario: Cenario,
) -> None:
    cenario.gerador.resposta = SpecInvalida("Schemathesis não conseguiu interpretar a spec")

    run = cenario.executar(API_URL)

    assert run.status == StatusRun.FALHOU
    assert run.mensagem_erro == "Schemathesis não conseguiu interpretar a spec"
    assert run.spec_versao_id is None
    assert cenario.runs.resultados[API_URL] == []


def test_rn13_t2_spec_por_url_com_hash_novo_cria_versao(cenario: Cenario) -> None:
    anterior = cenario.versao(API_URL, SPEC_V2)

    run = cenario.executar(API_URL)

    nova = cenario.specs.specs[-1]
    assert nova.id != anterior
    assert (nova.api_alvo_id, nova.conteudo, nova.origem) == (API_URL, SPEC_V1, OrigemSpec.URL)
    assert nova.hash == calcular_hash(SPEC_V1)
    assert run.spec_versao_id == nova.id


def test_rn13_t2_spec_por_url_com_hash_existente_reusa_a_versao(cenario: Cenario) -> None:
    existente = cenario.versao(API_URL, SPEC_V1)

    run = cenario.executar(API_URL)

    assert len(cenario.specs.specs) == 1
    assert run.spec_versao_id == existente


def test_rn13_t3_spec_por_arquivo_usa_a_versao_mais_recente(cenario: Cenario) -> None:
    cenario.versao(API_ARQUIVO, SPEC_V1, horas=1)
    recente = cenario.versao(API_ARQUIVO, SPEC_V2, horas=2)

    run = cenario.executar(API_ARQUIVO)

    assert run.spec_versao_id == recente
    assert cenario.gerador.chamadas[0][0] == SPEC_V2
    assert cenario.carregador.urls_baixadas == []


def test_rn13_t1_run_com_resultados_tem_versao_da_spec(cenario: Cenario) -> None:
    run = cenario.executar(API_URL)

    assert cenario.runs.resultados[API_URL] == [OK]
    assert run.spec_versao_id is not None


def test_rn12_t3_erro_inesperado_sobe_com_a_run_em_execucao(cenario: Cenario) -> None:
    # A entrada do worker recebe a exceção e interrompe a run (InterromperRun).
    cenario.gerador.resposta = RuntimeError("bug no hub")

    with pytest.raises(RuntimeError, match="bug no hub"):
        cenario.executar(API_URL)

    assert cenario.runs.runs[API_URL].status == StatusRun.EM_EXECUCAO
    assert cenario.runs.resultados[API_URL] == []


def test_rn12_t3_api_da_run_inexistente_e_erro_interno(cenario: Cenario) -> None:
    del cenario.apis.apis[API_URL]

    with pytest.raises(ApiNaoEncontrada):
        cenario.executar(API_URL)


def test_rn12_t3_api_por_arquivo_sem_versao_de_spec_e_erro_interno(cenario: Cenario) -> None:
    with pytest.raises(SpecDoCadastroAusente):
        cenario.executar(API_ARQUIVO)


def test_rn12_t3_run_inexistente_e_erro_interno(cenario: Cenario) -> None:
    with pytest.raises(RunNaoEncontrada):
        cenario.executar(99)


def test_rn05_t1_run_em_status_final_nao_e_executada_de_novo(cenario: Cenario) -> None:
    cenario.executar(API_URL)
    gravacoes = len(cenario.runs.gravacoes)

    with pytest.raises(TransicaoInvalida):
        cenario.executar(API_URL)

    assert len(cenario.runs.gravacoes) == gravacoes
