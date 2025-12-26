"""
Knowledge base defining agent's possible actions.
Contains action definitions with preconditions, effects, and costs.
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Knowledge base containing action definitions."""
    
    def __init__(self):
        """Initialize knowledge base with action definitions."""
        self.actions = self._initialize_actions()
        logger.info(f"Knowledge Base initialized with {len(self.actions)} actions")
    
    def _initialize_actions(self) -> List[Dict[str, Any]]:
        """Initialize the action knowledge base."""
        return [
            {
                "name": "CheckWeather",
                "parameters": ["location"],
                "preconditions": {"location_valid": True},
                "effects": {"weather_known": True, "weather_location": None},
                "cost": 1.0,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "weather_service",
                "description": "Check weather conditions for a location"
            },
            {
                "name": "SendEmail",
                "parameters": ["recipient", "subject", "body"],
                "preconditions": {"recipient_valid": True, "email_content_ready": True},
                "effects": {"email_sent": True},
                "cost": 2.0,
                "execution_time": 3.0,
                "dependencies": [],
                "api_endpoint": "email_service",
                "description": "Send an email to a recipient"
            },
            {
                "name": "BookHotel",
                "parameters": ["location", "check_in", "check_out", "guests"],
                "preconditions": {"location_valid": True, "dates_valid": True},
                "effects": {"hotel_booked": True},
                "cost": 5.0,
                "execution_time": 10.0,
                "dependencies": ["CheckWeather"],  # Optional dependency
                "api_endpoint": "hotel_service",
                "description": "Book a hotel room"
            },
            {
                "name": "SetReminder",
                "parameters": ["datetime", "message"],
                "preconditions": {"datetime_valid": True},
                "effects": {"reminder_set": True},
                "cost": 1.0,
                "execution_time": 1.0,
                "dependencies": [],
                "api_endpoint": "reminder_service",
                "description": "Set a reminder or alarm"
            },
            {
                "name": "SearchFlights",
                "parameters": ["origin", "destination", "date"],
                "preconditions": {"origin_valid": True, "destination_valid": True, "date_valid": True},
                "effects": {"flights_found": True},
                "cost": 3.0,
                "execution_time": 5.0,
                "dependencies": [],
                "api_endpoint": "flight_service",
                "description": "Search for flight options"
            },
            {
                "name": "CreateCalendarEvent",
                "parameters": ["title", "datetime", "duration"],
                "preconditions": {"datetime_valid": True, "title_provided": True},
                "effects": {"calendar_event_created": True},
                "cost": 1.5,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "calendar_service",
                "description": "Create a calendar event"
            },
            {
                "name": "PlanTrip",
                "parameters": ["location", "date", "duration"],
                "preconditions": {"location_valid": True, "date_valid": True},
                "effects": {"trip_planned": True},
                "cost": 8.0,
                "execution_time": 15.0,
                "dependencies": ["CheckWeather", "SearchFlights", "BookHotel"],
                "api_endpoint": "trip_planning_service",
                "description": "Plan a multi-step trip"
            },
            {
                "name": "CheckAttendance",
                "parameters": [],
                "preconditions": {},
                "effects": {"attendance_known": True},
                "cost": 2.0,
                "execution_time": 3.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Check overall student attendance records"
            },
            {
                "name": "CheckSubjectAttendance",
                "parameters": ["subject"],
                "preconditions": {},
                "effects": {"subject_attendance_known": True},
                "cost": 1.5,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Check attendance for a specific subject"
            },
            {
                "name": "CheckMonthlyAttendance",
                "parameters": [],
                "preconditions": {},
                "effects": {"monthly_attendance_known": True},
                "cost": 1.5,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Check this month's attendance"
            },
            {
                "name": "CheckTimetable",
                "parameters": ["date"],
                "preconditions": {},
                "effects": {"timetable_known": True},
                "cost": 2.0,
                "execution_time": 3.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Check full class timetable or schedule"
            },
            {
                "name": "CheckSubjectSchedule",
                "parameters": ["subject"],
                "preconditions": {},
                "effects": {"subject_schedule_known": True},
                "cost": 1.5,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Find when a specific subject is scheduled"
            },
            {
                "name": "CheckTimeSchedule",
                "parameters": ["time"],
                "preconditions": {},
                "effects": {"time_schedule_known": True},
                "cost": 1.5,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Find what subject is scheduled at a specific time"
            },
            {
                "name": "CheckCafeteriaMenu",
                "parameters": [],
                "preconditions": {},
                "effects": {"cafeteria_menu_known": True},
                "cost": 1.5,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Check full cafeteria or mess menu"
            },
            {
                "name": "CheckBreakfastMenu",
                "parameters": [],
                "preconditions": {},
                "effects": {"breakfast_menu_known": True},
                "cost": 1.0,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Check breakfast menu"
            },
            {
                "name": "CheckLunchMenu",
                "parameters": [],
                "preconditions": {},
                "effects": {"lunch_menu_known": True},
                "cost": 1.0,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Check lunch menu"
            },
            {
                "name": "CheckDinnerMenu",
                "parameters": [],
                "preconditions": {},
                "effects": {"dinner_menu_known": True},
                "cost": 1.0,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Check dinner menu"
            },
            {
                "name": "CheckSnackMenu",
                "parameters": [],
                "preconditions": {},
                "effects": {"snack_menu_known": True},
                "cost": 1.0,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "erp_service",
                "description": "Check snack menu"
            },
            {
                "name": "SearchInternet",
                "parameters": ["query"],
                "preconditions": {"query_valid": True},
                "effects": {"internet_search_complete": True},
                "cost": 3.0,
                "execution_time": 5.0,
                "dependencies": [],
                "api_endpoint": "perplexity_search",
                "description": "Search the internet for information"
            },
            {
                "name": "GenerateAttendancePDF",
                "parameters": [],
                "preconditions": {},
                "effects": {"attendance_pdf_sent": True},
                "cost": 3.0,
                "execution_time": 5.0,
                "dependencies": [],
                "api_endpoint": "pdf_service",
                "description": "Generate and send attendance PDF report"
            },
            {
                "name": "GenerateTimetablePDF",
                "parameters": ["date"],
                "preconditions": {},
                "effects": {"timetable_pdf_sent": True},
                "cost": 3.0,
                "execution_time": 5.0,
                "dependencies": [],
                "api_endpoint": "pdf_service",
                "description": "Generate and send timetable PDF report"
            },
            {
                "name": "GenerateCafeteriaPDF",
                "parameters": [],
                "preconditions": {},
                "effects": {"cafeteria_pdf_sent": True},
                "cost": 3.0,
                "execution_time": 5.0,
                "dependencies": [],
                "api_endpoint": "pdf_service",
                "description": "Generate and send cafeteria menu PDF report"
            },
            {
                "name": "Greeting",
                "parameters": [],
                "preconditions": {},
                "effects": {"greeting_responded": True},
                "cost": 0.5,
                "execution_time": 1.0,
                "dependencies": [],
                "api_endpoint": "openai_conversation",
                "description": "Respond to greetings naturally"
            },
            {
                "name": "SmallTalk",
                "parameters": [],
                "preconditions": {},
                "effects": {"smalltalk_responded": True},
                "cost": 0.5,
                "execution_time": 1.0,
                "dependencies": [],
                "api_endpoint": "openai_conversation",
                "description": "Engage in casual conversation"
            },
            {
                "name": "Conversation",
                "parameters": [],
                "preconditions": {},
                "effects": {"conversation_responded": True},
                "cost": 1.0,
                "execution_time": 2.0,
                "dependencies": [],
                "api_endpoint": "openai_conversation",
                "description": "Handle nuanced conversations"
            }
        ]
    
    def get_available_actions(self) -> List[Dict[str, Any]]:
        """
        Get all available actions.
        
        Returns:
            List of action definitions
        """
        return self.actions.copy()
    
    def get_action(self, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Get action definition by name.
        
        Args:
            action_name: Name of the action
            
        Returns:
            Action definition or None if not found
        """
        for action in self.actions:
            if action["name"] == action_name:
                return action.copy()
        return None
    
    def check_preconditions(
        self, 
        action: Dict[str, Any], 
        state: Dict[str, Any]
    ) -> bool:
        """
        Check if action preconditions are met.
        
        Args:
            action: Action definition
            state: Current state dictionary
            
        Returns:
            True if all preconditions are satisfied
        """
        preconditions = action.get("preconditions", {})
        
        for fact_name, required_value in preconditions.items():
            if fact_name not in state:
                return False
            if state[fact_name] != required_value:
                return False
        
        return True
    
    def apply_effects(
        self, 
        action: Dict[str, Any], 
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply action effects to state.
        
        Args:
            action: Action definition
            state: Current state dictionary
            
        Returns:
            New state dictionary with effects applied
        """
        new_state = state.copy()
        effects = action.get("effects", {})
        
        for fact_name, fact_value in effects.items():
            if fact_value is None:
                # Placeholder effect, will be filled during execution
                new_state[fact_name] = True
            else:
                new_state[fact_name] = fact_value
        
        return new_state
    
    def estimate_action_cost(
        self, 
        action: Dict[str, Any], 
        state: Dict[str, Any] = None
    ) -> float:
        """
        Estimate cost of executing an action.
        
        Args:
            action: Action definition
            state: Optional current state for context
            
        Returns:
            Estimated cost
        """
        base_cost = action.get("cost", 1.0)
        execution_time = action.get("execution_time", 1.0)
        
        # Weighted combination
        total_cost = base_cost + (execution_time * 0.1)
        
        return total_cost
    
    def get_action_dependencies(self, action: Dict[str, Any]) -> List[str]:
        """
        Get list of action dependencies.
        
        Args:
            action: Action definition
            
        Returns:
            List of dependent action names
        """
        return action.get("dependencies", []).copy()
    
    def validate_action_sequence(self, actions: List[Dict[str, Any]]) -> bool:
        """
        Validate that action sequence respects dependencies.
        
        Args:
            actions: List of actions in sequence
            
        Returns:
            True if sequence is valid
        """
        executed_actions = set()
        
        for action in actions:
            action_name = action.get("name")
            dependencies = self.get_action_dependencies(action)
            
            # Check if all dependencies have been executed
            for dep in dependencies:
                if dep not in executed_actions:
                    logger.warning(f"Action {action_name} depends on {dep} which hasn't been executed")
                    return False
            
            executed_actions.add(action_name)
        
        return True

