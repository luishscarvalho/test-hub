"""Run interrompida pelas três causas da RN-12 (ADR-006).

O motivo gravado na run é montado aqui, a partir da causa. A entrada do worker só diz qual
foi a causa, sem decidir o texto nem o status.
"""

from enum import StrEnum

from app.application.portas import Relogio, RepositorioDeRuns
from app.domain.run import Run
from app.domain.status_run import StatusRun


class CausaDaInterrupcao(StrEnum):
    WORKER_REINICIADO = "worker_reiniciado"  # RN-12a
    TEMPO_EXCEDIDO = "tempo_excedido"  # RN-12b
    ERRO_INTERNO = "erro_interno"  # RN-12c


_MOTIVOS = {
    CausaDaInterrupcao.WORKER_REINICIADO: "Run interrompida: o worker reiniciou durante a execução",
    CausaDaInterrupcao.TEMPO_EXCEDIDO: "Run interrompida: tempo máximo de execução excedido",
    CausaDaInterrupcao.ERRO_INTERNO: "Run interrompida por erro interno do hub",
}


def motivo_da_interrupcao(causa: CausaDaInterrupcao, detalhe: str | None = None) -> str:
    motivo = _MOTIVOS[causa]
    return f"{motivo}: {detalhe}" if detalhe else motivo


class InterromperRun:
    """Usado pela entrada do worker quando o job termina com exceção (RN-12b e RN-12c)."""

    def __init__(self, *, runs: RepositorioDeRuns, relogio: Relogio) -> None:
        self._runs = runs
        self._relogio = relogio

    def executar(self, run_id: int, causa: CausaDaInterrupcao, detalhe: str | None = None) -> bool:
        """Interrompe a run se ela estiver em execução. Devolve se interrompeu.

        Run inexistente ou fora de em_execucao não muda: em status final não pode mudar
        (RN-05), e em na_fila só o início da execução pode tirá-la desse status (RN-11).
        """
        run = self._runs.buscar(run_id)
        if run is None or run.status != StatusRun.EM_EXECUCAO:
            return False
        _interromper(self._runs, run, self._relogio, motivo_da_interrupcao(causa, detalhe))
        return True


class RecuperarRunsPresas:
    """Usado na subida do worker (RN-12a).

    Worker único (ADR-006): na subida, nenhuma run pode estar em execução de verdade, então
    toda run em em_execucao ficou presa por uma queda anterior.
    """

    def __init__(self, *, runs: RepositorioDeRuns, relogio: Relogio) -> None:
        self._runs = runs
        self._relogio = relogio

    def executar(self) -> list[int]:
        """Devolve os ids das runs interrompidas."""
        motivo = motivo_da_interrupcao(CausaDaInterrupcao.WORKER_REINICIADO)
        presas = self._runs.listar_em_execucao()
        for run in presas:
            _interromper(self._runs, run, self._relogio, motivo)
        return [run.id for run in presas if run.id is not None]


def _interromper(runs: RepositorioDeRuns, run: Run, relogio: Relogio, motivo: str) -> None:
    # Sem resultados: run interrompida não tem resultados e tem totais zerados (RN-15).
    run.interromper(relogio(), motivo)
    runs.salvar(run, [])
