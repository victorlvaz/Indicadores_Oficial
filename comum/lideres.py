"""Cadastro de líderes regionais (quem cobrar em cada regional) — guardado no mesmo banco do histórico.

Cada linha: regional, nome do líder e, opcionalmente, o ID do Feishu (open_id "ou_..."), que faz a menção (@) funcionar
de verdade na mensagem. Sem o ID, o nome sai como texto "@Nome"."""
import pandas as pd
from sqlalchemy import Column, Integer, MetaData, String, Table, delete, insert, select

CONTROLADORIA = "Controladoria"
REGIONAIS = ["SPE", "SPS", "SPN", "RJ", "MG", "PR", "CE", "BA", "GP", "SR", CONTROLADORIA]

meta = MetaData()
tabela = Table(
    "lideres_regionais", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("regional", String(30), nullable=False),
    Column("nome", String(150), nullable=False),
    Column("feishu_id", String(80)),
)
COLUNAS = ["regional", "nome", "feishu_id"]


def ler(engine) -> pd.DataFrame:
    meta.create_all(engine)
    with engine.connect() as con:
        linhas = con.execute(select(tabela.c.regional, tabela.c.nome, tabela.c.feishu_id).order_by(tabela.c.id)).fetchall()
    return pd.DataFrame(linhas, columns=COLUNAS).fillna("")


def salvar(engine, df: pd.DataFrame) -> int:
    """Troca o cadastro inteiro pelo conteúdo da tabela editada (linhas sem regional ou sem nome são ignoradas)."""
    meta.create_all(engine)
    registros = []
    for _, r in df.iterrows():
        reg, nome, uid = (("" if pd.isna(r.get(c)) else str(r.get(c)).strip()) for c in COLUNAS)
        if reg and nome:
            registros.append({"regional": reg, "nome": nome, "feishu_id": uid or None})
    with engine.begin() as con:
        con.execute(delete(tabela))
        if registros:
            con.execute(insert(tabela), registros)
    return len(registros)


def da_regional(df: pd.DataFrame, regional: str) -> list[tuple]:
    """[("@", nome, id_feishu_ou_None), ...] da regional, no formato de menção da mensagem."""
    sub = df[df["regional"].str.upper() == str(regional).upper()]
    return [("@", r.nome, (None if pd.isna(r.feishu_id) or not str(r.feishu_id).strip() else str(r.feishu_id).strip())) for r in sub.itertuples()]


def mencoes(df: pd.DataFrame, regional: str) -> list:
    """Menções separadas por " / ": ["@", " / ", "@"...] (vazio se a regional não tem líder cadastrado)."""
    out = []
    for i, m in enumerate(da_regional(df, regional)):
        if i:
            out.append(" / ")
        out.append(m)
    return out
