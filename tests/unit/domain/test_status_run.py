import pytest

from app.domain.status_run import StatusRun, TransicaoInvalida, eh_final, transicionar


@pytest.mark.unit
def test_us05_c4_run_na_fila_vai_para_em_execucao() -> None:
    assert transicionar(StatusRun.NA_FILA, StatusRun.EM_EXECUCAO) == StatusRun.EM_EXECUCAO


@pytest.mark.unit
def test_rn05_t1_run_passou_nao_volta_para_em_execucao() -> None:
    with pytest.raises(TransicaoInvalida):
        transicionar(StatusRun.PASSOU, StatusRun.EM_EXECUCAO)


@pytest.mark.unit
@pytest.mark.parametrize("status", [StatusRun.PASSOU, StatusRun.FALHOU, StatusRun.INTERROMPIDA])
def test_rn05_t1_status_finais_sao_finais(status: StatusRun) -> None:
    assert eh_final(status) is True


@pytest.mark.unit
@pytest.mark.parametrize("status", [StatusRun.NA_FILA, StatusRun.EM_EXECUCAO])
def test_rn05_t1_status_intermediarios_nao_sao_finais(status: StatusRun) -> None:
    assert eh_final(status) is False
