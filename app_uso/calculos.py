"""Leitura, tratamento e cálculo da Taxa de Uso de APP (sem Streamlit).

Taxa = (check-outs feitos + check-ins feitos) / (viagens x 2).  Coleta agrupa pela regional de SAÍDA,
Entrega pela regional de CHEGADA; o dia é o da chegada planejada (igual à planilha do Lucas)."""
import pandas as pd

from comum import periodos
from . import textos as tx
from .config import COL, INDICADORES, META, ORDEM_TENDENCIA, PREVISTO_POR_VIAGEM, REGIOES, STATUS_VALIDOS, TRANSPORTADOR_EXCLUIDO, APOIO

TOTAL = "合计 Total"


# ---------- leitura ----------
def ler_relatorio(origem, sheet_name=0) -> pd.DataFrame:
    """Lê o relatório extraído (.xls que costuma ser xlsx). Só as colunas usadas."""
    precisa = set(COL.values())
    uso = lambda nome: str(nome).strip() in precisa or nome in precisa
    try:
        return pd.read_excel(origem, sheet_name=sheet_name, engine="openpyxl", usecols=uso)
    except Exception:
        if hasattr(origem, "seek"):
            origem.seek(0)
        return pd.read_excel(origem, sheet_name=sheet_name, engine="xlrd", usecols=uso)


def carregar_apoio() -> dict:
    return {"rotas_mesmo_sc": set(pd.read_csv(APOIO / "rotas_mesmo_sc.csv")["rota"].astype(str).str.strip())}


def _preenchido(s: pd.Series) -> pd.Series:
    return s.notna() & s.astype(str).str.strip().ne("")


def _limpo(s: pd.Series) -> pd.Series:
    """Texto sem espaços; vazio/nan vira NA (para poder preencher com o último valor conhecido)."""
    s = s.astype("string").str.strip()
    return s.mask(s.isin(["", "nan", "NaN", "None", "<NA>"]))


def tipos_do_arquivo(df: pd.DataFrame) -> dict:
    """{viagem: tipo de transportador} das linhas que têm o tipo preenchido (a última do arquivo vale).
    Guardado no banco ANTES do filtro de franqueado, para preencher tipos vazios em extrações futuras."""
    d = df[[COL["viagem"], COL["tipo_transportador"]]].copy()
    d.columns = ["viagem", "tipo"]
    d["viagem"], d["tipo"] = _limpo(d["viagem"]), _limpo(d["tipo"])
    d = d.dropna().drop_duplicates("viagem", keep="last")
    return dict(zip(d["viagem"], d["tipo"]))


# ---------- tratamento ----------
def preparar(df: pd.DataFrame, apoio: dict | None = None, tipos_conhecidos: dict | None = None, *,
             filtro_status=True, filtro_mesmo_sc=True, filtro_franqueado=True):
    """Retorna (base tratada, diagnóstico). `tipos_conhecidos` = {viagem: tipo} do último relatório."""
    apoio = apoio or carregar_apoio()
    faltando = [nome for nome in COL.values() if nome not in df.columns and nome != COL["condutor"]]
    if faltando:
        raise ValueError(tx.ERRO_COLUNAS + ", ".join(faltando))

    inverso = {nome: chave for chave, nome in COL.items()}
    b = df.reindex(columns=list(COL.values())).rename(columns=inverso).copy()
    b = b[b["id"].astype(str).str.strip().ne("任务单号")]            # linha de cabeçalho em chinês, se existir

    for c in ("status", "viagem", "partida", "reg_saida", "reg_chegada"):
        b[c] = b[c].astype(str).str.strip()
    b["tipo_linha"] = b["tipo_linha"].astype(str).str.strip().str.upper()
    b["tipo_transportador"] = _limpo(b["tipo_transportador"])
    b["condutor"] = b["condutor"].where(b["condutor"].notna(), "").astype(str).str.strip()
    b["chegada_plan"] = pd.to_datetime(b["chegada_plan"], errors="coerce")
    b["dia"] = b["chegada_plan"].dt.normalize()
    b["saiu_ok"] = _preenchido(b["hora_checkout"]).astype(int)
    b["chegou_ok"] = _preenchido(b["hora_checkin"]).astype(int)

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

    vazio = b["tipo_transportador"].isna()                        # transportador vazio: vale o do último relatório
    if vazio.any() and tipos_conhecidos:
        b.loc[vazio, "tipo_transportador"] = b.loc[vazio, "viagem"].map(tipos_conhecidos)
    diag[tx.DIAG["tipo_preenchido"]] = int(vazio.sum() - b["tipo_transportador"].isna().sum())
    diag[tx.DIAG["tipo_vazio"]] = int(b["tipo_transportador"].isna().sum())

    if filtro_franqueado:
        fr = b["tipo_transportador"].fillna("").str.startswith(TRANSPORTADOR_EXCLUIDO)
        diag[tx.DIAG["franqueado"]] = int(fr.sum())
        b = b[~fr]

    diag[tx.DIAG["usadas"]] = len(b)
    return b.reset_index(drop=True), diag


