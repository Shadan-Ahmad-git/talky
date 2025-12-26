"""
Probabilistic Intent Classification using GPT-4.
Handles ambiguity, multi-intent scenarios, and confidence scoring.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import Config
from nlp.nlp_utils import extract_entities, normalize_text

logger = logging.getLogger(__name__)


class Intent:
    """Represents a detected intent with confidence score."""
    
    def __init__(
        self, 
        name: str, 
        confidence: float, 
        parameters: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.confidence = confidence
        self.parameters = parameters or {}
    
    def __repr__(self):
        return f"Intent(name={self.name}, confidence={self.confidence:.2f})"


class IntentClassifier:
    """Probabilistic intent classifier using GPT-4."""
    
    # Defined intents and their descriptions
    AVAILABLE_INTENTS = {
        "CheckWeather": {
            "description": "Check weather conditions for a location",
            "parameters": ["location"],
            "examples": ["check weather", "what's the weather", "weather in mumbai"]
        },
        "SendEmail": {
            "description": "Send an email to a recipient. Classify as SendEmail if the user explicitly mentions 'email' or 'mail' in their message. This includes requests to email responses, reports, or any information.",
            "parameters": ["recipient", "subject", "body"],
            "examples": ["send email", "email someone", "send mail", "email to professor", "email me", "email it", "mail me", "mail it", "send via email", "email the response"]
        },
        "BookHotel": {
            "description": "Book a hotel room",
            "parameters": ["location", "check_in", "check_out", "guests"],
            "examples": ["book hotel", "find hotel", "reserve room"]
        },
        "SetReminder": {
            "description": "Set a time-based reminder or alarm with a specific datetime. DO NOT classify 'add reminder' without a time as SetReminder - use AddTodo instead.",
            "parameters": ["datetime", "message"],
            "examples": ["set reminder for 3pm", "remind me at 10am", "create alarm for tomorrow", "reminder at 5pm"]
        },
        "SearchFlights": {
            "description": "Search for flight options",
            "parameters": ["origin", "destination", "date"],
            "examples": ["find flights", "search flights", "book flight"]
        },
        "CreateCalendarEvent": {
            "description": "Create a calendar event",
            "parameters": ["title", "datetime", "duration"],
            "examples": ["add to calendar", "create event", "schedule meeting"]
        },
        "PlanTrip": {
            "description": "Plan a multi-step trip",
            "parameters": ["location", "date", "duration"],
            "examples": ["plan trip", "organize travel", "trip planning"]
        },
        "CheckAttendance": {
            "description": "Check overall student attendance records",
            "parameters": [],
            "examples": ["check attendance", "my attendance", "attendance report", "overall attendance", "show attendance"]
        },
        "GenerateAttendancePDF": {
            "description": "Generate and send PDF report for attendance",
            "parameters": [],
            "examples": ["attendance pdf", "send attendance report", "attendance report pdf", "generate attendance pdf", "email attendance report"]
        },
        "GenerateTimetablePDF": {
            "description": "Generate and send PDF report for timetable",
            "parameters": ["date"],
            "examples": ["timetable pdf", "send timetable report", "timetable report pdf", "generate timetable pdf", "email timetable report"]
        },
        "GenerateCafeteriaPDF": {
            "description": "Generate and send PDF report for cafeteria menu",
            "parameters": [],
            "examples": ["cafeteria pdf", "menu pdf", "send menu report", "cafeteria report pdf", "generate menu pdf", "email menu report"]
        },
        "CheckSubjectAttendance": {
            "description": "Check attendance for a specific subject",
            "parameters": ["subject"],
            "examples": ["attendance for CSET208", "how many classes attended in CSET305", "CSET324 attendance", "attendance in Automata Theory"]
        },
        "CheckMonthlyAttendance": {
            "description": "Check this month's attendance",
            "parameters": [],
            "examples": ["this month attendance", "monthly attendance", "attendance this month", "current month attendance"]
        },
        "CheckTimetable": {
            "description": "Check full class timetable or schedule",
            "parameters": ["date"],
            "examples": ["timetable", "schedule", "today's classes", "class schedule", "what classes today", "show timetable"]
        },
        "CheckSubjectSchedule": {
            "description": "Find when a specific subject is scheduled",
            "parameters": ["subject"],
            "examples": ["when is CSET305", "CSET208 schedule", "when is Automata Theory", "time for High Performance Computing"]
        },
        "CheckTimeSchedule": {
            "description": "Find what subject is scheduled at a specific time",
            "parameters": ["time"],
            "examples": ["what class at 10 am", "subject at 2 pm", "what's at 9:30", "class at 11:00"]
        },
        "CheckCafeteriaMenu": {
            "description": "Check full cafeteria or mess menu",
            "parameters": [],
            "examples": ["cafeteria menu", "mess menu", "today's menu", "full menu", "food menu"]
        },
        "CheckBreakfastMenu": {
            "description": "Check breakfast menu",
            "parameters": [],
            "examples": ["what's for breakfast", "breakfast menu", "breakfast today", "morning food"]
        },
        "CheckLunchMenu": {
            "description": "Check lunch menu",
            "parameters": [],
            "examples": ["what's for lunch", "lunch menu", "lunch today", "afternoon food"]
        },
        "CheckDinnerMenu": {
            "description": "Check dinner menu",
            "parameters": [],
            "examples": ["what's for dinner", "dinner menu", "dinner tonight", "evening food", "tonight's dinner"]
        },
        "CheckSnackMenu": {
            "description": "Check snack menu",
            "parameters": [],
            "examples": ["what's for snack", "snack menu", "evening snack", "snacks today"]
        },
        "SearchInternet": {
            "description": "Search the internet for information on a topic",
            "parameters": ["query"],
            "examples": [
                "search the internet for",
                "search for",
                "look up",
                "find information about",
                "what is",
                "tell me about",
                "search online for",
                "internet search for"
            ]
        },
        "Greeting": {
            "description": "Greeting or casual conversation",
            "parameters": [],
            "examples": [
                "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
                "how are you", "what's up", "how's it going", "nice to meet you",
                "greetings", "sup", "hey there", "good day"
            ]
        },
        "SmallTalk": {
            "description": "Casual conversation, small talk, or chit-chat",
            "parameters": [],
            "examples": [
                "how are you doing", "what's going on", "tell me about yourself",
                "what can you do", "who are you", "thanks", "thank you",
                "appreciate it", "goodbye", "bye", "see you later", "talk to you later"
            ]
        },
        "Conversation": {
            "description": "General conversation that requires nuanced understanding",
            "parameters": [],
            "examples": [
                "tell me more", "that's interesting", "what do you think",
                "explain further", "why do you say that", "what's your opinion"
            ]
        },
        "AddTodo": {
            "description": "Add a new todo item or task to the todo list. This includes reminders and tasks the user wants to track.",
            "parameters": ["task"],
            "examples": [
                "add todo", "create task", "add task", "new todo", 
                "remember to", "remind me to", "add reminder", 
                "add to todo list", "add to my todo", "add to my todo list",
                "create reminder", "set a todo", "make a todo"
            ]
        },
        "ListTodos": {
            "description": "List all todos or show todo list",
            "parameters": [],
            "examples": ["show todos", "list tasks", "my todos", "what are my todos", "show my tasks"]
        },
        "CompleteTodo": {
            "description": "Mark a todo as completed or done",
            "parameters": ["task_number", "task"],
            "examples": ["complete todo", "mark done", "finish task", "todo done", "complete task"]
        },
        "DeleteTodo": {
            "description": "Delete or remove a todo item",
            "parameters": ["task_number", "task"],
            "examples": ["delete todo", "remove task", "cancel todo", "delete task"]
        },
        "Unknown": {
            "description": "Unclear or unknown intent",
            "parameters": [],
            "examples": []
        }
    }
    
    def __init__(self):
        """Initialize intent classifier with OpenAI client."""
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info("Intent Classifier initialized")
    
    async def classify_intent(self, text: str) -> List[Intent]:
        """
        Classify user intent from text using probabilistic reasoning.
        
        Args:
            text: User input text
            
        Returns:
            List of Intent objects sorted by confidence (highest first)
        """
        try:
            normalized_text = normalize_text(text)
            
            # Build prompt for GPT-4
            prompt = self._build_classification_prompt(normalized_text)
            
            # Call GPT-4 API
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an intent classification system. Analyze user commands and identify their intent with confidence scores."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3  # Lower temperature for more consistent classification
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Convert to Intent objects
            intents = []
            if isinstance(result, dict):
                if "intents" in result:
                    for intent_data in result["intents"]:
                        intent = Intent(
                            name=intent_data.get("name", "Unknown"),
                            confidence=float(intent_data.get("confidence", 0.0)) / 100.0,
                            parameters=intent_data.get("parameters", {})
                        )
                        intents.append(intent)
                elif "name" in result:
                    # Single intent response
                    intent = Intent(
                        name=result.get("name", "Unknown"),
                        confidence=float(result.get("confidence", 0.0)) / 100.0,
                        parameters=result.get("parameters", {})
                    )
                    intents.append(intent)
            
            # Fallback if no intents found
            if not intents:
                intents.append(Intent("Unknown", 0.5))
            
            # Sort by confidence
            intents.sort(key=lambda x: x.confidence, reverse=True)
            
            # Extract additional parameters using NLP utils
            for intent in intents:
                if not intent.parameters:
                    intent.parameters = extract_entities(
                        text, 
                        self.AVAILABLE_INTENTS.get(intent.name, {}).get("parameters", [])
                    )
            
            logger.info(f"Classified intent: {intents[0].name} (confidence: {intents[0].confidence:.2f})")
            return intents
            
        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return [Intent("Unknown", 0.0)]
    
    def _build_classification_prompt(self, text: str) -> str:
        """Build classification prompt for GPT-4."""
        intents_json = json.dumps(self.AVAILABLE_INTENTS, indent=2)
        
        prompt = f"""Analyze the following user command and identify the intent(s) with confidence scores (0-100).

