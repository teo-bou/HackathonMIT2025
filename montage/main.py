import os
import re
import subprocess

# 📂 Chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "fichiers")
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")
OUTPUT_VIDEO = os.path.join(BASE_DIR, "video_finale.mp4")

# 📄 Lire le prompt
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt_content = f.read()

# 🎤 Extraire le fichier narration
narration_match = re.search(r"Narration:\s*(.+)", prompt_content)
narration_file = narration_match.group(1).strip() if narration_match else None
narration_path = os.path.join(FILES_DIR, narration_file) if narration_file else None

# 🎵 Extraire le fichier musique
music_match = re.search(r"Music:\s*(.+)", prompt_content)
music_file = music_match.group(1).strip() if music_match else None
music_path = os.path.join(FILES_DIR, music_file) if music_file else None

# 🖼 Extraire les images avec timecodes
image_lines = re.findall(r"(\S+\.(?:jpg|png))\s+(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+)", prompt_content)
images_info = [(os.path.join(FILES_DIR, img), start, end) for img, start, end in image_lines]

# 🏗 Création d'un fichier temporaire pour FFmpeg concat
ffmpeg_list_path = os.path.join(BASE_DIR, "ffmpeg_images.txt")
with open(ffmpeg_list_path, "w", encoding="utf-8") as f:
    for img_path, start, end in images_info:
        # Calcul de la durée en secondes
        start_parts = list(map(int, start.split(":")))
        end_parts = list(map(int, end.split(":")))
        start_sec = start_parts[0] * 3600 + start_parts[1] * 60 + start_parts[2]
        end_sec = end_parts[0] * 3600 + end_parts[1] * 60 + end_parts[2]
        duration = end_sec - start_sec

        # Création d'une vidéo à partir de l'image (verticale 9:16)
        temp_video = f"temp_{os.path.basename(img_path)}.mp4"
        duration_cmd = f'ffmpeg -y -loop 1 -i "{img_path}" -t {duration} -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" -pix_fmt yuv420p -r 30 "{temp_video}"'
        subprocess.run(duration_cmd, shell=True)
        f.write(f"file '{temp_video}'\n")

# 🎬 Concaténer les images en une vidéo
concat_cmd = f'ffmpeg -y -f concat -safe 0 -i "{ffmpeg_list_path}" -c:v libx264 -pix_fmt yuv420p temp_video.mp4'
subprocess.run(concat_cmd, shell=True)

# 🎧 Combiner narration et musique
if narration_path and os.path.exists(narration_path):
    if music_path and os.path.exists(music_path):
        # Mix narration + musique de fond
        mixed_audio = "temp_audio.mp3"
        subprocess.run(f'ffmpeg -y -i "{narration_path}" -i "{music_path}" -filter_complex "[0:a]volume=1.0[a0];[1:a]volume=0.2[a1];[a0][a1]amix=inputs=2:duration=longest" "{mixed_audio}"', shell=True)
        audio_source = mixed_audio
    else:
        audio_source = narration_path

    final_cmd = f'ffmpeg -y -i temp_video.mp4 -i "{audio_source}" -shortest -c:v copy -c:a aac "{OUTPUT_VIDEO}"'
else:
    final_cmd = f'ffmpeg -y -i temp_video.mp4 -c:v copy "{OUTPUT_VIDEO}"'

subprocess.run(final_cmd, shell=True)

# 🧹 Nettoyage
for img_path, _, _ in images_info:
    temp_file = f"temp_{os.path.basename(img_path)}.mp4"
    if os.path.exists(temp_file):
        os.remove(temp_file)
if os.path.exists("temp_video.mp4"):
    os.remove("temp_video.mp4")
if os.path.exists(ffmpeg_list_path):
    os.remove(ffmpeg_list_path)
if os.path.exists("temp_audio.mp3"):
    os.remove("temp_audio.mp3")

print(f"✅ Vidéo générée : {OUTPUT_VIDEO}")
# Fin du script