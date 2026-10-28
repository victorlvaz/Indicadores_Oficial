"""Leitura, tratamento e cálculo da Taxa de Chegada e da Taxa de Saída (sem Streamlit).

Cada linha do relatório consolidado é um TRECHO (uma viagem pode ter vários).
Chegada pontual = chegada real <= chegada planejada.  Saída pontual = saída real <= saída planejada.
Sem horário real = atraso (a menos que o horário planejado ainda não tenha chegado na hora da extração).
O dia é o da operação (começa às 08:00): horário planejado - 8 h.  Coleta agrupa pela regional de SAÍDA,
Entrega pela regional de CHEGADA (igual às planilhas).  A linha de total é a MÉDIA das taxas das regionais,
como na planilha; a taxa de cada regional é ponderada pelo número de trechos."""
import pandas as pd

from comum import original

from comum import periodos
from . import textos as tx
from .config import APOIO, COL, IND, PEDIDO_MAE_MINIMO, PEDIDO_MAE_NOMES, TRANSPORTADOR_EXCLUIDO, INICIO_DIA_HORAS, META, ORDEM_TENDENCIA, REGIOES, STATUS_VALIDOS, TIPOS

TOTAL = "合计 Total"


# ---------- leitura ----------
def ler_relatorio(origem, sheet_name=0) -> pd.DataFrame:
    """Lê o relatório consolidado (.xls que costuma ser xlsx). Só as colunas usadas."""
    precisa = set(COL.values())
    uso = lambda nome: str(nome).strip() in precisa or nome in precisa
    try:
        return pd.read_excel(origem, sheet_name=sheet_name, engine="openpyxl")
    except Exception:
        if hasattr(origem, "seek"):
            origem.seek(0)
        return pd.read_excel(origem, sheet_name=sheet_name, engine="xlrd")


# ---------- tratamento ----------
def _chave(b: pd.DataFrame) -> pd.DataFrame:
    return b[["id", "cod_partida", "cod_chegada", "saida_plan"]]


def carregar_apoio() -> dict:
    return {"rotas_mesmo_sc": set(pd.read_csv(APOIO / "rotas_mesmo_sc.csv")["rota"].astype(str).str.strip()),
            "pontos_coleta": set(pd.read_csv(APOIO / "pontos_coleta.csv")["estacao"].astype(str).str.strip())}


