# montage_moviepy_v2.py
import os
import re
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import importlib

# ---- Imports robustes pour MoviePy (essayez editor, sinon import "sous-modules") ----
try:
    # premier essai (fonctionne sur de nombreuses installs)
    from moviepy.editor import (
        ImageClip, AudioFileClip, concatenate_videoclips,
        CompositeAudioClip, CompositeVideoClip, ColorClip
    )
    from moviepy.video.fx.all import fadein, fadeout
except Exception:
    # fallback : import explicite des sous-modules (compatible avec les réorganisations)
    ImageClip = importlib.import_module("moviepy.video.VideoClip").ImageClip
    AudioFileClip = importlib.import_module("moviepy.audio.io.AudioFileClip").AudioFileClip
    concatenate_videoclips = importlib.import_module("moviepy.video.compositing.concatenate").concatenate_videoclips
    CompositeAudioClip = importlib.import_module("moviepy.audio.CompositeAudioClip").CompositeAudioClip
    CompositeVideoClip = importlib.import_module("moviepy.video.compositing.CompositeVideoClip").CompositeVideoClip
    ColorClip = importlib.import_module("moviepy.video.VideoClip").ColorClip
    # fx fade : si indisponible, on fera sans fade
    try:
        fadein = importlib.import_module("moviepy.video.fx.all").fadein
        fadeout = importlib.import_module("moviepy.video.fx.all").fadeout
    except Exception:
        fadein = None
        fadeout = None

# ----------------- CONFIG -----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "fichiers")
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")
OUTPUT_VIDEO = os.path.join(BASE_DIR, "video_finale.mp4")

VIDEO_W, VIDEO_H = 1080, 1920  # vertical 9:16
FPS = 30
TITLE_DURATION = 2.5
FADE_DURATION = 0.5
TEXT_AREA_HEIGHT = 220  # zone pour le texte en bas
# ------------------------------------------

def time_to_seconds(t):
    h, m, s = map(int, t.split(":"))
    return h*3600 + m*60 + s

def parse_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    title_m = re.search(r'Titre\s*:\s*"(.*?)"', content)
    title = title_m.group(1) if title_m else "Titre"

    narr_m = re.search(r"Narration:\s*(.+)", content)
    narr = narr_m.group(1).strip() if narr_m else None

    music_m = re.search(r"Music:\s*(.+)", content)
    music = music_m.group(1).strip() if music_m else None

    images = re.findall(r"(\S+\.(?:jpg|png))\s+(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+)", content)
    texts  = re.findall(r'"(.*?)"\s+(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+)', content)

    return title, narr, music, images, texts

