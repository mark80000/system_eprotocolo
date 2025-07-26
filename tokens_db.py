# Controla banco de tokens: salvar, buscar, validar, gerar hash.

import sqlite3
import hashlib
from datetime import datetime, timedelta


DB_NAME = "onr_tokens.db"
CHAVE = "SUA_CHAVE_AQUI"  # SUBSTIRUIR PELA CHAVE FORNECIDA PELA ONR


def inicializar_banco():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            criado_em DATETIME,
            usado BOOLEAN DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def salvar_tokens(tokens):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for token in tokens:
        cursor.execute("""
            INSERT OR IGNORE INTO tokens (token, criado_em, usado)
            VALUES (?, ?, 0)
        """, (token, datetime.now()))
    
    conn.commit()
    conn.close()


def obter_token_valido():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    limite_tempo = datetime.now() - timedelta(hours=8)
    cursor.execute("""
        SELECT id, token FROM tokens
        WHERE usado = 0 AND criado_em > ?
        ORDER BY criado_em ASC
        LIMIT 1
    """, (limite_tempo,))
    
    resultado = cursor.fetchone()
    conn.close()
    return resultado  # (id, token) ou None


def marcar_token_como_usado(token_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tokens SET usado = 1 WHERE id = ?", (token_id,))
    conn.commit()
    conn.close()


def gerar_hash(chave, token):
    """
    Gera o hash de autenticação no padrão exigido pela ONR:
    SHA-1(chave + token), codificado em UTF-8.
    """
    dados = (chave + token).encode("utf-8")
    return hashlib.sha1(dados).hexdigest()