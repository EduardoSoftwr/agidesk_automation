import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

# --- 1. Carregamento das Variáveis de Ambiente ---
# Carrega as variáveis do arquivo .env (se existir) para o ambiente
# O caminho é ajustado para encontrar o .env na raiz do projeto, um nível acima de src/
load_dotenv(dotenv_path="../.env")

# Obtém as chaves de API e IDs do ambiente. 
# Para testes locais, você pode preencher um arquivo .env com valores fictícios para AGIDESK_APP_KEY, AGIDESK_TENANT_ID e AGIDESK_SERVICE_ID.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGIDESK_APP_KEY = os.getenv("AGIDESK_APP_KEY")
AGIDESK_TENANT_ID = os.getenv("AGIDESK_TENANT_ID")
AGIDESK_SERVICE_ID = os.getenv("AGIDESK_SERVICE_ID")

# Inicializa o cliente OpenAI com sua chave de API
client = OpenAI(api_key=OPENAI_API_KEY)

# --- 2. Funções de Mock para o AgiDesk (Simulação Local) ---
# Este arquivo JSON simulará a base de dados do AgiDesk para contatos e chamados.
# O caminho é ajustado para encontrar o arquivo na raiz do projeto, um nível acima de src/
MOCK_DATA_FILE = "../agidesk_mock_data.json"

def load_mock_data():
    """Carrega os dados de mock do arquivo JSON."""
    if os.path.exists(MOCK_DATA_FILE):
        with open(MOCK_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"contacts": [], "tickets": []}

def save_mock_data(data):
    """Salva os dados de mock no arquivo JSON."""
    with open(MOCK_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_agidesk_contact_info_mock(solicitante_name):
    """Simula a busca de contact_id e customer_id pelo nome do solicitante em dados locais."""
    mock_data = load_mock_data()
    normalized_name = solicitante_name.lower().strip()
    for contact in mock_data["contacts"]:
        if contact["name"].lower() == normalized_name:
            print(f"[MOCK] Solicitante \'{solicitante_name}\' encontrado localmente.")
            return {"contact_id": contact["contact_id"], "customer_id": contact["customer_id"]}
    print(f"[MOCK] Solicitante \'{solicitante_name}\' NÃO encontrado localmente.")
    return None

def create_agidesk_ticket_mock(customer_id, contact_id, service_id, title, description=None):
    """Simula a criação de um chamado no AgiDesk, salvando-o em um arquivo JSON local."""
    mock_data = load_mock_data()
    new_ticket = {
        "id": len(mock_data["tickets"]) + 1, # ID simples para o mock
        "customer_id": customer_id,
        "contact_id": contact_id,
        "service_id": service_id,
        "title": title,
        "description": description,
        "created_at": "2026-06-17 10:00:00" # Data fictícia
    }
    mock_data["tickets"].append(new_ticket)
    save_mock_data(mock_data)
    print(f"[MOCK] Chamado simulado criado localmente: {new_ticket["title"]} (ID: {new_ticket["id"]})")
    return {"status": "success", "ticket_id": new_ticket["id"]}

# --- 3. Funções de Integração com OpenAI ---

def transcribe_audio(audio_file_path):
    """Transcreve um arquivo de áudio para texto usando a API Whisper da OpenAI."""
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Erro na transcrição de áudio com OpenAI Whisper: {e}")
        return None

def extract_info_with_chatgpt(text):
    """Extrai o nome do solicitante e a ação do texto usando a API ChatGPT da OpenAI."""
    prompt = f"""
    O seguinte texto é uma solicitação de um usuário: \'{text}\'. 
    Por favor, identifique o nome do solicitante e a ação solicitada. 
    Retorne as informações em formato JSON com as chaves \'solicitante\' e \'acao\'. 
    Se o solicitante não for explicitamente mencionado, retorne \'Desconhecido\'.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Você pode usar "gpt-4" se tiver acesso
            messages=[
                {"role": "system", "content": "Você é um assistente que extrai informações de texto."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" } # Garante que a resposta seja um JSON
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Erro na extração de informações com ChatGPT: {e}")
        return None

# --- 4. Função Principal de Automação ---

def automate_agidesk_ticket_from_audio(audio_file_path):
    """Orquestra o fluxo completo de automação: transcrição, extração e criação de chamado (mock)."""
    print(f"\n--- Iniciando automação para o arquivo de áudio: {audio_file_path} ---")
    
    # 1. Transcrever áudio
    transcribed_text = transcribe_audio(audio_file_path)
    if not transcribed_text:
        print("Falha na transcrição de áudio. Encerrando automação.")
        return
    print(f"Texto transcrito: {transcribed_text}")
    
    # 2. Extrair informações com ChatGPT
    extracted_info = extract_info_with_chatgpt(transcribed_text)
    if not extracted_info or extracted_info.get(\'solicitante\') == \'Desconhecido\':
        print("Não foi possível extrair solicitante ou ação do texto. Encerrando automação.")
        return
    
    solicitante = extracted_info.get(\'solicitante\')
    acao = extracted_info.get(\'acao\')
    print(f"Informações extraídas: Solicitante=\'{solicitante}\', Ação=\'{acao}\'")
    
    # 3. Buscar IDs de contato/cliente no AgiDesk (usando mock local)
    contact_info = get_agidesk_contact_info_mock(solicitante)
    if not contact_info:
        print(f"Não foi possível encontrar informações de contato para \'{solicitante}\' no mock local. Encerrando automação.")
        return
        
    customer_id = contact_info[\'customer_id\']
    contact_id = contact_info[\'contact_id\']
    print(f"IDs AgiDesk (mock) encontrados: Customer ID={customer_id}, Contact ID={contact_id}")
    
    # 4. Criar chamado no AgiDesk (usando mock local)
    # O \'title\' do chamado será a \'acao\' identificada pelo ChatGPT
    # A \'description\' pode ser o texto transcrito completo, se desejar mais detalhes
    ticket_response = create_agidesk_ticket_mock(
        customer_id=customer_id,
        contact_id=contact_id,
        service_id=AGIDESK_SERVICE_ID, # Usará o valor do .env, mesmo que fictício para o mock
        title=acao,
        description=transcribed_text # Opcional: usar o texto completo como descrição
    )
    
    if ticket_response:
        print("Automação (mock) concluída com sucesso!")
    else:
        print("Automação (mock) falhou na criação do chamado.")

# --- 5. Execução Principal ---

if __name__ == "__main__":
    # Caminho para o arquivo de áudio de teste
    # O caminho é ajustado para encontrar o arquivo na raiz do projeto, um nível acima de src/
    test_audio_file = "../audio_samples/audio_teste.mp3" 
    
    # Verifica se o arquivo de áudio existe
    if not os.path.exists(test_audio_file):
        print(f"ERRO: Arquivo de áudio \'{test_audio_file}\' não encontrado. Por favor, crie-o na pasta \'audio_samples/\'.")
    else:
        automate_agidesk_ticket_from_audio(test_audio_file)

    print("\n--- Conteúdo atual de agidesk_mock_data.json ---")
    # O caminho é ajustado para encontrar o arquivo na raiz do projeto, um nível acima de src/
    mock_data_for_display = load_mock_data()
    print(json.dumps(mock_data_for_display, indent=2, ensure_ascii=False))