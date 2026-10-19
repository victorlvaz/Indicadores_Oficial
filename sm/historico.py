"""Histórico do SM no banco de dados (sem Streamlit).

Guarda uma linha por viagem (tipo + ID da tarefa) já tratada pelas regras, com o SM previsto e a CONTAGEM de SMs
do TECHIS. O SM realizado (limitado ao previsto) é calculado na leitura, então a opção de limite continua válida.

Ao salvar de novo uma viagem que já existe, a linha é atualizada e a contagem fica com o MAIOR valor entre o que
já estava gravado e o do TECHIS novo (o TECHIS novo pode não cobrir dias antigos).
"""
from datetime import datetime

import pandas as pd
from sqlalchemy import (Column, Date, DateTime, Float, Index, Integer, MetaData, String, Table, Text, and_,
                        bindparam, delete, func, select)

from comum.sql import apagar_por_chaves  # noqa: E402

meta = MetaData()

viagens = Table(
    "sm_viagens", meta,
    Column("tipo", String(10), primary_key=True),
    Column("id", String(40), primary_key=True),
    Column("saida_plan", DateTime, nullable=False),
    Column("dia", Date, nullable=False),
    Column("status", String(40)),
    Column("viagem", String(150)),
    Column("rota", String(150)),
    Column("rota_usada", String(150)),
    Column("tipo_transportador", String(80)),
    Column("transportador", String(80)),
    Column("pedido_mae", Float),
    Column("partida", String(150)),
    Column("chegada", String(150)),
    Column("placa", String(30)),
    Column("regiao", String(30)),
    Column("regiao_destino", String(30)),
    Column("sm_prev", Integer, nullable=False),
    Column("sm_contagem", Integer, nullable=False),
    Column("carregado_em", DateTime, nullable=False),
    Column("arquivo", String(250)),
    Index("ix_sm_viagens_dia", "dia"),
)

cargas = Table(
    "sm_cargas", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("carregado_em", DateTime, nullable=False),
    Column("arquivo", String(250)),
    Column("linhas_usadas", Integer),
    Column("novas", Integer),
    Column("atualizadas", Integer),
    Column("dia_min", Date),
    Column("dia_max", Date),
    Column("observacao", Text),
)

CHAVE = ["tipo", "id"]
_COLUNAS = [c.name for c in viagens.columns if c.name not in ("carregado_em", "arquivo")]
_TEXTOS = ["status", "viagem", "rota", "rota_usada", "tipo_transportador", "transportador", "partida", "chegada",
           "placa", "regiao", "regiao_destino"]


def preparar_tabelas(engine) -> None:
    meta.create_all(engine)


def salvar(engine, base: pd.DataFrame, arquivo: str, observacao: str = "") -> dict:
    """Grava a base (já com sm_contagem, vinda de aplicar_techis). Retorna {"novas", "atualizadas", "linhas"}."""
    preparar_tabelas(engine)
    agora = datetime.now().replace(microsecond=0)
    df = base.copy()
    df["id"] = df["id"].astype(str).str.strip()
    df["saida_plan"] = pd.to_datetime(df["saida_plan"])
    df["dia"] = df["saida_plan"].dt.normalize().dt.date
    for c in _TEXTOS:
        df[c] = df[c].where(df[c].notna(), None).map(lambda v: None if v is None else str(v))
    df = df.drop_duplicates(subset=CHAVE, keep="last")[_COLUNAS].copy()
    df["sm_prev"] = df["sm_prev"].astype(int)
    df["sm_contagem"] = df["sm_contagem"].fillna(0).astype(int)
    if df.empty:
        return {"novas": 0, "atualizadas": 0, "linhas": 0}

    with engine.begin() as con:
        existentes = pd.read_sql(
            select(viagens.c.tipo, viagens.c.id, viagens.c.sm_contagem)
            .where(and_(viagens.c.dia >= df["dia"].min(), viagens.c.dia <= df["dia"].max())), con)
        # a viagem pode ter mudado de dia: confere também pelas chaves enviadas
        ja = {(t, i): c for t, i, c in zip(existentes["tipo"], existentes["id"], existentes["sm_contagem"])}
        antes = df.apply(lambda r: ja.get((r["tipo"], r["id"])), axis=1)
        df["sm_contagem"] = [max(n, int(a)) if pd.notna(a) else n for n, a in zip(df["sm_contagem"], antes)]
        repetidas = [(t, i) for t, i, a in zip(df["tipo"], df["id"], antes) if pd.notna(a)]
        if repetidas:
            apagar_por_chaves(con, viagens, ["tipo", "id"], repetidas)
        df["carregado_em"] = agora
        df["arquivo"] = arquivo[:250]
        registros = df.astype(object).where(df.notna(), None).to_dict("records")
        for r in registros:
            r["saida_plan"] = r["saida_plan"].to_pydatetime()
        for i in range(0, len(registros), 2000):
            con.execute(viagens.insert(), registros[i:i + 2000])
        resumo = {"novas": len(df) - len(repetidas), "atualizadas": len(repetidas), "linhas": len(df)}
        con.execute(cargas.insert().values(
            carregado_em=agora, arquivo=arquivo[:250], linhas_usadas=len(df), novas=resumo["novas"],
            atualizadas=resumo["atualizadas"], dia_min=df["dia"].min(), dia_max=df["dia"].max(),
            observacao=observacao or None))
    return resumo


def versao(engine) -> tuple:
    preparar_tabelas(engine)
    with engine.connect() as con:
        n, ultimo = con.execute(select(func.count(), func.max(viagens.c.carregado_em))).one()
    return int(n), str(ultimo)


def ler(engine) -> pd.DataFrame:
    """Histórico no formato da base do SM (colunas de preparar_jms). sm_real_hist = contagem já apurada."""
    preparar_tabelas(engine)
    with engine.connect() as con:
        df = pd.read_sql(select(*[viagens.c[c] for c in _COLUNAS]), con)
    df["saida_plan"] = pd.to_datetime(df["saida_plan"])
    df["dia"] = pd.to_datetime(df["dia"])
    for c in _TEXTOS:
        df[c] = df[c].fillna("")
    df["sm_prev"] = df["sm_prev"].astype(int)
    df["sm_real_hist"] = df["sm_contagem"].astype(int)
    return df.drop(columns=["sm_contagem"])


def ler_cargas(engine) -> pd.DataFrame:
    preparar_tabelas(engine)
    with engine.connect() as con:
        return pd.read_sql(select(cargas).order_by(cargas.c.id.desc()), con)
