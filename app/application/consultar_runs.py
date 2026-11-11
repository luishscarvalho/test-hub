"""Consulta do histórico de runs (US-07 e US-08)."""

from dataclasses import dataclass
from datetime import datetime

from app.application.portas import (
    ApiNaoEncontrada,
    RepositorioDeApis,
    RepositorioDeRuns,
    RunNaoEncontrada,
)
from app.domain.resultado_teste import ResultadoDoTeste
from app.domain.run import Run
from app.domain.status_run import StatusRun, eh_final


@dataclass(frozen=True)
class ResumoDaRun:
    """Item da listagem. Totais só existem para run em status final (US07-C4)."""

    id: int
    criado_em: datetime
    status: StatusRun
    total_passou: int | None
    total_falhou: int | None


@dataclass(frozen=True)
class DetalheDaRun:
    run: Run
    resultados: list[ResultadoDoTeste]


class ListarRuns:
    def __init__(self, *, apis: RepositorioDeApis, runs: RepositorioDeRuns) -> None:
        self._apis = apis
        self._runs = runs

    def executar(self, api_alvo_id: int) -> list[ResumoDaRun]:
        """Runs da API, da mais recente para a mais antiga (US07-C1, ordem do repositório)."""
        if self._apis.buscar(api_alvo_id) is None:
            raise ApiNaoEncontrada(f"API alvo {api_alvo_id} não existe")
        return [resumir(run) for run in self._runs.listar_por_api(api_alvo_id)]


def resumir(run: Run) -> ResumoDaRun:
    # Run lida do repositório sempre tem id.
    assert run.id is not None
    final = eh_final(run.status)
    return ResumoDaRun(
        id=run.id,
        criado_em=run.criado_em,
        status=run.status,
        total_passou=run.total_passou if final else None,
        total_falhou=run.total_falhou if final else None,
    )


class ConsultarRun:
    def __init__(self, *, runs: RepositorioDeRuns) -> None:
        self._runs = runs

    def executar(self, run_id: int) -> DetalheDaRun:
        """Run com os resultados. Run não finalizada vem com o status atual e sem resultados
        (US08-C4): os resultados só são gravados ao final (RN-15)."""
        run = self._runs.buscar(run_id)
        if run is None:
            raise RunNaoEncontrada(f"Run {run_id} não existe")
        resultados = self._runs.buscar_resultados(run_id) if eh_final(run.status) else []
        return DetalheDaRun(run, resultados)
