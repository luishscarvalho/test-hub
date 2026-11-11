"""DTOs da API do hub (ERS 10.3). Separados das tabelas e das entidades (ADR-002)."""

from datetime import datetime

from pydantic import BaseModel

from app.application.consultar_runs import DetalheDaRun, ResumoDaRun, resumir
from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado
from app.domain.status_run import StatusRun


class Erro(BaseModel):
    detail: str


class ApiCriada(BaseModel):
    id: int


class DisparoDeRun(BaseModel):
    api_alvo_id: int


class RunDisparada(BaseModel):
    id: int
    status: StatusRun


class RunResumo(BaseModel):
    id: int
    criado_em: datetime
    status: StatusRun
    # Nulos enquanto a run não está em status final (US07-C4).
    total_passou: int | None
    total_falhou: int | None

    @classmethod
    def de(cls, resumo: ResumoDaRun) -> "RunResumo":
        return cls(
            id=resumo.id,
            criado_em=resumo.criado_em,
            status=resumo.status,
            total_passou=resumo.total_passou,
            total_falhou=resumo.total_falhou,
        )


class ResultadoTeste(BaseModel):
    endpoint: str
    metodo: str
    status: StatusResultado
    duracao_ms: int
    mensagem_erro: str | None

    @classmethod
    def de(cls, resultado: ResultadoDoTeste) -> "ResultadoTeste":
        return cls(
            endpoint=resultado.endpoint,
            metodo=resultado.metodo,
            status=resultado.status,
            duracao_ms=resultado.duracao_ms,
            mensagem_erro=resultado.mensagem_erro,
        )


class RunDetalhe(RunResumo):
    api_alvo_id: int
    seed: int
    # Nula quando a run terminou antes de resolver a spec (RN-13).
    spec_versao_id: int | None
    inicio: datetime | None
    fim: datetime | None
    mensagem_erro: str | None
    resultados: list[ResultadoTeste]

    @classmethod
    def do_detalhe(cls, detalhe: DetalheDaRun) -> "RunDetalhe":
        run = detalhe.run
        resumo = resumir(run)
        return cls(
            **RunResumo.de(resumo).model_dump(),
            api_alvo_id=run.api_alvo_id,
            seed=run.seed,
            spec_versao_id=run.spec_versao_id,
            inicio=run.inicio,
            fim=run.fim,
            mensagem_erro=run.mensagem_erro,
            resultados=[ResultadoTeste.de(r) for r in detalhe.resultados],
        )
