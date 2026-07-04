import os
import requests
from requests.auth import HTTPBasicAuth
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

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
SPOTIFY_PLAYLIST_ID = os.getenv("SPOTIFY_PLAYLIST_SUNDAY_ID")


def get_next_sunday_songs():
    auth = HTTPBasicAuth(APP_ID, SECRET)
    url = f"{BASE_URL}/service_types/{SERVICE_TYPE_ID}/plans?filter=future"
    response = requests.get(url, auth=auth)
    
    if response.status_code != 200:
        print(f"Erro no Planning Center: {response.status_code}")
        return []
    
    plans_data = response.json().get('data', [])
    if not plans_data:
        print("Não foi encontrado nenhum culto programado.")
        return []

    next_plan = plans_data[0]
    plan_id = next_plan['id']
    
    # ADIÇÃO: Agora pedimos para a API incluir 'song' e 'arrangement' na resposta
    items_url = f"{BASE_URL}/service_types/{SERVICE_TYPE_ID}/plans/{plan_id}/items?include=song,arrangement"
    items_response = requests.get(items_url, auth=auth)
    
    songs_to_find = []
    
    if items_response.status_code == 200:
        payload = items_response.json()
        items = payload.get('data', [])
        included_data = payload.get('included', [])
        
        # Criamos dicionários separados para Mapear Autores e Arranjos
        authors_map = {}
        arrangements_map = {}
        
        for inc in included_data:
            obj_type = inc.get('type', '').lower()
            obj_id = inc.get('id')
            
            if obj_type == 'song':
                author = inc.get('attributes', {}).get('author')
                if author:
                    authors_map[obj_id] = author
            elif obj_type == 'arrangement':
                # Arranjos guardam o seu texto no campo 'name'
                arr_name = inc.get('attributes', {}).get('name')
                if arr_name:
                    arrangements_map[obj_id] = arr_name

        for item in items:
            if item.get('attributes', {}).get('item_type') == 'song':
                title = item['attributes']['title']
                relationships = item.get('relationships', {})
                
                # Coleta os IDs de relacionamento garantindo proteção contra maiúsculas/minúsculas
                song_rel = relationships.get('song', {}).get('data') or relationships.get('Song', {}).get('data')
                arr_rel = relationships.get('arrangement', {}).get('data') or relationships.get('Arrangement', {}).get('data')
                
                author = None
                arr_name = None
                
                if song_rel:
                    author = authors_map.get(song_rel.get('id'))
                if arr_rel:
                    arr_name = arrangements_map.get(arr_rel.get('id'))
                
                # LÓGICA DE PRIORIDADE: Se o autor for vazio, mas existir um arranjo (ex: Dany Grace), usamos ele.
                artista_final = author
                if not artista_final and arr_name:
                    artista_final = arr_name
                
                songs_to_find.append({
                    'title': title,
                    'author': artista_final
                })
    
    return songs_to_find


def search_songs_on_spotify(songs_list):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE
    ))
    
    spotify_track_uris = []
    
    print("\n🔍 BUSCANDO MÚSICAS NO SPOTIFY:")
    
    for song in songs_list:
        title = song['title']
        author = song['author']
        
        # Se tivermos o autor do Planning Center, tentamos a busca estrita primeiro
        if author:
            # Limpamos o nome do autor (pega só o primeiro nome se houver vírgula ou barra) para evitar falhas
            primeiro_autor = author.split(',')[0].split('/')[0].strip()
            query = f'track:"{title}" artist:"{primeiro_autor}"'
            print(f" ⚙️  Buscando rigorosamente: {title} ({primeiro_autor})")
        else:
            # Se a música não tiver autor cadastrado lá, volta para a estratégia antiga
            query = f"{title} gospel"
            print(f" ⚙️  Buscando amplamente: {title} (sem autor cadastrado)")

        result = sp.search(q=query, limit=1, type='track')
        tracks = result.get('tracks', {}).get('items', [])
        
        # Estratégia de Fallback: Se a busca estrita falhou (por erro de digitação do autor no cadastro, por exemplo)
        if not tracks and author:
            print(f" ⚠️  Busca estrita falhou. Tentando busca ampla de segurança...")
            query = f"{title} gospel"
            result = sp.search(q=query, limit=1, type='track')
            tracks = result.get('tracks', {}).get('items', [])

        if tracks:
            track = tracks[0]
            print(f" ✅ Encontrada: {track['name']} - {track['artists'][0]['name']}")
            spotify_track_uris.append(track['uri'])
        else:
            print(f" ❌ Não encontrada no Spotify: {title}")
            
    return sp, spotify_track_uris


def update_spotify_playlist(sp, track_uris):
    if not track_uris:
        print("Nenhuma URI válida para adicionar à playlist.")
        return
        
    print("\n🔄 Atualizando a playlist no Spotify...")
    
    try:
        sp.playlist_replace_items(playlist_id=SPOTIFY_PLAYLIST_ID, items=track_uris)
        print("🎉 Playlist atualizada com sucesso no Spotify!")        
    except Exception as e:
        print(f"Erro ao atualizar playlist: {e}")


if __name__ == "__main__":

    # 1. Busca no Planning Center (agora retorna dicionários)
    songs_data = get_next_sunday_songs()
    
    if songs_data:
        print(f"🎶 {len(songs_data)} músicas extraídas do Planning Center.")

        # 2. Busca os IDs no Spotify usando a nova lógica inteligente
        sp_client, track_uris = search_songs_on_spotify(songs_data)
        
        # 3. Atualiza a Playlist
        update_spotify_playlist(sp_client, track_uris)

    else:
        print("Nenhuma música encontrada no Planning Center para o próximo domingo.")