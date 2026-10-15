"""Gráficos do Resumo (Altair). Cores: vermelho (principal) e cinza. Compartilhado entre os relatórios."""
import altair as alt
import pandas as pd

from .tema import VERMELHO

CINZA_BARRA = "#BFBFBF"
CINZA_META = "#808080"
CINZA_PONTO = "#8C8C8C"


def grafico_taxa(df: pd.DataFrame, ordem: list, meta: float | None = None, pequeno: bool = False,
                 titulo_y: str = "", titulo_periodo: str = "Período", titulo_taxa: str = "Taxa") -> alt.Chart:
    """Linha vermelha com pontos cinza; a meta (se houver) é uma linha tracejada cinza."""
    x = alt.X("periodo:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=-45, labelOverlap=True))
    y = alt.Y("taxa:Q", title=titulo_y, axis=alt.Axis(format=".0%"), scale=alt.Scale(zero=False))
    dica = [alt.Tooltip("periodo:N", title=titulo_periodo), alt.Tooltip("taxa:Q", title=titulo_taxa, format=".2%"),
            alt.Tooltip("prev:Q", title="Previsto"), alt.Tooltip("real:Q", title="Realizado")]
    base = alt.Chart(df)
    linha = base.mark_line(color=VERMELHO, strokeWidth=2.5).encode(x=x, y=y)
    pontos = base.mark_circle(size=18 if pequeno else 55, color=CINZA_PONTO).encode(x=x, y=y, tooltip=dica)
    camadas = [linha, pontos]
    if meta is not None:
        camadas.append(alt.Chart(pd.DataFrame({"meta": [meta]})).mark_rule(color=CINZA_META, strokeDash=[6, 4])
                       .encode(y="meta:Q"))
    return alt.layer(*camadas).properties(height=280)


def grafico_volume(df: pd.DataFrame, ordem: list, nome_prev: str, nome_real: str, titulo_y: str = "Volume",
                   titulo_periodo: str = "Período") -> alt.Chart:
    """Barras: previsto em cinza e realizado em vermelho por cima (a parte cinza visível é o que faltou)."""
    longo = df.melt(id_vars=["periodo"], value_vars=["prev", "real"], var_name="serie", value_name="valor")
    longo["ordem"] = longo["serie"].map({"prev": 0, "real": 1})
    longo["serie"] = longo["serie"].map({"prev": nome_prev, "real": nome_real})
    return alt.Chart(longo).mark_bar().encode(
        x=alt.X("periodo:N", sort=ordem, title=None, axis=alt.Axis(labelAngle=-45, labelOverlap=True)),
        y=alt.Y("valor:Q", stack=None, title=titulo_y),
        color=alt.Color("serie:N", title=None, sort=[nome_prev, nome_real],
                        scale=alt.Scale(domain=[nome_prev, nome_real], range=[CINZA_BARRA, VERMELHO]),
                        legend=alt.Legend(orient="top")),
        order=alt.Order("ordem:Q", sort="ascending"),
        tooltip=[alt.Tooltip("periodo:N", title=titulo_periodo), "serie:N", alt.Tooltip("valor:Q", title=titulo_y)],
    ).properties(height=280)
