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


def ranking_meta(tab: pd.DataFrame, meta: float, nome_taxa: str = "Taxa") -> go.Figure:
    """Ranking: uma haste por regional até a taxa (vermelha se abaixo da meta, cinza se atingiu) e a linha da meta.
    tab: colunas regiao, prev, real, taxa (sem o total). Ordena da melhor para a pior."""
    t = tab.dropna(subset=["taxa"]).sort_values("taxa", ascending=False)
    r, x = t["regiao"].tolist(), t["taxa"].tolist()
    cor = [VERMELHO if v < meta else CINZA_PONTO for v in x]
    fig = go.Figure()
    for reg, v, c in zip(r, x, cor):
        fig.add_shape(type="line", x0=0, x1=v, y0=reg, y1=reg, line=dict(color=c, width=4))
    fig.add_scatter(x=x, y=r, mode="markers+text", marker=dict(color=cor, size=15), showlegend=False,
                    text=[_pct(v) for v in x], textposition="middle right", customdata=t[["real", "prev"]],
                    hovertemplate="%{y}<br>" + nome_taxa + ": %{x:.1%}<br>%{customdata[0]} / %{customdata[1]}<extra></extra>")
    fig.add_vline(x=meta, line=dict(color="#555555", dash="dash", width=1.5),
                  annotation_text=f"Meta {_pct(meta)}", annotation_position="top")
    piso = max(0.0, min(x + [meta]) - 0.12) if x else 0
    fig.update_layout(height=70 + 40 * max(len(r), 1), margin=dict(l=10, r=40, t=30, b=20),
                      yaxis=dict(autorange="reversed", showgrid=False, type="category"),
                      xaxis=dict(range=[piso, 1.08], tickformat=".0%", gridcolor=GRADE, zeroline=False))
    return fig


def mapa_calor(df: pd.DataFrame, regionais: list, ordem: list, meta: float, nome_taxa: str = "Taxa") -> go.Figure:
    """Regional (linhas) x período (colunas). Abaixo da meta = tons de vermelho; atingiu a meta = cinza claro.
    df: colunas regiao, periodo, prev, real, taxa."""
    z = df.pivot_table(index="regiao", columns="periodo", values="taxa", aggfunc="first").reindex(index=regionais, columns=ordem)
    n = df.pivot_table(index="regiao", columns="periodo", values="real", aggfunc="first").reindex(index=regionais, columns=ordem)
    p = df.pivot_table(index="regiao", columns="periodo", values="prev", aggfunc="first").reindex(index=regionais, columns=ordem)
    piso = max(0.0, float(z.min().min()) - 0.02) if z.notna().any().any() else 0.0
    escala = [[0.0, VERMELHO], [max(min((meta - piso) / (1 - piso), 0.999), 0.001) if piso < 1 else 0.5, "#F3C4C4"],
              [max(min((meta - piso) / (1 - piso), 0.999), 0.001) + 0.0005 if piso < 1 else 0.51, "#D9D9D9"], [1.0, "#EDEDED"]]
    texto = z.map(lambda v: "" if pd.isna(v) else f"{v * 100:.0f}") if hasattr(z, "map") else z.applymap(lambda v: "" if pd.isna(v) else f"{v * 100:.0f}")
    fig = go.Figure(go.Heatmap(
        z=z.values, x=list(z.columns), y=list(z.index), zmin=piso, zmax=1.0, colorscale=escala, xgap=2, ygap=2,
        text=texto.values, texttemplate="%{text}", showscale=False, hoverongaps=False,
        customdata=list(zip(n.values.tolist(), p.values.tolist())),
        hovertemplate="%{y} · %{x}<br>" + nome_taxa + ": %{z:.1%}<extra></extra>"))
    fig.update_layout(height=70 + 34 * max(len(regionais), 1), margin=dict(l=10, r=10, t=10, b=10),
                      yaxis=dict(autorange="reversed", type="category"), xaxis=dict(type="category", side="top", tickangle=-45))
    return fig
