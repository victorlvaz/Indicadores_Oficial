"""Guarda a linha ORIGINAL do JMS (todas as colunas, na ordem do arquivo) junto de cada viagem do histórico,
para a base exportada sair idêntica à que as regionais já conhecem.

A linha vai compactada (JSON + zlib + base64) numa coluna de texto "original" da tabela de viagens: ~4x menor que o JSON puro."""
import base64
import json
import re
import zlib
from datetime import date, datetime, time

import pandas as pd
from sqlalchemy import inspect, select

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")


def _valor(v):
    if v is None or (not isinstance(v, (str, bytes)) and pd.isna(v)):
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat(sep=" ")
    if isinstance(v, (date, time)):
        return v.isoformat()
    if hasattr(v, "item"):                       # numpy -> Python
        return v.item()
    return v


def empacotar(df_raw: pd.DataFrame) -> list[str]:
    """Uma string compactada por linha, com todas as colunas do arquivo original (mesma ordem, mesmos nomes)."""
    cols = [str(c) for c in df_raw.columns]
    out = []
    for linha in df_raw.itertuples(index=False, name=None):
        d = {c: _valor(v) for c, v in zip(cols, linha)}
        out.append(base64.b64encode(zlib.compress(json.dumps(d, ensure_ascii=False).encode("utf-8"), 6)).decode("ascii"))
    return out


def anexar(b: pd.DataFrame, df_raw: pd.DataFrame) -> pd.DataFrame:
    """Põe a coluna "original" em `b` (linhas que sobraram do tratamento; o índice de `b` é o do arquivo)."""
    b = b.copy()
    b["original"] = pd.Series(empacotar(df_raw.loc[b.index]), index=b.index)
    return b


_CJK = re.compile(r"[\u2e80-\u9fff\uff00-\uffef]")
_KM_GOOGLE = re.compile(r"km\s*google|tipo de horas extras|hor[aá]rio previsto de chegada", re.I)


def coluna_indesejada(nome) -> bool:
    """Colunas que não vão para a base exportada: nome em chinês, "Km Google", "Tipo de horas extras" e
    "Horário previsto de chegada" (as colunas de chegada planejada, que o app usa, continuam)."""
    n = str(nome)
    return bool(_CJK.search(n) or _KM_GOOGLE.search(n))


def _restaurar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        s = df[c]
        txt = s.dropna()
        if len(txt) and txt.map(lambda v: isinstance(v, str) and bool(_ISO.match(v))).all():
            df[c] = pd.to_datetime(s, errors="coerce")
    return df


def desempacotar(textos) -> pd.DataFrame:
    linhas = [json.loads(zlib.decompress(base64.b64decode(t)).decode("utf-8")) for t in textos if isinstance(t, str) and t]
    df = pd.DataFrame(linhas)
    indesejadas = [c for c in df.columns if coluna_indesejada(c)]
    if {"Previsão de chegada", "Pontual na chegada"} <= set(df.columns):
        # "Exportação de detalhes" (extract novo): sai com TODAS as colunas dele; nas linhas vindas do consolidado, as indesejadas ficam vazias
        ext = df["Previsão de chegada"].notna() & df["Pontual na chegada"].notna()
        df.loc[~ext, indesejadas] = None
        return _restaurar_tipos(df)
    return _restaurar_tipos(df.drop(columns=indesejadas))


def garantir_coluna(engine, tabela) -> None:
    """Bancos criados antes: acrescenta a coluna "original" (texto) se ainda não existir."""
    if "original" not in {c["name"] for c in inspect(engine).get_columns(tabela.name)}:
        tipo = "NVARCHAR(MAX)" if engine.dialect.name == "mssql" else "TEXT"
        with engine.begin() as con:
            con.exec_driver_sql(f"ALTER TABLE {tabela.name} ADD COLUMN original {tipo}" if tipo == "TEXT"
                                else f"ALTER TABLE {tabela.name} ADD original {tipo}")


def ler(engine, tabela, coluna_dia: str, ini, fim) -> pd.DataFrame:
    """Linhas originais das viagens do período [ini, fim] (datas ou None para tudo), na ordem do dia.
    Linhas gravadas antes desta função existir não têm original e ficam de fora."""
    garantir_coluna(engine, tabela)
    q = select(tabela.c.original).where(tabela.c.original.is_not(None))
    if ini is not None:
        q = q.where(tabela.c[coluna_dia] >= pd.Timestamp(ini).date())
    if fim is not None:
        q = q.where(tabela.c[coluna_dia] <= pd.Timestamp(fim).date())
    q = q.order_by(tabela.c[coluna_dia])
    with engine.connect() as con:
        textos = [r[0] for r in con.execute(q)]
    return desempacotar(textos)


