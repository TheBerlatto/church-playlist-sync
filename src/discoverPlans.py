import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# carrega as variáveis .env para a memória do sistema
load_dotenv()

# --- CONFIGURA AS CREDENCIAIS ---
APP_ID = os.getenv("PC_APP_ID")
SECRET = os.getenv("PC_SECRET")

BASE_URL = "https://api.planningcenteronline.com/services/v2"

def descobrir_ids():
    # cria o objeto de autenticação usando o protocolo Basic Auth (Passando ID e Senha)
    auth = HTTPBasicAuth(APP_ID, SECRET)
    
    # monta a URL (endpoint) para acessar a lista de Plans da IBNJ
    url = f"{BASE_URL}/service_types"
    
    # dispara uma requisição HTTP do tipo GET para a URL, enviando o crachá de autenticação
    response = requests.get(url, auth=auth)
    
    if response.status_code == 200:
        # transforma o texto bruto retornado (JSON) em um dicionário Python e pega a lista dentro de 'data'
        services = response.json().get('data', [])
        
        print("\n🔍  OS SERVIÇOS ENCONTRADOS NA IBNJ FORAM:\n")
        
        for service in services:
            # extrai o nome do serviço navegando pela estrutura de chaves do JSON
            nome = service['attributes']['name']
            
            # extrai o ID do serviço
            id_servico = service['id']
            
            print(f"📚 {nome} | ID: {id_servico}")
            print("-" * 40)
            
    else:
        print(f"Erro ao buscar serviços. Status: {response.status_code}\n")        
        print(response.text)

# bloco padrão do Python que garante que o script só vai rodar se for executado diretamente
if __name__ == "__main__":
    descobrir_ids()
