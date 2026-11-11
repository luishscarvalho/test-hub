"""Run interrompida pelas causas da RN-12 (US-05, RN-05, RN-12 e RN-15)."""

import pytest

from app.application.interromper_run import (
    CausaDaInterrupcao,
    InterromperRun,
    RecuperarRunsPresas,
)
from app.domain.run import Run
from app.domain.status_run import StatusRun
from tests.unit.application.fakes import (
    INICIO_DO_RELOGIO,
    RelogioFalso,
    RepositorioDeRunsFalso,
)

pytestmark = pytest.mark.unit


def _run(runs: RepositorioDeRunsFalso, status: StatusRun) -> int:
    """Grava uma run e a leva até o status pedido pelos métodos do domínio."""
    run = runs.adicionar(Run(1, 42, INICIO_DO_RELOGIO))
    assert run.id is not None
    if status != StatusRun.NA_FILA:
        run.iniciar(INICIO_DO_RELOGIO)
        runs.salvar(run, [])
    if status == StatusRun.FALHOU:
        run.falhar(INICIO_DO_RELOGIO, "spec inválida")
        runs.salvar(run, [])
    return run.id


@pytest.fixture
def runs() -> RepositorioDeRunsFalso:
    return RepositorioDeRunsFalso()


def _interromper(runs: RepositorioDeRunsFalso) -> InterromperRun:
    return InterromperRun(runs=runs, relogio=RelogioFalso())


def test_rn12_t2_tempo_excedido_interrompe_com_fim_e_motivo(runs: RepositorioDeRunsFalso) -> None:
    run_id = _run(runs, StatusRun.EM_EXECUCAO)

    assert _interromper(runs).executar(run_id, CausaDaInterrupcao.TEMPO_EXCEDIDO)

    run = runs.runs[run_id]
    assert run.status == StatusRun.INTERROMPIDA
    assert run.fim is not None
    assert run.mensagem_erro == "Run interrompida: tempo máximo de execução excedido"


def test_rn12_t3_erro_interno_interrompe_com_o_detalhe_e_nunca_como_falhou(
    runs: RepositorioDeRunsFalso,
) -> None:
    run_id = _run(runs, StatusRun.EM_EXECUCAO)

    _interromper(runs).executar(run_id, CausaDaInterrupcao.ERRO_INTERNO, "RuntimeError: bug")

    run = runs.runs[run_id]
    assert run.status == StatusRun.INTERROMPIDA
    assert run.mensagem_erro == "Run interrompida por erro interno do hub: RuntimeError: bug"


def test_us05_c1_run_interrompida_registra_inicio_e_fim(runs: RepositorioDeRunsFalso) -> None:
    run_id = _run(runs, StatusRun.EM_EXECUCAO)

    _interromper(runs).executar(run_id, CausaDaInterrupcao.ERRO_INTERNO)

    run = runs.runs[run_id]
    assert run.inicio is not None and run.fim is not None
    assert run.inicio < run.fim


def test_rn15_t1_run_interrompida_nao_tem_resultados_e_tem_totais_zerados(
    runs: RepositorioDeRunsFalso,
) -> None:
    run_id = _run(runs, StatusRun.EM_EXECUCAO)

    _interromper(runs).executar(run_id, CausaDaInterrupcao.TEMPO_EXCEDIDO)

    final, resultados = runs.gravacoes[-1]
    assert resultados == []
    assert (final.total_passou, final.total_falhou) == (0, 0)


@pytest.mark.parametrize("status", [StatusRun.FALHOU, StatusRun.NA_FILA])
def test_rn05_t1_run_fora_de_execucao_nao_e_interrompida(
    runs: RepositorioDeRunsFalso, status: StatusRun
) -> None:
    run_id = _run(runs, status)
    gravacoes = len(runs.gravacoes)

    assert not _interromper(runs).executar(run_id, CausaDaInterrupcao.ERRO_INTERNO)

    assert runs.runs[run_id].status == status
    assert len(runs.gravacoes) == gravacoes


def test_rn12_t3_run_inexistente_nao_e_interrompida(runs: RepositorioDeRunsFalso) -> None:
    assert not _interromper(runs).executar(99, CausaDaInterrupcao.ERRO_INTERNO)


def test_rn12_t1_subida_do_worker_interrompe_toda_run_presa_em_execucao(
    runs: RepositorioDeRunsFalso,
) -> None:
    presa_1 = _run(runs, StatusRun.EM_EXECUCAO)
    na_fila = _run(runs, StatusRun.NA_FILA)
    presa_2 = _run(runs, StatusRun.EM_EXECUCAO)

    interrompidas = RecuperarRunsPresas(runs=runs, relogio=RelogioFalso()).executar()

    assert interrompidas == [presa_1, presa_2]
    for run_id in (presa_1, presa_2):
        run = runs.runs[run_id]
        assert run.status == StatusRun.INTERROMPIDA
        assert run.fim is not None
        assert run.mensagem_erro == "Run interrompida: o worker reiniciou durante a execução"
    assert runs.runs[na_fila].status == StatusRun.NA_FILA


def test_rn12_t1_subida_sem_runs_presas_nao_altera_nada(runs: RepositorioDeRunsFalso) -> None:
    _run(runs, StatusRun.NA_FILA)

    assert RecuperarRunsPresas(runs=runs, relogio=RelogioFalso()).executar() == []
    assert runs.gravacoes == []
