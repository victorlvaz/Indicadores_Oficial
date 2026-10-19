# Indicadores (Streamlit)

App web com menu para navegar entre relatórios. Hoje: **Lacre / Deslacre – Linha Secundária**.

## Rodar no seu computador
```
pip install -r requirements.txt
python -m streamlit run app.py
```
(rode dentro da pasta do projeto; no Windows, se `python` não funcionar, use `py`)

## Histórico em banco de dados (Lacre / Deslacre)
Os relatórios agora são **enviados uma vez** e ficam gravados num banco; a tela lê sempre do histórico.
1. Na barra lateral, envie o relatório consolidado e clique em **Salvar no histórico**.
   - Reenviar o mesmo dia só **atualiza** as viagens (chave: ID + estação de chegada + horário planejado); não duplica e
     não apaga viagens que só estavam no envio anterior. Depois de salvar, o arquivo sai da lista.
   - A aba *Base / Diagnóstico* mostra o histórico de cargas (arquivo, quantas linhas novas e quantas atualizadas).
2. **Onde fica o banco:** por padrão, um arquivo SQLite local em `dados/historico.db` (não vai para o GitHub).
   Para usar o servidor da empresa, informe só a URL de conexão, sem mudar código:
   - arquivo `.streamlit/secrets.toml`:
     ```
     [banco]
     url = "postgresql+psycopg2://usuario:senha@servidor:5432/indicadores"
     ```
     ou a variável de ambiente `INDICADORES_DB_URL`. Exemplos para SQL Server e MySQL estão em `comum/banco.py`.
   - Instale o driver do banco (`psycopg2-binary`, `pyodbc` ou `pymysql`). As tabelas `lacre_viagens` e `lacre_cargas`
     são criadas sozinhas (o usuário precisa de permissão para criar tabelas).
   - Para levar o que já está no SQLite para o servidor, é só reenviar os relatórios (ou pedir a migração).
3. O que fica guardado é a base **já tratada** (depois das regras de exclusão). As regras agora são fixas, em
   `lacre_deslacre/config.py` — não há mais caixas de seleção na tela.
4. **Backup:** com SQLite, copie `dados/historico.db`. No servidor, o backup é da TI.
5. No Streamlit Community Cloud o disco é temporário: SQLite lá perderia o histórico. Use o servidor da empresa.

## Histórico do SM (SM状态统计)
Mesmo banco e mesmo fluxo do Lacre/Deslacre, nas tabelas `sm_viagens` e `sm_cargas`.
- Envie os relatórios JMS (Coleta e/ou Entrega) **e a extração do TECHIS** e clique em **Salvar no histórico**
  (sem o TECHIS o botão não salva, porque os SMs realizados ficariam em 0). Depois de salvar, os arquivos saem da lista.
- Chave da viagem: tipo + ID da tarefa. Reenviar atualiza a viagem; a contagem de SMs do TECHIS fica com o **maior**
  valor entre o já gravado e o do arquivo novo (um TECHIS mais recente pode não cobrir dias antigos).
- O SM realizado nunca passa do previsto (regra fixa); o previsto usa a coluna G, ou a D se a G estiver vazia, e vale a
  que tiver mais trechos. Não há mais caixas de regras na tela.
- Arquivos enviados e ainda não salvos já entram nas tabelas (aviso na tela).
- A aba **Resumo** tem filtro de regional, visão por dia/semana/mês e ano (padrão: ano corrente), com Coleta e Entrega.

## Taxa de Uso de APP (支线打卡率)
Mesmo relatório consolidado do Lacre/Deslacre, mesma lógica de histórico (botão "Salvar no histórico", tabelas
`app_viagens`, `app_cargas`, `app_transportadores`). Taxa = (check-outs + check-ins feitos) / (viagens x 2); Coleta agrupa
pela regional de saída, Entrega pela de chegada; meta 95%. Regras (passo a passo do Documents): só Concluído e Em Trânsito,
excluir rotas do mesmo SC (coletas e entregas), excluir Franqueados e, se o transportador vier vazio, usar o último valor
conhecido da viagem. Todas as regionais (inclusive GP, CE, BA e SR) entram no total, como na planilha do Lucas.
Validar: `python validar_app_uso.py "Taxa_uso_de_APP.xlsx" ["relatorio_bruto.xls"]`.

