"""Диагностика Gemini TTS: какие модели доступны с этим ключом и какая ошибка."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

KEY_FILE = os.path.expandvars(r"%APPDATA%\pixel\voice.json")
cfg = json.load(open(KEY_FILE, encoding="utf-8"))
key = cfg["gemini_key"]

from google import genai

client = genai.Client(api_key=key)


def scrub(s):
    return s.replace(key, "***KEY***")


print("== 1. Список моделей, поддерживающих generateContent ==")
try:
    for m in client.models.list():
        sup = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None)
        name = m.name
        if "tts" in name.lower() or (sup and "generateContent" in str(sup)):
            print(" ", name, "| actions:", sup)
except Exception as e:
    print("LIST ERROR:", scrub(str(e))[:500])

print("\n== 2. Прямой вызов TTS (gemini-2.5-flash-preview-tts, голос Leda) ==")
try:
    from google.genai import types
    resp = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents="Скажи по-русски. Стиль: спокойно. Текст: Привет, это тест голоса Кая.",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Leda")))))
    part = resp.candidates[0].content.parts[0]
    print("OK! mime:", getattr(part.inline_data, "mime_type", "?"), "| bytes:", len(part.inline_data.data))
except Exception as e:
    print("TTS ERROR:", scrub(str(e))[:800])
