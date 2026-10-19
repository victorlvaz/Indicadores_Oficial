"""Leitura, tratamento e regras do relatório SM (sem Streamlit).

Equivalência com a planilha finalizada (abas 支线跟踪查询集货COLETA / 散货ENTREGA):
  ROTA / Quantidade de trechos / SM previsto  -> sm_prev = nº de pontos da rota - 1
      (rota = a de MAIS trechos entre a coluna G "Nome da rota" e a D "Nome da viagem"; G vazia -> D. Regra de 14/10, ver config.PREVISTO_PELA_ROTA)
      (a planilha usa LEN(rota) + tabela 索引; dá o mesmo resultado nas 6 regionais do relatório,
       e não quebra quando o código da unidade tem 3 letras)
  SM realizado  -> nº de linhas do TECHIS com Nº Embarque = Tarefa de transporte No. (limitado ao previsto)
  Data saida planejado -> dia
  SM COLETA/ENTREGA 状态统计 -> tabela_dia();  Tendência -> tendencia()
"""
import io

import pandas as pd

from comum import periodos
from . import config as cfg
from . import textos as tx
from .config import (APOIO, COL_JMS, PREVISTO_PELA_ROTA, COL_JMS_OPCIONAIS, COL_TECHIS_EMBARQUE, COLUNAS_CALCULADAS,
                     COLUNAS_REMOVER, PEDIDO_MAE_MINIMO, REGIOES, STATUS_VALIDOS, TECHIS_COLUNAS,
                     TECHIS_STATUS_VALIDOS, TRANSPORTADOR_EXCLUIDO)


# ---------- leitura ----------
def ler_planilha(origem, sheet_name=0, header=0) -> pd.DataFrame:
    """Lê .xlsx / .xls / .csv. O JMS costuma mandar .xls que na verdade é xlsx."""
    nome = str(getattr(origem, "name", origem)).lower()
    if nome.endswith(".csv"):
        return pd.read_csv(origem, dtype=str, sep=None, engine="python", header=header)
    try:
        return pd.read_excel(origem, sheet_name=sheet_name, engine="openpyxl", header=header)
    except Exception:
        if hasattr(origem, "seek"):
            origem.seek(0)
        return pd.read_excel(origem, sheet_name=sheet_name, engine="xlrd", header=header)


def carregar_apoio() -> dict:
    return {
        "pontos_coleta": set(pd.read_csv(APOIO / "pontos_coleta.csv")["estacao"].astype(str).str.strip()),
        "rotas_mesmo_sc": set(pd.read_csv(APOIO / "rotas_mesmo_sc.csv")["rota"].astype(str).str.strip()),
    }


def _chave(s: pd.Series, limpar_espacos: bool = True) -> pd.Series:
    """Nº de embarque normalizado. O CONT.SE do Excel ignora maiúsculas/minúsculas, mas NÃO ignora
    espaço/TAB no fim: no TECHIS há embarques digitados com TAB ("SRTR...\t") que a planilha não conta.
    limpar_espacos=True conta esses SMs (correto); False reproduz a planilha exatamente."""
    s = s.astype(str)
    return (s.str.strip() if limpar_espacos else s).str.upper()


# ---------- TECHIS ----------
def ler_techis(origem, sheet_name=0) -> pd.DataFrame:
    """Extração do TECHIS. Procura a linha de cabeçalho que contém "Nº Embarque" (o arquivo
    pode vir com linhas de título acima)."""
    df = ler_planilha(origem, sheet_name=sheet_name)
    if COL_TECHIS_EMBARQUE not in df.columns:
        topo = df.head(15)
        for i in range(len(topo)):
            if COL_TECHIS_EMBARQUE in [str(v).strip() for v in topo.iloc[i].tolist()]:
                df.columns = [str(v).strip() for v in topo.iloc[i].tolist()]
                df = df.iloc[i + 1:]
                break
        else:
            raise ValueError(tx.ERRO_TECHIS + COL_TECHIS_EMBARQUE)
    df = df.dropna(how="all").reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]
    # anotação: copiar da coluna Status até Tecnologia (A:K)
    ini, fim = TECHIS_COLUNAS
    if ini in df.columns and fim in df.columns:
        i, j = list(df.columns).index(ini), list(df.columns).index(fim)
        if i < j:
            df = df.iloc[:, i:j + 1]
    # números longos (SM, CNPJ, embarque) como texto, sem ".0" nem notação científica
    for c in df.columns:
        if df[c].dtype.kind == "f" and df[c].dropna().apply(float.is_integer).all():
            df[c] = df[c].astype("Int64")
    return df


