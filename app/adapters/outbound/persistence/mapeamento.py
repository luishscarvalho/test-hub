"""Conversão entre tabelas SQLModel e entidades do domínio.

Os enums das tabelas e os do domínio têm os mesmos valores. A conversão passa pelo valor
(texto), para que nenhum dos dois lados dependa do outro.
"""

from datetime import datetime
from typing import Any

from app.adapters.outbound.persistence.tabelas import (
    ApiAlvoTabela,
    ResultadoTesteTabela,
    RunTabela,
    SpecVersaoTabela,
)
from app.adapters.outbound.persistence.tabelas import OrigemSpec as OrigemSpecTabela
from app.adapters.outbound.persistence.tabelas import StatusResultado as StatusResultadoTabela
from app.adapters.outbound.persistence.tabelas import StatusRun as StatusRunTabela
from app.domain.api_alvo import ApiAlvo
from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado
from app.domain.run import Run
from app.domain.spec_versao import OrigemSpec, SpecVersao
from app.domain.status_run import StatusRun


def _criado_em(linha: ApiAlvoTabela | SpecVersaoTabela | RunTabela) -> datetime:
    # Linha lida do banco sempre tem criado_em: a coluna é NOT NULL com default now().
    if linha.criado_em is None:
        raise ValueError(f"{type(linha).__name__} sem criado_em: a linha não veio do banco")
    return linha.criado_em


def api_para_tabela(api: ApiAlvo) -> ApiAlvoTabela:
    return ApiAlvoTabela(
        id=api.id,
        nome=api.nome,
        base_url=api.base_url,
        spec_url=api.spec_url,
        criado_em=api.criado_em,
    )


def api_para_dominio(linha: ApiAlvoTabela) -> ApiAlvo:
    return ApiAlvo(
        id=linha.id,
        nome=linha.nome,
        base_url=linha.base_url,
        spec_url=linha.spec_url,
        criado_em=_criado_em(linha),
    )


def spec_para_tabela(spec: SpecVersao) -> SpecVersaoTabela:
    return SpecVersaoTabela(
        id=spec.id,
        api_alvo_id=spec.api_alvo_id,
        conteudo=spec.conteudo,
        hash=spec.hash,
        origem=OrigemSpecTabela(spec.origem.value),
        criado_em=spec.criado_em,
    )


def spec_para_dominio(linha: SpecVersaoTabela) -> SpecVersao:
    return SpecVersao(
        id=linha.id,
        api_alvo_id=linha.api_alvo_id,
        conteudo=linha.conteudo,
        hash=linha.hash,
        origem=OrigemSpec(linha.origem.value),
        criado_em=_criado_em(linha),
    )


def run_para_tabela(run: Run) -> RunTabela:
    return RunTabela(
        id=run.id,
        api_alvo_id=run.api_alvo_id,
        seed=run.seed,
        criado_em=run.criado_em,
        **estado_da_run(run),
    )


def estado_da_run(run: Run) -> dict[str, Any]:
    """Campos que mudam ao longo da execução. Identidade, seed e criação não mudam."""
    return {
        "spec_versao_id": run.spec_versao_id,
        "status": StatusRunTabela(run.status.value),
        "inicio": run.inicio,
        "fim": run.fim,
        "total_passou": run.total_passou,
        "total_falhou": run.total_falhou,
        "mensagem_erro": run.mensagem_erro,
    }


def run_para_dominio(linha: RunTabela) -> Run:
    return Run(
        id=linha.id,
        api_alvo_id=linha.api_alvo_id,
        seed=linha.seed,
        criado_em=_criado_em(linha),
        status=StatusRun(linha.status.value),
        spec_versao_id=linha.spec_versao_id,
        inicio=linha.inicio,
        fim=linha.fim,
        total_passou=linha.total_passou,
        total_falhou=linha.total_falhou,
        mensagem_erro=linha.mensagem_erro,
    )


def resultado_para_tabela(run_id: int, resultado: ResultadoDoTeste) -> ResultadoTesteTabela:
    return ResultadoTesteTabela(
        run_id=run_id,
        endpoint=resultado.endpoint,
        metodo=resultado.metodo,
        status=StatusResultadoTabela(resultado.status.value),
        duracao_ms=resultado.duracao_ms,
        mensagem_erro=resultado.mensagem_erro,
    )


def resultado_para_dominio(linha: ResultadoTesteTabela) -> ResultadoDoTeste:
    return ResultadoDoTeste(
        endpoint=linha.endpoint,
        metodo=linha.metodo,
        status=StatusResultado(linha.status.value),
        duracao_ms=linha.duracao_ms,
        mensagem_erro=linha.mensagem_erro,
    )
