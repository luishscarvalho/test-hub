from pydantic_settings import BaseSettings


class Configuracao(BaseSettings):
    """Lida das variáveis de ambiente na subida da API (ADR-008).

    MODO_FALHA aceita true/false, 1/0, yes/no e on/off. Valor inválido impede a subida.
    """

    modo_falha: bool = False