def calcular_partes(b: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta previsto (2 por viagem) e realizado (check-out + check-in)."""
    b = b.copy()
    b["n_prev"] = PREVISTO_POR_VIAGEM
    b["n_real"] = b["saiu_ok"] + b["chegou_ok"]
    return b


# ---------- indicadores ----------
def _regioes(base: pd.DataFrame, coluna: str) -> list[str]:
    """Regionais fixas + qualquer nova que apareça nos dados (o total sempre fecha com a soma das linhas)."""
    extras = sorted(r for r in base[coluna].dropna().unique() if r not in REGIOES and str(r).strip())
    return list(REGIOES) + extras


def _soma(sub: pd.DataFrame, chaves) -> pd.DataFrame:
    g = sub.groupby(chaves)[["n_prev", "n_real"]].sum()
    g["taxa"] = (g["n_real"] / g["n_prev"]).where(g["n_prev"] > 0)
    return g


def tabela_periodo(base: pd.DataFrame, tipo: str, ini=None, fim=None) -> pd.DataFrame:
    """Equivalente às abas Coleta汇总/Entrega汇总: previsto, realizado, taxa, meta e ranking por região."""
    col = INDICADORES[tipo]["regiao_col"]
    sub = base[base["tipo_linha"] == tipo]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim if fim is not None else ini))]
    g = sub.groupby(col)[["n_prev", "n_real"]].sum().reindex(_regioes(sub, col), fill_value=0)
    g.index.name = "regiao"
    g = g.reset_index().rename(columns={"n_prev": "prev", "n_real": "real"})
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    g["meta"] = META
    g["ranking"] = g["taxa"].fillna(0).rank(method="min", ascending=False).astype(int)
    g = g.sort_values(["ranking", "prev"], ascending=[True, False]).reset_index(drop=True)

    prev, real = int(g["prev"].sum()), int(g["real"].sum())
    total = pd.DataFrame([{"regiao": TOTAL, "prev": prev, "real": real,
                           "taxa": real / prev if prev else float("nan"), "meta": META, "ranking": None}])
    out = pd.concat([total, g], ignore_index=True)
    out.insert(0, "n", ["合计"] + list(range(1, len(g) + 1)))
    return out


def comparar(atual: pd.DataFrame, comparada: pd.DataFrame) -> pd.DataFrame:
    taxa = comparada.set_index("regiao")["taxa"]
    out = atual.copy()
    out["taxa_comp"] = out["regiao"].map(taxa)
    out["variacao"] = out["taxa"] - out["taxa_comp"]
    return out


def rotular_tabela(tab: pd.DataFrame, tipo: str) -> pd.DataFrame:
    return tab.rename(columns={
        "n": "序号 Nº", "regiao": INDICADORES[tipo]["regiao_rot"], "prev": tx.COL_PREV, "real": tx.COL_REAL,
        "taxa": tx.COL_TAXA, "meta": "目标 Meta", "ranking": "排名 Ranking",
        "taxa_comp": tx.COL_COMP, "variacao": tx.COL_VAR})


def tendencia(base: pd.DataFrame, tipo: str, freq: str = "D", ate=None, janela: int | None = None) -> pd.DataFrame:
    """Taxa por período e região + acumulado da janela + variação do último contra o anterior."""
    col = INDICADORES[tipo]["regiao_col"]
    sub = base[base["tipo_linha"] == tipo]
    if ate is not None:
        sub = sub[sub["dia"] <= pd.Timestamp(ate)]
    if sub.empty:
        return pd.DataFrame()
    sub = sub.assign(per=periodos.inicio(sub["dia"], freq))
    recentes = sorted(sub["per"].unique())[-(janela or periodos.JANELA[freq]):]
    sub = sub[sub["per"].isin(recentes)]

    diaria = _soma(sub, [col, "per"])["taxa"].unstack("per")
    diaria.loc[TOTAL] = _soma(sub, ["per"])["taxa"]
    acumulado = pd.concat([_soma(sub, [col])["taxa"], pd.Series({TOTAL: sub["n_real"].sum() / sub["n_prev"].sum()})])

    out = diaria.copy()
    curtos = [periodos.rotulo_curto(d, freq) for d in out.columns]
    if len(set(curtos)) < len(curtos):
        curtos = [periodos.rotulo_curto(d, freq, com_ano=True) for d in out.columns]
    out.columns = curtos
    out.insert(0, "环比 Variação±", out.iloc[:, -1] - out.iloc[:, -2] if out.shape[1] >= 2 else float("nan"))
    out.insert(1, "累计 Acumulado", acumulado.reindex(out.index))
    resto = sorted(r for r in out.index if r not in ORDEM_TENDENCIA and r != TOTAL)
    ordem = [TOTAL] + [r for r in ORDEM_TENDENCIA if r in out.index] + resto
    out = out.loc[ordem]
    out.index.name = INDICADORES[tipo]["regiao_rot"]
    return out.reset_index()


def resumo(base: pd.DataFrame, tipo: str, freq: str = "W", regional: str | None = None, ini=None, fim=None) -> pd.DataFrame:
    """Previsto, realizado e taxa por período (dia, semana ou mês) para uma regional (None = todas)."""
    col = INDICADORES[tipo]["regiao_col"]
    sub = base[base["tipo_linha"] == tipo]
    if regional:
        sub = sub[sub[col] == regional]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim))]
    if sub.empty:
        return pd.DataFrame(columns=["inicio", "periodo", "prev", "real", "taxa", "meta", "variacao"])
    g = sub.groupby(periodos.inicio(sub["dia"], freq))[["n_prev", "n_real"]].sum().rename(columns={"n_prev": "prev", "n_real": "real"})
    g = g.reindex(periodos.completos(g.index.min(), g.index.max(), freq), fill_value=0)
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    g["meta"] = META
    g["variacao"] = g["taxa"].diff()
    anos = {d.year for d in g.index}
    g["periodo"] = [periodos.rotulo_curto(d, freq, com_ano=len(anos) > 1) for d in g.index]
    g.index.name = "inicio"
    return g.reset_index()[["inicio", "periodo", "prev", "real", "taxa", "meta", "variacao"]]


def resumo_regionais(base: pd.DataFrame, tipo: str, freq: str, ini=None, fim=None) -> pd.DataFrame:
    """Uma linha por regional x período (para o mapa de calor). Colunas: regiao, periodo, inicio, prev, real, taxa."""
    col = INDICADORES[tipo]["regiao_col"]
    sub = base[base["tipo_linha"] == tipo]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim))]
    if sub.empty:
        return pd.DataFrame(columns=["regiao", "inicio", "periodo", "prev", "real", "taxa"])
    sub = sub.assign(inicio=periodos.inicio(sub["dia"], freq))
    g = sub.groupby([col, "inicio"])[["n_prev", "n_real"]].sum().rename(columns={"n_prev": "prev", "n_real": "real"}).reset_index()
    g = g.rename(columns={col: "regiao"})
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    anos = {d.year for d in g["inicio"]}
    g["periodo"] = [periodos.rotulo_curto(d, freq, com_ano=len(anos) > 1) for d in g["inicio"]]
    return g


def regionais(base: pd.DataFrame, tipo: str) -> list[str]:
    col = INDICADORES[tipo]["regiao_col"]
    sub = base[base["tipo_linha"] == tipo]
    return [r for r in _regioes(sub, col) if (sub[col] == r).any()]