def filtrar_techis(techis: pd.DataFrame, filtro_status: bool = True) -> tuple[pd.DataFrame, int]:
    """Anotação: manter só Em Viagem e Finalizado. Retorna (techis filtrado, linhas removidas)."""
    if not filtro_status or "Status" not in techis.columns:
        return techis, 0
    ok = techis["Status"].astype(str).str.strip().str.upper().isin([s.upper() for s in TECHIS_STATUS_VALIDOS])
    return techis[ok].reset_index(drop=True), int((~ok).sum())


def contagem_techis(techis: pd.DataFrame | None, limpar_espacos: bool = True) -> pd.Series:
    """Quantos SMs o TECHIS tem para cada Nº Embarque."""
    if techis is None or techis.empty:
        return pd.Series(dtype=int)
    k = _chave(techis[COL_TECHIS_EMBARQUE], limpar_espacos)
    return k[k.ne("") & k.ne("NAN")].value_counts()


# ---------- JMS ----------
def _achar_colunas(df: pd.DataFrame) -> dict:
    escolhidas, faltando = {}, []
    for chave, nomes in COL_JMS.items():
        nome = next((n for n in nomes if n in df.columns), None)
        if nome:
            escolhidas[chave] = nome
        elif chave not in COL_JMS_OPCIONAIS:
            faltando.append(nomes[0])
    if faltando:
        raise ValueError(tx.ERRO_COLUNAS + ", ".join(faltando))
    return escolhidas


def sm_previsto(viagem: pd.Series) -> pd.Series:
    """Nome da viagem = pontos da rota + horário + sequência, ex. "S107-S268-GRU-2200-1".
    Tira horário e sequência; cada trecho entre dois pontos é um SM: 3 pontos -> 2 SMs."""
    partes = viagem.astype(str).str.strip().str.split("-")
    return (partes.str.len() - 3).clip(lower=1)


def rota_usada(viagem: pd.Series, rota: pd.Series) -> pd.Series:
    """Rota que define o SM previsto (regra de 14/10, confirmada com o Renan).
    Cada hífen separa um trecho. Coluna G (Nome da rota) vazia -> vale a D (Nome da viagem).
    As duas preenchidas e com nº de trechos diferente -> vale a que tiver MAIS trechos (empate -> G)."""
    d = viagem.fillna("").astype(str).str.strip()
    g = rota.fillna("").astype(str).str.strip()
    g = g.mask(g.str.lower().isin(["nan", "none", "nat"]), "")
    usar_g = g.ne("") & (g.str.count("-") >= d.str.count("-"))
    return g.where(usar_g, d)