def create_text_imageclip(text, duration, fontsize=64, color=(255,255,255,255)):
    # crée une image RGBA via Pillow et renvoie un ImageClip (numpy array)
    max_w = int(VIDEO_W * 0.9)
    img_w, img_h = max_w, TEXT_AREA_HEIGHT
    img = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    # tenter de charger une police TTF ; fallback par défaut
    font = None
    for fpath in ["arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        try:
            font = ImageFont.truetype(fpath, fontsize)
            break
        except Exception:
            font = None
    if font is None:
        font = ImageFont.load_default()

    # wrap
    lines = textwrap.wrap(text, width=30)
    line_h = font.getsize("Ay")[1] if hasattr(font, "getsize") else fontsize + 4
    total_h = line_h * len(lines)
    y = (img_h - total_h) // 2
    for line in lines:
        w, h = draw.textsize(line, font=font)
        draw.text(((img_w - w)//2, y), line, font=font, fill=color)
        y += line_h

    arr = np.array(img)
    clip = ImageClip(arr).set_duration(duration)
    # position: bottom center, un peu au-dessus du bord
    clip = clip.set_position(("center", VIDEO_H - img_h - 40))
    return clip

def main():
    title, narr_file, music_file, images, texts = parse_prompt(PROMPT_FILE)
    if not images:
        raise SystemExit("Aucune image trouvée dans prompt.txt")

    # dernier timecode (les timecodes des images commencent à 00:00:00 correspondant au début des images)
    last_end = time_to_seconds(images[-1][2])

    # créer les clips image
    clips = []
    for idx, (img_file, start, end) in enumerate(images):
        duration = time_to_seconds(end) - time_to_seconds(start)
        img_path = os.path.join(FILES_DIR, img_file)
        if not os.path.exists(img_path):
            raise SystemExit(f"Image manquante: {img_path}")

        ic = ImageClip(img_path).set_duration(duration)
        # resize en gardant ratio, centré sur fond noir 1080x1920
        ic = ic.resize(height=VIDEO_H)
        if ic.w > VIDEO_W:
            ic = ic.resize(width=VIDEO_W)
        bg = ColorClip(size=(VIDEO_W, VIDEO_H), color=(0,0,0)).set_duration(duration)
        composed = CompositeVideoClip([bg, ic.set_position("center")]).set_duration(duration)

        # fondus (si fx disponibles)
        if fadein and fadeout:
            if idx > 0:
                composed = fadein(composed, FADE_DURATION)
            if idx < len(images) - 1:
                composed = fadeout(composed, FADE_DURATION)

        clips.append(composed)

    # concat body (les images vont commencer après le titre)
    video_body = concatenate_videoclips(clips, method="compose")

    # créer le titre (image via Pillow)
    title_h = int(VIDEO_H * 0.15)
    title_img = Image.new("RGBA", (VIDEO_W, title_h), (0,0,0,0))
    d = ImageDraw.Draw(title_img)
    try:
        font = ImageFont.truetype("arial.ttf", 120)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        except Exception:
            font = ImageFont.load_default()
    w, h = d.textsize(title, font=font)
    d.text(((VIDEO_W-w)//2, (title_img.size[1]-h)//2), title, font=font, fill=(255,255,0,255))
    title_clip = ImageClip(np.array(title_img)).set_duration(TITLE_DURATION)
    if fadein and fadeout:
        title_clip = fadein(title_clip, 0.4)
        title_clip = fadeout(title_clip, 0.4)

    # full timeline : titre puis body (les timecodes du prompt correspondent au début du body = TITLE_DURATION)
    full_video = concatenate_videoclips([title_clip, video_body], method="compose")

    # créer les overlays texte et les positionner : on décale par TITLE_DURATION
    text_clips = []
    for txt, start, end in texts:
        start_s = time_to_seconds(start) + TITLE_DURATION
        end_s = time_to_seconds(end) + TITLE_DURATION
        dur = end_s - start_s
        if dur <= 0:
            continue
        txt_clip = create_text_imageclip(txt, dur, fontsize=64)
        txt_clip = txt_clip.set_start(start_s)
        text_clips.append(txt_clip)

    # composite final (video + textes)
    all_clips = [full_video] + text_clips
    composite = CompositeVideoClip(all_clips, size=(VIDEO_W, VIDEO_H))

    # AUDIO : narration + musique, démarrent après le titre ; on clippe chaque piste à la durée last_end
    audio_clips = []
    if narr_file:
        narr_path = os.path.join(FILES_DIR, narr_file)
        if os.path.exists(narr_path):
            narr_audio = AudioFileClip(narr_path).set_start(TITLE_DURATION).set_duration(last_end)
            audio_clips.append(narr_audio)
        else:
            print("Warning: narration file not found:", narr_path)

    if music_file:
        music_path = os.path.join(FILES_DIR, music_file)
        if os.path.exists(music_path):
            music_audio = AudioFileClip(music_path).volumex(0.2).set_start(TITLE_DURATION).set_duration(last_end)
            audio_clips.append(music_audio)
        else:
            print("Warning: music file not found:", music_path)

    if audio_clips:
        final_audio = CompositeAudioClip(audio_clips).set_duration(last_end + TITLE_DURATION)
        composite = composite.set_audio(final_audio)

    # durée finale = last_end (images) + title duration (titre placé avant)
    final_duration = last_end + TITLE_DURATION
    composite = composite.set_duration(final_duration)

    # export
    composite.write_videofile(
        OUTPUT_VIDEO,
        codec="libx264",
        audio_codec="aac",
        fps=FPS,
        threads=4,
        preset="medium"
    )

    print("✅ Vidéo générée :", OUTPUT_VIDEO)

if __name__ == "__main__":
    main()
