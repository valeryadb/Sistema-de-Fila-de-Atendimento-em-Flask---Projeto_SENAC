"""
Camada de banco de dados — SQLite com interface compatível com o
mysql.connector.

POR QUE SQLITE?
O projeto original usava MySQL, que exige um servidor de banco à parte —
inviável em hospedagem gratuita e desnecessário para uma demo de
portfólio. Este adaptador expõe a MESMA interface que o restante do
código já usa (get_db() → conn.cursor(dictionary=True) → execute com
%s → commit/lastrowid), então `routes.py` e `models.py` continuam
praticamente intactos. Trocar a implementação sem tocar em quem a
consome é o ponto da separação em camadas.

O arquivo do banco é criado e populado com dados de demonstração na
primeira execução (schema_sqlite.sql + seed abaixo).
"""
import os
import re
import sqlite3
import threading

import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.getenv("MOVIDA_DB_PATH", os.path.join(BASE_DIR, "movida.db"))
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema_sqlite.sql")

# Erro com o mesmo nome que o mysql.connector exporta, para os excepts
# existentes continuarem funcionando.
Error = sqlite3.Error


# O mysql.connector devolve colunas TIMESTAMP como datetime; o sqlite3
# devolve texto. Os templates chamam .strftime() nesses valores, então
# registramos um conversor: toda coluna DECLARADA como TIMESTAMP no
# schema volta como datetime (PARSE_DECLTYPES faz o casamento).
from datetime import datetime as _dt


def _parse_timestamp(raw: bytes):
    texto = raw.decode()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return _dt.strptime(texto, fmt)
        except ValueError:
            continue
    return texto  # formato inesperado: devolve como veio


sqlite3.register_converter("TIMESTAMP", _parse_timestamp)

_init_lock = threading.Lock()
_initialized = False


# ------------------------------------------------------------------
# Adaptação de sintaxe: o código escreve queries no dialeto MySQL;
# aqui convertemos o que o SQLite não entende.
# ------------------------------------------------------------------
def _adapt_sql(sql: str) -> str:
    sql = sql.replace("%s", "?")
    return sql


def _dict_factory(cursor, row):
    return {d[0]: row[i] for i, d in enumerate(cursor.description)}


class _CursorShim:
    """Imita a API do cursor do mysql.connector sobre o sqlite3."""

    def __init__(self, conn: sqlite3.Connection, dictionary: bool = False):
        self._cur = conn.cursor()
        self._dictionary = dictionary

    # --- API usada pelo projeto ---
    def execute(self, sql, params=None):
        return self._cur.execute(_adapt_sql(sql), params or [])

    def executemany(self, sql, seq):
        return self._cur.executemany(_adapt_sql(sql), seq)

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None or not self._dictionary:
            return row
        return _dict_factory(self._cur, row)

    def fetchall(self):
        rows = self._cur.fetchall()
        if not self._dictionary:
            return rows
        return [_dict_factory(self._cur, r) for r in rows]

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def close(self):
        self._cur.close()


class _ConnShim:
    """Imita a API da conexão do mysql.connector sobre o sqlite3."""

    def __init__(self, path: str):
        # check_same_thread=False: o Flask-SocketIO usa threads; cada
        # requisição abre a própria conexão, então o acesso é seguro.
        self._conn = sqlite3.connect(path, check_same_thread=False, timeout=15,
                                     detect_types=sqlite3.PARSE_DECLTYPES)
        self._conn.execute("PRAGMA foreign_keys = ON")

    def cursor(self, dictionary: bool = False, buffered: bool = False, **_kw):
        # `buffered` existe no mysql.connector; no sqlite é irrelevante,
        # mas aceitamos o argumento para manter a assinatura.
        return _CursorShim(self._conn, dictionary=dictionary)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    # usado pelo pandas em query_to_df
    @property
    def raw(self):
        return self._conn


# ------------------------------------------------------------------
# Inicialização: cria o schema e os dados de demonstração uma vez.
# ------------------------------------------------------------------
def _seed(conn: sqlite3.Connection):
    from werkzeug.security import generate_password_hash

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tb_empresa")
    if cur.fetchone()[0]:
        return  # já populado

    senha = generate_password_hash("demo123")
    cur.execute(
        """INSERT INTO tb_empresa
           (nome, cnpj, segmento, funcionarios, site, email, telefone, cep,
            endereco, cidade, estado, senha, confirmar_senha, descricao)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("Clínica Movida (demo)", "00.000.000/0001-00", "Clinica particular",
         12, "https://example.com", "demo@movida.com", "(61) 99999-0000",
         "70000-000", "SGAS 915", "Brasília", "DF", senha, senha,
         "Estabelecimento de demonstração do sistema de fila."),
    )
    empresa_id = cur.lastrowid

    demo_pacientes = [
        ("111.111.111-11", "Ana Souza", "1988-04-12", "(61) 98888-0001",
         "Febre e dor de cabeça", "verde", "Dra. Lima"),
        ("222.222.222-22", "Bruno Castro", "1975-09-30", "(61) 98888-0002",
         "Dor no peito", "vermelho", "Dr. Nogueira"),
        ("333.333.333-33", "Carla Mendes", "2001-01-22", "(61) 98888-0003",
         "Torção no tornozelo", "amarelo", "Dra. Lima"),
        ("444.444.444-44", "Diego Farias", "1995-07-08", "(61) 98888-0004",
         "Crise alérgica", "laranja", "Dr. Nogueira"),
    ]
    for cpf, nome, nasc, tel, sintomas, cls, resp in demo_pacientes:
        cur.execute(
            """INSERT INTO pacientes
               (cpf, nome, nascimento, telefone, sintomas, classificacao,
                responsavel, empresa_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (cpf, nome, nasc, tel, sintomas, cls, resp, empresa_id),
        )
        cur.execute(
            "INSERT INTO fila (paciente_id, empresa_id) VALUES (?, ?)",
            (cur.lastrowid, empresa_id),
        )

    cur.execute(
        """INSERT INTO profissionais
           (id_empresa, nome_completo, data_nascimento, telefone,
            email_profissional, especialidade, registro_crm_coren,
            estado_crm, turno_atendimento, status_clinica,
            informacoes_adicionais)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (empresa_id, "Dra. Helena Lima", "1980-03-15", "(61) 97777-0001",
         "helena.lima@movida.com", "Clínica geral", "CRM-12345", "DF",
         "Manhã", "Ativo", "Profissional de demonstração."),
    )
    conn.commit()


def _ensure_db():
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        conn = sqlite3.connect(DB_PATH, check_same_thread=False,
                               detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            with open(SCHEMA_PATH, encoding="utf-8") as f:
                conn.executescript(f.read())
            _seed(conn)
        finally:
            conn.close()
        _initialized = True


# ------------------------------------------------------------------
# API pública — exatamente a que o projeto já usava
# ------------------------------------------------------------------
def get_db():
    """Retorna uma conexão (interface compatível com mysql.connector)."""
    _ensure_db()
    return _ConnShim(DB_PATH)


def query_to_df(query: str, params: tuple = None) -> pd.DataFrame:
    """Executa uma query e retorna um DataFrame do pandas."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql(_adapt_sql(query), conn, params=params)
    finally:
        conn.close()
    return df
