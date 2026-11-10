from dataclasses import dataclass
from datetime import datetime

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
