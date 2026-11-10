"""Repositórios de API alvo e de versões da spec contra PostgreSQL (ADR-002 e ADR-007)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DataError, IntegrityError

from app.adapters.outbound.persistence.repositorio_apis import RepositorioDeApisSQL
from app.adapters.outbound.persistence.repositorio_specs import RepositorioDeSpecsSQL
from app.domain.api_alvo import ApiAlvo
from app.domain.spec_versao import OrigemSpec, SpecVersao

pytestmark = pytest.mark.integration

AGORA = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
HASH_A = "a" * 64
HASH_B = "b" * 64
# Hash da versão gravada junto com a API em _api(). Diferente dos usados nos testes.
HASH_CADASTRO = "0" * 64
CONTEUDO: dict[str, object] = {
    "openapi": "3.1.0",
    "info": {"title": "x", "version": "1"},
    "paths": {"/a": {}},
}


def _spec(api_alvo_id: int, hash: str = HASH_A, criado_em: datetime = AGORA) -> SpecVersao:
    return SpecVersao(
        api_alvo_id=api_alvo_id,
        conteudo=CONTEUDO,
        hash=hash,
        origem=OrigemSpec.URL,
        criado_em=criado_em,
    )


def _api(engine: Engine, nome: str = "tarefas") -> ApiAlvo:
    api = ApiAlvo(nome=nome, base_url="http://alvo:8000", criado_em=AGORA, spec_url="http://s")
    return RepositorioDeApisSQL(engine).adicionar(api, _spec(0, HASH_CADASTRO))


def _contar(engine: Engine, tabela: str) -> int:
    with engine.connect() as conexao:
        total: int = conexao.execute(text(f"SELECT count(*) FROM {tabela}")).scalar_one()
        return total


def test_us01_c3_adicionar_api_devolve_o_identificador_e_os_dados_gravados(
    engine: Engine,
) -> None:
    repositorio = RepositorioDeApisSQL(engine)
    entrada = ApiAlvo(nome="tarefas", base_url="http://alvo:8000", criado_em=AGORA)

    gravada = repositorio.adicionar(entrada, _spec(0))

    assert gravada.id is not None
    # A versão fica ligada à API recém-criada, não ao api_alvo_id que veio na spec.
    versao = RepositorioDeSpecsSQL(engine).buscar_mais_recente(gravada.id)
    assert versao is not None and versao.hash == HASH_A
    # Lida de novo em outra sessão: prova que foi confirmada no banco, não só no objeto.
    assert repositorio.buscar(gravada.id) == ApiAlvo(
        id=gravada.id,
        nome="tarefas",
        base_url="http://alvo:8000",
        spec_url=None,
        criado_em=AGORA,
    )


def test_us02_c1_falha_ao_gravar_a_spec_desfaz_a_gravacao_da_api(engine: Engine) -> None:
    entrada = ApiAlvo(nome="tarefas", base_url="http://alvo:8000", criado_em=AGORA)
    # Hash maior que CHAR(64): o INSERT da spec falha depois do INSERT da API.
    # Se a API fosse confirmada em outra transação, ela sobreviveria ao erro.
    spec_que_falha = _spec(0, hash="x" * 65)

    with pytest.raises(DataError, match="character"):
        RepositorioDeApisSQL(engine).adicionar(entrada, spec_que_falha)

    assert _contar(engine, "api_alvo") == 0
    assert _contar(engine, "spec_versao") == 0


def test_us04_c1_buscar_api_inexistente_devolve_none(engine: Engine) -> None:
    _api(engine)
    assert RepositorioDeApisSQL(engine).buscar(999_999) is None


def test_us02_c4_spec_e_gravada_como_versao_com_hash(engine: Engine) -> None:
    api = _api(engine)
    assert api.id is not None
    repositorio = RepositorioDeSpecsSQL(engine)

    gravada = repositorio.adicionar(_spec(api.id))

    assert gravada.id is not None
    assert repositorio.buscar_por_hash(api.id, HASH_A) == SpecVersao(
        id=gravada.id,
        api_alvo_id=api.id,
        conteudo=CONTEUDO,
        hash=HASH_A,
        origem=OrigemSpec.URL,
        criado_em=AGORA,
    )


def test_rn13_t2_buscar_por_hash_so_encontra_a_versao_da_mesma_api(engine: Engine) -> None:
    api, outra = _api(engine, "a"), _api(engine, "b")
    assert api.id is not None and outra.id is not None
    repositorio = RepositorioDeSpecsSQL(engine)
    repositorio.adicionar(_spec(outra.id, HASH_A))

    # Mesmo hash, outra API: não pode ser reaproveitada.
    assert repositorio.buscar_por_hash(api.id, HASH_A) is None
    assert repositorio.buscar_por_hash(outra.id, HASH_B) is None
    assert repositorio.buscar_por_hash(outra.id, HASH_A) is not None


def test_rn13_t2_mesma_api_e_mesmo_hash_nao_sao_gravados_duas_vezes(engine: Engine) -> None:
    api = _api(engine)
    assert api.id is not None
    repositorio = RepositorioDeSpecsSQL(engine)
    repositorio.adicionar(_spec(api.id, HASH_A))

    with pytest.raises(IntegrityError, match="uq_spec_versao_api_hash"):
        repositorio.adicionar(_spec(api.id, HASH_A))

    # A versão do cadastro e a primeira com HASH_A.
    assert _contar(engine, "spec_versao") == 2


def test_rn13_t3_buscar_mais_recente_devolve_a_ultima_versao_da_api(engine: Engine) -> None:
    api, outra = _api(engine, "a"), _api(engine, "b")
    assert api.id is not None and outra.id is not None
    repositorio = RepositorioDeSpecsSQL(engine)
    # A mais recente é gravada primeiro: a ordem tem de vir de criado_em, não do id.
    recente = repositorio.adicionar(_spec(api.id, HASH_B, AGORA + timedelta(minutes=1)))
    repositorio.adicionar(_spec(api.id, HASH_A, AGORA))
    repositorio.adicionar(_spec(outra.id, "c" * 64, AGORA + timedelta(hours=1)))

    assert repositorio.buscar_mais_recente(api.id) == recente


def test_rn13_t3_api_sem_versao_devolve_none(engine: Engine) -> None:
    # O repositório de APIs sempre grava uma versão: a API sem versão vai direto ao banco.
    with engine.begin() as conexao:
        api_id = conexao.execute(
            text("INSERT INTO api_alvo (nome, base_url) VALUES ('a', 'http://a') RETURNING id")
        ).scalar_one()
    assert RepositorioDeSpecsSQL(engine).buscar_mais_recente(api_id) is None


def test_rn13_t5_versao_referenciada_por_run_nao_pode_ser_removida(engine: Engine) -> None:
    api = _api(engine)
    assert api.id is not None
    spec = RepositorioDeSpecsSQL(engine).adicionar(_spec(api.id))
    with engine.begin() as conexao:
        conexao.execute(
            text("INSERT INTO run (api_alvo_id, spec_versao_id, seed) VALUES (:api, :spec, 1)"),
            {"api": api.id, "spec": spec.id},
        )

    # O repositório não tem remoção: o teste vai direto ao banco, que é a última barreira.
    with pytest.raises(IntegrityError, match="foreign key"), engine.begin() as conexao:
        conexao.execute(text("DELETE FROM spec_versao WHERE id = :id"), {"id": spec.id})