def preparar(df: pd.DataFrame, apoio: dict | None = None, *, filtro_mesmo_sc=True, filtro_franqueado=True,
             filtro_pedido_mae=True, filtro_ponto_coleta=True, original_df: pd.DataFrame | None = None):
    """Retorna (base tratada, diagnóstico, chaves dos trechos descartados por regra).
    Regras iguais às dos outros relatórios JMS: status, Franqueado, pedido mãe vazio/0/1 e rota do mesmo SC."""
    apoio = apoio or carregar_apoio()
    col_pm = next((n for n in PEDIDO_MAE_NOMES if n in df.columns), None)
    if filtro_pedido_mae and col_pm is None:
        raise ValueError(tx.ERRO_COLUNAS + PEDIDO_MAE_NOMES[0])
    faltando = [nome for nome in COL.values() if nome not in df.columns]
    if faltando:
        raise ValueError(tx.ERRO_COLUNAS + ", ".join(faltando))

    inverso = {nome: chave for chave, nome in COL.items()}
    b = df[list(COL.values())].rename(columns=inverso).copy()
    b["pedido_mae"] = pd.to_numeric(df[col_pm], errors="coerce").reindex(b.index) if col_pm else float("nan")
    b = b[b["id"].astype(str).str.strip().ne("任务单号")]            # cabeçalho em chinês, se existir
    b["_dia_ref"] = pd.to_datetime(df["__dia_ref"].reindex(b.index), errors="coerce") if "__dia_ref" in df.columns else pd.NaT
    b["_sa"] = (df["__sem_apoio"].reindex(b.index).fillna(False).astype(bool) if "__sem_apoio" in df.columns
                else pd.Series(False, index=b.index))                # extract novo: trecho que não está no consolidado de apoio

    for c in ("id", "status", "viagem", "partida", "chegada", "reg_saida", "reg_chegada", "cod_partida", "cod_chegada", "tipo_transportador"):
        b[c] = b[c].astype("string").str.strip()
    b["cod_partida"] = b["cod_partida"].str.replace(r"\.0$", "", regex=True)
    b["cod_chegada"] = b["cod_chegada"].str.replace(r"\.0$", "", regex=True)
    b["tipo_linha"] = b["tipo_linha"].astype(str).str.strip().str.upper()
    for c in ("saida_plan", "saida_real", "chegada_plan", "chegada_real"):
        b[c] = pd.to_datetime(b[c], errors="coerce")

    diag = {tx.DIAG["lidas"]: len(b)}
    sem = b["saida_plan"].isna() | b["chegada_plan"].isna()
    diag[tx.DIAG["sem_data"]] = int(sem.sum())
    b = b[~sem]

    valido = b["status"].str.startswith(STATUS_VALIDOS).fillna(False) | b["_sa"]
    diag[tx.DIAG["status"]] = int((~valido).sum())
    descartadas = _chave(b[~valido]).copy()
    b = b[valido].copy()

    # regras comuns (as linhas removidas entram em `descartadas` para sair do histórico ao salvar)
    regras = []
    if filtro_mesmo_sc:
        regras.append(("mesmo_sc", b["viagem"].isin(apoio["rotas_mesmo_sc"])))
    if filtro_ponto_coleta:        # ponto de coleta = base do cliente: sai da Coleta
        regras.append(("ponto_coleta", (b["tipo_linha"] == "COLETA") & b["partida"].isin(apoio["pontos_coleta"])))
    if filtro_franqueado:
        regras.append(("franqueado", b["tipo_transportador"].fillna("").str.startswith(TRANSPORTADOR_EXCLUIDO) & ~b["_sa"]))
    if filtro_pedido_mae:
        regras.append(("pedido_mae", (b["pedido_mae"].isna() | (b["pedido_mae"] < PEDIDO_MAE_MINIMO)) & ~b["_sa"]))
    for nome, cond in regras:
        cond = cond.reindex(b.index).fillna(False)
        diag[tx.DIAG[nome]] = int(cond.sum())
        descartadas = pd.concat([descartadas, _chave(b[cond])], ignore_index=True)
        b = b[~cond].copy()

    antes = len(b)
    b = b.drop_duplicates(subset=["id", "cod_partida", "cod_chegada", "saida_plan"], keep="last")
    diag[tx.DIAG["duplicadas"]] = antes - len(b)

    # momento da extração = o último horário real do arquivo; o que ainda não venceu não é atraso
    momento = pd.concat([b["saida_real"], b["chegada_real"]]).max()
    b = calcular(b, momento)
    if b["_dia_ref"].notna().any():                    # extract novo: a coluna Data manda no dia (Chegada e Saída)
        b["dia_chegada"] = b["_dia_ref"].fillna(b["dia_chegada"])
        b["dia_saida"] = b["_dia_ref"].fillna(b["dia_saida"])
    diag[tx.DIAG["futuro_chegada"]] = int(b["aberto_chegada"].sum())
    diag[tx.DIAG["futuro_saida"]] = int(b["aberto_saida"].sum())
    if b["_sa"].any():
        diag[tx.DIAG["sem_apoio"]] = int(b["_sa"].sum())
    diag[tx.DIAG["usadas"]] = len(b)
    b = b.drop(columns=["pedido_mae", "_sa", "_dia_ref"])
    b = original.anexar(b, df if original_df is None else original_df)    # linha original (no extract novo: com as colunas de apoio)                          # linha original do JMS (todas as colunas) para a base exportada
    return b.reset_index(drop=True), diag, descartadas


