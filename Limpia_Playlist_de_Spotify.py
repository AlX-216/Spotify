import os
import re
import unicodedata
from collections import defaultdict

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# CONFIGURACIÓN
# ============================================================

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

REDIRECT_URI = "http://127.0.0.1:9090/callback"

# Para obtener el ID de tu playlist:
# 1. Abre Spotify (App o Web) y entra a la playlist.
# 2. Haz clic en los tres puntos (...) -> Compartir -> "Copiar enlace a la playlist".
# 3. El enlace se verá así: https://open.spotify.com/playlist/16RuPUHtO3UX5w6aESJE9K?si=996de644a5de4ae3
# 4. Copia únicamente los caracteres entre '/playlist/' y el signo '?', en este caso: 16RuPUHtO3UX5w6aESJE9K
PLAYLIST_ID = "tu_playlist_id_aqui"

# True  = solo detectar y mostrar, NO borra nada
# False = detectar Y borrar
DRY_RUN = False

SCOPE = "playlist-read-private playlist-modify-public playlist-modify-private"


# ============================================================
# AUTENTICACIÓN
# ============================================================

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError(
        "Faltan SPOTIFY_CLIENT_ID y/o SPOTIFY_CLIENT_SECRET "
        "en las variables de entorno."
    )

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
    )
)


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalize_text(text):
    """Normaliza texto para que diferencias pequeñas no impidan
    detectar duplicados (mayúsculas, espacios, caracteres invisibles)."""

    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    text = text.casefold()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# OBTENER TODAS LAS CANCIONES
# ============================================================

def get_all_tracks(playlist_id):

    print("Obteniendo todas las canciones de Spotify...\n")

    tracks = []
    offset = 0
    limit = 50

    while True:

        response = sp.playlist_items(
            playlist_id,
            offset=offset,
            limit=limit,
            additional_types=["track"],
        )

        items = response.get("items", [])

        if not items:
            break

        tracks.extend(items)

        print(f"Obtenidas: {len(tracks)} / {response.get('total', '?')}")

        if not response.get("next"):
            break

        offset += limit

    print(f"\nTotal de elementos obtenidos: {len(tracks)}")

    return tracks


# ============================================================
# ANALIZAR DUPLICADOS
# ============================================================

def find_duplicates(tracks):

    print("\nAnalizando duplicados...\n")

    # clave = (nombre_normalizado, (artistas_normalizados_ordenados))
    groups = defaultdict(list)

    for position, playlist_item in enumerate(tracks):

        obj = playlist_item.get("item") or playlist_item.get("track")

        if not obj:
            continue

        # Solo canciones (no podcasts)
        if obj.get("type") != "track":
            continue

        # Las canciones locales no se pueden borrar de forma confiable
        if obj.get("is_local") or playlist_item.get("is_local"):
            continue

        name = (obj.get("name") or "").strip()
        artists = obj.get("artists") or []
        uri = obj.get("uri")

        artist_names = [
            (a.get("name") or "").strip()
            for a in artists
            if a.get("name")
        ]

        if not name or not artist_names or not uri:
            continue

        # TODOS los artistas, ordenados para que el orden no importe
        normalized_artists = tuple(
            sorted(normalize_text(a) for a in artist_names)
        )

        key = (normalize_text(name), normalized_artists)

        groups[key].append({
            "position": position,
            "name": name,
            "artist": ", ".join(artist_names),
            "uri": uri,
        })

    duplicates = []

    for songs in groups.values():

        if len(songs) <= 1:
            continue

        # La primera se conserva, las demás se borran
        original = songs[0]

        for duplicate in songs[1:]:
            duplicate["original_position"] = original["position"]
            duplicates.append(duplicate)

    # Ordenadas por posición para mostrarlas de forma natural
    duplicates.sort(key=lambda d: d["position"])

    return duplicates


# ============================================================
# MOSTRAR DUPLICADOS
# ============================================================

def print_duplicates(duplicates):

    print("=" * 70)
    print("DUPLICADOS ENCONTRADOS")
    print("=" * 70)

    if not duplicates:
        print("\nNo se encontraron duplicados.")
        return

    for i, d in enumerate(duplicates, start=1):
        print(
            f"{i}. {d['name']} - {d['artist']} "
            f"(posición {d['position'] + 1}, "
            f"se conserva la de la posición {d['original_position'] + 1})"
        )

    print()
    print(f"Total de canciones que se pueden eliminar: {len(duplicates)}")
    print("=" * 70)


