from typing import Any

from fastapi import FastAPI, HTTPException, Response, status

from target_api.modelos import Erro, SaudeResposta, Tarefa, TarefaEntrada
from target_api.repositorio import RepositorioDeTarefas

# Todo erro esperado precisa estar declarado na rota para constar na spec (ADR-008).
NAO_ENCONTRADA: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": Erro, "description": "Tarefa não encontrada"},
}


def _nao_encontrada(id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Tarefa {id} não encontrada")


def criar_app() -> FastAPI:
    """Cada instância tem o próprio repositório, carregado com a seed."""
    repositorio = RepositorioDeTarefas()
    app = FastAPI(title="API Alvo", version="0.1.0")

    @app.get("/saude")
    def saude() -> SaudeResposta:
        return SaudeResposta(status="ok")

    @app.get("/tarefas")
    def listar_tarefas() -> list[Tarefa]:
        return repositorio.listar()

    @app.get("/tarefas/{id}", responses=NAO_ENCONTRADA)
    def buscar_tarefa(id: int) -> Tarefa:
        tarefa = repositorio.buscar(id)
        if tarefa is None:
            raise _nao_encontrada(id)
        return tarefa

    @app.post("/tarefas", status_code=status.HTTP_201_CREATED)
    def criar_tarefa(entrada: TarefaEntrada) -> Tarefa:
        return repositorio.criar(entrada)

    @app.put("/tarefas/{id}", responses=NAO_ENCONTRADA)
    def editar_tarefa(id: int, entrada: TarefaEntrada) -> Tarefa:
        tarefa = repositorio.editar(id, entrada)
        if tarefa is None:
            raise _nao_encontrada(id)
        return tarefa

    @app.delete(
        "/tarefas/{id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
        responses=NAO_ENCONTRADA,
    )
    def apagar_tarefa(id: int) -> Response:
        if not repositorio.apagar(id):
            raise _nao_encontrada(id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = criar_app()
