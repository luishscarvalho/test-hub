from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="API Alvo", version="0.1.0")


class SaudeResposta(BaseModel):
    status: str


@app.get("/saude")
def saude() -> SaudeResposta:
    return SaudeResposta(status="ok")