def preparar_jms(df: pd.DataFrame, tipo: str, apoio: dict | None = None, *, filtro_status=True,
                 filtro_mesmo_sc=True, filtro_ponto_coleta=True, filtro_franqueado=True,
                 filtro_pedido_mae=True, prev_pela_rota=PREVISTO_PELA_ROTA):
    """Retorna (base tratada, diagnóstico). tipo = "COLETA" ou "ENTREGA"."""
    apoio = apoio or carregar_apoio()
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    # histórico: guarda o SM realizado já apurado (o TECHIS novo pode não cobrir dias antigos)
    real_hist = pd.to_numeric(df.get(COLUNAS_CALCULADAS["sm_real"], pd.Series(index=df.index, dtype=float)),
                              errors="coerce")
    # anotação: remover KM do Google e CHECK-IN (e colunas calculadas, se vier de um histórico exportado)
    df = df.drop(columns=[c for c in [*COLUNAS_REMOVER, *COLUNAS_CALCULADAS.values()] if c in df.columns])
    cols = _achar_colunas(df)
    b = df[list(cols.values())].rename(columns={v: k for k, v in cols.items()})
    for c in COL_JMS:
        if c not in b.columns:
            b[c] = ""
    originais = list(df.columns)
    b = pd.concat([b, df], axis=1)          # colunas originais do JMS seguem junto (para exportar a base)
    b["sm_real_hist"] = real_hist

    for c in ("id", "status", "viagem", "rota", "tipo_transportador", "partida", "regiao"):
        b[c] = b[c].fillna("").astype(str).str.strip()
    b["tipo"] = tipo
    b["saida_plan"] = pd.to_datetime(b["saida_plan"], errors="coerce", format="mixed")
    b["dia"] = b["saida_plan"].dt.normalize()
    b["pedido_mae"] = pd.to_numeric(b["pedido_mae"], errors="coerce")

    diag = {tx.DIAG["tipo"]: tx.TIPO_PT[tipo], tx.DIAG["lidas"]: len(b)}
    sem_data = b["dia"].isna()                      # inclui a linha de cabeçalho em chinês, se vier
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
    if filtro_ponto_coleta and tipo == "COLETA":
        fora = ~b["partida"].isin(apoio["pontos_coleta"])
        diag[tx.DIAG["ponto_coleta"]] = int(fora.sum())
        b = b[~fora]
    if filtro_pedido_mae:
        ruim = b["pedido_mae"].isna() | (b["pedido_mae"] < PEDIDO_MAE_MINIMO)
        diag[tx.DIAG["pedido_mae"]] = int(ruim.sum())
        b = b[~ruim]
    if filtro_franqueado:
        fr = b["tipo_transportador"].str.startswith(TRANSPORTADOR_EXCLUIDO)
        diag[tx.DIAG["franqueado"]] = int(fr.sum())
        b = b[~fr]

    b["rota_usada"] = rota_usada(b["viagem"], b["rota"]) if prev_pela_rota else b["viagem"]
    b["sm_prev"] = sm_previsto(b["rota_usada"]).astype(int)
    diag[tx.DIAG["usadas"]] = len(b)
    if prev_pela_rota:
        diag[tx.DIAG["rota_vazia"]] = int((b["rota"].eq("") | b["rota"].str.lower().isin(["nan", "none"])).sum())
    return b[INTERNAS + originais].reset_index(drop=True), diag


INTERNAS = ["tipo", "id", "status", "viagem", "rota", "rota_usada", "tipo_transportador", "transportador", "pedido_mae",
            "partida", "chegada", "saida_plan", "placa", "regiao", "regiao_destino", "dia", "sm_prev",
            "sm_real_hist"]


def colunas_internas(base: pd.DataFrame) -> list:
    return [c for c in INTERNAS + ["sm_contagem", "sm_real"] if c in base.columns and c != "sm_real_hist"]


