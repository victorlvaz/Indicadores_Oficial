"""Gráficos em Plotly (vermelho e cinza). Usados no Resumo do SM."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .tema import VERMELHO

CINZA_BARRA = "#BFBFBF"
CINZA_PONTO = "#8C8C8C"
GRADE = "rgba(128,128,128,.25)"


def _pct(v) -> str:
    return "–" if pd.isna(v) else f"{v * 100:.1f}".replace(".", ",") + "%"


def cobertura(tab: pd.DataFrame, nome_real: str, nome_faltam: str, titulo_regional: str = "Regional") -> go.Figure:
    """Barras horizontais por regional: parte vermelha = realizado, cinza = o que faltou (a barra inteira é o previsto).
    tab tem as colunas regiao, prev, real, taxa (sem a linha de total), já em ordem de exibição."""
    r = tab["regiao"].tolist()
    fig = go.Figure()
    fig.add_bar(y=r, x=tab["real"], orientation="h", marker_color=VERMELHO, name=nome_real,
                hovertemplate="%{y}<br>" + nome_real + ": %{x:,}<extra></extra>")
    fig.add_bar(y=r, x=tab["prev"] - tab["real"], orientation="h", marker_color=CINZA_BARRA, name=nome_faltam,
                hovertemplate="%{y}<br>" + nome_faltam + ": %{x:,}<extra></extra>")
    fig.add_scatter(y=r, x=tab["prev"], mode="text", textposition="middle right", hoverinfo="skip", showlegend=False,
                    text=[f"  {_pct(t)} ({int(a)}/{int(p)})" for t, a, p in zip(tab["taxa"], tab["real"], tab["prev"])])
    teto = max(float(tab["prev"].max()), 1) * 1.4
    fig.update_layout(barmode="stack", bargap=0.3, height=70 + 46 * len(r), margin=dict(l=10, r=10, t=10, b=30),
                      legend=dict(orientation="h", y=1.12, x=0), yaxis=dict(autorange="reversed", showgrid=False),
                      xaxis=dict(range=[0, teto], gridcolor=GRADE, zeroline=False))
    return fig


def mini_graficos(df: pd.DataFrame, regionais: list, ordem: list, nome_taxa: str = "Taxa", colunas: int = 3) -> go.Figure:
    """Uma linha pequena por regional, cada uma com o seu próprio eixo (para ver a tendência de cada uma)."""
    linhas = -(-len(regionais) // colunas)
    fig = make_subplots(rows=linhas, cols=colunas, subplot_titles=[f"<b>{r}</b>" for r in regionais],
                        horizontal_spacing=0.07, vertical_spacing=0.18)
    for i, r in enumerate(regionais):
        d = df[df["regiao"] == r]
        pontos = len(d) <= 60
        fig.add_scatter(x=d["periodo"], y=d["taxa"], mode="lines+markers" if pontos else "lines", showlegend=False,
                        line=dict(color=VERMELHO, width=2), marker=dict(color=CINZA_PONTO, size=6), connectgaps=False,
                        customdata=d[["prev", "real"]], name=r,
                        hovertemplate="%{x}<br>" + nome_taxa + ": %{y:.1%}<br>%{customdata[1]} / %{customdata[0]}<extra>" + r + "</extra>",
                        row=i // colunas + 1, col=i % colunas + 1)
        v = d["taxa"].dropna()
        piso = max(0.0, (v.min() if len(v) else 0) - 0.08)
        fig.update_yaxes(tickformat=".0%", nticks=3, range=[piso, 1.03], gridcolor=GRADE, zeroline=False,
                         row=i // colunas + 1, col=i % colunas + 1)
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=ordem, showgrid=False, nticks=6,
                         tickangle=-45, tickfont=dict(size=10), row=i // colunas + 1, col=i % colunas + 1)
    fig.update_layout(height=190 * linhas + 60, margin=dict(l=10, r=10, t=30, b=10))
    return fig
