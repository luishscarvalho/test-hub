"""Caso de uso de disparo da run (US-04, RN-14 e RN-16)."""

import pytest

from app.application.disparar_run import DispararRun
from app.application.portas import ApiNaoEncontrada, FilaIndisponivel
from app.domain.api_alvo import ApiAlvo
from app.domain.spec_versao import OrigemSpec, SpecVersao
from app.domain.status_run import StatusRun
from tests.unit.application.fakes import (
    INICIO_DO_RELOGIO,
    ExecutorDeRunFalso,
    RelogioFalso,
    RepositorioDeApisFalso,
    RepositorioDeRunsFalso,
)

pytestmark = pytest.mark.unit

SEED = 20261111


@pytest.fixture
def apis() -> RepositorioDeApisFalso:
    apis = RepositorioDeApisFalso()
    spec = SpecVersao(0, {}, "0" * 64, OrigemSpec.ARQUIVO, INICIO_DO_RELOGIO)
    apis.adicionar(ApiAlvo("tarefas", "http://alvo:8000", INICIO_DO_RELOGIO), spec)
    return apis


@pytest.fixture
def runs() -> RepositorioDeRunsFalso:
    return RepositorioDeRunsFalso()


def _disparar(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso, executor: ExecutorDeRunFalso
) -> DispararRun:
    return DispararRun(apis=apis, runs=runs, executor=executor, relogio=RelogioFalso(), seed=SEED)


def test_us04_c4_disparo_devolve_run_na_fila_com_identificador(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso
) -> None:
    run = _disparar(apis, runs, ExecutorDeRunFalso()).executar(1)

    assert run.id == 1
    assert run.status == StatusRun.NA_FILA
    assert runs.runs[1].status == StatusRun.NA_FILA


def test_us04_c4_disparo_enfileira_a_run_sem_executar(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso
) -> None:
    executor = ExecutorDeRunFalso()

    _disparar(apis, runs, executor).executar(1)

    assert executor.enfileiradas == [1]
    assert runs.gravacoes == []


def test_rn14_t1_run_registra_a_seed_configurada(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso
) -> None:
    _disparar(apis, runs, ExecutorDeRunFalso()).executar(1)

    assert runs.runs[1].seed == SEED


def test_us04_c1_api_inexistente_nao_cria_nem_enfileira_run(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso
) -> None:
    executor = ExecutorDeRunFalso()

    with pytest.raises(ApiNaoEncontrada):
        _disparar(apis, runs, executor).executar(99)

    assert runs.runs == {}
    assert executor.enfileiradas == []


def test_us04_c6_fila_indisponivel_remove_a_run_e_avisa(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso
) -> None:
    with pytest.raises(FilaIndisponivel):
        _disparar(apis, runs, ExecutorDeRunFalso(indisponivel=True)).executar(1)

    assert runs.runs == {}
