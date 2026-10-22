"""Histórico da Taxa de Uso de APP no banco (sem Streamlit).

Guarda a base JÁ TRATADA, uma linha por viagem/estação de chegada (chave id + cod_chegada + chegada_plan):
enviar o mesmo dia de novo atualiza as linhas e acrescenta as novas, sem duplicar.
Também guarda o último "Tipo de transportador" conhecido de cada viagem (app_transportadores), para
preencher os vazios das próximas extrações, como pede o passo a passo.
"""
from datetime import datetime

import pandas as pd
from sqlalchemy import (Column, Date, DateTime, Index, Integer, MetaData, String, Table, Text, and_, bindparam,
                        delete, func, inspect, select)

from .calculos import calcular_partes

from comum.sql import apagar_por_chaves  # noqa: E402

meta = MetaData()

viagens = Table(
    "app_viagens", meta,
    Column("id", String(40), primary_key=True),
    Column("cod_chegada", String(40), primary_key=True),
    Column("chegada_plan", DateTime, primary_key=True),
    Column("dia", Date, nullable=False),
    Column("status", String(40)),
    Column("viagem", String(150)),
    Column("tipo_linha", String(20)),
    Column("tipo_transportador", String(80)),
    Column("condutor", String(120)),
    Column("partida", String(150)),
    Column("reg_saida", String(30)),
    Column("reg_chegada", String(30)),
    Column("hora_checkout", String(40)),
    Column("hora_checkin", String(40)),
    Column("saiu_ok", Integer, nullable=False),
    Column("chegou_ok", Integer, nullable=False),
    Column("carregado_em", DateTime, nullable=False),
    Column("arquivo", String(250)),
    Index("ix_app_viagens_dia", "dia"),
)

cargas = Table(
    "app_cargas", meta,
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

transportadores = Table(
    "app_transportadores", meta,
    Column("viagem", String(150), primary_key=True),
    Column("tipo", String(80), nullable=False),
    Column("atualizado_em", DateTime, nullable=False),
)

CHAVE = ["id", "cod_chegada", "chegada_plan"]
_COLUNAS_BASE = [c.name for c in viagens.columns if c.name not in ("carregado_em", "arquivo")]


def preparar_tabelas(engine) -> None:
    meta.create_all(engine)
    colunas = {c["name"] for c in inspect(engine).get_columns(viagens.name)}
    if "condutor" not in colunas:                 # banco criado antes da coluna do motorista: acrescenta
        with engine.begin() as con:
            con.exec_driver_sql(f"ALTER TABLE {viagens.name} ADD COLUMN condutor VARCHAR(120)")


def _para_registros(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict("records")


def tipos_conhecidos(engine) -> dict:
    preparar_tabelas(engine)
    with engine.connect() as con:
        d = pd.read_sql(select(transportadores.c.viagem, transportadores.c.tipo), con)
    return dict(zip(d["viagem"], d["tipo"]))


def guardar_tipos(engine, tipos: dict) -> None:
    """Atualiza o último tipo conhecido de cada viagem (apaga as viagens enviadas e regrava)."""
    if not tipos:
        return
    preparar_tabelas(engine)
    agora = datetime.now().replace(microsecond=0)
    chaves = list(tipos)
    with engine.begin() as con:
        for i in range(0, len(chaves), 500):                       # lotes: limite de parâmetros do SQLite
            con.execute(delete(transportadores).where(transportadores.c.viagem.in_(chaves[i:i + 500])))
        regs = [{"viagem": v[:150], "tipo": t[:80], "atualizado_em": agora} for v, t in tipos.items()]
        for i in range(0, len(regs), 2000):
            con.execute(transportadores.insert(), regs[i:i + 2000])


def salvar(engine, base: pd.DataFrame, arquivo: str, linhas_lidas: int, observacao: str = "") -> dict:
    """Grava a base tratada. Retorna {"novas": n, "atualizadas": n, "linhas": n}."""
    preparar_tabelas(engine)
    agora = datetime.now().replace(microsecond=0)
    df = base.copy()
    df["id"] = df["id"].astype(str).str.strip()
    df["cod_chegada"] = df["cod_chegada"].astype(str).str.strip()
    df["chegada_plan"] = pd.to_datetime(df["chegada_plan"])
    df["dia"] = df["chegada_plan"].dt.normalize().dt.date
    for c in ("hora_checkout", "hora_checkin"):
        df[c] = df[c].where(df[c].notna(), None).map(lambda v: None if v is None else str(v))
    df["tipo_transportador"] = df["tipo_transportador"].astype(object).where(df["tipo_transportador"].notna(), None)
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
            apagar_por_chaves(con, viagens, CHAVE, [(i, c, p.to_pydatetime()) for i, c, p in repetidas])
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
    preparar_tabelas(engine)
    with engine.connect() as con:
        n, ultimo = con.execute(select(func.count(), func.max(viagens.c.carregado_em))).one()
    return int(n), str(ultimo)


def ler(engine) -> pd.DataFrame:
    """Histórico completo no formato da base tratada (+ n_prev e n_real)."""
    preparar_tabelas(engine)
    with engine.connect() as con:
        df = pd.read_sql(select(*[viagens.c[c] for c in _COLUNAS_BASE]), con)
    df["chegada_plan"] = pd.to_datetime(df["chegada_plan"])
    df["dia"] = pd.to_datetime(df["dia"])
    df["condutor"] = df["condutor"].fillna("")
    df["saiu_ok"] = df["saiu_ok"].astype(int)
    df["chegou_ok"] = df["chegou_ok"].astype(int)
    return calcular_partes(df)


def ler_cargas(engine) -> pd.DataFrame:
    preparar_tabelas(engine)
    with engine.connect() as con:
        return pd.read_sql(select(cargas).order_by(cargas.c.id.desc()), con)
