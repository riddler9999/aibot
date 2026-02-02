"""
Video Compilation Service
Combines video clips with voiceover to create the final recap
"""

import os
import subprocess
from typing import List, Dict, Optional


class VideoCompiler:
    """Compile video clips and audio into final recap video"""

    def __init__(self):
        self.output_width = 1280
        self.output_height = 720
        self.output_fps = 30

    def compile(
        self,
        video_clips: List[str],
        voiceover_path: str,
        output_folder: str,
        title: str = "Movie Recap",
        add_intro: bool = True,
        add_outro: bool = True
    ) -> str:
        """
        Compile video clips with voiceover into final video

        Args:
            video_clips: List of paths to video clip files
            voiceover_path: Path to voiceover audio file
            output_folder: Directory to save output
            title: Title for intro card
            add_intro: Whether to add title intro
            add_outro: Whether to add outro card

        Returns:
            Path to the compiled video file
        """
        if not video_clips:
            raise ValueError("No video clips provided")

        # Step 1: Create intro/outro if needed
        clips_to_concat = []

        if add_intro:
            intro_path = self._create_title_card(title, output_folder, "intro")
            clips_to_concat.append(intro_path)

        clips_to_concat.extend(video_clips)

        if add_outro:
            outro_path = self._create_title_card(
                "Thanks for watching!",
                output_folder,
                "outro"
            )
            clips_to_concat.append(outro_path)

        # Step 2: Concatenate all clips
        concat_path = self._concatenate_clips(clips_to_concat, output_folder)

        # Step 3: Add voiceover
        output_path = os.path.join(output_folder, "final_recap.mp4")
        self._add_audio(concat_path, voiceover_path, output_path)

        return output_path

    def _create_title_card(
        self,
        text: str,
        output_folder: str,
        name: str,
        duration: float = 3.0,
        bg_color: str = "black",
        text_color: str = "white"
    ) -> str:
        """Create a title card video clip"""
        output_path = os.path.join(output_folder, f"{name}.mp4")

        # Escape special characters in text for FFmpeg
        escaped_text = text.replace("'", "'\\''").replace(":", "\\:")

        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f'color=c={bg_color}:s={self.output_width}x{self.output_height}:d={duration}',
            '-vf', f"drawtext=text='{escaped_text}':fontsize=48:fontcolor={text_color}:x=(w-text_w)/2:y=(h-text_h)/2:font=Arial",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            # Fallback without text if font fails
            cmd_simple = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'color=c={bg_color}:s={self.output_width}x{self.output_height}:d={duration}',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                output_path
            ]
            subprocess.run(cmd_simple, capture_output=True, check=True)

        return output_path

    def _concatenate_clips(self, clips: List[str], output_folder: str) -> str:
        """Concatenate multiple video clips into one"""
        concat_path = os.path.join(output_folder, "concat.mp4")
        list_path = os.path.join(output_folder, "concat_list.txt")

        # Create concat list file
        with open(list_path, 'w') as f:
            for clip in clips:
                # Escape single quotes in path
                escaped_path = clip.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        # Use concat demuxer (faster, no re-encoding if codecs match)
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-an',  # No audio yet
            concat_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to concatenate clips: {e.stderr.decode()}")

        return concat_path

    def _add_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        mix_original: bool = False
    ):
        """Add audio track to video"""

        if mix_original:
            # Mix voiceover with original audio (if video had audio)
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-filter_complex',
                '[0:a]volume=0.3[a0];[1:a]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=longest',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                output_path
            ]
        else:
            # Replace audio entirely with voiceover
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',  # Match duration to shortest stream
                output_path
            ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to add audio: {e.stderr.decode()}")

    def adjust_video_duration(
        self,
        video_path: str,
        target_duration: float,
        output_path: str
    ):
        """
        Adjust video duration to match target (speed up or slow down)

        Useful for syncing video length with voiceover duration
        """
        # Get current duration
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        current_duration = float(result.stdout.strip())

        if current_duration <= 0:
            raise ValueError("Could not determine video duration")

        # Calculate speed factor
        speed_factor = current_duration / target_duration

        # FFmpeg setpts filter: PTS*factor (factor < 1 speeds up, > 1 slows down)
        pts_factor = 1 / speed_factor

        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-filter:v', f'setpts={pts_factor}*PTS',
            '-an',  # Remove audio (we'll add voiceover separately)
            '-c:v', 'libx264',
            '-preset', 'fast',
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to adjust duration: {e.stderr.decode()}")

    def add_subtitles(
        self,
        video_path: str,
        subtitles: List[Dict],
        output_path: str
    ):
        """
        Add burned-in subtitles to video

        Args:
            subtitles: List of dicts with 'start', 'end', 'text' keys
        """
        # Create SRT file
        srt_path = video_path.replace('.mp4', '.srt')

        with open(srt_path, 'w') as f:
            for i, sub in enumerate(subtitles, 1):
                start = self._seconds_to_srt_time(sub['start'])
                end = self._seconds_to_srt_time(sub['end'])
                text = sub['text']
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

        # Burn subtitles into video
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', f"subtitles='{srt_path}'",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-c:a', 'copy',
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to add subtitles: {e.stderr.decode()}")

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def get_video_duration(self, video_path: str) -> float:
        """Get duration of a video file in seconds"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
