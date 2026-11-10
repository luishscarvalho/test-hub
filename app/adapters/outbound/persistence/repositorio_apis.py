from sqlalchemy import Engine
from sqlmodel import Session

from app.adapters.outbound.persistence.mapeamento import api_para_dominio, api_para_tabela
from app.adapters.outbound.persistence.tabelas import ApiAlvoTabela
from app.domain.api_alvo import ApiAlvo


class RepositorioDeApisSQL:
    """Implementa a porta RepositorioDeApis. Cada método abre e confirma a própria sessão."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def adicionar(self, api: ApiAlvo) -> ApiAlvo:
        with Session(self._engine) as sessao:
            linha = api_para_tabela(api)
            sessao.add(linha)
            sessao.commit()
            sessao.refresh(linha)
            return api_para_dominio(linha)

    def buscar(self, id: int) -> ApiAlvo | None:
        with Session(self._engine) as sessao:
            linha = sessao.get(ApiAlvoTabela, id)
            return None if linha is None else api_para_dominio(linha)
