"""Configuração dos indicadores de Lacre/Deslacre da linha secundária.
Tudo que muda com o layout do relatório, metas ou regras fica aqui."""
from pathlib import Path

APOIO = Path(__file__).parent / "apoio"

# chave interna -> nome da coluna no relatório extraído (linha 1)
COL = {
    "id": "Número do ID",
    "status": "Status",
    "viagem": "Nome da viagem",
    "tipo_linha": "Tipo de linha",
    "tipo_transportador": "Tipo de transportador",
    "condutor": "Condutor",                  # motorista (opcional)
    "pedido_mae": 'Número de " Pedido mãe"',
    "partida": "Nome de estação de partida",
    "reg_saida": "Regional de saída do carro",
    "chegada": "Nome de estação de chegada",
    "reg_chegada": "Regional de chegada do carro",
    "cod_chegada": "Código de estação de chegada",
    "chegada_plan": "Tempo de chegada planejado",
    "hora_lacre": "hora de lacre",
    "hora_deslacre": "hora de deslacre",
}

# Ordem das regionais nas tabelas de tendência (SR sempre por último; regiões novas depois de SR)
ORDEM_TENDENCIA = {
    "COLETA": ["SPN", "SPS", "GP", "SPE", "RJ", "PR", "MG", "CE"],
    "ENTREGA": ["CE", "SPN", "SPS", "GP", "SPE", "RJ", "PR", "MG", "BA"],
}
REGIOES = ["BA", "CE", "GP", "MG", "PR", "RJ", "SPE", "SPN", "SPS"]

# Regras de filtragem inferidas da base finalizada (29/09) -- confirmar com a equipe:
STATUS_VALIDOS = ("Concluído", "Em Trânsito")   # exclui Cancelado, Programado, Planejado
# + Franqueado: excluir "Tipo de transportador" = Franqueado
# + Pedido mãe: excluir vazio, 0 e 1 (manter só 2 ou mais)
# + remover viagens listadas em apoio/rotas_mesmo_sc.csv (transferência no mesmo SC)
# + Coleta: manter só partidas listadas em apoio/pontos_coleta.csv

TRANSPORTADOR_EXCLUIDO = "Franqueado"     # prefixo do valor, ex.: "Franqueado-加盟商"
PEDIDO_MAE_MINIMO = 2                     # vazio, 0 e 1 são excluídos

METAS = {"lacre": 0.95, "deslacre": 0.90}

# (tipo de linha, evento) -> definição da tabela
INDICADORES = {
    ("COLETA", "lacre"): {
        "titulo": "集货支线封车率 / Taxa de lacramento secundária - Coleta",
        "regiao_col": "reg_saida", "flag": "lacrado", "regiao_rot": "发车区域 Região Saída",
    },
    ("COLETA", "deslacre"): {
        "titulo": "集货支线解车率 / Taxa de deslacramento secundária - Coleta",
        "regiao_col": "reg_chegada", "flag": "deslacrado", "regiao_rot": "到车区域 Região chegada",
    },
    ("ENTREGA", "lacre"): {
        "titulo": "散货支线封车率 / Taxa de lacramento secundária - Entrega",
        "regiao_col": "reg_saida", "flag": "lacrado", "regiao_rot": "发车区域 Região Saída",
    },
    ("ENTREGA", "deslacre"): {
        "titulo": "散货支线解车率 / Taxa de deslacramento secundária - Entrega",
        "regiao_col": "reg_chegada", "flag": "deslacrado", "regiao_rot": "到车区域 Região chegada",
    },
}

ROTULOS = {
    "lacre": {"prev": "应封车 Lacre previsto", "real": "实际封车 Lacre realizado", "taxa": "封车率 Taxa de lacre"},
    "deslacre": {"prev": "应解车 Deslacre previsto", "real": "实际解车 Deslacre realizado", "taxa": "解车率 Taxa de deslacre"},
}
