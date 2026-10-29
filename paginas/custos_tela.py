"""Página: 物流成本指标 / Indicadores de Custos Linha Secundária (dados vêm do histórico no banco)."""
import pandas as pd
import streamlit as st

from comum import banco, feishu_envio, lideres, periodos
from comum.estilos import estilizar_tendencia  # noqa: F401
from comum.exportar import para_excel
from comum.idioma import cabecalho, rodape
from comum.sparkline import tabela_tendencia_html
from comum.tema import CINZA_DESTAQUE, VERDE, VERMELHO
from comum.uploads import manter, opcao_valida, remover, upload_persistente
from custos import historico, resumo_ui, textos as tx
from custos.calculos import (TOTAL, comparar, detalhe, lista_duplicidades, lista_pendencias, ler_arquivo,
                             pendencias_por_regional, preparar, regioes_da, tabela_periodo, tendencia)
from custos.config import REGIOES, regional_do_nome
from custos.resumo_ui import brl, inteiro, variacao

cabecalho(*tx.PAGINA)


@st.cache_data(show_spinner=False, max_entries=4)
def _ler_cache(conteudo: bytes, nome: str):
    return ler_arquivo(conteudo, nome)


@st.cache_data(show_spinner="Carregando histórico…", max_entries=2)
def _historico(versao: tuple) -> pd.DataFrame:
    return historico.ler(banco.engine())


def _estilo(tab: pd.DataFrame, cols_texto: list, comp: bool):
    """Texto formatado + linha de total em cinza; custo que sobe (variação positiva) fica em vermelho."""
    txt = tab.copy()
    for c in cols_texto:
        txt[c] = tab[c].astype(str)
    for c in (tx.COL_PACOTES, tx.COL_KM):
        txt[c] = tab[c].map(inteiro)
    txt[tx.COL_VIAGENS] = tab[tx.COL_VIAGENS].map(inteiro)
    for c in (tx.COL_FRETE, tx.COL_FRETE_KM, tx.COL_FRETE_PACOTE, tx.COL_COMP_PACOTE, tx.COL_COMP_KM):
        if c in tab:
            txt[c] = tab[c].map(brl)
    for c in (tx.COL_VAR_PACOTE, tx.COL_VAR_KM):
        if c in tab:
            txt[c] = tab[c].map(variacao)
    est = pd.DataFrame("", index=txt.index, columns=txt.columns)
    est.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"
    if comp:
        for c in (tx.COL_VAR_PACOTE, tx.COL_VAR_KM):
            est.loc[(tab[c].round(4) > 0).fillna(False), c] = f"color:{VERMELHO};font-weight:700"
            est.loc[(tab[c].round(4) < 0).fillna(False), c] = f"color:{VERDE};font-weight:700"
    return txt.style.apply(lambda _: est, axis=None)


def _rotular(t: pd.DataFrame) -> pd.DataFrame:
    return t.rename(columns={"n": "序号 Nº", "regiao": tx.COL_REGIAO, "item": tx.COL_ITEM, "viagens": tx.COL_VIAGENS,
                             "pacotes": tx.COL_PACOTES, "km": tx.COL_KM, "frete": tx.COL_FRETE,
                             "frete_km": tx.COL_FRETE_KM, "frete_pacote": tx.COL_FRETE_PACOTE,
                             "frete_pacote_comp": tx.COL_COMP_PACOTE, "var_pacote": tx.COL_VAR_PACOTE,
                             "frete_km_comp": tx.COL_COMP_KM, "var_km": tx.COL_VAR_KM})


def _para_exportar(tab, comp, titulo=None):
    """titulo: nome completo para a imagem do Feishu (o nome da aba do Excel é cortado em 31 caracteres)."""
    exp = tab.copy()
    if comp:
        for c in (tx.COL_VAR_PACOTE, tx.COL_VAR_KM):
            exp[c] = exp[c] * 100
        return exp, {"custos": True, "var_inverso": True, "pp_extra": [tx.COL_VAR_PACOTE, tx.COL_VAR_KM], "titulo_img": titulo}
    return exp, {"custos": True, "titulo_img": titulo}


