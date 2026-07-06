"""Testes unitários do módulo de criptografia LGPD (app.core.crypto).

Cobre o round-trip Fernet (encrypt/decrypt) e o hash determinístico de busca
(hash_for_search) — antes sem cobertura direta (achado #5 do Grupo 9).
"""

import pytest

from app.core.crypto import decrypt, encrypt, hash_for_search


def test_encrypt_decrypt_round_trip():
    """decrypt(encrypt(x)) == x e o ciphertext difere do plaintext."""
    plain = "123.456.789-00"
    cipher = encrypt(plain)
    assert cipher != plain
    assert decrypt(cipher) == plain


def test_encrypt_nao_deterministico():
    """Fernet inclui IV/timestamp: o mesmo valor cifra para ciphertexts diferentes."""
    assert encrypt("segredo") != encrypt("segredo")


def test_decrypt_valor_invalido_levanta():
    """Decifrar lixo (não-Fernet) deve falhar, não retornar texto puro."""
    with pytest.raises(Exception):
        decrypt("isto-nao-e-um-token-fernet")


def test_hash_for_search_deterministico():
    """O mesmo valor sempre gera o mesmo hash (busca exata estável)."""
    assert hash_for_search("12345678900") == hash_for_search("12345678900")


def test_hash_for_search_normaliza_formato():
    """CPF com e sem formatação (./-, espaços) gera o MESMO hash."""
    assert hash_for_search("123.456.789-00") == hash_for_search("12345678900")
    assert hash_for_search("  123.456.789-00  ") == hash_for_search("12345678900")


def test_hash_for_search_valores_diferentes():
    """Valores distintos geram hashes distintos."""
    assert hash_for_search("12345678900") != hash_for_search("00000000000")


def test_hash_for_search_nao_e_plaintext_nem_sha256_puro():
    """O hash é hex de 64 chars (SHA-256) e não revela o valor original."""
    h = hash_for_search("12345678900")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
    assert "12345678900" not in h
