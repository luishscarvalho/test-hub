"""Gerador de smoke tests com a API Python do Schemathesis (porta GeradorDeTestes, ADR-005).

Para cada operação da spec: gera os casos com seed fixa, executa cada caso contra a base URL,
valida só status e schema da resposta (RN-04) e consolida com consolidar_casos do domínio.

A geração termina antes da execução: os casos não dependem das respostas, então a mesma
spec e a mesma seed produzem as mesmas requisições, com a API alvo de pé ou não (RN-14).
"""

import time

import requests
import schemathesis
from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import seed as semente
from hypothesis.errors import Unsatisfiable
from schemathesis import APIOperation, Case
from schemathesis.core.failures import Failure, FailureGroup
from schemathesis.core.result import Err
from schemathesis.specs.openapi.checks import (
    response_schema_conformance,
    status_code_conformance,
)

from app.domain.resultado_teste import CasoDeTeste, ResultadoDoTeste, consolidar_casos

# Lista explícita: substitui o conjunto padrão de checagens do Schemathesis (RN-04).
CHECAGENS = [status_code_conformance, response_schema_conformance]


class GeradorSchemathesis:
    def __init__(self, *, limite_de_casos: int, timeout_s: float) -> None:
        """limite_de_casos: máximo de casos gerados por operação (ADR-005).

        timeout_s: tempo máximo de cada requisição à API alvo. Esgotado, o caso falha.
        """
        self._limite_de_casos = limite_de_casos
        self._timeout_s = timeout_s

    def gerar_e_executar(
        self, spec: dict[str, object], base_url: str, seed: int
    ) -> list[ResultadoDoTeste]:
        esquema = schemathesis.openapi.from_dict(spec)
        resultados = []
        for item in esquema.get_all_operations():
            if isinstance(item, Err):
                # Operação que o Schemathesis não consegue interpretar (ex.: $ref quebrado).
                raise item.err()
            operacao = item.ok()
            casos = [self._executar(caso, base_url) for caso in self._gerar(operacao, seed)]
            resultados.append(consolidar_casos(operacao.path, operacao.method.upper(), casos))
        return resultados

    def _gerar(self, operacao: APIOperation, seed: int) -> list[Case]:
        casos: list[Case] = []

        # database=None: o Hypothesis não reaproveita exemplos de execuções anteriores.
        # Phase.generate: só casos gerados, sem a fase de redução (shrink) de falhas.
        @semente(seed)
        @settings(
            max_examples=self._limite_de_casos,
            database=None,
            deadline=None,
            phases=[Phase.generate],
            suppress_health_check=list(HealthCheck),
        )
        @given(caso=operacao.as_strategy())
        def coletar(caso: Case) -> None:
            casos.append(caso)

        try:
            coletar()
        except Unsatisfiable:
            # Nenhum caso gerado: consolidar_casos registra a operação como falhou (RN-03).
            pass
        return casos

    def _executar(self, caso: Case, base_url: str) -> CasoDeTeste:
        inicio = time.perf_counter()
        try:
            resposta = caso.call(base_url=base_url, timeout=self._timeout_s)
        except requests.RequestException as erro:
            # API alvo inacessível ou tempo esgotado: o caso falha (RN-03, ADR-005).
            return CasoDeTeste(False, _ms_desde(inicio), f"Erro ao chamar a API alvo: {erro}")
        duracao_ms = _ms_desde(inicio)
        try:
            caso.validate_response(resposta, checks=CHECAGENS)
        except FailureGroup as falhas:
            requisicao = f"{caso.method.upper()} {caso.formatted_path}"
            return CasoDeTeste(
                False,
                duracao_ms,
                f"{requisicao} respondeu {resposta.status_code}. {_mensagem(falhas)}",
            )
        return CasoDeTeste(True, duracao_ms)


def _ms_desde(inicio: float) -> int:
    return round((time.perf_counter() - inicio) * 1000)


def _mensagem(falhas: FailureGroup) -> str:
    """Resumo de cada falha, em ordem estável.

    O Schemathesis junta as falhas em um set, então a ordem original varia entre execuções.
    """
    return "; ".join(sorted({_resumo(falha) for falha in falhas.exceptions}))


def _resumo(falha: Failure) -> str:
    # O primeiro parágrafo diz o que falhou. O resto repete o schema e o valor recebido.
    primeiro_paragrafo = falha.message.split("\n\n")[0].replace("\n", ", ")
    return f"{falha.title}: {primeiro_paragrafo}"
