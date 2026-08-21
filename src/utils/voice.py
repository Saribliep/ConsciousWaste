import os
from pathlib import Path
from mistralai.client import Mistral

client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

# todo: import reference_voice.mp3 from database 
sample_audio_b64 = base64.b64encode(Path("reference_voice.mp3").read_bytes()).decode()

# create a voice using the reference_voice audio
voice = client.audio.voices.create(
    name="my-voice",
    sample_audio=sample_audio_b64,
    sample_filename="reference_voice.mp3",
    languages=["nl", "en"],
    gender="female",
)

print(f"Created voice: {voice.id}")
print(f"Name: {voice.name}")
print(f"Languages: {voice.languages}")

# delete the voice
result = client.audio.voices.delete(voice_id="your-voice-id")
print(f"Deleted: {result.id}")
