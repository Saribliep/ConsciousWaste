import base64
from pathlib import Path
from mistralai.client import Mistral

client = Mistral(api_key="your-api-key")

response = client.audio.speech.complete(
    model="voxtral-mini-tts-2603",
    input="Hello! This is Voxtral, Mistral's text-to-speech model.",
    voice_id="your-voice-id",
    response_format="mp3",
)

Path("output.mp3").write_bytes(base64.b64decode(response.audio_data))
print("Saved to output.mp3")