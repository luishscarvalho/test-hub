import pytest
from fastapi.testclient import TestClient

from app.bootstrap.api import app


@pytest.mark.integration
def test_nf_06_saude_do_hub_responde_200() -> None:
    resposta = TestClient(app).get("/saude")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
