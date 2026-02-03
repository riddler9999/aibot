"""
Transcription Service
Converts audio to text using OpenAI Whisper
"""

import os
import whisper
from typing import Dict, List, Optional


class Transcriber:
    """Transcribe audio files to text using Whisper"""

    def __init__(self, model_name: str = None):
        """
        Initialize transcriber with specified Whisper model

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
        """
        self.model_name = model_name or os.getenv('WHISPER_MODEL', 'base')
        self.model = None

    def _load_model(self):
        """Lazy load the Whisper model"""
        if self.model is None:
            print(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)

    def transcribe(self, audio_path: str, language: str = None) -> Dict:
        """
        Transcribe audio file to text

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es', 'fr')

        Returns:
            Dictionary with full text and segments with timestamps
        """
        self._load_model()

        options = {
            'task': 'transcribe',
            'verbose': False
        }

        if language:
            options['language'] = language

        result = self.model.transcribe(audio_path, **options)

        # Process segments for better structure
        segments = []
        for seg in result.get('segments', []):
            segments.append({
                'start': seg['start'],
                'end': seg['end'],
                'text': seg['text'].strip(),
                'confidence': seg.get('confidence', 1.0)
            })

        return {
            'text': result['text'].strip(),
            'language': result.get('language', 'en'),
            'segments': segments,
            'duration': segments[-1]['end'] if segments else 0
        }

    def transcribe_with_timestamps(self, audio_path: str) -> List[Dict]:
        """
        Transcribe audio and return timestamped segments

        Useful for syncing narration with video
        """
        result = self.transcribe(audio_path)
        return result.get('segments', [])

    def detect_language(self, audio_path: str) -> str:
        """Detect the language of the audio"""
        self._load_model()

        # Load audio and pad/trim to 30 seconds
        audio = whisper.load_audio(audio_path)
        audio = whisper.pad_or_trim(audio)

        # Make log-Mel spectrogram
        mel = whisper.log_mel_spectrogram(audio).to(self.model.device)

        # Detect language
        _, probs = self.model.detect_language(mel)
        detected_lang = max(probs, key=probs.get)

        return detected_lang

    def get_dialogue_summary(self, transcript: Dict, max_chars: int = 10000) -> str:
        """
        Extract a condensed version of the dialogue

        Useful for summarization when the full transcript is too long
        """
        full_text = transcript.get('text', '')

        if len(full_text) <= max_chars:
            return full_text

        # Take text from beginning, middle, and end
        third = max_chars // 3
        summary = (
            full_text[:third] +
            "\n...\n" +
            full_text[len(full_text)//2 - third//2 : len(full_text)//2 + third//2] +
            "\n...\n" +
            full_text[-third:]
        )

        return summary
