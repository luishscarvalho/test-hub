from dataclasses import dataclass
from datetime import datetime

from app.domain.apuracao_run import apurar_resultados
from app.domain.resultado_teste import ResultadoDoTeste
from app.domain.status_run import StatusRun, transicionar


@dataclass
class Run:
    api_alvo_id: int
    seed: int
    criado_em: datetime
    id: int | None = None
    status: StatusRun = StatusRun.NA_FILA
    spec_versao_id: int | None = None
    inicio: datetime | None = None
    fim: datetime | None = None
    total_passou: int = 0
    total_falhou: int = 0
    mensagem_erro: str | None = None

    def iniciar(self, agora: datetime) -> None:
        self.status = transicionar(self.status, StatusRun.EM_EXECUCAO)
        self.inicio = agora

    def finalizar(self, agora: datetime, resultados: list[ResultadoDoTeste]) -> None:
        apuracao = apurar_resultados(resultados)
        self.status = transicionar(self.status, apuracao.status)
        self.fim = agora
        self.total_passou = apuracao.total_passou
        self.total_falhou = apuracao.total_falhou

    def falhar(self, agora: datetime, motivo: str) -> None:
        self.status = transicionar(self.status, StatusRun.FALHOU)
        self.fim = agora
        self.mensagem_erro = motivo

    def interromper(self, agora: datetime, motivo: str) -> None:
        self.status = transicionar(self.status, StatusRun.INTERROMPIDA)
        self.fim = agora
        self.mensagem_erro = motivo
