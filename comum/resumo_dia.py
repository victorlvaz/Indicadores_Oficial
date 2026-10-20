"""Regra comum das abas Resumo: na visão "Dia", o Resumo segue o dia escolhido na barra lateral.
Semana e Mês continuam independentes (botões próprios da aba)."""
import pandas as pd
import streamlit as st

from .idioma import bi


def dia_lateral(gran: str, ini):
    """Dia escolhido na barra lateral (None se a barra não está em 'Dia' ou está em 'Todos')."""
    return pd.Timestamp(ini) if gran == "D" and ini is not None else None


def aplicar(freq: str, ini, fim, dia):
    """Visão Dia + dia da barra lateral -> (ini, fim) = só esse dia. Caso contrário devolve o que veio."""
    if freq != "D" or dia is None:
        return ini, fim
    st.caption(bi("日视图：跟随左侧边栏所选日期", "Visão Dia: segue o dia escolhido na barra lateral") + f" · {dia:%d/%m/%Y}")
    return dia, dia
