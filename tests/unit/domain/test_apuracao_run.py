import pytest

from app.domain.apuracao_run import apurar_resultados
from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado
from app.domain.status_run import StatusRun

PASSOU = ResultadoDoTeste("/tarefas", "GET", StatusResultado.PASSOU, 10, None)
FALHOU = ResultadoDoTeste("/tarefas", "POST", StatusResultado.FALHOU, 10, "erro A")


@pytest.mark.unit
def test_us05_c2_todos_passando_resulta_em_passou() -> None:
    apuracao = apurar_resultados([PASSOU, PASSOU])

    assert apuracao.status == StatusRun.PASSOU


@pytest.mark.unit
def test_us05_c2_um_falhando_resulta_em_falhou() -> None:
    apuracao = apurar_resultados([PASSOU, FALHOU])

    assert apuracao.status == StatusRun.FALHOU


@pytest.mark.unit
def test_us05_c2_sem_resultados_nao_resulta_em_passou() -> None:
    apuracao = apurar_resultados([])

    assert apuracao.status == StatusRun.FALHOU


@pytest.mark.unit
def test_us05_c3_totais_conferem_com_os_resultados() -> None:
    apuracao = apurar_resultados([PASSOU, PASSOU, FALHOU])

    assert apuracao.total_passou == 2
    assert apuracao.total_falhou == 1
