from sqlalchemy import Engine, update
from sqlmodel import Session, col, select

from app.adapters.outbound.persistence.mapeamento import (
    estado_da_run,
    resultado_para_dominio,
    resultado_para_tabela,
    run_para_dominio,
    run_para_tabela,
)
from app.adapters.outbound.persistence.tabelas import ResultadoTesteTabela, RunTabela
from app.adapters.outbound.persistence.tabelas import StatusRun as StatusRunTabela
from app.application.portas import RunFinalizada, RunNaoEncontrada
from app.domain.resultado_teste import ResultadoDoTeste
from app.domain.run import Run
from app.domain.status_run import StatusRun, eh_final

# Status finais pela regra do domínio (RN-05), convertidos para o enum da tabela.
_STATUS_FINAIS = [StatusRunTabela(s.value) for s in StatusRun if eh_final(s)]


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

        O UPDATE só altera a linha se o status gravado ainda não for final (RN-05). A
        condição fica no próprio UPDATE, não em uma leitura anterior: duas gravações
        concorrentes (worker e varredura de tempo máximo, por exemplo) não conseguem as duas
        passar pela checagem. Se nenhuma linha for atualizada, nada é gravado e a exceção diz
        se a run não existe ou já terminou.

        Se qualquer INSERT falhar, nada é gravado: nem o status, nem os totais, nem os
        resultados.
        """
        if run.id is None:
            raise ValueError("salvar() exige uma run já adicionada (com id)")
        comando = (
            update(RunTabela)
            .where(col(RunTabela.id) == run.id, col(RunTabela.status).not_in(_STATUS_FINAIS))
            .values(**estado_da_run(run))
        )
        with Session(self._engine) as sessao:
            # connection(): mesma transação da sessão, e o retorno tipado expõe rowcount.
            if sessao.connection().execute(comando).rowcount == 0:
                if sessao.get(RunTabela, run.id) is None:
                    raise RunNaoEncontrada(f"Run {run.id} não existe")
                raise RunFinalizada(f"Run {run.id} já está em status final")
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