manter("cures_reg", "cures_vis", "cures_ano", "cures_pil_W", "cures_pil_M", "cu_gran", "cu_comp", "cu_per_D", "cu_per_W",
       "cu_per_M", "cu_per_Y", "cu_n_dias", "cu_escala", "cu_metrica", "cu_aud_reg", "cu_aud_tipo")

# ---------- Banco ----------
try:
    eng = banco.engine()
    versao = historico.versao(eng)
except Exception as erro:
    st.error(tx.ERRO_BANCO + str(erro).split("[SQL:")[0].strip()[:400])
    st.stop()

# ---------- Carga (vários arquivos de uma vez) ----------
st.sidebar.header(tx.HIST)
st.sidebar.caption(f"{tx.BANCO_EM_USO}: {banco.descricao()}")
arquivos = upload_persistente("custos", tx.UPLOAD, ["xlsx", "xlsm", "xlsb"], tx.UPLOAD_AJUDA)
regionais_arq: dict[str, str | None] = {}
for arq in arquivos:
    reg = regional_do_nome(arq.name)
    if reg is None:
        st.sidebar.caption(tx.REGIONAL_NAO_ACHADA)
        escolha = st.sidebar.selectbox(arq.name, ["—"] + REGIOES, key=f"cu_reg_{arq.name}")
        reg = None if escolha == "—" else escolha
    regionais_arq[arq.name] = reg
