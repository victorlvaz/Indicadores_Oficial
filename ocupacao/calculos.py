"""Leitura, tratamento e cálculo da Taxa de Ocupação (sem Streamlit).

Ocupação = volume carregado (nº de pedidos mãe do veículo) / capacidade do veículo (票数), somando por regional de ORIGEM.
A ocupação de cada regional (ou tipo de veículo) é limitada a 100%, como na planilha: MIN(carregado/previsto; 100%).
O dia é o do horário planejado de saída."""
import pandas as pd

from comum import periodos
from . import config as cfg, textos as tx
from .config import CAPACIDADE, COL, COL_OPCIONAIS, INDICADORES, META, PEDIDO_MAE_REMOVER, REGIOES, STATUS_VALIDOS, TRANSPORTADOR_EXCLUIDO

TOTAL = "总合计 Total"


# ---------- leitura ----------
def ler_relatorio(origem, sheet_name=0) -> pd.DataFrame:
    """Lê o relatório (.xls que costuma ser xlsx). Só as colunas usadas: Km Google e CHECK-IN já ficam de fora."""
    nomes = {n for lst in COL.values() for n in lst}
    uso = lambda nome: str(nome).strip() in nomes
    try:
        return pd.read_excel(origem, sheet_name=sheet_name, engine="openpyxl", usecols=uso)
    except Exception:
        if hasattr(origem, "seek"):
            origem.seek(0)
        return pd.read_excel(origem, sheet_name=sheet_name, engine="xlrd", usecols=uso)


def carregar_apoio() -> dict:
    return {"rotas_mesmo_sc": set(pd.read_csv(cfg.APOIO / "rotas_mesmo_sc.csv")["rota"].astype(str).str.strip())}


def _achar_colunas(df: pd.DataFrame) -> dict:
    escolhidas, faltando = {}, []
    for chave, nomes in COL.items():
        nome = next((n for n in nomes if n in df.columns), None)
        if nome:
            escolhidas[chave] = nome
        elif chave not in COL_OPCIONAIS:
            faltando.append(nomes[0])
    if faltando:
        raise ValueError(tx.ERRO_COLUNAS + ", ".join(faltando))
    return escolhidas


# ---------- tratamento ----------
def preparar(df: pd.DataFrame, apoio: dict | None = None, *, filtro_status=True, filtro_mesmo_sc=True,
             filtro_franqueado=True, filtro_pedido_mae=True):
    """Retorna (base tratada, diagnóstico). Coleta e Entrega vêm juntas no mesmo arquivo."""
    apoio = apoio or carregar_apoio()
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    cols = _achar_colunas(df)
    b = df[list(cols.values())].rename(columns={v: k for k, v in cols.items()})
    if "placa" not in b.columns:
        b["placa"] = ""
    if "condutor" not in b.columns:
        b["condutor"] = ""

    for c in ("id", "status", "viagem", "tipo_transportador", "condutor", "partida", "reg_origem", "veiculo"):
        b[c] = b[c].fillna("").astype(str).str.strip()
    b["id"] = b["id"].str.upper()
    b = b[b["id"].ne("") & b["id"].ne("NAN")]
    b["tipo_linha"] = b["tipo_linha"].astype(str).str.strip().str.upper()
    b["saida_plan"] = pd.to_datetime(b["saida_plan"], errors="coerce", format="mixed")
    b["dia"] = b["saida_plan"].dt.normalize()
    b["volume"] = pd.to_numeric(b["volume"], errors="coerce")
    b["veiculo"] = b["veiculo"].str.upper().replace({"NAN": ""})

    diag = {tx.DIAG["lidas"]: len(b)}
    sem = b["dia"].isna() | ~b["tipo_linha"].isin(INDICADORES)
    diag[tx.DIAG["sem_data"]] = int(sem.sum())
    b = b[~sem]

    if filtro_status:
        ok = b["status"].str.startswith(STATUS_VALIDOS)
        diag[tx.DIAG["status"]] = int((~ok).sum())
        b = b[ok]
    if filtro_mesmo_sc:
        sc = b["viagem"].isin(apoio["rotas_mesmo_sc"])
        diag[tx.DIAG["mesmo_sc"]] = int(sc.sum())
        b = b[~sc]
    if filtro_franqueado:
        fr = b["tipo_transportador"].str.startswith(TRANSPORTADOR_EXCLUIDO)
        diag[tx.DIAG["franqueado"]] = int(fr.sum())
        b = b[~fr]
    if filtro_pedido_mae:
        ruim = pd.Series(False, index=b.index)
        for t, regras in PEDIDO_MAE_REMOVER.items():
            m = b["tipo_linha"] == t
            if "vazio" in regras:
                ruim |= m & b["volume"].isna()
            if "zero_um" in regras:
                ruim |= m & (b["volume"] < 2)
        diag[tx.DIAG["pedido_mae"]] = int(ruim.sum())
        b = b[~ruim]

    sem_cap = ~b["veiculo"].isin(CAPACIDADE)
    diag[tx.DIAG["sem_capacidade"]] = int(sem_cap.sum())
    diag[tx.DIAG["usadas"]] = len(b)
    return b.reset_index(drop=True), diag


