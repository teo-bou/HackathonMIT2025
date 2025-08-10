# montage_ffmpeg_final.py
import os
import re
import subprocess
import tempfile
import math
from PIL import Image, ImageDraw, ImageFont

# ---------- CONFIG ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")
OUTPUT_VIDEO = os.path.join(BASE_DIR, "video_finale.mp4")

VIDEO_W, VIDEO_H = 1080, 1920  # vertical 9:16
FPS = 30
TITLE_DURATION = 2.5          # secondes
FADE_DURATION = 0.5           # secondes pour fade in/out sur images
ASS_STYLE_NAME = "Default"
# ----------------------------

def time_to_seconds(hms: str) -> float:
    parts = list(map(int, hms.split(":")))
    return parts[0] * 3600 + parts[1] * 60 + parts[2]

def seconds_to_ass(ts: float) -> str:
    h = int(ts // 3600)
    m = int((ts % 3600) // 60)
    s = int(ts % 60)
    cs = int(round((ts - math.floor(ts)) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def extract_section(content: str, name: str) -> str:
    """
    Récupère le bloc après 'name:' jusqu'au prochain header (ligne qui finit par ':') ou EOF.
    Case-insensitive.
    """
    pattern = rf'(?is){re.escape(name)}\s*:\s*(.*?)(?=\n\s*\w[\w \-]*\s*:|\Z)'
    m = re.search(pattern, content)
    return m.group(1).strip() if m else ""

def parse_prompt(path):
    """
    Parse prompt.txt et renvoie:
    title, music, narrs ([(file,hms),...]), sfxs ([(file,hms),...]), images ([(file,start,end),...]), texts ([(text,start,end),...])
    """
    if not os.path.exists(path):
        raise SystemExit(f"prompt introuvable: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    title_m = re.search(r'(?i)Titre\s*:\s*"(.*?)"', content)
    title = title_m.group(1).strip() if title_m else "Titre"

    music_m = re.search(r'(?i)Music\s*:\s*(\S+)', content)
    music = music_m.group(1).strip() if music_m else None

    # extraire sections robustement
    narr_block = extract_section(content, "Narration")
    sfx_block = extract_section(content, "SFX")
    images_block = extract_section(content, "Images")
    texts_block = extract_section(content, "Texte") or extract_section(content, "Text")

    # trouver fichiers + timecodes dans chaque bloc
    narrs = re.findall(r'(\S+\.mp3)\s+(\d{1,2}:\d{2}:\d{2})', narr_block)
    sfxs  = re.findall(r'(\S+\.mp3)\s+(\d{1,2}:\d{2}:\d{2})', sfx_block)
    images = re.findall(r'(\S+\.(?:jpg|png))\s+(\d{1,2}:\d{2}:\d{2})\s*-\s*(\d{1,2}:\d{2}:\d{2})', images_block)
    texts  = re.findall(r'"(.*?)"\s+(\d{1,2}:\d{2}:\d{2})\s*-\s*(\d{1,2}:\d{2}:\d{2})', texts_block)

    # debug print
    print("Parsed prompt ->")
    print(" Title :", title)
    print(" Music :", music)
    print(" Narrations:", narrs)
    print(" SFXs:", sfxs)
    print(" Images:", images)
    print(" Texts:", len(texts), "entries")

    return title, music, narrs, sfxs, images, texts

def make_title_image(title, out_path):
    img = Image.new("RGB", (VIDEO_W, VIDEO_H//6), (0,0,0))
    draw = ImageDraw.Draw(img)
    font = None
    for candidate in ["arial.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        try:
            font = ImageFont.truetype(candidate, 64)
            break
        except Exception:
            font = None
    if font is None:
        font = ImageFont.load_default()
    try:
        bbox = draw.textbbox((0,0), title, font=font)
        w = bbox[2]-bbox[0]; h = bbox[3]-bbox[1]
    except Exception:
        w,h = draw.textsize(title, font=font)
    draw.text(((VIDEO_W-w)//2, (img.height-h)//2), title, font=font, fill=(255,215,0))
    img.save(out_path)

def build_ass_file(text_entries, ass_path, title_offset):
    # ASS header with Alignment=5 (middle-center)
    header = "[Script Info]\nScriptType: v4.00+\nCollisions: Normal\nPlayResX: %d\nPlayResY: %d\n\n" % (VIDEO_W, VIDEO_H)
    header += "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    # set Alignment=5 (middle center) - MarginV=20
    header += f"Style: {ASS_STYLE_NAME},DejaVu Sans,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,20,1\n\n"
    header += "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    lines = [header]
    for text, start_h, end_h in text_entries:
        start_s = time_to_seconds(start_h) + title_offset
        end_s   = time_to_seconds(end_h) + title_offset
        start_ass = seconds_to_ass(start_s)
        end_ass = seconds_to_ass(end_s)
        txt = text.replace("\n", "\\N").replace(",", "\\,")
        lines.append(f"Dialogue: 0,{start_ass},{end_ass},{ASS_STYLE_NAME},,0000,0000,0000,,{txt}\n")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def run(cmd, cwd=None):
    print("RUN:", " ".join(cmd))
    try:
        p = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=cwd)
        if p.stdout:
            print("FFMPEG stdout:", p.stdout[:2000])
        if p.stderr:
            print("FFMPEG stderr:", p.stderr[:2000])
        return p
    except subprocess.CalledProcessError as e:
        print("Command failed. Returncode:", e.returncode)
        if e.stdout:
            print("STDOUT:\n", e.stdout)
        if e.stderr:
            print("STDERR:\n", e.stderr)
        raise

def build_audio_mix(tmpdir, music_path, narrs, sfxs, total_duration):
    """
    Make mixed audio file 'mixed_audio.mp3' in tmpdir.
    Inputs can be absolute paths. We run ffmpeg in tmpdir.
    """
    inputs = []
    filters = []
    labels = []
    idx = 0

    # Music
    if music_path:
        if not os.path.exists(music_path):
            print(f"⚠ Music not found: {music_path} (ignored)")
            music_path = None
        else:
            inputs.append(music_path)
            lbl = f"[a{idx}]"
            filters.append(f"[{idx}:a]volume=0.18,apad,atrim=0:{total_duration}{lbl}")
            labels.append(lbl)
            idx += 1

    # Narrations
    for narr_file, start_h in narrs:
        narr_path = narr_file
        if not os.path.exists(narr_path):
            print(f"⚠ Narration missing: {narr_path} (ignored)")
            continue
        inputs.append(narr_path)
        start = time_to_seconds(start_h) + TITLE_DURATION
        ms = int(round(start * 1000))
        lbl = f"[a{idx}]"
        filters.append(f"[{idx}:a]adelay={ms}|{ms},apad,atrim=0:{total_duration}{lbl}")
        labels.append(lbl)
        idx += 1

    # SFX
    for sfx_file, start_h in sfxs:
        sfx_path = sfx_file
        if not os.path.exists(sfx_path):
            print(f"⚠ SFX missing: {sfx_path} (ignored)")
            continue
        inputs.append(sfx_path)
        start = time_to_seconds(start_h) + TITLE_DURATION
        ms = int(round(start * 1000))
        lbl = f"[a{idx}]"
        filters.append(f"[{idx}:a]adelay={ms}|{ms},apad,atrim=0:{total_duration}{lbl}")
        labels.append(lbl)
        idx += 1

    if not inputs:
        print("No audio inputs found.")
        return None

    mixed_basename = "mixed_audio.mp3"
    out_path = os.path.join(tmpdir, mixed_basename)

    # single input -> just trim/export
    if len(labels) == 1:
        print("Single audio input -> simple trim/export")
        cmd = ["ffmpeg", "-y", "-i", inputs[0], "-t", str(total_duration), "-c:a", "mp3", mixed_basename]
        run(cmd, cwd=tmpdir)
        return out_path

    # multiple -> amix
    amix_inputs = "".join(labels)  # [a0][a1]...
    filters.append(f"{amix_inputs}amix=inputs={len(labels)}:duration=longest[aout]")

    filter_complex = ";".join(filters)
    print("Audio filter_complex:\n", filter_complex)

    cmd = ["ffmpeg", "-y"]
    for p in inputs:
        cmd += ["-i", p]
    cmd += ["-filter_complex", filter_complex, "-map", "[aout]", "-t", str(total_duration), "-c:a", "mp3", mixed_basename]

    run(cmd, cwd=tmpdir)
    return out_path

def montage():
    title, music_file, narrs, sfxs, images, texts = parse_prompt(PROMPT_FILE)

    print("Title:", title)
    print("Music file:", music_file)
    print("Narrations:", narrs)
    print("SFXs:", sfxs)
    print("Images:", images)
    print("Texts:", texts)

    # debug: existence checks
    print("Checking files exist")
    if music_file:
        print(" -", music_file, "exists?", os.path.exists(os.path.join(music_file)))
    for n in narrs:
        print(" - narr:", n[0], "exists?", os.path.exists(os.path.join(n[0])))
    for s in sfxs:
        print(" - sfx:", s[0], "exists?", os.path.exists(os.path.join(s[0])))

    if not images:
        raise SystemExit("Aucune image trouvée dans prompt.txt")

    last_end_seconds = time_to_seconds(images[-1][2])
    total_duration = TITLE_DURATION + last_end_seconds

    tmpdir = tempfile.mkdtemp(prefix="montage_tmp_")
    print("Temp dir:", tmpdir)

    # title (create in tmpdir)
    title_png = os.path.join(tmpdir, "title.png")
    make_title_image(title, title_png)
    title_mp4 = os.path.join(tmpdir, "title.mp4")
    vf_title = f"scale=1080:-1,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
    run(["ffmpeg", "-y", "-loop", "1", "-i", os.path.basename(title_png), "-t", str(TITLE_DURATION), "-vf", vf_title, "-r", str(FPS), "-pix_fmt", "yuv420p", os.path.basename(title_mp4)], cwd=tmpdir)

    # image segments (create in tmpdir)
    seg_files = []
    for idx, (imgfile, start_h, end_h) in enumerate(images):
        duration = time_to_seconds(end_h) - time_to_seconds(start_h)
        in_path = imgfile
        if not os.path.exists(in_path):
            raise SystemExit(f"Image manquante: {in_path}")
        out_seg = os.path.join(tmpdir, f"seg_{idx:03d}.mp4")
        fade_out_start = max(0, duration - FADE_DURATION)
        vf = (
            f"scale=1080:-1:force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p,"
            f"fade=t=in:st=0:d={FADE_DURATION},fade=t=out:st={fade_out_start}:d={FADE_DURATION}"
        )
        run(["ffmpeg", "-y", "-loop", "1", "-i", os.path.abspath(in_path), "-t", str(duration), "-vf", vf, "-r", str(FPS), "-pix_fmt", "yuv420p", os.path.basename(out_seg)], cwd=tmpdir)
        seg_files.append(out_seg)

    # concat
    concat_list = os.path.join(tmpdir, "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        f.write(f"file '{os.path.basename(title_mp4)}'\n")
        for sf in seg_files:
            f.write(f"file '{os.path.basename(sf)}'\n")
    concat_out = os.path.join(tmpdir, "concat_all.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.basename(concat_list), "-c", "copy", os.path.basename(concat_out)], cwd=tmpdir)

    # subs ASS (centered)
    ass_path = os.path.join(tmpdir, "subs.ass")
    build_ass_file(texts, ass_path, title_offset=TITLE_DURATION)

    # audio: pass absolute music path (or None)
    music_path = music_file if music_file else None
    mixed_audio = build_audio_mix(tmpdir, music_path, narrs, sfxs, total_duration)

    # final mux + burn subs (run in tmpdir)
    final_cmd = ["ffmpeg", "-y", "-i", os.path.basename(concat_out)]
    if mixed_audio:
        final_cmd += ["-i", os.path.basename(mixed_audio)]
    final_cmd += ["-vf", f"ass={os.path.basename(ass_path)}", "-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    if mixed_audio:
        final_cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k", "-shortest", "-t", str(total_duration)]
    else:
        final_cmd += ["-an", "-shortest", "-t", str(total_duration)]
    final_cmd += [OUTPUT_VIDEO]

    run(final_cmd, cwd=tmpdir)

    print("✅ Vidéo finale:", OUTPUT_VIDEO)
    print("Temp files in:", tmpdir)
