"""Repositório de runs contra PostgreSQL (ADR-002 e ADR-006)."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.adapters.outbound.persistence.repositorio_apis import RepositorioDeApisSQL
from app.adapters.outbound.persistence.repositorio_runs import (
    RepositorioDeRunsSQL,
    RunNaoEncontrada,
)
from app.adapters.outbound.persistence.repositorio_specs import RepositorioDeSpecsSQL
from app.domain.api_alvo import ApiAlvo
from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado
from app.domain.run import Run
from app.domain.spec_versao import OrigemSpec, SpecVersao
from app.domain.status_run import StatusRun

pytestmark = pytest.mark.integration

AGORA = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
SEED = 20261110

PASSOU = ResultadoDoTeste("/tarefas", "GET", StatusResultado.PASSOU, 12, None)
FALHOU = ResultadoDoTeste(
    "/tarefas/{id}", "GET", StatusResultado.FALHOU, 30, "Response violates schema"
)


def _api(engine: Engine, nome: str = "tarefas") -> int:
    api = RepositorioDeApisSQL(engine).adicionar(
        ApiAlvo(nome=nome, base_url="http://alvo:8000", criado_em=AGORA)
    )
    assert api.id is not None
    return api.id


def _spec(engine: Engine, api_alvo_id: int) -> int:
    spec = RepositorioDeSpecsSQL(engine).adicionar(
        SpecVersao(api_alvo_id, {"openapi": "3.1.0"}, "a" * 64, OrigemSpec.URL, AGORA)
    )
    assert spec.id is not None
    return spec.id


def _run_na_fila(engine: Engine, api_alvo_id: int, criado_em: datetime = AGORA) -> Run:
    return RepositorioDeRunsSQL(engine).adicionar(Run(api_alvo_id, SEED, criado_em))


def _contar(engine: Engine, tabela: str) -> int:
    with engine.connect() as conexao:
        total: int = conexao.execute(text(f"SELECT count(*) FROM {tabela}")).scalar_one()
        return total


def test_rn14_t1_run_adicionada_registra_a_seed_e_nasce_na_fila(engine: Engine) -> None:
    api_id = _api(engine)
    repositorio = RepositorioDeRunsSQL(engine)

    gravada = repositorio.adicionar(Run(api_id, SEED, AGORA))

    assert gravada.id is not None
    assert repositorio.buscar(gravada.id) == Run(
        id=gravada.id, api_alvo_id=api_id, seed=SEED, criado_em=AGORA, status=StatusRun.NA_FILA
    )


def test_us08_c3_buscar_run_inexistente_devolve_none(engine: Engine) -> None:
    _run_na_fila(engine, _api(engine))
    assert RepositorioDeRunsSQL(engine).buscar(999_999) is None


def test_us06_c1_salvar_grava_estado_da_run_e_todos_os_campos_dos_resultados(
    engine: Engine,
) -> None:
    api_id = _api(engine)
    repositorio = RepositorioDeRunsSQL(engine)
    run = _run_na_fila(engine, api_id)
    run.iniciar(AGORA)
    run.spec_versao_id = _spec(engine, api_id)
    run.finalizar(AGORA + timedelta(seconds=5), [PASSOU, FALHOU])
    assert run.id is not None

    repositorio.salvar(run, [PASSOU, FALHOU])

    assert repositorio.buscar_resultados(run.id) == [PASSOU, FALHOU]
    lida = repositorio.buscar(run.id)
    assert lida == run
    assert lida.status == StatusRun.FALHOU
    assert (lida.total_passou, lida.total_falhou) == (1, 1)


def test_rn15_t1_falha_ao_gravar_resultado_desfaz_status_e_totais(engine: Engine) -> None:
    api_id = _api(engine)
    repositorio = RepositorioDeRunsSQL(engine)
    run = _run_na_fila(engine, api_id)
    run.iniciar(AGORA)
    repositorio.salvar(run, [])
    assert run.id is not None
    em_execucao = repositorio.buscar(run.id)

    # O mesmo par endpoint e método duas vezes viola uq_resultado_run_endpoint_metodo.
    # Se o UPDATE da run estivesse em outra transação, o status final sobreviveria ao erro.
    duplicados = [PASSOU, replace(PASSOU, duracao_ms=99)]
    run.spec_versao_id = _spec(engine, api_id)
    run.finalizar(AGORA + timedelta(seconds=5), duplicados)
    with pytest.raises(IntegrityError, match="uq_resultado_run_endpoint_metodo"):
        repositorio.salvar(run, duplicados)

    assert repositorio.buscar(run.id) == em_execucao
    assert em_execucao is not None and em_execucao.status == StatusRun.EM_EXECUCAO
    assert repositorio.buscar_resultados(run.id) == []
    assert _contar(engine, "resultado_teste") == 0


def test_rn15_t1_run_interrompida_e_salva_sem_resultados_e_com_totais_zerados(
    engine: Engine,
) -> None:
    repositorio = RepositorioDeRunsSQL(engine)
    run = _run_na_fila(engine, _api(engine))
    run.iniciar(AGORA)
    run.interromper(AGORA + timedelta(minutes=10), "Tempo máximo excedido")
    assert run.id is not None

    repositorio.salvar(run, [])

    lida = repositorio.buscar(run.id)
    assert lida is not None
    assert (lida.status, lida.fim, lida.mensagem_erro) == (
        StatusRun.INTERROMPIDA,
        AGORA + timedelta(minutes=10),
        "Tempo máximo excedido",
    )
    assert (lida.total_passou, lida.total_falhou, lida.spec_versao_id) == (0, 0, None)
    assert repositorio.buscar_resultados(run.id) == []


def test_us04_c6_remover_apaga_a_run_do_banco(engine: Engine) -> None:
    repositorio = RepositorioDeRunsSQL(engine)
    run = _run_na_fila(engine, _api(engine))
    outra = _run_na_fila(engine, _api(engine, "outra"))
    assert run.id is not None and outra.id is not None

    repositorio.remover(run.id)

    assert repositorio.buscar(run.id) is None
    assert repositorio.buscar(outra.id) == outra


def test_us04_c6_remover_run_inexistente_levanta_erro(engine: Engine) -> None:
    with pytest.raises(RunNaoEncontrada):
        RepositorioDeRunsSQL(engine).remover(999_999)


def test_us07_c1_listar_por_api_traz_so_as_runs_da_api_da_mais_recente_para_a_antiga(
    engine: Engine,
) -> None:
    api_id, outra_id = _api(engine), _api(engine, "outra")
    # Gravadas fora de ordem: a ordem do resultado tem de vir de criado_em, não do id.
    meio = _run_na_fila(engine, api_id, AGORA)
    nova = _run_na_fila(engine, api_id, AGORA + timedelta(hours=1))
    _run_na_fila(engine, outra_id, AGORA + timedelta(hours=2))
    antiga = _run_na_fila(engine, api_id, AGORA - timedelta(hours=1))

    assert RepositorioDeRunsSQL(engine).listar_por_api(api_id) == [nova, meio, antiga]


def test_us07_c3_api_sem_runs_devolve_lista_vazia(engine: Engine) -> None:
    _run_na_fila(engine, _api(engine, "com runs"))
    assert RepositorioDeRunsSQL(engine).listar_por_api(_api(engine)) == []


def test_rn12_t1_listar_em_execucao_traz_so_runs_em_execucao(engine: Engine) -> None:
    api_id = _api(engine)
    repositorio = RepositorioDeRunsSQL(engine)
    _run_na_fila(engine, api_id)
    presa = _run_na_fila(engine, api_id)
    presa.iniciar(AGORA)
    repositorio.salvar(presa, [])
    terminada = _run_na_fila(engine, api_id)
    terminada.iniciar(AGORA)
    terminada.interromper(AGORA, "Erro interno")
    repositorio.salvar(terminada, [])

    assert repositorio.listar_em_execucao() == [presa]