# ---------- extract novo (sem status, tipo de transportador e pedido mãe) ----------
COL_EXTRACT = {
    "id": ("Número do ID",), "viagem": ("Nome da viagem",), "tipo_linha": ("Tipo de linha",),
    "cod_partida": ("Código de estação de partida",), "partida": ("Nome de estação de partida",),
    "reg_saida": ("Nome regional partida",), "cod_chegada": ("Código de estação de chegada",),
    "chegada": ("Nome de estação de chegada",), "reg_chegada": ("Nome regional chegada",),
    "saida_plan": ("Hora de partida planejada", "Horario de Saída planejada"),
    "saida_real": ("Horário real de saída",), "chegada_plan": ("Previsão de chegada",),
    "chegada_real": ("Tempo real de chegada",),
}


def eh_extract(df: pd.DataFrame) -> bool:
    """Extract novo do JMS: tem "Previsão de chegada" e "Pontual na chegada", mas não o Status do consolidado."""
    return {"Previsão de chegada", "Pontual na chegada"} <= set(df.columns) and COL["status"] not in df.columns


def _cod(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def preparar_extract(df: pd.DataFrame, apoio_df: pd.DataFrame | None, apoio: dict | None = None, **regras):
    """Mesmo resultado de `preparar`, a partir do extract novo. O consolidado (apoio_df) só serve para achar, por
    ID + estação de chegada, o Status, o Tipo de transportador e o Pedido mãe; os números vêm do extract.
    Trecho que não está no consolidado é mantido (e contado no diagnóstico)."""
    if apoio_df is None or apoio_df.empty:
        raise ValueError(tx.ERRO_SEM_APOIO)
    col_pm = next((n for n in PEDIDO_MAE_NOMES if n in apoio_df.columns), None)
    falta = [COL[k] for k in ("id", "cod_chegada", "status", "tipo_transportador") if COL[k] not in apoio_df.columns]
    if col_pm is None or falta:
        raise ValueError(tx.ERRO_COLUNAS_APOIO + ", ".join(falta + ([PEDIDO_MAE_NOMES[0]] if col_pm is None else [])))
    ps = pd.DataFrame(index=df.index)
    for chave, nomes in COL_EXTRACT.items():
        nome = next((n for n in nomes if n in df.columns), None)
        if nome is None:
            raise ValueError(tx.ERRO_COLUNAS + nomes[0])
        ps[COL[chave]] = df[nome]
    ap = pd.DataFrame({"_id": _cod(apoio_df[COL["id"]]), "_cod": _cod(apoio_df[COL["cod_chegada"]]),
                       COL["status"]: apoio_df[COL["status"]].values, COL["tipo_transportador"]: apoio_df[COL["tipo_transportador"]].values,
                       PEDIDO_MAE_NOMES[0]: apoio_df[col_pm].values}).drop_duplicates(["_id", "_cod"], keep="last")
    chave = pd.DataFrame({"_id": _cod(ps[COL["id"]]), "_cod": _cod(ps[COL["cod_chegada"]])}, index=ps.index)
    m = chave.merge(ap, on=["_id", "_cod"], how="left", indicator=True)
    m.index = ps.index
    for c in (COL["status"], COL["tipo_transportador"], PEDIDO_MAE_NOMES[0]):
        ps[c] = m[c]
    ps["__sem_apoio"] = m["_merge"].ne("both")
    if "Data" in df.columns:        # a 1ª coluna do extract (Data) é o dia da operação: vale para Chegada e Saída
        ps["__dia_ref"] = pd.to_datetime(df["Data"], errors="coerce").dt.normalize()
    raw = df.copy()                       # base exportada = idêntica ao "Exportação de detalhes" (sem colunas a mais)
    b, diag, descartadas = preparar(ps, apoio, original_df=raw, **regras)
    return b, diag, descartadas


def calcular(b: pd.DataFrame, momento) -> pd.DataFrame:
    """Dia da operação, pontualidade e "ainda não venceu" (aberto) de cada trecho."""
    b = b.copy()
    h = pd.Timedelta(hours=INICIO_DIA_HORAS)
    b["dia_chegada"] = (b["chegada_plan"] - h).dt.normalize()
    b["dia_saida"] = (b["saida_plan"] - h).dt.normalize()
    b["ok_chegada"] = (b["chegada_real"].notna() & (b["chegada_real"] <= b["chegada_plan"])).astype(int)
    b["ok_saida"] = (b["saida_real"].notna() & (b["saida_real"] <= b["saida_plan"])).astype(int)
    b["aberto_chegada"] = (b["chegada_real"].isna() & (b["chegada_plan"] > momento)).astype(int)   # sem horário real e ainda no prazo
    b["aberto_saida"] = (b["saida_real"].isna() & (b["saida_plan"] > momento)).astype(int)
    return b


def visao(base: pd.DataFrame, ind: str, tipo: str) -> pd.DataFrame:
    """Uma linha por trecho do tipo de linha pedido, com regiao, dia, n_prev (=1) e n_real (=pontual)."""
    cfg = IND[ind]
    sub = base[(base["tipo_linha"] == tipo) & (base[cfg["aberto"]] == 0)]
    return pd.DataFrame({"regiao": sub[TIPOS[tipo]["regiao_col"]].values, "dia": sub[cfg["dia"]].values,
                         "n_prev": 1, "n_real": sub[cfg["ok"]].values})


# ---------- indicadores ----------
def _regioes(v: pd.DataFrame) -> list[str]:
    extras = sorted(r for r in v["regiao"].dropna().unique() if r not in REGIOES and str(r).strip())
    return list(REGIOES) + extras


def _taxa(g: pd.DataFrame) -> pd.Series:
    return (g["n_real"] / g["n_prev"]).where(g["n_prev"] > 0)


def _total_por(g: pd.DataFrame, nivel) -> pd.Series:
    """Média das taxas das regionais em cada período (linha de total da planilha). g: índice (regiao, ...)."""
    return _taxa(g).groupby(level=nivel).mean()


def tabela_periodo(v: pd.DataFrame, ini=None, fim=None) -> pd.DataFrame:
    """Total de trechos, atrasos, taxa no prazo, meta e ranking por região (aba Taxa de ...)."""
    sub = v
    if ini is not None:
        sub = v[(v["dia"] >= pd.Timestamp(ini)) & (v["dia"] <= pd.Timestamp(fim if fim is not None else ini))]
    g = sub.groupby("regiao")[["n_prev", "n_real"]].sum().reindex(_regioes(sub), fill_value=0)
    g.index.name = "regiao"
    g = g.reset_index().rename(columns={"n_prev": "prev", "n_real": "real"})
    g["atraso"] = g["prev"] - g["real"]
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    g["meta"] = META
    g["ranking"] = g["taxa"].fillna(0).rank(method="min", ascending=False).astype(int)
    g = g.sort_values(["ranking", "prev"], ascending=[True, False]).reset_index(drop=True)

    total = pd.DataFrame([{"regiao": TOTAL, "prev": int(g["prev"].sum()), "real": int(g["real"].sum()),
                           "atraso": int(g["atraso"].sum()), "taxa": g["taxa"].mean(), "meta": META, "ranking": None}])
    out = pd.concat([total, g], ignore_index=True)
    out.insert(0, "n", ["合计"] + list(range(1, len(g) + 1)))
    return out


def comparar(atual: pd.DataFrame, comparada: pd.DataFrame) -> pd.DataFrame:
    taxa = comparada.set_index("regiao")["taxa"]
    out = atual.copy()
    out["taxa_comp"] = out["regiao"].map(taxa)
    out["variacao"] = out["taxa"] - out["taxa_comp"]
    return out


def rotular_tabela(tab: pd.DataFrame, ind: str, tipo: str) -> pd.DataFrame:
    """Colunas na ordem: Nº, região, total, atraso, taxa, meta, ranking [, comparação, variação]."""
    cols = ["n", "regiao", "prev", "atraso", "taxa", "meta", "ranking"] + [c for c in ("taxa_comp", "variacao") if c in tab]
    return tab[cols].rename(columns={
        "n": "序号 Nº", "regiao": TIPOS[tipo]["regiao_rot"], "prev": tx.COL_TOTAL[ind], "atraso": tx.COL_ATRASO[ind],
        "taxa": tx.COL_TAXA[ind], "meta": "目标 Meta", "ranking": "排名 Ranking",
        "taxa_comp": tx.COL_COMP, "variacao": tx.COL_VAR})


def tendencia(v: pd.DataFrame, tipo: str, freq: str = "D", ate=None, janela: int | None = None) -> pd.DataFrame:
    """Taxa por período e região + acumulado da janela + variação do último contra o anterior."""
    sub = v
    if ate is not None:
        sub = sub[sub["dia"] <= pd.Timestamp(ate)]
    if sub.empty:
        return pd.DataFrame()
    sub = sub.assign(per=periodos.inicio(sub["dia"], freq))
    recentes = sorted(sub["per"].unique())[-(janela or periodos.JANELA[freq]):]
    sub = sub[sub["per"].isin(recentes)]

    g = sub.groupby(["regiao", "per"])[["n_prev", "n_real"]].sum()
    diaria = _taxa(g).unstack("per")
    diaria.loc[TOTAL] = _total_por(g, "per")
    acum_g = sub.groupby("regiao")[["n_prev", "n_real"]].sum()
    acumulado = pd.concat([_taxa(acum_g), pd.Series({TOTAL: _taxa(acum_g).mean()})])

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
    out.index.name = TIPOS[tipo]["regiao_rot"]
    return out.reset_index()


def resumo(v: pd.DataFrame, freq: str = "W", regional: str | None = None, ini=None, fim=None) -> pd.DataFrame:
    """Total, atrasos e taxa por período (dia, semana ou mês). Sem regional: média das regionais, como no total da planilha."""
    sub = v
    if regional:
        sub = sub[sub["regiao"] == regional]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim))]
    cols = ["inicio", "periodo", "prev", "real", "atraso", "taxa", "meta", "variacao"]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    sub = sub.assign(per=periodos.inicio(sub["dia"], freq))
    g = sub.groupby(["regiao", "per"])[["n_prev", "n_real"]].sum()
    tot = g.groupby(level="per").sum().rename(columns={"n_prev": "prev", "n_real": "real"})
    tot["taxa"] = _total_por(g, "per") if not regional else (tot["real"] / tot["prev"]).where(tot["prev"] > 0)
    tot["atraso"] = tot["prev"] - tot["real"]
    tot = tot.reindex(periodos.completos(tot.index.min(), tot.index.max(), freq))
    tot[["prev", "real", "atraso"]] = tot[["prev", "real", "atraso"]].fillna(0).astype(int)
    tot["meta"] = META
    tot["variacao"] = tot["taxa"].diff()
    anos = {d.year for d in tot.index}
    tot["periodo"] = [periodos.rotulo_curto(d, freq, com_ano=len(anos) > 1) for d in tot.index]
    tot.index.name = "inicio"
    return tot.reset_index()[cols]


def resumo_regionais(v: pd.DataFrame, freq: str, ini=None, fim=None) -> pd.DataFrame:
    """Uma linha por regional x período (mapa de calor). Colunas: regiao, periodo, inicio, prev, real, taxa."""
    sub = v
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim))]
    if sub.empty:
        return pd.DataFrame(columns=["regiao", "inicio", "periodo", "prev", "real", "taxa"])
    sub = sub.assign(inicio=periodos.inicio(sub["dia"], freq))
    g = sub.groupby(["regiao", "inicio"])[["n_prev", "n_real"]].sum().rename(columns={"n_prev": "prev", "n_real": "real"}).reset_index()
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    anos = {d.year for d in g["inicio"]}
    g["periodo"] = [periodos.rotulo_curto(d, freq, com_ano=len(anos) > 1) for d in g["inicio"]]
    return g


def regionais(v: pd.DataFrame) -> list[str]:
    return [r for r in _regioes(v) if (v["regiao"] == r).any()]
