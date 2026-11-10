from datetime import datetime

import pytest

from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado
from app.domain.run import Run
from app.domain.status_run import StatusRun, TransicaoInvalida

FIM = datetime(2026, 11, 10, 12, 10)
OK = ResultadoDoTeste("/tarefas", "GET", StatusResultado.PASSOU, 10, None)
ERRO = ResultadoDoTeste("/tarefas", "POST", StatusResultado.FALHOU, 10, "erro A")
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


@pytest.mark.unit
def test_us05_c2_finalizar_com_todos_passando_resulta_em_passou() -> None:
    run = Run(1, 42, CRIADO)
    run.iniciar(AGORA)

    run.finalizar(FIM, [OK, OK])

    assert run.status == StatusRun.PASSOU


@pytest.mark.unit
def test_us05_c1_finalizar_registra_fim() -> None:
    run = Run(1, 42, CRIADO)
    run.iniciar(AGORA)

    run.finalizar(FIM, [OK])

    assert run.fim == FIM


@pytest.mark.unit
def test_us05_c3_finalizar_grava_totais() -> None:
    run = Run(1, 42, CRIADO)
    run.iniciar(AGORA)

    run.finalizar(FIM, [OK, OK, ERRO])

    assert run.total_passou == 2
    assert run.total_falhou == 1


@pytest.mark.unit
def test_rn05_t1_run_finalizada_nao_finaliza_de_novo() -> None:
    run = Run(1, 42, CRIADO)
    run.iniciar(AGORA)
    run.finalizar(FIM, [OK])

    with pytest.raises(TransicaoInvalida):
        run.finalizar(FIM, [OK])


@pytest.mark.unit
def test_rn11_t1_run_na_fila_nao_finaliza() -> None:
    run = Run(1, 42, CRIADO)
    with pytest.raises(TransicaoInvalida):
        run.finalizar(FIM, [OK])


@pytest.mark.unit
def test_us04_c5_falhar_resulta_em_falhou_com_motivo() -> None:
    run = Run(1, 42, CRIADO)
    run.iniciar(AGORA)

    run.falhar(FIM, "spec inválida")
    assert run.status == StatusRun.FALHOU
    assert run.mensagem_erro == "spec inválida"


@pytest.mark.unit
def test_us05_c1_interromper_registra_fim() -> None:
    run = Run(1, 42, CRIADO)
    run.iniciar(AGORA)

    run.interromper(FIM, "tempo excedido")
    assert run.fim == FIM


@pytest.mark.unit
def test_rn12_t3_interromper_resulta_em_interrompida() -> None:
    run = Run(1, 42, CRIADO)
    run.iniciar(AGORA)

    run.interromper(FIM, "erro interno")
    assert run.status == StatusRun.INTERROMPIDA
