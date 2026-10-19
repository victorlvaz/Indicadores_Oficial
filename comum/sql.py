"""Apoio a gravações em banco que funcionam bem também em servidor remoto (Neon, Azure SQL...)."""
from sqlalchemy import delete, tuple_

LOTE = 400          # chaves por comando (x nº de colunas da chave = parâmetros; abaixo dos limites do SQLite e do Postgres)


def apagar_por_chaves(con, tabela, colunas: list[str], chaves: list[tuple], lote: int = LOTE) -> int:
    """Apaga as linhas cujas `colunas` (a chave) estão em `chaves`, em lotes: ~1 comando por 400 linhas.
    NÃO usar executemany com bindparam: o driver do Postgres manda um comando por linha e, num servidor remoto,
    apagar 50 mil linhas leva dezenas de minutos."""
    cols = tuple_(*[tabela.c[c] for c in colunas])
    for i in range(0, len(chaves), lote):
        con.execute(delete(tabela).where(cols.in_(chaves[i:i + lote])))
    return len(chaves)
