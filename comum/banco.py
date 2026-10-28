"""Conexão com o banco de dados do histórico.

Por padrão grava num arquivo SQLite local (dados/historico.db): funciona sem instalar nada.
Para usar o servidor de banco da empresa, informe só a URL de conexão (o código não muda):

  1) variável de ambiente INDICADORES_DB_URL, ou
  2) arquivo .streamlit/secrets.toml:
         [banco]
         url = "postgresql+psycopg2://usuario:senha@servidor:5432/indicadores"

Exemplos de URL (peça à TI: tipo do banco, servidor, porta, nome do banco, usuário e senha):
  PostgreSQL  postgresql+psycopg2://usuario:senha@servidor:5432/banco      (pip install psycopg2-binary)
  Neon (Postgres grátis, sem CNPJ): postgresql+psycopg2://usuario:senha@HOST.neon.tech/banco?sslmode=require
  Azure SQL / SQL Server (recomendado no Streamlit Cloud, não precisa de driver ODBC):
              mssql+pymssql://usuario:senha@SERVIDOR.database.windows.net/banco                     (pip install pymssql)
  SQL Server  mssql+pyodbc://usuario:senha@servidor/banco?driver=ODBC+Driver+17+for+SQL+Server   (pip install pyodbc)
  MySQL       mysql+pymysql://usuario:senha@servidor:3306/banco             (pip install pymysql)
As tabelas são criadas sozinhas na primeira vez (o usuário precisa de permissão de criar tabelas).
"""
import os
from pathlib import Path

import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
URL_PADRAO = "sqlite:///" + (PASTA_DADOS / "historico.db").as_posix()


def url_banco() -> str:
    url = os.environ.get("INDICADORES_DB_URL")
    if not url:
        try:
            url = st.secrets["banco"]["url"]
        except Exception:                      # sem secrets.toml
            url = None
    return url or URL_PADRAO


@st.cache_resource
def engine():
    url = url_banco()
    if url.startswith("sqlite"):
        PASTA_DADOS.mkdir(exist_ok=True)
    args = {}
    if url.startswith("mssql+pymssql"):        # Azure SQL grátis pausa sozinho: a 1ª conexão pode levar ~1 min para acordar
        args = {"login_timeout": 90, "timeout": 90}
    elif url.startswith("postgresql"):          # Neon dorme após 5 min sem uso: acorda em poucos segundos na 1ª conexão
        args = {"connect_timeout": 60, "keepalives": 1, "keepalives_idle": 30, "keepalives_interval": 10, "keepalives_count": 5}   # mantém a conexão viva durante comandos longos
    return create_engine(url, pool_pre_ping=True, pool_recycle=240, connect_args=args)


def eh_sqlite() -> bool:
    return url_banco().startswith("sqlite")


def descricao() -> str:
    """Texto curto e SEM senha para mostrar na tela."""
    u = make_url(url_banco())
    if u.drivername.startswith("sqlite"):
        return "SQLite (arquivo local)"
    return f"{u.drivername.split('+')[0]} · {u.host or ''}/{u.database or ''}"
