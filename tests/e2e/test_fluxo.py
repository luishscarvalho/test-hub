"""Fluxo completo com o ambiente do Compose no ar (E2E-01 e E2E-02, Plano de Testes 2.3).

Cliente HTTP de fora do Compose. O hub chama a API alvo pela rede interna (target-api:8000).
Pré-requisito: docker compose up -d --wait.
"""

import json
import os
import subprocess
import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.e2e

HUB_URL = os.getenv("HUB_URL", "http://localhost:8000")
# Endereço da API alvo visto de dentro do Compose, onde o hub e o worker rodam.
ALVO_NA_REDE_INTERNA = "http://target-api:8000"
LIMITE_RUN_S = 120.0
INTERVALO_CONSULTA_S = 0.5
STATUS_FINAIS = {"passou", "falhou", "interrompida"}


def _compose(*argumentos: str, modo_falha: str | None = None) -> str:
    ambiente = dict(os.environ)
    if modo_falha is not None:
        ambiente["MODO_FALHA"] = modo_falha
    resultado = subprocess.run(
        ["docker", "compose", *argumentos],
        env=ambiente,
        check=True,
        capture_output=True,
        text=True,
    )
    return resultado.stdout


def _recriar_api_alvo(modo_falha: str) -> None:
    """MODO_FALHA é lido na subida da API alvo (ADR-008): troca exige recriar o serviço."""
    _compose(
        "up",
        "-d",
        "--no-build",
        "--force-recreate",
        "--wait",
        "target-api",
        modo_falha=modo_falha,
    )


@pytest.fixture
def hub() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=HUB_URL, timeout=10) as cliente:
        yield cliente


@pytest.fixture
def api_alvo_com_falha() -> Iterator[None]:
    _recriar_api_alvo("true")
    try:
        yield
    finally:
        _recriar_api_alvo("false")


def _executar_run(hub: httpx.Client) -> dict[str, Any]:
    """Cadastra a API alvo por URL, dispara a run e acompanha até o status final."""
    cadastro = hub.post(
        "/apis",
        data={
            "nome": "tarefas",
            "base_url": ALVO_NA_REDE_INTERNA,
            "spec_url": f"{ALVO_NA_REDE_INTERNA}/openapi.json",
        },
    )
    assert cadastro.status_code == 201, cadastro.text
    disparo = hub.post("/runs", json={"api_alvo_id": cadastro.json()["id"]})
    assert disparo.status_code == 202, disparo.text
    assert disparo.json()["status"] == "na_fila"
    run_id = disparo.json()["id"]

    prazo = time.monotonic() + LIMITE_RUN_S
    while time.monotonic() < prazo:
        detalhe: dict[str, Any] = hub.get(f"/runs/{run_id}").json()
        if detalhe["status"] in STATUS_FINAIS:
            return detalhe
        time.sleep(INTERVALO_CONSULTA_S)
    raise TimeoutError(f"Run {run_id} não chegou a status final em {LIMITE_RUN_S}s")


def _inicio_do_container(servico: str) -> datetime:
    container_id = _compose("ps", "-q", servico).strip()
    assert container_id, f"serviço {servico} não está no ar"
    estado = json.loads(
        subprocess.run(
            ["docker", "inspect", "--format", "{{json .State}}", container_id],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert estado["Running"], f"serviço {servico} não está rodando"
    return datetime.fromisoformat(estado["StartedAt"])


def test_e2e_01_ambiente_sobe_sem_passo_manual_e_run_sem_falha_termina_passou(
    hub: httpx.Client,
) -> None:
    # O worker depende do hub saudável (depends_on: service_healthy no Compose).
    assert _inicio_do_container("worker") > _inicio_do_container("hub")

    detalhe = _executar_run(hub)

    assert detalhe["status"] == "passou", detalhe
    assert detalhe["total_falhou"] == 0
    assert detalhe["total_passou"] == len(detalhe["resultados"]) > 0
    assert detalhe["spec_versao_id"] is not None


def test_e2e_02_com_modo_falha_a_run_termina_falhou_e_aponta_os_endpoints(
    hub: httpx.Client, api_alvo_com_falha: None
) -> None:
    detalhe = _executar_run(hub)

    assert detalhe["status"] == "falhou", detalhe
    falhas = {
        (r["metodo"], r["endpoint"]): r["mensagem_erro"]
        for r in detalhe["resultados"]
        if r["status"] == "falhou"
    }
    assert set(falhas) == {("GET", "/tarefas"), ("GET", "/tarefas/{id}")}
    assert all(falhas.values())
    assert detalhe["total_falhou"] == 2
