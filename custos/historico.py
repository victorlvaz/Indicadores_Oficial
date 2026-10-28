"""Histórico de Custos no banco (sem Streamlit).

Guarda a base JÁ TRATADA, uma linha por viagem (chave = regional + ID + seq; seq > 1 só quando o mesmo ID veio com valores
diferentes). Reenviar o arquivo de uma regional substitui os dias que ele cobre, sem duplicar."""
from datetime import datetime

import pandas as pd

from comum.sql import com_reconexao
from sqlalchemy import (Column, Date, DateTime, Float, Index, Integer, MetaData, String, Table, Text, and_, delete, func,
                        select)

from .calculos import COLUNAS_BASE, completar

meta = MetaData()

viagens = Table(
    "cu_viagens", meta,
    Column("regional", String(20), primary_key=True),
    Column("id", String(40), primary_key=True),
    Column("seq", Integer, primary_key=True),
    Column("dia", Date, nullable=False),
    Column("uf", String(10)),
    Column("sc_origem", String(80)),
    Column("hub_destino", String(80)),
    Column("frota", String(30)),
    Column("transportadora", String(200)),
    Column("placa", String(30)),
    Column("veiculo", String(40)),
    Column("rota", String(250)),
    Column("tipo_transp", String(50)),
    Column("frete_rota", Float),
    Column("frete_total", Float),
    Column("pacotes", Float),
    Column("km", Float),
    Column("iguais_removidas", Integer),
    Column("carregado_em", DateTime, nullable=False),
    Column("arquivo", String(250)),
    Index("ix_cu_viagens_dia", "dia"),
)

cargas = Table(
    "cu_cargas", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("carregado_em", DateTime, nullable=False),
    Column("arquivo", String(250)),
    Column("regional", String(20)),
    Column("linhas_lidas", Integer),
    Column("linhas_usadas", Integer),
    Column("novas", Integer),
    Column("atualizadas", Integer),
    Column("dia_min", Date),
    Column("dia_max", Date),
    Column("observacao", Text),
)


def preparar_tabelas(engine) -> None:
    meta.create_all(engine)


def _para_registros(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict("records")


def _lotes(seq, n=500):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


@com_reconexao
def salvar(engine, base: pd.DataFrame, regional: str, arquivo: str, linhas_lidas: int, observacao: str = "") -> dict:
    """Grava a base de UMA regional. Substitui o que já existia dessa regional entre a 1ª e a última data do arquivo."""
    preparar_tabelas(engine)
    agora = datetime.now().replace(microsecond=0)
    df = base[COLUNAS_BASE].copy()
    df["regional"] = regional
    df["dia"] = pd.to_datetime(df["dia"]).dt.date
    df["seq"] = df["seq"].astype(int)
    df["iguais_removidas"] = df["iguais_removidas"].astype(int)
    df["carregado_em"] = agora
    df["arquivo"] = arquivo[:250]
    for c, n in (("transportadora", 200), ("rota", 250), ("hub_destino", 80), ("sc_origem", 80)):
        df[c] = df[c].astype(str).str.slice(0, n)
    if df.empty:
        return {"novas": 0, "atualizadas": 0, "linhas": 0}

    ini, fim = df["dia"].min(), df["dia"].max()
    with engine.begin() as con:
        antes = con.execute(select(func.count()).where(and_(
            viagens.c.regional == regional, viagens.c.dia >= ini, viagens.c.dia <= fim))).scalar_one()
        con.execute(delete(viagens).where(and_(
            viagens.c.regional == regional, viagens.c.dia >= ini, viagens.c.dia <= fim)))
        for lote in _lotes(df["id"].unique()):                              # o mesmo ID com outra data também é substituído
            con.execute(delete(viagens).where(and_(viagens.c.regional == regional, viagens.c.id.in_(lote))))
        registros = _para_registros(df)
        for lote in _lotes(registros, 2000):
            con.execute(viagens.insert(), lote)
        novas = max(len(df) - int(antes), 0)
        resumo = {"novas": novas, "atualizadas": len(df) - novas, "linhas": len(df)}
        con.execute(cargas.insert().values(
            carregado_em=agora, arquivo=arquivo[:250], regional=regional, linhas_lidas=linhas_lidas,
            linhas_usadas=len(df), novas=resumo["novas"], atualizadas=resumo["atualizadas"], dia_min=ini, dia_max=fim,
            observacao=observacao or None))
    return resumo


def versao(engine) -> tuple:
    preparar_tabelas(engine)
    with engine.connect() as con:
        n, ultimo = con.execute(select(func.count(), func.max(viagens.c.carregado_em))).one()
    return int(n), str(ultimo)


def ler(engine) -> pd.DataFrame:
    preparar_tabelas(engine)
    cols = [viagens.c[c] for c in COLUNAS_BASE]
    with engine.connect() as con:
        df = pd.read_sql(select(*cols), con)
    df["dia"] = pd.to_datetime(df["dia"])
    for c in ("frete_rota", "frete_total", "pacotes", "km"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("regional", "hub_destino", "transportadora", "placa", "veiculo", "rota", "tipo_transp", "sc_origem", "uf", "frota"):
        df[c] = df[c].fillna("")
    df["iguais_removidas"] = df["iguais_removidas"].fillna(0).astype(int)
    return completar(df)


def ler_cargas(engine) -> pd.DataFrame:
    preparar_tabelas(engine)
    with engine.connect() as con:
        return pd.read_sql(select(cargas).order_by(cargas.c.id.desc()), con)
