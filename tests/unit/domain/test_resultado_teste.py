import pytest

from app.domain.resultado_teste import CasoDeTeste, StatusResultado, consolidar_casos


@pytest.mark.unit
def test_us03_c1_todos_passando_resulta_em_passou() -> None:
    # monta a entrada: dois casos que passaram (passou, duracao_ms)
    casos = [CasoDeTeste(True, 10), CasoDeTeste(True, 20)]

    # executa a função: endpoint, método e a lista de casos
    resultado = consolidar_casos("/tarefas", "GET", casos)

    # confere o campo status do resultado
    assert resultado.status == StatusResultado.PASSOU


@pytest.mark.unit
def test_us03_c1_um_falhando_resulta_em_falhou() -> None:

    casos = [CasoDeTeste(True, 10), CasoDeTeste(False, 20, "erro A")]

    resultado = consolidar_casos("/tarefas", "GET", casos)

    assert resultado.status == StatusResultado.FALHOU


@pytest.mark.unit
def test_us03_c1_mensagem_e_do_primeiro_que_falhou() -> None:

    casos = [CasoDeTeste(False, 10, "erro A"), CasoDeTeste(False, 20, "erro B")]

    resultado = consolidar_casos("/tarefas", "GET", casos)

    assert resultado.mensagem_erro == "erro A"


@pytest.mark.unit
def test_us03_c1_duracao_e_a_soma_dos_casos() -> None:

    casos = [CasoDeTeste(True, 10), CasoDeTeste(False, 20, "erro A")]

    resultado = consolidar_casos("/tarefas", "GET", casos)

    assert resultado.duracao_ms == 30


@pytest.mark.unit
def test_us03_c1_todos_passando_nao_tem_mensagem() -> None:

    casos = [CasoDeTeste(True, 10)]

    resultado = consolidar_casos("/tarefas", "GET", casos)

    assert resultado.mensagem_erro is None


@pytest.mark.unit
def test_rn03_t2_sem_casos_resulta_em_falhou() -> None:
    resultado = consolidar_casos("/tarefas", "GET", [])

    assert resultado.status == StatusResultado.FALHOU
