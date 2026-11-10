from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.adapters.outbound.persistence.mapeamento import spec_para_dominio, spec_para_tabela
from app.adapters.outbound.persistence.tabelas import SpecVersaoTabela
from app.domain.spec_versao import SpecVersao


class RepositorioDeSpecsSQL:
    """Implementa a porta RepositorioDeSpecs.

    Não há método de alteração nem de remoção: versões são imutáveis (ADR-007). A unicidade
    de (api_alvo_id, hash) é garantida pela restrição uq_spec_versao_api_hash do banco.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def adicionar(self, spec: SpecVersao) -> SpecVersao:
        with Session(self._engine) as sessao:
            linha = spec_para_tabela(spec)
            sessao.add(linha)
            sessao.commit()
            sessao.refresh(linha)
            return spec_para_dominio(linha)

    def buscar_por_hash(self, api_alvo_id: int, hash: str) -> SpecVersao | None:
        consulta = select(SpecVersaoTabela).where(
            SpecVersaoTabela.api_alvo_id == api_alvo_id, SpecVersaoTabela.hash == hash
        )
        with Session(self._engine) as sessao:
            linha = sessao.exec(consulta).first()
            return None if linha is None else spec_para_dominio(linha)

    def buscar_mais_recente(self, api_alvo_id: int) -> SpecVersao | None:
        # id desempata versões criadas no mesmo instante.
        consulta = (
            select(SpecVersaoTabela)
            .where(SpecVersaoTabela.api_alvo_id == api_alvo_id)
            .order_by(col(SpecVersaoTabela.criado_em).desc(), col(SpecVersaoTabela.id).desc())
            .limit(1)
        )
        with Session(self._engine) as sessao:
            linha = sessao.exec(consulta).first()
            return None if linha is None else spec_para_dominio(linha)
