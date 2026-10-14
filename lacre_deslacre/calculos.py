"""Leitura, tratamento e regras dos indicadores (sem Streamlit)."""
import pandas as pd

from . import textos as tx
from .config import (APOIO, COL, INDICADORES, METAS, PEDIDO_MAE_MINIMO, ORDEM_TENDENCIA, REGIOES, ROTULOS,
                    STATUS_VALIDOS, TRANSPORTADOR_EXCLUIDO)


# ---------- leitura ----------
def ler_relatorio(origem, sheet_name=0) -> pd.DataFrame:
    """Lê o relatório extraído. O arquivo vem com extensão .xls mas costuma ser xlsx."""
    precisa = set(COL.values())              # só as colunas usadas: lê bem mais rápido e ocupa menos memória
    uso = lambda nome: str(nome).strip() in precisa or nome in precisa
    try:
        return pd.read_excel(origem, sheet_name=sheet_name, engine="openpyxl", usecols=uso)
    except Exception:
        if hasattr(origem, "seek"):
            origem.seek(0)
        return pd.read_excel(origem, sheet_name=sheet_name, engine="xlrd", usecols=uso)


def carregar_apoio() -> dict:
    return {
        "pontos_coleta": set(pd.read_csv(APOIO / "pontos_coleta.csv")["estacao"].astype(str).str.strip()),
        "rotas_mesmo_sc": set(pd.read_csv(APOIO / "rotas_mesmo_sc.csv")["rota"].astype(str).str.strip()),
    }


def _preenchido(s: pd.Series) -> pd.Series:
    return s.notna() & s.astype(str).str.strip().ne("")


# ---------- tratamento ----------
def preparar(df: pd.DataFrame, apoio: dict | None = None, *, filtro_status=True,
             filtro_mesmo_sc=True, filtro_ponto_coleta=True,
             filtro_franqueado=True, filtro_pedido_mae=True):
    """Retorna (base tratada, diagnóstico de linhas removidas por regra)."""
    apoio = apoio or carregar_apoio()
    faltando = [nome for nome in COL.values() if nome not in df.columns]
    if faltando:
        raise ValueError(tx.ERRO_COLUNAS + ", ".join(faltando))

    inverso = {nome: chave for chave, nome in COL.items()}
    b = df[list(COL.values())].rename(columns=inverso).copy()
    b = b[b["id"].astype(str).str.strip().ne("任务单号")]          # linha de cabeçalho em chinês, se existir

    for c in ("status", "viagem", "partida", "reg_saida", "reg_chegada", "tipo_transportador"):
        b[c] = b[c].astype(str).str.strip()
    b["tipo_linha"] = b["tipo_linha"].astype(str).str.strip().str.upper()
    b["chegada_plan"] = pd.to_datetime(b["chegada_plan"], errors="coerce")
    b["dia"] = b["chegada_plan"].dt.normalize()
    b["pedido_mae"] = pd.to_numeric(b["pedido_mae"], errors="coerce")
    b["lacrado"] = _preenchido(b["hora_lacre"]).astype(int)
    b["deslacrado"] = _preenchido(b["hora_deslacre"]).astype(int)

    diag = {tx.DIAG["lidas"]: len(b)}
    sem_data = b["dia"].isna()
    diag[tx.DIAG["sem_data"]] = int(sem_data.sum())
    b = b[~sem_data]

    if filtro_status:
        ok = b["status"].str.startswith(STATUS_VALIDOS)
        diag[tx.DIAG["status"]] = int((~ok).sum())
        b = b[ok]
    if filtro_mesmo_sc:
        sc = b["viagem"].isin(apoio["rotas_mesmo_sc"])
        diag[tx.DIAG["mesmo_sc"]] = int(sc.sum())
        b = b[~sc]
    if filtro_ponto_coleta:
        fora = (b["tipo_linha"] == "COLETA") & ~b["partida"].isin(apoio["pontos_coleta"])
        diag[tx.DIAG["ponto_coleta"]] = int(fora.sum())
        b = b[~fora]

    if filtro_franqueado:
        fr = b["tipo_transportador"].str.startswith(TRANSPORTADOR_EXCLUIDO)
        diag[tx.DIAG["franqueado"]] = int(fr.sum())
        b = b[~fr]
    if filtro_pedido_mae:
        ruim = b["pedido_mae"].isna() | (b["pedido_mae"] < PEDIDO_MAE_MINIMO)
        diag[tx.DIAG["pedido_mae"]] = int(ruim.sum())
        b = b[~ruim]

    diag[tx.DIAG["usadas"]] = len(b)
    return b.reset_index(drop=True), diag


