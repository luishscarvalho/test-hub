import os

import httpx
import pytest


@pytest.mark.e2e
@pytest.mark.parametrize(
    "base_url",
    [
        os.getenv("HUB_URL", "http://localhost:8000"),
        os.getenv("TARGET_API_URL", "http://localhost:8001"),
    ],
)
def test_ambiente_hub_e_api_alvo_saudaveis(base_url: str) -> None:
    assert httpx.get(f"{base_url}/saude", timeout=5).status_code == 200
