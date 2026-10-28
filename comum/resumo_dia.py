"""Regra comum das abas Resumo: os filtros Dia/Semana/Mês são da PRÓPRIA aba (não seguem a barra lateral).
Na visão "Dia" a aba tem seu próprio seletor de data; vazio = todos os dias do período (ano) escolhido."""
import pandas as pd
import streamlit as st

from .idioma import bi


def dia_lateral(gran: str, ini):
    """Mantida por compatibilidade: a aba Resumo não segue mais a barra lateral."""
    return None


def aplicar(freq: str, ini, fim, dia=None):
    """Visão Dia -> seletor de data próprio da aba (vazio = todos os dias). Semana/Mês: devolve o que veio."""
    if freq != "D":
        return ini, fim
    escolhido = st.date_input(bi("选择日期（留空=全部日期）", "Dia (vazio = todos os dias do período)"),
                              value=None, format="DD/MM/YYYY", key="resumo_dia_proprio")
    if escolhido is None:
        return ini, fim
    d = pd.Timestamp(escolhido)
    return d, d
