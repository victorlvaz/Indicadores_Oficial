"""Configuração do relatório Estatística de Status dos SMs (SM状态统计).
Tudo que muda com o layout dos relatórios, regras ou regiões fica aqui.

Fontes:
  - JMS: Transporte > Transporte de linha secundária > Consulta de Viagens Secundárias,
         exportado duas vezes (Tipo de linha = Coleta e = Entrega), filtrando o horário planejado de saída.
  - TECHIS: Ger. Risco > Monitoramento > Liberação, todos os status, "Exportar Excel (todas as viagens)".
"""
from pathlib import Path

APOIO = Path(__file__).parent / "apoio"

TIPOS = ("COLETA", "ENTREGA")

# chave interna -> nomes aceitos para a coluna no relatório do JMS (o 1º que existir é usado)
COL_JMS = {
    "id": ["Tarefa de transporte No.", "Número do ID"],
    "status": ["Status"],
    "viagem": ["Nome da viagem"],
    "rota": ["Nome da rota"],                      # coluna G do JMS: a rota correta; vazia nas Horas Extras
    "tipo_transportador": ["Tipo de transportador"],
    "condutor": ["Condutor"],
    "transportador": ["Abreviatura de transportador"],
    "pedido_mae": ['Número de " Pedido mãe"', 'Número de "Pedido mãe"', "Número de Pedido mãe"],
    "partida": ["PDD de saida", "PDD de saída"],
    "chegada": ["PDD de chegada"],
    "saida_plan": ["Hora de saída planejada"],
    "placa": ["Placa do carro"],
    "regiao": ["Filial/Regional de Origem"],
    "regiao_destino": ["Filial/Regional de destino"],
}
# opcionais: se não existirem no arquivo, ficam vazias
COL_JMS_OPCIONAIS = {"condutor", "transportador", "chegada", "placa", "regiao_destino", "rota"}

# Anotação: remover do relatório do JMS
COLUNAS_REMOVER = ["Km Google", "CHECK-IN"]

# Colunas de fórmula da planilha (nomes usados na aba de base exportada / histórico)
COLUNAS_CALCULADAS = {
    "rota": "ROTA", "sm_prev": "SM previsto", "sm_real": "SM realizado", "dia": "Data saida planejado",
    "mesmo_sc": "Rota do mesmo SC", "coleta": "Avaliar se rota com coleta",
    "trechos": "Quantidade de trechos",          # só existe na planilha antiga; é descartada ao reler
}

# TECHIS: só as colunas de Status até Tecnologia (A:K) e só estes status
TECHIS_COLUNAS = ("Status", "Tecnologia")
TECHIS_STATUS_VALIDOS = ("Em Viagem", "Finalizado")

# TECHIS: a coluna que liga o SM à viagem do JMS (Nº Embarque = Tarefa de transporte No.)
COL_TECHIS_EMBARQUE = "Nº Embarque"

# Regionais da planilha, na ordem dela (sempre aparecem, mesmo sem dados no período)
REGIOES = ["RJ", "SPS", "SPE", "MG", "PR", "SPN"]

# Regionais extras que entram nas tabelas, gráficos e no total, depois das da planilha (só aparecem se houver dados).
# Hoje só o SR. As demais que existem nos dados (GP, CE, BA...) ficam de fora, como na planilha.
# Para incluir outra, acrescente o nome na lista; para voltar às seis da planilha, deixe a lista vazia: [].
REGIOES_EXTRAS = ["SR"]

# Regras do Manual da planilha (passos 2 a 4)
STATUS_VALIDOS = ("Concluído", "Em Trânsito")   # "Em viagem" e "Finalizado" no JMS
TRANSPORTADOR_EXCLUIDO = "Franqueado"            # prefixo do valor, ex.: "Franqueado-加盟商"
PEDIDO_MAE_MINIMO = 2                            # vazio, 0 e 1 são excluídos

# SM previsto = nº de trechos da rota (cada hífen separa um trecho). Regra confirmada com o Renan (14/10):
# usar a coluna G "Nome da rota" e a D "Nome da viagem" e ficar com a que tiver MAIS trechos
# (G vazia, comum nas Horas Extras, vale a D; empate vale a G).
# False = só a D, como na planilha antiga (usado pelo validar_sm.py para reproduzir a planilha finalizada).
PREVISTO_PELA_ROTA = True

# SM realizado nunca passa do previsto.
# Na planilha, a fórmula da Coleta usa MIN(previsto; contagem) e a da Entrega não limita.
# True nos dois = regra da Coleta aplicada também à Entrega (pode ser desligado na tela).
LIMITAR_REALIZADO = True

# Meta de rastreamento efetivo (None = sem meta; com meta, abaixo dela fica em vermelho)
META = None
