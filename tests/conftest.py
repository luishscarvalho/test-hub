"""Fixtures compartilhadas."""

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

RAIZ = Path(__file__).resolve().parent.parent
LIMITE_SUBIDA_S = 15.0
INTERVALO_CONSULTA_S = 0.05


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta: int = s.getsockname()[1]
        return porta


def _esperar_saude(processo: subprocess.Popen[bytes], base_url: str) -> None:
    """Espera o GET /saude responder 200, com tempo limite (sem sleep fixo)."""
    prazo = time.monotonic() + LIMITE_SUBIDA_S
    while time.monotonic() < prazo:
        if processo.poll() is not None:
            raise RuntimeError(f"API alvo encerrou na subida (código {processo.returncode})")
        try:
            if httpx.get(f"{base_url}/saude", timeout=0.5).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(INTERVALO_CONSULTA_S)
    raise TimeoutError(f"API alvo não ficou saudável em {LIMITE_SUBIDA_S}s")


@contextmanager
def _subir_api_alvo(modo_falha: str | None) -> Iterator[str]:
    """Sobe a API alvo com uvicorn em subprocesso (ADR-004) e devolve a base URL.

    modo_falha=None remove MODO_FALHA do ambiente, para testar o padrão de verdade.
    """
    ambiente = {k: v for k, v in os.environ.items() if k != "MODO_FALHA"}
    if modo_falha is not None:
        ambiente["MODO_FALHA"] = modo_falha
    porta = _porta_livre()
    comando = [sys.executable, "-m", "uvicorn", "target_api.main:app"]
    comando += ["--host", "127.0.0.1", "--port", str(porta), "--log-level", "warning"]
    processo = subprocess.Popen(comando, cwd=RAIZ, env=ambiente)
    base_url = f"http://127.0.0.1:{porta}"
    try:
        _esperar_saude(processo, base_url)
        yield base_url
    finally:
        processo.terminate()
        try:
            processo.wait(timeout=10)
        except subprocess.TimeoutExpired:
            processo.kill()
            processo.wait()


# Escopo de função: cada teste recebe a API no estado inicial da seed (ADR-008).
@pytest.fixture
def api_alvo() -> Iterator[str]:
    """API alvo sem MODO_FALHA no ambiente."""
    with _subir_api_alvo(modo_falha=None) as base_url:
        yield base_url


@pytest.fixture
def api_alvo_com_falha() -> Iterator[str]:
    """API alvo com MODO_FALHA=true."""
    with _subir_api_alvo(modo_falha="true") as base_url:
        yield base_url
