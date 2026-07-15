# Pass a base64-encoded audio clip directly via ref_audio to clone a voice on the fly, without creating a saved voice.

import base64
from pathlib import Path
from mistralai.client import Mistral

client = Mistral(api_key="your-api-key")

ref_audio_b64 = base64.b64encode(Path("sample.mp3").read_bytes()).decode()

response = client.audio.speech.complete(
    model="voxtral-mini-tts-2603",
    input="This speech will sound like the voice in the reference audio.",
    ref_audio=ref_audio_b64,
    response_format="wav",
)

Path("output.wav").write_bytes(base64.b64decode(response.audio_data))
