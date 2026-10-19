"""Configuração do relatório de Custos (物流成本指标) da linha secundária.

Fonte: planilhas "Fretes Diarios" de cada regional (pasta da Controladoria), aba "支线 用车成本模板- SECUNDARIA".
Cada regional manda um arquivo com o mês inteiro; o app lê vários arquivos de uma vez, identifica a regional
pelo nome do arquivo e junta tudo no histórico. As colunas são lidas pelo NOME do cabeçalho (o layout muda entre regionais).
"""
import re

# Regionais, na ordem dos outros relatórios. Qualquer regional nova que apareça nos dados entra no fim.
REGIOES = ["SPE", "SPS", "SPN", "RJ", "MG", "PR", "CE", "BA", "GP", "SR"]

# chave interna -> início do texto do cabeçalho (maiúsculo, sem acento extra). O 1º cabeçalho que começar com o texto é usado.
CABECALHOS = {
    "uf": ["UF"],
    "dia": ["DATA"],
    "id": ["ID VIAGEM"],
    "sc_origem": ["SC ORIGEM"],
    "hub_destino": ["HUB DESTINO"],
    "frota": ["FROTA PROPRIA", "FROTA PRÓPRIA"],
    "transportadora": ["TRANSPORTADORA/PARCEIRO"],
    "placa": ["PLACA"],
    "veiculo": ["MODELO VEICULO", "MODELO VEÍCULO"],
    "frete_rota": ["FRETE ROTA"],
    "pacotes": ["PACOTES"],
    "km": ["KM"],
    "rota": ["ROTA COMPLETA", "PERCURSO COMPLETO"],
    "tipo_transp": ["TIPO DE TRANSPORTADORA"],
}
# colunas de custo somadas ao frete da rota (a planilha faz SUM(frete rota, ÔNUS/BÔNUS … OUTRAS DESPESAS); o "total custo frota própria"
# fica de fora porque já é a soma delas)
CABECALHOS_EXTRAS = ["ONUS BONUS", "CUSTO ALUGUEL", "VALOR COMBUSTIVEL", "VALOR MOTORISTA", "DEPRECIA", "MANUTEN",
                     "SEGURO", "IPVA", "PEDAGIO", "OUTRAS DESPESAS"]
OBRIGATORIAS = ["dia", "id", "frete_rota", "pacotes", "km", "veiculo"]

ABA_DADOS = ("SECUNDARIA", "支线")         # a aba de dados tem as duas palavras no nome

# Tipo de veículo: "como veio" (maiúsculo, sem espaços nas pontas) -> nome padrão (aba Apoio da planilha, colunas K:L)
VEICULOS = {
    "3/4": "3/4", "03/ABR": "3/4", "BARCO": "BARCO", "CARRETA": "CARRETA", "CAVALO": "CARRETA", "BAÚ": "CARRETA", "BAU": "CARRETA",
    "FURGAO": "FURGÃO", "FURGÃO": "FURGÃO", "HR": "HR", "PASSEIO": "PASSEIO", "TOCO": "TOCO", "TOCO P": "TOCO",
    "TRUCK": "TRUCK", "UTILITÁRIO": "UTILITÁRIO", "UTILITARIO": "UTILITÁRIO", "FIORINO": "UTILITÁRIO", "VUC": "VUC",
    "MOTO": "MOTO", "VAN": "VAN",
}
ORDEM_VEICULOS = ["MOTO", "PASSEIO", "UTILITÁRIO", "VAN", "FURGÃO", "HR", "VUC", "3/4", "TOCO", "TRUCK", "CARRETA", "BARCO"]

# Tipo de transportadora (coluna AP da Base): início do texto -> nome padrão. Vazio = "Não informado" (a regional não preencheu).
TIPOS_TRANSP = {"TRANSPORTADORA": "Transportadora-三方", "FROTA": "Frota-自营", "FRANQUEADO": "Franqueado-加盟商"}
NAO_INFORMADO = "Não informado-未填写"
ORDEM_TIPOS = list(TIPOS_TRANSP.values()) + [NAO_INFORMADO]


def regional_do_nome(nome: str) -> str | None:
    """Acha a sigla da regional no nome do arquivo (ex.: '10_GP_末端…Fretes_Diarios.xlsx' -> GP).
    Sem sigla, ou com mais de uma diferente, devolve None (a tela pede para o usuário escolher)."""
    maius = nome.upper()
    achadas = {r for r in REGIOES if re.search(rf"(?<![A-Z0-9]){r}(?![A-Z0-9])", maius)}
    return achadas.pop() if len(achadas) == 1 else None
