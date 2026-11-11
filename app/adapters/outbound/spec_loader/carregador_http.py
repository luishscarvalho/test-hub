"""Download, leitura e validação da spec OpenAPI (porta CarregadorDeSpec, ADR-007).

A mesma validação vale para spec baixada por URL e para spec enviada como arquivo (US02-C5).
"""

import httpx
from openapi_spec_validator import validate
from openapi_spec_validator.validation.exceptions import (
    OpenAPIValidationError,
    ValidatorDetectError,
)
from referencing.exceptions import Unresolvable

from app.application.portas import SpecInvalida
from app.application.spec_normalizada import normalizar

# Chaves de um Path Item que são operações. As demais (parameters, summary...) não são.
METODOS_HTTP = frozenset({"get", "put", "post", "delete", "options", "head", "patch", "trace"})


class CarregadorDeSpecHttp:
    def __init__(self, *, timeout_s: float) -> None:
        self._timeout_s = timeout_s

    def baixar(self, url: str) -> dict[str, object]:
        try:
            resposta = httpx.get(url, timeout=self._timeout_s, follow_redirects=True)
            resposta.raise_for_status()
        except httpx.HTTPStatusError as erro:
            codigo = erro.response.status_code
            raise SpecInvalida(f"Falha ao baixar a spec: {url} respondeu {codigo}") from erro
        except (httpx.HTTPError, httpx.InvalidURL) as erro:
            raise SpecInvalida(f"Falha ao baixar a spec de {url}: {erro}") from erro
        return self.ler(resposta.content)

    def ler(self, conteudo: bytes) -> dict[str, object]:
        spec = normalizar(conteudo)
        _validar_openapi(spec)
        if not _tem_endpoint(spec):
            raise SpecInvalida("Spec inválida: nenhum endpoint declarado em paths (RN-02)")
        return spec


def _validar_openapi(spec: dict[str, object]) -> None:
    try:
        validate(spec)
    except ValidatorDetectError as erro:
        raise SpecInvalida(
            "Spec inválida: versão OpenAPI não identificada (campo openapi ou swagger)"
        ) from erro
    except OpenAPIValidationError as erro:
        local = erro.json_path if erro.absolute_path else "raiz"
        # A mensagem completa repete a spec inteira. A primeira linha já diz o motivo.
        motivo = erro.message.splitlines()[0]
        raise SpecInvalida(f"Spec inválida em {local}: {motivo}") from erro
    except Unresolvable as erro:
        # Vem da biblioteca referencing, usada pelo validador para seguir os $ref.
        raise SpecInvalida(f"Spec inválida: referência não encontrada: {erro.ref}") from erro


def _tem_endpoint(spec: dict[str, object]) -> bool:
    caminhos = spec.get("paths")
    if not isinstance(caminhos, dict):
        return False
    return any(isinstance(item, dict) and METODOS_HTTP & item.keys() for item in caminhos.values())
