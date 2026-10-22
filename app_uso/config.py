"""Configuração do relatório Taxa de Uso de APP (打卡率) da linha secundária.
Tudo que muda com o layout do relatório, meta ou regras fica aqui."""
from pathlib import Path

APOIO = Path(__file__).parent.parent / "lacre_deslacre" / "apoio"      # mesma lista de rotas do mesmo SC do Lacre

# chave interna -> nome da coluna no relatório extraído (linha 1)
COL = {
    "id": "Número do ID",
    "status": "Status",
    "viagem": "Nome da viagem",
    "tipo_linha": "Tipo de linha",
    "tipo_transportador": "Tipo de transportador",
    "condutor": "Condutor",                  # motorista (opcional)
    "partida": "Nome de estação de partida",
    "reg_saida": "Regional de saída do carro",
    "reg_chegada": "Regional de chegada do carro",
    "cod_chegada": "Código de estação de chegada",
    "chegada_plan": "Tempo de chegada planejado",
    "hora_checkout": "Horário de check-out do codutor",
    "hora_checkin": "Horário de check-in do motorista",
}

# Regionais da planilha do Lucas (todas entram no total). Qualquer regional nova que apareça nos dados é incluída.
REGIOES = ["GP", "SPS", "RJ", "SPN", "BA", "MG", "CE", "SPE", "PR", "SR"]

# Regras (passo a passo "Relatorio Taxa de Uso do APP.docx"):
STATUS_VALIDOS = ("Concluído", "Em Trânsito")       # só concluído e em trânsito
TRANSPORTADOR_EXCLUIDO = "Franqueado"               # prefixo, ex.: "Franqueado-加盟商"
# + rotas do mesmo SC: excluir (coletas E entregas, diferente do Lacre/Deslacre)
# + transportador vazio: usar o último valor conhecido da mesma viagem (tabela app_transportadores)

PREVISTO_POR_VIAGEM = 2        # cada viagem tem 2 batidas previstas: check-out (saída) e check-in (chegada)
META = 0.95

# tipo de linha -> definição
INDICADORES = {
    "COLETA": {"regiao_col": "reg_saida", "regiao_rot": "发车区域 Região Origem",
               "titulo": "支线集货打卡率 / Taxa de utilização no APP da Coleta Secundária"},
    "ENTREGA": {"regiao_col": "reg_chegada", "regiao_rot": "到车区域 Região Destino",
                "titulo": "支线散货打卡率 / Taxa de utilização no APP da Entrega Secundária"},
}
ORDEM_TENDENCIA = REGIOES
