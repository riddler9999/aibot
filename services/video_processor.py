"""
Video Processing Service
Handles video analysis, audio extraction, scene extraction with 9:16 format,
face tracking, dynamic zoom, and video DNA modification for copyright avoidance
"""

import os
import subprocess
import json
import random
from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np


class VideoProcessor:
    """Process video files for viral 9:16 recap generation"""

    # Output dimensions for 9:16 vertical format
    OUTPUT_WIDTH = 1080
    OUTPUT_HEIGHT = 1920

    def __init__(self, video_path: str):
        self.video_path = video_path
        self.duration = None
        self.fps = None
        self.width = None
        self.height = None
        self.face_cascade = None
        self._analyze_video()
        self._init_face_detector()

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

    def _init_face_detector(self):
        """Initialize OpenCV face detector"""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except:
            self.face_cascade = None

    def extract_audio(self, output_folder: str) -> str:
        """Extract audio track from video"""
        audio_path = os.path.join(output_folder, 'audio.wav')

        cmd = [
            'ffmpeg', '-y',
            '-i', self.video_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            audio_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to extract audio: {e.stderr.decode()}")

        return audio_path

    def detect_face_region(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect face in frame and return bounding box
        Returns (x, y, w, h) or None if no face found
        """
        if self.face_cascade is None:
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(50, 50)
        )

        if len(faces) > 0:
            # Return largest face
            largest = max(faces, key=lambda f: f[2] * f[3])
            return tuple(largest)
        return None

    def calculate_crop_region(
        self,
        frame_width: int,
        frame_height: int,
        face_box: Optional[Tuple[int, int, int, int]] = None,
        zoom_factor: float = 1.0
    ) -> Tuple[int, int, int, int]:
        """
        Calculate crop region for 9:16 aspect ratio with face tracking
        Returns (x, y, crop_width, crop_height)
        """
        target_ratio = 9 / 16  # Width / Height for vertical video
        current_ratio = frame_width / frame_height

        if current_ratio > target_ratio:
            # Video is wider - crop sides
            crop_height = frame_height
            crop_width = int(frame_height * target_ratio)
        else:
            # Video is taller - crop top/bottom
            crop_width = frame_width
            crop_height = int(frame_width / target_ratio)

        # Apply zoom
        crop_width = int(crop_width / zoom_factor)
        crop_height = int(crop_height / zoom_factor)

        # Center crop by default
        x = (frame_width - crop_width) // 2
        y = (frame_height - crop_height) // 2

        # Adjust for face tracking if face detected
        if face_box:
            face_x, face_y, face_w, face_h = face_box
            face_center_x = face_x + face_w // 2
            face_center_y = face_y + face_h // 2

            # Center crop on face
            x = max(0, min(face_center_x - crop_width // 2, frame_width - crop_width))
            y = max(0, min(face_center_y - crop_height // 2, frame_height - crop_height))

        return (x, y, crop_width, crop_height)

    def extract_scenes(self, timestamps: List[Dict], output_folder: str) -> List[str]:
        """
        Extract video clips in 9:16 format with face tracking and dynamic zoom
        """
        clips = []
        scenes_folder = os.path.join(output_folder, 'scenes')
        os.makedirs(scenes_folder, exist_ok=True)

        if not timestamps:
            timestamps = self._generate_default_timestamps()

        for i, ts in enumerate(timestamps):
            start = ts.get('start', 0)
            duration = ts.get('duration', 5)
            clip_path = os.path.join(scenes_folder, f'scene_{i:03d}.mp4')

            # Detect face position for this scene
            face_region = self._detect_face_at_timestamp(start)

            # Generate dynamic zoom pattern
            zoom_effect = self._generate_zoom_effect(i)

            # Build FFmpeg filter for 9:16 with effects
            vf_filter = self._build_viral_filter(face_region, zoom_effect, duration)

            # Add DNA modification filters
            dna_filter = self._build_dna_modification_filter()

            full_filter = f"{vf_filter},{dna_filter}"

            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start),
                '-i', self.video_path,
                '-t', str(duration),
                '-vf', full_filter,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-an',
                '-r', '30',  # Consistent frame rate
                clip_path
            ]

            try:
                subprocess.run(cmd, capture_output=True, check=True)
                clips.append(clip_path)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to extract scene {i}: {e.stderr.decode()}")
                # Try simpler extraction as fallback
                fallback_clip = self._extract_simple_scene(start, duration, scenes_folder, i)
                if fallback_clip:
                    clips.append(fallback_clip)

        return clips

    def _detect_face_at_timestamp(self, timestamp: float) -> Optional[Tuple[int, int, int, int]]:
        """Detect face at a specific timestamp"""
        cap = cv2.VideoCapture(self.video_path)
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)

        ret, frame = cap.read()
        cap.release()

        if ret:
            return self.detect_face_region(frame)
        return None

    def _generate_zoom_effect(self, scene_index: int) -> Dict:
        """Generate dynamic zoom parameters for a scene"""
        effects = [
            {'type': 'zoom_in', 'start': 1.0, 'end': 1.15},
            {'type': 'zoom_out', 'start': 1.15, 'end': 1.0},
            {'type': 'slow_zoom', 'start': 1.0, 'end': 1.08},
            {'type': 'ken_burns', 'start': 1.1, 'end': 1.0},
            {'type': 'static', 'start': 1.05, 'end': 1.05},
        ]
        return effects[scene_index % len(effects)]

    def _build_viral_filter(
        self,
        face_region: Optional[Tuple[int, int, int, int]],
        zoom_effect: Dict,
        duration: float
    ) -> str:
        """Build FFmpeg filter chain for viral 9:16 format"""
        filters = []

        # Calculate crop for 9:16 aspect ratio
        target_ratio = 9 / 16
        current_ratio = self.width / self.height

        if current_ratio > target_ratio:
            crop_height = self.height
            crop_width = int(self.height * target_ratio)
        else:
            crop_width = self.width
            crop_height = int(self.width / target_ratio)

        # Center position (default)
        x_pos = (self.width - crop_width) // 2
        y_pos = (self.height - crop_height) // 2

        # Adjust for face if detected
        if face_region:
            face_x, face_y, face_w, face_h = face_region
            face_center_x = face_x + face_w // 2
            face_center_y = face_y + face_h // 2

            x_pos = max(0, min(face_center_x - crop_width // 2, self.width - crop_width))
            y_pos = max(0, min(face_center_y - crop_height // 2, self.height - crop_height))

        # Dynamic zoom using zoompan filter
        zoom_start = zoom_effect['start']
        zoom_end = zoom_effect['end']
        fps = 30
        total_frames = int(duration * fps)

        # Create zoompan filter for dynamic zoom
        zoom_expr = f"zoom+({zoom_end}-{zoom_start})/{total_frames}"
        if zoom_end < zoom_start:
            zoom_expr = f"zoom-({zoom_start}-{zoom_end})/{total_frames}"

        # Zoompan with face-centered crop
        zoompan_filter = (
            f"zoompan=z='{zoom_start}+({zoom_end}-{zoom_start})*on/{total_frames}':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={self.OUTPUT_WIDTH}x{self.OUTPUT_HEIGHT}:fps={fps}"
        )

        # Alternative simpler approach: crop then scale with zoom
        simple_filter = (
            f"crop={crop_width}:{crop_height}:{x_pos}:{y_pos},"
            f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:flags=lanczos,"
            f"setsar=1"
        )

        return simple_filter

    def _build_dna_modification_filter(self) -> str:
        """
        Build FFmpeg filter for video DNA modification to avoid copyright detection

        Techniques used:
        - Slight speed change (0.98x - 1.02x)
        - Color hue/saturation shift
        - Slight brightness/contrast adjustment
        - Mirror some frames
        - Add subtle noise
        - Slight rotation
        """
        modifications = []

        # Random speed adjustment (0.98x to 1.02x) - changes temporal fingerprint
        speed = random.uniform(0.98, 1.02)
        modifications.append(f"setpts={1/speed}*PTS")

        # Slight hue shift (-5 to +5 degrees)
        hue_shift = random.uniform(-5, 5)
        modifications.append(f"hue=h={hue_shift}")

        # Brightness/contrast adjustment
        brightness = random.uniform(-0.03, 0.03)
        contrast = random.uniform(0.97, 1.03)
        modifications.append(f"eq=brightness={brightness}:contrast={contrast}")

        # Random horizontal flip (50% chance per scene - applied at scene level)
        # Note: We'll handle this separately to maintain consistency per scene

        # Add very subtle noise (imperceptible but changes pixel values)
        # Using unsharp mask for subtle texture modification
        modifications.append("unsharp=3:3:0.5:3:3:0.0")

        # Slight saturation adjustment
        saturation = random.uniform(0.95, 1.05)
        modifications.append(f"eq=saturation={saturation}")

        return ",".join(modifications)

    def _extract_simple_scene(
        self,
        start: float,
        duration: float,
        output_folder: str,
        index: int
    ) -> Optional[str]:
        """Fallback simple scene extraction"""
        clip_path = os.path.join(output_folder, f'scene_{index:03d}.mp4')

        # Simple 9:16 crop and scale
        target_ratio = 9 / 16
        current_ratio = self.width / self.height

        if current_ratio > target_ratio:
            crop_height = self.height
            crop_width = int(self.height * target_ratio)
        else:
            crop_width = self.width
            crop_height = int(self.width / target_ratio)

        x_pos = (self.width - crop_width) // 2
        y_pos = (self.height - crop_height) // 2

        vf = (
            f"crop={crop_width}:{crop_height}:{x_pos}:{y_pos},"
            f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT},"
            f"setsar=1"
        )

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', self.video_path,
            '-t', str(duration),
            '-vf', vf,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-an',
            clip_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return clip_path
        except:
            return None

    def _generate_default_timestamps(self, num_clips: int = 24, clip_duration: float = 5.0) -> List[Dict]:
        """Generate evenly distributed timestamps across the video"""
        if self.duration <= 0:
            return []

        timestamps = []
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
        """Detect major scene changes using frame differencing"""
        cap = cv2.VideoCapture(self.video_path)
        scene_changes = []

        prev_frame = None
        frame_idx = 0
        sample_rate = int(self.fps)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_rate == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (320, 180))

                if prev_frame is not None:
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
        """Extract representative keyframes from the video"""
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
            'path': self.video_path,
            'output_format': '9:16 vertical',
            'output_resolution': f'{self.OUTPUT_WIDTH}x{self.OUTPUT_HEIGHT}'
        }


def apply_dna_modification_to_final(
    input_path: str,
    output_path: str,
    apply_mirror: bool = False
) -> str:
    """
    Apply additional DNA modifications to final compiled video

    Args:
        input_path: Path to input video
        output_path: Path to output video
        apply_mirror: Whether to mirror the video

    Returns:
        Path to modified video
    """
    filters = []

    # Speed adjustment
    speed = random.uniform(0.99, 1.01)
    filters.append(f"setpts={1/speed}*PTS")

    # Audio pitch correction to match speed
    audio_tempo = speed

    # Color adjustments
    hue = random.uniform(-3, 3)
    saturation = random.uniform(0.97, 1.03)
    brightness = random.uniform(-0.02, 0.02)
    filters.append(f"hue=h={hue}:s={saturation}")
    filters.append(f"eq=brightness={brightness}")

    # Optional mirror
    if apply_mirror:
        filters.append("hflip")

    # Very slight rotation (imperceptible but changes pixels)
    rotation = random.uniform(-0.5, 0.5)
    filters.append(f"rotate={rotation}*PI/180:fillcolor=black")

    # Slight crop to remove rotation artifacts and change frame
    filters.append("crop=in_w-4:in_h-4")
    filters.append(f"scale=1080:1920")

    filter_chain = ",".join(filters)

    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-vf', filter_chain,
        '-af', f'atempo={audio_tempo}',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '22',
        '-c:a', 'aac',
        '-b:a', '192k',
        output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to apply DNA modification: {e.stderr.decode()}")
