"""Configuração do relatório Taxa de Ocupação (装载率) da linha secundária.

Fonte: JMS > Transporte > Transporte de linha secundária > Consulta de Viagens Secundárias (o mesmo relatório do SM),
exportado UMA vez com Coleta e Entrega juntas (sem TECHIS). Filtro: horário planejado de saída (HOJE - 2).
"""
from pathlib import Path

APOIO = Path(__file__).parent.parent / "lacre_deslacre" / "apoio"      # lista de rotas do mesmo SC (a mesma dos outros)

# chave interna -> nomes aceitos para a coluna no relatório (o 1º que existir é usado)
COL = {
    "id": ["Tarefa de transporte No.", "Número do ID"],
    "status": ["Status"],
    "viagem": ["Nome da viagem"],
    "tipo_linha": ["Tipo de linha"],
    "tipo_transportador": ["Tipo de transportador"],
    "condutor": ["Condutor"],
    "partida": ["PDD de saida", "PDD de saída"],
    "saida_plan": ["Hora de saída planejada"],
    "placa": ["Placa do carro"],
    "volume": ['Número de " Pedido mãe"', 'Número de "Pedido mãe"', "Número de Pedido mãe"],   # volume carregado
    "veiculo": ["Tipo de veículo utilizado"],
    "reg_origem": ["Filial/Regional de Origem"],
}
COL_OPCIONAIS = {"placa", "condutor"}

# Regionais, na ordem da tabela detalhada da planilha. Qualquer regional nova que apareça nos dados entra no fim.
REGIOES = ["SPE", "SPS", "SPN", "RJ", "MG", "PR", "CE", "BA", "GP", "SR"]

# Capacidade (票数) por tipo de veículo = aba 车型核载票数 da planilha (igual em todas as regionais).
# Tipo de veículo não listado aqui (ex.: BARCO) fica sem capacidade e é avisado na aba Base.
CAPACIDADE = {
    "MOTO": 70, "PASSEIO": 200, "FIORINO": 300, "UTILITÁRIO": 600, "VAN": 900, "FURGAO": 900, "HR": 1200,
    "VUC": 1800, "3/4": 2800, "TOCO": 5280, "TRUCK": 6000, "CARRETA": 15000, "CAVALO": 15000,
}

# Regras (mesmas do SM, conferidas contra a planilha concluída de 14/10):
STATUS_VALIDOS = ("Concluído", "Em Trânsito")
TRANSPORTADOR_EXCLUIDO = "Franqueado"
# Pedido mãe (volume carregado): na planilha, a COLETA remove vazio, 0 e 1; a ENTREGA mantém o vazio (conta volume 0)
# e só remove 0 e 1. Valores: ("vazio", "zero_um") = o que remover.
PEDIDO_MAE_REMOVER = {"COLETA": ("vazio", "zero_um"), "ENTREGA": ("zero_um",)}
# A Coleta NÃO filtra "rota com coleta" (lista 揽收业务网点) neste relatório: a planilha não usa essa coluna.

META = None            # sem meta definida; com um valor (ex.: 0.80) o que ficar abaixo fica em vermelho

TIPOS = ("COLETA", "ENTREGA")
INDICADORES = {
    "COLETA": {"titulo": "集货装载率汇总表 / Tabela consolidada de ocupação – Coleta"},
    "ENTREGA": {"titulo": "散货装载率汇总表 / Tabela consolidada de ocupação – Entrega"},
}
