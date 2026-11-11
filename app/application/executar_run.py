"""Execução da run pelo worker (US-04, US-05, RN-06, RN-11, RN-13, RN-15, ADR-006, ADR-007).

Erro inesperado não é tratado aqui: ele sobe para a entrada do worker, que marca a run
como interrompida pelo caso de uso InterromperRun (RN-12c). Assim, o mesmo caminho trata
erro interno e tempo máximo excedido, que o RQ também entrega como exceção.
"""

from app.application.portas import (
    ApiNaoEncontrada,
    CarregadorDeSpec,
    GeradorDeTestes,
    Relogio,
    RepositorioDeApis,
    RepositorioDeRuns,
    RepositorioDeSpecs,
    RunNaoEncontrada,
    SpecInvalida,
)
from app.application.spec_normalizada import calcular_hash
from app.domain.api_alvo import ApiAlvo
from app.domain.run import Run
from app.domain.spec_versao import OrigemSpec, SpecVersao


class SpecDoCadastroAusente(Exception):
    """API cadastrada por arquivo sem nenhuma versão de spec. O cadastro impede (RN-01)."""


class ExecutarRun:
    def __init__(
        self,
        *,
        apis: RepositorioDeApis,
        specs: RepositorioDeSpecs,
        runs: RepositorioDeRuns,
        carregador: CarregadorDeSpec,
        gerador: GeradorDeTestes,
        relogio: Relogio,
    ) -> None:
        self._apis = apis
        self._specs = specs
        self._runs = runs
        self._carregador = carregador
        self._gerador = gerador
        self._relogio = relogio

    def executar(self, run_id: int) -> None:
        run = self._runs.buscar(run_id)
        if run is None:
            raise RunNaoEncontrada(f"Run {run_id} não existe")

        # Gravado antes de tudo: se o worker cair daqui em diante, a recuperação na
        # subida encontra a run em em_execucao (RN-12a).
        run.iniciar(self._relogio())
        self._runs.salvar(run, [])

        api = self._apis.buscar(run.api_alvo_id)
        if api is None:
            raise ApiNaoEncontrada(f"API alvo {run.api_alvo_id} da run {run_id} não existe")

        try:
            spec = self._resolver_spec(api)
            resultados = self._gerador.gerar_e_executar(spec.conteudo, api.base_url, run.seed)
        except SpecInvalida as erro:
            # Spec inacessível ou inválida: falhou, sem resultados e sem versão (RN-06, RN-13).
            self._falhar(run, str(erro))
            return

        run.spec_versao_id = spec.id
        run.finalizar(self._relogio(), resultados)
        # Status, totais e resultados na mesma gravação (RN-15).
        self._runs.salvar(run, resultados)

    def _resolver_spec(self, api: ApiAlvo) -> SpecVersao:
        """Versão da spec usada pela run (RN-13).

        Por URL: baixa e valida de novo (US02-C5), reusa a versão se o hash já existe e
        cria uma nova se não existe. Por arquivo: usa a versão mais recente.
        """
        # API lida do repositório sempre tem id.
        assert api.id is not None
        if api.spec_url is None:
            spec = self._specs.buscar_mais_recente(api.id)
            if spec is None:
                raise SpecDoCadastroAusente(f"API alvo {api.id} não tem versão de spec")
            return spec

        conteudo = self._carregador.baixar(api.spec_url)
        hash_da_spec = calcular_hash(conteudo)
        existente = self._specs.buscar_por_hash(api.id, hash_da_spec)
        if existente is not None:
            return existente
        nova = SpecVersao(api.id, conteudo, hash_da_spec, OrigemSpec.URL, self._relogio())
        return self._specs.adicionar(nova)

    def _falhar(self, run: Run, motivo: str) -> None:
        run.falhar(self._relogio(), motivo)
        self._runs.salvar(run, [])
