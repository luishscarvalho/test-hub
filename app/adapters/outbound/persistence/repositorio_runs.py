from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.adapters.outbound.persistence.mapeamento import (
    copiar_estado_da_run,
    resultado_para_dominio,
    resultado_para_tabela,
    run_para_dominio,
    run_para_tabela,
)
from app.adapters.outbound.persistence.tabelas import ResultadoTesteTabela, RunTabela
from app.adapters.outbound.persistence.tabelas import StatusRun as StatusRunTabela
from app.domain.resultado_teste import ResultadoDoTeste
from app.domain.run import Run


class RunNaoEncontrada(LookupError):
    """salvar() ou remover() chamados para uma run que não existe no banco."""


class RepositorioDeRunsSQL:
    """Implementa a porta RepositorioDeRuns. Cada método abre e confirma a própria sessão."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def adicionar(self, run: Run) -> Run:
        with Session(self._engine) as sessao:
            linha = run_para_tabela(run)
            sessao.add(linha)
            sessao.commit()
            sessao.refresh(linha)
            return run_para_dominio(linha)

    def buscar(self, id: int) -> Run | None:
        with Session(self._engine) as sessao:
            linha = sessao.get(RunTabela, id)
            return None if linha is None else run_para_dominio(linha)

    def remover(self, id: int) -> None:
        with Session(self._engine) as sessao:
            linha = sessao.get(RunTabela, id)
            if linha is None:
                raise RunNaoEncontrada(f"Run {id} não existe")
            sessao.delete(linha)
            sessao.commit()

    def salvar(self, run: Run, resultados: list[ResultadoDoTeste]) -> None:
        """Grava o estado da run e os resultados em uma única transação (RN-15).

        Se qualquer INSERT falhar, nada é gravado: nem o status, nem os totais, nem os
        resultados.
        """
        if run.id is None:
            raise ValueError("salvar() exige uma run já adicionada (com id)")
        with Session(self._engine) as sessao:
            linha = sessao.get(RunTabela, run.id)
            if linha is None:
                raise RunNaoEncontrada(f"Run {run.id} não existe")
            copiar_estado_da_run(run, linha)
            sessao.add(linha)
            sessao.add_all(resultado_para_tabela(run.id, r) for r in resultados)
            sessao.commit()

    def listar_por_api(self, api_alvo_id: int) -> list[Run]:
        # Mais recente primeiro (US-07). id desempata runs criadas no mesmo instante.
        consulta = (
            select(RunTabela)
            .where(RunTabela.api_alvo_id == api_alvo_id)
            .order_by(col(RunTabela.criado_em).desc(), col(RunTabela.id).desc())
        )
        with Session(self._engine) as sessao:
            return [run_para_dominio(linha) for linha in sessao.exec(consulta)]

    def buscar_resultados(self, run_id: int) -> list[ResultadoDoTeste]:
        consulta = (
            select(ResultadoTesteTabela)
            .where(ResultadoTesteTabela.run_id == run_id)
            .order_by(col(ResultadoTesteTabela.id))
        )
        with Session(self._engine) as sessao:
            return [resultado_para_dominio(linha) for linha in sessao.exec(consulta)]

    def listar_em_execucao(self) -> list[Run]:
        consulta = (
            select(RunTabela)
            .where(RunTabela.status == StatusRunTabela.EM_EXECUCAO)
            .order_by(col(RunTabela.id))
        )
        with Session(self._engine) as sessao:
            return [run_para_dominio(linha) for linha in sessao.exec(consulta)]
