from typing import Any

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse

from target_api.config import Configuracao
from target_api.modelos import Erro, SaudeResposta, Tarefa, TarefaEntrada
from target_api.repositorio import RepositorioDeTarefas

# Todo erro esperado precisa estar declarado na rota para constar na spec (ADR-008).
NAO_ENCONTRADA: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": Erro, "description": "Tarefa não encontrada"},
}


def _nao_encontrada(id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Tarefa {id} não encontrada")


def _tarefa_com_tipos_errados(id: int) -> JSONResponse:
    """Nenhum campo tem o tipo prometido na spec. Sai direto, sem validação do FastAPI."""
    corpo = {"id": f"tarefa-{id}", "titulo": id, "concluida": "talvez"}
    return JSONResponse(status_code=status.HTTP_200_OK, content=corpo)


def criar_app(configuracao: Configuracao | None = None) -> FastAPI:
    """Cada instância tem o próprio repositório, carregado com a seed.

    O MODO_FALHA é lido uma vez, na subida: para trocar o modo, recrie a instância.
    """
    modo_falha = (configuracao or Configuracao()).modo_falha
    repositorio = RepositorioDeTarefas()
    app = FastAPI(title="API Alvo", version="0.1.0")

    # Nunca afetado pelo MODO_FALHA: é o healthcheck do Compose (ADR-008).
    @app.get("/saude")
    def saude() -> SaudeResposta:
        return SaudeResposta(status="ok")

    # response_model explícito: a spec é a mesma nos dois modos, só a resposta muda.
    @app.get("/tarefas", response_model=list[Tarefa])
    def listar_tarefas() -> list[Tarefa] | JSONResponse:
        if modo_falha:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Falha simulada pelo MODO_FALHA"},
            )
        return repositorio.listar()

    @app.get("/tarefas/{id}", response_model=Tarefa, responses=NAO_ENCONTRADA)
    def buscar_tarefa(id: int) -> Tarefa | JSONResponse:
        # Qualquer id, existente ou não, para a falha não cair em um 404 documentado.
        if modo_falha:
            return _tarefa_com_tipos_errados(id)
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
