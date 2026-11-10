from datetime import datetime

import pytest

from app.domain.run import Run
from app.domain.status_run import StatusRun, TransicaoInvalida

# horários fixos: o teste dá sempre o mesmo resultado
CRIADO = datetime(2026, 11, 10, 12, 0)
AGORA = datetime(2026, 11, 10, 12, 5)


@pytest.mark.unit
def test_us05_c4_iniciar_muda_para_em_execucao() -> None:
    run = Run(1, 42, CRIADO)

    run.iniciar(AGORA)

    assert run.status == StatusRun.EM_EXECUCAO


@pytest.mark.unit
def test_us05_c1_iniciar_registra_inicio() -> None:
    run = Run(1, 42, CRIADO)

    run.iniciar(AGORA)

    assert run.inicio == AGORA


@pytest.mark.unit
def test_rn11_t1_run_ja_iniciada_nao_inicia_de_novo() -> None:
    run = Run(1, 42, CRIADO)

    run.iniciar(AGORA)

    with pytest.raises(TransicaoInvalida):
        run.iniciar(AGORA)
