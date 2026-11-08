from fastapi import FastAPI

from app.adapters.inbound.http.saude import router as saude_router

app = FastAPI(title="Test Hub", version="0.1.0")
app.include_router(saude_router)