def base_para_exportar(base: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Aba de base como na planilha: colunas originais do JMS (sem Km Google e CHECK-IN) + colunas de
    fórmula (ROTA, SM previsto, SM realizado, Data saida planejado...). Também serve de HISTÓRICO:
    o arquivo exportado pode ser enviado de volta no campo Histórico."""
    sub = base[base["tipo"] == tipo]
    internas = set(INTERNAS + ["sm_contagem", "sm_real"])
    originais = [c for c in sub.columns if c not in internas and sub[c].notna().any()]
    out = sub[originais].copy()
    for k, nomes in COL_JMS.items():                    # linhas vindas do banco não têm as colunas originais do JMS
        if k in sub.columns:
            n = nomes[0]
            out[n] = out[n].where(out[n].notna(), sub[k]) if n in out.columns else sub[k]
    out[COLUNAS_CALCULADAS["rota"]] = sub["rota_usada"].str.split("-").str[:-2].str.join("-")
    out[COLUNAS_CALCULADAS["sm_prev"]] = sub["sm_prev"]
    if "sm_real" in sub:
        out[COLUNAS_CALCULADAS["sm_real"]] = sub["sm_real"]
    out[COLUNAS_CALCULADAS["dia"]] = sub["dia"].dt.date
    out[COLUNAS_CALCULADAS["mesmo_sc"]] = "Não"
    if tipo == "COLETA":
        out[COLUNAS_CALCULADAS["coleta"]] = "Sim"
    return out.reset_index(drop=True)


def ler_historico(origem) -> dict:
    """Excel exportado pelo app (ou a planilha antiga): devolve {tipo: DataFrame} das abas de base."""
    abas = pd.ExcelFile(origem).sheet_names
    out = {}
    for tipo in ("COLETA", "ENTREGA"):
        aba = next((a for a in abas if "跟踪查询" in a and a.upper().endswith(tipo)), None)
        if aba:
            out[tipo] = pd.read_excel(origem, sheet_name=aba)
    return out


def juntar(bases: list[pd.DataFrame]) -> pd.DataFrame:
    """Empilha extrações (vários dias / arquivos); repetição da mesma tarefa vale a mais recente."""
    bases = [b for b in bases if b is not None and not b.empty]
    if not bases:
        return pd.DataFrame()
    todas = pd.concat(bases, ignore_index=True)
    return todas.drop_duplicates(subset=["tipo", "id", "saida_plan"], keep="last").reset_index(drop=True)


def aplicar_techis(base: pd.DataFrame, contagem: pd.Series, limitar: bool | dict = True) -> pd.DataFrame:
    """sm_contagem = linhas do TECHIS da tarefa; sm_real = mesmo valor, limitado ao previsto.
    limitar pode ser True/False ou {"COLETA": bool, "ENTREGA": bool} (a planilha limita só a Coleta)."""
    b = base.copy()
    b["sm_contagem"] = _chave(b["id"]).map(contagem).fillna(0).astype(int)
    if "sm_real_hist" in b:               # dia vindo do histórico: vale o maior entre o já apurado e o TECHIS novo
        b["sm_contagem"] = b[["sm_contagem", "sm_real_hist"]].max(axis=1).fillna(0).astype(int)
    lim = limitar if isinstance(limitar, dict) else {t: bool(limitar) for t in ("COLETA", "ENTREGA")}
    aplica = b["tipo"].map(lim).fillna(True).astype(bool)
    b["sm_real"] = b["sm_contagem"].where(~aplica, b[["sm_contagem", "sm_prev"]].min(axis=1)).astype(int)
    return b


# ---------- indicadores ----------
def regioes_da(df: pd.DataFrame) -> list:
    """Regionais da planilha + as extras de config.REGIOES_EXTRAS que aparecem nos dados."""
    if df.empty or not cfg.REGIOES_EXTRAS:
        return list(REGIOES)
    presentes = set(df["regiao"].dropna().astype(str).str.strip())
    return list(REGIOES) + [r for r in cfg.REGIOES_EXTRAS if r in presentes and r not in REGIOES]


def tabela_periodo(base: pd.DataFrame, tipo: str, ini=None, fim=None) -> pd.DataFrame:
    """Equivalente às abas SM COLETA/ENTREGA 状态统计: previsto, realizado e % por regional de origem.
    ini/fim = período (inclusive); None = "Todos": acumulado de todos os dias."""
    sub = base[base["tipo"] == tipo]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim if fim is not None else ini))]
    g = sub.groupby("regiao")[["sm_prev", "sm_real"]].sum().reindex(regioes_da(sub), fill_value=0)
    g = g.rename(columns={"sm_prev": "prev", "sm_real": "real"})
    g.index.name = "regiao"
    g = g.reset_index()
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    g["ranking"] = g["taxa"].fillna(-1).rank(method="min", ascending=False).astype(int)
    g = g.sort_values(["ranking", "prev"], ascending=[True, False]).reset_index(drop=True)

    prev, real = int(g["prev"].sum()), int(g["real"].sum())
    total = pd.DataFrame([{"regiao": tx.TOTAL, "prev": prev, "real": real,
                           "taxa": real / prev if prev else float("nan"), "ranking": None}])
    return pd.concat([total, g], ignore_index=True)


def tabela_dia(base: pd.DataFrame, tipo: str, dia) -> pd.DataFrame:
    """Um dia só (ou None = todos). Mantido para o validador."""
    return tabela_periodo(base, tipo, dia, dia)


def comparar(atual: pd.DataFrame, comparada: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta a taxa do período comparado e a variação (fração: 0,0125 = +1,25 p.p.)."""
    taxa = comparada.set_index("regiao")["taxa"]
    out = atual.copy()
    out["taxa_comp"] = out["regiao"].map(taxa)
    out["variacao"] = out["taxa"] - out["taxa_comp"]
    return out


def rotular_tabela(tab: pd.DataFrame) -> pd.DataFrame:
    return tab.rename(columns={"regiao": tx.COL_REGIAO, "prev": tx.COL_PREV, "real": tx.COL_REAL,
                               "taxa": tx.COL_TAXA, "ranking": tx.COL_RANK,
                               "taxa_comp": tx.COL_COMP, "variacao": tx.COL_VAR})


def tendencia(base: pd.DataFrame, tipo: str, freq: str = "D", ate=None, janela: int | None = None) -> pd.DataFrame:
    """Aba Tendência: % por período (dia, semana, mês ou ano) e regional + acumulado (média das taxas dos períodos,
    como na planilha) + variação do último período vs. o anterior. `ate` = último dia considerado."""
    sub = base[base["tipo"] == tipo]
    sub = sub[sub["regiao"].isin(regioes_da(sub))]
    if ate is not None:
        sub = sub[sub["dia"] <= pd.Timestamp(ate)]
    if sub.empty:
        return pd.DataFrame()
    sub = sub.assign(per=periodos.inicio(sub["dia"], freq))
    sub = sub[sub["per"].isin(sorted(sub["per"].unique())[-(janela or periodos.JANELA[freq]):])]
    g = sub.groupby(["regiao", "per"])[["sm_prev", "sm_real"]].sum()
    diaria = (g["sm_real"] / g["sm_prev"]).unstack("per")
    t = sub.groupby("per")[["sm_prev", "sm_real"]].sum()
    diaria.loc[tx.TOTAL] = t["sm_real"] / t["sm_prev"]

    out = diaria.copy()
    curtos = [periodos.rotulo_curto(d, freq) for d in out.columns]
    if len(set(curtos)) < len(curtos):
        curtos = [periodos.rotulo_curto(d, freq, com_ano=True) for d in out.columns]
    out.columns = curtos
    out.insert(0, tx.COL_VARIACAO,
               out.iloc[:, -1] - out.iloc[:, -2] if out.shape[1] >= 2 else float("nan"))
    out.insert(1, tx.COL_ACUMULADO, diaria.mean(axis=1, skipna=True))
    out = out.loc[[tx.TOTAL] + [r for r in regioes_da(sub) if r in out.index]]
    out.index.name = tx.COL_REGIAO
    return out.reset_index()


def resumo(base: pd.DataFrame, tipo: str, freq: str = "W", regional: str | None = None, ini=None, fim=None) -> pd.DataFrame:
    """Previsto, realizado e taxa por período para uma regional (None = todas as regionais do relatório).
    Períodos sem nenhuma viagem entram com taxa vazia (lacuna visível no gráfico)."""
    sub = base[base["tipo"] == tipo]
    sub = sub[sub["regiao"].isin(regioes_da(sub))]
    if regional:
        sub = sub[sub["regiao"] == regional]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim))]
    if sub.empty:
        return pd.DataFrame(columns=["inicio", "periodo", "prev", "real", "taxa", "variacao"])
    g = sub.groupby(periodos.inicio(sub["dia"], freq))[["sm_prev", "sm_real"]].sum()
    g = g.rename(columns={"sm_prev": "prev", "sm_real": "real"})
    g = g.reindex(periodos.completos(g.index.min(), g.index.max(), freq), fill_value=0)
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    g["variacao"] = g["taxa"].diff()
    anos = {d.year for d in g.index}
    g["periodo"] = [periodos.rotulo_curto(d, freq, com_ano=len(anos) > 1) for d in g.index]
    g.index.name = "inicio"
    return g.reset_index()[["inicio", "periodo", "prev", "real", "taxa", "variacao"]]