def juntar_relatorios(bases: list[pd.DataFrame]) -> pd.DataFrame:
    """Empilha extrações de vários dias; em caso de repetição vale a mais recente."""
    todas = pd.concat(bases, ignore_index=True)
    chave = ["id", "cod_chegada", "chegada_plan"]
    return todas.drop_duplicates(subset=chave, keep="last").reset_index(drop=True)


# ---------- indicadores ----------
def _regioes(base: pd.DataFrame, coluna: str) -> list[str]:
    """Regiões fixas da config + qualquer região nova (ex.: SR) que apareça nos dados.
    Assim nenhuma linha some da tabela e o total sempre fecha com a soma das linhas."""
    extras = sorted(r for r in base[coluna].dropna().unique() if r not in REGIOES and str(r).strip())
    return list(REGIOES) + extras


def tabela_dia(base: pd.DataFrame, tipo: str, evento: str, dia) -> pd.DataFrame:
    """Equivalente às abas 集货/散货 封车/解车: previsto, realizado, taxa, meta e ranking por região."""
    cfg = INDICADORES[(tipo, evento)]
    sub = base[base["tipo_linha"] == tipo]
    if dia is not None:                      # None = "Todos": acumulado de todos os dias
        sub = sub[sub["dia"] == pd.Timestamp(dia)]
    g = sub.groupby(cfg["regiao_col"])[cfg["flag"]].agg(prev="size", real="sum").reindex(_regioes(sub, cfg["regiao_col"]), fill_value=0)
    g.index.name = "regiao"
    g = g.reset_index()
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    g["meta"] = METAS[evento]
    g["ranking"] = g["taxa"].fillna(0).rank(method="min", ascending=False).astype(int)
    g = g.sort_values(["ranking", "prev"], ascending=[True, False]).reset_index(drop=True)

    prev, real = int(g["prev"].sum()), int(g["real"].sum())
    total = pd.DataFrame([{"regiao": "合计 Total", "prev": prev, "real": real,
                           "taxa": real / prev if prev else float("nan"),
                           "meta": METAS[evento], "ranking": None}])
    out = pd.concat([total, g], ignore_index=True)
    out.insert(0, "n", ["合计"] + list(range(1, len(g) + 1)))
    return out


def rotular_tabela(tab: pd.DataFrame, tipo: str, evento: str) -> pd.DataFrame:
    cfg, rot = INDICADORES[(tipo, evento)], ROTULOS[evento]
    return tab.rename(columns={
        "n": "序号 Nº", "regiao": cfg["regiao_rot"], "prev": rot["prev"], "real": rot["real"],
        "taxa": rot["taxa"], "meta": "目标 Meta", "ranking": "排名 Ranking"})


def tendencia(base: pd.DataFrame, tipo: str, evento: str) -> pd.DataFrame:
    """Taxa diária por região + acumulado do período + variação do último dia vs. anterior."""
    cfg = INDICADORES[(tipo, evento)]
    sub = base[base["tipo_linha"] == tipo]
    if sub.empty:
        return pd.DataFrame()

    def taxa(df, chaves):
        g = df.groupby(chaves)[cfg["flag"]].agg(prev="size", real="sum")
        return (g["real"] / g["prev"]).rename("taxa")

    diaria = taxa(sub, [cfg["regiao_col"], "dia"]).unstack("dia")
    diaria.loc["合计 Total"] = taxa(sub, ["dia"])
    acumulado = pd.concat([taxa(sub, [cfg["regiao_col"]]), pd.Series({"合计 Total": sub[cfg["flag"]].mean()})])

    out = diaria.copy()
    out.columns = [d.strftime("%d/%m") for d in out.columns]
    if out.shape[1] >= 2:
        out.insert(0, "环比 Variação±", out.iloc[:, -1] - out.iloc[:, -2])
    else:
        out.insert(0, "环比 Variação±", float("nan"))
    out.insert(1, "累计 Acumulado", acumulado.reindex(out.index))
    fixas = ORDEM_TENDENCIA[tipo]
    resto = sorted(r for r in out.index if r not in fixas and r not in ("合计 Total", "SR"))
    ordem = ["合计 Total"] + [r for r in fixas if r in out.index] + (["SR"] if "SR" in out.index else []) + resto
    out = out.loc[ordem]
    out.index.name = cfg["regiao_rot"]
    return out.reset_index()
