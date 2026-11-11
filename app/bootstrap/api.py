from fastapi import FastAPI

from app.adapters.inbound.http.rotas import CasosDeUsoHttp, criar_router
from app.adapters.inbound.http.saude import router as saude_router
from app.bootstrap.configuracao import Configuracao
from app.bootstrap.container import Container, montar


def criar_app(container: Container) -> FastAPI:
    app = FastAPI(title="Test Hub", version="0.1.0")
    app.include_router(saude_router)
    app.include_router(
        criar_router(
            CasosDeUsoHttp(
                cadastrar_api=container.cadastrar_api,
                disparar_run=container.disparar_run,
                listar_runs=container.listar_runs,
                consultar_run=container.consultar_run,
            )
        )
    )
    return app


# uvicorn app.bootstrap.api:app. O engine e o Redis só conectam no primeiro uso.
app = criar_app(montar(Configuracao()))