## Custos (物流成本指标)

Mede o custo do transporte da linha secundária: viagens, pacotes, KM, frete total, frete por KM e frete por pacote, por
regional, por regional × tipo de veículo e por regional × tipo de transportadora.

**Como carregar:** na barra lateral, selecione de uma vez os arquivos "Fretes Diarios" de todas as regionais (aba
`支线 用车成本模板- SECUNDARIA`) e clique em "Salvar no histórico". A regional é identificada pelo nome do arquivo (ex.:
`10_GP_…`); se o nome não tiver a sigla, o app pede para escolher. As colunas são lidas pelo nome do cabeçalho, porque o
layout muda entre regionais. Reenviar o arquivo de uma regional substitui os dias que ele cobre.

**Regras:**
- Frete total = frete da rota + ônus/bônus + aluguel + combustível + motorista + depreciação + manutenção + seguro + IPVA +
  pedágio + outras despesas (igual à coluna FRETE TOTAL da Base da planilha).
- Mesmo ID de viagem com os mesmos valores (frete, pacotes, KM e destino): conta uma vez. Com valores diferentes: as
  linhas ficam e os fretes são somados. Os dois casos aparecem na aba Auditoria.
- Tipo de transportadora vazio aparece como "Não informado" (a regional não preencheu).
- Tipo de veículo é padronizado como na aba Apoio da planilha (Cavalo/Baú → CARRETA, Fiorino → UTILITÁRIO, "03/abr" → 3/4 …).
- Pacotes ou KM zerados não são completados por nenhum relatório do JMS (ainda); aparecem na Auditoria como pendência.

**Auditoria:** pendências de preenchimento por regional (frete zerado, sem pacotes, sem KM, sem rota, sem tipo de
transportadora), lista de viagens a cobrar e IDs repetidos.

**Ainda não implementado:** conferência do frete lançado contra as tabelas de frete das regionais (aguardando as tabelas
atualizadas) e leitura direta do SharePoint da Controladoria.

Validar: `python validar_custos.py "planilha_pronta.xlsx" "arquivo_BA.xlsx" "arquivo_GP.xlsx"`.

## Taxa de Ocupação (装载率)
Mesmo relatório do SM ("Consulta de Viagens Secundárias"), mas **um único arquivo** com Coleta e Entrega, sem TECHIS.
Ocupação = pedidos mãe carregados / capacidade do tipo de veículo (tabela `CAPACIDADE` em `ocupacao/config.py`), somados
por regional de **origem** e limitados a 100% por regional, como na planilha. Regras: só Concluído e Em Trânsito, sem rotas
do mesmo SC, sem Franqueados; a Coleta ignora pedido mãe vazio/0/1 e a Entrega ignora 0/1 (vazio conta como 0), igual à
planilha do Lucas. Tipo de veículo sem capacidade (ex.: BARCO) aparece em aviso na aba Base. Tabelas `oc_viagens`, `oc_cargas`.
Validar: `python validar_ocupacao.py "relatorio_bruto.xls" "OCUPAÇÃO_SECUNDÁRIA.xlsx" 2026-10-14`.

## Período e comparação
- **Período de análise:** Dia, Semana (segunda a domingo), Mês ou Ano, mais a opção *Todos (acumulado)*.
- **Comparar com:** *Período anterior* (dia anterior, semana anterior, mês anterior, ano anterior) ou
  *Mesmo período do ano passado*. As tabelas ganham a taxa comparada e a variação em **pontos percentuais** (▲ subiu,
  ▼ caiu em vermelho). Com *Todos* não há comparação.
- As abas de **tendência** seguem o período escolhido (dias, semanas, meses ou anos).

