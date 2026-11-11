"""Disparo de run: grava na fila e enfileira a execução (US-04, RN-14, RN-16, ADR-006)."""

from app.application.portas import (
    ApiNaoEncontrada,
    ExecutorDeRun,
    FilaIndisponivel,
    Relogio,
    RepositorioDeApis,
    RepositorioDeRuns,
)
from app.domain.run import Run


class DispararRun:
    def __init__(
        self,
        *,
        apis: RepositorioDeApis,
        runs: RepositorioDeRuns,
        executor: ExecutorDeRun,
        relogio: Relogio,
        seed: int,
    ) -> None:
        """seed: semente configurada do gerador. Cada run registra a que recebeu (RN-14)."""
        self._apis = apis
        self._runs = runs
        self._executor = executor
        self._relogio = relogio
        self._seed = seed

    def executar(self, api_alvo_id: int) -> Run:
        """Devolve a run em na_fila, sem esperar a execução (US04-C4).

        A run é confirmada antes de enfileirar, porque o worker roda em outro processo e
        precisa encontrá-la no banco. Se a fila estiver indisponível, a run é removida e
        FilaIndisponivel sobe para a rota responder 503 (RN-16).
        """
        if self._apis.buscar(api_alvo_id) is None:
            raise ApiNaoEncontrada(f"API alvo {api_alvo_id} não existe")

        run = self._runs.adicionar(Run(api_alvo_id, self._seed, self._relogio()))
        # adicionar devolve a run com o id gerado pelo banco (porta RepositorioDeRuns).
        assert run.id is not None
        try:
            self._executor.enfileirar(run.id)
        except FilaIndisponivel:
            self._runs.remover(run.id)
            raise
        return run
