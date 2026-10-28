"""Copia o histórico do arquivo local (dados/historico.db) para outro banco (servidor), uma única vez.

Uso (na pasta do projeto):
    python migrar_historico.py "URL_DO_BANCO_DESTINO"
Exemplo de URL: postgresql+psycopg2://usuario:senha@servidor:5432/banco   (ver comum/banco.py)
Origem diferente do padrão:  python migrar_historico.py "URL_DESTINO" --origem "sqlite:///caminho/outro.db"

Só a partir de uma data (ex.: setembro):  python migrar_historico.py "URL_DESTINO" --desde 2026-09-01
As tabelas são criadas no destino. Se uma tabela do destino já tiver dados, ela é pulada (nada é duplicado nem apagado);
use --substituir para esvaziar e copiar de novo.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, delete, func, inspect, select

from lacre_deslacre import historico as lac
from app_uso import historico as app
from custos import historico as cu
from ocupacao import historico as oc
from pontualidade import historico as pt
from sm import historico as sm
from comum import lideres

RAIZ = Path(__file__).resolve().parent
TABELAS = [lac.viagens, lac.cargas, sm.viagens, sm.cargas, app.viagens, app.cargas, app.transportadores, oc.viagens, oc.cargas, cu.viagens, cu.cargas, pt.trechos, pt.cargas, lideres.tabela]
LOTE = 5000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("destino")
    ap.add_argument("--origem", default="sqlite:///" + (RAIZ / "dados" / "historico.db").as_posix())
    ap.add_argument("--substituir", action="store_true")
    ap.add_argument("--desde", help="copia só as viagens com dia >= AAAA-MM-DD (o resto fica só no arquivo local)")
    a = ap.parse_args()
    if a.destino == a.origem:
        print("Origem e destino são iguais.")
        return 1
    org, dst = create_engine(a.origem), create_engine(a.destino)
    lac.meta.create_all(dst)
    sm.meta.create_all(dst)
    app.meta.create_all(dst)
    oc.meta.create_all(dst)
    cu.meta.create_all(dst)
    pt.meta.create_all(dst)
    lideres.meta.create_all(dst)
    existentes = set(inspect(org).get_table_names())
    for t in TABELAS:
        if t.name not in existentes:
            print(f"{t.name}: não existe na origem, pulada")
            continue
        with dst.begin() as con:
            ja = con.execute(select(func.count()).select_from(t)).scalar()
            if ja and not a.substituir:
                print(f"{t.name}: destino já tem {ja} linhas, pulada (use --substituir para copiar de novo)")
                continue
            if ja:
                con.execute(delete(t))
            copiadas = 0
            with org.connect() as o:
                consulta = select(t)
                col_dia = next((c for c in ("dia", "dia_saida") if c in t.columns), None)
                if a.desde and col_dia:
                    consulta = consulta.where(t.c[col_dia] >= pd.Timestamp(a.desde).date())
                for lote in pd.read_sql(consulta, o, chunksize=LOTE):
                    if lote.empty:
                        continue
                    lote = lote.astype(object).where(lote.notna(), None)
                    for c in t.columns:
                        if type(c.type).__name__ in ("DateTime", "Date"):
                            lote[c.name] = [None if (v is None or pd.isna(v)) else pd.Timestamp(v).to_pydatetime() if type(c.type).__name__ == "DateTime"
                                            else pd.Timestamp(v).date() for v in lote[c.name]]
                    lote = lote.astype(object).where(lote.notna(), None)
                    con.execute(t.insert(), [{k: (None if (v is not None and not isinstance(v, (str, bytes)) and pd.isna(v)) else v) for k, v in r.items()} for r in lote.to_dict("records")])
                    copiadas += len(lote)
        print(f"{t.name}: {copiadas} linhas copiadas")
    from corrigir_sequencias import corrigir
    corrigir(dst)                                  # PostgreSQL: o contador dos ids precisa continuar depois dos copiados
    print("Pronto. Configure a mesma URL em .streamlit/secrets.toml ([banco] url = ...) para o app usar esse banco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
