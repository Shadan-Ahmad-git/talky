"""
External API clients for service integrations.
Mock implementations for demonstration purposes.
"""
import logging
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional
from config import Config
from openai import OpenAI

logger = logging.getLogger(__name__)

# Try to import Perplexity SDK, fallback to direct HTTP if not available
try:
    from perplexity import Perplexity
    PERPLEXITY_SDK_AVAILABLE = True
except ImportError:
    PERPLEXITY_SDK_AVAILABLE = False
    logger.warning("Perplexity SDK not installed. Install with: pip install perplexity")


class WeatherAPIClient:
    """Client for weather service API."""
    
    def __init__(self):
        """Initialize weather API client."""
        self.base_url = Config.WEATHER_API_URL
        self.api_key = Config.WEATHER_API_KEY
    
    async def get_weather(self, location: str) -> Dict[str, Any]:
        """
        Get weather information for a location.
        
        Args:
            location: Location name or coordinates
            
        Returns:
            Weather data dictionary
        """
        try:
            if not self.api_key:
                # Fallback to mock only if API key is missing
                logger.warning(f"Weather API key not configured, using mock response for {location}")
                temp = 28
                desc = "Sunny"
                return {
                    "location": location,
                    "temperature": temp,
                    "description": desc,
                    "humidity": 65,
                    "wind_speed": 12,
                    "success": True,
                    "result": f"{location}: {temp}°C, {desc}",
                    "note": "Mock data - API key not configured"
                }
            
            # Real API call using OpenWeatherMap
            logger.info(f"Fetching weather from API for: {location}")
            params = {
                "q": location,
                "appid": self.api_key,
                "units": "metric"
            }
            response = requests.get(
                self.base_url,
                params=params,
                timeout=Config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                temp = data.get("main", {}).get("temp")
                desc = data.get("weather", [{}])[0].get("description", "")
                humidity = data.get("main", {}).get("humidity")
                wind_speed = data.get("wind", {}).get("speed")
                
                logger.info(f"Weather API success for {location}: {temp}°C, {desc}")
                return {
                    "location": location,
                    "temperature": temp,
                    "description": desc,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "success": True,
                    "result": f"{location}: {temp}°C, {desc}"
                }
            else:
                logger.error(f"Weather API error: {response.status_code} - {response.text}")
                return {
                    "location": location,
                    "success": False,
                    "error": f"Weather API error: {response.status_code}"
                }
            
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return {
                "location": location,
                "success": False,
                "error": str(e)
            }


class EmailAPIClient:
    """Client for email service API using SMTP."""
    
    def __init__(self):
        """Initialize email client with SMTP configuration."""
        self.host = Config.EMAIL_HOST
        self.port = Config.EMAIL_PORT
        self.user = Config.EMAIL_USER
        self.password = Config.EMAIL_PASS
    
    async def send_email(
        self,
        recipient: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """
        Send an email using SMTP.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            body: Email body
            
        Returns:
            Result dictionary
        """
        try:
            if not self.user or not self.password:
                logger.warning("Email credentials not configured, using mock implementation")
                logger.info(f"Mock email sent to {recipient}: {subject}")
                return {
                    "recipient": recipient,
                    "subject": subject,
                    "success": True,
                    "message_id": f"mock_{hash(recipient + subject) % 10000}",
                    "note": "Email credentials not configured"
                }
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email using SMTP
            logger.info(f"Sending email to {recipient} via SMTP ({self.host}:{self.port})")
            
            # Use asyncio.to_thread to run synchronous SMTP operations
            import asyncio
            
            def _send_smtp():
                """Synchronous SMTP send function."""
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()  # Enable TLS encryption
                server.login(self.user, self.password)
                text = msg.as_string()
                server.sendmail(self.user, recipient, text)
                server.quit()
                return True
            
            # Run SMTP send in thread pool
            await asyncio.to_thread(_send_smtp)
            
            logger.info(f"Email successfully sent to {recipient}")
            return {
                "recipient": recipient,
                "subject": subject,
                "success": True,
                "message_id": f"email_{hash(recipient + subject) % 10000}"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipient refused: {e}")
            return {
                "success": False,
                "error": f"Recipient refused: {str(e)}"
            }
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected: {e}")
            return {
                "success": False,
                "error": f"Server disconnected: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_email_with_pdf(
        self,
        recipient: str,
        subject: str,
        body: str,
        pdf_buffer: bytes,
        filename: str = "report.pdf"
    ) -> Dict[str, Any]:
        """
        Send an email with PDF attachment using SMTP.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            body: Email body
            pdf_buffer: PDF file as bytes
            filename: Name for the PDF attachment
            
        Returns:
            Result dictionary
        """
        try:
            if not self.user or not self.password:
                logger.warning("Email credentials not configured")
                return {
                    "success": False,
                    "error": "Email credentials not configured"
                }
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            pdf_attachment = MIMEBase('application', 'octet-stream')
            pdf_attachment.set_payload(pdf_buffer)
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(pdf_attachment)
            
            # Send email using SMTP
            logger.info(f"Sending email with PDF attachment to {recipient} via SMTP ({self.host}:{self.port})")
            
            # Use asyncio.to_thread to run synchronous SMTP operations
            import asyncio
            
            def _send_smtp():
                """Synchronous SMTP send function."""
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()  # Enable TLS encryption
                server.login(self.user, self.password)
                text = msg.as_string()
                server.sendmail(self.user, recipient, text)
                server.quit()
                return True
            
            # Run SMTP send in thread pool
            await asyncio.to_thread(_send_smtp)
            
            logger.info(f"Email with PDF successfully sent to {recipient}")
            return {
                "recipient": recipient,
                "subject": subject,
                "success": True,
                "message_id": f"email_pdf_{hash(recipient + subject) % 10000}"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipient refused: {e}")
            return {
                "success": False,
                "error": f"Recipient refused: {str(e)}"
            }
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected: {e}")
            return {
                "success": False,
                "error": f"Server disconnected: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error sending email with PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


class HotelAPIClient:
    """Client for hotel booking API."""
    
    async def book_hotel(
        self,
        location: str,
        check_in: str,
        check_out: str,
        guests: int = 1
    ) -> Dict[str, Any]:
        """
        Book a hotel room.
        
        Args:
            location: Hotel location
            check_in: Check-in date
            check_out: Check-out date
            guests: Number of guests
            
        Returns:
            Booking result dictionary
        """
        try:
            # Mock implementation
            logger.info(f"Mock hotel booking: {location} from {check_in} to {check_out}")
            return {
                "location": location,
                "check_in": check_in,
                "check_out": check_out,
                "guests": guests,
                "success": True,
                "booking_id": f"HTL_{hash(location + check_in) % 100000}"
            }
        except Exception as e:
            logger.error(f"Error booking hotel: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_email_with_pdf(
        self,
        recipient: str,
        subject: str,
        body: str,
        pdf_buffer: bytes,
        filename: str = "report.pdf"
    ) -> Dict[str, Any]:
        """
        Send an email with PDF attachment using SMTP.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            body: Email body
            pdf_buffer: PDF file as bytes
            filename: Name for the PDF attachment
            
        Returns:
            Result dictionary
        """
        try:
            if not self.user or not self.password:
                logger.warning("Email credentials not configured")
                return {
                    "success": False,
                    "error": "Email credentials not configured"
                }
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            pdf_attachment = MIMEBase('application', 'octet-stream')
            pdf_attachment.set_payload(pdf_buffer)
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(pdf_attachment)
            
            # Send email using SMTP
            logger.info(f"Sending email with PDF attachment to {recipient} via SMTP ({self.host}:{self.port})")
            
            # Use asyncio.to_thread to run synchronous SMTP operations
            import asyncio
            
            def _send_smtp():
                """Synchronous SMTP send function."""
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()  # Enable TLS encryption
                server.login(self.user, self.password)
                text = msg.as_string()
                server.sendmail(self.user, recipient, text)
                server.quit()
                return True
            
            # Run SMTP send in thread pool
            await asyncio.to_thread(_send_smtp)
            
            logger.info(f"Email with PDF successfully sent to {recipient}")
            return {
                "recipient": recipient,
                "subject": subject,
                "success": True,
                "message_id": f"email_pdf_{hash(recipient + subject) % 10000}"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipient refused: {e}")
            return {
                "success": False,
                "error": f"Recipient refused: {str(e)}"
            }
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected: {e}")
            return {
                "success": False,
                "error": f"Server disconnected: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error sending email with PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


class FlightAPIClient:
    """Client for flight search API."""
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        date: str
    ) -> Dict[str, Any]:
        """
        Search for flights.
        
        Args:
            origin: Origin airport/city
            destination: Destination airport/city
            date: Travel date
            
        Returns:
            Flight search results
        """
        try:
            # Mock implementation
            logger.info(f"Mock flight search: {origin} to {destination} on {date}")
            return {
                "origin": origin,
                "destination": destination,
                "date": date,
                "flights": [
                    {
                        "flight_number": "FL123",
                        "departure_time": "10:00",
                        "arrival_time": "12:30",
                        "price": 350,
                        "airline": "Mock Airlines"
                    }
                ],
                "success": True
            }
        except Exception as e:
            logger.error(f"Error searching flights: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_email_with_pdf(
        self,
        recipient: str,
        subject: str,
        body: str,
        pdf_buffer: bytes,
        filename: str = "report.pdf"
    ) -> Dict[str, Any]:
        """
        Send an email with PDF attachment using SMTP.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            body: Email body
            pdf_buffer: PDF file as bytes
            filename: Name for the PDF attachment
            
        Returns:
            Result dictionary
        """
        try:
            if not self.user or not self.password:
                logger.warning("Email credentials not configured")
                return {
                    "success": False,
                    "error": "Email credentials not configured"
                }
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            pdf_attachment = MIMEBase('application', 'octet-stream')
            pdf_attachment.set_payload(pdf_buffer)
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(pdf_attachment)
            
            # Send email using SMTP
            logger.info(f"Sending email with PDF attachment to {recipient} via SMTP ({self.host}:{self.port})")
            
            # Use asyncio.to_thread to run synchronous SMTP operations
            import asyncio
            
            def _send_smtp():
                """Synchronous SMTP send function."""
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()  # Enable TLS encryption
                server.login(self.user, self.password)
                text = msg.as_string()
                server.sendmail(self.user, recipient, text)
                server.quit()
                return True
            
            # Run SMTP send in thread pool
            await asyncio.to_thread(_send_smtp)
            
            logger.info(f"Email with PDF successfully sent to {recipient}")
            return {
                "recipient": recipient,
                "subject": subject,
                "success": True,
                "message_id": f"email_pdf_{hash(recipient + subject) % 10000}"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipient refused: {e}")
            return {
                "success": False,
                "error": f"Recipient refused: {str(e)}"
            }
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected: {e}")
            return {
                "success": False,
                "error": f"Server disconnected: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error sending email with PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


class ReminderAPIClient:
    """Client for reminder service API."""
    
    async def set_reminder(
        self,
        datetime: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Set a reminder.
        
        Args:
            datetime: Reminder date/time
            message: Reminder message
            
        Returns:
            Reminder result dictionary
        """
        try:
            # Mock implementation
            logger.info(f"Mock reminder set: {message} at {datetime}")
            return {
                "datetime": datetime,
                "message": message,
                "success": True,
                "reminder_id": f"REM_{hash(datetime + message) % 10000}"
            }
        except Exception as e:
            logger.error(f"Error setting reminder: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_email_with_pdf(
        self,
        recipient: str,
        subject: str,
        body: str,
        pdf_buffer: bytes,
        filename: str = "report.pdf"
    ) -> Dict[str, Any]:
        """
        Send an email with PDF attachment using SMTP.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            body: Email body
            pdf_buffer: PDF file as bytes
            filename: Name for the PDF attachment
            
        Returns:
            Result dictionary
        """
        try:
            if not self.user or not self.password:
                logger.warning("Email credentials not configured")
                return {
                    "success": False,
                    "error": "Email credentials not configured"
                }
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            pdf_attachment = MIMEBase('application', 'octet-stream')
            pdf_attachment.set_payload(pdf_buffer)
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(pdf_attachment)
            
            # Send email using SMTP
            logger.info(f"Sending email with PDF attachment to {recipient} via SMTP ({self.host}:{self.port})")
            
            # Use asyncio.to_thread to run synchronous SMTP operations
            import asyncio
            
            def _send_smtp():
                """Synchronous SMTP send function."""
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()  # Enable TLS encryption
                server.login(self.user, self.password)
                text = msg.as_string()
                server.sendmail(self.user, recipient, text)
                server.quit()
                return True
            
            # Run SMTP send in thread pool
            await asyncio.to_thread(_send_smtp)
            
            logger.info(f"Email with PDF successfully sent to {recipient}")
            return {
                "recipient": recipient,
                "subject": subject,
                "success": True,
                "message_id": f"email_pdf_{hash(recipient + subject) % 10000}"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipient refused: {e}")
            return {
                "success": False,
                "error": f"Recipient refused: {str(e)}"
            }
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected: {e}")
            return {
                "success": False,
                "error": f"Server disconnected: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error sending email with PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


class CalendarAPIClient:
    """Client for calendar service API."""
    
    async def create_event(
        self,
        title: str,
        datetime: str,
        duration: int = 60
    ) -> Dict[str, Any]:
        """
        Create a calendar event.
        
        Args:
            title: Event title
            datetime: Event date/time
            duration: Duration in minutes
            
        Returns:
            Event creation result
        """
        try:
            # Mock implementation
            logger.info(f"Mock calendar event created: {title} at {datetime}")
            return {
                "title": title,
                "datetime": datetime,
                "duration": duration,
                "success": True,
                "event_id": f"EVT_{hash(title + datetime) % 10000}"
            }
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_email_with_pdf(
        self,
        recipient: str,
        subject: str,
        body: str,
        pdf_buffer: bytes,
        filename: str = "report.pdf"
    ) -> Dict[str, Any]:
        """
        Send an email with PDF attachment using SMTP.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            body: Email body
            pdf_buffer: PDF file as bytes
            filename: Name for the PDF attachment
            
        Returns:
            Result dictionary
        """
        try:
            if not self.user or not self.password:
                logger.warning("Email credentials not configured")
                return {
                    "success": False,
                    "error": "Email credentials not configured"
                }
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            pdf_attachment = MIMEBase('application', 'octet-stream')
            pdf_attachment.set_payload(pdf_buffer)
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(pdf_attachment)
            
            # Send email using SMTP
            logger.info(f"Sending email with PDF attachment to {recipient} via SMTP ({self.host}:{self.port})")
            
            # Use asyncio.to_thread to run synchronous SMTP operations
            import asyncio
            
            def _send_smtp():
                """Synchronous SMTP send function."""
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()  # Enable TLS encryption
                server.login(self.user, self.password)
                text = msg.as_string()
                server.sendmail(self.user, recipient, text)
                server.quit()
                return True
            
            # Run SMTP send in thread pool
            await asyncio.to_thread(_send_smtp)
            
            logger.info(f"Email with PDF successfully sent to {recipient}")
            return {
                "recipient": recipient,
                "subject": subject,
                "success": True,
                "message_id": f"email_pdf_{hash(recipient + subject) % 10000}"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipient refused: {e}")
            return {
                "success": False,
                "error": f"Recipient refused: {str(e)}"
            }
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected: {e}")
            return {
                "success": False,
                "error": f"Server disconnected: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error sending email with PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


class PerplexitySearchClient:
    """Client for Perplexity AI search API."""
    
    def __init__(self):
        """Initialize Perplexity search client."""
        # Hardcoded API key (same as user's working code)
        self.api_key = "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"
        self.api_url = Config.PERPLEXITY_API_URL
        self.model = Config.PERPLEXITY_MODEL
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None
        
        # Use official SDK if available, otherwise fallback to HTTP
        if PERPLEXITY_SDK_AVAILABLE and self.api_key:
            try:
                self.perplexity_client = Perplexity(api_key=self.api_key)
                self.use_sdk = True
                logger.info("Perplexity SDK client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Perplexity SDK: {e}. Falling back to HTTP requests.")
                self.use_sdk = False
                self.perplexity_client = None
        else:
            self.use_sdk = False
            self.perplexity_client = None
        
        # Log configuration status (without exposing key)
        if self.api_key:
            logger.info(f"Perplexity client initialized. Using SDK: {self.use_sdk}, Model: {self.model}")
            logger.debug(f"API key present: {bool(self.api_key)}, length: {len(self.api_key) if self.api_key else 0}")
        else:
            logger.warning("Perplexity API key not configured. Internet search will not work.")
    
    async def search_and_format(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        Search the internet using Perplexity and format response with OpenAI.
        
        Args:
            query: Search query from user
            
        Returns:
            Formatted search result dictionary
        """
        try:
            if not self.api_key or not self.api_key.strip():
                logger.error("Perplexity API key is missing or empty")
                return {
                    "success": False,
                    "error": "Perplexity API key not configured. Please set PERPLEXITY_API_KEY in your .env file."
                }
            
            logger.info(f"Searching Perplexity for: {query}")
            
            # Step 1: Search using Perplexity API (SDK or HTTP)
            if self.use_sdk and self.perplexity_client:
                # Use official SDK - search.create() method (same as user's working code)
                try:
                    import asyncio
                    
                    def _sdk_search():
                        """Synchronous SDK call wrapped for async."""
                        # Use search.create() API via SDK (matches user's working code)
                        search_response = self.perplexity_client.search.create(
                            query=query,
                            max_results=5,
                            max_tokens_per_page=1024
                        )
                        return search_response
                    
                    search_response = await asyncio.to_thread(_sdk_search)
                    
                    # Format search results into readable text (include all available data for comprehensive summarization)
                    if hasattr(search_response, 'results') and search_response.results:
                        result_parts = []
                        for i, result in enumerate(search_response.results, 1):
                            result_text = f"{i}. {result.title}\n   URL: {result.url}"
                            if hasattr(result, 'snippet') and result.snippet:
                                # Include full snippet - OpenAI will summarize it
                                result_text += f"\n   {result.snippet}"
                            if hasattr(result, 'date') and result.date:
                                result_text += f"\n   Date: {result.date}"
                            # Include any additional content if available
                            if hasattr(result, 'content') and result.content:
                                result_text += f"\n   Content: {result.content[:500]}"  # First 500 chars of content
                            result_parts.append(result_text)
                        search_result = "\n\n".join(result_parts)
                    else:
                        search_result = "No search results found."
                    
                except Exception as e:
                    logger.error(f"Perplexity SDK error: {e}")
                    # Fallback to HTTP method
                    search_result = await self._search_via_http(query)
            else:
                # Use HTTP requests (fallback)
                search_result = await self._search_via_http(query)
            
            if not search_result:
                return {
                    "success": False,
                    "error": "No search results returned"
                }
            
            # Step 2: Format response using OpenAI for smooth, detailed, to-the-point answers
            if self.openai_client:
                try:
                    logger.info(f"Formatting search results with OpenAI for query: {query}")
                    logger.debug(f"Search result length: {len(search_result)} characters, {len(search_result.split())} words")
                    
                    system_prompt = (
                        "You are a helpful assistant that summarizes search results "
                        "into clear, concise, and natural responses. "
                        "CRITICAL REQUIREMENTS:\n"
                        "- Your response MUST be UNDER 500 words - this is a hard limit\n"
                        "- Count your words carefully - aim for 300-400 words maximum\n"
                        "- DO NOT copy-paste text from search results - SUMMARIZE everything\n"
                        "- Extract ONLY the most important and relevant information\n"
                        "- Prioritize facts that directly answer the user's question\n"
                        "- Remove all redundant information, repetitions, and fluff\n"
                        "- Use smooth, conversational language (not bullet points unless necessary)\n"
                        "- Organize information logically in paragraphs\n"
                        "- Include key facts, dates, names, but only the essential ones\n"
                        "- If search results are long, summarize only the top 3-5 most relevant facts\n"
                        "- Write concisely - every sentence must add value\n"
                        "- DO NOT exceed 500 words - stop before reaching the limit"
                    )
                    
                    user_message = (
                        f"User question: {query}\n\n"
                        f"Search results from Perplexity (comprehensive data - SUMMARIZE this, don't copy):\n{search_result}\n\n"
                        f"IMPORTANT: Summarize the search results into a concise response UNDER 500 words. "
                        f"Do NOT copy text directly - extract and summarize the key information. "
                        f"Focus on facts that directly answer: '{query}'. "
                        f"Be brief and to the point. Maximum 400 words recommended."
                    )
                    
                    logger.debug(f"System prompt length: {len(system_prompt)} chars")
                    logger.debug(f"User message length: {len(user_message)} chars")
                    
                    formatted_response = self.openai_client.chat.completions.create(
                        model=Config.OPENAI_MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": user_message
                            }
                        ],
                        temperature=0.5,  # Lower temperature for more focused summarization
                        max_tokens=350  # Further reduced to ensure under 500 words (350 tokens ≈ 260-280 words)
                    )
                    
                    formatted_text = formatted_response.choices[0].message.content.strip()
                    
                    # Validate word count and truncate if necessary (safety check)
                    word_count = len(formatted_text.split())
                    if word_count > 500:
                        logger.warning(f"Response exceeded 500 words ({word_count}), truncating...")
                        # Truncate to first 500 words
                        words = formatted_text.split()[:500]
                        formatted_text = " ".join(words) + "..."
                        logger.info(f"Truncated to {len(formatted_text.split())} words")
                    
                    return {
                        "success": True,
                        "query": query,
                        "search_result": search_result,
                        "formatted_response": formatted_text,
                        "result": formatted_text
                    }
                except Exception as e:
                    logger.warning(f"Error formatting with OpenAI, using raw result: {e}")
                    # Fallback to raw Perplexity result (truncate if too long)
                    truncated_result = search_result
                    if len(search_result.split()) > 500:
                        words = search_result.split()[:500]
                        truncated_result = " ".join(words) + "..."
                        logger.info(f"Truncated raw search result to {len(truncated_result.split())} words")
                    return {
                        "success": True,
                        "query": query,
                        "search_result": search_result,
                        "result": truncated_result
                    }
            else:
                # No OpenAI key, return raw Perplexity result (truncate if too long)
                truncated_result = search_result
                if len(search_result.split()) > 500:
                    words = search_result.split()[:500]
                    truncated_result = " ".join(words) + "..."
                    logger.info(f"Truncated raw search result to {len(truncated_result.split())} words")
                return {
                    "success": True,
                    "query": query,
                    "search_result": search_result,
                    "result": truncated_result
                }
                
        except Exception as e:
            logger.error(f"Error in Perplexity search: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _search_via_http(self, query: str) -> str:
        """
        Fallback HTTP method for Perplexity search.
        
        Args:
            query: Search query
            
        Returns:
            Search result text
        """
        try:
            api_key_clean = self.api_key.strip()
            headers = {
                "Authorization": f"Bearer {api_key_clean}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that searches the internet "
                            "and provides accurate, up-to-date information. "
                            "Return comprehensive search results with sources."
                        )
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 1000
            }
            
            logger.debug(f"Using HTTP method. API URL: {self.api_url}, Model: {self.model}")
            
            import asyncio
            def _http_request():
                return requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=Config.REQUEST_TIMEOUT
                )
            
            response = await asyncio.to_thread(_http_request)
            
            if response.status_code == 401:
                logger.error(f"Perplexity API authentication failed. Check your API key.")
                logger.debug(f"Response: {response.text[:500]}")
                raise Exception("Perplexity API authentication failed. Please check your PERPLEXITY_API_KEY in .env file.")
            elif response.status_code != 200:
                logger.error(f"Perplexity API error: {response.status_code} - {response.text[:500]}")
                raise Exception(f"Search API error: {response.status_code}. Please check your API key and endpoint configuration.")
            
            perplexity_data = response.json()
            search_result = perplexity_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return search_result
            
        except Exception as e:
            logger.error(f"HTTP search method failed: {e}")
            raise
    
    async def send_email_with_pdf(
        self,
        recipient: str,
        subject: str,
        body: str,
        pdf_buffer: bytes,
        filename: str = "report.pdf"
    ) -> Dict[str, Any]:
        """
        Send an email with PDF attachment using SMTP.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            body: Email body
            pdf_buffer: PDF file as bytes
            filename: Name for the PDF attachment
            
        Returns:
            Result dictionary
        """
        try:
            if not self.user or not self.password:
                logger.warning("Email credentials not configured")
                return {
                    "success": False,
                    "error": "Email credentials not configured"
                }
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            pdf_attachment = MIMEBase('application', 'octet-stream')
            pdf_attachment.set_payload(pdf_buffer)
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(pdf_attachment)
            
            # Send email using SMTP
            logger.info(f"Sending email with PDF attachment to {recipient} via SMTP ({self.host}:{self.port})")
            
            # Use asyncio.to_thread to run synchronous SMTP operations
            import asyncio
            
            def _send_smtp():
                """Synchronous SMTP send function."""
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()  # Enable TLS encryption
                server.login(self.user, self.password)
                text = msg.as_string()
                server.sendmail(self.user, recipient, text)
                server.quit()
                return True
            
            # Run SMTP send in thread pool
            await asyncio.to_thread(_send_smtp)
            
            logger.info(f"Email with PDF successfully sent to {recipient}")
            return {
                "recipient": recipient,
                "subject": subject,
                "success": True,
                "message_id": f"email_pdf_{hash(recipient + subject) % 10000}"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipient refused: {e}")
            return {
                "success": False,
                "error": f"Recipient refused: {str(e)}"
            }
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP server disconnected: {e}")
            return {
                "success": False,
                "error": f"Server disconnected: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error sending email with PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

