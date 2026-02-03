"""
Text-to-Speech Service
Generates voiceover audio with multiple fallback options:
1. Edge-TTS (Microsoft) - Primary
2. gTTS (Google) - Fallback
3. OpenAI TTS - Premium fallback
"""

import os
import asyncio
import subprocess
from typing import Optional, List, Dict


class TextToSpeech:
    """Generate voiceover audio from text with fallback support"""

    # Popular voices for movie narration (Edge-TTS)
    VOICES = {
        'male_us': 'en-US-GuyNeural',
        'female_us': 'en-US-JennyNeural',
        'male_uk': 'en-GB-RyanNeural',
        'female_uk': 'en-GB-SoniaNeural',
        'male_au': 'en-AU-WilliamNeural',
        'female_au': 'en-AU-NatashaNeural',
        'dramatic': 'en-US-DavisNeural',
        'storyteller': 'en-US-TonyNeural',
    }

    def __init__(self, voice: str = None):
        """
        Initialize TTS with specified voice

        Args:
            voice: Voice name or key from VOICES dict
        """
        default_voice = os.getenv('TTS_VOICE', 'en-US-GuyNeural')

        if voice in self.VOICES:
            self.voice = self.VOICES[voice]
        else:
            self.voice = voice or default_voice

        self.rate = "+0%"
        self.pitch = "+0Hz"

    def generate(
        self,
        text: str,
        output_folder: str,
        filename: str = "voiceover.mp3"
    ) -> str:
        """
        Generate voiceover audio from text with fallback support

        Tries in order:
        1. Edge-TTS (Microsoft)
        2. gTTS (Google)
        3. OpenAI TTS (if API key available)

        Args:
            text: The narration text to convert to speech
            output_folder: Directory to save the audio file
            filename: Output filename

        Returns:
            Path to the generated audio file
        """
        output_path = os.path.join(output_folder, filename)

        # Try Edge-TTS first
        try:
            asyncio.run(self._generate_edge_tts(text, output_path))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
        except Exception as e:
            print(f"Edge-TTS failed: {e}")

        # Try gTTS as fallback
        try:
            self._generate_gtts(text, output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print("Using gTTS fallback")
                return output_path
        except Exception as e:
            print(f"gTTS failed: {e}")

        # Try OpenAI TTS as final fallback
        if os.getenv('OPENAI_API_KEY'):
            try:
                self._generate_openai_tts(text, output_path)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print("Using OpenAI TTS fallback")
                    return output_path
            except Exception as e:
                print(f"OpenAI TTS failed: {e}")

        # Try pyttsx3 as offline fallback
        try:
            self._generate_pyttsx3(text, output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print("Using pyttsx3 offline fallback")
                return output_path
        except Exception as e:
            print(f"pyttsx3 failed: {e}")

        raise RuntimeError("All TTS services failed. Please check your internet connection.")

    async def _generate_edge_tts(self, text: str, output_path: str):
        """Generate using Edge-TTS (Microsoft)"""
        import edge_tts

        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            pitch=self.pitch
        )
        await communicate.save(output_path)

    def _generate_gtts(self, text: str, output_path: str):
        """Generate using gTTS (Google Text-to-Speech)"""
        from gtts import gTTS

        # Determine language from voice setting
        lang = 'en'
        if 'en-GB' in self.voice:
            lang = 'en'
            tld = 'co.uk'
        elif 'en-AU' in self.voice:
            lang = 'en'
            tld = 'com.au'
        else:
            tld = 'com'

        tts = gTTS(text=text, lang=lang, tld=tld, slow=False)
        tts.save(output_path)

    def _generate_openai_tts(self, text: str, output_path: str):
        """Generate using OpenAI TTS API"""
        from openai import OpenAI

        client = OpenAI()

        # Map voice to OpenAI voices
        openai_voice = 'onyx'  # Default male
        if 'Female' in self.voice or 'Jenny' in self.voice or 'Sonia' in self.voice:
            openai_voice = 'nova'
        elif 'Guy' in self.voice or 'Ryan' in self.voice:
            openai_voice = 'onyx'

        response = client.audio.speech.create(
            model="tts-1",
            voice=openai_voice,
            input=text
        )

        response.stream_to_file(output_path)

    def _generate_pyttsx3(self, text: str, output_path: str):
        """Generate using pyttsx3 (offline)"""
        import pyttsx3

        engine = pyttsx3.init()

        # Adjust voice
        voices = engine.getProperty('voices')
        if voices:
            # Try to find a matching voice
            for voice in voices:
                if 'female' in self.voice.lower() and 'female' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
                elif 'male' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break

        engine.setProperty('rate', 150)  # Speed
        engine.save_to_file(text, output_path)
        engine.runAndWait()

    def generate_with_timestamps(
        self,
        text: str,
        output_folder: str,
        filename: str = "voiceover.mp3"
    ) -> Dict:
        """
        Generate voiceover with word-level timestamps

        Note: Timestamps only available with Edge-TTS
        """
        output_path = os.path.join(output_folder, filename)
        timestamps = []

        async def generate_with_sync():
            import edge_tts

            communicate = edge_tts.Communicate(
                text,
                self.voice,
                rate=self.rate,
                pitch=self.pitch
            )

            with open(output_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        timestamps.append({
                            "text": chunk["text"],
                            "offset": chunk["offset"] / 10000000,
                            "duration": chunk["duration"] / 10000000
                        })

        try:
            asyncio.run(generate_with_sync())
            return {
                "audio_path": output_path,
                "timestamps": timestamps,
                "total_duration": timestamps[-1]["offset"] + timestamps[-1]["duration"] if timestamps else 0
            }
        except Exception as e:
            # Fallback without timestamps
            print(f"Edge-TTS with timestamps failed: {e}, using fallback")
            audio_path = self.generate(text, output_folder, filename)
            return {
                "audio_path": audio_path,
                "timestamps": [],
                "total_duration": self._get_audio_duration(audio_path)
            }

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            return 0

    def set_voice_style(self, rate: str = "+0%", pitch: str = "+0Hz"):
        """
        Adjust voice characteristics

        Args:
            rate: Speech rate (-50% to +50%)
            pitch: Voice pitch (-50Hz to +50Hz)
        """
        self.rate = rate
        self.pitch = pitch

    @classmethod
    def list_voices(cls, language: str = "en") -> List[Dict]:
        """List available voices for a language"""
        try:
            import edge_tts
            voices = asyncio.run(edge_tts.list_voices())

            filtered = [
                {
                    "name": v["Name"],
                    "gender": v["Gender"],
                    "locale": v["Locale"],
                    "friendly_name": v["FriendlyName"]
                }
                for v in voices
                if v["Locale"].startswith(language)
            ]

            return filtered
        except Exception as e:
            print(f"Could not list Edge-TTS voices: {e}")
            return [
                {"name": "gTTS", "gender": "Neutral", "locale": "en", "friendly_name": "Google TTS (Fallback)"}
            ]
