"""
Audio format conversion utilities.
Handles conversion between Telegram .oga format and .wav format.
"""
import os
import logging
import tempfile
import subprocess
import json
from pathlib import Path
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)


def convert_oga_to_wav(oga_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Convert Telegram .oga audio file to .wav format.
    
    Args:
        oga_path: Path to input .oga file
        output_path: Optional output path. If None, creates temp file.
        
    Returns:
        Path to converted .wav file or None if conversion fails
    """
    try:
        if not os.path.exists(oga_path):
            logger.error(f"Input file not found: {oga_path}")
            return None
        
        if output_path is None:
            # Create temporary output file
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(
                temp_dir, 
                f"talky_{os.path.basename(oga_path)}.wav"
            )
        
        # Convert using ffmpeg
        # Check if ffmpeg executable exists at configured path
        ffmpeg_path = Config.FFMPEG_PATH
        if not os.path.exists(ffmpeg_path):
            logger.error(f"FFmpeg not found at configured path: {ffmpeg_path}")
            logger.error("Please set FFMPEG_PATH in .env file or update config.py")
            return None
        
        try:
            # Use subprocess with explicit path to ensure correct FFmpeg is used
            cmd = [
                ffmpeg_path,
                '-i', oga_path,
                '-acodec', 'pcm_s16le',
                '-ac', '1',
                '-ar', '16000',
                '-y',  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg conversion failed: {result.stderr}")
                return None
            
            if os.path.exists(output_path):
                logger.info(f"Successfully converted {oga_path} to {output_path}")
                return output_path
            else:
                logger.error("Conversion completed but output file not found")
                return None
        except Exception as e:
            logger.error(f"Error converting audio file: {e}")
            return None
    except Exception as e:
        logger.error(f"Unexpected error in convert_oga_to_wav: {e}")
        return None


def validate_audio_file(file_path: str, max_duration: int = 60) -> bool:
    """
    Validate audio file exists and duration is within limits.
    
    Args:
        file_path: Path to audio file
        max_duration: Maximum allowed duration in seconds
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return False
        
        # Check if ffmpeg exists
        ffmpeg_path = Config.FFMPEG_PATH
        if not os.path.exists(ffmpeg_path):
            logger.error(f"FFmpeg not found at: {ffmpeg_path}")
            return False
        
        # Probe audio file using configured FFmpeg path
        # Use ffprobe with explicit path
        ffprobe_path = ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
        if not os.path.exists(ffprobe_path):
            logger.error(f"FFprobe not found at: {ffprobe_path}")
            return False
        
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error(f"FFprobe failed: {result.stderr}")
            return False
        
        probe = json.loads(result.stdout)
        duration = float(probe['format']['duration'])
        
        if duration > max_duration:
            logger.warning(f"Audio file exceeds max duration: {duration}s > {max_duration}s")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating audio file: {e}")
        return False


def cleanup_temp_file(file_path: str) -> None:
    """
    Safely remove temporary audio file.
    
    Args:
        file_path: Path to file to remove
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Error cleaning up temp file {file_path}: {e}")

