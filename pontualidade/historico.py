"""Histórico da Pontualidade (Taxa de Chegada e Taxa de Saída) no banco (sem Streamlit).

Guarda a base JÁ TRATADA, uma linha por trecho (chave id + estação de partida + estação de chegada + saída planejada):
enviar o mesmo dia de novo atualiza as linhas (os horários reais vão sendo preenchidos) e acrescenta as novas.
Trechos que viraram Cancelado/Planejado no arquivo novo saem do histórico."""
from datetime import datetime

import pandas as pd
from sqlalchemy import (Column, Date, DateTime, Index, Integer, MetaData, String, Table, Text, and_, bindparam,
                        delete, func, select)

meta = MetaData()

trechos = Table(
    "pt_trechos", meta,
    Column("id", String(40), primary_key=True),
    Column("cod_partida", String(40), primary_key=True),
    Column("cod_chegada", String(40), primary_key=True),
    Column("saida_plan", DateTime, primary_key=True),
    Column("status", String(40)),
    Column("viagem", String(150)),
    Column("tipo_linha", String(20)),
    Column("partida", String(150)),
    Column("chegada", String(150)),
    Column("reg_saida", String(30)),
    Column("reg_chegada", String(30)),
    Column("saida_real", DateTime),
    Column("chegada_plan", DateTime),
    Column("chegada_real", DateTime),
    Column("dia_saida", Date, nullable=False),
    Column("dia_chegada", Date, nullable=False),
    Column("ok_saida", Integer, nullable=False),
    Column("ok_chegada", Integer, nullable=False),
    Column("aberto_saida", Integer, nullable=False),
    Column("aberto_chegada", Integer, nullable=False),
    Column("carregado_em", DateTime, nullable=False),
    Column("arquivo", String(250)),
    Index("ix_pt_trechos_dia_saida", "dia_saida"),
    Index("ix_pt_trechos_dia_chegada", "dia_chegada"),
)

cargas = Table(
    "pt_cargas", meta,
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

CHAVE = ["id", "cod_partida", "cod_chegada", "saida_plan"]
_COLUNAS_BASE = [c.name for c in trechos.columns if c.name not in ("carregado_em", "arquivo")]
_DATAS_HORA = ("saida_plan", "saida_real", "chegada_plan", "chegada_real")


def preparar_tabelas(engine) -> None:
    meta.create_all(engine)


def _py(df: pd.DataFrame) -> list[dict]:
    """Registros com tipos do Python (NaT/NaN -> None) para o SQLAlchemy."""
    regs = []
    for r in df.astype(object).where(df.notna(), None).to_dict("records"):
        for c in _DATAS_HORA:
            if r.get(c) is not None:
                r[c] = pd.Timestamp(r[c]).to_pydatetime()
        regs.append(r)
    return regs


def salvar(engine, base: pd.DataFrame, arquivo: str, linhas_lidas: int, descartadas: pd.DataFrame | None = None,
           observacao: str = "") -> dict:
    """Grava a base tratada. Retorna {"novas": n, "atualizadas": n, "linhas": n}."""
    preparar_tabelas(engine)
    agora = datetime.now().replace(microsecond=0)
    df = base.copy()
    df["dia_saida"] = pd.to_datetime(df["dia_saida"]).dt.date
    df["dia_chegada"] = pd.to_datetime(df["dia_chegada"]).dt.date
    df = df.drop_duplicates(subset=CHAVE, keep="last")[_COLUNAS_BASE].copy()
    df["carregado_em"] = agora
    df["arquivo"] = arquivo[:250]
    if df.empty:
        return {"novas": 0, "atualizadas": 0, "linhas": 0}

    def _chaves(d):
        return list(zip(d["id"].astype(str), d["cod_partida"].astype(str), d["cod_chegada"].astype(str),
                        pd.to_datetime(d["saida_plan"])))

    novas_k = _chaves(df)
    sair = _chaves(descartadas) if descartadas is not None and len(descartadas) else []
    apagar_k = list(dict.fromkeys(novas_k + sair))

    with engine.begin() as con:
        ini = min(k[3] for k in apagar_k).to_pydatetime()
        fim = max(k[3] for k in apagar_k).to_pydatetime()
        existentes = pd.read_sql(
            select(trechos.c.id, trechos.c.cod_partida, trechos.c.cod_chegada, trechos.c.saida_plan)
            .where(and_(trechos.c.saida_plan >= ini, trechos.c.saida_plan <= fim)), con)
        exist = set(zip(existentes["id"], existentes["cod_partida"], existentes["cod_chegada"],
                        pd.to_datetime(existentes["saida_plan"])))
        a_apagar = [k for k in apagar_k if k in exist]
        if a_apagar:
            cmd = delete(trechos).where(and_(
                trechos.c.id == bindparam("k_id"), trechos.c.cod_partida == bindparam("k_par"),
                trechos.c.cod_chegada == bindparam("k_cheg"), trechos.c.saida_plan == bindparam("k_sai")))
            for i in range(0, len(a_apagar), 5000):
                con.execute(cmd, [{"k_id": a, "k_par": b, "k_cheg": c, "k_sai": d.to_pydatetime()}
                                  for a, b, c, d in a_apagar[i:i + 5000]])
        regs = _py(df)
        for i in range(0, len(regs), 2000):
            con.execute(trechos.insert(), regs[i:i + 2000])
        ja = {k for k in novas_k if k in exist}
        res = {"novas": len(novas_k) - len(ja), "atualizadas": len(ja), "linhas": len(df)}
        con.execute(cargas.insert().values(
            carregado_em=agora, arquivo=arquivo[:250], linhas_lidas=linhas_lidas, linhas_usadas=len(df),
            novas=res["novas"], atualizadas=res["atualizadas"],
            dia_min=min(df["dia_saida"].min(), df["dia_chegada"].min()),
            dia_max=max(df["dia_saida"].max(), df["dia_chegada"].max()), observacao=observacao or None))
    return res


def versao(engine) -> tuple:
    preparar_tabelas(engine)
    with engine.connect() as con:
        n, ultimo = con.execute(select(func.count(), func.max(trechos.c.carregado_em))).one()
    return int(n), str(ultimo)


def ler(engine) -> pd.DataFrame:
    """Histórico completo no formato da base tratada."""
    preparar_tabelas(engine)
    with engine.connect() as con:
        df = pd.read_sql(select(*[trechos.c[c] for c in _COLUNAS_BASE]), con)
    for c in _DATAS_HORA + ("dia_saida", "dia_chegada"):
        df[c] = pd.to_datetime(df[c])
    for c in ("ok_saida", "ok_chegada", "aberto_saida", "aberto_chegada"):
        df[c] = df[c].astype(int)
    return df


def ler_cargas(engine) -> pd.DataFrame:
    preparar_tabelas(engine)
    with engine.connect() as con:
        return pd.read_sql(select(cargas).order_by(cargas.c.id.desc()), con)
