import pytest

from app.domain.status_run import StatusRun, TransicaoInvalida, transicionar


@pytest.mark.unit
def test_us05_c4_run_na_fila_vai_para_em_execucao() -> None:
    assert transicionar(StatusRun.NA_FILA, StatusRun.EM_EXECUCAO) == StatusRun.EM_EXECUCAO


@pytest.mark.unit
def test_rn05_t1_run_passou_nao_volta_para_em_execucao() -> None:
    with pytest.raises(TransicaoInvalida):
        transicionar(StatusRun.PASSOU, StatusRun.EM_EXECUCAO)
