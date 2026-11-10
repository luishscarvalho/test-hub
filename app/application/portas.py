from typing import Protocol

from app.domain.api_alvo import ApiAlvo
from app.domain.resultado_teste import ResultadoDoTeste
from app.domain.run import Run
from app.domain.spec_versao import SpecVersao


class SpecInvalida(Exception):
    """Spec não baixou ou não é OpenAPI válida (RN-02)."""


class FilaIndisponivel(Exception):
    """Execução não pôde ser enfileirada (RN-16)."""


class RepositorioDeApis(Protocol):
    def adicionar(self, api: ApiAlvo, spec: SpecVersao) -> ApiAlvo: ...
    def buscar(self, id: int) -> ApiAlvo | None: ...


class RepositorioDeSpecs(Protocol):
    def adicionar(self, spec: SpecVersao) -> SpecVersao: ...
    def buscar_por_hash(self, api_alvo_id: int, hash: str) -> SpecVersao | None: ...
    def buscar_mais_recente(self, api_alvo_id: int) -> SpecVersao | None: ...


class RepositorioDeRuns(Protocol):
    def adicionar(self, run: Run) -> Run: ...
    def buscar(self, id: int) -> Run | None: ...
    def remover(self, id: int) -> None: ...
    def salvar(self, run: Run, resultados: list[ResultadoDoTeste]) -> None: ...
    def listar_por_api(self, api_alvo_id: int) -> list[Run]: ...
    def buscar_resultados(self, run_id: int) -> list[ResultadoDoTeste]: ...
    def listar_em_execucao(self) -> list[Run]: ...


class CarregadorDeSpec(Protocol):
    def baixar(self, url: str) -> dict[str, object]: ...
    def ler(self, conteudo: bytes) -> dict[str, object]: ...


class GeradorDeTestes(Protocol):
    def gerar_e_executar(
        self, spec: dict[str, object], base_url: str, seed: int
    ) -> list[ResultadoDoTeste]: ...


class ExecutorDeRun(Protocol):
    def enfileirar(self, run_id: int) -> None: ...


class RunFinalizada(Exception):
    """Run em status final não pode ser alterada (RN-05)."""


class RunNaoEncontrada(Exception):
    """Run em status final não pode ser alterada (RN-05)."""
