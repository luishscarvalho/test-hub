from dataclasses import dataclass
from datetime import datetime


@dataclass
class ApiAlvo:
    nome: str
    base_url: str
    criado_em: datetime
    spec_url: str | None = None
    id: int | None = None
