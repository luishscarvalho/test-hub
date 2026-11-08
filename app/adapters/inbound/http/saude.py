from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["saude"])


class SaudeResposta(BaseModel):
    status: str


@router.get("/saude")
def saude() -> SaudeResposta:
    return SaudeResposta(status="ok")
