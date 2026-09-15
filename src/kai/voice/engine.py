"""
voice.engine — голосовой движок: очередь, worker-поток, кэш, конфиг voice.json.
Владельцы: VoiceEngine.
Зависимости: queue, json, os, time, asyncio, tempfile, threading, pathlib;
pygame (ленивый импорт); kai.text_utils.clean_for_speech; kai.voice.styles.STYLE_PROMPTS;
провайдеры kai.voice.gemini/edge/system_voice.
Цепочка фолбэков: gemini → edge → system.
"""
import queue
import json
import os
import time
import asyncio
import tempfile
import threading
from pathlib import Path

from kai.text_utils import clean_for_speech
from kai.voice.styles import STYLE_PROMPTS
from kai.voice.gemini import GeminiProvider
from kai.voice.edge import EdgeProvider
from kai.voice.system_voice import SystemProvider


class VoiceEngine:
    def __init__(self, data_dir):
        self.voice_file = Path(data_dir) / "voice.json"
        cfg = self._load_cfg()
        self.engine = cfg.get("engine", "edge")
        self.gemini_key = cfg.get("gemini_key", "")
        self.gemini_voice = cfg.get("gemini_voice", "Leda")
        # прокси для Gemini API (регионы с геоблоком): "http://host:port", "socks5://..."
        self.gemini_proxy = cfg.get("gemini_proxy", "")
        self.gemini_proxy_verify = cfg.get("gemini_proxy_verify", "")
        self.styles = dict(STYLE_PROMPTS)
        self.styles.update(cfg.get("styles", {}))
        self.voice_id = cfg.get("voice_id", "ru-RU-SvetlanaNeural")
        self.pitch_hz = cfg.get("pitch_hz", 0)
        self.rate_extra = cfg.get("rate_extra", 0)
        self.emotion_fx = cfg.get("emotion_fx", True)
        self._queue = queue.Queue()
        self._pygame_ok = False
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._gclient = None
        self._gclient_key = None
        try:
            import edge_tts
            self._edge_ok = True
        except ImportError:
            self._edge_ok = False
        self.gemini_provider = GeminiProvider(self)
        self.edge_provider = EdgeProvider(self)
        self.system_provider = SystemProvider(self)
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    def _load_cfg(self):
        try:
            if self.voice_file.exists():
                with open(self.voice_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_cfg(self):
        try:
            with open(self.voice_file, "w", encoding="utf-8") as f:
                json.dump({"engine": self.engine, "gemini_key": self.gemini_key,
                           "gemini_voice": self.gemini_voice, "styles": self.styles,
                           "gemini_proxy": self.gemini_proxy,
                           "gemini_proxy_verify": self.gemini_proxy_verify,
                           "voice_id": self.voice_id, "pitch_hz": self.pitch_hz,
                           "rate_extra": self.rate_extra, "emotion_fx": self.emotion_fx}, f)
        except Exception:
            pass

    def set_config(self, engine, gemini_key, gemini_voice, voice_id, pitch_hz, rate_extra,
                   gemini_proxy=None, gemini_proxy_verify=None):
        self.engine = engine
        self.gemini_key = gemini_key.strip()
        self.gemini_voice = gemini_voice
        self.voice_id = voice_id
        self.pitch_hz = pitch_hz
        self.rate_extra = rate_extra
        if gemini_proxy is not None:
            self.gemini_proxy = gemini_proxy.strip()
        if gemini_proxy_verify is not None:
            self.gemini_proxy_verify = gemini_proxy_verify.strip()
        self._gclient = None
        self._clear_cache()
        self._save_cfg()

    def last_error(self):
        """Последняя ошибка провайдера цепочки (для показа пользователю)."""
        for prov in (self.gemini_provider, self.edge_provider, self.system_provider):
            err = getattr(prov, "last_error", None)
            if err:
                return err
        return None

    def set_styles(self, styles):
        self.styles = dict(styles)
        self._clear_cache()
        self._save_cfg()

    def set_emotion_fx(self, on):
        self.emotion_fx = on
        self._save_cfg()

    def current_params(self):
        return (self.voice_id, self.pitch_hz, self.rate_extra)

    def edge_params(self, rate_pct, params):
        return self.edge_provider.edge_params(rate_pct, params)

    def speak(self, text, block=False, rate_pct=0, emotion="neutral"):
        cleaned = clean_for_speech(text)
        if not cleaned:
            return
        ev = threading.Event() if block else None
        self._queue.put((cleaned, ev, rate_pct, self.current_params(), emotion))
        if block:
            ev.wait(timeout=180)

    def prepare(self, text, rate_pct=0, emotion="caring"):
        cleaned = clean_for_speech(text)
        if not cleaned:
            return
        threading.Thread(target=self._prepare_sync,
                         args=(cleaned, rate_pct, emotion), daemon=True).start()

    def _prepare_sync(self, text, rate_pct, emotion):
        try:
            if self.engine == "gemini" and self.gemini_key:
                try:
                    self.gemini_provider.render(text, emotion)
                except Exception as e:
                    self.gemini_provider.last_error = str(e)
                    print("Gemini TTS error (prepare):", e)
            else:
                params = self.current_params()
                if params[0] is None:
                    return
                key = ("edge", text, rate_pct, params)
                with self._cache_lock:
                    if key in self._cache:
                        return
                import edge_tts
                voice_id, rate_str, pitch_str = self.edge_params(rate_pct, params)
                fd, path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                asyncio.run(edge_tts.Communicate(text, voice_id, rate=rate_str, pitch=pitch_str).save(path))
                with self._cache_lock:
                    self._cache[key] = path
        except Exception:
            pass

    def _clear_cache(self):
        with self._cache_lock:
            for path in self._cache.values():
                try:
                    os.remove(path)
                except Exception:
                    pass
            self._cache.clear()

    def clear(self):
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass
        try:
            if self._pygame_ok:
                import pygame
                pygame.mixer.music.stop()
        except Exception:
            pass
        self._clear_cache()

    def _ensure_pygame(self):
        import pygame
        if not self._pygame_ok:
            pygame.mixer.init()
            self._pygame_ok = True
        return pygame

    def _play_file(self, path):
        pygame = self._ensure_pygame()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

    # --- GEMINI ---
    def _gemini_client(self):
        return self.gemini_provider._client()

    def _gemini_generate(self, text, emotion):
        return self.gemini_provider.render(text, emotion)

    def _speak_gemini(self, text, emotion):
        return self.gemini_provider.speak(text, emotion)

    # --- EDGE ---
    def _apply_fx(self, src, emotion):
        return self.edge_provider.apply_fx(src, emotion)

    def _speak_edge(self, text, rate_pct, params, emotion):
        return self.edge_provider.speak(text, rate_pct, params, emotion)

    # --- SYS ---
    def _speak_sys(self, text, tts, rate_pct, params, emotion):
        return self.system_provider.speak(text, tts, rate_pct, params, emotion)

    def _loop(self):
        tts = None
        while True:
            text, ev, rate_pct, params, emotion = self._queue.get()
            try:
                ok = False
                if self.engine == "gemini":
                    ok = self._speak_gemini(text, emotion)
                    if not ok:
                        print("Gemini недоступен, фолбэк на edge/system.")
                if not ok:
                    ok = self._speak_edge(text, rate_pct, params, emotion)
                if not ok:
                    tts = self._speak_sys(text, tts, rate_pct, params, emotion)
            except Exception as e:
                print("Voice error:", e)
            finally:
                if ev:
                    ev.set()
