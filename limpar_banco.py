"""Esvazia o histórico de um banco (ex.: o Aiven que encheu), apagando as tabelas dos relatórios.

Uso (na pasta do projeto):
    python limpar_banco.py                 (pede a URL do banco; a senha não aparece na tela)
    python limpar_banco.py "URL_DO_BANCO"
    python limpar_banco.py --tudo          (apaga também o cadastro de líderes regionais)

No Postgres do Aiven, com o disco cheio o servidor fica só-leitura e bloqueia até o DELETE; este script liberta a escrita só
na sessão dele e usa DROP TABLE, que devolve o espaço na hora. As tabelas voltam a ser criadas vazias na próxima gravação.
Não mexe no arquivo local dados/historico.db."""
import argparse
import getpass
import sys

from sqlalchemy import create_engine, inspect, text

from app_uso import historico as app
from comum import lideres
from custos import historico as cu
from lacre_deslacre import historico as lac
from ocupacao import historico as oc
from pontualidade import historico as pt
from sm import historico as sm


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--tudo", action="store_true", help="apaga também o cadastro de líderes regionais")
    a = ap.parse_args()
    url = a.url or getpass.getpass("URL do banco (postgresql+psycopg2://...): ").strip()
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    if url.startswith("sqlite") and "historico.db" in url:
        print("Este é o banco local: não é o que o script deve limpar.")
        return 1
    tabelas = [t for mod in (lac, sm, app, oc, cu, pt) for t in mod.meta.sorted_tables]
    if a.tudo:
        tabelas.append(lideres.tabela)
    nomes = list(dict.fromkeys(t.name for t in tabelas))
    eng = create_engine(url, connect_args={"connect_timeout": 60} if url.startswith("postgresql") else {})
    with eng.connect() as con:
        existentes = set(inspect(con).get_table_names())
    alvo = [n for n in nomes if n in existentes]
    print(f"Banco: {eng.url.render_as_string(hide_password=True)}")
    print("Tabelas que serão APAGADAS:", ", ".join(alvo) or "(nenhuma)")
    if not alvo:
        return 0
    if input('Digite APAGAR para confirmar: ').strip() != "APAGAR":
        print("Cancelado, nada foi apagado.")
        return 1
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as con:
        if url.startswith("postgresql"):
            con.execute(text("SET default_transaction_read_only = OFF"))     # só nesta sessão
        for n in alvo:
            con.execute(text(f'DROP TABLE IF EXISTS "{n}"' + (" CASCADE" if url.startswith("postgresql") else "")))
            print("apagada:", n)
    print("Pronto. As tabelas voltam sozinhas, vazias, na próxima vez que você salvar um arquivo no app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
