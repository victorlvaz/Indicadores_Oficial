"""Apoio ao app bilíngue (chinês + português).

Regras de uso:
  - cabecalho(zh, pt): título da página, chinês ACIMA do português
  - bi(zh, pt):        nomes/rótulos, LADO A LADO ("支线 Linha secundária")
  - frase(zh, pt):     mensagens longas, chinês na 1ª linha e português na 2ª
"""
import html


def bi(zh: str, pt: str) -> str:
    return f"{zh} {pt}"


def frase(zh: str, pt: str) -> str:
    return f"{zh}  \n{pt}"        # dois espaços + quebra = nova linha no markdown


def rodape(zh_linhas: list[str], pt_linhas: list[str]) -> None:
    """Nota abaixo da tabela, centralizada: chinês em cima, português embaixo."""
    import streamlit as st

    def bloco(linhas):
        return "<br>".join(html.escape(l) for l in linhas)

    st.html(
        '<div style="text-align:center;font-size:.85rem;line-height:1.55;opacity:.8;margin:.25rem auto 1.25rem;max-width:900px">'
        f'<div>{bloco(zh_linhas)}</div><div style="margin-top:.35rem">{bloco(pt_linhas)}</div></div>'
    )


def cabecalho(zh: str, pt: str) -> None:
    import streamlit as st          # só aqui: o resto do módulo funciona sem Streamlit (ex.: validar)

    st.html(
        '<div style="margin:0 0 .75rem">'
        f'<h1 style="margin:0;padding:0;font-size:2.4rem;font-weight:700;line-height:1.25">{html.escape(zh)}</h1>'
        f'<h2 style="margin:.2rem 0 0;padding:0;font-size:1.55rem;font-weight:600;line-height:1.3;opacity:.85">'
        f'{html.escape(pt)}</h2></div>'
    )
