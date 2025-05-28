import pyfolio as pf
import empyrical as ep
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
from pandas.tseries.offsets import BDay

import sgs  # Importa o módulo sgs para acessar séries temporais do Banco Central
CDI_CODE = 12  # Código do CDI na SGS (Sistema Gerenciador de Séries Temporais do Banco Central do Brasil)

import warnings
#ignorar warnings de tipo de dados
warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)

"""
Função para buscar o cadastro de fundos de investimento da CVM
@return: DataFrame com os dados do cadastro de fundos de investimento
""" 
def busca_cadastro_cvm():
   
  try:     
    #url = 'https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv'
    url = 'cad_fi.csv'
    print("Buscando arquivo: {}".format(url))
    dados = pd.read_csv(url, sep=';', encoding='ISO-8859-1')
    return dados

  except: 
    print("Arquivo {} não encontrado!".format(url))
    print("Forneça outra data!")


"""
Função para buscar os informes diários de fundos de investimento da CVM por período
@param data_inicio: Data de início do período (formato 'YYYY-MM-DD')
@param data_fim: Data de fim do período (formato 'YYYY-MM-DD')
@return: DataFrame com os informes diários de fundos de investimento
"""
#´Cálculo do Valor da cota diaria dos fundos de investimento
def busca_informes_diarios_cvm_por_periodo(data_inicio, data_fim):
  datas = pd.date_range(data_inicio, data_fim, freq='MS') 
  informe_completo = pd.DataFrame()

  for data in datas:
    try:
      #url ='http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{}{:02d}.zip'.format(data.year, data.month)
      url = 'inf_diario_fi_202501.zip'
      print("Obtendo Arquivo... {}".format(url))
      informe_mensal = pd.read_csv(url, compression='zip', sep=';')    
    
    except: 
      print("Arquivo {} não encontrado!".format(url))    

    informe_completo = pd.concat([informe_completo, informe_mensal], ignore_index=True)

  return informe_completo


def melhores_fundos(informes, cadastro, top=5, minimo_de_cotistas=100, classe='', CDI_periodo=0):
  """
  Função para calcular os melhores fundos de investimento com base nos retornos acumulados

  Parameters
  ----------
  @param informes: DataFrame com os informes diários de fundos de investimento
  @param cadastro: DataFrame com o cadastro de fundos de investimento
  @param top: Número de melhores fundos a serem retornados
  @param minimo_de_cotistas: Número mínimo de cotistas para considerar o fundo
  @param classe: Classe do fundo (opcional, pode ser 'multimercado', 'acoes', 'rendafixa' ou 'cambial')
  @param CDI_periodo: Taxa CDI acumulada no período (opcional, padrão é 0) usada para calcular o Sharpe Ratio

  Returns
  ----------

  @return: DataFrame com os melhores fundos de investimento
  """
