import os
import requests
from requests.auth import HTTPBasicAuth
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# carrega as variáveis .env para a memória do sistema
load_dotenv()

# --- CONFIGURA O PLANNING CENTER ---
APP_ID = os.getenv("PC_APP_ID")
SECRET = os.getenv("PC_SECRET")
SERVICE_TYPE_ID = os.getenv("PC_SERVICE_TYPE_ID")
BASE_URL = "https://api.planningcenteronline.com/services/v2"

# --- CONFIGURA O SPOTIFY ---
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8080"
SPOTIFY_SCOPE = "playlist-modify-public playlist-modify-private"
SPOTIFY_PLAYLIST_ID = os.getenv("SPOTIFY_PLAYLIST_ID")


def get_next_sunday_songs():
    auth = HTTPBasicAuth(APP_ID, SECRET)
    
    # monta a URL (endpoint) para buscar as próximas celebrações de domingo da IBNJ (via service type ID)
    url = f"{BASE_URL}/service_types/{SERVICE_TYPE_ID}/plans?filter=future"
    
    # dispara uma requisição HTTP do tipo GET para a URL, enviando o crachá de autenticação
    response = requests.get(url, auth=auth)
    
    if response.status_code != 200:
        print(f"Erro no Planning Center: {response.status_code}")
        # retorna uma lista vazia e encerra a função, uma vez que deu erro
        return []
    
    
    # converte o JSON recebido e extrai a lista de cultos que fica dentro da chave 'data'
    plans_data = response.json().get('data', [])
    
    # verifica se a lista de cultos futuros veio vazia
    if not plans_data:
        print("Não foi encontrado nenhum culto programado.")
        # retorna uma lista vazia e encerra a função
        return []

    # como a API traz os cultos em ordem cronológica, o primeiro da lista ([0]) é o próximo domingo
    next_plan = plans_data[0]
    
    # extrai o ID único desse culto específico de domingo
    plan_id = next_plan['id']
    
    # monta a nova URL para acessar a lista de itens (cronograma) desse culto específico
    items_url = f"{BASE_URL}/service_types/{SERVICE_TYPE_ID}/plans/{plan_id}/items"
    
    # faz outra requisição GET para trazer todos os itens daquele domingo
    items_response = requests.get(items_url, auth=auth)
    
    # Cria uma lista vazia onde vamos guardar apenas os nomes das músicas encontradas
    songs_to_find = []
    
    if items_response.status_code == 200:
        # converte o JSON e pega a lista com todos os itens do cronograma (avisos, palavra, músicas)
        items = items_response.json().get('data', [])
        
        for item in items:
            # verifica se o tipo do item atual do loop é estritamente uma música ('song')
            if item['attributes']['item_type'] == 'song':
                # se for, adiciona o título dela no final da nossa lista 'songs_to_find'
                songs_to_find.append(item['attributes']['title'])
    
    # devolve a lista preenchida com os nomes das músicas para quem chamou a função
    return songs_to_find


def search_songs_on_spotify(song_titles):
    # inicializa o cliente do Spotify configurando o gerenciador de autenticação OAuth 2.0
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE
    ))
    
    # cria uma lista vazia onde vamos guardar os IDs únicos (URIs) das músicas encontradas
    spotify_track_uris = []
    
    print("\n🔍 BUSCANDO MÚSICAS NO SPOTIFY:")
    
    for title in song_titles:
        # cria uma string combinando o título com a palavra "gospel" para refinar o resultado
        query_refinada = f"{title} gospel"
        
        # faz a chamada de busca na API do Spotify usando a query refinada, limitando a apenas 1 resultado do tipo música ('track')
        result = sp.search(q=query_refinada, limit=1, type='track')
        
        # navega pelo dicionário de resposta do Spotify para extrair a lista de músicas encontradas
        tracks = result.get('tracks', {}).get('items', [])
        
        # verifica se a lista 'tracks' não veio vazia
        if tracks:
            # como limitamos a busca a 1, pegamos o primeiro e único resultado da lista ([0])
            track = tracks[0]
            
            print(f" ✅ Encontrada: {track['name']} - {track['artists'][0]['name']}")
            
            # extrai o link interno exclusivo da música (URI) e adiciona na nossa lista de resultados (criada lá em cima)
            spotify_track_uris.append(track['uri'])
            
        # Cse o Spotify não achou nenhuma música com os termos da busca
        else:
            print(f" ❌ Não encontrada no Spotify: {title}")
            
    # retorna duas coisas para quem chamou a função: o objeto cliente do Spotify autenticado ('sp') e a lista de URIs gerada
    return sp, spotify_track_uris


def update_spotify_playlist(sp, track_uris):
    # verifica se a lista de URIs veio vazia
    if not track_uris:
        print("Nenhuma URI válida para adicionar à playlist.")
        return
        
    print("\n🔄 Atualizando a playlist no Spotify...")
    
    try:
        # o método abaixo limpa a playlist antiga e adiciona todos os novos itens de uma só vez
        sp.playlist_replace_items(playlist_id=SPOTIFY_PLAYLIST_ID, items=track_uris)
        
        print("🎉 Playlist atualizada com sucesso no Spotify!")        
        
    except Exception as e:
        # captura o erro na variável 'e' e exibe a mensagem detalhada do problema no terminal
        print(f"Erro ao atualizar playlist: {e}")


# bloco padrão do Python que garante que o script só vai rodar se for executado diretamente
if __name__ == "__main__":

    # 1. Busca no Planning Center
    titles = get_next_sunday_songs()
    
    if titles:
        print(f"🎶 {len(titles)} músicas extraídas do Planning Center.")

        # 2. Busca os IDs no Spotify
        sp_client, track_uris = search_songs_on_spotify(titles)
        
        # 3. Atualiza a Playlist
        update_spotify_playlist(sp_client, track_uris)
    else:
        print("Nenhuma música encontrada no Planning Center para o próximo domingo.")