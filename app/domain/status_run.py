from enum import StrEnum


class StatusRun(StrEnum):
    NA_FILA = "na_fila"
    EM_EXECUCAO = "em_execucao"
    PASSOU = "passou"
    FALHOU = "falhou"
    INTERROMPIDA = "interrompida"


_DESTINOS: dict[StatusRun, frozenset[StatusRun]] = {
    StatusRun.NA_FILA: frozenset({StatusRun.EM_EXECUCAO}),
    StatusRun.EM_EXECUCAO: frozenset({StatusRun.PASSOU, StatusRun.FALHOU, StatusRun.INTERROMPIDA}),
    StatusRun.PASSOU: frozenset(),
    StatusRun.FALHOU: frozenset(),
    StatusRun.INTERROMPIDA: frozenset(),
}


class TransicaoInvalida(Exception):
    pass


def transicionar(atual: StatusRun, novo: StatusRun) -> StatusRun:
    if novo not in _DESTINOS[atual]:
        raise TransicaoInvalida(f"{atual} -> {novo}")
    return novo


def eh_final(status: StatusRun) -> bool:
    return not _DESTINOS[status]
