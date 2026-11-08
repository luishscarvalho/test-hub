from pydantic import BaseModel, Field


class TarefaEntrada(BaseModel):
    """Corpo de criação e edição. Não tem id: quem gera é a API (ADR-008)."""

    titulo: str = Field(min_length=1, max_length=200)
    concluida: bool = False


class Tarefa(BaseModel):
    id: int
    titulo: str
    concluida: bool


class Erro(BaseModel):
    """Mesmo formato do corpo que o FastAPI devolve em HTTPException."""

    detail: str


class SaudeResposta(BaseModel):
    status: str
