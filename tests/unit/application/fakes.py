"""Adapters falsos, em memória, para as portas da aplicação (Plano de Testes, 2.1).

Os repositórios guardam cópias: o caso de uso só vê o que gravou se gravar de novo, como
no banco. Sem isso, um teste passaria mesmo com o caso de uso esquecendo de salvar.
"""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta

from app.application.portas import (
    FilaIndisponivel,
    RunFinalizada,
    RunNaoEncontrada,
    SpecInvalida,
)
from app.domain.api_alvo import ApiAlvo
from app.domain.resultado_teste import ResultadoDoTeste
from app.domain.run import Run
from app.domain.spec_versao import SpecVersao
from app.domain.status_run import StatusRun, eh_final

INICIO_DO_RELOGIO = datetime(2026, 11, 11, 12, 0)


class RelogioFalso:
    """Avança um segundo a cada leitura, para distinguir início e fim nos testes."""

    def __init__(self, inicio: datetime = INICIO_DO_RELOGIO) -> None:
        self._agora = inicio
        self.leituras: list[datetime] = []

    def __call__(self) -> datetime:
        self._agora += timedelta(seconds=1)
        self.leituras.append(self._agora)
        return self._agora


class RepositorioDeApisFalso:
    def __init__(self) -> None:
        self.apis: dict[int, ApiAlvo] = {}
        self.specs_do_cadastro: dict[int, SpecVersao] = {}

    def adicionar(self, api: ApiAlvo, spec: SpecVersao) -> ApiAlvo:
        novo_id = len(self.apis) + 1
        self.apis[novo_id] = replace(api, id=novo_id)
        self.specs_do_cadastro[novo_id] = replace(spec, api_alvo_id=novo_id)
        return deepcopy(self.apis[novo_id])

    def buscar(self, id: int) -> ApiAlvo | None:
        return deepcopy(self.apis.get(id))


class RepositorioDeSpecsFalso:
    def __init__(self) -> None:
        self.specs: list[SpecVersao] = []

    def adicionar(self, spec: SpecVersao) -> SpecVersao:
        gravada = replace(spec, id=100 + len(self.specs))
        self.specs.append(gravada)
        return gravada

    def buscar_por_hash(self, api_alvo_id: int, hash: str) -> SpecVersao | None:
        for spec in self.specs:
            if spec.api_alvo_id == api_alvo_id and spec.hash == hash:
                return spec
        return None

    def buscar_mais_recente(self, api_alvo_id: int) -> SpecVersao | None:
        da_api = [s for s in self.specs if s.api_alvo_id == api_alvo_id]
        return max(da_api, key=lambda s: (s.criado_em, s.id or 0), default=None)


class RepositorioDeRunsFalso:
    """Imita o repositório SQL: salvar recusa run já final no armazenamento (RN-05)."""

    def __init__(self) -> None:
        self.runs: dict[int, Run] = {}
        self.resultados: dict[int, list[ResultadoDoTeste]] = {}
        # Cópia da run a cada salvar, na ordem das chamadas.
        self.gravacoes: list[tuple[Run, list[ResultadoDoTeste]]] = []

    def adicionar(self, run: Run) -> Run:
        novo_id = len(self.runs) + 1
        self.runs[novo_id] = replace(run, id=novo_id)
        return deepcopy(self.runs[novo_id])

    def buscar(self, id: int) -> Run | None:
        return deepcopy(self.runs.get(id))

    def remover(self, id: int) -> None:
        if id not in self.runs:
            raise RunNaoEncontrada(f"Run {id} não existe")
        del self.runs[id]

    def salvar(self, run: Run, resultados: list[ResultadoDoTeste]) -> None:
        assert run.id is not None
        if run.id not in self.runs:
            raise RunNaoEncontrada(f"Run {run.id} não existe")
        if eh_final(self.runs[run.id].status):
            raise RunFinalizada(f"Run {run.id} já está em status final")
        self.runs[run.id] = deepcopy(run)
        self.resultados.setdefault(run.id, []).extend(resultados)
        self.gravacoes.append((deepcopy(run), list(resultados)))

    def listar_por_api(self, api_alvo_id: int) -> list[Run]:
        da_api = [r for r in self.runs.values() if r.api_alvo_id == api_alvo_id]
        return deepcopy(sorted(da_api, key=lambda r: (r.criado_em, r.id or 0), reverse=True))

    def buscar_resultados(self, run_id: int) -> list[ResultadoDoTeste]:
        return list(self.resultados.get(run_id, []))

    def listar_em_execucao(self) -> list[Run]:
        return deepcopy([r for r in self.runs.values() if r.status == StatusRun.EM_EXECUCAO])


class CarregadorDeSpecFalso:
    """baixar devolve a spec registrada para a URL, ou SpecInvalida com o motivo registrado."""

    def __init__(self) -> None:
        self.por_url: dict[str, dict[str, object] | SpecInvalida] = {}
        self.por_arquivo: dict[bytes, dict[str, object] | SpecInvalida] = {}
        self.urls_baixadas: list[str] = []

    def baixar(self, url: str) -> dict[str, object]:
        self.urls_baixadas.append(url)
        return _devolver(self.por_url[url])

    def ler(self, conteudo: bytes) -> dict[str, object]:
        return _devolver(self.por_arquivo[conteudo])


def _devolver(registro: dict[str, object] | SpecInvalida) -> dict[str, object]:
    if isinstance(registro, SpecInvalida):
        raise registro
    return deepcopy(registro)


class GeradorDeTestesFalso:
    def __init__(self, resultados: list[ResultadoDoTeste] | Exception | None = None) -> None:
        self.resposta: list[ResultadoDoTeste] | Exception = resultados or []
        self.chamadas: list[tuple[dict[str, object], str, int]] = []

    def gerar_e_executar(
        self, spec: dict[str, object], base_url: str, seed: int
    ) -> list[ResultadoDoTeste]:
        self.chamadas.append((spec, base_url, seed))
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return list(self.resposta)


class ExecutorDeRunFalso:
    def __init__(self, *, indisponivel: bool = False) -> None:
        self.indisponivel = indisponivel
        self.enfileiradas: list[int] = []

    def enfileirar(self, run_id: int) -> None:
        if self.indisponivel:
            raise FilaIndisponivel("Redis fora do ar")
        self.enfileiradas.append(run_id)
