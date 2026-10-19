"""Leitura, tratamento e regras dos indicadores (sem Streamlit)."""
import pandas as pd

from . import periodos, textos as tx
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


def tabela_periodo(base: pd.DataFrame, tipo: str, evento: str, ini=None, fim=None) -> pd.DataFrame:
    """Equivalente às abas 集货/散货 封车/解车: previsto, realizado, taxa, meta e ranking por região.
    ini/fim = período (inclusive); None = "Todos": acumulado de todos os dias."""
    cfg = INDICADORES[(tipo, evento)]
    sub = base[base["tipo_linha"] == tipo]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim if fim is not None else ini))]
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


def tabela_dia(base: pd.DataFrame, tipo: str, evento: str, dia) -> pd.DataFrame:
    """Um dia só (ou None = todos). Mantido para os validadores."""
    return tabela_periodo(base, tipo, evento, dia, dia)


def comparar(atual: pd.DataFrame, comparada: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta à tabela do período a taxa do período comparado e a variação (em pontos percentuais,
    como fração: 0,0125 = +1,25 p.p.). Região sem dado no período comparado fica vazia."""
    taxa = comparada.set_index("regiao")["taxa"]
    out = atual.copy()
    out["taxa_comp"] = out["regiao"].map(taxa)
    out["variacao"] = out["taxa"] - out["taxa_comp"]
    return out


def rotular_tabela(tab: pd.DataFrame, tipo: str, evento: str) -> pd.DataFrame:
    cfg, rot = INDICADORES[(tipo, evento)], ROTULOS[evento]
    return tab.rename(columns={
        "n": "序号 Nº", "regiao": cfg["regiao_rot"], "prev": rot["prev"], "real": rot["real"],
        "taxa": rot["taxa"], "meta": "目标 Meta", "ranking": "排名 Ranking",
        "taxa_comp": tx.COL_COMP, "variacao": tx.COL_VAR})


def tendencia(base: pd.DataFrame, tipo: str, evento: str, freq: str = "D", ate=None, janela: int | None = None) -> pd.DataFrame:
    """Taxa por período (dia, semana, mês ou ano) e região + acumulado da janela + variação do último período
    contra o anterior. `ate` = último dia considerado (None = tudo)."""
    cfg = INDICADORES[(tipo, evento)]
    sub = base[base["tipo_linha"] == tipo]
    if ate is not None:
        sub = sub[sub["dia"] <= pd.Timestamp(ate)]
    if sub.empty:
        return pd.DataFrame()
    sub = sub.assign(per=periodos.inicio(sub["dia"], freq))
    recentes = sorted(sub["per"].unique())[-(janela or periodos.JANELA[freq]):]      # só os períodos mais recentes
    sub = sub[sub["per"].isin(recentes)]

    def taxa(df, chaves):
        g = df.groupby(chaves)[cfg["flag"]].agg(prev="size", real="sum")
        return (g["real"] / g["prev"]).rename("taxa")

    diaria = taxa(sub, [cfg["regiao_col"], "per"]).unstack("per")
    diaria.loc["合计 Total"] = taxa(sub, ["per"])
    acumulado = pd.concat([taxa(sub, [cfg["regiao_col"]]), pd.Series({"合计 Total": sub[cfg["flag"]].mean()})])

    out = diaria.copy()
    curtos = [periodos.rotulo_curto(d, freq) for d in out.columns]
    if len(set(curtos)) < len(curtos):                      # ex.: S41 de 2025 e de 2026 na mesma tabela
        curtos = [periodos.rotulo_curto(d, freq, com_ano=True) for d in out.columns]
    out.columns = curtos
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


def resumo(base: pd.DataFrame, tipo: str, evento: str, freq: str = "W", regional: str | None = None,
           ini=None, fim=None) -> pd.DataFrame:
    """Previsto, realizado e taxa por período (dia, semana ou mês) para uma regional (None = todas).
    Períodos sem nenhuma viagem entram com taxa vazia (lacuna visível no gráfico)."""
    cfg = INDICADORES[(tipo, evento)]
    sub = base[base["tipo_linha"] == tipo]
    if regional:
        sub = sub[sub[cfg["regiao_col"]] == regional]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim))]
    if sub.empty:
        return pd.DataFrame(columns=["inicio", "periodo", "prev", "real", "taxa", "meta", "variacao"])
    g = sub.groupby(periodos.inicio(sub["dia"], freq))[cfg["flag"]].agg(prev="size", real="sum")
    g = g.reindex(periodos.completos(g.index.min(), g.index.max(), freq), fill_value=0)
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    g["meta"] = METAS[evento]
    g["variacao"] = g["taxa"].diff()                       # contra o período anterior (vazio se ele não teve dado)
    anos = {d.year for d in g.index}
    g["periodo"] = [periodos.rotulo_curto(d, freq, com_ano=len(anos) > 1) for d in g.index]
    g.index.name = "inicio"
    return g.reset_index()[["inicio", "periodo", "prev", "real", "taxa", "meta", "variacao"]]


def regionais(base: pd.DataFrame, tipo: str, evento: str) -> list[str]:
    """Regionais que existem nos dados para o indicador (fixas da config + novas, ex.: SR)."""
    col = INDICADORES[(tipo, evento)]["regiao_col"]
    sub = base[base["tipo_linha"] == tipo]
    return [r for r in _regioes(sub, col) if (sub[col] == r).any()]