if arquivos:
    st.sidebar.caption(tx.PENDENTE)
    for arq in arquivos:
        if regionais_arq[arq.name]:
            st.sidebar.caption(f"{arq.name} → **{regionais_arq[arq.name]}**")
    pronto = all(regionais_arq.values())
    if st.sidebar.button(tx.SALVAR, type="primary", help=tx.SALVAR_AJUDA, key="cu_salvar", disabled=not pronto):
        resumos, erros = [], []
        for arq in arquivos:                                   # cada arquivo é independente: um com erro não impede os outros
            reg = regionais_arq[arq.name]
            try:
                with st.spinner(tx.SALVANDO + arq.name, show_time=True):
                    df, info = _ler_cache(arq.getvalue(), arq.name)
                    b, diag = preparar(df, reg)
                    obs = "; ".join(f"{k}: {v}" for k, v in diag.items() if "Linhas" not in k)
                    resumos.append((arq.name, reg, historico.salvar(eng, b, reg, arq.name, len(df), obs)))
            except ValueError as erro:
                erros.append(f"{arq.name}  \n{erro}")
            except Exception as erro:
                erros.append(f"{arq.name}  \n{tx.ERRO_BANCO}{str(erro).split("[SQL:")[0].strip()[:400]}")
        remover("custos", [n for n, _, _ in resumos])
        st.session_state["cu_msg_salvo"] = [
            f"{nome} ({reg}): {r['novas']} novas · {r['atualizadas']} atualizadas" for nome, reg, r in resumos]
        st.session_state["cu_msg_erro"] = erros
        st.rerun()
for linha in st.session_state.pop("cu_msg_erro", []):
    st.sidebar.error(linha)
for linha in st.session_state.pop("cu_msg_salvo", []):
    st.sidebar.success(f"{tx.SALVO_OK} — {linha}")

if versao[0] == 0:
    st.info(tx.INFO_SEM_ARQUIVO)
    st.stop()

base = _historico(versao)
if base.empty:
    st.warning(tx.AVISO_BASE_VAZIA)
    st.stop()

# ---------- Período e comparação ----------
st.sidebar.header(tx.GRAN)
gran = st.sidebar.radio(tx.GRAN, periodos.GRANULARIDADES, horizontal=True, label_visibility="collapsed",
                        format_func=lambda g: tx.GRAN_NOMES[g], key="cu_gran")
lista = periodos.lista(base["dia"], gran)
opcoes = lista + [None]
chave_per = f"cu_per_{gran}"
opcao_valida(chave_per, opcoes)
if chave_per not in st.session_state:
    st.session_state[chave_per] = opcoes[len(lista) - 1]
ini = st.sidebar.selectbox(tx.PERIODO[gran], opcoes, key=chave_per,
                           format_func=lambda p: tx.TODOS if p is None else periodos.rotulo(p, gran))
fim = None if ini is None else periodos.fim(ini, gran)
modo_comp = st.sidebar.radio(tx.COMPARAR, ["ant", "ano"], key="cu_comp",
                             format_func=lambda m: tx.COMP_ANTERIOR if m == "ant" else tx.COMP_ANO)
n_per = st.sidebar.slider(tx.N_DIAS, 3, 10, 6, key="cu_n_dias")
escala_comum = st.sidebar.checkbox("统一刻度 / Escala comum", value=False, key="cu_escala")

per_txt = tx.TODOS if ini is None else periodos.rotulo(ini, gran)
ini_comp = fim_comp = None
if ini is not None:
    ini_comp = (periodos.anterior if modo_comp == "ant" else periodos.ano_passado)(ini, gran)
    fim_comp = periodos.fim(ini_comp, gran)
comp = ini is not None

abas = st.tabs([tx.ABA_REGIONAL, tx.ABA_VEICULO, tx.ABA_TIPO, tx.ABA_TENDENCIA, tx.ABA_RESUMO, tx.ABA_AUDITORIA, tx.ABA_BASE])
export = {}


def _legenda_comp(atual):
    if not comp:
        st.caption(tx.COMP_SEM_TODOS)
    else:
        st.caption(f"{tx.COMP_LEGENDA}: {periodos.rotulo(ini_comp, gran)}")
        if atual["frete_pacote_comp"].isna().all():
            st.caption(tx.COMP_SEM_DADOS)


# --- por regional ---
with abas[0]:
    st.subheader(f"{tx.SUB_REGIONAL} – {per_txt}")
    atual = tabela_periodo(base, ini, fim)
    if comp:
        atual = comparar(atual, tabela_periodo(base, ini_comp, fim_comp))
    tab = _rotular(atual)
    st.dataframe(_estilo(tab, [tab.columns[0], tx.COL_REGIAO], comp), width="stretch", hide_index=True,
                 height=(len(tab) + 1) * 35 + 3)
    _legenda_comp(atual)
    export[tx.SUB_REGIONAL[:31]] = (*_para_exportar(tab, comp, tx.SUB_REGIONAL), tx.nota_texto())
    rodape(*tx.NOTAS)

# --- por veículo / por tipo de transportadora ---
for aba, dim, sub, nome in ((abas[1], "veiculo", tx.SUB_VEICULO, "veiculo"), (abas[2], "tipo_transp", tx.SUB_TIPO, "tipo")):
    with aba:
        st.subheader(f"{sub} – {per_txt}")
        atual = detalhe(base, dim, ini, fim)
        if comp:
            atual = comparar(atual, detalhe(base, dim, ini_comp, fim_comp), chave=("regiao", "item"))
        tab = _rotular(atual)
        st.dataframe(_estilo(tab, [tx.COL_REGIAO, tx.COL_ITEM], comp), width="stretch", hide_index=True,
                     height=min((len(tab) + 1) * 35 + 3, 620))
        _legenda_comp(atual if comp else pd.DataFrame({"frete_pacote_comp": [float("nan")]}))
        if dim == "tipo_transp":
            st.caption(tx.NAO_INFORMADO_NOTA)
        export[sub[:31]] = _para_exportar(tab, comp, sub)
        rodape(*tx.NOTAS)

# --- tendência ---
with abas[3]:
    metrica = st.radio(tx.METRICA, list(tx.METRICAS), horizontal=True, key="cu_metrica", format_func=lambda m: tx.METRICAS[m])
    t = tendencia(base, metrica, gran, fim)
    if not t.empty:
        st.subheader(tx.SUB_TEND[metrica])
        if t.shape[1] > 4:
            st.html(tabela_tendencia_html(t, n_dias=n_per, escala_comum=escala_comum, fmt=brl,
                                          unidade={"D": ("天", "dias"), "W": ("周", "semanas"), "M": ("月", "meses"),
                                                   "Y": ("年", "anos")}[gran]))
        else:
            st.info(tx.INFO_UM_DIA)
        with st.expander(tx.RES_TABELA):
            vis = t.copy()
            for c in vis.columns[1:]:
                vis[c] = vis[c].map(variacao if c == tx.COL_VAR_TEND else brl)
            st.dataframe(vis, width="stretch", hide_index=True)
        if gran == "W" and ini is not None:      # semana: o Excel traz os dias da semana
            _td = tendencia(base[base["dia"] >= pd.Timestamp(ini)], metrica, "D", fim)
            exp = _td.copy() if not _td.empty else t.copy()
        else:
            exp = t.copy()
        exp[tx.COL_VAR_TEND] = exp[tx.COL_VAR_TEND] * 100
        export[tx.SUB_TEND[metrica][:31]] = (exp, {"custos": True, "var_inverso": True, "pp_extra": [tx.COL_VAR_TEND], "sparkline": True, "titulo_img": tx.SUB_TEND[metrica]})

# --- resumo ---
with abas[4]:
    resumo_ui.mostrar(base, export)

# --- auditoria ---
with abas[5]:
    sub_p = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    st.subheader(f"{tx.AUD_PEND} – {per_txt}")
    pend = pendencias_por_regional(base, ini, fim)
    vis = pend.rename(columns={"regiao": tx.COL_REGIAO, **tx.PEND_COLS})
    st.dataframe(vis, width="stretch", hide_index=True, height=(len(vis) + 1) * 35 + 3)
    export[tx.AUD_PEND[:31]] = (vis, {"custos": True, "sem_pct": True})

    st.subheader(tx.AUD_LISTA)
    a1, a2 = st.columns(2)
    opc_reg = ["*"] + regioes_da(base)
    opcao_valida("cu_aud_reg", opc_reg)
    reg_a = a1.selectbox(tx.RES_REGIONAL, opc_reg, key="cu_aud_reg", format_func=lambda r: tx.RES_TODAS if r == "*" else r)
    opc_tipo = [None, "frota", "pacote", "km", "rota", "tipo"]
    opcao_valida("cu_aud_tipo", opc_tipo)
    tipo_a = a2.selectbox(tx.AUD_FILTRO, opc_tipo, key="cu_aud_tipo",
                          format_func=lambda k: tx.AUD_TODAS if k is None else tx.PEND_NOMES[k])
    lst = lista_pendencias(base, ini, fim, None if reg_a == "*" else reg_a, tipo_a)
    if lst.empty:
        st.info(tx.AUD_SEM_PEND)
    else:
        cru = lst.rename(columns={"regional": tx.COL_REGIAO, "dia": tx.COL_DIA, "id": tx.COL_ID, "hub_destino": tx.COL_DESTINO,
                                  "transportadora": tx.COL_TRANSP, "placa": tx.COL_PLACA, "veiculo": tx.COL_VEICULO,
                                  "frete": tx.COL_FRETE, "pacotes_n": tx.COL_PACOTES, "km_n": tx.COL_KM,
                                  "pendencias": tx.COL_PEND})
        cru[tx.COL_DIA] = cru[tx.COL_DIA].dt.strftime("%d/%m/%Y")
        st.caption(f"{len(cru):,}".replace(",", ".") + " " + tx.COL_VIAGENS.split(" ", 1)[1].lower())
        st.dataframe(cru.head(5000), width="stretch", hide_index=True, height=400)
        export[tx.AUD_LISTA[:31]] = (cru, {"custos": True, "sem_pct": True})

    st.subheader(tx.AUD_DUP)
    st.caption(tx.AUD_AJUDA_DUP)
    dup = lista_duplicidades(base, ini, fim, None if reg_a == "*" else reg_a)
    if dup.empty:
        st.info(tx.AUD_SEM_DUP)
    else:
        v = dup.rename(columns={"regional": tx.COL_REGIAO, "dia": tx.COL_DIA, "id": tx.COL_ID, "tipo": tx.COL_DUP_TIPO,
                                "linhas": tx.COL_LINHAS, "frete_somado": tx.COL_FRETE_SOMADO})
        v[tx.COL_DIA] = v[tx.COL_DIA].dt.strftime("%d/%m/%Y")
        st.dataframe(v, width="stretch", hide_index=True, height=min((len(v) + 1) * 35 + 3, 300))
        export[tx.AUD_DUP[:31]] = (v, {"custos": True, "sem_pct": True})

# --- base ---
with abas[6]:
    st.subheader(tx.SUB_CARGAS)
    cargas = historico.ler_cargas(eng).rename(columns={
        "carregado_em": "Carga", "arquivo": "Arquivo", "regional": "Regional", "linhas_lidas": "Linhas lidas",
        "linhas_usadas": "Linhas usadas", "novas": "Novas", "atualizadas": "Atualizadas",
        "dia_min": "De", "dia_max": "Até", "observacao": "Observação"}).drop(columns=["id"], errors="ignore")
    st.dataframe(cargas, width="stretch", hide_index=True, height=min((len(cargas) + 1) * 35 + 3, 240))
    st.subheader(tx.SUB_BASE)
    sub = base if ini is None else base[(base["dia"] >= ini) & (base["dia"] <= fim)]
    st.caption(f"{len(sub):,}".replace(",", ".") + " linhas · " + per_txt)
    mostrar = sub[[c for c in tx.COLUNAS_BASE if c in sub.columns]].head(5000).rename(columns=tx.COLUNAS_BASE)
    st.dataframe(mostrar, width="stretch", hide_index=True, height=400)

st.sidebar.download_button(
    tx.EXPORTAR, data=para_excel(export),
    file_name=tx.arquivo_excel("Todos" if ini is None else periodos.rotulo_curto(ini, gran).replace("/", ".")),
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------- Envio para o Feishu ----------
def _cobranca() -> list:
    """Linhas de cobrança: regionais com viagens sem 'tipo de transportadora' no período, com os líderes do cadastro."""
    try:
        cad = lideres.ler(eng)
    except Exception:
        cad = pd.DataFrame(columns=lideres.COLUNAS)
    pend = pendencias_por_regional(base, ini, fim)
    pend = pend[(pend["regiao"] != TOTAL) & (pend["tipo"] > 0)]
    linhas = []
    if len(pend):
        linhas += [("linha", _partes_bold("Preencher a coluna **TIPO DE TRANSPORTADORA**:")),
                   ("linha", ["请填写“承运商类型”列："])]          # [revisar]
        for reg in pend["regiao"]:
            m = lideres.mencoes(cad, reg)
            linhas.append(("linha", [(f"{reg}", True), " - "] + (m or ["(sem líder cadastrado)"])))
    ctrl = lideres.mencoes(cad, lideres.CONTROLADORIA)
    if ctrl:
        linhas.append(("linha", ctrl))
    return linhas


def _partes_bold(t: str) -> list:
    return [(x, True) if i % 2 else x for i, x in enumerate(t.split("**")) if x]


_nome_xl = tx.arquivo_excel("Todos" if ini is None else periodos.rotulo_curto(ini, gran).replace("/", "."))
feishu_envio.botao(
    chave="cus", ini=ini, fim=fim, dias=base["dia"], export=export, titulo="", periodo_xl=per_txt, nome_xl=_nome_xl,
    excel=lambda: para_excel(export),
    abertura=("📊 Indicadores de Custos referente ao dia {d}.", "以下是{d}支线物流成本指标。"),
    blocos=[("linha", "Base de dados: Report das regionais à Controladoria."),
            ("linha", "数据来源：各区域向财务管控部报送的报表。"),
            ("img", "**Visão geral**", [tx.SUB_REGIONAL[:31]]),
            ("img", "**Custos por Veículo**", [tx.SUB_VEICULO[:31]]),
            ("img", "**Custo por Tipo de Transportador**", [tx.SUB_TIPO[:31]]),
            ("comentario",), ("linhas", _cobranca())])