def resumo_regionais(base: pd.DataFrame, tipo: str, freq: str = "W", ini=None, fim=None) -> pd.DataFrame:
    """Previsto, realizado e taxa por regional e por período (mini-gráficos). Períodos sem viagem ficam com taxa vazia."""
    sub = base[base["tipo"] == tipo]
    sub = sub[sub["regiao"].isin(regioes_da(sub))]
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim))]
    cols = ["regiao", "inicio", "periodo", "prev", "real", "taxa"]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    g = sub.groupby(["regiao", periodos.inicio(sub["dia"], freq)])[["sm_prev", "sm_real"]].sum()
    todos = periodos.completos(g.index.get_level_values(1).min(), g.index.get_level_values(1).max(), freq)
    regs = [r for r in regioes_da(sub) if r in set(sub["regiao"])]
    g = g.reindex(pd.MultiIndex.from_product([regs, todos], names=["regiao", "inicio"]), fill_value=0).reset_index()
    g = g.rename(columns={"sm_prev": "prev", "sm_real": "real"})
    g["taxa"] = (g["real"] / g["prev"]).where(g["prev"] > 0)
    com_ano = len({d.year for d in todos}) > 1
    g["periodo"] = [periodos.rotulo_curto(d, freq, com_ano=com_ano) for d in g["inicio"]]
    return g[cols]


