"""
voice.system_voice — системный провайдер озвучки (pyttsx3).
Владельцы: SystemProvider (_speak_sys из монолита).
Зависимости: pyttsx3 (ленивый импорт); kai.voice.styles.EMOTION_FX.
"""
from kai.voice.styles import EMOTION_FX


class SystemProvider:
    """Локальный офлайн-голос; последний фолбэк в цепочке."""

    def __init__(self, engine):
        self.engine = engine

    def available(self):
        return True

    def speak(self, text, tts, rate_pct, params, emotion):
        try:
            if tts is None:
                import pyttsx3
                tts = pyttsx3.init()
            st, speed, vol = EMOTION_FX.get(emotion, (0, 1.0, 1.0))
            total = rate_pct + params[2]
            tts.setProperty("rate", max(100, int((200 + total * 2 + st * 10) * speed)))
            tts.setProperty("volume", vol)
            tts.say(text)
            tts.runAndWait()
        except Exception:
            pass
        return tts
