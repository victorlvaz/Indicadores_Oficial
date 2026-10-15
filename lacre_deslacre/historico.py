"""Histórico do Lacre/Deslacre no banco de dados (sem Streamlit).

Guarda a base JÁ TRATADA (depois das regras de exclusão), uma linha por viagem/estação de chegada.
A chave é (id, cod_chegada, chegada_plan): enviar o mesmo dia de novo atualiza as linhas existentes
e acrescenta as novas, sem duplicar e sem apagar viagens que só estavam no envio anterior.

Se as regras de exclusão mudarem no futuro, o que já está no banco continua como foi gravado.
"""
from datetime import datetime

import pandas as pd
from sqlalchemy import (Column, DateTime, Date, Float, Index, Integer, MetaData, String, Table, Text,
                        and_, bindparam, delete, func, inspect, select)

meta = MetaData()

viagens = Table(
    "lacre_viagens", meta,
    Column("id", String(40), primary_key=True),
    Column("cod_chegada", String(40), primary_key=True),
    Column("chegada_plan", DateTime, primary_key=True),
    Column("dia", Date, nullable=False),
    Column("status", String(40)),
    Column("viagem", String(150)),
    Column("tipo_linha", String(20)),
    Column("tipo_transportador", String(80)),
    Column("pedido_mae", Float),
    Column("partida", String(150)),
    Column("reg_saida", String(30)),
    Column("reg_chegada", String(30)),
    Column("hora_lacre", String(40)),
    Column("hora_deslacre", String(40)),
    Column("lacrado", Integer, nullable=False),
    Column("deslacrado", Integer, nullable=False),
    Column("carregado_em", DateTime, nullable=False),
    Column("arquivo", String(250)),
    Index("ix_lacre_viagens_dia", "dia"),
)

cargas = Table(
    "lacre_cargas", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("carregado_em", DateTime, nullable=False),
    Column("arquivo", String(250)),
    Column("linhas_lidas", Integer),
    Column("linhas_usadas", Integer),
    Column("novas", Integer),
    Column("atualizadas", Integer),
    Column("dia_min", Date),
    Column("dia_max", Date),
    Column("observacao", Text),
)

CHAVE = ["id", "cod_chegada", "chegada_plan"]
_COLUNAS_BASE = [c.name for c in viagens.columns if c.name not in ("carregado_em", "arquivo")]


def preparar_tabelas(engine) -> None:
    meta.create_all(engine)                       # só cria o que não existe


def _para_registros(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict("records")


def salvar(engine, base: pd.DataFrame, arquivo: str, linhas_lidas: int, observacao: str = "") -> dict:
    """Grava a base tratada no histórico. Retorna {"novas": n, "atualizadas": n, "linhas": n}."""
    preparar_tabelas(engine)
    agora = datetime.now().replace(microsecond=0)
    df = base.copy()
    df["id"] = df["id"].astype(str).str.strip()
    df["cod_chegada"] = df["cod_chegada"].astype(str).str.strip()
    df["chegada_plan"] = pd.to_datetime(df["chegada_plan"])
    df["dia"] = df["chegada_plan"].dt.normalize().dt.date
    for c in ("hora_lacre", "hora_deslacre"):
        df[c] = df[c].where(df[c].notna(), None).map(lambda v: None if v is None else str(v))
    df = df.drop_duplicates(subset=CHAVE, keep="last")
    df = df[_COLUNAS_BASE].copy()
    df["carregado_em"] = agora
    df["arquivo"] = arquivo[:250]

    if df.empty:
        return {"novas": 0, "atualizadas": 0, "linhas": 0}

    with engine.begin() as con:
        existentes = pd.read_sql(
            select(viagens.c.id, viagens.c.cod_chegada, viagens.c.chegada_plan)
            .where(and_(viagens.c.dia >= df["dia"].min(), viagens.c.dia <= df["dia"].max())), con)
        chaves_exist = set(zip(existentes["id"], existentes["cod_chegada"], pd.to_datetime(existentes["chegada_plan"])))
        chaves_novas = list(zip(df["id"], df["cod_chegada"], df["chegada_plan"]))
        repetidas = [k for k in chaves_novas if k in chaves_exist]

        if repetidas:
            apagar = delete(viagens).where(and_(
                viagens.c.id == bindparam("k_id"), viagens.c.cod_chegada == bindparam("k_cod"),
                viagens.c.chegada_plan == bindparam("k_plan")))
            con.execute(apagar, [{"k_id": i, "k_cod": c, "k_plan": p.to_pydatetime()} for i, c, p in repetidas])
        registros = _para_registros(df)
        for r in registros:
            r["chegada_plan"] = r["chegada_plan"].to_pydatetime()
        for i in range(0, len(registros), 2000):
            con.execute(viagens.insert(), registros[i:i + 2000])

        resumo = {"novas": len(chaves_novas) - len(repetidas), "atualizadas": len(repetidas), "linhas": len(df)}
        con.execute(cargas.insert().values(
            carregado_em=agora, arquivo=arquivo[:250], linhas_lidas=linhas_lidas, linhas_usadas=len(df),
            novas=resumo["novas"], atualizadas=resumo["atualizadas"],
            dia_min=df["dia"].min(), dia_max=df["dia"].max(), observacao=observacao or None))
    return resumo


def versao(engine) -> tuple:
    """Muda sempre que entra dado novo (serve de chave para o cache da tela)."""
    preparar_tabelas(engine)
    with engine.connect() as con:
        n, ultimo = con.execute(select(func.count(), func.max(viagens.c.carregado_em))).one()
    return int(n), str(ultimo)


def ler(engine) -> pd.DataFrame:
    """Histórico completo no mesmo formato da base tratada (colunas de calculos.preparar)."""
    preparar_tabelas(engine)
    with engine.connect() as con:
        df = pd.read_sql(select(*[viagens.c[c] for c in _COLUNAS_BASE]), con)
    df["chegada_plan"] = pd.to_datetime(df["chegada_plan"])
    df["dia"] = pd.to_datetime(df["dia"])
    df["lacrado"] = df["lacrado"].astype(int)
    df["deslacrado"] = df["deslacrado"].astype(int)
    return df


def ler_cargas(engine) -> pd.DataFrame:
    preparar_tabelas(engine)
    with engine.connect() as con:
        return pd.read_sql(select(cargas).order_by(cargas.c.id.desc()), con)
