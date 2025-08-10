import os
import requests
from dotenv import load_dotenv

load_dotenv()  # charge les variables du fichier .env dans os.environ

API_KEY = os.getenv("PEXELS_API_KEY")

headers = {
    "Authorization": API_KEY
}

def download_first_media(query, folder="C:\\Users\\anase\\Desktop\\HackathonMIT2025", filename="media1", is_video=False):
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    ext = ".mp4" if is_video else ".jpg"
    save_path = os.path.join(folder, filename + ext)

    if is_video:
        url = "https://api.pexels.com/videos/search"
        resource_key = "videos"
    else:
        url = "https://api.pexels.com/v1/search"
        resource_key = "photos"

    params = {
        "query": query,
        "per_page": 1
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Erreur API : {response.status_code} - {response.text}")
        return
    
    data = response.json()
    media_list = data.get(resource_key, [])
    if not media_list:
        print(f"Aucune ressource trouvée pour la requête '{query}'.")
        return

    first_media = media_list[0]

    if is_video:
        video_files = first_media.get("video_files", [])
        if not video_files:
            print("Aucune vidéo disponible à télécharger.")
            return
        best_video = max(video_files, key=lambda x: x.get("width", 0))
        media_url = best_video["link"]
    else:
        media_url = first_media["src"]["original"]

    media_response = requests.get(media_url, stream=is_video)
    if media_response.status_code == 200:
        with open(save_path, "wb") as f:
            if is_video:
                for chunk in media_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            else:
                f.write(media_response.content)
        print(f"{'Vidéo' if is_video else 'Image'} téléchargée et enregistrée sous '{save_path}'")
    else:
        print(f"Erreur lors du téléchargement : {media_response.status_code}")

def get_pictures_videos(req, is_video=False):
    folder_path = "C:\\Users\\anase\\Desktop\\HackathonMIT2025"
    for index, word in enumerate(req[-1]):
        filename = f"scene{req[index][0]}"
        download_first_media(word, folder=folder_path, filename=filename, is_video=is_video)

if __name__ == "__main__":
    get_pictures_videos(["sunrise"], is_video=True)
