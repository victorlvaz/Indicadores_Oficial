"""Taxa de Desperdício = tudo o que não foi ocupado. Usa a mesma base da Taxa de Ocupação (sem upload próprio).

Por regional: Desperdício % = 1 − Ocupação, com a ocupação limitada a 100% (veículo que levou mais que o previsto não desperdiçou);
Volume desperdiçado = previsto − carregado, e zero quando a regional passou de 100%."""
import numpy as np
import pandas as pd

from ocupacao import calculos as oc
from ocupacao.calculos import TOTAL, regionais  # noqa: F401  (reexportado para a tela)


def _acrescentar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["desp_vol"] = np.where(df["prev"] > 0, (df["prev"] - df["real"]).clip(lower=0), np.nan)
    df["desp"] = 1 - df["taxa"]
    return df


def frete_por_viagem(engine) -> pd.Series:
    """Frete total de cada viagem (ID do JMS) vindo do relatório de Custos: frete da rota + custos extras, somado por ID."""
    from custos import historico as ch
    try:
        c = ch.ler(engine)
    except Exception:
        return pd.Series(dtype=float)
    if c.empty:
        return pd.Series(dtype=float)
    c = c.assign(id=c["id"].astype(str).str.strip().str.upper())
    return c.groupby("id")["frete_total"].sum(min_count=1).dropna()


def tabela_periodo(base, tipo, ini=None, fim=None) -> pd.DataFrame:
    """Linhas: total + regionais. Colunas: n, regiao, viagens, prev, real, desp_vol, desp, [frete, perda], ranking (1 = menor desperdício).
    Se a base tiver a coluna `frete`: Frete = soma do frete das viagens da regional; Perda R$ = Frete × Desperdício %."""
    t = _acrescentar(oc.tabela_periodo(base, tipo, ini, fim))
    cols = ["n", "regiao", "viagens", "prev", "real", "desp_vol", "desp", "ranking"]
    if "frete" in base.columns:
        fr = oc._recorte(base, tipo, ini, fim).groupby("reg_origem")["frete"].sum(min_count=1)
        t["frete"] = t["regiao"].map(fr)
        t["perda"] = t["frete"] * t["desp"]
        total = t["regiao"] == TOTAL
        t.loc[total, "frete"] = t.loc[~total, "frete"].sum(min_count=1)
        t.loc[total, "perda"] = t.loc[~total, "perda"].sum(min_count=1)
        cols = cols[:7] + ["frete", "perda"] + cols[7:]
    return t[cols]


def viagens_sem_frete(base, tipo, ini=None, fim=None) -> tuple[int, int]:
    """(viagens do período sem frete encontrado, viagens do período)."""
    sub = oc._recorte(base, tipo, ini, fim)
    return int(sub["frete"].isna().sum()), len(sub)


def comparar(atual: pd.DataFrame, comparada: pd.DataFrame) -> pd.DataFrame:
    comp = comparada.set_index("regiao")["desp"]
    out = atual.copy()
    out["desp_comp"] = out["regiao"].map(comp)
    out["variacao"] = out["desp"] - out["desp_comp"]          # positivo = piorou (mais desperdício)
    return out


def detalhe_veiculo(base, tipo, ini=None, fim=None) -> pd.DataFrame:
    d = _acrescentar(oc.detalhe_veiculo(base, tipo, ini, fim))
    return d[["regiao", "veiculo", "cap_veiculo", "viagens", "prev", "real", "desp_vol", "desp"]]


def tendencia(base, tipo, freq="D", ate=None, janela=None) -> pd.DataFrame:
    """Mesma tabela da ocupação, com os percentuais invertidos (1 − ocupação) e a variação recalculada."""
    t = oc.tendencia(base, tipo, freq, ate, janela)
    if t.empty:
        return t
    t = t.copy()
    dados = list(t.columns[3:])
    t[t.columns[2]] = 1 - t[t.columns[2]]
    for c in dados:
        t[c] = 1 - t[c]
    t[t.columns[1]] = t[dados[-1]] - t[dados[-2]] if len(dados) >= 2 else float("nan")
    return t
