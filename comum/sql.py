"""Apoio a gravações em banco que funcionam bem também em servidor remoto (Neon, Azure SQL...)."""
import time
from functools import wraps

from sqlalchemy import delete, tuple_
from sqlalchemy.exc import InterfaceError, OperationalError

LOTE = 400          # chaves por comando (x nº de colunas da chave = parâmetros; abaixo dos limites do SQLite e do Postgres)


def apagar_por_chaves(con, tabela, colunas: list[str], chaves: list[tuple], lote: int = LOTE) -> int:
    """Apaga as linhas cujas `colunas` (a chave) estão em `chaves`, em lotes: ~1 comando por 400 linhas.
    NÃO usar executemany com bindparam: o driver do Postgres manda um comando por linha e, num servidor remoto,
    apagar 50 mil linhas leva dezenas de minutos."""
    cols = tuple_(*[tabela.c[c] for c in colunas])
    for i in range(0, len(chaves), lote):
        con.execute(delete(tabela).where(cols.in_(chaves[i:i + lote])))
    return len(chaves)


def apagar_por_ids(con, tabela, ids, coluna: str = "id", lote: int = 400) -> int:
    """Apaga TODAS as linhas cujo `coluna` está em `ids` (em lotes). Usado para "reprocessar o arquivo inteiro":
    viagens que o filtro novo agora exclui também saem do histórico, em vez de ficarem lá com a regra antiga."""
    ids = list(dict.fromkeys(i for i in ids if i))
    for i in range(0, len(ids), lote):
        con.execute(delete(tabela).where(tabela.c[coluna].in_(ids[i:i + lote])))
    return len(ids)


def ids_do_arquivo(df, coluna) -> list:
    """IDs de viagem de TODAS as linhas do arquivo lido (antes dos filtros). `coluna` = nome ou lista de nomes possíveis."""
    nomes = [coluna] if isinstance(coluna, str) else list(coluna)
    achou = next((n for n in nomes if n in df.columns), None)
    if achou is None:
        return []
    s = df[achou].dropna().astype(str).str.strip()
    s = s[s.ne("") & ~s.str.upper().isin(["NAN", "NONE"])]
    return list(dict.fromkeys(list(s) + list(s.str.upper())))


def com_reconexao(funcao, tentativas: int = 4):
    """Repete a gravação inteira se o servidor derrubar a conexão no meio (ex.: "SSL connection has been closed unexpectedly",
    comum em banco grátis na nuvem). Seguro porque cada `salvar` roda numa única transação: se cair, nada foi gravado,
    e reenviar o mesmo dia só atualiza as linhas (sem duplicar)."""
    @wraps(funcao)
    def interna(engine, *args, **kwargs):
        ultimo = None
        for t in range(tentativas):
            try:
                return funcao(engine, *args, **kwargs)
            except (OperationalError, InterfaceError) as erro:
                ultimo = erro
                engine.dispose()                      # descarta as conexões quebradas; a próxima tentativa abre uma nova
                time.sleep(2 * (t + 1))
        raise ultimo
    return interna
