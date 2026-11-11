"""Normalização da spec e cálculo do hash (ADR-007, RN-13).

A spec chega como JSON ou YAML. As duas formas viram o mesmo dict compatível com JSON, e o
hash é o SHA-256 desse dict serializado com chaves ordenadas. Assim, diferenças só de
formato (YAML ou JSON) ou de ordem de chaves não geram versão nova.
"""

import hashlib
import json

import yaml

from app.application.portas import SpecInvalida


def normalizar(conteudo: bytes) -> dict[str, object]:
    """Lê JSON ou YAML e devolve um dict compatível com JSON.

    JSON é lido primeiro pelo próprio json: o PyYAML segue o YAML 1.1, que lê número com
    expoente e sem ponto (1e+17, válido em JSON) como texto.

    YAML aceita chaves que JSON não aceita, como `200:` sem aspas (vira int). A volta por
    json.dumps transforma essas chaves em texto, como ficariam se a spec fosse JSON.
    """
    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError as erro:
        raise SpecInvalida("Spec inválida: o conteúdo não é texto UTF-8") from erro
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        try:
            dados = yaml.safe_load(texto)
        except yaml.YAMLError as erro:
            motivo = f"Spec inválida: o conteúdo não é JSON nem YAML ({erro})"
            raise SpecInvalida(motivo) from erro
    if not isinstance(dados, dict):
        raise SpecInvalida("Spec inválida: o conteúdo não é um objeto JSON ou YAML")
    convertido: dict[str, object] = json.loads(json.dumps(dados, default=str))
    return convertido


def calcular_hash(spec: dict[str, object]) -> str:
    """SHA-256 em hexadecimal do JSON com chaves ordenadas e sem espaços."""
    texto = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()
