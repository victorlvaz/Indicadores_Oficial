"""Envio geral: roda cada relatório (a página dele, sem desenhar nada na tela) para um período e recolhe o que o botão
"Enviar para o Feishu" de cada um enviaria. Assim a mensagem e o Excel saem IDÊNTICOS aos do envio individual.
Cada relatório roda num processo separado (comum/envio_worker.py)."""
import json
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from .envio_worker import MARCA_COMENTARIO, RAIZ

# (id, nome PT, nome ZH, página, prefixo das chaves da página, extras no session_state)
INDICADORES = [
    ("lac", "Lacre / Deslacre", "支线解封车率", "paginas/lacre_deslacre_tela.py", "lac", {"lac_ind": "lac"}),
    ("lac_pl", "Pontualidade do lacre", "封车准点率", "paginas/lacre_deslacre_tela.py", "lac", {"lac_ind": "pl"}),
    ("sm", "SM", "SM状态统计", "paginas/sm_tela.py", "sm", {}),
    ("app", "Uso de APP", "支线打卡率", "paginas/app_uso_tela.py", "app", {}),
    ("pt_chegada", "Pontualidade — Chegada", "支线准点率 — 到达", "paginas/pontualidade_tela.py", "pt", {"pt_ind": "CHEGADA"}),
    ("pt_saida", "Pontualidade — Saída", "支线准点率 — 发车", "paginas/pontualidade_tela.py", "pt", {"pt_ind": "SAIDA"}),
    ("oc", "Taxa de Ocupação", "装载率", "paginas/ocupacao_tela.py", "oc", {}),
]


def capturar(pagina: str, prefixo: str, extras: dict, gran: str, ini: pd.Timestamp) -> dict:
    """Devolve {itens, nome_xl, xl, xl_sem_base}. Levanta RuntimeError com o motivo se não der."""
    with tempfile.TemporaryDirectory() as pasta:
        saida = str(Path(pasta) / "r.pkl")
        proc = subprocess.run(
            [sys.executable, "-m", "comum.envio_worker", pagina, prefixo, gran, str(pd.Timestamp(ini).date()),
             json.dumps(extras), saida],
            cwd=str(RAIZ), capture_output=True, text=True, timeout=600, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if not Path(saida).exists():
            linhas = (proc.stderr or "").strip().splitlines()
            raise RuntimeError(("falha ao preparar: " + linhas[-1])[:400] if linhas else "falha ao preparar")
        r = pickle.loads(Path(saida).read_bytes())
    if "erro" in r:
        raise RuntimeError(r["erro"])
    return r


def itens_finais(cap: dict, saudar: bool, comentario: str) -> list:
    """Aplica saudação (só se saudar) e comentário (no lugar marcado) aos itens guardados."""
    itens = list(cap["itens"])
    if not saudar:
        itens = itens[1:]                                    # o 1º item é sempre a saudação
    linhas = [("linha", [t]) for t in (comentario or "").splitlines() if t.strip()]
    saida = []
    for it in itens:
        if it[0] == "linha" and it[1] == [MARCA_COMENTARIO]:
            saida.extend(linhas)
        else:
            saida.append(it)
    return saida
