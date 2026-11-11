"""Cadastro de API alvo com a primeira versão da spec (US-01, US-02, RN-01, RN-13)."""

from app.application.portas import (
    CadastroInvalido,
    CarregadorDeSpec,
    Relogio,
    RepositorioDeApis,
)
from app.application.spec_normalizada import calcular_hash
from app.domain.api_alvo import ApiAlvo
from app.domain.spec_versao import OrigemSpec, SpecVersao

# O repositório ignora o api_alvo_id da spec do cadastro: o id vem do INSERT da API.
_API_AINDA_SEM_ID = 0


class CadastrarApi:
    def __init__(
        self, *, apis: RepositorioDeApis, carregador: CarregadorDeSpec, relogio: Relogio
    ) -> None:
        self._apis = apis
        self._carregador = carregador
        self._relogio = relogio

    def executar(
        self,
        *,
        nome: str,
        base_url: str,
        spec_url: str | None = None,
        spec_arquivo: bytes | None = None,
    ) -> ApiAlvo:
        """Valida a spec e grava a API com a primeira versão.

        Spec inválida ou inacessível levanta SpecInvalida e nada é gravado (US02-C1).
        """
        if spec_url is not None and spec_arquivo is None:
            conteudo = self._carregador.baixar(spec_url)
            origem = OrigemSpec.URL
        elif spec_arquivo is not None and spec_url is None:
            conteudo = self._carregador.ler(spec_arquivo)
            origem = OrigemSpec.ARQUIVO
        else:
            raise CadastroInvalido("Informe exatamente um entre spec_url e spec_arquivo")

        agora = self._relogio()
        spec = SpecVersao(_API_AINDA_SEM_ID, conteudo, calcular_hash(conteudo), origem, agora)
        api = ApiAlvo(nome=nome, base_url=base_url, criado_em=agora, spec_url=spec_url)
        return self._apis.adicionar(api, spec)
