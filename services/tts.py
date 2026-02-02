"""
Text-to-Speech Service
Generates voiceover audio using Edge-TTS (Microsoft)
"""

import os
import asyncio
import edge_tts
from typing import Optional, List, Dict


class TextToSpeech:
    """Generate voiceover audio from text"""

    # Popular voices for movie narration
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

        self.rate = "+0%"  # Speech rate adjustment
        self.pitch = "+0Hz"  # Pitch adjustment

    def generate(
        self,
        text: str,
        output_folder: str,
        filename: str = "voiceover.mp3"
    ) -> str:
        """
        Generate voiceover audio from text

        Args:
            text: The narration text to convert to speech
            output_folder: Directory to save the audio file
            filename: Output filename

        Returns:
            Path to the generated audio file
        """
        output_path = os.path.join(output_folder, filename)

        # Run async function in sync context
        asyncio.run(self._generate_async(text, output_path))

        return output_path

    async def _generate_async(self, text: str, output_path: str):
        """Async implementation of TTS generation"""
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            pitch=self.pitch
        )

        await communicate.save(output_path)

    def generate_with_timestamps(
        self,
        text: str,
        output_folder: str,
        filename: str = "voiceover.mp3"
    ) -> Dict:
        """
        Generate voiceover with word-level timestamps

        Useful for precise video-audio synchronization

        Returns:
            Dict with audio_path and word timestamps
        """
        output_path = os.path.join(output_folder, filename)
        timestamps = []

        async def generate_with_sync():
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
                            "offset": chunk["offset"] / 10000000,  # Convert to seconds
                            "duration": chunk["duration"] / 10000000
                        })

        asyncio.run(generate_with_sync())

        return {
            "audio_path": output_path,
            "timestamps": timestamps,
            "total_duration": timestamps[-1]["offset"] + timestamps[-1]["duration"] if timestamps else 0
        }

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
        """
        List available voices for a language

        Returns:
            List of voice information dicts
        """
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

    def preview_voices(self, text: str, output_folder: str) -> List[str]:
        """
        Generate preview audio for all available voice styles

        Useful for letting users choose their preferred narrator voice
        """
        previews = []

        for name, voice in self.VOICES.items():
            original_voice = self.voice
            self.voice = voice

            try:
                path = self.generate(
                    text[:200],  # Short preview
                    output_folder,
                    f"preview_{name}.mp3"
                )
                previews.append({
                    "name": name,
                    "voice": voice,
                    "path": path
                })
            finally:
                self.voice = original_voice

        return previews
