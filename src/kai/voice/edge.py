"""
voice.edge — провайдер озвучки через edge-tts с ffmpeg-окраской.
Владельцы: EdgeProvider (_speak_edge/_apply_fx/_edge_params из монолита).
Зависимости: os, tempfile, asyncio, subprocess; edge-tts, imageio-ffmpeg (ленивые импорты).
"""
import os
import tempfile
import asyncio
import subprocess

from kai.voice.styles import EMOTION_FX


class EdgeProvider:
    """edge-tts + ffmpeg-окраска _apply_fx; play() остаётся в VoiceEngine."""

    def __init__(self, engine):
        self.engine = engine
        self.last_error = None

    def available(self):
        return self.engine._edge_ok

    @staticmethod
    def edge_params(rate_pct, params):
        voice_id, pitch_hz, rate_extra = params
        total = rate_pct + rate_extra
        rate_str = f"{'+' if total >= 0 else ''}{total}%"
        pitch_str = f"{'+' if pitch_hz >= 0 else ''}{pitch_hz}Hz"
        return voice_id, rate_str, pitch_str

    def apply_fx(self, src, emotion):
        if not self.engine.emotion_fx:
            return src
        st, speed, vol = EMOTION_FX.get(emotion, (0, 1.0, 1.0))
        if st == 0 and speed == 1.0 and vol == 1.0:
            return src
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return src
        f = 2 ** (st / 12.0)
        fd, dst = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        tempo = max(0.5, min(2.0, speed / f))
        filt = f"asetrate=24000*{f:.4f},aresample=24000,atempo={tempo:.4f},volume={vol:.2f}"
        try:
            subprocess.run([exe, "-y", "-i", src, "-af", filt, dst],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            return dst
        except Exception:
            try:
                os.remove(dst)
            except Exception:
                pass
            return src

    def speak(self, text, rate_pct, params, emotion):
        voice_id, rate_str, pitch_str = self.edge_params(rate_pct, params)
        if not self.engine._edge_ok or voice_id is None:
            if not self.engine._edge_ok:
                self.last_error = "edge-tts не установлен"
            return False
        try:
            key = ("edge", text, rate_pct, params)
            with self.engine._cache_lock:
                path = self.engine._cache.pop(key, None)
            owned = path is None
            if owned:
                import edge_tts
                fd, path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                try:
                    asyncio.run(edge_tts.Communicate(text, voice_id, rate=rate_str, pitch=pitch_str).save(path))
                except Exception as e:
                    self.last_error = str(e)
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                    return False
            play_path = self.apply_fx(path, emotion)
            try:
                self.engine._play_file(play_path)
            finally:
                if play_path != path:
                    try:
                        os.remove(play_path)
                    except Exception:
                        pass
                if owned:
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = str(e)
            return False
