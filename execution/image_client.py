"""
Image recognition client using Ollama Llava (local or remote via Flask/ngrok).
"""
import logging
import requests
import base64
import os
import re
from typing import Dict, Any, Optional
from config import Config

logger = logging.getLogger(__name__)


class ImageRecognitionClient:
    """Client for image recognition using Ollama Llava (local or remote)."""
    
    def __init__(self):
        """Initialize image recognition client."""
        self.base_url = Config.OLLAMA_BASE_URL
        self.model = Config.OLLAMA_MODEL
        self.use_ngrok_url = Config.USE_NGROK_URL  # Check env var to decide if we should use ngrok
        self.remote_url = ""  # Store ngrok URL in memory only (from npoint.io API)
        self.use_remote = False
        
        # Only load ngrok URL if USE_NGROK_URL is enabled
        if self.use_ngrok_url:
            # Initial load - read from npoint.io API
            self._load_ngrok_url(force_log=True)
        else:
            logger.info("USE_NGROK_URL is false, using local Ollama server only")
    
    def _load_ngrok_url(self, force_log: bool = False):
        """Load ngrok URL from npoint.io API. If not found, use local Ollama. Stores in memory only."""
        # Only proceed if USE_NGROK_URL is enabled
        if not self.use_ngrok_url:
            self.use_remote = False
            return
        
        old_url = self.remote_url  # Track if URL changed
        old_use_remote = self.use_remote
        self.remote_url = ""
        
        # Priority 1: Get from npoint.io API
        api_url = self._get_ngrok_url_from_api()
        if api_url:
            self.remote_url = api_url
            if force_log or (old_url and old_url != self.remote_url):
                logger.info(f"Loaded ngrok URL from npoint.io API: {self.remote_url}")
                if old_url and old_url != self.remote_url:
                    logger.info(f"URL updated from {old_url} to {self.remote_url}")
        
        # Priority 2: If no API URL found, use local Ollama
        if not self.remote_url:
            if force_log or old_use_remote:
                logger.info("No ngrok URL found in API, using local Ollama server")
        
        # Update use_remote flag
        if self.remote_url:
            self.use_remote = True
        else:
            self.use_remote = False
    
    def _get_ngrok_url_from_api(self) -> Optional[str]:
        """Get ngrok URL from npoint.io API. Handles empty JSON gracefully."""
        try:
            # npoint.io API endpoint (same as Flask server uses)
            api_url = "https://api.npoint.io/bc5f0114df0586ffd535"
            
            logger.info(f"Fetching ngrok URL from npoint.io API...")
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Handle empty JSON or invalid data
                    if not data or not isinstance(data, dict):
                        logger.warning("⚠️ API returned empty or invalid JSON, waiting for Flask server to update")
                        return None
                    
                    ngrok_url = data.get("ngrok_url", "").strip()
                    
                    if ngrok_url:
                        logger.info(f"Got ngrok URL from API: {ngrok_url}")
                        return ngrok_url
                    else:
                        logger.warning("API response doesn't contain ngrok_url field")
                        logger.debug(f"API response: {data}")
                except ValueError as e:
                    # JSON decode error - empty or invalid JSON
                    logger.warning(f"API returned invalid JSON (might be empty): {e}")
                    logger.info("Waiting for Flask server to initialize and update the API")
                    return None
            else:
                logger.warning(f"Could not fetch ngrok URL from API: {response.status_code} - {response.text[:200]}")
                
        except Exception as e:
            logger.warning(f"Error getting ngrok URL from API: {e}", exc_info=True)
        
        return None
    
    def _check_and_reload_url(self):
        """Check API for updated ngrok URL and reload if needed."""
        self._load_ngrok_url()
    
    async def recognize_image(
        self,
        image_path: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recognize and describe an image using Ollama Llava (local or remote).
        
        Args:
            image_path: Path to the image file
            prompt: Optional custom prompt for image analysis
            
        Returns:
            Recognition result dictionary
        """
        try:
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}"
                }
            
            # Read image and convert to base64
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Default prompt if not provided
            if not prompt:
                prompt = "Describe this image in detail. What do you see? Be specific and mention any important details, objects, people, text, or scenes."
            
            import asyncio
            
            # Always check for updated ngrok URL before making request
            self._check_and_reload_url()
            
            if self.use_remote:
                # Use remote Flask/ngrok server
                logger.info(f"Analyzing image with remote Llava server: {image_path}")
                try:
                    result = await self._call_remote_server(image_base64, prompt)
                except Exception as e:
                    # If remote server fails, fallback to local Ollama
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ["connection", "timeout", "404", "503", "expired", "unreachable", "refused", "network error"]):
                        logger.warning(f"Remote server error detected: {error_str[:100]}")
                        logger.info("Falling back to local Ollama server...")
                        # Clear remote URL and use local
                        self.remote_url = ""
                        self.use_remote = False
                        # Retry with local Ollama
                        result = await self._call_local_ollama(image_base64, prompt)
                    else:
                        # Some other error, re-raise
                        raise
            else:
                # Use local Ollama server
                logger.info(f"Analyzing image with local Ollama Llava: {image_path}")
                result = await self._call_local_ollama(image_base64, prompt)
            
            if not result:
                return {
                    "success": False,
                    "error": "No response from image recognition server"
                }
            
            # Extract description from result
            if isinstance(result, dict):
                description = result.get("description", result.get("content", result.get("response", ""))).strip()
            else:
                description = str(result).strip()
            
            if not description:
                return {
                    "success": False,
                    "error": "No description generated"
                }
            
            logger.info(f"Image recognition successful: {len(description)} characters")
            
            return {
                "success": True,
                "description": description,
                "model": self.model,
                "result": description
            }
            
        except requests.exceptions.Timeout:
            server_type = "remote server" if self.use_remote else "Ollama"
            logger.error(f"Network error: {server_type} timed out (timeout={Config.IMAGE_RECOGNITION_TIMEOUT})")
            return {
                "success": False,
                "error": f"Network error: {server_type} timed out. Please try again or check server status."
            }
        except requests.exceptions.ConnectionError as e:
            server_type = "remote server" if self.use_remote else "Ollama"
            server_url = self.remote_url if self.use_remote else self.base_url
            logger.error(f"Network error connecting to {server_type}: {e}")
            return {
                "success": False,
                "error": f"Network error: Could not connect to {server_type} at {server_url}. Is the server running?"
            }
        except Exception as e:
            # Don't show full traceback for expected errors (already logged above)
            error_msg = str(e)
            if "Remote server error" in error_msg or "Network error" in error_msg:
                logger.error(f"Error recognizing image: {error_msg}")
            else:
                logger.error(f"Error recognizing image: {e}", exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def _call_remote_server(self, image_base64: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Call remote Flask/ngrok server for image recognition."""
        def _http_request():
            """Synchronous HTTP request to remote server."""
            payload = {
                "image": image_base64,
                "prompt": prompt,
                "model": self.model
            }
            
            # Ensure URL doesn't have trailing slash and add endpoint
            base_url = self.remote_url.rstrip('/')
            api_url = f"{base_url}/analyze"  # Flask endpoint
            
            logger.info(f"Calling remote server: {api_url}")
            
            # Add headers to bypass ngrok free tier browser warning
            headers = {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"  # Skip ngrok free tier browser warning
            }
            
            response = requests.post(
                api_url,
                json=payload,
                timeout=Config.IMAGE_RECOGNITION_TIMEOUT,
                headers=headers
            )
            
            logger.info(f"Remote server response: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text[:500]
                logger.error(f"Remote server error {response.status_code}: {error_text}")
                # Check if it's ngrok browser warning page
                if "ngrok" in error_text.lower() and "browser" in error_text.lower():
                    raise Exception(f"Ngrok browser warning detected. Add 'ngrok-skip-browser-warning: true' header. Status: {response.status_code}")
                raise Exception(f"Remote server error: {response.status_code} - {error_text}")
        
        import asyncio
        try:
            return await asyncio.to_thread(_http_request)
        except Exception as e:
            # Log error but don't show full traceback for expected remote server errors
            error_msg = str(e)
            if "Remote server error" in error_msg:
                logger.error(f"Error calling remote Llava server: {error_msg}")
            else:
                logger.error(f"Error calling remote Llava server: {e}", exc_info=True)
            raise
    
    async def _call_local_ollama(self, image_base64: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Call local Ollama server for image recognition."""
        def _call_ollama():
            """Synchronous Ollama API call."""
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_base64]
                    }
                ],
                "stream": False
            }
            
            api_url = f"{self.base_url}/api/chat"
            
            response = requests.post(
                api_url,
                json=payload,
                timeout=Config.IMAGE_RECOGNITION_TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text[:500]}")
        
        import asyncio
        try:
            return await asyncio.to_thread(_call_ollama)
        except Exception as e:
            logger.error(f"Error calling local Ollama: {e}")
            raise