def pendentes(base: pd.DataFrame, ini=None, fim=None) -> pd.DataFrame:
    """Viagens do período com SM realizado abaixo do previsto (para as regionais cobrarem). None = todos os dias."""
    sub = base[base["sm_real"] < base["sm_prev"]].copy()
    if ini is not None:
        sub = sub[(sub["dia"] >= pd.Timestamp(ini)) & (sub["dia"] <= pd.Timestamp(fim if fim is not None else ini))]
    sub["faltam"] = sub["sm_prev"] - sub["sm_real"]
    return sub.sort_values(["tipo", "regiao", "saida_plan"]).reset_index(drop=True)


def embarque_com_espaco(techis: pd.DataFrame) -> pd.Series:
    """Linhas do TECHIS cujo Nº Embarque tem espaço/TAB sobrando (a planilha antiga não as contava)."""
    s = techis[COL_TECHIS_EMBARQUE].astype(str)
    return s.ne(s.str.strip())


def techis_ligado(techis: pd.DataFrame, base: pd.DataFrame) -> pd.Series:
    """True para as linhas do TECHIS cujo Nº Embarque existe na base do JMS."""
    ids = set(_chave(base["id"])) if base is not None and not base.empty else set()
    return _chave(techis[COL_TECHIS_EMBARQUE]).isin(ids)


def df_para_xlsx(df: pd.DataFrame, aba: str = "dados") -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name=aba[:31], index=False)
        w.sheets[aba[:31]].freeze_panes = "A2"
    return buf.getvalue()
