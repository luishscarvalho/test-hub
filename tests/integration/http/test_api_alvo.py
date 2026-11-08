"""NF-05: conformidade da API alvo com o ADR-008 (Plano de Testes, seção 8.3)."""

from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.integration

ID_INEXISTENTE = 999_999
TIPOS_JSON: dict[str, type] = {"integer": int, "string": str, "boolean": bool}


def _spec(base_url: str) -> dict[str, Any]:
    spec: dict[str, Any] = httpx.get(f"{base_url}/openapi.json").json()
    return spec


@pytest.mark.parametrize("metodo", ["get", "put", "delete"])
def test_nf_05_spec_declara_404_nas_rotas_com_id(api_alvo: str, metodo: str) -> None:
    respostas = _spec(api_alvo)["paths"]["/tarefas/{id}"][metodo]["responses"]

    assert "404" in respostas
    schema = respostas["404"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/Erro"}


def test_nf_05_modo_falha_desligado_por_padrao(api_alvo: str) -> None:
    # A fixture remove MODO_FALHA do ambiente: o que se vê aqui é o padrão.
    listagem = httpx.get(f"{api_alvo}/tarefas")
    assert listagem.status_code == 200
    assert [t["id"] for t in listagem.json()] == [1, 2, 3]

    existente = httpx.get(f"{api_alvo}/tarefas/1")
    assert existente.status_code == 200
    assert existente.json() == {"id": 1, "titulo": "Ler a spec OpenAPI", "concluida": True}

    inexistente = httpx.get(f"{api_alvo}/tarefas/{ID_INEXISTENTE}")
    assert inexistente.status_code == 404
    assert inexistente.json() == {"detail": f"Tarefa {ID_INEXISTENTE} não encontrada"}


def test_nf_05_saude_nao_e_afetada_pelo_modo_falha(api_alvo_com_falha: str) -> None:
    # Garante que a instância está mesmo em falha, senão o teste passaria à toa.
    assert httpx.get(f"{api_alvo_com_falha}/tarefas").status_code == 500

    saude = httpx.get(f"{api_alvo_com_falha}/saude")
    assert saude.status_code == 200
    assert saude.json() == {"status": "ok"}


@pytest.mark.parametrize("id", [1, ID_INEXISTENTE], ids=["existente", "inexistente"])
def test_nf_05_modo_falha_responde_tipos_errados_para_qualquer_id(
    api_alvo_com_falha: str, id: int
) -> None:
    prometido = _spec(api_alvo_com_falha)["components"]["schemas"]["Tarefa"]["properties"]

    resposta = httpx.get(f"{api_alvo_com_falha}/tarefas/{id}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo.keys() == prometido.keys()
    for campo, schema in prometido.items():
        # type() em vez de isinstance(): bool é subclasse de int.
        assert type(corpo[campo]) is not TIPOS_JSON[schema["type"]], campo
