from dataclasses import dataclass
from enum import StrEnum


class StatusResultado(StrEnum):
    PASSOU = "passou"
    FALHOU = "falhou"


@dataclass(frozen=True)
class CasoDeTeste:
    passou: bool
    duracao_ms: int
    mensagem_erro: str | None = None


@dataclass(frozen=True)
class ResultadoDoTeste:
    endpoint: str
    metodo: str
    status: StatusResultado
    duracao_ms: int
    mensagem_erro: str | None


MENSAGEM_FALHA_SEM_DETALHE = "Caso de teste falhou sem mensagem de erro"


def consolidar_casos(endpoint: str, metodo: str, casos: list[CasoDeTeste]) -> ResultadoDoTeste:
    duracao_total = 0
    todos_passaram = True
    primeira_mensagem: str | None = None

    if not casos:  # RN03 T2: sem casos, resulta em falhou
        return ResultadoDoTeste(
            endpoint,
            metodo,
            StatusResultado.FALHOU,
            0,
            "Nenhum caso de teste executado",
        )

    for caso in casos:
        duracao_total += caso.duracao_ms
        if not caso.passou and todos_passaram:
            todos_passaram = False
            primeira_mensagem = caso.mensagem_erro
            if primeira_mensagem is None or not primeira_mensagem.strip():
                # US06 C2: teste que falhou sempre traz mensagem de erro
                primeira_mensagem = MENSAGEM_FALHA_SEM_DETALHE

    status = StatusResultado.PASSOU if todos_passaram else StatusResultado.FALHOU
    return ResultadoDoTeste(endpoint, metodo, status, duracao_total, primeira_mensagem)
