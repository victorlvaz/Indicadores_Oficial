"""Formatação visual das tabelas na tela (cor de meta, percentuais)."""
import pandas as pd

from .tema import CINZA_DESTAQUE, CSS_ABAIXO_META


def pct(v, sinal=False) -> str:
    """Percentual com 2 casas e vírgula (95,87%); "–" quando não há dado."""
    if pd.isna(v):
        return "–"
    return f"{v * 100:+.2f}".replace(".", ",") + "%" if sinal else f"{v * 100:.2f}".replace(".", ",") + "%"


def estilizar_tabela(df: pd.DataFrame, col_taxa: str, col_meta: str):
    """Tabela do dia pronta para exibir.
    - taxa abaixo da meta: fundo vermelho #E60000 com texto branco; atingiu a meta: sem cor
    - percentuais e ranking viram texto, com "–" onde não há dado (senão o Streamlit mostra "None")
    A última coluna é o ranking."""
    col_rank = df.columns[-1]
    abaixo = (df[col_taxa] < df[col_meta]).fillna(False)

    txt = df.copy()
    txt[df.columns[0]] = df[df.columns[0]].astype(str)      # coluna Nº mistura "合计" e números
    txt[col_taxa] = df[col_taxa].map(pct)
    txt[col_meta] = df[col_meta].map(pct)
    txt[col_rank] = df[col_rank].map(lambda v: "–" if pd.isna(v) else str(int(v)))

    estilos = pd.DataFrame("", index=txt.index, columns=txt.columns)
    estilos.iloc[0, :] = f"background-color:{CINZA_DESTAQUE};font-weight:700"   # linha de total (1ª)
    estilos.loc[abaixo, col_taxa] = CSS_ABAIXO_META
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