Available intents:
{intents_json}

User command: "{text}"

IMPORTANT RULES:
1. For SendEmail intent: ONLY classify as SendEmail if the user explicitly mentions "email" or "mail" AND wants to send/compose an email. Do NOT classify queries about attendance emails, timetable emails, or cafeteria menu emails as SendEmail.
2. Be strict with SendEmail - it should only be for composing/sending emails, not for checking or requesting email-related information.

Return a JSON object with the following structure:
{{
    "intents": [
        {{
            "name": "IntentName",
            "confidence": 85,
            "parameters": {{"param1": "value1"}}
        }}
    ]
}}

If multiple intents are present, include all of them. If intent is unclear, use "Unknown" with low confidence.
Focus on the primary intent first, but identify secondary intents if present.
"""
        return prompt
    
    def handle_ambiguity(self, intents: List[Intent]) -> Optional[Intent]:
        """
        Handle ambiguous intent scenarios.
        
        Args:
            intents: List of candidate intents
            
        Returns:
            Resolved intent or None if clarification needed
        """
        if not intents:
            return None
        
        # If single intent with high confidence, return it
        if len(intents) == 1 and intents[0].confidence > 0.7:
            return intents[0]
        
        # Special handling for similar/compatible intents
        conversational_intents = ["Greeting", "SmallTalk", "Conversation"]
        
        # If all intents are conversational (compatible), pick highest confidence
        if len(intents) > 1 and all(i.name in conversational_intents for i in intents):
            return max(intents, key=lambda x: x.confidence)
        
        # If top intent has significantly higher confidence, return it
        if len(intents) > 1:
            top_confidence = intents[0].confidence
            second_confidence = intents[1].confidence
            
            # Lower threshold for conversational intents (they're similar)
            if intents[0].name in conversational_intents:
                threshold = 0.1  # Lower threshold for conversational
            else:
                threshold = 0.2  # Normal threshold for other intents
            
            if top_confidence - second_confidence > threshold:
                return intents[0]
        
        # If top intent has decent confidence (>0.75) and others are much lower, use it
        if len(intents) > 1 and intents[0].confidence > 0.75:
            if intents[1].confidence < 0.6:  # Second intent is much lower
                return intents[0]
        
        # Ambiguity detected
        return None
    
    def ask_clarification(self, ambiguous_intents: List[Intent]) -> str:
        """
        Generate clarification question for ambiguous intents.
        
        Args:
            ambiguous_intents: List of ambiguous intents
            
        Returns:
            Clarification question text
        """
        if len(ambiguous_intents) == 0:
            return "I didn't understand. Could you please rephrase?"
        
        intent_names = [intent.name for intent in ambiguous_intents[:3]]
        return f"I detected multiple possible intents: {', '.join(intent_names)}. Could you clarify what you'd like me to do?"
    
    def manage_multi_intent_scenarios(self, intents: List[Intent]) -> List[Intent]:
        """
        Handle scenarios with multiple simultaneous intents.
        
        Args:
            intents: List of detected intents
            
        Returns:
            Filtered list of valid multi-intents
        """
        # Filter intents with confidence > 0.6
        valid_intents = [intent for intent in intents if intent.confidence > 0.6]
        
        # Limit to top 3 intents
        return valid_intents[:3]
    
    def calculate_confidence(self, intent: Intent, text: str) -> float:
        """
        Recalculate confidence score based on text analysis.
        
        Args:
            intent: Intent object
            text: Original text
            
        Returns:
            Updated confidence score
        """
        # Base confidence from classification
        base_confidence = intent.confidence
        
        # Boost confidence if required parameters are present
        required_params = self.AVAILABLE_INTENTS.get(intent.name, {}).get("parameters", [])
        if required_params:
            extracted_params = extract_entities(text, required_params)
            param_coverage = len(extracted_params) / len(required_params)
            base_confidence = (base_confidence + param_coverage) / 2
        
        return min(base_confidence, 1.0)

