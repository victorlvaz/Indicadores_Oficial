"""Arquivo enviado e ainda não salvo: o relatório pode mostrar SÓ o que foi enviado ou o histórico + o enviado
(igual ao SM). O enviado é tratado pelas mesmas regras do "Salvar" e passa por um banco temporário em memória,
então os números e o Excel exportado saem iguais aos que sairão depois de salvar."""
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from .idioma import bi, frase

VER_TITULO = bi("查看与导出范围", "Visualização e exportação")                                                   # [revisar]
VER_ENVIADO = bi("仅上传的数据", "Só o que enviei (visualização)")                                          # [revisar]
VER_HISTORICO = bi("历史 + 上传的数据", "Soma com o histórico")                          # [revisar]
VER_AJUDA = ("Só o que enviei: tela e Excel exportado trazem apenas os arquivos enviados. "
             "Soma com o histórico: tela e Excel trazem o histórico salvo com os arquivos enviados por cima. O que aparece na tela é o que sai no Excel.")
AVISO_SO_ENVIADO = frase("当前仅显示已上传的文件，未合并历史数据；保存后才会计入历史。",             # [revisar]
                         "Mostrando só os arquivos enviados, sem somar o histórico. Salve para guardá-los no histórico.")
PENDENTES_AVISO = frase("以下数据尚未保存到历史，已计入当前统计。",                              # [revisar]
                        "Os dados enviados ainda não foram salvos no histórico, mas já entram nas tabelas abaixo.")


def engine_memoria():
    """Banco SQLite só em memória (some quando o processo acaba)."""
    return create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})


def combinar(chave_radio: str, hist: pd.DataFrame | None, pend: pd.DataFrame | None, chave: list, ids_brutos) -> pd.DataFrame:
    """Devolve a base a mostrar. Sem arquivo pendente: o histórico. Com pendente: radio na barra lateral."""
    hist = pd.DataFrame() if hist is None else hist
    if pend is None or pend.empty:
        return hist
    ver = st.sidebar.radio(VER_TITULO, ["env", "hist"], key=chave_radio, help=VER_AJUDA,
                           format_func=lambda v: VER_ENVIADO if v == "env" else VER_HISTORICO)
    if ver == "env" or hist.empty:
        st.info(AVISO_SO_ENVIADO if ver == "env" else PENDENTES_AVISO)
        return pend.reset_index(drop=True)
    st.info(PENDENTES_AVISO)
    ids = set(ids_brutos or [])
    antigo = hist[~hist["id"].astype(str).str.strip().isin(ids)] if ids else hist     # como o Salvar: o arquivo substitui o que já havia
    junto = pd.concat([antigo, pend], ignore_index=True)
    return junto.drop_duplicates(subset=chave, keep="last").reset_index(drop=True)
