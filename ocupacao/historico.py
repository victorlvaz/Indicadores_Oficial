"""Histórico da Taxa de Ocupação no banco (sem Streamlit).

Guarda a base JÁ TRATADA, uma linha por viagem (chave = id da tarefa de transporte): reenviar o mesmo dia
atualiza as linhas e acrescenta as novas, sem duplicar."""
from datetime import datetime

import pandas as pd

from comum import original
from comum.sql import apagar_por_ids, com_reconexao
from sqlalchemy import (Column, Date, DateTime, Float, Index, Integer, MetaData, String, Table, Text, delete, func, inspect,
                        select)

from .calculos import completar

meta = MetaData()

viagens = Table(
    "oc_viagens", meta,
    Column("id", String(40), primary_key=True),
    Column("dia", Date, nullable=False),
    Column("saida_plan", DateTime),
    Column("status", String(40)),
    Column("viagem", String(150)),
    Column("tipo_linha", String(20)),
    Column("tipo_transportador", String(80)),
    Column("condutor", String(120)),
    Column("partida", String(150)),
    Column("reg_origem", String(30)),
    Column("placa", String(30)),
    Column("veiculo", String(40)),
    Column("volume", Float),
    Column("carregado_em", DateTime, nullable=False),
    Column("arquivo", String(250)),
    Column("original", Text),                       # linha original do JMS (compactada), para a base exportada
    Index("ix_oc_viagens_dia", "dia"),
)

cargas = Table(
    "oc_cargas", meta,
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

_COLUNAS_BASE = [c.name for c in viagens.columns if c.name not in ("carregado_em", "arquivo", "original")]


def preparar_tabelas(engine) -> None:
    meta.create_all(engine)
    original.garantir_coluna(engine, viagens)
    colunas = {c["name"] for c in inspect(engine).get_columns(viagens.name)}
    if "condutor" not in colunas:                 # banco criado antes da coluna do motorista: acrescenta
        with engine.begin() as con:
            con.exec_driver_sql(f"ALTER TABLE {viagens.name} ADD COLUMN condutor VARCHAR(120)")


def _para_registros(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict("records")


@com_reconexao
def salvar(engine, base: pd.DataFrame, arquivo: str, linhas_lidas: int, observacao: str = "", ids_brutos=None) -> dict:
    preparar_tabelas(engine)
    agora = datetime.now().replace(microsecond=0)
    df = base.copy()
    df["id"] = df["id"].astype(str).str.strip()
    df["dia"] = pd.to_datetime(df["dia"]).dt.date
    df["saida_plan"] = pd.to_datetime(df["saida_plan"])
    df = df.drop_duplicates(subset=["id"], keep="last")
    df = df[_COLUNAS_BASE + (["original"] if "original" in df.columns else [])].copy()
    df["carregado_em"] = agora
    df["arquivo"] = arquivo[:250]
    if df.empty:
        return {"novas": 0, "atualizadas": 0, "linhas": 0}

    with engine.begin() as con:
        ids = list(df["id"])
        existentes = set()
        for i in range(0, len(ids), 500):
            lote = ids[i:i + 500]
            existentes |= set(con.execute(select(viagens.c.id).where(viagens.c.id.in_(lote))).scalars())
        if existentes:
            lista = list(existentes)
            for i in range(0, len(lista), 500):
                con.execute(delete(viagens).where(viagens.c.id.in_(lista[i:i + 500])))
        if ids_brutos:                                # reprocessa o arquivo inteiro: some também o que o filtro novo exclui
            apagar_por_ids(con, viagens, ids_brutos)
        registros = _para_registros(df)
        for r in registros:
            if r["saida_plan"] is not None:
                r["saida_plan"] = r["saida_plan"].to_pydatetime()
        for i in range(0, len(registros), 2000):
            con.execute(viagens.insert(), registros[i:i + 2000])
        resumo = {"novas": len(ids) - len(existentes), "atualizadas": len(existentes), "linhas": len(df)}
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


def ler(engine, com_original: bool = False) -> pd.DataFrame:
    preparar_tabelas(engine)
    with engine.connect() as con:
        df = pd.read_sql(select(*[viagens.c[c] for c in _COLUNAS_BASE + (["original"] if com_original else [])]), con)
    df["saida_plan"] = pd.to_datetime(df["saida_plan"])
    df["dia"] = pd.to_datetime(df["dia"])
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    for c in ("placa", "veiculo", "reg_origem", "condutor"):
        df[c] = df[c].fillna("")
    return completar(df)


def ler_cargas(engine) -> pd.DataFrame:
    preparar_tabelas(engine)
    with engine.connect() as con:
        return pd.read_sql(select(cargas).order_by(cargas.c.id.desc()), con)
