"""
Summarization Service
Generates movie recap scripts using OpenAI GPT
"""

import os
import json
import re
from typing import Dict, List, Optional
from openai import OpenAI


class Summarizer:
    """Generate movie recap scripts using AI"""

    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')

    def generate_recap(
        self,
        transcript: Dict,
        movie_title: str = "Unknown Movie",
        genre: str = "Drama",
        target_duration: int = 120,
        style: str = "engaging"
    ) -> Dict:
        """
        Generate a 2-minute movie recap script

        Args:
            transcript: The full movie transcript with segments
            movie_title: Title of the movie
            genre: Genre of the movie
            target_duration: Target duration in seconds (default 120 = 2 min)
            style: Narration style (engaging, dramatic, humorous, documentary)

        Returns:
            Dictionary containing narration script and scene timestamps
        """
        # Prepare transcript text (condensed if too long)
        transcript_text = transcript.get('text', '')
        if len(transcript_text) > 15000:
            # Condense for API limits
            transcript_text = self._condense_transcript(transcript_text)

        movie_duration = transcript.get('duration', 7200)  # Default 2 hours

        prompt = self._build_prompt(
            transcript_text,
            movie_title,
            genre,
            target_duration,
            style,
            movie_duration
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=4000
            )

            content = response.choices[0].message.content
            return self._parse_response(content, movie_title, movie_duration)

        except Exception as e:
            raise RuntimeError(f"Failed to generate recap: {str(e)}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for recap generation"""
        return """You are an expert movie recap narrator, known for creating engaging,
concise, and entertaining movie summaries. Your recaps are famous for:

1. Capturing the essence of the story in a compelling way
2. Highlighting key plot points without unnecessary details
3. Creating dramatic tension and emotional engagement
4. Using vivid language that paints a picture
5. Maintaining a consistent narrative flow

Your task is to create a 2-minute movie recap narration script that will be
read as a voiceover while key scenes from the movie are shown.

IMPORTANT GUIDELINES:
- Write in present tense for immediacy
- Keep sentences punchy and dynamic
- Include emotional beats and turning points
- Avoid spoiling the ending completely (leave some mystery)
- Structure: Setup (20s) → Rising Action (40s) → Climax (40s) → Resolution hint (20s)
- The narration should be approximately 280-320 words for 2 minutes

You must respond in valid JSON format."""

    def _build_prompt(
        self,
        transcript: str,
        title: str,
        genre: str,
        duration: int,
        style: str,
        movie_duration: float
    ) -> str:
        """Build the prompt for recap generation"""
        words_target = int(duration * 2.5)  # ~2.5 words per second for narration

        return f"""Create a {duration}-second movie recap narration for:

MOVIE TITLE: {title}
GENRE: {genre}
MOVIE LENGTH: {movie_duration/60:.0f} minutes
NARRATION STYLE: {style}
TARGET WORD COUNT: {words_target-40} to {words_target} words

TRANSCRIPT/DIALOGUE FROM THE MOVIE:
{transcript}

Based on the transcript above, create an engaging recap narration.

Respond in this exact JSON format:
{{
    "title": "Recap title (e.g., '{title} - 2 Minute Recap')",
    "narration": "The full narration script here. Write it as continuous prose that will be read aloud.",
    "scene_timestamps": [
        {{"start": 0, "duration": 5, "description": "Opening scene description"}},
        {{"start": 300, "duration": 5, "description": "Key scene description"}},
        ... (include 20-25 scene suggestions spread across the movie)
    ],
    "key_moments": [
        "Brief description of key moment 1",
        "Brief description of key moment 2",
        ... (5-7 key moments)
    ],
    "tone": "The overall tone of the recap"
}}

For scene_timestamps:
- "start" is seconds from the beginning of the original movie
- Spread scenes evenly across the movie (0% to 95% of duration)
- Each scene should be 4-6 seconds
- Include {int(duration/5)} scenes to cover the {duration}-second recap
- Scene descriptions help identify what type of footage to show

Make the narration {style} and suitable for the {genre} genre."""

    def _condense_transcript(self, text: str, max_length: int = 15000) -> str:
        """Condense a long transcript while preserving key information"""
        if len(text) <= max_length:
            return text

        # Split into roughly equal parts and take samples
        parts = 5
        part_length = len(text) // parts
        sample_length = max_length // parts

        condensed = []
        for i in range(parts):
            start = i * part_length
            end = start + sample_length
            condensed.append(text[start:end])

        return "\n[...]\n".join(condensed)

    def _parse_response(self, content: str, title: str, duration: float) -> Dict:
        """Parse the AI response into structured data"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return data
        except json.JSONDecodeError:
            pass

        # Fallback: create structure from plain text
        return {
            "title": f"{title} - 2 Minute Recap",
            "narration": content,
            "scene_timestamps": self._generate_default_scenes(duration),
            "key_moments": [],
            "tone": "engaging"
        }

    def _generate_default_scenes(self, movie_duration: float, num_scenes: int = 24) -> List[Dict]:
        """Generate default evenly-spaced scene timestamps"""
        scenes = []
        interval = (movie_duration * 0.9) / num_scenes  # Use 90% of movie

        for i in range(num_scenes):
            scenes.append({
                "start": int(movie_duration * 0.05 + i * interval),
                "duration": 5,
                "description": f"Scene {i + 1}"
            })

        return scenes

    def refine_narration(self, narration: str, feedback: str) -> str:
        """Refine narration based on user feedback"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a script editor. Refine the narration based on the feedback while maintaining the same length and structure."
                    },
                    {
                        "role": "user",
                        "content": f"ORIGINAL NARRATION:\n{narration}\n\nFEEDBACK:\n{feedback}\n\nPlease provide the refined narration:"
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"Failed to refine narration: {str(e)}")
