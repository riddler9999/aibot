"""
Video Processing Service
Handles video analysis, audio extraction, and scene extraction
"""

import os
import subprocess
import json
from typing import List, Dict, Tuple
import cv2
import numpy as np


class VideoProcessor:
    """Process video files for recap generation"""

    def __init__(self, video_path: str):
        self.video_path = video_path
        self.duration = None
        self.fps = None
        self.width = None
        self.height = None
        self._analyze_video()

    def _analyze_video(self):
        """Analyze video to get metadata"""
        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            raise ValueError(f"Could not open video: {self.video_path}")

        self.fps = cap.get(cv2.CAP_PROP_FPS)
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = frame_count / self.fps if self.fps > 0 else 0

        cap.release()

    def extract_audio(self, output_folder: str) -> str:
        """Extract audio track from video"""
        audio_path = os.path.join(output_folder, 'audio.wav')

        cmd = [
            'ffmpeg', '-y',
            '-i', self.video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # WAV format
            '-ar', '16000',  # 16kHz sample rate (good for Whisper)
            '-ac', '1',  # Mono
            audio_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to extract audio: {e.stderr.decode()}")

        return audio_path

    def extract_scenes(self, timestamps: List[Dict], output_folder: str) -> List[str]:
        """
        Extract video clips at specified timestamps

        Args:
            timestamps: List of dicts with 'start' and 'duration' keys (in seconds)
            output_folder: Where to save extracted clips

        Returns:
            List of paths to extracted clips
        """
        clips = []
        scenes_folder = os.path.join(output_folder, 'scenes')
        os.makedirs(scenes_folder, exist_ok=True)

        # If no timestamps provided, generate evenly spaced clips
        if not timestamps:
            timestamps = self._generate_default_timestamps()

        for i, ts in enumerate(timestamps):
            start = ts.get('start', 0)
            duration = ts.get('duration', 5)
            clip_path = os.path.join(scenes_folder, f'scene_{i:03d}.mp4')

            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start),
                '-i', self.video_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-an',  # No audio (we'll add voiceover later)
                '-vf', f'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
                clip_path
            ]

            try:
                subprocess.run(cmd, capture_output=True, check=True)
                clips.append(clip_path)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to extract scene {i}: {e.stderr.decode()}")
                continue

        return clips

    def _generate_default_timestamps(self, num_clips: int = 24, clip_duration: float = 5.0) -> List[Dict]:
        """
        Generate evenly distributed timestamps across the video

        For a 2-minute recap, we need about 24 clips of 5 seconds each
        """
        if self.duration <= 0:
            return []

        timestamps = []

        # Skip first and last 5% of the movie (usually credits)
        start_offset = self.duration * 0.05
        end_offset = self.duration * 0.95
        usable_duration = end_offset - start_offset

        interval = usable_duration / num_clips

        for i in range(num_clips):
            timestamp = start_offset + (i * interval)
            timestamps.append({
                'start': timestamp,
                'duration': clip_duration,
                'description': f'Scene {i + 1}'
            })

        return timestamps

    def detect_scene_changes(self, threshold: float = 30.0) -> List[float]:
        """
        Detect major scene changes in the video using frame differencing

        Returns list of timestamps where scene changes occur
        """
        cap = cv2.VideoCapture(self.video_path)
        scene_changes = []

        prev_frame = None
        frame_idx = 0
        sample_rate = int(self.fps)  # Check every second

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_rate == 0:
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (320, 180))  # Downscale for speed

                if prev_frame is not None:
                    # Calculate frame difference
                    diff = cv2.absdiff(gray, prev_frame)
                    mean_diff = np.mean(diff)

                    if mean_diff > threshold:
                        timestamp = frame_idx / self.fps
                        scene_changes.append(timestamp)

                prev_frame = gray

            frame_idx += 1

        cap.release()
        return scene_changes

    def extract_keyframes(self, num_frames: int = 10, output_folder: str = None) -> List[str]:
        """
        Extract representative keyframes from the video

        Useful for thumbnail generation or visual analysis
        """
        if output_folder:
            frames_folder = os.path.join(output_folder, 'keyframes')
            os.makedirs(frames_folder, exist_ok=True)

        cap = cv2.VideoCapture(self.video_path)
        frame_paths = []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = total_frames // (num_frames + 1)

        for i in range(1, num_frames + 1):
            frame_pos = i * interval
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)

            ret, frame = cap.read()
            if ret and output_folder:
                frame_path = os.path.join(frames_folder, f'keyframe_{i:03d}.jpg')
                cv2.imwrite(frame_path, frame)
                frame_paths.append(frame_path)

        cap.release()
        return frame_paths

    def get_video_info(self) -> Dict:
        """Get video metadata"""
        return {
            'duration': self.duration,
            'fps': self.fps,
            'width': self.width,
            'height': self.height,
            'path': self.video_path
        }