# ============================================================
# ELIMINAR DUPLICADOS
# ============================================================

def remove_duplicates(playlist_id, duplicates, snapshot_id):
    """
    Borra las canciones duplicadas por posición exacta.

    IMPORTANTE: todas las posiciones corresponden al snapshot original,
    así que se usa SIEMPRE ese mismo snapshot en cada lote (Spotify
    aplica los cambios sobre esas posiciones aunque la playlist ya
    haya cambiado).
    """

    if not duplicates:
        print("\nNo hay nada que eliminar.")
        return

    print(f"\nSnapshot original: {snapshot_id}")

    # Agrupar posiciones por URI y recordar qué canción es cada una
    positions_by_uri = defaultdict(list)
    info_by_position = {}

    for d in duplicates:
        positions_by_uri[d["uri"]].append(d["position"])
        info_by_position[(d["uri"], d["position"])] = d

    removal_items = [
        {"uri": uri, "positions": positions}
        for uri, positions in positions_by_uri.items()
    ]

    print(f"\nSe eliminarán {len(duplicates)} canciones duplicadas.")

    print("\n" + "=" * 70)
    print("HISTORIAL DE CANCIONES ELIMINADAS")
    print("=" * 70)

    removed_count = 0

    # Spotify permite máximo 100 objetos por petición
    for start in range(0, len(removal_items), 100):

        batch = removal_items[start:start + 100]

        sp.playlist_remove_specific_occurrences_of_items(
            playlist_id,
            batch,
            snapshot_id=snapshot_id,
        )

        # Imprimir historial de este lote (ya se borró correctamente)
        batch_songs = []
        for item in batch:
            for pos in item["positions"]:
                batch_songs.append(info_by_position[(item["uri"], pos)])

        batch_songs.sort(key=lambda d: d["position"])

        for d in batch_songs:
            removed_count += 1
            print(f"  ✗ {removed_count}. {d['name']} - {d['artist']}")

    print("=" * 70)


# ============================================================
# GUARDAR HISTORIAL EN ARCHIVO
# ============================================================

def save_history(duplicates):

    filename = "historial_eliminadas.txt"

    with open(filename, "w", encoding="utf-8") as file:

        file.write("=" * 52 + "\n")
        file.write("HISTORIAL DE CANCIONES DUPLICADAS\n")
        file.write("=" * 52 + "\n\n")

        if not duplicates:
            file.write("No se encontraron duplicados.\n")
        else:
            for i, d in enumerate(duplicates, start=1):
                file.write(f"{i}. {d['name']} - {d['artist']}\n")
                file.write(f"   Posición eliminada: {d['position'] + 1}\n")
                file.write(
                    f"   Posición conservada: {d['original_position'] + 1}\n"
                )
                file.write(f"   URI: {d['uri']}\n\n")

    print(f"\nHistorial guardado en: {filename}")


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def clean_playlist():

    # Snapshot ANTES de leer, para que las posiciones coincidan
    snapshot_id = sp.playlist(PLAYLIST_ID, fields="snapshot_id")["snapshot_id"]

    tracks = get_all_tracks(PLAYLIST_ID)

    duplicates = find_duplicates(tracks)

    print_duplicates(duplicates)

    if not duplicates:
        return

    save_history(duplicates)

    if DRY_RUN:
        print("\n" + "=" * 70)
        print("MODO PRUEBA ACTIVADO")
        print("=" * 70)
        print("\nNO se eliminó ninguna canción.")
        print("\nSi la lista de arriba es correcta, cambia:")
        print("\n    DRY_RUN = True")
        print("\npor:")
        print("\n    DRY_RUN = False")
        print("\nY vuelve a ejecutar el programa.")
        return

    remove_duplicates(PLAYLIST_ID, duplicates, snapshot_id)

    print("\n" + "=" * 70)
    print("PROCESO TERMINADO")
    print("=" * 70)
    print(f"\nSe eliminaron {len(duplicates)} duplicados.")


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":
    clean_playlist()