def completar(b: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta capacidade (票数 do tipo de veículo) e volume carregado sem vazios. Chamado depois de ler o histórico."""
    b = b.copy()
    b["capacidade"] = b["veiculo"].map(CAPACIDADE).fillna(0).astype(float)
    b["carregado"] = b["volume"].fillna(0).astype(float)
    return b


# ---------- indicadores ----------
def _regioes(sub: pd.DataFrame) -> list[str]:
    extras = sorted(r for r in sub["reg_origem"].dropna().unique() if r not in REGIOES and str(r).strip())
    return list(REGIOES) + extras


def _taxa(real, prev):
    """Ocupação limitada a 100% (como a planilha). Sem capacidade -> vazio."""
    t = (real / prev).where(prev > 0) if hasattr(prev, "where") else (real / prev if prev else float("nan"))
    return t.clip(upper=1) if hasattr(t, "clip") else min(t, 1.0)


def _recorte(base, tipo, ini=None, fim=None):
    sub = base[base["tipo_linha"] == tipo]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim if fim is not None else ini))]
    return sub


def tabela_periodo(base: pd.DataFrame, tipo: str, ini=None, fim=None) -> pd.DataFrame:
    """Tabela consolidada (topo da aba da planilha): viagens, volume previsto (capacidade), carregado e ocupação por regional."""
    sub = _recorte(base, tipo, ini, fim)
    g = sub.groupby("reg_origem").agg(viagens=("id", "size"), prev=("capacidade", "sum"), real=("carregado", "sum"))
    g = g.reindex(_regioes(sub), fill_value=0)
    g.index.name = "regiao"
    g = g.reset_index()
    g["taxa"] = _taxa(g["real"], g["prev"])
    g["ranking"] = g["taxa"].fillna(0).rank(method="min", ascending=False).astype(int)
    g = g.sort_values(["ranking", "viagens"], ascending=[True, False]).reset_index(drop=True)
    v, p, r = int(g["viagens"].sum()), float(g["prev"].sum()), float(g["real"].sum())
    total = pd.DataFrame([{"regiao": TOTAL, "viagens": v, "prev": p, "real": r,
                           "taxa": min(r / p, 1.0) if p else float("nan"), "ranking": None}])
    out = pd.concat([total, g], ignore_index=True)
    out.insert(0, "n", ["合计"] + list(range(1, len(g) + 1)))
    return out


def detalhe_veiculo(base: pd.DataFrame, tipo: str, ini=None, fim=None) -> pd.DataFrame:
    """Tabela detalhada da planilha: por regional, uma linha Total e uma por tipo de veículo (só os que tiveram viagens).
    Colunas: regiao, veiculo, viagens, prev, real, taxa, cap_veiculo."""
    sub = _recorte(base, tipo, ini, fim)
    ordem_veic = sorted(CAPACIDADE, key=CAPACIDADE.get)
    linhas = []

    def linha(reg, veic, s):
        p, r = float(s["capacidade"].sum()), float(s["carregado"].sum())
        return {"regiao": reg, "veiculo": veic, "viagens": len(s), "prev": p, "real": r,
                "taxa": min(r / p, 1.0) if p else float("nan"), "cap_veiculo": CAPACIDADE.get(veic) if veic != "Total" else None}

    linhas.append(linha(TOTAL, "Total", sub))
    for reg in _regioes(sub):
        s = sub[sub["reg_origem"] == reg]
        if s.empty:
            continue
        linhas.append(linha(reg, "Total", s))
        presentes = list(s["veiculo"].unique())
        for v in [x for x in ordem_veic if x in presentes] + sorted(x for x in presentes if x not in CAPACIDADE):
            linhas.append(linha(reg, v if v else "(?)", s[s["veiculo"] == v]))
    return pd.DataFrame(linhas)


def por_veiculo(base: pd.DataFrame, tipo: str, ini=None, fim=None, regional: str | None = None) -> pd.DataFrame:
    sub = _recorte(base, tipo, ini, fim)
    if regional:
        sub = sub[sub["reg_origem"] == regional]
    g = sub.groupby("veiculo").agg(viagens=("id", "size"), prev=("capacidade", "sum"), real=("carregado", "sum")).reset_index()
    g["taxa"] = _taxa(g["real"], g["prev"])
    g["veiculo"] = g["veiculo"].replace("", "(?)")
    return g.sort_values("viagens", ascending=False).reset_index(drop=True)


def comparar(atual: pd.DataFrame, comparada: pd.DataFrame) -> pd.DataFrame:
    taxa = comparada.set_index("regiao")["taxa"]
    out = atual.copy()
    out["taxa_comp"] = out["regiao"].map(taxa)
    out["variacao"] = out["taxa"] - out["taxa_comp"]
    return out


def rotular_tabela(tab: pd.DataFrame) -> pd.DataFrame:
    return tab.rename(columns={"n": "序号 Nº", "regiao": tx.COL_REGIAO, "viagens": tx.COL_VIAGENS, "prev": tx.COL_PREV,
                               "real": tx.COL_REAL, "taxa": tx.COL_TAXA, "ranking": "排名 Ranking",
                               "taxa_comp": tx.COL_COMP, "variacao": tx.COL_VAR})


def tendencia(base: pd.DataFrame, tipo: str, freq: str = "D", ate=None, janela: int | None = None) -> pd.DataFrame:
    sub = base[base["tipo_linha"] == tipo]
    if ate is not None:
        sub = sub[sub["dia"] <= pd.Timestamp(ate)]
    if sub.empty:
        return pd.DataFrame()
    sub = sub.assign(per=periodos.inicio(sub["dia"], freq))
    recentes = sorted(sub["per"].unique())[-(janela or periodos.JANELA[freq]):]
    sub = sub[sub["per"].isin(recentes)]

    def taxa(chaves):
        g = sub.groupby(chaves)[["capacidade", "carregado"]].sum()
        return (g["carregado"] / g["capacidade"]).where(g["capacidade"] > 0).clip(upper=1)

    diaria = taxa(["reg_origem", "per"]).unstack("per")
    diaria.loc[TOTAL] = taxa(["per"])
    acum = pd.concat([taxa(["reg_origem"]), pd.Series({TOTAL: min(sub["carregado"].sum() / sub["capacidade"].sum(), 1.0)
                                                      if sub["capacidade"].sum() else float("nan")})])
    out = diaria.copy()
    curtos = [periodos.rotulo_curto(d, freq) for d in out.columns]
    if len(set(curtos)) < len(curtos):
        curtos = [periodos.rotulo_curto(d, freq, com_ano=True) for d in out.columns]
    out.columns = curtos
    out.insert(0, "环比 Variação±", out.iloc[:, -1] - out.iloc[:, -2] if out.shape[1] >= 2 else float("nan"))
    out.insert(1, "累计 Acumulado", acum.reindex(out.index))
    ordem = [TOTAL] + [r for r in _regioes(sub) if r in out.index]
    out = out.loc[ordem]
    out.index.name = tx.COL_REGIAO
    return out.reset_index()


def resumo(base: pd.DataFrame, tipo: str, freq: str = "W", regional: str | None = None, ini=None, fim=None) -> pd.DataFrame:
    sub = base[base["tipo_linha"] == tipo]
    if regional:
        sub = sub[sub["reg_origem"] == regional]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim))]
    cols = ["inicio", "periodo", "viagens", "prev", "real", "taxa", "variacao"]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    g = sub.groupby(periodos.inicio(sub["dia"], freq)).agg(viagens=("id", "size"), prev=("capacidade", "sum"), real=("carregado", "sum"))
    g = g.reindex(periodos.completos(g.index.min(), g.index.max(), freq), fill_value=0)
    g["taxa"] = _taxa(g["real"], g["prev"])
    g["variacao"] = g["taxa"].diff()
    anos = {d.year for d in g.index}
    g["periodo"] = [periodos.rotulo_curto(d, freq, com_ano=len(anos) > 1) for d in g.index]
    g.index.name = "inicio"
    return g.reset_index()[cols]


def regionais(base: pd.DataFrame, tipo: str) -> list[str]:
    sub = base[base["tipo_linha"] == tipo]
    return [r for r in _regioes(sub) if (sub["reg_origem"] == r).any()]
