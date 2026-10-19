"""Seletor do tamanho da tabela completa de tendência (padrão: últimos 7 períodos; dá para ampliar)."""
import streamlit as st

from . import periodos
from .idioma import bi

PADRAO = 7
UNIDADE = {"D": ("天", "dias"), "W": ("周", "semanas"), "M": ("个月", "meses"), "Y": ("年", "anos")}
TITULO = bi("完整表显示最近", "Tabela completa (variação e acumulado) mostra os últimos")


def escolher(gran: str, chave: str) -> int:
    """Mostra o seletor e devolve quantos períodos entram na tabela completa."""
    maximo = periodos.JANELA[gran]
    opcoes = [n for n in (PADRAO, 14) if n < maximo] + [maximo]
    zh, pt = UNIDADE[gran]

    def rotulo(n):
        return f"{n} (最大 máx.)" if n == maximo and n != PADRAO else str(n)

    n = st.radio(f"{TITULO}: {zh} {pt}", opcoes, index=0, horizontal=True, key=chave, format_func=rotulo)
    return int(n)
