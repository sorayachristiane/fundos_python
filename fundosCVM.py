import pandas as pd
from datetime import date
from pandas.tseries.offsets import BDay

# Função para buscar o cadastro de fundos de investimento da CVM
# A função busca o arquivo CSV correspondente ao mês da data fornecida
# Se a data não for fornecida, a função busca o arquivo do dia anterior
# A função retorna um DataFrame com os dados do cadastro de fundos

def busca_cadastro_cvm(data=(date.today()-BDay(2))):
  if data is not busca_cadastro_cvm.__defaults__[0]:
    data = pd.to_datetime(data)
  
  try:     
    #url = 'https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv'
    url = 'cad_fi.csv'
    print("Buscando arquivo: {}".format(url))
    dados = pd.read_csv(url, sep=';', encoding='ISO-8859-1')
    dados.info()
    return dados

  except: 
    print("Arquivo {} não encontrado!".format(url))
    print("Forneça outra data!")


def busca_informes_diarios_cvm_por_periodo(data_inicio, data_fim):
  datas = pd.date_range(data_inicio, data_fim, freq='MS') 
  informe_completo = pd.DataFrame()

  for data in datas:
    try:
      url ='http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{}{:02d}.zip'.format(data.year, data.month)
      #url = 'inf_diario_fi_202505.zip'
      informe_mensal = pd.read_csv(url, compression='zip', sep=';')    
    
    except: 
      print("Arquivo {} não encontrado!".format(url))    

    informe_completo = pd.concat([informe_completo, informe_mensal], ignore_index=True)

  return informe_completo


def melhores_e_piores(informes, cadastro, top=5, minimo_de_cotistas=100, classe=''):  
  cadastro      = cadastro[cadastro['SIT'] == 'EM FUNCIONAMENTO NORMAL']
  fundos        = informes[informes['NR_COTST'] >= minimo_de_cotistas]
  cnpj_informes = fundos['CNPJ_FUNDO_CLASSE'].drop_duplicates()
  
  fundos = fundos.drop_duplicates(subset=['DT_COMPTC', 'CNPJ_FUNDO_CLASSE'])
  
  fundos = fundos.pivot(index='DT_COMPTC', columns='CNPJ_FUNDO_CLASSE')
  
  cotas_normalizadas = fundos['VL_QUOTA'] / fundos['VL_QUOTA'].iloc[0]
  
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
  
  #melhores
  melhores = pd.DataFrame()
  melhores['retorno(%)'] = (cotas_normalizadas.iloc[-1].sort_values(ascending=False)[:top] - 1) * 100
  print(melhores)
  for cnpj in melhores.index:
    fundo = cadastro[cadastro['CNPJ_FUNDO'] == cnpj]
    melhores.at[cnpj, 'Fundo de Investimento'] = fundo['DENOM_SOCIAL'].values[0]
    melhores.at[cnpj, 'Classe']                = fundo['CLASSE'].values[0]
    melhores.at[cnpj, 'PL']                    = fundo['VL_PATRIM_LIQ'].values[0]

  return melhores

cadastro_fundos = busca_cadastro_cvm()
#cadastro_fundos.info()

diario_cvm  = busca_informes_diarios_cvm_por_periodo('2025-01-01', '2025-05-31')
#diario_cvm.info()

melhores = melhores_e_piores(diario_cvm, cadastro_fundos, top=5, minimo_de_cotistas=100, classe='acoes')
print("Melhores fundos de investimento")
print(melhores)