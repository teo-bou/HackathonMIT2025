from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import os

load_dotenv()

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_API_KEY"),
)


def generate_audio(text: str, path: str) -> None:
    """
    Generate audio from text using ElevenLabs API.
    
    :param text: The text to convert to speech.
    """
    audio = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",  # Example voice ID
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    
    with open(path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

