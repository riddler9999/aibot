"""
Video Compilation Service
Combines video clips with voiceover to create the final 9:16 viral recap
with DNA modification for copyright avoidance
"""

import os
import subprocess
import random
from typing import List, Dict, Optional


class VideoCompiler:
    """Compile video clips and audio into final 9:16 viral recap video"""

    def __init__(self):
        # 9:16 vertical format for TikTok/Reels/Shorts
        self.output_width = 1080
        self.output_height = 1920
        self.output_fps = 30

    def compile(
        self,
        video_clips: List[str],
        voiceover_path: str,
        output_folder: str,
        title: str = "Movie Recap",
        add_intro: bool = True,
        add_outro: bool = True,
        apply_dna_mod: bool = True
    ) -> str:
        """
        Compile video clips with voiceover into final 9:16 viral video

        Args:
            video_clips: List of paths to video clip files
            voiceover_path: Path to voiceover audio file
            output_folder: Directory to save output
            title: Title for intro card
            add_intro: Whether to add title intro
            add_outro: Whether to add outro card
            apply_dna_mod: Apply DNA modification for copyright avoidance

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
                "Follow for more!",
                output_folder,
                "outro",
                duration=2.0
            )
            clips_to_concat.append(outro_path)

        # Step 2: Concatenate all clips
        concat_path = self._concatenate_clips(clips_to_concat, output_folder)

        # Step 3: Add voiceover
        with_audio_path = os.path.join(output_folder, "with_audio.mp4")
        self._add_audio(concat_path, voiceover_path, with_audio_path)

        # Step 4: Apply DNA modification for copyright avoidance
        if apply_dna_mod:
            output_path = os.path.join(output_folder, "final_recap.mp4")
            self._apply_final_dna_modification(with_audio_path, output_path)
        else:
            output_path = with_audio_path

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
        """Create a 9:16 title card video clip with styled text"""
        output_path = os.path.join(output_folder, f"{name}.mp4")

        # Escape special characters for FFmpeg
        escaped_text = text.replace("'", "'\\''").replace(":", "\\:")

        # Create gradient background with animated text
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f'color=c={bg_color}:s={self.output_width}x{self.output_height}:d={duration}:r={self.output_fps}',
            '-vf', (
                f"drawtext=text='{escaped_text}':"
                f"fontsize=60:fontcolor={text_color}:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:"
                f"font=Arial:borderw=3:bordercolor=black"
            ),
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError:
            # Fallback without text if font fails
            cmd_simple = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'color=c={bg_color}:s={self.output_width}x{self.output_height}:d={duration}:r={self.output_fps}',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                output_path
            ]
            subprocess.run(cmd_simple, capture_output=True, check=True)

        return output_path

    def _concatenate_clips(self, clips: List[str], output_folder: str) -> str:
        """Concatenate multiple video clips into one 9:16 video"""
        concat_path = os.path.join(output_folder, "concat.mp4")
        list_path = os.path.join(output_folder, "concat_list.txt")

        # Create concat list file
        with open(list_path, 'w') as f:
            for clip in clips:
                escaped_path = clip.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        # Concatenate with re-encoding to ensure consistent format
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-r', str(self.output_fps),
            '-s', f'{self.output_width}x{self.output_height}',
            '-an',
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
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                output_path
            ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to add audio: {e.stderr.decode()}")

    def _apply_final_dna_modification(self, input_path: str, output_path: str):
        """
        Apply final DNA modifications to avoid copyright detection

        Techniques:
        - Slight speed change
        - Color adjustments
        - Subtle frame modifications
        - Audio pitch adjustment
        """
        # Random modifications (imperceptible but changes fingerprint)
        speed = random.uniform(0.995, 1.005)
        hue = random.uniform(-2, 2)
        saturation = random.uniform(0.98, 1.02)
        brightness = random.uniform(-0.01, 0.01)

        # Build filter chain
        vf_filters = [
            f"setpts={1/speed}*PTS",
            f"hue=h={hue}:s={saturation}",
            f"eq=brightness={brightness}",
            # Subtle unsharp mask changes pixel values
            "unsharp=3:3:0.3:3:3:0.0",
        ]

        # Random chance to flip horizontally (makes it harder to match)
        if random.random() > 0.5:
            vf_filters.append("hflip")

        vf = ",".join(vf_filters)

        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-vf', vf,
            '-af', f'atempo={speed}',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '22',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            # Fallback: just copy without DNA mod
            subprocess.run([
                'ffmpeg', '-y',
                '-i', input_path,
                '-c:v', 'copy',
                '-c:a', 'copy',
                output_path
            ], capture_output=True, check=True)

    def adjust_video_duration(
        self,
        video_path: str,
        target_duration: float,
        output_path: str
    ):
        """Adjust video duration to match target"""
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

        speed_factor = current_duration / target_duration
        pts_factor = 1 / speed_factor

        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-filter:v', f'setpts={pts_factor}*PTS',
            '-an',
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
        output_path: str,
        style: str = "viral"
    ):
        """
        Add burned-in subtitles in viral style (large, centered, with effects)
        """
        srt_path = video_path.replace('.mp4', '.srt')

        with open(srt_path, 'w') as f:
            for i, sub in enumerate(subtitles, 1):
                start = self._seconds_to_srt_time(sub['start'])
                end = self._seconds_to_srt_time(sub['end'])
                text = sub['text'].upper()  # Viral style: uppercase
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

        if style == "viral":
            # Large, bold subtitles for vertical video
            subtitle_filter = (
                f"subtitles='{srt_path}':force_style='"
                f"FontSize=24,FontName=Arial,Bold=1,"
                f"PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                f"BorderStyle=3,Outline=2,Shadow=1,"
                f"Alignment=2,MarginV=100'"
            )
        else:
            subtitle_filter = f"subtitles='{srt_path}'"

        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', subtitle_filter,
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
        """Convert seconds to SRT timestamp format"""
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

    def add_background_music(
        self,
        video_path: str,
        music_path: str,
        output_path: str,
        music_volume: float = 0.15
    ):
        """Add background music mixed with voiceover"""
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', music_path,
            '-filter_complex',
            f'[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=first',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to add background music: {e.stderr.decode()}")