# ---------- exportar a base ----------
def _chave_valor(v):
    if isinstance(v, (pd.Timestamp, datetime)) or hasattr(v, "year") and hasattr(v, "hour"):
        return pd.Timestamp(v).to_pydatetime()
    if hasattr(v, "year"):
        return pd.Timestamp(v).date()
    return str(v).strip()


def _do_banco(engine, tabela, chave: list[str], coluna_dia: str, sub: pd.DataFrame, faltam: pd.Series) -> dict:
    """{chave da viagem: texto compactado} das viagens de `sub` marcadas em `faltam` (só o período delas)."""
    garantir_coluna(engine, tabela)
    dias = pd.to_datetime(sub.loc[faltam, coluna_dia])
    q = (select(*[tabela.c[c] for c in chave], tabela.c.original)
         .where(tabela.c.original.is_not(None))
         .where(tabela.c[coluna_dia] >= dias.min().date()).where(tabela.c[coluna_dia] <= dias.max().date()))
    with engine.connect() as con:
        linhas = con.execute(q).fetchall()
    return {tuple(_chave_valor(v) for v in r[:-1]): r[-1] for r in linhas}


def _textos(engine, tabela, chave, coluna_dia, sub: pd.DataFrame) -> pd.Series:
    """Texto compactado de cada linha de `sub`: o que já veio no próprio arquivo ainda não salvo, senão o do banco."""
    sub = sub.reset_index(drop=True)
    textos = sub["original"].copy() if "original" in sub.columns else pd.Series([None] * len(sub), dtype=object)
    faltam = textos.isna()
    if faltam.any() and len(sub):
        mapa = _do_banco(engine, tabela, chave, coluna_dia, sub, faltam)
        chaves = [tuple(_chave_valor(v) for v in r) for r in sub.loc[faltam, chave].itertuples(index=False, name=None)]
        textos = textos.astype(object)
        textos.loc[faltam] = [mapa.get(k) for k in chaves]
    return textos


def base_original(engine, tabela, chave: list[str], coluna_dia: str, sub: pd.DataFrame):
    """(linhas no formato original do JMS, linhas de `sub` que ainda não têm original). Mesma ordem de `sub`."""
    sub = sub.reset_index(drop=True)
    textos = _textos(engine, tabela, chave, coluna_dia, sub)
    tem = textos.notna()
    return desempacotar(textos[tem]), sub[~tem]


def _antigas_como_jms(sem: pd.DataFrame, jms: dict) -> pd.DataFrame:
    """Viagens gravadas antes de existir o original: só as colunas que o app guardava, com os nomes do JMS."""
    mapa = {k: (v if isinstance(v, str) else v[0]) for k, v in jms.items() if k in sem.columns and v}
    d = sem[list(mapa)].rename(columns=mapa)
    return d.drop(columns=[c for c in d.columns if coluna_indesejada(c)])


def base_primeiro(export: dict, engine, tabela, chave: list[str], coluna_dia: str, sub: pd.DataFrame, jms: dict,
                  nome: str = "已处理数据 Base tratada") -> dict:
    """Como comum.exportar.base_primeiro, mas a base sai IDÊNTICA ao arquivo do JMS (todas as colunas, mesma ordem), numa
    aba só. Viagens gravadas antes de existir o original entram na mesma aba, só com as colunas que o app guardava
    (as demais ficam vazias); reenviar o arquivo daquele dia completa as colunas."""
    orig, sem = base_original(engine, tabela, chave, coluna_dia, sub)
    base = orig
    if len(sem):
        antigas = _antigas_como_jms(sem, jms)
        base = antigas if orig.empty else pd.concat([orig, antigas], ignore_index=True)
    return {nome[:31]: (base.head(1_048_575), {"sem_pct": True}), **export}


def completar_colunas(engine, tabela, chave: list[str], coluna_dia: str, sub: pd.DataFrame) -> pd.DataFrame:
    """SM: devolve `sub` com as colunas originais do JMS preenchidas também nas linhas vindas do banco."""
    sub = sub.reset_index(drop=True)
    textos = _textos(engine, tabela, chave, coluna_dia, sub)
    tem = textos.notna() & (sub["original"].isna() if "original" in sub.columns else True)
    if not tem.any():
        return sub.drop(columns=["original"], errors="ignore")
    o = desempacotar(textos[tem])
    o.index = sub.index[tem]
    out = sub.drop(columns=["original"], errors="ignore").copy()
    for c in o.columns:
        if c in out.columns:
            out[c] = out[c].where(out[c].notna(), o[c].reindex(out.index))
        else:
            out[c] = o[c].reindex(out.index)
    return out
