"""
voice.gemini — провайдер озвучки через Gemini TTS.
Владельцы: GeminiProvider (генерация wav по инструкции манеры).
Зависимости: wave, os, tempfile, threading; google-genai (ленивый импорт);
kai.voice.styles.STYLE_PROMPTS.

Особенность: Gemini API геоблокирован в некоторых регионах (ошибка
400 FAILED_PRECONDITION "User location is not supported"). Для обхода
клиенту можно передать прокси: поле gemini_proxy в voice.json или в UI.
"""
import wave
import os
import tempfile
import threading

from kai.voice.styles import STYLE_PROMPTS


class GeminiProvider:
    """Генерирует wav по инструкции манеры; play() остаётся в VoiceEngine."""

    def __init__(self, engine):
        # engine — VoiceEngine: читаем ключ, голос, стили и кэш напрямую (как в монолите)
        self.engine = engine
        self.last_error = None

    def available(self):
        return bool(self.engine.gemini_key)

    def _proxy_kwargs(self):
        """httpx-аргументы прокси из настроек (без новых зависимостей)."""
        proxy = (self.engine.gemini_proxy or "").strip()
        if not proxy:
            return {}
        kwargs = {"proxy": proxy}
        verify = (self.engine.gemini_proxy_verify or "").strip()
        if verify.lower() in ("0", "false", "no"):
            kwargs["verify"] = False
        elif verify:
            kwargs["verify"] = verify
        return kwargs

    def _client(self):
        from google import genai
        from google.genai import types as gtypes
        cache_valid = (self.engine._gclient is not None
                       and self.engine._gclient_key == self.engine.gemini_key
                       and getattr(self.engine, "_gclient_proxy", None) == (self.engine.gemini_proxy or ""))
        if not cache_valid:
            proxy_kwargs = self._proxy_kwargs()
            http_options = None
            if proxy_kwargs:
                http_options = gtypes.HttpOptions(client_args=proxy_kwargs)
                # async-клиенту нужны те же аргументы (иначе SDK создаст его без прокси)
                try:
                    http_options.async_client_args = proxy_kwargs
                except Exception:
                    pass
            self.engine._gclient = genai.Client(api_key=self.engine.gemini_key,
                                                http_options=http_options)
            self.engine._gclient_key = self.engine.gemini_key
            self.engine._gclient_proxy = self.engine.gemini_proxy or ""
        return self.engine._gclient

    def render(self, text, emotion, ctx=None):
        """Генерирует wav через Gemini TTS, кладёт в кэш, возвращает путь"""
        key = ("gemini", text, emotion, self.engine.gemini_voice)
        with self.engine._cache_lock:
            if key in self.engine._cache:
                return self.engine._cache[key]
        from google.genai import types
        style = self.engine.styles.get(emotion, STYLE_PROMPTS.get(emotion, ""))
        prompt = f"Скажи по-русски. Стиль: {style}. Текст: {text}"
        try:
            resp = self._client().models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.engine.gemini_voice)))))
        except Exception as e:
            # Прокинули наверх: engine покажет ошибку и уйдёт по фолбэку осознанно
            self.last_error = str(e)
            raise
        part = resp.candidates[0].content.parts[0]
        data = part.inline_data.data
        mime = getattr(part.inline_data, "mime_type", "") or ""
        rate = 24000
        if "rate=" in mime:
            try:
                rate = int(mime.split("rate=")[1].split(";")[0])
            except Exception:
                pass
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(data)
        with self.engine._cache_lock:
            self.engine._cache[key] = path
        return path

    def speak(self, text, emotion):
        if not self.engine.gemini_key:
            return False
        try:
            path = self.render(text, emotion)
            owned = False
            self.engine._play_file(path)
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = str(e)
            print("Gemini TTS error:", e)
            return False
