# montage_ffmpeg_fix.py
import os
import re
import subprocess
import tempfile
import math
from PIL import Image, ImageDraw, ImageFont

# ---------- CONFIG ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "fichiers")
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")
OUTPUT_VIDEO = os.path.join(BASE_DIR, "video_finale.mp4")

VIDEO_W, VIDEO_H = 1080, 1920  # vertical 9:16
FPS = 30
TITLE_DURATION = 2.5          # secondes
FADE_DURATION = 0.5           # secondes pour fade in/out sur images
TEXT_AREA_HEIGHT = 220
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

def make_title_image(title, out_path):
    img = Image.new("RGB", (VIDEO_W, int(VIDEO_H*0.15)), (0,0,0))
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
    w,h = draw.textsize(title, font=font)
    draw.text(((VIDEO_W-w)//2, (img.height-h)//2), title, font=font, fill=(255,215,0))
    img.save(out_path)

def build_ass_file(text_entries, ass_path, title_offset):
    header = "[Script Info]\nScriptType: v4.00+\nCollisions: Normal\nPlayResX: %d\nPlayResY: %d\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n" % (VIDEO_W, VIDEO_H)
    # Alignment=5 : centré au milieu
    header += f"Style: {ASS_STYLE_NAME},DejaVu Sans,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,10,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
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
    # Exécute une commande et capture stdout/stderr pour debug
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

def main():
    title, narr_file, music_file, images, texts = parse_prompt(PROMPT_FILE)
    if not images:
        raise SystemExit("Aucune image trouvée dans prompt.txt")

    last_end_seconds = time_to_seconds(images[-1][2])
    total_duration = TITLE_DURATION + last_end_seconds

    tmpdir = tempfile.mkdtemp(prefix="montage_tmp_")
    print("Temp dir:", tmpdir)

    # title
    title_png = os.path.join(tmpdir, "title.png")
    make_title_image(title, title_png)
    title_mp4 = os.path.join(tmpdir, "title.mp4")
    vf_title = f"scale=1080:-1,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", title_png,
        "-t", str(TITLE_DURATION), "-vf", vf_title, "-r", str(FPS),
        "-pix_fmt", "yuv420p", title_mp4
    ])

    seg_files = []
    for idx, (imgfile, start_h, end_h) in enumerate(images):
        duration = time_to_seconds(end_h) - time_to_seconds(start_h)
        in_path = os.path.join(FILES_DIR, imgfile)
        if not os.path.exists(in_path):
            raise SystemExit(f"Image manquante: {in_path}")
        out_seg = os.path.join(tmpdir, f"seg_{idx:03d}.mp4")
        fade_out_start = max(0, duration - FADE_DURATION)
        vf = (
            f"scale=1080:-1:force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p,"
            f"fade=t=in:st=0:d={FADE_DURATION},fade=t=out:st={fade_out_start}:d={FADE_DURATION}"
        )
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", in_path,
            "-t", str(duration),
            "-vf", vf,
            "-r", str(FPS),
            "-pix_fmt", "yuv420p",
            out_seg
        ])
        seg_files.append(out_seg)

    concat_list = os.path.join(tmpdir, "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        f.write(f"file '{os.path.basename(title_mp4)}'\n")
        for sf in seg_files:
            f.write(f"file '{os.path.basename(sf)}'\n")
    concat_out = os.path.join(tmpdir, "concat_all.mp4")
    # run concat in tmpdir to use relative paths in the list
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.basename(concat_list), "-c", "copy", os.path.basename(concat_out)], cwd=tmpdir)

    ass_path = os.path.join(tmpdir, "subs.ass")
    build_ass_file(texts, ass_path, title_offset=TITLE_DURATION)

    # prepare audio
    narr_path = os.path.join(FILES_DIR, narr_file) if narr_file else None
    music_path = os.path.join(FILES_DIR, music_file) if music_file else None
    mixed_audio = os.path.join(tmpdir, "mixed_audio.mp3")

    if narr_path and music_path and os.path.exists(narr_path) and os.path.exists(music_path):
        filter_complex = "[0:a]volume=1[a0];[1:a]volume=0.18[a1];[a0][a1]amix=inputs=2:duration=longest"
        run([
            "ffmpeg", "-y", "-i", narr_path, "-i", music_path,
            "-filter_complex", filter_complex,
            "-c:a", "mp3", "-t", str(total_duration), os.path.basename(mixed_audio)
        ], cwd=tmpdir)
    elif narr_path and os.path.exists(narr_path):
        run(["ffmpeg", "-y", "-i", narr_path, "-c:a", "mp3", "-t", str(total_duration), os.path.basename(mixed_audio)], cwd=tmpdir)
    elif music_path and os.path.exists(music_path):
        run(["ffmpeg", "-y", "-i", music_path, "-af", "volume=0.18", "-c:a", "mp3", "-t", str(total_duration), os.path.basename(mixed_audio)], cwd=tmpdir)
    else:
        mixed_audio = None
        print("No audio sources found; final will be silent.")

    # FINAL: run from tmpdir and use relative ass path
    final_cmd = ["ffmpeg", "-y", "-i", os.path.basename(concat_out)]
    if mixed_audio:
        final_cmd += ["-i", os.path.basename(mixed_audio)]
    # use relative ass filename in filter; run with cwd=tmpdir so ffmpeg resolves it
    final_cmd += ["-vf", f"ass={os.path.basename(ass_path)}", "-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    if mixed_audio:
        final_cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k", "-shortest", "-t", str(total_duration)]
    else:
        final_cmd += ["-an", "-shortest", "-t", str(total_duration)]
    final_cmd += [OUTPUT_VIDEO]

    # execute final command in tmpdir
    run(final_cmd, cwd=tmpdir)

    print("✅ Vidéo finale:", OUTPUT_VIDEO)
    print("Temp files in:", tmpdir)

if __name__ == "__main__":
    main()
