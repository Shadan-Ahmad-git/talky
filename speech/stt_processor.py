"""
Speech-to-Text processor using OpenAI Whisper API.
Handles voice command transcription with confidence scoring.
"""
import logging
import os
from typing import Optional, Dict, Any
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)


class STTProcessor:
    """Speech-to-Text processor using OpenAI Whisper."""
    
    def __init__(self):
        """Initialize OpenAI client for Whisper API."""
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info("STT Processor initialized with Whisper API")
    
    async def transcribe_audio(
        self, 
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text using Whisper API.
        
        Args:
            audio_path: Path to audio file (.wav, .mp3, etc.)
            language: Optional language code (e.g., 'en', 'hi')
            
        Returns:
            Dictionary with 'text' and 'confidence' keys
        """
        try:
            if not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return {
                    "text": "",
                    "confidence": 0.0,
                    "error": "File not found"
                }
            
            # Open audio file and transcribe
            # Force English language to avoid Hindi/Gujarati transcription
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=Config.WHISPER_MODEL,
                    file=audio_file,
                    language="en",  # Force English only
                    response_format="verbose_json"
                )
            
            # Extract text and confidence
            text = transcript.text
            # Whisper doesn't provide explicit confidence, estimate from model
            confidence = 0.95 if text else 0.0
            
            logger.info(f"Transcribed audio: {text[:50]}...")
            
            return {
                "text": text,
                "confidence": confidence,
                "language": getattr(transcript, 'language', language),
                "duration": getattr(transcript, 'duration', None)
            }
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def estimate_confidence(self, text: str, language: Optional[str] = None) -> float:
        """
        Estimate transcription confidence based on text quality.
        
        Args:
            text: Transcribed text
            language: Detected language
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not text or len(text.strip()) == 0:
            return 0.0
        
        # Basic heuristics for confidence estimation
        confidence = 0.9
        
        # Reduce confidence for very short transcriptions
        if len(text) < 5:
            confidence *= 0.7
        
        # Reduce confidence if contains many non-alphabetic characters
        alpha_ratio = sum(c.isalpha() for c in text) / len(text) if text else 0
        if alpha_ratio < 0.5:
            confidence *= 0.8
        
        return min(confidence, 1.0)

