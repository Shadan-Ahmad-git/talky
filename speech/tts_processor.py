"""
Text-to-Speech processor using OpenAI TTS API (with gTTS fallback).
Generates voice responses for Telegram bot.
"""
import logging
import os
import tempfile
from typing import Optional
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)

# Try to import gTTS for fallback
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not installed. Install with: pip install gtts")


class TTSProcessor:
    """Text-to-Speech processor using OpenAI TTS API with gTTS fallback."""
    
    def __init__(self):
        """Initialize TTS processor."""
        # Primary: Use OpenAI TTS (since we already have OpenAI API key)
        if Config.OPENAI_API_KEY:
            self.enabled = True
            self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
            self.use_openai = True
            logger.info("TTS Processor initialized with OpenAI TTS API")
        # Fallback: Use gTTS (completely free, no API key needed)
        elif GTTS_AVAILABLE:
            self.enabled = True
            self.use_openai = False
            logger.info("TTS Processor initialized with gTTS (free fallback)")
        else:
            logger.warning("No TTS provider available. TTS will be disabled")
            self.enabled = False
            self.use_openai = False
    
    async def generate_speech(
        self, 
        text: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate speech audio from text.
        
        Args:
            text: Text to convert to speech
            output_path: Optional output file path. If None, creates temp file.
            
        Returns:
            Path to generated audio file or None if generation fails
        """
        if not self.enabled:
            logger.warning("TTS not enabled, skipping speech generation")
            return None
        
        try:
            if output_path is None:
                # Create temporary output file
                temp_dir = tempfile.gettempdir()
                output_path = os.path.join(
                    temp_dir,
                    f"talky_tts_{hash(text) % 10000}.mp3"
                )
            
            # Try OpenAI TTS first (better quality)
            if self.use_openai:
                try:
                    response = self.openai_client.audio.speech.create(
                        model="tts-1",  # tts-1 is faster, tts-1-hd is higher quality
                        voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
                        input=text[:4000]  # Limit to 4000 characters per request
                    )
                    
                    # Save audio file
                    response.stream_to_file(output_path)
                    
                    logger.info(f"Generated speech file using OpenAI TTS: {output_path}")
                    return output_path
                    
                except Exception as e:
                    logger.warning(f"OpenAI TTS failed: {e}. Falling back to gTTS...")
                    # Fall through to gTTS
            
            # Fallback to gTTS (free, no API key needed)
            if GTTS_AVAILABLE:
                # Truncate text if too long (gTTS has limits)
                text_to_speak = text[:5000] if len(text) > 5000 else text
                
                tts = gTTS(text=text_to_speak, lang='en', slow=False)
                tts.save(output_path)
                
                logger.info(f"Generated speech file using gTTS: {output_path}")
                return output_path
            else:
                logger.error("gTTS not available as fallback")
                return None
                
        except Exception as e:
            logger.error(f"Error generating speech: {e}", exc_info=True)
            return None
    
    def is_enabled(self) -> bool:
        """Check if TTS is enabled."""
        return self.enabled

