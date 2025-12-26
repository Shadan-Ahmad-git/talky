"""
Main entry point for Talky Telegram bot.
Voice-driven intelligent agent with AI reasoning.
"""
import logging
import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import Config
from speech.stt_processor import STTProcessor
from speech.tts_processor import TTSProcessor
from nlp.intent_classifier import IntentClassifier, Intent
from planning.knowledge_base import KnowledgeBase
from planning.state_manager import StateManager, State
from planning.astar_planner import AStarPlanner
from execution.action_executor import ActionExecutor
from execution.image_client import ImageRecognitionClient
from explainability.explanation_engine import ExplanationEngine
from explainability.audit_logger import AuditLogger
from utils.audio_utils import convert_oga_to_wav, cleanup_temp_file
from utils.database import get_database
from openai import OpenAI
from nlp.nlp_utils import extract_entities, is_detailed_request, is_follow_up_question
from typing import Dict, Any, Optional
import json
import re
import tempfile

# Configure logging with simplified timestamp format
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',  # Simple time format: HH:MM:SS
    level=getattr(logging, Config.LOG_LEVEL.upper())
)

# Suppress verbose network library logging (httpcore, httpx, telegram internal)
# These libraries log at DEBUG level for every HTTP request/response
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.ExtBot").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Updater").setLevel(logging.WARNING)

# Keep application-level modules at configured level (INFO by default)
# This ensures we see intent classification, plan generation, OpenAI processing, etc.
logging.getLogger("main").setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
logging.getLogger("nlp.intent_classifier").setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
logging.getLogger("nlp.nlp_utils").setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
logging.getLogger("execution.action_executor").setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
logging.getLogger("execution.erp_client").setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
logging.getLogger("planning.astar_planner").setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
logging.getLogger("explainability.explanation_engine").setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
logging.getLogger("speech.stt_processor").setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
logging.getLogger("speech.tts_processor").setLevel(getattr(logging, Config.LOG_LEVEL.upper()))

logger = logging.getLogger(__name__)