## Estrutura
```
app.py                       entrada: monta o menu a partir de relatorios.py
relatorios.py                lista dos relatórios (grupo, título, arquivo da página, ícone, descrição)
.streamlit/config.toml       tema: vermelho #E60000 como única cor de destaque (modo claro e escuro)
paginas/
  inicio.py                  página inicial com atalhos
  lacre_deslacre_tela.py     tela do Lacre/Deslacre
  sm_tela.py                 tela do SM
  app_uso_tela.py            tela da Taxa de Uso de APP
  ocupacao_tela.py           tela da Taxa de Ocupação
  custos_tela.py             tela dos Custos
lacre_deslacre/              regras e cálculos do Lacre/Deslacre
  config.py  calculos.py  textos.py  apoio/*.csv
  historico.py  gravar/ler o histórico no banco     resumo_ui.py  aba Resumo
sm/                          regras e cálculos do SM (config, calculos, textos, historico, resumo_ui, apoio/*.csv)
app_uso/                     regras e cálculos da Taxa de Uso de APP (config, calculos, textos, historico, resumo_ui)
ocupacao/                    regras e cálculos da Taxa de Ocupação (idem)
custos/                      regras e cálculos dos Custos (idem)
comum/                       partes reaproveitadas por todos os relatórios
  banco.py      conexão com o banco (SQLite por padrão, URL da empresa por configuração)
  periodos.py   dia/semana/mês/ano e comparação      graficos.py  gráficos vermelho/cinza
  tema.py       cores (VERMELHO = "#E60000")
  idioma.py     bi(), frase() e cabecalho() para os textos em chinês + português
  estilos.py    cor de meta nas tabelas      exportar.py   Excel
  sparkline.py  tabela de tendência com mini-gráficos de linha e pontos
validar_lacre_deslacre.py    confere o cálculo contra a planilha finalizada
validar_sm.py, validar_app_uso.py, validar_ocupacao.py, validar_custos.py   idem para o SM, o APP, a Ocupação e os Custos
```

## Padrão visual e de idioma
- **Cor:** só vermelho `#E60000`. Taxa abaixo da meta = fundo vermelho com texto branco; meta atingida = sem cor.
  Nada de verde. Para trocar o tom: `comum/tema.py` e `.streamlit/config.toml`.
- **Idioma:** todo nome aparece em chinês + português.
  - Título da página: chinês ACIMA do português (`cabecalho("支线解封车率", "Lacre / Deslacre Linha Secundária")`).
  - Demais nomes (menu, abas, barra lateral, colunas, abas do Excel): LADO A LADO (`bi("支线", "Linha secundária")`).
  - Frases longas (avisos, ajudas): chinês na 1ª linha, português na 2ª (`frase(zh, pt)`).
- Os textos de cada relatório ficam num `textos.py` próprio. Em `lacre_deslacre/textos.py` cada termo está marcado
  `[planilha]` (já existia na planilha finalizada) ou `[revisar]` (escrito sem confirmação de falante nativo).

## Adicionar um relatório novo
1. Crie a pasta do relatório com suas regras (copie `lacre_deslacre/` como modelo): `config.py`, `calculos.py`, `textos.py`.
2. Crie a tela em `paginas/<nome>_tela.py`, começando com `cabecalho(zh, pt)` e usando os textos do `textos.py`.
3. Acrescente um item na lista `RELATORIOS` de `relatorios.py` (grupo e título com `bi()`, descrição com `frase()`).
   O menu e a página inicial se atualizam sozinhos.

## Publicar (GitHub + Streamlit Community Cloud)
- Repositório **privado**. Nunca suba relatórios reais: o `.gitignore` já bloqueia `.xls`, `.xlsx` e `.csv`
  (exceto as listas de apoio em `lacre_deslacre/apoio/`).
- Em share.streamlit.io: repositório, branch `main`, arquivo principal `app.py`.
- Atualizar o app = alterar os arquivos e enviar (commit + push) para o GitHub.
- Os relatórios são enviados pela própria tela do app; não ficam no repositório.

