"""Corrige o contador (sequência) dos ids das tabelas no PostgreSQL depois de copiar dados com migrar_historico.py.

Sintoma: "duplicate key value violates unique constraint ..._cargas_pkey  Key (id)=(2) already exists".
Uso (na pasta do projeto):
    python corrigir_sequencias.py                     # usa a URL de [banco] do .streamlit/secrets.toml
    python corrigir_sequencias.py "URL_DO_BANCO"      # ou informe a URL
É seguro rodar mais de uma vez. Não apaga nem altera dados."""
import sys

from sqlalchemy import create_engine, text

TABELAS = ["lacre_cargas", "sm_cargas", "app_cargas", "oc_cargas", "cu_cargas", "pt_cargas", "lideres_regionais"]


def url_do_secrets() -> str | None:
    try:
        import tomllib
        with open(".streamlit/secrets.toml", "rb") as f:
            return tomllib.load(f)["banco"]["url"]
    except Exception:
        return None


def corrigir(engine) -> None:
    if engine.dialect.name != "postgresql":
        print("Banco não é PostgreSQL: nada a corrigir.")
        return
    with engine.begin() as con:
        for t in TABELAS:
            existe = con.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar()
            if not existe:
                continue
            seq = con.execute(text("SELECT pg_get_serial_sequence(:t, 'id')"), {"t": t}).scalar()
            if not seq:
                continue
            maior = con.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {t}")).scalar()
            con.execute(text("SELECT setval(:s, :v, :c)"), {"s": seq, "v": max(maior, 1), "c": maior > 0})
            print(f"{t}: próximo id = {maior + 1}")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else url_do_secrets()
    if not url:
        sys.exit("Informe a URL do banco: python corrigir_sequencias.py \"postgresql+psycopg2://...\"")
    corrigir(create_engine(url))
    print("Pronto.")
