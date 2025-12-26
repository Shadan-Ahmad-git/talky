"""
Action execution engine.
Executes planned action sequences through external APIs.
"""
import logging
from typing import List, Dict, Any, Optional
from execution.api_clients import (
    WeatherAPIClient,
    EmailAPIClient,
    HotelAPIClient,
    FlightAPIClient,
    ReminderAPIClient,
    CalendarAPIClient,
    PerplexitySearchClient
)
from execution.erp_client import ERPClient
from utils.pdf_generator import PDFGenerator
from utils.database import get_database
from config import Config
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes actions from generated plans."""
    
    def __init__(self):
        """Initialize action executor with API clients."""
        self.weather_client = WeatherAPIClient()
        self.email_client = EmailAPIClient()
        self.hotel_client = HotelAPIClient()
        self.flight_client = FlightAPIClient()
        self.reminder_client = ReminderAPIClient()
        self.calendar_client = CalendarAPIClient()
        self.erp_client = ERPClient()
        self.search_client = PerplexitySearchClient()
        self.pdf_generator = PDFGenerator()
        
        # Map action names to execution methods
        self.action_handlers = {
            "CheckWeather": self._execute_check_weather,
            "SendEmail": self._execute_send_email,
            "BookHotel": self._execute_book_hotel,
            "SetReminder": self._execute_set_reminder,
            "SearchFlights": self._execute_search_flights,
            "CreateCalendarEvent": self._execute_create_calendar_event,
            "PlanTrip": self._execute_plan_trip,
            "CheckAttendance": self._execute_check_attendance,
            "CheckSubjectAttendance": self._execute_check_subject_attendance,
            "CheckMonthlyAttendance": self._execute_check_monthly_attendance,
            "CheckTimetable": self._execute_check_timetable,
            "CheckSubjectSchedule": self._execute_check_subject_schedule,
            "CheckTimeSchedule": self._execute_check_time_schedule,
            "CheckCafeteriaMenu": self._execute_check_cafeteria_menu,
            "CheckBreakfastMenu": self._execute_check_breakfast_menu,
            "CheckLunchMenu": self._execute_check_lunch_menu,
            "CheckDinnerMenu": self._execute_check_dinner_menu,
            "CheckSnackMenu": self._execute_check_snack_menu,
            "SearchInternet": self._execute_search_internet,
            "GenerateAttendancePDF": self._execute_generate_attendance_pdf,
            "GenerateTimetablePDF": self._execute_generate_timetable_pdf,
            "GenerateCafeteriaPDF": self._execute_generate_cafeteria_pdf,
            "AddTodo": self._execute_add_todo,
            "ListTodos": self._execute_list_todos,
            "CompleteTodo": self._execute_complete_todo,
            "DeleteTodo": self._execute_delete_todo
        }
        
        logger.info("Action Executor initialized")
    
    async def execute_action(
        self, 
        action: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single action.
        
        Args:
            action: Action definition
            parameters: Action parameters
            
        Returns:
            Execution result dictionary
        """
        action_name = action.get("name")
        handler = self.action_handlers.get(action_name)
        
        if not handler:
            logger.error(f"No handler found for action: {action_name}")
            return {
                "success": False,
                "error": f"Unknown action: {action_name}"
            }
        
        try:
            logger.info(f"Executing action: {action_name}")
            result = await handler(parameters)
            return result
        except Exception as e:
            logger.error(f"Error executing action {action_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_plan(
        self, 
        plan: List[Dict[str, Any]],
        intent_parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute a complete action plan.
        
        Args:
            plan: List of actions to execute
            intent_parameters: Parameters from intent classification
            
        Returns:
            List of execution results
        """
        results = []
        
        for action in plan:
            # Extract parameters for this action
            action_params = self._extract_action_parameters(
                action,
                intent_parameters
            )
            
            result = await self.execute_action(action, action_params)
            results.append({
                "action": action.get("name"),
                "parameters": action_params,
                "result": result
            })
            
            # Stop if action failed and it's critical
            if not result.get("success") and action.get("critical", False):
                logger.warning(f"Critical action failed: {action.get('name')}")
                break
        
        return results
    
    def _extract_action_parameters(
        self,
        action: Dict[str, Any],
        intent_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract relevant parameters for an action."""
        action_params = {}
        required_params = action.get("parameters", [])
        
        for param in required_params:
            # Try to find parameter in intent parameters
            if param in intent_parameters:
                action_params[param] = intent_parameters[param]
            elif param.lower() in intent_parameters:
                action_params[param] = intent_parameters[param.lower()]
        
        return action_params
    
    async def _execute_check_weather(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckWeather action."""
        location = parameters.get("location", "Unknown")
        return await self.weather_client.get_weather(location)
    
    async def _execute_send_email(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SendEmail action."""
        recipient = parameters.get("recipient", "")
        subject = parameters.get("subject", "No Subject")
        body = parameters.get("body", "")
        
        # Handle "send to me" or missing recipient - use default user email
        if not recipient or recipient.lower() in ["me", "my email", "myself", "to me"]:
            from config import Config
            if Config.USER_EMAIL:
                recipient = Config.USER_EMAIL
                logger.info(f"Using default user email: {recipient}")
            else:
                return {
                    "success": False,
                    "error": "No recipient specified and USER_EMAIL not configured. Please specify an email address or set USER_EMAIL in environment variables."
                }
        
        return await self.email_client.send_email(recipient, subject, body)
    
    async def _execute_book_hotel(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute BookHotel action."""
        location = parameters.get("location", "")
        check_in = parameters.get("check_in", "")
        check_out = parameters.get("check_out", "")
        guests = parameters.get("guests", 1)
        return await self.hotel_client.book_hotel(location, check_in, check_out, guests)
    
    async def _execute_set_reminder(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SetReminder action."""
        datetime = parameters.get("datetime", "")
        message = parameters.get("message", "")
        return await self.reminder_client.set_reminder(datetime, message)
    
    async def _execute_search_flights(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SearchFlights action."""
        origin = parameters.get("origin", "")
        destination = parameters.get("destination", "")
        date = parameters.get("date", "")
        return await self.flight_client.search_flights(origin, destination, date)
    
    async def _execute_create_calendar_event(
        self, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute CreateCalendarEvent action."""
        title = parameters.get("title", "")
        datetime = parameters.get("datetime", "")
        duration = parameters.get("duration", 60)
        return await self.calendar_client.create_event(title, datetime, duration)
    
    async def _execute_plan_trip(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PlanTrip action (composite action)."""
        location = parameters.get("location", "")
        date = parameters.get("date", "")
        
        # Execute sub-actions
        weather_result = await self.weather_client.get_weather(location)
        flights_result = await self.flight_client.search_flights("", location, date)
        
        return {
            "location": location,
            "date": date,
            "weather": weather_result,
            "flights": flights_result,
            "success": True
        }
    
    async def _execute_check_attendance(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckAttendance action."""
        result = await self.erp_client.get_attendance()
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckAttendance",
                "result": result.get("data", "Attendance data retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckAttendance",
                "result": f"Failed to fetch attendance: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_subject_attendance(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckSubjectAttendance action."""
        subject = parameters.get("subject", "")
        result = await self.erp_client.get_attendance(subject=subject)
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckSubjectAttendance",
                "result": result.get("data", "Subject attendance retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckSubjectAttendance",
                "result": f"Failed to fetch attendance: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_monthly_attendance(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckMonthlyAttendance action."""
        result = await self.erp_client.get_attendance(monthly_only=True)
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckMonthlyAttendance",
                "result": result.get("data", "Monthly attendance retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckMonthlyAttendance",
                "result": f"Failed to fetch attendance: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_timetable(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckTimetable action."""
        date = parameters.get("date")
        result = await self.erp_client.get_timetable(date=date)
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckTimetable",
                "result": result.get("data", "Timetable data retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckTimetable",
                "result": f"Failed to fetch timetable: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_subject_schedule(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckSubjectSchedule action."""
        subject = parameters.get("subject", "")
        date = parameters.get("date")
        result = await self.erp_client.get_timetable(date=date, subject=subject)
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckSubjectSchedule",
                "result": result.get("data", "Subject schedule retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckSubjectSchedule",
                "result": f"Failed to fetch schedule: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_time_schedule(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckTimeSchedule action."""
        time_query = parameters.get("time", "")
        date = parameters.get("date")
        result = await self.erp_client.get_timetable(date=date, time=time_query)
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckTimeSchedule",
                "result": result.get("data", "Time schedule retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckTimeSchedule",
                "result": f"Failed to fetch schedule: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_cafeteria_menu(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckCafeteriaMenu action."""
        result = await self.erp_client.get_cafeteria_menu()
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckCafeteriaMenu",
                "result": result.get("data", "Cafeteria menu retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckCafeteriaMenu",
                "result": f"Failed to fetch cafeteria menu: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_breakfast_menu(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckBreakfastMenu action."""
        result = await self.erp_client.get_cafeteria_menu("breakfast")
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckBreakfastMenu",
                "result": result.get("data", "Breakfast menu retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckBreakfastMenu",
                "result": f"Failed to fetch breakfast menu: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_lunch_menu(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckLunchMenu action."""
        result = await self.erp_client.get_cafeteria_menu("lunch")
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckLunchMenu",
                "result": result.get("data", "Lunch menu retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckLunchMenu",
                "result": f"Failed to fetch lunch menu: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_dinner_menu(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckDinnerMenu action."""
        result = await self.erp_client.get_cafeteria_menu("dinner")
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckDinnerMenu",
                "result": result.get("data", "Dinner menu retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckDinnerMenu",
                "result": f"Failed to fetch dinner menu: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_check_snack_menu(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CheckSnackMenu action."""
        result = await self.erp_client.get_cafeteria_menu("snack")
        if result.get("success"):
            return {
                "success": True,
                "action": "CheckSnackMenu",
                "result": result.get("data", "Snack menu retrieved"),
                "raw_data": result.get("raw_data")
            }
        else:
            return {
                "success": False,
                "action": "CheckSnackMenu",
                "result": f"Failed to fetch snack menu: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_search_internet(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SearchInternet action."""
        query = parameters.get("query", "")
        if not query:
            return {
                "success": False,
                "action": "SearchInternet",
                "result": "No search query provided"
            }
        
        result = await self.search_client.search_and_format(query)
        if result.get("success"):
            return {
                "success": True,
                "action": "SearchInternet",
                "result": result.get("result", "Search completed"),
                "query": result.get("query", query),
                "raw_data": result.get("search_result")
            }
        else:
            return {
                "success": False,
                "action": "SearchInternet",
                "result": f"Failed to search: {result.get('error', 'Unknown error')}"
            }
    
    async def _execute_generate_attendance_pdf(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GenerateAttendancePDF action."""
        try:
            # Fetch attendance data
            attendance_result = await self.erp_client.get_attendance()
            if not attendance_result.get("success"):
                return {
                    "success": False,
                    "action": "GenerateAttendancePDF",
                    "result": f"Failed to fetch attendance: {attendance_result.get('error', 'Unknown error')}"
                }
            
            # Generate PDF
            pdf_buffer = self.pdf_generator.generate_attendance_pdf(attendance_result.get("raw_data"))
            pdf_bytes = pdf_buffer.read()
            
            # Send via email
            # Handle "me" as recipient - use Config.USER_EMAIL
            recipient_param = parameters.get("recipient", "")
            if recipient_param and recipient_param.lower() == "me":
                recipient = Config.USER_EMAIL
            else:
                recipient = recipient_param or Config.USER_EMAIL
            
            if not recipient:
                return {
                    "success": False,
                    "action": "GenerateAttendancePDF",
                    "result": "No recipient email configured. Please set USER_EMAIL in environment variables."
                }
            
            subject = "Attendance Report"
            body = "Please find your attendance report attached."
            filename = f"attendance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            email_result = await self.email_client.send_email_with_pdf(
                recipient, subject, body, pdf_bytes, filename
            )
            
            if email_result.get("success"):
                return {
                    "success": True,
                    "action": "GenerateAttendancePDF",
                    "result": f"Attendance PDF report sent to {recipient}"
                }
            else:
                return {
                    "success": False,
                    "action": "GenerateAttendancePDF",
                    "result": f"Failed to send email: {email_result.get('error', 'Unknown error')}"
                }
        except Exception as e:
            logger.error(f"Error generating attendance PDF: {e}", exc_info=True)
            return {
                "success": False,
                "action": "GenerateAttendancePDF",
                "result": f"Error: {str(e)}"
            }
    
    async def _execute_generate_timetable_pdf(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GenerateTimetablePDF action."""
        try:
            date = parameters.get("date")
            # Fetch timetable data
            timetable_result = await self.erp_client.get_timetable(date=date)
            if not timetable_result.get("success"):
                return {
                    "success": False,
                    "action": "GenerateTimetablePDF",
                    "result": f"Failed to fetch timetable: {timetable_result.get('error', 'Unknown error')}"
                }
            
            # Get date string for PDF
            date_str = date or datetime.now().strftime("%Y-%m-%d")
            
            # Generate PDF
            pdf_buffer = self.pdf_generator.generate_timetable_pdf(
                timetable_result.get("raw_data"), date_str
            )
            pdf_bytes = pdf_buffer.read()
            
            # Send via email
            # Handle "me" as recipient - use Config.USER_EMAIL
            recipient_param = parameters.get("recipient", "")
            if recipient_param and recipient_param.lower() == "me":
                recipient = Config.USER_EMAIL
            else:
                recipient = recipient_param or Config.USER_EMAIL
            
            if not recipient:
                return {
                    "success": False,
                    "action": "GenerateTimetablePDF",
                    "result": "No recipient email configured. Please set USER_EMAIL in environment variables."
                }
            
            subject = f"Timetable Report - {date_str}"
            body = f"Please find your timetable report for {date_str} attached."
            filename = f"timetable_report_{date_str.replace('-', '')}.pdf"
            
            email_result = await self.email_client.send_email_with_pdf(
                recipient, subject, body, pdf_bytes, filename
            )
            
            if email_result.get("success"):
                return {
                    "success": True,
                    "action": "GenerateTimetablePDF",
                    "result": f"Timetable PDF report sent to {recipient}"
                }
            else:
                return {
                    "success": False,
                    "action": "GenerateTimetablePDF",
                    "result": f"Failed to send email: {email_result.get('error', 'Unknown error')}"
                }
        except Exception as e:
            logger.error(f"Error generating timetable PDF: {e}", exc_info=True)
            return {
                "success": False,
                "action": "GenerateTimetablePDF",
                "result": f"Error: {str(e)}"
            }
    
    async def _execute_generate_cafeteria_pdf(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GenerateCafeteriaPDF action."""
        try:
            meal_type = parameters.get("meal_type")
            # Fetch cafeteria menu data
            menu_result = await self.erp_client.get_cafeteria_menu(meal_type=meal_type)
            if not menu_result.get("success"):
                return {
                    "success": False,
                    "action": "GenerateCafeteriaPDF",
                    "result": f"Failed to fetch menu: {menu_result.get('error', 'Unknown error')}"
                }
            
            # Generate PDF
            pdf_buffer = self.pdf_generator.generate_cafeteria_pdf(
                menu_result.get("raw_data"), meal_type
            )
            pdf_bytes = pdf_buffer.read()
            
            # Send via email
            # Handle "me" as recipient - use Config.USER_EMAIL
            recipient_param = parameters.get("recipient", "")
            if recipient_param and recipient_param.lower() == "me":
                recipient = Config.USER_EMAIL
            else:
                recipient = recipient_param or Config.USER_EMAIL
            
            if not recipient:
                return {
                    "success": False,
                    "action": "GenerateCafeteriaPDF",
                    "result": "No recipient email configured. Please set USER_EMAIL in environment variables."
                }
            
            meal_name = meal_type.capitalize() if meal_type else "Full"
            subject = f"Cafeteria Menu Report - {meal_name}"
            body = f"Please find the cafeteria menu report ({meal_name}) attached."
            filename = f"cafeteria_menu_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            email_result = await self.email_client.send_email_with_pdf(
                recipient, subject, body, pdf_bytes, filename
            )
            
            if email_result.get("success"):
                return {
                    "success": True,
                    "action": "GenerateCafeteriaPDF",
                    "result": f"Cafeteria PDF report sent to {recipient}"
                }
            else:
                return {
                    "success": False,
                    "action": "GenerateCafeteriaPDF",
                    "result": f"Failed to send email: {email_result.get('error', 'Unknown error')}"
                }
        except Exception as e:
            logger.error(f"Error generating cafeteria PDF: {e}", exc_info=True)
            return {
                "success": False,
                "action": "GenerateCafeteriaPDF",
                "result": f"Error: {str(e)}"
            }
    
    async def _execute_add_todo(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new todo item."""
        try:
            task = parameters.get("task", "").strip()
            user_id = parameters.get("user_id", "telegram_user")
            priority = parameters.get("priority", "medium")
            
            if not task:
                return {
                    "success": False,
                    "error": "Task description is required"
                }
            
            db = get_database()
            
            def _create_todo():
                return db.client.table("todo_list").insert({
                    "user_id": str(user_id),
                    "task": task,
                    "priority": priority,
                    "completed": False
                }).execute()
            
            result = await asyncio.to_thread(_create_todo)
            
            if result.data:
                return {
                    "success": True,
                    "message": f"Added todo: {task}",
                    "todo": result.data[0]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create todo"
                }
        except Exception as e:
            logger.error(f"Error adding todo: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_list_todos(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List all todos for a user."""
        try:
            user_id = parameters.get("user_id", "telegram_user")
            show_completed = parameters.get("show_completed", False)
            completed_only = parameters.get("completed_only", False)
            
            db = get_database()
            
            def _fetch_todos():
                query = db.client.table("todo_list").select("*").eq("user_id", str(user_id))
                if completed_only:
                    # Show only completed tasks
                    query = query.eq("completed", True)
                elif not show_completed:
                    # Show only pending tasks (default)
                    query = query.eq("completed", False)
                # If show_completed=True and completed_only=False, show all tasks
                return query.order("created_at", desc=True).execute()
            
            result = await asyncio.to_thread(_fetch_todos)
            todos = result.data if result.data else []
            
            if not todos:
                if completed_only:
                    return {
                        "success": True,
                        "message": "No completed tasks found.",
                        "todos": []
                    }
                else:
                    return {
                        "success": True,
                        "message": "No todos found. Add one by saying 'add todo [task]'",
                        "todos": []
                    }
            
            # Format todos for display
            todo_list = []
            for i, todo in enumerate(todos, 1):
                status = "✓" if todo.get("completed") else "○"
                priority = todo.get("priority", "medium")
                todo_list.append(f"{i}. {status} {todo.get('task', '')} [{priority}]")
            
            if completed_only:
                message = "Your completed tasks:\n" + "\n".join(todo_list)
            elif show_completed:
                message = "All your tasks:\n" + "\n".join(todo_list)
            else:
                message = "Your todos:\n" + "\n".join(todo_list)
            
            return {
                "success": True,
                "message": message,
                "todos": todos
            }
        except Exception as e:
            logger.error(f"Error listing todos: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_complete_todo(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mark a todo as completed."""
        try:
            user_id = parameters.get("user_id", "telegram_user")
            task_number = parameters.get("task_number")
            task_text = parameters.get("task", "").strip()
            
            db = get_database()
            
            def _get_todos():
                return db.client.table("todo_list").select("*").eq("user_id", str(user_id)).eq("completed", False).order("created_at", desc=True).execute()
            
            result = await asyncio.to_thread(_get_todos)
            todos = result.data if result.data else []
            
            if not todos:
                return {
                    "success": False,
                    "error": "No pending todos found"
                }
            
            # Find todo by number or text
            todo_to_complete = None
            if task_number:
                try:
                    idx = int(task_number) - 1
                    if 0 <= idx < len(todos):
                        todo_to_complete = todos[idx]
                except ValueError:
                    pass
            
            if not todo_to_complete and task_text:
                # Try to find by task text
                for todo in todos:
                    if task_text.lower() in todo.get("task", "").lower():
                        todo_to_complete = todo
                        break
            
            if not todo_to_complete:
                available_todos = ', '.join([f"{i+1}. {t.get('task', '')}" for i, t in enumerate(todos[:5])])
                return {
                    "success": False,
                    "error": f"Todo not found. Available todos: {available_todos}"
                }
            
            def _update_todo():
                return db.client.table("todo_list").update({
                    "completed": True,
                    "completed_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", todo_to_complete["id"]).execute()
            
            await asyncio.to_thread(_update_todo)
            
            return {
                "success": True,
                "message": f"Completed todo: {todo_to_complete.get('task', '')}"
            }
        except Exception as e:
            logger.error(f"Error completing todo: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_delete_todo(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a todo item."""
        try:
            user_id = parameters.get("user_id", "telegram_user")
            task_number = parameters.get("task_number")
            task_text = parameters.get("task", "").strip()
            
            db = get_database()
            
            def _get_todos():
                return db.client.table("todo_list").select("*").eq("user_id", str(user_id)).order("created_at", desc=True).execute()
            
            result = await asyncio.to_thread(_get_todos)
            todos = result.data if result.data else []
            
            if not todos:
                return {
                    "success": False,
                    "error": "No todos found"
                }
            
            # Find todo by number or text
            todo_to_delete = None
            if task_number:
                try:
                    idx = int(task_number) - 1
                    if 0 <= idx < len(todos):
                        todo_to_delete = todos[idx]
                except ValueError:
                    pass
            
            if not todo_to_delete and task_text:
                # Try to find by task text
                for todo in todos:
                    if task_text.lower() in todo.get("task", "").lower():
                        todo_to_delete = todo
                        break
            
            if not todo_to_delete:
                available_todos = ', '.join([f"{i+1}. {t.get('task', '')}" for i, t in enumerate(todos[:5])])
                return {
                    "success": False,
                    "error": f"Todo not found. Available todos: {available_todos}"
                }
            
            def _delete_todo():
                return db.client.table("todo_list").delete().eq("id", todo_to_delete["id"]).execute()
            
            await asyncio.to_thread(_delete_todo)
            
            return {
                "success": True,
                "message": f"Deleted todo: {todo_to_delete.get('task', '')}"
            }
        except Exception as e:
            logger.error(f"Error deleting todo: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

