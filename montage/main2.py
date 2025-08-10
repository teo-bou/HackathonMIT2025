import os
import re
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips,
    CompositeAudioClip, TextClip, CompositeVideoClip
)

# 📂 Dossiers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "fichiers")
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")
OUTPUT_VIDEO = os.path.join(BASE_DIR, "video_finale.mp4")

# 📄 Lire prompt.txt
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt_content = f.read()

# 🔹 Extraire infos
title_match = re.search(r'Titre\s*:\s*"(.*?)"', prompt_content)
title_text = title_match.group(1) if title_match else "Titre"

narration_file = re.search(r"Narration:\s*(.+)", prompt_content).group(1).strip()
music_file = re.search(r"Music:\s*(.+)", prompt_content).group(1).strip()

# 📜 Récupérer images et textes
image_lines = re.findall(r"(\S+\.(?:jpg|png))\s+(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+)", prompt_content)
text_lines = re.findall(r'"(.*?)"\s+(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+)', prompt_content)

# 🔢 Fonction pour convertir HH:MM:SS → secondes
def time_to_seconds(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s

# 🕒 Durée totale = fin de la dernière image
last_end = time_to_seconds(image_lines[-1][2])

# 🎬 Clips images avec fondus
clips = []
for i, (img_file, start, end) in enumerate(image_lines):
    duration = time_to_seconds(end) - time_to_seconds(start)
    img_path = os.path.join(FILES_DIR, img_file)

    clip = ImageClip(img_path, duration=duration)
    clip = clip.resize(height=1920)
    if clip.w > 1080:
        clip = clip.resize(width=1080)
    clip = clip.on_color(size=(1080, 1920), color=(0, 0, 0), pos="center")

    # Fondus entrée/sortie
    if i > 0:
        clip = clip.crossfadein(0.5)
    if i < len(image_lines) - 1:
        clip = clip.crossfadeout(0.5)

    clips.append(clip)

video_clip = concatenate_videoclips(clips, method="compose")

# 📝 Ajouter textes
text_clips = []
for text, start, end in text_lines:
    start_s = time_to_seconds(start)
    end_s = time_to_seconds(end)
    txt_clip = (
        TextClip(text, fontsize=70, color="white", font="Arial-Bold")
        .set_position(("center", "bottom"))
        .set_start(start_s)
        .set_duration(end_s - start_s)
    )
    text_clips.append(txt_clip)

# 🏷 Titre animé au début
title_clip = (
    TextClip(title_text, fontsize=120, color="yellow", font="Arial-Bold")
    .set_position("center")
    .set_duration(2.5)
    .fadein(0.5)
    .fadeout(0.5)
)

# ⏯ Combiner tout
full_video = CompositeVideoClip([video_clip] + text_clips)
final_with_title = concatenate_videoclips([title_clip, full_video.set_start(0)], method="compose")

# 🎧 Audio narration + musique
narration_audio = AudioFileClip(os.path.join(FILES_DIR, narration_file))
audio_tracks = [narration_audio]

music_audio = AudioFileClip(os.path.join(FILES_DIR, music_file)).volumex(0.2)
music_audio = music_audio.set_duration(last_end)
audio_tracks.append(music_audio)

final_audio = CompositeAudioClip(audio_tracks).set_duration(last_end)
final_with_title = final_with_title.set_audio(final_audio).set_duration(last_end)

# 💾 Export
final_with_title.write_videofile(
    OUTPUT_VIDEO,
    codec="libx264",
    audio_codec="aac",
    fps=30
)

print(f"✅ Vidéo générée : {OUTPUT_VIDEO}")
