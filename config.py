"""
Configuration management for Talky bot.
Handles API keys, environment variables, and system settings.
"""
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class for all system settings."""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # OpenAI Configuration (for GPT-4 and Whisper)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")
    
    # ElevenLabs TTS Configuration
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # System Configuration
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_AUDIO_DURATION: int = int(os.getenv("MAX_AUDIO_DURATION", "60"))  # seconds
    
    # FFmpeg Configuration
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", r"C:\Users\Reetam\Downloads\ffmpeg-2025-11-02-git-f5eb11a71d-full_build\ffmpeg-2025-11-02-git-f5eb11a71d-full_build\bin\ffmpeg.exe")
    
    # Performance Settings
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    IMAGE_RECOGNITION_TIMEOUT: int = int(os.getenv("IMAGE_RECOGNITION_TIMEOUT", "300"))  # Longer timeout for local Llava (5 minutes)
    
    # External API Endpoints (mock services for demonstration)
    WEATHER_API_URL: str = os.getenv("WEATHER_API_URL", "https://api.openweathermap.org/data/2.5/weather")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    
    # Ollama/Llava Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llava:latest")
    USE_NGROK_URL: bool = os.getenv("USE_NGROK_URL", "false").lower() == "true"  # Set to "true" to use ngrok URL from API
    DEFAULT_WEATHER_LOCATION: str = os.getenv("DEFAULT_WEATHER_LOCATION", "Greater Noida, India")
    
    # Perplexity AI Search Configuration
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    PERPLEXITY_API_URL: str = os.getenv("PERPLEXITY_API_URL", "https://api.perplexity.ai/chat/completions")
    PERPLEXITY_MODEL: str = os.getenv("PERPLEXITY_MODEL", "llama-3.1-sonar-large-128k-online")
    
    # Bennett University ERP Configuration (LEGACY - for reference only)
    ERP_USER_EMAIL: str = os.getenv("ERP_USER_EMAIL", "")
    ERP_USER_PASSWORD: str = os.getenv("ERP_USER_PASSWORD", "")
    
    # Bennett University ERP Cookie Authentication (REQUIRED)
    # Get this cookie value from browser DevTools after logging in:
    # 1. Log in to https://student.bennetterp.camu.in
    # 2. Open DevTools (F12) -> Application/Storage -> Cookies
    # 3. Find 'connect.sid' cookie and copy its value
    ERP_COOKIE_SID: str = os.getenv("ERP_COOKIE_SID", "")
    
    # Email Configuration (SMTP)
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USER: str = os.getenv("EMAIL_USER", "")
    EMAIL_PASS: str = os.getenv("EMAIL_PASS", "")
    USER_EMAIL: str = os.getenv("USER_EMAIL", "")  # Default recipient email for "send to me"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present."""
        required = [
            cls.TELEGRAM_BOT_TOKEN,
            cls.OPENAI_API_KEY,
            cls.SUPABASE_URL,
            cls.SUPABASE_KEY,
        ]
        return all(required)
    
    @classmethod
    def get_missing_config(cls) -> list[str]:
        """Get list of missing required configuration keys."""
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not cls.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not cls.SUPABASE_KEY:
            missing.append("SUPABASE_KEY")
        return missing

