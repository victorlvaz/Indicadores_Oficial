"""Formatação visual das tabelas na tela (cor de meta, percentuais)."""
import pandas as pd

from .tema import CINZA_DESTAQUE, CSS_ABAIXO_META, VERDE, VERMELHO


def pct(v, sinal=False) -> str:
    """Percentual com 2 casas e vírgula (95,87%); "–" quando não há dado."""
    if pd.isna(v):
        return "–"
    return f"{v * 100:+.2f}".replace(".", ",") + "%" if sinal else f"{v * 100:.2f}".replace(".", ",") + "%"


def pp(v) -> str:
    """Variação em pontos percentuais com seta: ▲ +1,25 p.p. / ▼ -0,80 p.p.; "–" sem dado."""
    if pd.isna(v):
        return "–"
    x = round(v * 100, 2)
    seta = "▲" if x > 0 else "▼" if x < 0 else "＝"
    return f"{seta} {x:+.2f}".replace(".", ",") + " p.p."


def estilizar_tabela(df: pd.DataFrame, col_taxa: str, col_meta: str, col_comp: str | None = None,
                     col_var: str | None = None):
    """Tabela do dia pronta para exibir.
    - taxa abaixo da meta: fundo vermelho #E60000 com texto branco; atingiu a meta: sem cor
    - percentuais e ranking viram texto, com "–" onde não há dado (senão o Streamlit mostra "None")
    Se houver comparação (col_comp, col_var): a variação mostra seta ▲/▼ e a queda fica em vermelho."""
    col_rank = next((c for c in df.columns if str(c).startswith("排名")), df.columns[-1])
    abaixo = (df[col_taxa] < df[col_meta]).fillna(False)

    txt = df.copy()
    txt[df.columns[0]] = df[df.columns[0]].astype(str)      # coluna Nº mistura "合计" e números
    txt[col_taxa] = df[col_taxa].map(pct)
    txt[col_meta] = df[col_meta].map(pct)
    txt[col_rank] = df[col_rank].map(lambda v: "–" if pd.isna(v) else str(int(v)))
    if col_comp:
        txt[col_comp] = df[col_comp].map(pct)
        txt[col_var] = df[col_var].map(pp)

    estilos = pd.DataFrame("", index=txt.index, columns=txt.columns)
    estilos.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"   # linha de total (1ª)
    estilos.loc[abaixo, col_taxa] = CSS_ABAIXO_META
    if col_var:
        caiu = (df[col_var].round(4) < 0).fillna(False)
        estilos.loc[caiu, col_var] = f"color:{VERMELHO};font-weight:700"
        subiu = (df[col_var].round(4) > 0).fillna(False)
        estilos.loc[subiu, col_var] = f"color:{VERDE};font-weight:700"
    return txt.style.apply(lambda _: estilos, axis=None)


def estilizar_tendencia(df: pd.DataFrame):
    """Tabela de tendência pronta para exibir: percentuais em texto, "–" onde não há dado
    (o st.dataframe mostraria "None" em célula numérica vazia). A 2ª coluna (variação) mostra o sinal."""
    out = df.copy()
    for i, c in enumerate(out.columns[1:], start=1):
        out[c] = out[c].map(lambda v, s=(i == 1): pct(v, s))
    estilos = pd.DataFrame("", index=out.index, columns=out.columns)
    estilos.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"   # linha de total (1ª)
    return out.style.apply(lambda _: estilos, axis=None)
