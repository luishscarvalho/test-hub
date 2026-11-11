"""Configuração do hub, lida das variáveis de ambiente (nomes em maiúsculas)."""

from pydantic_settings import BaseSettings


class Configuracao(BaseSettings):
    # Mesmos valores do .env.example. No Compose e no CI vêm do ambiente.
    database_url: str = "postgresql+psycopg://testhub:testhub@localhost:5432/testhub"
    redis_url: str = "redis://localhost:6379/0"
    # Fila do RQ onde o hub enfileira e o worker escuta.
    fila_das_runs: str = "runs"

    # Seed fixa do gerador, registrada em cada run (RN-14).
    seed: int = 42
    # Máximo de casos gerados por operação (ADR-005).
    limite_de_casos: int = 10
    # Tempo máximo de cada requisição à API alvo. Esgotado, o caso falha (RN-03).
    timeout_requisicao_s: float = 5.0
    # Tempo máximo para baixar a spec por URL. Esgotado, a spec é inacessível (RN-02).
    timeout_download_spec_s: float = 5.0
    # Tempo máximo da run no job do RQ. Excedido, a run é interrompida (RN-12b).
    tempo_maximo_run_s: int = 300
    # Espera máxima pelo Redis no disparo. Esgotada, o disparo responde 503 (RN-16).
    timeout_conexao_s: float = 3.0
