"""Página: 支线解封车率 / Lacre / Deslacre Linha Secundária."""
import io

import pandas as pd
import streamlit as st

from comum.estilos import estilizar_tabela, estilizar_tendencia
from comum.exportar import para_excel
from comum.idioma import cabecalho, rodape
from comum.uploads import manter, opcao_valida, upload_persistente
from comum.sparkline import tabela_tendencia_html
from lacre_deslacre import textos as tx
from lacre_deslacre.calculos import (carregar_apoio, juntar_relatorios, ler_relatorio, preparar,
                                     rotular_tabela, tabela_dia, tendencia)
from lacre_deslacre.config import INDICADORES

cabecalho(*tx.PAGINA)


@st.cache_data(show_spinner=False, max_entries=8)
def _ler_cache(conteudo: bytes) -> pd.DataFrame:
    """Lê o Excel uma única vez por arquivo: mexer em filtros e abas não lê de novo."""
    return ler_relatorio(io.BytesIO(conteudo))


def _alinhar_direita(*colunas):
    """Percentuais e ranking viram texto; alinha à direita como os números. (Versões antigas do Streamlit sem 'alignment' ignoram.)"""
    try:
        return {c: st.column_config.TextColumn(alignment="right") for c in colunas}
    except TypeError:
        return {}


# ---------- Entrada ----------
manter("lac_f_status", "lac_f_sc", "lac_f_coleta", "lac_f_franq", "lac_f_pedido", "lac_dia", "lac_n_dias",
       "lac_escala")                                   # não perder filtros ao trocar de relatório
arquivos = upload_persistente("lacre", tx.UPLOAD, ["xls", "xlsx"], tx.UPLOAD_AJUDA)
if not arquivos:
    st.info(tx.INFO_SEM_ARQUIVO)
    st.stop()

st.sidebar.header(tx.REGRAS)
f_status = st.sidebar.checkbox(tx.R_STATUS, value=True, key="lac_f_status")
f_sc = st.sidebar.checkbox(tx.R_MESMO_SC, value=True, key="lac_f_sc")
f_coleta = st.sidebar.checkbox(tx.R_COLETA, value=True, key="lac_f_coleta")
f_franq = st.sidebar.checkbox(tx.R_FRANQ, value=True, key="lac_f_franq")
f_pedido = st.sidebar.checkbox(tx.R_PEDIDO, value=True, key="lac_f_pedido")

apoio = carregar_apoio()
try:
    partes, diags = [], []
    for arq in arquivos:
        b, d = preparar(_ler_cache(arq.getvalue()), apoio, filtro_status=f_status,
                        filtro_mesmo_sc=f_sc, filtro_ponto_coleta=f_coleta,
                        filtro_franqueado=f_franq, filtro_pedido_mae=f_pedido)
        partes.append(b)
        diags.append({tx.DIAG["arquivo"]: arq.name, **d})
except ValueError as erro:
    st.error(str(erro))
    st.stop()

base = juntar_relatorios(partes) if len(partes) > 1 else partes[0]
if base.empty:
    st.warning(tx.AVISO_BASE_VAZIA)
    st.stop()

dias = sorted(base["dia"].dt.date.unique())
opcoes = dias + [None]                      # None = "Todos"
opcao_valida("lac_dia", opcoes)
dia = st.sidebar.selectbox(tx.DIA, opcoes, index=len(dias) - 1, key="lac_dia",
                           format_func=lambda d: tx.TODOS if d is None else d.strftime("%d/%m/%Y"))
dia_txt = tx.TODOS if dia is None else dia.strftime("%d/%m")
n_dias = st.sidebar.slider(tx.N_DIAS, 3, 10, 6, key="lac_n_dias")
escala_comum = st.sidebar.checkbox(tx.ESCALA, value=False, help=tx.ESCALA_AJUDA, key="lac_escala")

# ---------- Abas ----------
nomes = ([tx.nome_aba(t, e) for t, e in INDICADORES]
         + [tx.nome_aba_tendencia(e) for e in ("lacre", "deslacre")]
         + [tx.ABA_BASE])
abas = st.tabs(nomes)
export = {}

for aba, (tipo, evento) in zip(abas[:4], INDICADORES):
    with aba:
        cfg = INDICADORES[(tipo, evento)]
        st.subheader(f"{cfg['titulo']} – {dia_txt}")
        tab = rotular_tabela(tabela_dia(base, tipo, evento, dia), tipo, evento)
        col_taxa, col_meta = tab.columns[4], tab.columns[5]
        st.dataframe(estilizar_tabela(tab, col_taxa, col_meta), width="stretch", hide_index=True,
                     height=(len(tab) + 1) * 35 + 3,          # mostra todas as regionais, sem rolagem
                     column_config=_alinhar_direita(col_taxa, col_meta, tab.columns[-1]))
        rodape(*tx.NOTAS[evento])
        export[tx.aba_excel_tabela(tipo, evento)] = (tab, {"taxa": col_taxa, "meta": col_meta}, tx.nota_texto(evento))

for aba, evento in zip(abas[4:6], ["lacre", "deslacre"]):
    with aba:
        if len(dias) < 2:
            st.info(tx.INFO_UM_DIA)
        for tipo in ("COLETA", "ENTREGA"):
            t = tendencia(base, tipo, evento)
            if t.empty:
                continue
            st.subheader(tx.subtitulo_tendencia(tipo, evento))
            if len(dias) >= 2:
                st.html(tabela_tendencia_html(t, n_dias=n_dias, escala_comum=escala_comum))
                with st.expander(tx.EXPANDER_TENDENCIA):
                    st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
            else:
                st.dataframe(estilizar_tendencia(t), width="stretch", hide_index=True)
            export[tx.aba_excel_tendencia(tipo, evento)] = (t, {})

with abas[6]:
    st.subheader(tx.SUB_DIAG)
    st.dataframe(pd.DataFrame(diags), width="stretch", hide_index=True)
    st.subheader(tx.SUB_BASE)
    st.dataframe(base.rename(columns=tx.COLUNAS_BASE), width="stretch", hide_index=True, height=400)

st.sidebar.download_button(
    tx.EXPORTAR, data=para_excel(export), file_name=tx.arquivo_excel(dia),
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
