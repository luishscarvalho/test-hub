from dataclasses import replace

from sqlalchemy import Engine
from sqlmodel import Session

from app.adapters.outbound.persistence.mapeamento import (
    api_para_dominio,
    api_para_tabela,
    spec_para_tabela,
)
from app.adapters.outbound.persistence.tabelas import ApiAlvoTabela
from app.domain.api_alvo import ApiAlvo
from app.domain.spec_versao import SpecVersao


class RepositorioDeApisSQL:
    """Implementa a porta RepositorioDeApis. Cada método abre e confirma a própria sessão."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def adicionar(self, api: ApiAlvo, spec: SpecVersao) -> ApiAlvo:
        """Grava a API e a primeira versão da spec em uma única transação (US-02).

        Se a gravação da spec falhar, a API também não fica gravada. O api_alvo_id da spec
        recebida é ignorado: a API ainda não tem id, então ele vem do INSERT da API.
        """
        with Session(self._engine) as sessao:
            linha_api = api_para_tabela(api)
            sessao.add(linha_api)
            # flush envia o INSERT da API sem confirmar, para obter o id gerado pelo banco.
            sessao.flush()
            if linha_api.id is None:
                raise RuntimeError("INSERT da API não devolveu id")
            sessao.add(spec_para_tabela(replace(spec, api_alvo_id=linha_api.id)))
            sessao.commit()
            sessao.refresh(linha_api)
            return api_para_dominio(linha_api)

    def buscar(self, id: int) -> ApiAlvo | None:
        with Session(self._engine) as sessao:
            linha = sessao.get(ApiAlvoTabela, id)
            return None if linha is None else api_para_dominio(linha)
