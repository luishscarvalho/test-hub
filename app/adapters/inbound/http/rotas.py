"""Rotas do contrato da ERS 10.3. Sem regra de negócio: traduzem HTTP para os casos de uso."""

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.adapters.inbound.http.dtos import (
    ApiCriada,
    DisparoDeRun,
    Erro,
    RunDetalhe,
    RunDisparada,
    RunResumo,
)
from app.application.cadastrar_api import CadastrarApi
from app.application.consultar_runs import ConsultarRun, ListarRuns
from app.application.disparar_run import DispararRun
from app.application.portas import (
    ApiNaoEncontrada,
    CadastroInvalido,
    FilaIndisponivel,
    RunNaoEncontrada,
    SpecInvalida,
)


@dataclass(frozen=True)
class CasosDeUsoHttp:
    cadastrar_api: CadastrarApi
    disparar_run: DispararRun
    listar_runs: ListarRuns
    consultar_run: ConsultarRun


def _erro(codigo: int, descricao: str) -> dict[int | str, dict[str, Any]]:
    return {codigo: {"model": Erro, "description": descricao}}


def criar_router(casos: CasosDeUsoHttp) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/apis",
        status_code=status.HTTP_201_CREATED,
        tags=["apis"],
        responses=_erro(422, "Campo faltante, ou spec inválida ou inacessível"),
    )
    def cadastrar_api(
        nome: Annotated[str, Form(min_length=1)],
        base_url: Annotated[str, Form(min_length=1)],
        spec_url: Annotated[str | None, Form()] = None,
        spec_arquivo: Annotated[UploadFile | None, File()] = None,
    ) -> ApiCriada:
        try:
            api = casos.cadastrar_api.executar(
                nome=nome,
                base_url=base_url,
                spec_url=spec_url,
                spec_arquivo=None if spec_arquivo is None else spec_arquivo.file.read(),
            )
        except (CadastroInvalido, SpecInvalida) as erro:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(erro)) from erro
        # API devolvida pelo repositório sempre tem id.
        assert api.id is not None
        return ApiCriada(id=api.id)

    @router.post(
        "/runs",
        status_code=status.HTTP_202_ACCEPTED,
        tags=["runs"],
        responses={**_erro(404, "API inexistente"), **_erro(503, "Fila indisponível")},
    )
    def disparar_run(disparo: DisparoDeRun) -> RunDisparada:
        try:
            run = casos.disparar_run.executar(disparo.api_alvo_id)
        except ApiNaoEncontrada as erro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(erro)) from erro
        except FilaIndisponivel as erro:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(erro)) from erro
        assert run.id is not None
        return RunDisparada(id=run.id, status=run.status)

    @router.get("/apis/{id}/runs", tags=["runs"], responses=_erro(404, "API inexistente"))
    def listar_runs(id: int) -> list[RunResumo]:
        try:
            resumos = casos.listar_runs.executar(id)
        except ApiNaoEncontrada as erro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(erro)) from erro
        return [RunResumo.de(resumo) for resumo in resumos]

    @router.get("/runs/{id}", tags=["runs"], responses=_erro(404, "Run inexistente"))
    def consultar_run(id: int) -> RunDetalhe:
        try:
            detalhe = casos.consultar_run.executar(id)
        except RunNaoEncontrada as erro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(erro)) from erro
        return RunDetalhe.do_detalhe(detalhe)

    return router
