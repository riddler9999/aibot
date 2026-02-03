"""
Video Downloader Service
Downloads videos from URLs and YouTube links
"""

import os
import re
import uuid
import tempfile
import subprocess
from typing import Optional, Tuple
from urllib.parse import urlparse
import requests


class VideoDownloader:
    """Download videos from various sources"""

    # Supported video extensions
    VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv', '.flv', '.m4v']

    # YouTube URL patterns
    YOUTUBE_PATTERNS = [
        r'(youtube\.com/watch\?v=)',
        r'(youtu\.be/)',
        r'(youtube\.com/embed/)',
        r'(youtube\.com/v/)',
        r'(youtube\.com/shorts/)',
    ]

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize downloader

        Args:
            output_dir: Directory to save downloaded videos
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        os.makedirs(self.output_dir, exist_ok=True)

    def download(self, url: str, filename: Optional[str] = None) -> Tuple[str, dict]:
        """
        Download video from URL or YouTube link

        Args:
            url: Video URL or YouTube link
            filename: Optional custom filename

        Returns:
            Tuple of (file_path, metadata_dict)
        """
        url = url.strip()

        if not url:
            raise ValueError("URL cannot be empty")

        # Check if it's a YouTube URL
        if self._is_youtube_url(url):
            return self._download_youtube(url, filename)
        else:
            return self._download_direct(url, filename)

    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube link"""
        for pattern in self.YOUTUBE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def _download_youtube(self, url: str, filename: Optional[str] = None) -> Tuple[str, dict]:
        """
        Download video from YouTube using yt-dlp

        Args:
            url: YouTube URL
            filename: Optional custom filename

        Returns:
            Tuple of (file_path, metadata_dict)
        """
        try:
            import yt_dlp
        except ImportError:
            raise RuntimeError("yt-dlp is not installed. Run: pip install yt-dlp")

        # Generate output filename
        if filename:
            output_name = filename
        else:
            output_name = f"youtube_{uuid.uuid4().hex[:8]}"

        output_path = os.path.join(self.output_dir, f"{output_name}.mp4")

        # yt-dlp options
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Prefer mp4
            'outtmpl': output_path,
            'noplaylist': True,  # Don't download playlists
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # Limit video length to 3 hours max
            'match_filter': yt_dlp.utils.match_filter_func("duration < 10800"),
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)

                if info is None:
                    raise ValueError("Could not extract video information")

                # Check duration (max 3 hours)
                duration = info.get('duration', 0)
                if duration > 10800:  # 3 hours
                    raise ValueError("Video is too long (max 3 hours)")

                # Download the video
                ydl.download([url])

                metadata = {
                    'title': info.get('title', 'Unknown'),
                    'duration': duration,
                    'uploader': info.get('uploader', 'Unknown'),
                    'description': info.get('description', '')[:500],
                    'source': 'youtube',
                    'original_url': url
                }

                return output_path, metadata

        except yt_dlp.utils.DownloadError as e:
            raise RuntimeError(f"Failed to download YouTube video: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"YouTube download error: {str(e)}")

    def _download_direct(self, url: str, filename: Optional[str] = None) -> Tuple[str, dict]:
        """
        Download video from direct URL

        Args:
            url: Direct video URL
            filename: Optional custom filename

        Returns:
            Tuple of (file_path, metadata_dict)
        """
        # Parse URL to get extension
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Detect extension
        ext = '.mp4'  # Default
        for video_ext in self.VIDEO_EXTENSIONS:
            if path.endswith(video_ext):
                ext = video_ext
                break

        # Generate filename
        if filename:
            output_name = filename
        else:
            output_name = f"video_{uuid.uuid4().hex[:8]}"

        output_path = os.path.join(self.output_dir, f"{output_name}{ext}")

        try:
            # Download with streaming
            response = requests.get(
                url,
                stream=True,
                timeout=60,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('content-type', '')
            if not ('video' in content_type or 'octet-stream' in content_type):
                # Try yt-dlp as fallback for other video sites
                return self._download_with_ytdlp(url, filename)

            # Check file size (max 2GB)
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 2 * 1024 * 1024 * 1024:
                raise ValueError("File too large (max 2GB)")

            # Download file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Get metadata using ffprobe
            metadata = self._get_video_metadata(output_path)
            metadata['source'] = 'direct_url'
            metadata['original_url'] = url

            return output_path, metadata

        except requests.exceptions.RequestException as e:
            # Try yt-dlp as fallback
            try:
                return self._download_with_ytdlp(url, filename)
            except:
                raise RuntimeError(f"Failed to download video: {str(e)}")

    def _download_with_ytdlp(self, url: str, filename: Optional[str] = None) -> Tuple[str, dict]:
        """
        Fallback: Download from any site using yt-dlp

        yt-dlp supports many video sites besides YouTube
        """
        try:
            import yt_dlp
        except ImportError:
            raise RuntimeError("yt-dlp is not installed")

        if filename:
            output_name = filename
        else:
            output_name = f"video_{uuid.uuid4().hex[:8]}"

        output_path = os.path.join(self.output_dir, f"{output_name}.mp4")

        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                metadata = {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'source': info.get('extractor', 'unknown'),
                    'original_url': url
                }

                return output_path, metadata

        except Exception as e:
            raise RuntimeError(f"Failed to download video: {str(e)}")

    def _get_video_metadata(self, video_path: str) -> dict:
        """Get video metadata using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)

                format_info = data.get('format', {})
                duration = float(format_info.get('duration', 0))

                # Get video stream info
                video_stream = None
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                        break

                return {
                    'title': os.path.basename(video_path),
                    'duration': duration,
                    'width': video_stream.get('width') if video_stream else None,
                    'height': video_stream.get('height') if video_stream else None,
                }

        except Exception:
            pass

        return {
            'title': os.path.basename(video_path),
            'duration': 0
        }

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False


def download_video(url: str, output_dir: Optional[str] = None) -> Tuple[str, dict]:
    """
    Convenience function to download a video

    Args:
        url: Video URL (direct link or YouTube)
        output_dir: Optional output directory

    Returns:
        Tuple of (file_path, metadata)
    """
    downloader = VideoDownloader(output_dir)
    return downloader.download(url)