## Onde o histórico fica guardado (importante no link publicado)
O histórico é um arquivo SQLite (`dados/historico.db`) e **não vai para o GitHub** (o `.gitignore` bloqueia `dados/` e `*.db`).
- **No computador:** o arquivo fica na pasta `dados/` e permanece entre uma execução e outra.
- **No link do Streamlit Cloud:** o arquivo fica no disco do servidor, que é **temporário**. Todos que abrem o link veem o mesmo
  histórico, e quem salvar um relatório novo atualiza para todos. Mas o histórico **volta vazio** sempre que o app:
  - é reimplantado (qualquer commit ou upload novo no GitHub);
  - é reiniciado em "Manage app" > "Reboot app";
  - hiberna por falta de acesso (cerca de 12 horas) e acorda de novo; nesse caso pode ou não ser apagado, não conte com ele.
- **Por isso, guarde os relatórios exportados de cada dia (`.xls`).** Se o histórico sumir, basta enviar os arquivos de novo e clicar
  em "Salvar no histórico" (reenviar o mesmo dia atualiza, não duplica).
- **Solução definitiva:** colocar o histórico fora do servidor do app, num banco da empresa (veja "Histórico em banco de dados" acima:
  basta informar a URL em `.streamlit/secrets.toml`) ou em arquivos por dia numa pasta do SharePoint (precisa de um registro de
  aplicativo no Microsoft Entra, pedido à TI).
- Depois de cada commit, abra o link, confira se o relatório carrega e, se o histórico tiver sumido, reenvie os arquivos.

### Guardar o histórico no Neon (Postgres grátis, sem CNPJ)
1. Crie a conta em neon.com (plano Free: 1 GB por projeto; ao passar disso as gravações travam) e um projeto (região mais próxima, ex.: São Paulo).
2. Em "Connect" copie a *connection string* e monte a URL assim (troque `postgresql://` por `postgresql+psycopg2://` e
   remova `&channel_binding=require` se aparecer):
```
[banco]
url = "postgresql+psycopg2://USUARIO:SENHA@ep-xxxx.sa-east-1.aws.neon.tech/neondb?sslmode=require"
```
3. No Streamlit Cloud: Settings > Secrets > cole o bloco acima. Faça o commit de `comum/banco.py` e `requirements.txt`
   (já incluem `psycopg2-binary`) e use Reboot app. As tabelas são criadas sozinhas.
4. Para copiar o histórico do computador: `python migrar_historico.py "URL_DO_NEON"`.
- O Neon "dorme" após 5 min sem uso e acorda sozinho em alguns segundos; o primeiro acesso pode demorar um pouco.
- Dados da empresa em conta pessoal: confirme com a TI antes de usar o histórico real.

### Guardar o histórico no Azure SQL (oferta gratuita)
1. No portal do Azure, crie um **Azure SQL Database** com a oferta gratuita ("Apply free offer": 32 GB e 100 mil vCore-segundos por mês).
2. Crie o servidor com login e senha de administrador SQL e anote o nome (`SERVIDOR.database.windows.net`).
3. Em Rede (Networking), ative "Permitir que serviços do Azure acessem o servidor". O Streamlit Cloud não tem IP fixo; a proteção
   fica por conta do login e da senha (use uma senha forte e confirme com a TI se a regra é aceita na empresa).
4. No Streamlit Cloud, em Settings > Secrets, cole:
```
[banco]
url = "mssql+pymssql://USUARIO:SENHA@SERVIDOR.database.windows.net/NOMEDOBANCO"
```
   (se a senha tiver `@`, `:` ou `/`, troque por `%40`, `%3A` e `%2F`).
5. Faça o commit de `comum/banco.py` e `requirements.txt` (já inclui `pymssql`) e use Reboot app. As tabelas são criadas sozinhas.
6. Para copiar o histórico que já existe no computador: `python migrar_historico.py "URL_DO_AZURE"`.
- O banco gratuito **pausa sozinho** sem uso: o primeiro acesso depois da pausa pode levar cerca de 1 minuto (o app espera até 90 s).
- Se a franquia mensal acabar, o banco fica pausado até o mês seguinte (sem cobrança, pois o excedente fica desligado).

## Validar o Lacre/Deslacre
```
python validar_lacre_deslacre.py "planilha_finalizada.xlsx"
```
Deve terminar com "39 linhas comparadas, 0 divergências".
