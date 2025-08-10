# diff_ytb.py
import os
import re
import pickle
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")
VIDEO_FILE = os.path.join(BASE_DIR, "video_finale.mp4")
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")

# scope minimal pour upload
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def parse_prompt_title(prompt_path):
    if not os.path.exists(prompt_path):
        return "Video"
    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'Titre\s*:\s*"(.*?)"', content)
    return m.group(1) if m else "Video"

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print("ERREUR: client_secret.json introuvable dans le dossier du script.")
                print("Place ton fichier téléchargé depuis Google Cloud Console sous le nom client_secret.json.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # sauvegarde le token pour usages futurs
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)

def initialize_upload(youtube, file_path, title, description="", tags=None, categoryId="22", privacyStatus="public"):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": categoryId
        },
        "status": {
            "privacyStatus": privacyStatus
        }
    }

    media = MediaFileUpload(file_path, chunksize=1024*1024, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("Démarrage de l'upload...")
    response = None
    try:
        while response is None:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                print(f"Upload progress: {percent}%")
    except HttpError as e:
        print("Erreur HTTP lors de l'upload :", e)
        raise
    except Exception as e:
        print("Erreur inattendue lors de l'upload :", e)
        raise

    return response

def main():
    if not os.path.exists(VIDEO_FILE):
        print("ERREUR: video_finale.mp4 introuvable dans le dossier.")
        sys.exit(1)

    title = parse_prompt_title(PROMPT_FILE)
    print("Titre extrait pour la vidéo :", title)

    youtube = get_authenticated_service()
    try:
        res = initialize_upload(youtube, VIDEO_FILE, title=title,
                                description="Vidéo auto-publiée via script",
                                tags=["AI","viral","shorts"], categoryId="22", privacyStatus="public")
        video_id = res.get("id")
        print("Upload terminé !")
        print("Lien :", f"https://youtu.be/{video_id}")
    except HttpError as e:
        print("Upload échoué (HttpError). Détails :", e.content if hasattr(e,'content') else e)
    except Exception as e:
        print("Upload échoué. Détails :", e)

if __name__ == "__main__":
    main()
