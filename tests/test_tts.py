"""
Standalone Mistral TTS test — run this directly in your terminal:

    python test_tts.py pad/naar/jouw/bestand.webm

It tests every step separately so you can see exactly where it fails.
"""

import os
import sys
import base64
import traceback

# ── Check: mistralai installed? ───────────────────────────────────────────────
try:
    from mistralai.client import Mistral
    print("✅ mistralai package found")
except ImportError:
    print("❌ mistralai not installed — run: pip install mistralai")
    sys.exit(1)

# ── Check: API key set? ───────────────────────────────────────────────────────
api_key = os.environ.get("MISTRAL_API_KEY", "")
if not api_key:
    print("❌ MISTRAL_API_KEY not set — run: export MISTRAL_API_KEY='your_key'")
    sys.exit(1)
print(f"✅ API key found (starts with: {api_key[:6]}...)")

# ── Check: audio file provided and readable? ──────────────────────────────────
if len(sys.argv) < 2:
    print("❌ No audio file given — usage: python test_tts.py path/to/file.webm")
    sys.exit(1)

audio_path = sys.argv[1]
if not os.path.exists(audio_path):
    print(f"❌ File not found: {audio_path}")
    sys.exit(1)

file_size = os.path.getsize(audio_path)
print(f"✅ Audio file found: {audio_path} ({file_size} bytes)")

# ── Step 1: base64-encode the audio ──────────────────────────────────────────
print("\n── Step 1: encoding audio ───────────────────────────────────────────")
try:
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")
    print(f"✅ Encoded to base64 ({len(audio_b64)} characters)")
except Exception:
    print("❌ Failed to read/encode file:")
    traceback.print_exc()
    sys.exit(1)

# ── Step 2: connect to Mistral ────────────────────────────────────────────────
print("\n── Step 2: connecting to Mistral ────────────────────────────────────")
try:
    client = Mistral(api_key=api_key)
    print("✅ Mistral client created")
except Exception:
    print("❌ Failed to create Mistral client:")
    traceback.print_exc()
    sys.exit(1)

# ── Step 3: create a voice profile ───────────────────────────────────────────
print("\n── Step 3: creating voice profile ───────────────────────────────────")
voice_id = None
try:
    voice = client.audio.voices.create(
        name="test-voice-delete-me",
        sample_audio=audio_b64,
        sample_filename=os.path.basename(audio_path),
        languages=["nl"],
    )
    voice_id = voice.id
    print(f"✅ Voice created — id: {voice_id}")
except Exception:
    print("❌ Failed to create voice:")
    traceback.print_exc()
    sys.exit(1)

# ── Step 4: generate TTS ──────────────────────────────────────────────────────
print("\n── Step 4: generating TTS audio ─────────────────────────────────────")
try:
    response = client.audio.speech.complete(
        model="voxtral-mini-tts-2603",
        input="Goed gedaan! Bedankt voor je deelname aan dit onderzoek.",
        voice_id=voice_id,
        response_format="mp3",
    )
    print("✅ TTS response received")
    print(f"   response type : {type(response)}")
    print(f"   attributes    : {[a for a in dir(response) if not a.startswith('_')]}")
except Exception:
    print("❌ Failed to generate TTS:")
    traceback.print_exc()
    # Still try to clean up voice
    try:
        client.audio.voices.delete(voice_id)
        print("🧹 Voice profile deleted")
    except Exception:
        pass
    sys.exit(1)

# ── Step 5: save the output ───────────────────────────────────────────────────
print("\n── Step 5: saving output audio ──────────────────────────────────────")
try:
    out_path = "tts_test_output.mp3"

    # Try the most common attribute names — print whichever exists
    if hasattr(response, "audio_data") and response.audio_data:
        print(f"   audio_data found (length: {len(response.audio_data)})")
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(response.audio_data))

    elif hasattr(response, "content") and response.content:
        print(f"   content found (length: {len(response.content)})")
        with open(out_path, "wb") as f:
            f.write(response.content)

    else:
        print("⚠️  Neither audio_data nor content found on response.")
        print("   Full response repr:")
        print(f"   {repr(response)}")
        sys.exit(1)

    saved_size = os.path.getsize(out_path)
    print(f"✅ Saved to {out_path} ({saved_size} bytes)")

except Exception:
    print("❌ Failed to save output:")
    traceback.print_exc()
    sys.exit(1)

# ── Cleanup ───────────────────────────────────────────────────────────────────
finally_ran = False
try:
    client.audio.voices.delete(voice_id)
    print("\n🧹 Temporary voice profile deleted from Mistral")
    finally_ran = True
except Exception:
    print("\n⚠️  Could not delete voice profile — delete it manually in Mistral Studio")

print("\n── All done ─────────────────────────────────────────────────────────")
print(f"🎧 Open tts_test_output.mp3 to hear the result!")