#Filtragem de fundos por cotista mínimo e em funcionamento normal e remove os duplicados (classes de cotistas diferentes)
  cadastro      = cadastro[cadastro['SIT'] == 'EM FUNCIONAMENTO NORMAL']
  fundos        = informes[informes['NR_COTST'] >= minimo_de_cotistas]
  cnpj_informes = fundos['CNPJ_FUNDO_CLASSE'].drop_duplicates()
  
  fundos = fundos.drop_duplicates(subset=['DT_COMPTC', 'CNPJ_FUNDO_CLASSE'])
  
  fundos = fundos.pivot(index='DT_COMPTC', columns='CNPJ_FUNDO_CLASSE')
  # Todas as cotas dividindo pela primeira para achar percentual de retorno
  cotas_normalizadas = fundos['VL_QUOTA'] / fundos['VL_QUOTA'].iloc[0]
  retornos_diarios = cotas_normalizadas.pct_change().dropna(axis=0, how='all')
  # Escolhe a classe escolhida no Main
  if classe == 'multimercado':
    cnpj_cadastro      = cadastro[cadastro['CLASSE'] == 'Multimercado']['CNPJ_FUNDO']   
    cotas_normalizadas = cotas_normalizadas[cnpj_cadastro[cnpj_cadastro.isin(cnpj_informes)]]

  if classe == 'acoes':
    cnpj_cadastro      = cadastro[cadastro['CLASSE'] == 'Ações']['CNPJ_FUNDO']   
    cotas_normalizadas = cotas_normalizadas[cnpj_cadastro[cnpj_cadastro.isin(cnpj_informes)]]

  if classe == 'rendafixa':
    cnpj_cadastro      = cadastro[cadastro['CLASSE'] == 'Renda Fixa']['CNPJ_FUNDO']   
    cotas_normalizadas = cotas_normalizadas[cnpj_cadastro[cnpj_cadastro.isin(cnpj_informes)]]

  if classe == 'cambial':
    cnpj_cadastro      = cadastro[cadastro['CLASSE'] == 'Cambial']['CNPJ_FUNDO']   
    cotas_normalizadas = cotas_normalizadas[cnpj_cadastro[cnpj_cadastro.isin(cnpj_informes)]]
  
  cotas_normalizadas = cotas_normalizadas.dropna(axis=0, how='all')
  #Cria tabela melhores vazia na memória do computador e calcula o retorno
  #melhores
  melhores = pd.DataFrame()
  #ordenando do maior para o menor retorno 
  melhores['retorno(%)'] = (cotas_normalizadas.iloc[-1].sort_values(ascending=False)[:top] - 1) * 100
  #Completar com outras informações: cNPJ, nome do fundo, classe, PL e drawdown
  for cnpj in melhores.index:
    fundo = cadastro[cadastro['CNPJ_FUNDO'] == cnpj]
    melhores.at[cnpj, 'Fundo de Investimento'] = fundo['DENOM_SOCIAL'].values[0]
    melhores.at[cnpj, 'Classe']                = fundo['CLASSE'].values[0]
    melhores.at[cnpj, 'PL']                    = fundo['VL_PATRIM_LIQ'].values[0]
    melhores.at[cnpj, 'Drawdown(%)']           = pf.timeseries.gen_drawdown_table(retornos_diarios[cnpj], top=4)
    
    pf.plot_drawdown_underwater(retornos_diarios[cnpj], title="Drawdown:" + cnpj + " " +
                                fundo['DENOM_SOCIAL'].values[0][:40] + "...")
    #Mostrar o gráfico de drawdown de cada fundo
    plt.show()
    #converte CDI do período de um mês para diário e usa para calcular o Sharpe Ratio
    num_dias = len(retornos_diarios[cnpj])
    CDI_diario_periodo = (1 + CDI_periodo) ** (1/num_dias) - 1
    melhores.at[cnpj, 'Sharpe(CDI)'] = ep.sharpe_ratio(retornos_diarios[cnpj], risk_free=CDI_diario_periodo)  
  #retorna os melhores fundos para o main
  return melhores

############################################## ## MAIN ## ################################################
periodo_inicio = date(2025, 1, 1)
periodo_fim    = date(2025, 1, 31)
# Quantos fundos trazer
NUM_FUNDOS = 5
cadastro_fundos = busca_cadastro_cvm()
# Busca valor da cota dos fundos no período
diario_cvm  = busca_informes_diarios_cvm_por_periodo(periodo_inicio.strftime("%Y-%m-%d"), periodo_fim.strftime("%Y-%m-%d"))
#busca dados do CDI
print("Obtendo dados do CDI")
CDI_diario = sgs.time_serie(CDI_CODE, start=periodo_inicio.strftime("%d/%m/%Y"), end=periodo_fim.strftime("%d/%m/%Y"))
# transforma os dados do CDI em percentual
CDI_diario = (CDI_diario/100)+1
#calcula o CDI acumulado no período
CDI_acumulado = CDI_diario.cumprod().iloc[-1]-1
#Função principal
melhores = melhores_fundos(diario_cvm, cadastro_fundos, top=NUM_FUNDOS, minimo_de_cotistas=100, classe='acoes', CDI_periodo=CDI_acumulado)

print("Melhores fundos de investimento")
#imprimir cada linha de melhores
print(f"Fundo de Investimento;Classe;Retorno;PL;Sharpe")
for index, row in melhores.iterrows():    
    print(f"{row['Fundo de Investimento']};{row['Classe']};{row['retorno(%)']:.2f}%;{row['PL']:.2f};{row['Sharpe(CDI)']:.2f}")    
    if (isinstance(row['Drawdown(%)'], pd.DataFrame)):
        print(row['Drawdown(%)'].to_csv(sep=';', index=True, encoding='ISO-8859-1'))
    else:        
        print("Nenhum drawdown no período: ", row['Drawdown(%)'])