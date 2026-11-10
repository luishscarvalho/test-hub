from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OrigemSpec(StrEnum):
    URL = "url"
    ARQUIVO = "arquivo"


@dataclass(frozen=True)
class SpecVersao:
    api_alvo_id: int
    conteudo: dict[str, object]
    hash: str
    origem: OrigemSpec
    criado_em: datetime
    id: int | None = None
