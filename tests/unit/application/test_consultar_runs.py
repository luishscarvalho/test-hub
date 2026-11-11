"""Consulta do histórico de runs (US-07 e US-08).

A ordem da listagem (US07-C1) é responsabilidade do repositório e fica nos testes de
integração. Aqui, o falso já devolve na ordem certa.
"""

import pytest

from app.application.consultar_runs import ConsultarRun, ListarRuns
from app.application.portas import ApiNaoEncontrada, RunNaoEncontrada
from app.domain.api_alvo import ApiAlvo
from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado
from app.domain.run import Run
from app.domain.spec_versao import OrigemSpec, SpecVersao
from app.domain.status_run import StatusRun
from tests.unit.application.fakes import (
    INICIO_DO_RELOGIO,
    RepositorioDeApisFalso,
    RepositorioDeRunsFalso,
)

pytestmark = pytest.mark.unit

OK = ResultadoDoTeste("/tarefas", "GET", StatusResultado.PASSOU, 12, None)
ERRO = ResultadoDoTeste("/tarefas/{id}", "GET", StatusResultado.FALHOU, 30, "schema")


@pytest.fixture
def apis() -> RepositorioDeApisFalso:
    apis = RepositorioDeApisFalso()
    spec = SpecVersao(0, {}, "0" * 64, OrigemSpec.ARQUIVO, INICIO_DO_RELOGIO)
    apis.adicionar(ApiAlvo("tarefas", "http://alvo:8000", INICIO_DO_RELOGIO), spec)
    return apis


@pytest.fixture
def runs() -> RepositorioDeRunsFalso:
    return RepositorioDeRunsFalso()


def _finalizada(runs: RepositorioDeRunsFalso, resultados: list[ResultadoDoTeste]) -> int:
    run = runs.adicionar(Run(1, 42, INICIO_DO_RELOGIO))
    assert run.id is not None
    run.iniciar(INICIO_DO_RELOGIO)
    run.spec_versao_id = 100
    run.finalizar(INICIO_DO_RELOGIO, resultados)
    runs.salvar(run, resultados)
    return run.id


def _em_execucao(runs: RepositorioDeRunsFalso) -> int:
    run = runs.adicionar(Run(1, 42, INICIO_DO_RELOGIO))
    assert run.id is not None
    run.iniciar(INICIO_DO_RELOGIO)
    runs.salvar(run, [])
    return run.id


def test_us07_c3_api_sem_runs_retorna_lista_vazia(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso
) -> None:
    assert ListarRuns(apis=apis, runs=runs).executar(1) == []


def test_us07_c3_api_inexistente_nao_e_tratada_como_lista_vazia(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso
) -> None:
    with pytest.raises(ApiNaoEncontrada):
        ListarRuns(apis=apis, runs=runs).executar(99)


def test_us07_c2_item_traz_data_status_e_totais(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso
) -> None:
    run_id = _finalizada(runs, [OK, ERRO])

    [item] = ListarRuns(apis=apis, runs=runs).executar(1)

    assert (item.id, item.criado_em, item.status) == (run_id, INICIO_DO_RELOGIO, StatusRun.FALHOU)
    assert (item.total_passou, item.total_falhou) == (1, 1)


def test_us07_c4_run_nao_finalizada_aparece_com_status_atual_e_sem_totais(
    apis: RepositorioDeApisFalso, runs: RepositorioDeRunsFalso
) -> None:
    _em_execucao(runs)

    [item] = ListarRuns(apis=apis, runs=runs).executar(1)

    assert item.status == StatusRun.EM_EXECUCAO
    assert (item.total_passou, item.total_falhou) == (None, None)


def test_us08_c1_detalhe_traz_a_run_e_os_resultados(runs: RepositorioDeRunsFalso) -> None:
    run_id = _finalizada(runs, [OK, ERRO])

    detalhe = ConsultarRun(runs=runs).executar(run_id)

    assert detalhe.run.id == run_id
    assert detalhe.resultados == [OK, ERRO]


def test_us08_c5_detalhe_traz_seed_e_versao_da_spec(runs: RepositorioDeRunsFalso) -> None:
    run_id = _finalizada(runs, [OK])

    detalhe = ConsultarRun(runs=runs).executar(run_id)

    assert (detalhe.run.seed, detalhe.run.spec_versao_id) == (42, 100)


def test_us08_c3_run_inexistente(runs: RepositorioDeRunsFalso) -> None:
    with pytest.raises(RunNaoEncontrada):
        ConsultarRun(runs=runs).executar(99)


def test_us08_c4_run_nao_finalizada_retorna_status_atual_sem_resultados(
    runs: RepositorioDeRunsFalso,
) -> None:
    run_id = _em_execucao(runs)
    # Mesmo que existissem linhas, run em execução não mostra resultados parciais.
    runs.resultados[run_id] = [OK]

    detalhe = ConsultarRun(runs=runs).executar(run_id)

    assert detalhe.run.status == StatusRun.EM_EXECUCAO
    assert detalhe.resultados == []
