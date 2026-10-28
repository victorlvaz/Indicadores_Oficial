"""Configuração do relatório de Pontualidade (准点率) da linha secundária: Taxa de Chegada e Taxa de Saída.
Tudo que muda com o layout do relatório, meta ou regras fica aqui."""

from pathlib import Path

# chave interna -> nome da coluna no relatório consolidado da linha secundária (linha 1)
COL = {
    "id": "Número do ID",
    "status": "Status",
    "viagem": "Nome da viagem",
    "tipo_linha": "Tipo de linha",
    "cod_partida": "Código de estação de partida",
    "partida": "Nome de estação de partida",
    "reg_saida": "Regional de saída do carro",
    "cod_chegada": "Código de estação de chegada",
    "chegada": "Nome de estação de chegada",
    "reg_chegada": "Regional de chegada do carro",
    "saida_plan": "Tempo de partida planejada",
    "saida_real": "Horário real de saída",
    "chegada_plan": "Tempo de chegada planejado",
    "chegada_real": "Tempo real de chegada",
    "tipo_transportador": "Tipo de transportador",
}
PEDIDO_MAE_NOMES = ['Número de " Pedido mãe"', 'Número de "Pedido mãe"', "Número de Pedido mãe"]
PEDIDO_MAE_MINIMO = 2                             # vazio, 0 e 1 são excluídos (mesma regra dos outros relatórios)
TRANSPORTADOR_EXCLUIDO = "Franqueado"             # prefixo, ex.: "Franqueado-加盟商"
APOIO = Path(__file__).parent.parent / "lacre_deslacre" / "apoio"      # lista de rotas do mesmo SC (compartilhada)

REGIOES = ["GP", "SPS", "RJ", "SPN", "BA", "MG", "CE", "SPE", "PR", "SR"]    # qualquer regional nova também entra

STATUS_VALIDOS = ("Concluído", "Em Trânsito")     # igual à planilha: só concluído e em trânsito
INICIO_DIA_HORAS = 8                              # o "dia" da operação começa às 08:00 (igual à coluna Data da planilha)
META = 0.95

# Indicador -> como o horário planejado/real é comparado e qual horário define o dia.
IND = {
    "CHEGADA": {"plan": "chegada_plan", "real": "chegada_real", "dia": "dia_chegada", "ok": "ok_chegada", "aberto": "aberto_chegada"},
    "SAIDA": {"plan": "saida_plan", "real": "saida_real", "dia": "dia_saida", "ok": "ok_saida", "aberto": "aberto_saida"},
}

# Tipo de linha -> qual regional agrupa (igual à planilha: Coleta pela origem, Entrega pelo destino)
TIPOS = {
    "COLETA": {"regiao_col": "reg_saida", "regiao_rot": "发车区域 Região Origem"},
    "ENTREGA": {"regiao_col": "reg_chegada", "regiao_rot": "到车区域 Região Destino"},
}
ORDEM_TENDENCIA = REGIOES
