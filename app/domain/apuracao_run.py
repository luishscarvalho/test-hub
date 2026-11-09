from dataclasses import dataclass

from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado
from app.domain.status_run import StatusRun


@dataclass(frozen=True)
class ApuracaoRun:
    status: StatusRun
    total_passou: int
    total_falhou: int


def apurar_resultados(resultados: list[ResultadoDoTeste]) -> ApuracaoRun:
    total_passou = 0
    total_falhou = 0

    for resultado in resultados:
        if resultado.status == StatusResultado.PASSOU:
            total_passou += 1
        else:
            total_falhou += 1

    status = StatusRun.PASSOU if total_passou > 0 and total_falhou == 0 else StatusRun.FALHOU
    return ApuracaoRun(status, total_passou, total_falhou)
