"""Roda UM relatório num processo separado (python -m comum.envio_worker ...) e grava o que o envio dele mandaria.
Processo à parte porque o AppTest do Streamlit derruba o runtime do app que está rodando."""
import json
import pickle
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA_COMENTARIO = "\0COMENTARIO\0"


def main(pagina: str, prefixo: str, gran: str, ini: str, extras: dict, saida: str) -> None:
    import pandas as pd
    from streamlit.testing.v1 import AppTest

    sys.path.insert(0, str(RAIZ))
    from comum import feishu_envio as fe

    ini = pd.Timestamp(ini)
    at = AppTest.from_file(str(RAIZ / pagina), default_timeout=300)
    at.session_state[f"{prefixo}_gran"] = gran
    at.session_state[f"{prefixo}_per_{gran}"] = ini
    for k, v in extras.items():
        at.session_state[k] = v
    fe.CAPTURA = []
    at.run()
    achados, fe.CAPTURA = fe.CAPTURA, None
    erro = None
    if len(at.exception):
        erro = str(at.exception[0].value)
    elif len(at.error):
        erro = str(at.error[0].value)
    elif not achados:
        avisos = [str(x.value) for x in list(at.warning) + list(at.info)]
        erro = avisos[0] if avisos else "o relatório não chegou ao ponto de envio (sem dados?)"
    elif achados[0]["ini"] is None or pd.Timestamp(achados[0]["ini"]) != ini:
        erro = "sem dados para o período escolhido neste indicador"
    if erro:
        resultado = {"erro": erro[:400]}
    else:
        c = achados[0]
        itens = fe.montar_itens(ini=c["ini"], fim=c["fim"], dias=c["dias"], export=c["export"], titulo=c["titulo"],
                                periodo_xl=c["periodo_xl"], abertura=c["abertura"], blocos=c["blocos"],
                                saudar=True, comentario=MARCA_COMENTARIO)
        xl = c["excel"]()
        resultado = {"itens": itens, "nome_xl": c["nome_xl"], "xl": xl, "xl_sem_base": fe._sem_base(xl)}
    Path(saida).write_bytes(pickle.dumps(resultado))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], json.loads(sys.argv[5]), sys.argv[6])
