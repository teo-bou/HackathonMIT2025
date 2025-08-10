import os
import re
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

# ---------- CONFIG ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "fichiers")
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")
OUTPUT_VIDEO = os.path.join(BASE_DIR, "video_finale_styled.mp4")

VIDEO_W, VIDEO_H = 1080, 1920
FPS = 30
TITLE_DURATION = 2.5
FADE_DURATION = 0.5
TEXT_FADE = 0.3
TEXT_FONT_SIZE = 72
TEXT_COLOR = (255, 255, 255)  # blanc
TEXT_OUTLINE = (0, 0, 0)      # contour noir
TEXT_POSITION_Y = VIDEO_H - 300  # position verticale des textes
# ----------------------------

def time_to_seconds(hms):
    h, m, s = map(int, hms.split(":"))
    return h * 3600 + m * 60 + s

def parse_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    title = re.search(r'Titre\s*:\s*"(.*?)"', content).group(1)
    narr = re.search(r"Narration:\s*(.+)", content).group(1).strip()
    music = re.search(r"Music:\s*(.+)", content).group(1).strip()
    images = re.findall(r"(\S+\.(?:jpg|png))\s+(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+)", content)
    texts  = re.findall(r'"(.*?)"\s+(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+)', content)

    return title, narr, music, images, texts

def make_title_image(title, out_path):
    img = Image.new("RGB", (VIDEO_W, VIDEO_H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 120)
    except:
        font = ImageFont.load_default()
    w, h = draw.textsize(title, font=font)
    draw.text(((VIDEO_W - w) // 2, (VIDEO_H - h) // 2), title, font=font, fill=(255, 215, 0))
    img.save(out_path)

def make_text_image(text, out_path):
    img = Image.new("RGBA", (VIDEO_W, VIDEO_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", TEXT_FONT_SIZE)
    except:
        font = ImageFont.load_default()
    w, h = draw.textsize(text, font=font)
    x = (VIDEO_W - w) // 2
    y = TEXT_POSITION_Y
    # contour noir
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            draw.text((x + dx, y + dy), text, font=font, fill=TEXT_OUTLINE)
    # texte blanc
    draw.text((x, y), text, font=font, fill=TEXT_COLOR)
    img.save(out_path)

def run(cmd, cwd=None):
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=cwd)

def main():
    title, narr_file, music_file, images, texts = parse_prompt(PROMPT_FILE)
    tmpdir = tempfile.mkdtemp(prefix="montage_styled_")
    print("Temp dir:", tmpdir)

    # Title clip
    title_img = os.path.join(tmpdir, "title.png")
    make_title_image(title, title_img)
    title_vid = os.path.join(tmpdir, "title.mp4")
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", title_img,
        "-t", str(TITLE_DURATION),
        "-vf", f"scale={VIDEO_W}:{VIDEO_H},format=yuv420p",
        "-r", str(FPS), title_vid
    ])

    # Image clips with Ken Burns effect
    seg_files = []
    for idx, (imgfile, start_h, end_h) in enumerate(images):
        duration = time_to_seconds(end_h) - time_to_seconds(start_h)
        in_path = os.path.join(FILES_DIR, imgfile)
        out_seg = os.path.join(tmpdir, f"seg_{idx:03d}.mp4")
        vf = (
            f"scale={VIDEO_W}:-1:force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z='min(zoom+0.0015,1.1)':d={FPS*duration}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
            f"fade=t=in:st=0:d={FADE_DURATION},fade=t=out:st={duration-FADE_DURATION}:d={FADE_DURATION},format=yuv420p"
        )
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", in_path,
            "-t", str(duration),
            "-vf", vf, "-r", str(FPS),
            out_seg
        ])
        seg_files.append(out_seg)

    # Concat video parts
    concat_list = os.path.join(tmpdir, "concat.txt")
    with open(concat_list, "w") as f:
        f.write(f"file '{os.path.basename(title_vid)}'\n")
        for sf in seg_files:
            f.write(f"file '{os.path.basename(sf)}'\n")
    concat_out = os.path.join(tmpdir, "concat.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", concat_out], cwd=tmpdir)

    # Add text overlays
    filter_parts = []
    input_files = [concat_out]
    last_v = "[0:v]"
    for idx, (text, start_h, end_h) in enumerate(texts, 1):
        start = time_to_seconds(start_h) + TITLE_DURATION
        end = time_to_seconds(end_h) + TITLE_DURATION
        txt_img = os.path.join(tmpdir, f"text_{idx}.png")
        make_text_image(text, txt_img)
        input_files.append(txt_img)
        out_v = f"[v{idx}]"
        filter_parts.append(f"{last_v}[{idx}:v]overlay=(W-w)/2:(H-h)/2:enable='between(t,{start},{end})'{out_v}")
        last_v = out_v

    filter_chain = ";".join(filter_parts)

    final_vid = os.path.join(tmpdir, "final_with_text.mp4")
    cmd = ["ffmpeg", "-y"]
    for f in input_files:
        cmd += ["-i", f]
    cmd += ["-filter_complex", filter_chain, "-map", last_v, "-pix_fmt", "yuv420p", final_vid]
    run(cmd)

    # Mix audio
    narr_path = os.path.join(FILES_DIR, narr_file)
    music_path = os.path.join(FILES_DIR, music_file)
    final_audio = os.path.join(tmpdir, "final_audio.mp3")
    run([
        "ffmpeg", "-y", "-i", narr_path, "-i", music_path,
        "-filter_complex", "[0:a]volume=1[a0];[1:a]volume=0.2[a1];[a0][a1]amix=inputs=2:duration=longest",
        final_audio
    ])

    # Merge video + audio
    run([
        "ffmpeg", "-y", "-i", final_vid, "-i", final_audio,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-shortest", OUTPUT_VIDEO
    ])

    print("✅ Vidéo finale stylée :", OUTPUT_VIDEO)

if __name__ == "__main__":
    main()