class TalkyBot:
    """Main bot class for Talky."""
    
    def __init__(self):
        """Initialize Talky bot with all components."""
        # Validate configuration
        if not Config.validate():
            missing = Config.get_missing_config()
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        # Initialize components
        self.stt = STTProcessor()
        self.tts = TTSProcessor()
        self.intent_classifier = IntentClassifier()
        self.kb = KnowledgeBase()
        self.state_manager = StateManager()
        self.planner = AStarPlanner(self.kb, self.state_manager)
        self.executor = ActionExecutor()
        self.action_executor = self.executor  # Alias for compatibility
        self.explainer = ExplanationEngine()
        self.audit_logger = AuditLogger()
        self.db = get_database()
        self.image_client = ImageRecognitionClient()
        
        # In-memory context storage for conversation (entire session)
        # Format: {user_id: {"last_intent": str, "last_data": dict, "last_response": str, "last_query": str, "conversation_history": list}}
        self.conversation_context: Dict[int, Dict[str, Any]] = {}
        
        logger.info("Talky bot initialized successfully")
    
    async def handle_voice_message(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming voice messages."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        session_id = self.audit_logger.generate_session_id()
        
        try:
            # Download voice file
            voice_file = await update.message.voice.get_file()
            oga_path = f"temp_{user_id}_{datetime.now().timestamp()}.oga"
            await voice_file.download_to_drive(oga_path)
            
            # Convert to WAV
            wav_path = convert_oga_to_wav(oga_path)
            if not wav_path:
                await update.message.reply_text(
                    "Sorry, I couldn't process the audio file. Please try again."
                )
                cleanup_temp_file(oga_path)
                return
            
            # Transcribe audio
            transcription = await self.stt.transcribe_audio(wav_path)
            command_text = transcription.get("text", "")
            
            if not command_text:
                await update.message.reply_text(
                    "I couldn't understand your voice message. Please try again or use text."
                )
                cleanup_temp_file(oga_path)
                cleanup_temp_file(wav_path)
                return
            
            # Process command
            await update.message.reply_text(f"User Input: {command_text}")
            response = await self.process_user_command(
                user_id, 
                command_text, 
                session_id
            )
            
            # Send text response
            await update.message.reply_text(response)
            
            # Generate and send voice response (for all responses including Unknown intents)
            await self._send_voice_response(update, response)
            
            # Cleanup
            cleanup_temp_file(oga_path)
            cleanup_temp_file(wav_path)
            
        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
            await update.message.reply_text(
                "Sorry, I encountered an error processing your voice message."
            )
    
    async def handle_image_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming image messages with Llava."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        session_id = self.audit_logger.generate_session_id()
        
        try:
            # Get the largest photo size
            photo = update.message.photo[-1] if update.message.photo else None
            if not photo:
                await update.message.reply_text("I couldn't process the image. Please try again.")
                return
            
            # Download image
            image_file = await photo.get_file()
            image_path = f"temp_image_{user_id}_{datetime.now().timestamp()}.jpg"
            await image_file.download_to_drive(image_path)
            
            # Get caption if provided
            caption = update.message.caption or "What do you see in this image? Describe it in detail."
            
            # Process with Llava (this can take 60-120 seconds)
            await update.message.reply_text("Analyzing image with AI... This may take a minute or two.")
            recognition_result = await self.image_client.recognize_image(image_path, caption)
            
            if recognition_result.get("success"):
                description = recognition_result.get("description", "")
                
                # Send text response
                await update.message.reply_text(f"Image Analysis:\n\n{description}")
                
                # Generate and send voice response
                await self._send_voice_response(update, description)
            else:
                error_msg = recognition_result.get("error", "Unknown error")
                await update.message.reply_text(f"Sorry, I couldn't analyze the image: {error_msg}")
            
            # Cleanup
            cleanup_temp_file(image_path)
            
        except Exception as e:
            logger.error(f"Error handling image message: {e}", exc_info=True)
            await update.message.reply_text("Sorry, I encountered an error processing the image. Please try again.")
    
    async def handle_text_message(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming text messages."""
        user_id = update.effective_user.id
        command_text = update.message.text
        session_id = self.audit_logger.generate_session_id()
        
        try:
            response = await self.process_user_command(
                user_id, 
                command_text, 
                session_id
            )
            # Send text response
            await update.message.reply_text(response)
            
            # Generate and send voice response if TTS is enabled
            await self._send_voice_response(update, response)
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            error_msg = "Sorry, I encountered an error processing your message."
            await update.message.reply_text(error_msg)
            await self._send_voice_response(update, error_msg)
    
    def _normalize_text_for_tts(self, text: str) -> str:
        """
        Normalize text before sending to TTS to avoid fraction reading issues.
        Ensures numbers are read correctly (e.g., "2 out of 5" not "two fifths").
        
        Args:
            text: Original text
            
        Returns:
            Normalized text for TTS
        """
        # Replace fractions like "2/5" with "2 out of 5" to prevent TTS from reading as fractions
        # Pattern matches: number/number (but not URLs or paths)
        text = re.sub(r'\b(\d+)/(\d+)\b', r'\1 out of \2', text)
        return text
    
    async def _send_voice_response(
        self,
        update: Update,
        text_response: str
    ) -> None:
        """
        Generate and send voice response for any text response.
        
        Args:
            update: Telegram update object
            text_response: Text response to convert to speech
        """
        try:
            if self.tts.is_enabled() and text_response:
                # Normalize text to prevent TTS from reading fractions incorrectly
                normalized_text = self._normalize_text_for_tts(text_response)
                voice_file_path = await self.tts.generate_speech(normalized_text)
                if voice_file_path:
                    # Check file size (Telegram has 50MB limit for voice messages)
                    file_size = os.path.getsize(voice_file_path)
                    max_size = 50 * 1024 * 1024  # 50MB
                    
                    if file_size > max_size:
                        logger.warning(f"Voice file too large ({file_size} bytes), skipping upload")
                        cleanup_temp_file(voice_file_path)
                        return
                    
                    # Upload with extended timeout for large files
                    # Telegram API can be slow for large audio files
                    # Pass file path as string (python-telegram-bot handles file reading internally)
                    try:
                        await asyncio.wait_for(
                            update.message.reply_voice(voice=voice_file_path),
                            timeout=60.0
                        )
                        logger.debug("Voice response sent successfully")
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout uploading voice file (size: {file_size} bytes)")
                    except Exception as upload_error:
                        logger.warning(f"Error uploading voice file: {upload_error}")
                    finally:
                        # Ensure file is cleaned up
                        cleanup_temp_file(voice_file_path)
        except Exception as e:
            logger.warning(f"Error generating/sending voice response: {e}")
            # Don't fail the whole request if voice fails
    
    async def _process_with_openai(
        self,
        user_query: str,
        json_data: Dict[str, Any],
        data_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process user query with OpenAI using JSON data for detailed responses.
        
        Args:
            user_query: User's question
            json_data: JSON data from ERP API
            data_type: Type of data ("attendance", "timetable", "cafeteria")
            context: Optional conversation context
            
        Returns:
            Personalized response from OpenAI
        """
        try:
            openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
            
            # Build system prompt based on data type
            if data_type == "attendance":
                system_prompt = (
                    "You are a helpful assistant for Bennett University students. "
                    "You have access to their attendance data. Answer their questions "
                    "based on the provided JSON data. Be concise, natural, and helpful. "
                    "Use 'out of' instead of '/' when showing attendance numbers "
                    "(e.g., '2 out of 5 classes' not '2/5'). "
                    "If they ask follow-up questions, use the conversation context provided. "
                    "Keep your response under 500 words. Be concise and get to the point."
                )
            elif data_type == "timetable":
                system_prompt = (
                    "You are a helpful assistant for Bennett University students. "
                    "You have access to their timetable/schedule data. Answer their questions "
                    "based on the provided JSON data. Be concise, natural, and helpful. "
                    "If they ask follow-up questions, use the conversation context provided. "
                    "Keep your response under 500 words. Be concise and get to the point."
                )
            elif data_type == "cafeteria":
                system_prompt = (
                    "You are a helpful assistant for Bennett University students. "
                    "You have access to cafeteria menu data. Answer their questions "
                    "based on the provided JSON data. Be concise, natural, and helpful. "
                    "If they ask follow-up questions, use the conversation context provided. "
                    "Keep your response under 500 words. Be concise and get to the point."
                )
            else:
                system_prompt = (
                    "You are a helpful assistant for Bennett University students. "
                    "Answer their questions based on the provided JSON data. "
                    "Be concise, natural, and helpful. "
                    "Keep your response under 500 words. Be concise and get to the point."
                )
            
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add context if available
            if context:
                context_str = f"Previous conversation:\nQuery: {context.get('last_query', '')}\nResponse: {context.get('last_response', '')}\n"
                messages.append({"role": "user", "content": context_str})
            
            # Add JSON data and current query
            json_str = json.dumps(json_data, indent=2)
            user_message = f"Data:\n{json_str}\n\nUser question: {user_query}"
            messages.append({"role": "user", "content": user_message})
            
            # Call OpenAI
            response = openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error processing with OpenAI: {e}", exc_info=True)
            return None
    
    async def process_user_command(
        self, 
        user_id: int, 
        command_text: str,
        session_id: str
    ) -> str:
        """
        Process user command through the full pipeline.
        
        Args:
            user_id: Telegram user ID
            command_text: User command text
            session_id: Session identifier
            
        Returns:
            Response text
        """
        try:
            # Check if this is a follow-up question and get user context
            is_followup = is_follow_up_question(command_text)
            user_context = self.conversation_context.get(user_id, {})
            
            # Step 1: Intent Classification
            intents = await self.intent_classifier.classify_intent(command_text)
            
            if not intents:
                return "I couldn't understand your request. Please try rephrasing."
            
            # Check if multiple distinct non-conversational intents are detected
            # These should be handled sequentially
            conversational_intents = ["Greeting", "SmallTalk", "Conversation"]
            non_conversational = [i for i in intents if i.name not in conversational_intents]
            
            # If we have multiple distinct actionable intents, handle them sequentially
            if len(non_conversational) > 1:
                # Filter out duplicates (same intent name)
                unique_intents = {}
                for intent in non_conversational:
                    if intent.name not in unique_intents or intent.confidence > unique_intents[intent.name].confidence:
                        unique_intents[intent.name] = intent
                
                unique_intent_list = list(unique_intents.values())
                
                # Only process multiple tasks if they're truly distinct (not just variations)
                if len(unique_intent_list) > 1:
                    logger.info(f"Detected multiple tasks: {[i.name for i in unique_intent_list]}")
                    
                    # Check if SendEmail is paired with a data-fetching intent
                    # These need special handling: fetch data first, then email it
                    data_fetching_intents = [
                        "CheckCafeteriaMenu", "CheckBreakfastMenu", "CheckLunchMenu", 
                        "CheckDinnerMenu", "CheckSnackMenu", "CheckTimetable",
                        "CheckSubjectSchedule", "CheckTimeSchedule", "CheckAttendance",
                        "CheckSubjectAttendance", "CheckMonthlyAttendance", "CheckWeather",
                        "SearchInternet"
                    ]
                    
                    # PDF generation intents already send emails, so if SendEmail is detected with them,
                    # skip SendEmail execution
                    pdf_intents = ["GenerateAttendancePDF", "GenerateTimetablePDF", "GenerateCafeteriaPDF"]
                    has_send_email = any(intent.name == "SendEmail" for intent in unique_intent_list)
                    has_pdf_intent = any(intent.name in pdf_intents for intent in unique_intent_list)
                    data_intent = next((intent for intent in unique_intent_list if intent.name in data_fetching_intents), None)
                    pdf_intent = next((intent for intent in unique_intent_list if intent.name in pdf_intents), None)
                    
                    # If PDF generation intent + SendEmail, skip SendEmail (PDF already sends email)
                    if has_pdf_intent and has_send_email and pdf_intent:
                        logger.info(f"Detected PDF generation + SendEmail: {pdf_intent.name} already handles email, skipping SendEmail")
                        # Extract recipient from SendEmail intent if present
                        email_intent = next((intent for intent in intents if intent.name == "SendEmail"), None)
                        if email_intent:
                            recipient = email_intent.parameters.get("recipient", "")
                            if not recipient or recipient.lower() in ["me", "my email", "myself", "to me", "send to me", "email it to me"]:
                                recipient = "me"  # Will use Config.USER_EMAIL
                            pdf_intent.parameters["recipient"] = recipient
                            logger.info(f"Set recipient for PDF generation: {recipient}")
                        
                        # Remove SendEmail from the list and only execute PDF intent
                        unique_intent_list = [intent for intent in unique_intent_list if intent.name != "SendEmail"]
                        
                        # Update has_send_email to reflect the filtered list
                        has_send_email = False
                        
                        # If only PDF intent remains, it will be handled in the sequential execution below
                        # (which will execute just that one intent)
                    
                    # If SendEmail + data-fetching intent, handle specially (but not if PDF is present)
                    if has_send_email and data_intent and not has_pdf_intent:
                        logger.info(f"Detected email request with data fetch: {data_intent.name} + SendEmail")
                        results = []
                        
                        # Step 1: Fetch the data first
                        try:
                            data_params = data_intent.parameters.copy()
                            if data_intent.name in ["AddTodo", "ListTodos", "CompleteTodo", "DeleteTodo"]:
                                data_params["user_id"] = str(user_id)
                            
                            data_result = await self.action_executor.execute_action(
                                {"name": data_intent.name},
                                data_params
                            )
                            
                            if not data_result.get("success"):
                                return f"Failed to fetch {data_intent.name}: {data_result.get('error', 'Unknown error')}"
                            
                            # Get the data content - check multiple possible fields
                            data_content = data_result.get("result", "")
                            
                            # If result is just a status message, try to get the actual data
                            if not data_content or data_content in ["Task completed successfully.", "Cafeteria menu retrieved", 
                                                                   "Lunch menu retrieved", "Dinner menu retrieved", 
                                                                   "Breakfast menu retrieved", "Snack menu retrieved",
                                                                   "Timetable data retrieved", "Attendance data retrieved"]:
                                # Try to get formatted data from different fields
                                data_content = data_result.get("data", "")
                            
                            # If still empty, try raw_data and format it using executor's erp_client
                            if not data_content and data_result.get("raw_data"):
                                # For cafeteria menu, format the raw data
                                if data_intent.name in ["CheckCafeteriaMenu", "CheckBreakfastMenu", "CheckLunchMenu", 
                                                         "CheckDinnerMenu", "CheckSnackMenu"]:
                                    meal_type = None
                                    if data_intent.name == "CheckBreakfastMenu":
                                        meal_type = "breakfast"
                                    elif data_intent.name == "CheckLunchMenu":
                                        meal_type = "lunch"
                                    elif data_intent.name == "CheckDinnerMenu":
                                        meal_type = "dinner"
                                    elif data_intent.name == "CheckSnackMenu":
                                        meal_type = "snack"
                                    # Use executor's erp_client to format the menu
                                    data_content = self.executor.erp_client._format_cafeteria_menu(
                                        data_result.get("raw_data"), meal_type
                                    )
                            
                            # Final fallback
                            if not data_content:
                                data_content = f"Data retrieved for {data_intent.name}"
                            
                            # Step 2: Send email with the fetched data
                            email_intent = next((intent for intent in unique_intent_list if intent.name == "SendEmail"), None)
                            if email_intent:
                                email_params = email_intent.parameters.copy()
                                
                                # Set email body to the fetched data
                                email_params["body"] = data_content
                                
                                # Generate subject from intent name
                                subject_map = {
                                    "CheckCafeteriaMenu": "Cafeteria Menu",
                                    "CheckBreakfastMenu": "Breakfast Menu",
                                    "CheckLunchMenu": "Lunch Menu",
                                    "CheckDinnerMenu": "Dinner Menu",
                                    "CheckSnackMenu": "Snack Menu",
                                    "CheckTimetable": "Class Timetable",
                                    "CheckSubjectSchedule": "Subject Schedule",
                                    "CheckTimeSchedule": "Time Schedule",
                                    "CheckAttendance": "Attendance Report",
                                    "CheckSubjectAttendance": "Subject Attendance",
                                    "CheckMonthlyAttendance": "Monthly Attendance",
                                    "CheckWeather": "Weather Information",
                                    "SearchInternet": "Internet Search Results"
                                }
                                
                                if "subject" not in email_params or not email_params.get("subject"):
                                    email_params["subject"] = subject_map.get(data_intent.name, f"{data_intent.name} Information")
                                
                                # Handle recipient
                                recipient = email_params.get("recipient", "")
                                if not recipient or recipient.lower() in ["me", "my email", "myself", "to me", "send to me", "email it to me"]:
                                    if Config.USER_EMAIL:
                                        recipient = Config.USER_EMAIL
                                    else:
                                        recipient = "me"  # Will use default
                                email_params["recipient"] = recipient
                                
                                # Send email
                                email_result = await self.action_executor.execute_action(
                                    {"name": "SendEmail"},
                                    email_params
                                )
                                
                                if email_result.get("success"):
                                    return f"Fetched {data_intent.name} and sent it via email to {recipient}."
                                else:
                                    return f"Fetched {data_intent.name} successfully, but failed to send email: {email_result.get('error', 'Unknown error')}"
                            else:
                                return f"Fetched {data_intent.name}: {data_content}"
                                
                        except Exception as e:
                            logger.error(f"Error executing email+data task: {e}", exc_info=True)
                            return f"Error: {str(e)}"
                    
                    # For other multiple intents, process sequentially
                    results = []
                    for idx, intent in enumerate(unique_intent_list):
                        try:
                            # Prepare parameters for this intent
                            intent_params = intent.parameters.copy()
                            if intent.name in ["AddTodo", "ListTodos", "CompleteTodo", "DeleteTodo"]:
                                intent_params["user_id"] = str(user_id)
                            
                            # Execute the intent
                            current_state = State()
                            action_result = await self.action_executor.execute_action(
                                {"name": intent.name},
                                intent_params
                            )
                            
                            if action_result.get("success"):
                                result_text = action_result.get("result", "Task completed successfully.")
                                results.append(f"Task {idx + 1} ({intent.name}): {result_text}")
                            else:
                                error_msg = action_result.get("error", "Unknown error occurred.")
                                results.append(f"Task {idx + 1} ({intent.name}): Failed - {error_msg}")
                        except Exception as e:
                            logger.error(f"Error executing task {intent.name}: {e}", exc_info=True)
                            results.append(f"Task {idx + 1} ({intent.name}): Error - {str(e)}")
                    
                    # Return combined results
                    return "\n\n".join(results)
            
            # Handle "add reminder" or "add to todo list" - prioritize AddTodo over SetReminder
            # Check if user said "add reminder" or "add to todo" without a specific time
            add_reminder_pattern = re.search(r'\badd\s+(?:reminder|to\s+(?:my\s+)?todo)', command_text, re.IGNORECASE)
            has_add_todo = any(intent.name == "AddTodo" for intent in intents)
            has_set_reminder = any(intent.name == "SetReminder" for intent in intents)
            
            # If both AddTodo and SetReminder are detected, and user said "add reminder",
            # prioritize AddTodo (unless there's a clear datetime in the message)
            if add_reminder_pattern and has_add_todo and has_set_reminder:
                # Check if there's a time/datetime mentioned
                time_patterns = [
                    r'\b(at|for|on|by)\s+\d+',  # "at 3pm", "for 10am", "on Monday"
                    r'\b\d+\s*(am|pm|AM|PM)',   # "3pm", "10am"
                    r'\b(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
                    r'\b(in|after)\s+\d+\s*(minute|hour|day|week)s?'
                ]
                has_time = any(re.search(pattern, command_text, re.IGNORECASE) for pattern in time_patterns)
                
                if not has_time:
                    # No time mentioned, treat as AddTodo - filter out SetReminder
                    intents = [intent for intent in intents if intent.name != "SetReminder"]
                    logger.info("Detected 'add reminder' without time - treating as AddTodo")
            
            # Check for valid multi-step patterns (e.g., Generate*PDF + SendEmail)
            # Also check if "email" or "mail" is mentioned anywhere in the command
            pdf_intents = ["GenerateAttendancePDF", "GenerateTimetablePDF", "GenerateCafeteriaPDF"]
            has_pdf_intent = any(intent.name in pdf_intents for intent in intents)
            has_send_email = any(intent.name == "SendEmail" for intent in intents)
            
            # Check if email/mail is mentioned in command text (even if SendEmail intent not detected)
            email_keywords = ["email", "mail", "send via email", "email me", "email it", "mail me", "mail it"]
            has_email_keyword = any(keyword in command_text.lower() for keyword in email_keywords)
            
            # If email keyword is present but SendEmail intent not detected, add it
            if has_email_keyword and not has_send_email:
                # Create a SendEmail intent with high confidence
                email_intent = Intent(
                    name="SendEmail",
                    confidence=0.95,
                    parameters={"recipient": ""}
                )
                intents.append(email_intent)
                has_send_email = True
                logger.info("Added SendEmail intent based on email/mail keyword detection")
            
            # If we have a PDF generation intent + SendEmail, treat as single task
            # (PDF generation actions already send emails, so we just need to set recipient)
            if has_pdf_intent and has_send_email:
                # Find the PDF intent and SendEmail intent
                pdf_intent = next((i for i in intents if i.name in pdf_intents), None)
                email_intent = next((i for i in intents if i.name == "SendEmail"), None)
                
                if pdf_intent and email_intent:
                    # Use PDF intent as primary (it already handles emailing)
                    primary_intent = pdf_intent
                    # Extract recipient from email intent or command text
                    recipient = email_intent.parameters.get("recipient", "")
                    if not recipient or recipient.lower() in ["me", "my email", "myself", "to me", "send to me"]:
                        recipient = "me"  # Will use Config.USER_EMAIL
                    # Set recipient in PDF intent parameters
                    primary_intent.parameters["recipient"] = recipient
                    logger.info(f"Detected report+email request: {primary_intent.name} with recipient: {recipient}")
                    secondary_intent = None  # PDF action handles emailing
                else:
                    # Fallback to normal ambiguity handling
                    resolved_intent = self.intent_classifier.handle_ambiguity(intents)
                    if resolved_intent is None:
                        clarification = self.intent_classifier.ask_clarification(intents)
                        return clarification
                    primary_intent = resolved_intent
                    secondary_intent = None
            else:
                # Special handling for conversational intents (Greeting, SmallTalk, Conversation)
                # These are similar and should be handled automatically without clarification
                conversational_intents = ["Greeting", "SmallTalk", "Conversation"]
                detected_conversational = [i for i in intents if i.name in conversational_intents]
                
                if len(detected_conversational) > 0:
                    # If all detected intents are conversational, pick the highest confidence one
                    if all(i.name in conversational_intents for i in intents):
                        primary_intent = max(intents, key=lambda x: x.confidence)
                        logger.info(f"Auto-resolved conversational intents: {primary_intent.name} (confidence: {primary_intent.confidence})")
                    # If conversational intents mixed with others, still prioritize conversational
                    elif len(detected_conversational) == 1 and len(intents) == 2:
                        # One conversational + one other - check if conversational is primary
                        if detected_conversational[0].confidence >= intents[0].confidence:
                            primary_intent = detected_conversational[0]
                            logger.info(f"Selected conversational intent over other: {primary_intent.name}")
                        else:
                            # Use normal ambiguity handling
                            resolved_intent = self.intent_classifier.handle_ambiguity(intents)
                            if resolved_intent is None:
                                clarification = self.intent_classifier.ask_clarification(intents)
                                return clarification
                            primary_intent = resolved_intent
                    else:
                        # Use normal ambiguity handling
                        resolved_intent = self.intent_classifier.handle_ambiguity(intents)
                        if resolved_intent is None:
                            clarification = self.intent_classifier.ask_clarification(intents)
                            return clarification
                        primary_intent = resolved_intent
                    secondary_intent = None
                else:
                    # Handle ambiguity normally for non-conversational intents
                    resolved_intent = self.intent_classifier.handle_ambiguity(intents)
                    
                    if resolved_intent is None:
                        clarification = self.intent_classifier.ask_clarification(intents)
                        return clarification
                    
                    primary_intent = resolved_intent
                    secondary_intent = None
            
            # Log intent classification
            await self.audit_logger.log_intent_classification(
                session_id=session_id,
                user_input=command_text,
                detected_intents=[{"name": i.name, "confidence": i.confidence} 
                                for i in intents],
                selected_intent=primary_intent.name,
                confidence=primary_intent.confidence
            )
            
            # Check for capability questions early and return hardcoded response
            capability_keywords = [
                "what can you do", "what do you do", "how can you help", "what are your capabilities",
                "what can you help with", "what features", "what are you capable of", "what can i ask you",
                "how can i use you", "what do you offer", "tell me what you can do", "explain what you can do"
            ]
            is_capability_question = any(keyword in command_text.lower() for keyword in capability_keywords)
            
            if is_capability_question:
                capabilities_response = (
                    "I'm Talky, your AI assistant! Here's what I can do for you:\n\n"
                    "Academic Information:\n"
                    "• Check your attendance for any subject or month\n"
                    "• View your class timetable and schedule\n"
                    "• Get cafeteria menu for breakfast, lunch, dinner, or snacks\n"
                    "• Generate PDF reports of attendance, timetable, or cafeteria menu\n\n"
                    "Internet & Information:\n"
                    "• Search the internet for any topic or question\n"
                    "• Answer general knowledge questions\n"
                    "• Provide detailed explanations on various subjects\n\n"
                    "Communication:\n"
                    "• Send emails with formatted responses\n"
                    "• Email PDF reports directly to you\n"
                    "• Format and organize information for email\n\n"
                    "Task Management:\n"
                    "• Add tasks to your todo list\n"
                    "• List all your todos (pending or completed)\n"
                    "• Mark tasks as complete\n"
                    "• Delete tasks from your list\n\n"
                    "Other Features:\n"
                    "• Check weather for any location\n"
                    "• Analyze images and describe what's in them\n"
                    "• Have natural conversations\n"
                    "• Answer follow-up questions with context\n\n"
                    "You can ask me anything using text or voice messages! "
                    "Try saying things like 'What's my attendance?', 'Email me my timetable', "
                    "or 'Search for information about AI'."
                )
                
                return capabilities_response
            
            # Step 2: State Setup
            # Create a fresh state for this command (don't reuse global state)
            current_state = State()
            
            # Add user_id to todo-related intents
            # For web UI, use 'web_user' to match dashboard; for Telegram, use the actual user_id
            if primary_intent.name in ["AddTodo", "ListTodos", "CompleteTodo", "DeleteTodo"]:
                # Check if this is from web UI (session_id is a string UUID) vs Telegram (session_id is None or numeric)
                # Web UI sessions have string session_ids (UUIDs), Telegram doesn't use session_id
                if session_id and isinstance(session_id, str) and len(session_id) > 10:
                    # Web UI - use consistent 'web_user' for todos so they appear in dashboard
                    primary_intent.parameters["user_id"] = "web_user"
                    logger.info(f"Using 'web_user' for todo operations from web UI (session_id: {session_id[:20]}...)")
                else:
                    # Telegram - use the actual user_id
                    primary_intent.parameters["user_id"] = str(user_id)
                    logger.info(f"Using user_id '{user_id}' for todo operations from Telegram")
                
                # For ListTodos, detect if user wants completed tasks
                if primary_intent.name == "ListTodos":
                    completed_keywords = ["completed", "done", "finished", "complete"]
                    if any(keyword in command_text.lower() for keyword in completed_keywords):
                        primary_intent.parameters["show_completed"] = True
                        primary_intent.parameters["completed_only"] = True  # Filter for completed only
                    else:
                        primary_intent.parameters["show_completed"] = False
                # For AddTodo, extract task from command text if not provided
                if primary_intent.name == "AddTodo" and "task" not in primary_intent.parameters:
                    # Extract task text after various todo/reminder phrases
                    task_patterns = [
                        r'(?:add|create|new)\s+(?:todo|task)\s+(.+)',
                        r'add\s+to\s+(?:my\s+)?todo\s+(?:list\s+)?(.+)',
                        r'add\s+reminder\s+(?:to\s+)?(.+)',
                        r'create\s+reminder\s+(?:to\s+)?(.+)',
                        r'remember\s+to\s+(.+)',
                        r'remind\s+me\s+to\s+(.+)',
                        r'set\s+a\s+todo\s+(?:to\s+)?(.+)',
                        r'make\s+a\s+todo\s+(?:to\s+)?(.+)',
                        r'add\s+(.+?)\s+to\s+(?:my\s+)?todo',
                        r'add\s+(.+?)\s+for\s+(?:my\s+)?todo'
                    ]
                    task_text = None
                    for pattern in task_patterns:
                        match = re.search(pattern, command_text, re.IGNORECASE)
                        if match:
                            task_text = match.group(1).strip()
                            break
                    
                    # If no direct match, try fallback extraction
                    if not task_text:
                        task_text = re.sub(
                            r'^(add|create|new|set|make)\s+(?:a\s+)?(?:to\s+)?(?:my\s+)?(?:todo|task|reminder)(?:\s+list)?\s+(?:to\s+)?', 
                            '', 
                            command_text, 
                            flags=re.IGNORECASE
                        ).strip()
                    
                    # Handle references like "that class", "it", "this", etc. using conversation context
                    if task_text and user_context:
                        last_response = user_context.get("last_response", "")
                        last_query = user_context.get("last_query", "")
                        
                        # Check for references to classes/subjects
                        reference_patterns = [
                            r'\b(that|this|it)\s+class\b',
                            r'\bfor\s+(that|this|it)\s+class\b',
                            r'\b(that|this|it)\s+subject\b',
                            r'\bfor\s+(that|this|it)\s+subject\b'
                        ]
                        
                        has_reference = any(re.search(pattern, task_text, re.IGNORECASE) for pattern in reference_patterns)
                        
                        if has_reference:
                            # Try to extract class/subject name from previous response
                            # Prioritize patterns that mention attendance/classes
                            class_patterns = [
                                # Patterns specifically for attendance-related responses (highest priority)
                                r'lowest attendance.*?"([^"]+)"',  # "lowest attendance is "Class Name""
                                r'class with.*?lowest.*?"([^"]+)"',  # "class with lowest attendance is "Class Name""
                                r'lowest.*?attendance.*?"([^"]+)"',  # "lowest attendance: "Class Name""
                                r'"([^"]+)".*?lowest.*?attendance',  # ""Class Name" has lowest attendance"
                                r'"([^"]+)".*?\d+%.*?attendance',  # ""Class Name" with 40% attendance"
                                r'attendance.*?"([^"]+)"',  # "attendance for "Class Name""
                                
                                # General quoted patterns
                                r'class is "([^"]+)"',
                                r'subject is "([^"]+)"',
                                r'class[:\s]+"([^"]+)"',
                                r'"([^"]+)"',  # Any quoted name
                                
                                # Pattern for unquoted class names (backup)
                                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,})\b'  # Multi-word capitalized phrases
                            ]
                            
                            extracted_class = None
                            for pattern in class_patterns:
                                matches = re.findall(pattern, last_response, re.IGNORECASE)
                                if matches:
                                    # Prefer quoted names, then longer capitalized phrases
                                    for match in matches:
                                        match_clean = match.strip()
                                        # Filter out common false positives
                                        if (match_clean.lower() not in ['user input', 'bennett university', 'united states', 'new york'] and
                                            len(match_clean.split()) >= 2):  # At least 2 words for a class name
                                            # Prefer longer names (more likely to be full class names)
                                            if not extracted_class or len(match_clean.split()) > len(extracted_class.split()):
                                                extracted_class = match_clean
                                    if extracted_class:
                                        break
                            
                            # Also check stored class name from context (if available)
                            if not extracted_class and user_context.get("last_class_name"):
                                stored_class = user_context.get("last_class_name")
                                if len(stored_class.split()) >= 2:
                                    extracted_class = stored_class
                                    logger.info(f"Using stored class name from context: {extracted_class}")
                            
                            # Also check last_query for class names if not found in response
                            if not extracted_class and last_query:
                                # Look for class/subject mentions in the query
                                query_class_patterns = [
                                    r'attendance.*?for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                                    r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,})',
                                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,}).*?attendance'
                                ]
                                for pattern in query_class_patterns:
                                    matches = re.findall(pattern, last_query, re.IGNORECASE)
                                    if matches:
                                        for match in matches:
                                            match_clean = match.strip()
                                            if len(match_clean.split()) >= 2:
                                                extracted_class = match_clean
                                                break
                                        if extracted_class:
                                            break
                            
                            if extracted_class:
                                # Replace reference with actual class name
                                task_text = re.sub(
                                    r'\b(that|this|it)\s+(class|subject)\b',
                                    extracted_class,
                                    task_text,
                                    flags=re.IGNORECASE
                                )
                                task_text = re.sub(
                                    r'\bfor\s+(that|this|it)\s+(class|subject)\b',
                                    f'for {extracted_class}',
                                    task_text,
                                    flags=re.IGNORECASE
                                )
                                logger.info(f"Resolved reference to class: {extracted_class}")
                    
                    # Clean up common abbreviations
                    if task_text:
                        task_text = re.sub(r'\binc\b', 'increase', task_text, flags=re.IGNORECASE)
                        task_text = re.sub(r'\batt\b', 'attendance', task_text, flags=re.IGNORECASE)
                        task_text = task_text.strip()
                        
                        # Ensure task ends properly (remove trailing "to my todo" etc.)
                        task_text = re.sub(r'\s+to\s+(?:my\s+)?todo(?:\s+list)?\s*$', '', task_text, flags=re.IGNORECASE)
                        task_text = task_text.strip()
                        
                        if task_text:
                            primary_intent.parameters["task"] = task_text
            
            # Handle missing required parameters
            # For CheckWeather, use default location if not specified
            if primary_intent.name == "CheckWeather" and "location" not in primary_intent.parameters:
                primary_intent.parameters["location"] = Config.DEFAULT_WEATHER_LOCATION
                logger.info(f"No location specified, using default: {Config.DEFAULT_WEATHER_LOCATION}")
            
            # For CheckSubjectAttendance, try to extract subject if missing
            if primary_intent.name == "CheckSubjectAttendance":
                if "subject" not in primary_intent.parameters or not primary_intent.parameters.get("subject"):
                    # Try to extract from command text
                    entities = extract_entities(command_text, ["subject"])
                    if "subject" in entities:
                        primary_intent.parameters["subject"] = entities["subject"]
                    else:
                        # Try to extract from command text using regex patterns
                        # Look for subject name patterns after "for" or "in"
                        subject_match = re.search(r'(?:for|in|attendance|schedule)\s+([A-Z][a-z]+(?:\s+[a-z]+)*)', command_text, re.IGNORECASE)
                        if subject_match:
                            subject_text = subject_match.group(1).strip()
                            # Clean up common words
                            subject_text = re.sub(r'\b(attendance|schedule|the|for|in|of|my)\b', '', subject_text, flags=re.IGNORECASE).strip()
                            if subject_text:
                                primary_intent.parameters["subject"] = subject_text
                        else:
                            # Last resort: extract everything after "for" or "in"
                            fallback_match = re.search(r'(?:for|in)\s+(.+?)(?:\?|$)', command_text, re.IGNORECASE)
                            if fallback_match:
                                subject_text = fallback_match.group(1).strip()
                                subject_text = re.sub(r'\b(attendance|schedule|the|for|in|of|my)\b', '', subject_text, flags=re.IGNORECASE).strip()
                                if subject_text:
                                    primary_intent.parameters["subject"] = subject_text
                
                # If still no subject, return helpful message
                if "subject" not in primary_intent.parameters or not primary_intent.parameters.get("subject"):
                    return (
                        "I need to know which subject you're asking about. Please specify:\n"
                        "• 'Attendance for CSET381'\n"
                        "• 'CSET381 attendance'\n"
                        "• 'Attendance in Applications of AI'"
                    )
            
            # For CheckSubjectSchedule, try to extract subject if missing
            if primary_intent.name == "CheckSubjectSchedule" and "subject" not in primary_intent.parameters:
                entities = extract_entities(command_text, ["subject"])
                if "subject" in entities:
                    primary_intent.parameters["subject"] = entities["subject"]
                else:
                    # Extract after "when is" or "schedule for"
                    subject_match = re.search(r'(?:when is|schedule for|time for)\s+([A-Z][a-z]+(?:\s+[a-z]+)*)', command_text, re.IGNORECASE)
                    if subject_match:
                        subject_text = subject_match.group(1).strip()
                        subject_text = re.sub(r'\b(schedule|the|for|when|is|time)\b', '', subject_text, flags=re.IGNORECASE).strip()
                        if subject_text:
                            primary_intent.parameters["subject"] = subject_text
            
            # For SearchInternet, extract query if missing and handle follow-up context
            if primary_intent.name == "SearchInternet":
                if "query" not in primary_intent.parameters or not primary_intent.parameters.get("query"):
                    # Extract query by removing search keywords
                    query = command_text
                    # Remove common search prefixes
                    query = re.sub(r'^(search\s+(the\s+)?(internet|web|online)\s+for|search\s+for|look\s+up|find\s+information\s+about|what\s+is|tell\s+me\s+about)\s+', '', query, flags=re.IGNORECASE)
                    query = query.strip()
                    
                    # If this is a follow-up question, append context from previous conversation
                    if is_followup and user_context:
                        # Check if previous message mentioned a topic/entity (like "Bennett University")
                        last_query = user_context.get("last_query", "")
                        last_response = user_context.get("last_response", "")
                        
                        # Extract potential entities from previous messages (capitalized phrases, proper nouns)
                        # Look for patterns like "about X" or mentions of entities
                        context_entity = None
                        
                        # Check last query for "about X" pattern (e.g., "It will be about Bennett University")
                        # Enhanced pattern to catch "Tell me about X" specifically for person names
                        about_patterns = [
                            r'(?:tell\s+me\s+about|about)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "Tell me about Abhay Bansal"
                            r'(?:about|regarding|concerning|will be about|talking about)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # Generic pattern
                        ]
                        for pattern in about_patterns:
                            about_match = re.search(pattern, last_query, re.IGNORECASE)
                            if about_match:
                                context_entity = about_match.group(1).strip()
                                # Extract full name if there's more after comma
                                if ',' in last_query and context_entity:
                                    parts = last_query.split(',')
                                    for part in parts:
                                        name_match = re.search(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', part)
                                        if name_match:
                                            potential_name = name_match.group(1).strip()
                                            if potential_name.lower() not in ['bennett university', 'united states']:
                                                context_entity = potential_name
                                                break
                                if context_entity:
                                    logger.info(f"Extracted entity from query: {context_entity}")
                                    break
                        
                        # If no "about" pattern, look for capitalized multi-word phrases in last query
                        if not context_entity:
                            # Find all capitalized multi-word phrases
                            capitalized_matches = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', last_query)
                            for potential_entity in capitalized_matches:
                                # Filter out common words and phrases (but keep proper nouns like "Bennett University")
                                potential_lower = potential_entity.lower()
                                # Only filter out very common/obvious non-entities
                                if potential_lower not in ['user input', 'bennett university', 'united states', 'new york']:
                                    # Two words = likely person name (First Last)
                                    if len(potential_entity.split()) == 2:
                                        context_entity = potential_entity
                                        logger.info(f"Extracted person name from query: {context_entity}")
                                        break
                        
                        # Also check last response for entities (in case the entity was mentioned in bot's response)
                        # This is important for follow-ups like "his policies" after "who won the election?"
                        if not context_entity and last_response:
                            # First try "about X" pattern
                            about_match_resp = re.search(r'(?:about|regarding|concerning)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', last_response, re.IGNORECASE)
                            if about_match_resp:
                                context_entity = about_match_resp.group(1).strip()
                            
                            # If still no entity, look for person names (proper nouns) in the response
                            # Common patterns: "X won", "X is", "X was elected", "X's", "X is Dean", etc.
                            if not context_entity:
                                # Look for person names (capitalized first + last name pattern)
                                person_patterns = [
                                    r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:won|is|was|has|have|did|will|mayor|president|governor|dean|elected|appointed|serves|works)',
                                    r'(?:won|elected|appointed|serves as|is)\s+(?:by|as|the)?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                                    r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\'s',  # "Abhay Bansal's"
                                    r'(?:mayor|president|governor|dean|director|professor)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:is|was|serves as)\s+(?:the\s+)?(?:dean|director|president|mayor)',  # "Abhay Bansal is the Dean"
                                    r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b',  # Fallback: any two-word capitalized phrase
                                ]
                                
                                found_names = []
                                for pattern in person_patterns:
                                    matches = re.findall(pattern, last_response, re.IGNORECASE)
                                    for match in matches:
                                        if isinstance(match, tuple):
                                            potential_name = match[0] if match[0] else match[1]
                                        else:
                                            potential_name = match
                                        potential_name = potential_name.strip()
                                        # Filter out common false positives
                                        if (potential_name.lower() not in ['new york', 'united states', 'user input', 'bennett university'] 
                                            and len(potential_name.split()) == 2):  # Two words = person name
                                            found_names.append(potential_name)
                                
                                # Use the first valid person name found
                                if found_names:
                                    context_entity = found_names[0]
                                    logger.info(f"Extracted person name from response: {context_entity}")
                            
                            # If still no specific entity, try extracting from last_query (might be in the question)
                            if not context_entity:
                                # Look for "who won" or "who is" patterns
                                who_patterns = [
                                    r'who\s+(?:won|is|was|has)\s+(?:the\s+)?(?:election|mayor|president|governor|race)\s+(?:for|in|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                                    r'who\s+(?:won|is|was)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                                ]
                                for pattern in who_patterns:
                                    match = re.search(pattern, last_query, re.IGNORECASE)
                                    if match:
                                        context_entity = match.group(1).strip()
                                        break
                        
                        # If we found context, intelligently combine it with the query
                        if context_entity:
                            # Check if query already contains the context entity
                            if context_entity.lower() not in query.lower():
                                # Handle queries with pronouns like "his policies", "their plans", "it's"
                                # Replace pronouns with the actual entity name
                                pronoun_replacements = [
                                    (r'\bhis\b', f"{context_entity}'s"),
                                    (r'\bher\b', f"{context_entity}'s"),
                                    (r'\btheir\b', f"{context_entity}'s"),
                                    (r'\bits\b', f"{context_entity}'s"),
                                    (r'\bhe\b', context_entity),
                                    (r'\bshe\b', context_entity),
                                    (r'\bthey\b', context_entity),
                                    (r'\bit\b', context_entity),
                                ]
                                
                                query_clean = query
                                for pronoun_pattern, replacement in pronoun_replacements:
                                    query_clean = re.sub(pronoun_pattern, replacement, query_clean, flags=re.IGNORECASE)
                                
                                if query_clean != query:
                                    query = query_clean
                                else:
                                    # If no pronoun replacement, prepend the entity
                                    query = f"{context_entity} {query}".strip()
                                logger.info(f"Added context to search query: {query}")
                    
                    if query:
                        primary_intent.parameters["query"] = query
                    else:
                        # If no query extracted, use full command text
                        primary_intent.parameters["query"] = command_text
                
                # Ensure query_valid fact is set
                if primary_intent.parameters.get("query"):
                    current_state.set_fact("query_valid", True)
            
            # For SendEmail, handle "send to me" or normalize recipient
            if primary_intent.name == "SendEmail":
                recipient = primary_intent.parameters.get("recipient", "")
                # Normalize "me", "my email", "myself", "to me" to "me" for later processing
                if recipient:
                    normalized_recipient = recipient.lower().strip()
                    if normalized_recipient in ["me", "my email", "myself", "to me", "send to me"]:
                        primary_intent.parameters["recipient"] = "me"
                        logger.info("Normalized recipient to 'me' for default user email")
            
            # Set up initial facts based on intent parameters
            logger.debug(f"Intent parameters: {primary_intent.parameters}")
            for param_name, param_value in primary_intent.parameters.items():
                current_state.set_fact(f"{param_name}_valid", True)
                current_state.set_fact(param_name, param_value)
            
            # Ensure required preconditions are set
            # For CheckWeather, we need location_valid=True
            if primary_intent.name == "CheckWeather":
                if "location" in primary_intent.parameters:
                    current_state.set_fact("location_valid", True)
                else:
                    # Fallback: use a default location if somehow missing
                    current_state.set_fact("location", "current location")
                    current_state.set_fact("location_valid", True)
            
            # For CheckTimetable, date is optional (defaults to today)
            if primary_intent.name == "CheckTimetable":
                if "date" not in primary_intent.parameters:
                    # Will default to today in the ERP client
                    pass
            
            # Handle Greeting, SmallTalk, and Conversation intents with OpenAI for natural responses
            if primary_intent.name in ["Greeting", "SmallTalk", "Conversation"]:
                try:
                    # Get conversation history for context
                    user_context = self.conversation_context.get(user_id, {})
                    conversation_history = user_context.get("conversation_history", [])
                    
                    # Use OpenAI for natural, conversational responses
                    openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
                    
                    # Build conversation history
                    messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are Talky, a friendly and helpful AI assistant for Bennett University students. "
                                "You're warm, conversational, and personable. Make users feel like they're talking to a real person.\n\n"
                                "Guidelines:\n"
                                "- Be natural and friendly\n"
                                "- Keep responses concise (2-3 sentences for greetings, slightly longer for conversations)\n"
                                "- Show genuine interest in helping\n"
                                "- Remember context from previous messages\n"
                                "- If they ask what you can do, mention: weather, attendance, timetable, cafeteria menu, internet search, emails, and more\n"
                                "- Use natural language, avoid robotic responses\n"
                                "- Be engaging but not overly verbose\n"
                                "- Keep your response under 500 words. Be concise and get to the point."
                            )
                        }
                    ]
                    
                    # Add conversation history (last 4 exchanges)
                    for exchange in conversation_history[-4:]:
                        messages.append({"role": "user", "content": exchange.get("user", "")})
                        messages.append({"role": "assistant", "content": exchange.get("assistant", "")})
                    
                    # Add current message
                    messages.append({"role": "user", "content": command_text})
                    
                    response = openai_client.chat.completions.create(
                        model=Config.OPENAI_MODEL,
                        messages=messages,
                        temperature=0.8,
                        max_tokens=200
                    )
                    
                    ai_response = response.choices[0].message.content.strip()
                    
                    # Update conversation history
                    if user_id not in self.conversation_context:
                        self.conversation_context[user_id] = {"conversation_history": []}
                    
                    self.conversation_context[user_id]["conversation_history"].append({
                        "user": command_text,
                        "assistant": ai_response
                    })
                    # Keep only last 10 exchanges
                    if len(self.conversation_context[user_id]["conversation_history"]) > 10:
                        self.conversation_context[user_id]["conversation_history"] = \
                            self.conversation_context[user_id]["conversation_history"][-10:]
                    
                    # Log the intent handling
                    await self.audit_logger.log_intent_classification(
                        session_id=session_id,
                        user_input=command_text,
                        detected_intents=[{"name": primary_intent.name, "confidence": primary_intent.confidence}],
                        selected_intent=primary_intent.name,
                        confidence=primary_intent.confidence
                    )
                    
                    return ai_response
                    
                except Exception as e:
                    logger.error(f"Error getting AI response for {primary_intent.name}: {e}")
                    # Fallback responses
                    if primary_intent.name == "Greeting":
                        return "Hello! I'm Talky, your AI assistant. How can I help you today?"
                    elif primary_intent.name == "SmallTalk":
                        return "I'm doing well, thanks for asking! I'm here to help with weather, attendance, timetable, cafeteria menu, and more. What would you like to know?"
                    else:
                        return "I'm here to help! What can I do for you?"
            
            # Step 3: Goal State Creation
            goal_state = State()  # Create fresh goal state
            
            # Handle Unknown intent specially - forward to OpenAI for general AI response
            if primary_intent.name == "Unknown":
                try:
                    # Use OpenAI to generate a helpful response for unknown queries
                    openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
                    
                    response = openai_client.chat.completions.create(
                        model=Config.OPENAI_MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are Talky, a helpful AI assistant for Bennett University students. "
                                    "You can help with:\n"
                                    "- Checking weather, attendance, timetable, and cafeteria menu\n"
                                    "- Searching the internet for information\n"
                                    "- Sending emails\n"
                                    "- Answering general questions\n"
                                    "- Providing academic assistance\n\n"
                                    "Guidelines:\n"
                                    "- Be concise and to the point\n"
                                    "- Use natural, conversational language\n"
                                    "- Avoid repetition or redundant information\n"
                                    "- Speak naturally as if having a conversation\n"
                                    "- If asked about attendance/timetable/menu, mention that you can check those for them\n"
                                    "- Be helpful and engaging\n"
                                    "- Keep your response under 500 words. Be concise and get to the point."
                                )
                            },
                            {
                                "role": "user",
                                "content": command_text
                            }
                        ],
                        temperature=0.7,
                        max_tokens=300
                    )
                    
                    ai_response = response.choices[0].message.content.strip()
                    
                    # Log the Unknown intent handling
                    await self.audit_logger.log_intent_classification(
                        session_id=session_id,
                        user_input=command_text,
                        detected_intents=[{"name": "Unknown", "confidence": primary_intent.confidence}],
                        selected_intent="Unknown",
                        confidence=primary_intent.confidence
                    )
                    
                    return ai_response
                    
                except Exception as e:
                    logger.error(f"Error getting AI response for Unknown intent: {e}")
                    # Fallback to helpful message
                    return (
                        "I'm not sure how to help with that request.\n\n"
                        "I can help you with:\n"
                        "• Check current weather for any location\n"
                        "• Search the internet for information\n"
                        "• Send emails\n"
                        "• Check attendance\n"
                        "• Check timetable\n"
                        "• Check cafeteria menu\n"
                        "• Book hotels\n"
                        "• Set reminders\n"
                        "• Search for flights\n"
                        "• Create calendar events\n"
                        "• Plan trips\n\n"
                        "Try rephrasing your request, or use one of the examples above!"
                    )
            
            # Map intent to goal facts
            intent_to_goal = {
                "CheckWeather": "weather_known",
                "SendEmail": "email_sent",
                "BookHotel": "hotel_booked",
                "SetReminder": "reminder_set",
                "SearchFlights": "flights_found",
                "CreateCalendarEvent": "calendar_event_created",
                "PlanTrip": "trip_planned",
                "CheckAttendance": "attendance_known",
                "CheckSubjectAttendance": "subject_attendance_known",
                "CheckMonthlyAttendance": "monthly_attendance_known",
                "CheckTimetable": "timetable_known",
                "CheckSubjectSchedule": "subject_schedule_known",
                "CheckTimeSchedule": "time_schedule_known",
                "CheckCafeteriaMenu": "cafeteria_menu_known",
                "CheckBreakfastMenu": "breakfast_menu_known",
                "CheckLunchMenu": "lunch_menu_known",
                "CheckDinnerMenu": "dinner_menu_known",
                "CheckSnackMenu": "snack_menu_known",
                "SearchInternet": "internet_search_complete",
                "GenerateAttendancePDF": "attendance_pdf_sent",
                "GenerateTimetablePDF": "timetable_pdf_sent",
                "GenerateCafeteriaPDF": "cafeteria_pdf_sent",
                "Greeting": "greeting_responded",
                "SmallTalk": "smalltalk_responded",
                "Conversation": "conversation_responded"
            }
            
            goal_fact = intent_to_goal.get(primary_intent.name)
            if goal_fact:
                goal_state.add_goal(goal_fact)
            
            # For PDF generation intents, ensure recipient is set if user said "to me" or "email it to me"
            if primary_intent.name in pdf_intents:
                recipient = primary_intent.parameters.get("recipient", "")
                if not recipient or recipient.lower() in ["me", "my email", "myself", "to me", "send to me", "email it to me"]:
                    primary_intent.parameters["recipient"] = "me"  # Will use Config.USER_EMAIL
                    current_state.set_fact("recipient", "me")
                    current_state.set_fact("recipient_valid", True)
                    logger.info(f"Set recipient to 'me' for {primary_intent.name}")
            
            # Step 4: Planning
            # Skip planning for simple intents that can be executed directly
            simple_intents = ["AddTodo", "ListTodos", "CompleteTodo", "DeleteTodo"]
            if primary_intent.name in simple_intents:
                # Execute directly without planning
                logger.info(f"Executing {primary_intent.name} directly without planning")
                action_result = await self.action_executor.execute_action(
                    {"name": primary_intent.name},
                    primary_intent.parameters
                )
                
                if action_result.get("success"):
                    response = action_result.get("message", action_result.get("result", "Task completed successfully."))
                else:
                    error_msg = action_result.get("error", "Unknown error occurred.")
                    response = f"Sorry, I couldn't complete that task: {error_msg}"
                
                # Update conversation context
                if user_id not in self.conversation_context:
                    self.conversation_context[user_id] = {"conversation_history": []}
                
                # Extract and store class name from response if mentioned (for future reference resolution)
                class_match = None
                class_patterns_for_storage = [
                    r'lowest attendance.*?"([^"]+)"',
                    r'class with.*?lowest.*?"([^"]+)"',
                    r'"([^"]+)".*?\d+%.*?attendance',
                    r'attendance.*?"([^"]+)"'
                ]
                for pattern in class_patterns_for_storage:
                    match = re.search(pattern, response, re.IGNORECASE)
                    if match:
                        potential_class = match.group(1).strip()
                        if len(potential_class.split()) >= 2 and potential_class.lower() not in ['user input', 'bennett university']:
                            class_match = potential_class
                            break
                
                self.conversation_context[user_id]["conversation_history"].append({
                    "type": "user",
                    "text": command_text,
                    "timestamp": datetime.now().isoformat()
                })
                self.conversation_context[user_id]["conversation_history"].append({
                    "type": "bot",
                    "text": response,
                    "timestamp": datetime.now().isoformat()
                })
                
                if len(self.conversation_context[user_id]["conversation_history"]) > 10:
                    self.conversation_context[user_id]["conversation_history"] = \
                        self.conversation_context[user_id]["conversation_history"][-10:]
                
                context_update = {
                    "last_query": command_text,
                    "last_response": response,
                    "last_intent": primary_intent.name
                }
                
                # Store class name if found
                if class_match:
                    context_update["last_class_name"] = class_match
                    logger.info(f"Stored class name in context: {class_match}")
                
                self.conversation_context[user_id].update(context_update)
                
                # Check if user mentioned "email" or "mail" - automatically send response via email
                email_keywords = ["email", "mail", "send via email", "email me", "email it", "mail me", "mail it"]
                should_send_email = any(keyword in command_text.lower() for keyword in email_keywords)
                
                if should_send_email:
                    try:
                        # Extract recipient from command or use default
                        recipient = Config.USER_EMAIL
                        recipient_patterns = [
                            r'to\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                            r'email\s+to\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                            r'mail\s+to\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                        ]
                        for pattern in recipient_patterns:
                            match = re.search(pattern, command_text, re.IGNORECASE)
                            if match:
                                recipient = match.group(1)
                                break
                        
                        if not recipient:
                            response += "\n\nCould not send email: No recipient email configured. Please set USER_EMAIL in environment variables."
                        else:
                            # Format email content using OpenAI if available
                            email_body = response
                            email_subject = f"Response to: {command_text[:50]}"
                            
                            # Use OpenAI to format email nicely
                            try:
                                openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
                                format_response = openai_client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[
                                        {
                                            "role": "system",
                                            "content": "You are an email formatting assistant. Format the given content into a professional, well-structured email body. Keep it concise and easy to read. Don't add extra information, just format what's provided."
                                        },
                                        {
                                            "role": "user",
                                            "content": f"Format this content as an email body:\n\n{response}"
                                        }
                                    ],
                                    temperature=0.3,
                                    max_tokens=1000
                                )
                                email_body = format_response.choices[0].message.content.strip()
                                
                                # Generate subject from command
                                subject_response = openai_client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[
                                        {
                                            "role": "system",
                                            "content": "Generate a concise email subject line (max 10 words) based on the user's query."
                                        },
                                        {
                                            "role": "user",
                                            "content": command_text
                                        }
                                    ],
                                    temperature=0.3,
                                    max_tokens=20
                                )
                                email_subject = subject_response.choices[0].message.content.strip()
                            except Exception as e:
                                logger.warning(f"Error formatting email with OpenAI: {e}. Using original response.")
                                # Use original response if OpenAI formatting fails
                                email_body = response
                            
                            # Check if report is requested
                            has_report_keyword = any(keyword in command_text.lower() for keyword in ["report", "pdf"])
                            if has_report_keyword:
                                # For simple intents like todos, we might not have report data
                                # Check if user is asking for attendance/timetable/cafeteria report
                                report_type = None
                                if "attendance" in command_text.lower():
                                    report_type = "attendance"
                                elif "timetable" in command_text.lower() or "schedule" in command_text.lower():
                                    report_type = "timetable"
                                elif "cafeteria" in command_text.lower() or "menu" in command_text.lower():
                                    report_type = "cafeteria"
                                
                                if report_type:
                                    # Generate PDF based on type
                                    pdf_result = None
                                    if report_type == "attendance":
                                        attendance_result = await self.executor.erp_client.get_attendance()
                                        if attendance_result.get("success"):
                                            pdf_buffer = self.executor.pdf_generator.generate_attendance_pdf(attendance_result.get("raw_data"))
                                            pdf_bytes = pdf_buffer.read()
                                            filename = f"attendance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                                            pdf_result = await self.executor.email_client.send_email_with_pdf(
                                                recipient, email_subject, email_body, pdf_bytes, filename
                                            )
                                    elif report_type == "timetable":
                                        timetable_result = await self.executor.erp_client.get_timetable()
                                        if timetable_result.get("success"):
                                            pdf_buffer = self.executor.pdf_generator.generate_timetable_pdf(timetable_result.get("raw_data"))
                                            pdf_bytes = pdf_buffer.read()
                                            filename = f"timetable_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                                            pdf_result = await self.executor.email_client.send_email_with_pdf(
                                                recipient, email_subject, email_body, pdf_bytes, filename
                                            )
                                    elif report_type == "cafeteria":
                                        cafeteria_result = await self.executor.erp_client.get_cafeteria_menu()
                                        if cafeteria_result.get("success"):
                                            pdf_buffer = self.executor.pdf_generator.generate_cafeteria_pdf(cafeteria_result.get("raw_data"))
                                            pdf_bytes = pdf_buffer.read()
                                            filename = f"cafeteria_menu_{datetime.now().strftime('%Y%m%d')}.pdf"
                                            pdf_result = await self.executor.email_client.send_email_with_pdf(
                                                recipient, email_subject, email_body, pdf_bytes, filename
                                            )
                                    
                                    if pdf_result and pdf_result.get("success"):
                                        response += f"\n\nEmail sent successfully to {recipient} with PDF report attached."
                                    elif pdf_result:
                                        response += f"\n\nCould not send email: {pdf_result.get('error', 'Unknown error')}"
                                    else:
                                        # Fallback to regular email if PDF generation fails
                                        email_result = await self.executor.email_client.send_email(recipient, email_subject, email_body)
                                        if email_result.get("success"):
                                            response += f"\n\nEmail sent successfully to {recipient}."
                                        else:
                                            response += f"\n\nCould not send email: {email_result.get('error', 'Unknown error')}"
                                else:
                                    # No specific report type, just send regular email
                                    email_result = await self.executor.email_client.send_email(recipient, email_subject, email_body)
                                    if email_result.get("success"):
                                        response += f"\n\nEmail sent successfully to {recipient}."
                                    else:
                                        response += f"\n\nCould not send email: {email_result.get('error', 'Unknown error')}"
                            else:
                                # Regular email (no PDF)
                                email_result = await self.executor.email_client.send_email(recipient, email_subject, email_body)
                                if email_result.get("success"):
                                    response += f"\n\nEmail sent successfully to {recipient}."
                                else:
                                    response += f"\n\nCould not send email: {email_result.get('error', 'Unknown error')}"
                    except Exception as e:
                        logger.error(f"Error sending email: {e}", exc_info=True)
                        response += f"\n\nError sending email: {str(e)}"
                
                return response
            
            # Continue with planning for non-simple intents
            import time
            planning_start = time.time()
            
            # Debug: Log state and goals
            logger.debug(f"Current state facts: {current_state.facts}")
            logger.debug(f"Goal state goals: {goal_state.goals}")
            logger.debug(f"Goal satisfied check: {current_state.is_goal_satisfied('weather_known') if 'weather_known' in goal_state.goals else 'N/A'}")
            
            plan = self.planner.plan(current_state, goal_state)
            planning_time = time.time() - planning_start
            
            logger.info(f"Generated plan with {len(plan)} actions")
            logger.debug(f"Plan details: {[a.get('name') for a in plan]}")
            
            if not plan:
                # Provide more helpful error message based on intent
                if primary_intent.name == "CheckSubjectAttendance":
                    subject_param = primary_intent.parameters.get("subject", "unspecified")
                    return (
                        f"I couldn't find attendance information for '{subject_param}'. "
                        f"Please specify the subject more clearly. For example:\n"
                        f"• 'Attendance for CSET381'\n"
                        f"• 'CSET381 attendance'\n"
                        f"• 'Attendance in Applications of AI'"
                    )
                elif primary_intent.name == "CheckSubjectSchedule":
                    subject_param = primary_intent.parameters.get("subject", "unspecified")
                    return (
                        f"I couldn't find schedule information for '{subject_param}'. "
                        f"Please specify the subject more clearly. For example:\n"
                        f"• 'When is CSET305'\n"
                        f"• 'CSET305 schedule'\n"
                        f"• 'Schedule for High Performance Computing'"
                    )
                else:
                    return (
                        f"I couldn't create a plan to fulfill your request. "
                        f"Your intent was understood as: {primary_intent.name}. "
                        f"Please provide more details or try rephrasing."
                    )
            
            # Log planning decision
            await self.audit_logger.log_planning_decision(
                session_id=session_id,
                plan=plan,
                initial_state=current_state.facts,
                goal_state=goal_state.facts,
                planning_time=planning_time
            )
            
            # Step 5: Generate Explanation
            explanation = self.explainer.explain_plan(plan, primary_intent.name)
            
            # Step 6: Execute Plan
            execution_results = await self.executor.execute_plan(
                plan,
                primary_intent.parameters
            )
            
            # Log execution
            for result in execution_results:
                await self.audit_logger.log_action_execution(
                    session_id=session_id,
                    action={"name": result["action"]},
                    result=result["result"]
                )
            
            # Check if this is a detailed request or follow-up for ERP-related intents
            erp_intents = [
                "CheckAttendance", "CheckSubjectAttendance", "CheckMonthlyAttendance",
                "CheckTimetable", "CheckSubjectSchedule", "CheckTimeSchedule",
                "CheckCafeteriaMenu", "CheckBreakfastMenu", "CheckLunchMenu",
                "CheckDinnerMenu", "CheckSnackMenu"
            ]
            
            # Determine data_type from intent name (for context storage)
            data_type = None
            if primary_intent.name in erp_intents:
                if "attendance" in primary_intent.name.lower():
                    data_type = "attendance"
                elif "timetable" in primary_intent.name.lower() or "schedule" in primary_intent.name.lower():
                    data_type = "timetable"
                elif "cafeteria" in primary_intent.name.lower() or "menu" in primary_intent.name.lower():
                    data_type = "cafeteria"
            
            is_detailed = is_detailed_request(command_text)
            should_use_openai = (is_detailed or is_followup) and primary_intent.name in erp_intents
            
            if should_use_openai:
                # Find the ERP data from execution results
                json_data = None
                # data_type already determined above, but may be refined from action name
                
                for result in execution_results:
                    action_name = result.get("action", "")
                    execution_result = result.get("result", {})
                    
                    # Get raw_data if available
                    if isinstance(execution_result, dict) and "raw_data" in execution_result:
                        json_data = execution_result["raw_data"]
                        
                        # Determine data type
                        if "attendance" in action_name.lower():
                            data_type = "attendance"
                        elif "timetable" in action_name.lower() or "schedule" in action_name.lower():
                            data_type = "timetable"
                        elif "cafeteria" in action_name.lower() or "menu" in action_name.lower():
                            data_type = "cafeteria"
                        
                        if json_data:
                            break
                
                # If no raw_data, try to get from user context (for follow-ups)
                if not json_data and is_followup and user_context.get("last_data"):
                    json_data = user_context.get("last_data")
                    data_type = user_context.get("last_data_type", "attendance")
                
                # Process with OpenAI if we have data
                if json_data:
                    ai_response = await self._process_with_openai(
                        command_text,
                        json_data,
                        data_type,
                        user_context if is_followup else None
                    )
                    
                    if ai_response:
                        response = ai_response
                    else:
                        # Fallback to normal formatting
                        execution_summary = self.explainer.format_execution_results(execution_results)
                        if explanation and explanation.strip():
                            response = f"{explanation}\n\n{execution_summary}"
                        else:
                            response = execution_summary
                else:
                    # No JSON data available, use normal formatting
                    execution_summary = self.explainer.format_execution_results(execution_results)
                    if explanation and explanation.strip():
                        response = f"{explanation}\n\n{execution_summary}"
                    else:
                        response = execution_summary
            else:
                # Normal request - use formatted response
                execution_summary = self.explainer.format_execution_results(execution_results)
                
                # Combine explanation and results smoothly
                if explanation and explanation.strip():
                    # Only include explanation if it's meaningful (multi-step plans)
                    response = f"{explanation}\n\n{execution_summary}"
                else:
                    # For single actions, just show results directly
                    response = execution_summary
            
            # Update conversation context for all intents (for better conversation flow)
            if user_id not in self.conversation_context:
                self.conversation_context[user_id] = {"conversation_history": []}
            
            # Add to conversation history (consistent format with simple intents)
            self.conversation_context[user_id]["conversation_history"].append({
                "type": "user",
                "text": command_text,
                "timestamp": datetime.now().isoformat()
            })
            self.conversation_context[user_id]["conversation_history"].append({
                "type": "bot",
                "text": response,
                "timestamp": datetime.now().isoformat()
            })
            # Keep only last 10 exchanges
            if len(self.conversation_context[user_id]["conversation_history"]) > 10:
                self.conversation_context[user_id]["conversation_history"] = \
                    self.conversation_context[user_id]["conversation_history"][-10:]
            
            # Store last query and response for all intents (for follow-up context, especially SearchInternet)
            # This allows follow-up questions to access previous context
            self.conversation_context[user_id].update({
                "last_query": command_text,
                "last_response": response
            })
            
            # Update conversation context for ERP intents (for follow-ups)
            if primary_intent.name in erp_intents:
                # Store context for follow-ups
                json_data_for_context = None
                for result in execution_results:
                    execution_result = result.get("result", {})
                    if isinstance(execution_result, dict) and "raw_data" in execution_result:
                        json_data_for_context = execution_result["raw_data"]
                        break
                
                if json_data_for_context:
                    # Determine data_type from intent name if not already set
                    if not data_type:
                        if "attendance" in primary_intent.name.lower():
                            data_type = "attendance"
                        elif "timetable" in primary_intent.name.lower() or "schedule" in primary_intent.name.lower():
                            data_type = "timetable"
                        elif "cafeteria" in primary_intent.name.lower() or "menu" in primary_intent.name.lower():
                            data_type = "cafeteria"
                        else:
                            data_type = "attendance"  # Default fallback
                    
                    self.conversation_context[user_id].update({
                        "last_intent": primary_intent.name,
                        "last_data": json_data_for_context,
                        "last_response": response,
                        "last_query": command_text,
                        "last_data_type": data_type
                    })
            
            # Check if user mentioned "email" or "mail" - automatically send response via email
            email_keywords = ["email", "mail", "send via email", "email me", "email it", "mail me", "mail it"]
            should_send_email = any(keyword in command_text.lower() for keyword in email_keywords)
            
            # Check if email was already sent by PDF generation intent
            # PDF generation intents always send emails and return messages like "PDF report sent to..."
            pdf_intents = ["GenerateAttendancePDF", "GenerateTimetablePDF", "GenerateCafeteriaPDF"]
            email_already_sent = (
                primary_intent.name in pdf_intents or
                any(indicator in response.lower() for indicator in [
                    "pdf report sent", "report sent to", "sent to", "email sent", 
                    "attendance pdf report sent", "timetable pdf report sent", 
                    "cafeteria pdf report sent", "email sent successfully",
                    "pdf report sent to", "email with pdf successfully sent",
                    "attendance pdf report sent to", "timetable pdf report sent to",
                    "cafeteria pdf report sent to"
                ])
            )
            
            # Check if "report" is mentioned along with email - generate PDF
            has_report_keyword = any(keyword in command_text.lower() for keyword in ["report", "pdf"])
            should_generate_pdf = has_report_keyword and should_send_email
            
            # Handle email sending (skip if email already sent by PDF generation intent)
            if should_send_email and not email_already_sent:
                try:
                    # Extract recipient from command or use default
                    recipient = Config.USER_EMAIL
                    recipient_patterns = [
                        r'to\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                        r'email\s+to\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                        r'mail\s+to\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                    ]
                    for pattern in recipient_patterns:
                        match = re.search(pattern, command_text, re.IGNORECASE)
                        if match:
                            recipient = match.group(1)
                            break
                    
                    if not recipient:
                        response += "\n\n⚠️ Could not send email: No recipient email configured. Please set USER_EMAIL in environment variables."
                    else:
                        # Format email content using OpenAI if available
                        email_body = response
                        email_subject = f"Response to: {command_text[:50]}"
                        
                        # Use OpenAI to format email nicely
                        try:
                            openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
                            format_response = openai_client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {
                                        "role": "system",
                                        "content": "You are an email formatting assistant. Format the given content into a professional, well-structured email body. Keep it concise and easy to read. Don't add extra information, just format what's provided."
                                    },
                                    {
                                        "role": "user",
                                        "content": f"Format this content as an email body:\n\n{response}"
                                    }
                                ],
                                temperature=0.3,
                                max_tokens=1000
                            )
                            email_body = format_response.choices[0].message.content.strip()
                            
                            # Generate subject from command
                            subject_response = openai_client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {
                                        "role": "system",
                                        "content": "Generate a concise email subject line (max 10 words) based on the user's query."
                                    },
                                    {
                                        "role": "user",
                                        "content": command_text
                                    }
                                ],
                                temperature=0.3,
                                max_tokens=20
                            )
                            email_subject = subject_response.choices[0].message.content.strip()
                        except Exception as e:
                            logger.warning(f"Error formatting email with OpenAI: {e}. Using original response.")
                            # Use original response if OpenAI formatting fails
                            email_body = response
                        
                        # If report is requested, generate PDF and email it
                        if should_generate_pdf:
                            # Determine which type of report based on intent or command
                            report_type = None
                            if "attendance" in command_text.lower() or primary_intent.name in ["CheckAttendance", "CheckSubjectAttendance", "CheckMonthlyAttendance"]:
                                report_type = "attendance"
                            elif "timetable" in command_text.lower() or "schedule" in command_text.lower() or primary_intent.name in ["CheckTimetable", "CheckSubjectSchedule"]:
                                report_type = "timetable"
                            elif "cafeteria" in command_text.lower() or "menu" in command_text.lower() or primary_intent.name in ["CheckCafeteriaMenu"]:
                                report_type = "cafeteria"
                            
                            if report_type:
                                # Generate PDF based on type
                                pdf_result = None
                                if report_type == "attendance":
                                    attendance_result = await self.executor.erp_client.get_attendance()
                                    if attendance_result.get("success"):
                                        pdf_buffer = self.executor.pdf_generator.generate_attendance_pdf(attendance_result.get("raw_data"))
                                        pdf_bytes = pdf_buffer.read()
                                        filename = f"attendance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                                        pdf_result = await self.executor.email_client.send_email_with_pdf(
                                            recipient, email_subject, email_body, pdf_bytes, filename
                                        )
                                elif report_type == "timetable":
                                    timetable_result = await self.executor.erp_client.get_timetable()
                                    if timetable_result.get("success"):
                                        pdf_buffer = self.executor.pdf_generator.generate_timetable_pdf(timetable_result.get("raw_data"))
                                        pdf_bytes = pdf_buffer.read()
                                        filename = f"timetable_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                                        pdf_result = await self.executor.email_client.send_email_with_pdf(
                                            recipient, email_subject, email_body, pdf_bytes, filename
                                        )
                                elif report_type == "cafeteria":
                                    cafeteria_result = await self.executor.erp_client.get_cafeteria_menu()
                                    if cafeteria_result.get("success"):
                                        pdf_buffer = self.executor.pdf_generator.generate_cafeteria_pdf(cafeteria_result.get("raw_data"))
                                        pdf_bytes = pdf_buffer.read()
                                        filename = f"cafeteria_menu_{datetime.now().strftime('%Y%m%d')}.pdf"
                                        pdf_result = await self.executor.email_client.send_email_with_pdf(
                                            recipient, email_subject, email_body, pdf_bytes, filename
                                        )
                                
                                if pdf_result and pdf_result.get("success"):
                                    response += f"\n\nEmail sent successfully to {recipient} with PDF report attached."
                                elif pdf_result:
                                    response += f"\n\nCould not send email: {pdf_result.get('error', 'Unknown error')}"
                                else:
                                    response += f"\n\nCould not generate report: Failed to fetch {report_type} data."
                            else:
                                # No specific report type, just send regular email
                                email_result = await self.executor.email_client.send_email(recipient, email_subject, email_body)
                                if email_result.get("success"):
                                    response += f"\n\nEmail sent successfully to {recipient}."
                                else:
                                    response += f"\n\nCould not send email: {email_result.get('error', 'Unknown error')}"
                        else:
                            # Regular email (no PDF)
                            email_result = await self.executor.email_client.send_email(recipient, email_subject, email_body)
                            if email_result.get("success"):
                                response += f"\n\n✅ Email sent successfully to {recipient}."
                            else:
                                response += f"\n\n⚠️ Could not send email: {email_result.get('error', 'Unknown error')}"
                except Exception as e:
                    logger.error(f"Error sending email: {e}", exc_info=True)
                    response += f"\n\nError sending email: {str(e)}"
            
            # Save interaction history
            await self.db.save_interaction_history(
                user_id=str(user_id),
                intent=primary_intent.name,
                command_text=command_text,
                response_text=response,
                plan=[{"name": a.get("name")} for a in plan],
                success=all(r["result"].get("success", False) for r in execution_results)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing command: {e}", exc_info=True)
            return f"Sorry, I encountered an error: {str(e)}"
    
    def get_welcome_message(self) -> str:
        """Get the welcome message text."""
        return (
            "Welcome to Talky!\n\n"
            "I'm a voice-driven intelligent agent that can help you with various tasks:\n"
            "• Check weather\n"
            "• Search the internet\n"
            "• Send emails\n"
            "• Check attendance\n"
            "• Check timetable\n"
            "• Check cafeteria menu\n"
            "• Book hotels\n"
            "• Set reminders\n"
            "• Search flights\n"
            "• Create calendar events\n"
            "• Plan trips\n\n"
            "You can send me voice messages or text commands. "
            "Try saying: 'Check weather in Mumbai'"
        )
    
    async def start_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        welcome_message = self.get_welcome_message()
        await update.message.reply_text(welcome_message)
    
    async def help_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command."""
        help_message = (
            "Talky Help\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n\n"
            "Examples:\n"
            "• 'Check weather in Mumbai'\n"
            "• 'Set a reminder for tomorrow at 10 AM'\n"
            "• 'Plan a trip to Delhi for this weekend'\n\n"
            "You can use voice messages or text!"
        )
        await update.message.reply_text(help_message)


async def post_init(application: Application) -> None:
    """Send welcome message on bot startup."""
    try:
        # Get startup chat ID from config (optional)
        startup_chat_id = os.getenv("STARTUP_CHAT_ID", "")
        if startup_chat_id:
            try:
                chat_id = int(startup_chat_id)
                welcome_message = (
                    "Welcome to Talky!\n\n"
                    "I'm a voice-driven intelligent agent that can help you with various tasks:\n"
                    "• Check weather\n"
                    "• Search the internet\n"
                    "• Send emails\n"
                    "• Check attendance\n"
                    "• Check timetable\n"
                    "• Check cafeteria menu\n"
                    "• Book hotels\n"
                    "• Set reminders\n"
                    "• Search flights\n"
                    "• Create calendar events\n"
                    "• Plan trips\n\n"
                    "You can send me voice messages or text commands. "
                    "Try saying: 'Check weather in Mumbai'"
                )
                await application.bot.send_message(chat_id=chat_id, text=welcome_message)
                logger.info(f"Startup welcome message sent to chat {chat_id}")
            except ValueError:
                logger.warning(f"Invalid STARTUP_CHAT_ID format: {startup_chat_id}. Should be a numeric chat ID.")
            except Exception as e:
                logger.warning(f"Could not send startup message: {e}")
        else:
            logger.info("STARTUP_CHAT_ID not set. Skipping startup message. (Set STARTUP_CHAT_ID in .env to enable)")
    except Exception as e:
        logger.warning(f"Error in post_init: {e}")


def main():
    """Main function to start the bot."""
    if not Config.validate():
        missing = Config.get_missing_config()
        logger.error(f"Missing required configuration: {', '.join(missing)}")
        logger.error("Please set the required environment variables in .env file")
        return
    
    # Create bot instance
    bot = TalkyBot()
    
    # Create application
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(MessageHandler(filters.VOICE, bot.handle_voice_message))
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_image_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text_message))
    
    # Start bot
    logger.info("Starting Talky bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

