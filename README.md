Markdown# Spotify Playlist Cleaner

Script en Python que detecta y elimina canciones duplicadas dentro de tus playlists de Spotify utilizando la API oficial y la librería Spotipy.

## Criterio de duplicados

Dos canciones se consideran duplicadas cuando coinciden exactamente en:
- Nombre de la canción.
- Lista completa de artistas (independientemente del orden).

La comparación no distingue entre mayúsculas y minúsculas, ni considera espacios repetidos o caracteres invisibles. Al encontrar duplicados, se conserva la primera aparición en la lista y se eliminan las posteriores.

## Características

- **Modo de prueba (DRY_RUN):** Muestra los duplicados identificados sin aplicar modificaciones en la playlist.
- **Registro de actividad:** Genera un historial en consola y guarda un reporte local en `historial_eliminadas.txt` con la posición eliminada, posición conservada y URI.
- **Borrado optimizado:** Procesamiento por lotes de hasta 100 elementos por consulta para cumplir con los límites de la API de Spotify.
- **Precisión por posición:** Elimina únicamente las copias repetidas mediante su índice exacto.
- **Filtrado:** Omite podcasts y archivos locales automáticamente.

## Requisitos

- Python 3.9 o superior
- Cuenta de Spotify (Free o Premium)
- Permisos de edición sobre la playlist (propia o colaborativa)
- Aplicación registrada en Spotify Developer Dashboard

## Instalación

```bash
git clone [https://github.com/TU_USUARIO/TU_REPOSITORIO.git](https://github.com/TU_USUARIO/TU_REPOSITORIO.git)
cd TU_REPOSITORIO
pip install spotipy python-dotenv
Configuración1. Registrar la aplicación en SpotifyAccede a Spotify Developer Dashboard y crea una aplicación.En Settings → Redirect URIs, añade la siguiente dirección de retorno:http://127.0.0.1:9090/callbackCopia las credenciales Client ID y Client Secret.2. Crear archivo de variables de entornoCrea un archivo .env en el directorio principal del proyecto:Fragmento de códigoSPOTIFY_CLIENT_ID=tu_client_id
SPOTIFY_CLIENT_SECRET=tu_client_secret
Añade los archivos sensibles y de caché a tu .gitignore:Plaintext.env
.cache
historial_eliminadas.txt
3. Asignar la playlistAbre el archivo Limpia_Playlist_de_Spotify.py y asigna el ID de tu playlist a la variable PLAYLIST_ID:Plaintext[https://open.spotify.com/playlist/6cHYwhc9MF3kjGDbFToaDT?si=](https://open.spotify.com/playlist/6cHYwhc9MF3kjGDbFToaDT?si=)...
                        └──────── ID ────────┘
UsoPaso 1: Modo de pruebaCon la variable DRY_RUN = True (activada por defecto), ejecuta el script para verificar las coincidencias sin realizar modificaciones:Bashpython Limpia_Playlist_de_Spotify.py
Paso 2: Ejecución de borradoSi el listado en consola es correcto, cambia la variable en el script a DRY_RUN = False y ejecuta nuevamente para procesar los cambios.Permisos (Scopes)ScopeFunciónplaylist-read-privateLeer contenido de las playlistsplaylist-modify-publicModificar playlists públicasplaylist-modify-privateModificar playlists privadasSolución de problemasErrorCausa y Soluciónclient_id: InvalidEl SPOTIFY_CLIENT_ID en el .env es incorrecto. Comprueba las credenciales en el dashboard.INVALID_CLIENT: Invalid redirect URILa Redirect URI registrada en el dashboard no coincide exactamente con la del script.Error 403 al borrarLa playlist no pertenece a la cuenta autenticada ni es colaborativa.No se aplican cambiosComprueba que la variable DRY_RUN esté configurada en False.NotasLas versiones con variaciones en el título (ej. "Canción - Remix") o colaboraciones distintas no se clasifican como duplicados.LicenciaMIT