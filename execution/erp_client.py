"""
Bennett University ERP API Client with Cookie-Based Authentication.
Handles authentication and data fetching for attendance, timetable, and cafeteria.
"""
import logging
import re
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from config import Config

logger = logging.getLogger(__name__)

# IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

# API Endpoints
ATTENDANCE_DATA_URL = "https://student.bennetterp.camu.in/api/Attendance/getDtaForStupage"
TIMETABLE_URL = "https://student.bennetterp.camu.in/api/Timetable/get"
CAFETERIA_MENU_URL = "https://student.bennetterp.camu.in/api/mess-management/get-student-menu-list"

# Hardcoded student data (from cookie session)
STUDENT_ID = "668c19e7b26adcc7e79ea448"


def get_ist_now():
    """Get current time in IST"""
    return datetime.now(IST)


class ERPClient:
    """Client for Bennett University ERP API with cookie-based authentication."""
    
    def __init__(self):
        """Initialize ERP client with cookie authentication."""
        self._session: Optional[requests.Session] = None
        self.student_id = STUDENT_ID
        
        if not Config.ERP_COOKIE_SID:
            logger.warning("ERP_COOKIE_SID not configured. ERP features will not work.")
    
    def _get_session(self) -> Tuple[Optional[requests.Session], Optional[Tuple[Dict, str]]]:
        """Get or create authenticated session using cookie."""
        if self._session:
            # Return session with hardcoded progression data
            progression_data = {
                "InId": "663474b11dd0e9412a1f793f",
                "PrID": "6664712a86b084b1cb33e4b2",
                "CrID": "666473aae88943d812522d92",
                "DeptID": "666471d086b084b1cb33e4dc",
                "SemID": "6674080baa6e1fcb4aedb235",
                "AcYr": "669291a9e22fa158b82ea968",
                "CmProgID": "6886255f2fda3dbda69250f9",
                "OID": "663474b11dd0e9412a1f793f"
            }
            return self._session, (progression_data, self.student_id)
        
        if not Config.ERP_COOKIE_SID:
            logger.error("ERP_COOKIE_SID not configured. Please set it in your .env file.")
            return None, None
        
        try:
            session = requests.Session()
            
            # Set up session headers with cookie authentication
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Content-Type": "application/json",
                "Origin": "https://student.bennetterp.camu.in",
                "Referer": "https://student.bennetterp.camu.in/v2/timetable",
                "Cookie": f"connect.sid={Config.ERP_COOKIE_SID}"
            })
            
            # Hardcoded progression data
            progression_data = {
                "InId": "663474b11dd0e9412a1f793f",
                "PrID": "6664712a86b084b1cb33e4b2",
                "CrID": "666473aae88943d812522d92",
                "DeptID": "666471d086b084b1cb33e4dc",
                "SemID": "6674080baa6e1fcb4aedb235",
                "AcYr": "669291a9e22fa158b82ea968",
                "CmProgID": "6886255f2fda3dbda69250f9",
                "OID": "663474b11dd0e9412a1f793f"
            }
            
            self._session = session
            logger.info(f"Session created with cookie authentication. Student ID: {self.student_id}")
            
            return session, (progression_data, self.student_id)
        
        except Exception as e:
            logger.error(f"Error creating ERP session: {e}")
            return None, None
    
    async def get_attendance(self, subject: Optional[str] = None, monthly_only: bool = False) -> Dict[str, Any]:
        """
        Fetch attendance data with cookie-based authentication.
        
        Args:
            subject: Optional subject code or name to filter by
            monthly_only: If True, only return monthly attendance summary
        """
        session_data = self._get_session()
        if not session_data or not session_data[0]:
            return {
                "success": False,
                "error": "Failed to authenticate with ERP system. Please check ERP_COOKIE_SID in .env file."
            }
        
        session, (progression_data, student_id) = session_data
        
        payload = {
            "InId": progression_data.get("InId"),
            "PrID": progression_data.get("PrID"),
            "CrID": progression_data.get("CrID"),
            "DeptID": progression_data.get("DeptID"),
            "SemID": progression_data.get("SemID"),
            "AcYr": progression_data.get("AcYr"),
            "CmProgID": progression_data.get("CmProgID"),
            "StuID": student_id,
            "isFE": True,
            "isForWeb": True,
            "isFrAbLg": True
        }
        
        try:
            response = session.post(ATTENDANCE_DATA_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Log for debugging
            logger.debug(f"Attendance API response received. Status: {response.status_code}")
            
            # Check response structure
            if not isinstance(data, dict):
                logger.error(f"Invalid attendance response type: {type(data)}")
                return {
                    "success": False,
                    "error": "Invalid response format from attendance API"
                }
            
            # Validate response structure and log key fields
            if "output" in data and "data" in data["output"]:
                response_data = data["output"]["data"]
                logger.debug(f"Response data keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
                
                # Check if subjectList exists and log sample
                if isinstance(response_data, dict) and "subjectList" in response_data:
                    subject_list = response_data.get("subjectList", [])
                    logger.debug(f"Found {len(subject_list)} subjects in response")
                    if subject_list and logger.isEnabledFor(logging.DEBUG):
                        # Log first subject structure for debugging
                        first_subject = subject_list[0]
                        logger.debug(f"First subject keys: {list(first_subject.keys()) if isinstance(first_subject, dict) else 'Not a dict'}")
                        logger.debug(f"First subject sample: SubjCd={first_subject.get('SubjCd')}, SubjNm={first_subject.get('SubjNm')}")
            
            # Format the response based on filters
            if subject:
                formatted = self._format_subject_attendance(data, subject)
            elif monthly_only:
                formatted = self._format_monthly_attendance(data)
            else:
                formatted = self._format_attendance(data)
            
            return {
                "success": True,
                "data": formatted,
                "raw_data": data
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403]:
                logger.error("Cookie has expired. Please update ERP_COOKIE_SID in .env file.")
                return {
                    "success": False,
                    "error": "Cookie expired. Please update ERP_COOKIE_SID in .env file with a fresh cookie value."
                }
            logger.error(f"HTTP error fetching attendance: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"HTTP error: {str(e)}"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching attendance: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to fetch attendance: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_timetable(
        self, 
        date: Optional[str] = None,
        subject: Optional[str] = None,
        time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch timetable data for a specific date (default: today).
        Uses hardcoded payload structure from working cookie authentication.
        
        Args:
            date: Optional date string (YYYY-MM-DD format)
            subject: Optional subject code or name to filter by
            time: Optional time string to filter by (e.g., "10:00 AM", "2:00 PM")
        """
        session_data = self._get_session()
        if not session_data or not session_data[0]:
            return {
                "success": False,
                "error": "Failed to authenticate with ERP system. Please check ERP_COOKIE_SID in .env file."
            }
        
        session, (progression_data, _) = session_data
        
        now = get_ist_now()
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except:
                target_date = now
        else:
            target_date = now
        
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Use full hardcoded payload structure from working example
        payload = {
            "PrName": "Undergraduate",
            "SemID": "6674080baa6e1fcb4aedb235",
            "SemName": "Semester - 5",
            "AcYrNm": "2025-2026",
            "AcyrToDt": "2026-06-30",
            "AcyrFrDt": "2025-07-01",
            "DeptCode": "SCSET",
            "DepName": "School of Computer Science Engineering & Technology",
            "CrCode": "B.Tech.(CSE)",
            "CrName": "Bachelor of Technology (Computer Science and Engineering)",
            "InName": "Bennett University",
            "CmProgID": "6886255f2fda3dbda69250f9",
            "_id": "6886255f2fda3dbda69250f9",
            "stustatus": "Progressed",
            "progstdt": "2025-07-27T13:10:55.059Z",
            "StuID": self.student_id,
            "semRstd": "6674080baa6e1fcb4aedb235",
            "AcYr": "669291a9e22fa158b82ea968",
            "DeptID": "666471d086b084b1cb33e4dc",
            "CrID": "666473aae88943d812522d92",
            "PrID": "6664712a86b084b1cb33e4b2",
            "InId": "663474b11dd0e9412a1f793f",
            "OID": "663474b11dd0e9412a1f793f",
            "frmPrg": False,
            "__v": 0,
            "StFl": "A",
            "MoAt": "2025-07-27T13:10:55.061Z",
            "CrAt": "2025-07-27T13:10:55.061Z",
            "isFE": True,
            "BP": "N",
            "lang_code": "663474b11dd0e9412a1f793f",
            "start": date_str,
            "end": date_str,
            "schdlTyp": "slctdSchdl",
            "isShowCancelledPeriod": True,
            "isFromTt": True
        }
        
        try:
            response = session.post(TIMETABLE_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Format based on filters
            if subject:
                formatted = self._format_subject_schedule(data, subject, date_str)
            elif time:
                formatted = self._format_time_schedule(data, time, date_str)
            else:
                formatted = self._format_timetable(data, date_str)
            
            return {
                "success": True,
                "data": formatted,
                "raw_data": data
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403]:
                logger.error("Cookie has expired. Please update ERP_COOKIE_SID in .env file.")
                return {
                    "success": False,
                    "error": "Cookie expired. Please update ERP_COOKIE_SID in .env file with a fresh cookie value."
                }
            logger.error(f"HTTP error fetching timetable: {e}")
            return {
                "success": False,
                "error": f"HTTP error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to fetch timetable: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_cafeteria_menu(self, meal_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch today's cafeteria menu with cookie-based authentication.
        
        Args:
            meal_type: Optional filter for specific meal ("breakfast", "lunch", "dinner", "snack")
        """
        session_data = self._get_session()
        if not session_data or not session_data[0]:
            return {
                "success": False,
                "error": "Failed to authenticate with ERP system. Please check ERP_COOKIE_SID in .env file."
            }
        
        session, (progression_data, student_id) = session_data
        institution_id = progression_data.get("InId")
        
        if not institution_id:
            return {
                "success": False,
                "error": "Institution ID not available"
            }
        
        days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        today = get_ist_now()
        day_name = days[today.weekday()]
        
        payload = {
            "stuId": student_id,
            "InId": institution_id,
            "day": day_name
        }
        
        try:
            response = session.post(CAFETERIA_MENU_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            formatted = self._format_cafeteria_menu(data, meal_type)
            return {
                "success": True,
                "data": formatted,
                "raw_data": data
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403]:
                logger.error("Cookie has expired. Please update ERP_COOKIE_SID in .env file.")
                return {
                    "success": False,
                    "error": "Cookie expired. Please update ERP_COOKIE_SID in .env file with a fresh cookie value."
                }
            logger.error(f"HTTP error fetching cafeteria menu: {e}")
            return {
                "success": False,
                "error": f"HTTP error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to fetch cafeteria menu: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_attendance(self, attendance_data: Dict[str, Any]) -> str:
        """Format attendance data into readable summary - matches original code structure exactly."""
        if not attendance_data or not attendance_data.get("output", {}).get("data"):
            return "No attendance data available"
        
        data = attendance_data["output"]["data"]
        overall_percentage = data.get("OvrAllPrcntg", 0)
        current_month_percentage = data.get("CurMnthPrcntg", 0)
        overall_present = data.get("OvrAllPCnt", 0)
        overall_total = data.get("OvrAllCnt", 0)
        current_month_present = data.get("CurMPCnt", 0)
        current_month_total = data.get("CurMCnt", 0)
        
        summary = f"Overall Attendance: {overall_percentage}% ({overall_present} out of {overall_total} classes)\n"
        summary += f"This Month: {current_month_percentage}% ({current_month_present} out of {current_month_total} classes)\n\n"
        
        # Subject-wise breakdown - matches original format exactly
        subjects = data.get("subjectList", [])
        if subjects:
            summary += "Subject Details:\n\n"
            for subject in subjects:
                # Extract subject code and name - handle different possible field names
                subj_code = subject.get("SubjCd") or subject.get("subjCd") or subject.get("Subj_Code") or "Unknown"
                subj_name = subject.get("SubjNm") or subject.get("subjNm") or subject.get("Subj_Name") or "Unknown"
                
                # Ensure we have string values
                subj_code = str(subj_code).strip()
                subj_name = str(subj_name).strip()
                attendance_pct = subject.get("OvrAllPrcntg", 0)
                present = subject.get("prsentCnt", 0)
                absent = subject.get("absentCnt", 0)
                leave = subject.get("leaveCnt", 0)
                on_duty = subject.get("onDutyCnt", 0)
                med_leave = subject.get("medLeaveCnt", 0)
                total = subject.get("all", 0)
                
                summary += f"{subj_code}\n"
                summary += f"{subj_name}\n"
                summary += f"Attendance: {attendance_pct}% ({present} out of {total} classes)\n"
                summary += f"Present: {present}, Absent: {absent}"
                
                # Add optional fields if they have values (matches original)
                if leave > 0:
                    summary += f", Leave: {leave}"
                if on_duty > 0:
                    summary += f", On Duty: {on_duty}"
                if med_leave > 0:
                    summary += f", Medical Leave: {med_leave}"
                
                summary += f"\n\n"
        
        return summary.strip()
    
    def _format_subject_attendance(self, attendance_data: Dict[str, Any], subject_query: str) -> str:
        """Format attendance for a specific subject - matches original code structure."""
        if not attendance_data or not attendance_data.get("output", {}).get("data"):
            return "No attendance data available"
        
        data = attendance_data["output"]["data"]
        subjects = data.get("subjectList", [])
        
        if not subjects:
            return "No subject data available"
        
        # Log available subjects for debugging
        logger.debug(f"Found {len(subjects)} subjects in attendance data")
        if logger.isEnabledFor(logging.DEBUG):
            sample_subjects = [{"code": s.get("SubjCd"), "name": s.get("SubjNm")} for s in subjects[:3]]
            logger.debug(f"Sample subjects: {sample_subjects}")
        
        # Normalize query - handle variations like "application of AI" vs "Applications of AI"
        subject_query_normalized = subject_query.upper().strip()
        # Remove common words and articles
        query_words = [w for w in subject_query_normalized.split() if w not in ['OF', 'THE', 'FOR', 'IN', 'ATTENDANCE']]
        subject_query_normalized = ' '.join(query_words)
        
        matched_subject = None
        best_match_score = 0
        
        for subject in subjects:
            # Extract subject code and name - ensure we get the correct fields from JSON
            subj_code = subject.get("SubjCd") or subject.get("subjCd") or subject.get("Subj_Code") or ""
            subj_name = subject.get("SubjNm") or subject.get("subjNm") or subject.get("Subj_Name") or ""
            
            # Convert to uppercase for matching
            subj_code = str(subj_code).upper().strip()
            subj_name = str(subj_name).upper().strip()
            
            # Skip if both are empty
            if not subj_code and not subj_name:
                logger.warning(f"Skipping subject with missing code and name: {subject}")
                continue
            
            # Exact match on code
            if subject_query_normalized == subj_code:
                matched_subject = subject
                break
            
            # Check if query is in code
            if subject_query_normalized in subj_code or subj_code in subject_query_normalized:
                matched_subject = subject
                break
            
            # Fuzzy match on subject name - check if all query words are in subject name
            subj_name_words = set(subj_name.split())
            query_words_set = set(query_words)
            
            # Calculate match score
            if query_words_set.issubset(subj_name_words) or subj_name_words.issubset(query_words_set):
                # All query words found in subject name
                match_score = len(query_words_set.intersection(subj_name_words))
                if match_score > best_match_score:
                    best_match_score = match_score
                    matched_subject = subject
            elif any(word in subj_name for word in query_words if len(word) > 3):
                # Partial match - at least one significant word matches
                match_score = len([w for w in query_words if w in subj_name and len(w) > 3])
                if match_score > best_match_score:
                    best_match_score = match_score
                    matched_subject = subject
        
        if not matched_subject:
            # List available subjects to help user - extract properly from JSON
            available_subjects = []
            for s in subjects[:5]:
                code = s.get("SubjCd") or s.get("subjCd") or s.get("Subj_Code") or "N/A"
                name = s.get("SubjNm") or s.get("subjNm") or s.get("Subj_Name") or "N/A"
                available_subjects.append(f"{code} - {name}")
            
            return (
                f"Subject '{subject_query}' not found in your attendance records.\n\n"
                f"Available subjects:\n" + "\n".join(available_subjects)
            )
        
        # Format single subject - extract properly from JSON response
        subj_code = matched_subject.get("SubjCd") or matched_subject.get("subjCd") or matched_subject.get("Subj_Code") or "Unknown"
        subj_name = matched_subject.get("SubjNm") or matched_subject.get("subjNm") or matched_subject.get("Subj_Name") or "Unknown"
        
        # Ensure we have string values
        subj_code = str(subj_code).strip()
        subj_name = str(subj_name).strip()
        attendance_pct = matched_subject.get("OvrAllPrcntg", 0)
        present = matched_subject.get("prsentCnt", 0)
        absent = matched_subject.get("absentCnt", 0)
        leave = matched_subject.get("leaveCnt", 0)
        on_duty = matched_subject.get("onDutyCnt", 0)
        med_leave = matched_subject.get("medLeaveCnt", 0)
        total = matched_subject.get("all", 0)
        
        summary = f"{subj_code}\n"
        summary += f"{subj_name}\n"
        summary += f"Attendance: {attendance_pct}% ({present}/{total})\n"
        summary += f"Present: {present}, Absent: {absent}"
        
        # Add optional fields if they have values (matches original)
        if leave > 0:
            summary += f", Leave: {leave}"
        if on_duty > 0:
            summary += f", On Duty: {on_duty}"
        if med_leave > 0:
            summary += f", Medical Leave: {med_leave}"
        
        return summary
    
    def _format_monthly_attendance(self, attendance_data: Dict[str, Any]) -> str:
        """Format only monthly attendance summary - matches original code structure."""
        if not attendance_data or not attendance_data.get("output", {}).get("data"):
            return "No attendance data available"
        
        data = attendance_data["output"]["data"]
        current_month_percentage = data.get("CurMnthPrcntg", 0)
        current_month_present = data.get("CurMPCnt", 0)
        current_month_total = data.get("CurMCnt", 0)
        
        summary = f"This Month: {current_month_percentage}% ({current_month_present} out of {current_month_total} classes)\n"
        
        if current_month_total == 0:
            summary += "\nNo classes recorded this month yet."
        
        return summary.strip()
    
    def _format_timetable(self, timetable_data: Dict[str, Any], date_str: str) -> str:
        """Format full timetable data into readable summary."""
        if not timetable_data or not timetable_data.get("output", {}).get("data"):
            return f"No timetable data available for {date_str}"
        
        summary = f"Timetable for {date_str}\n\n"
        has_classes = False
        
        for day in timetable_data["output"]["data"]:
            periods = day.get("Periods", [])
            if periods:
                has_classes = True
                for idx, period in enumerate(periods, 1):
                    # Extract subject name - handle different possible field names
                    subject_name = period.get("SubNa") or period.get("subNa") or period.get("Sub_Name") or period.get("subjectName") or "Unknown Subject"
                    faculty_name = period.get("StaffNm") or period.get("staffNm") or period.get("Staff_Name") or period.get("facultyName") or "Unknown Faculty"
                    room = period.get("Location") or period.get("location") or period.get("Room") or "TBA"
                    
                    # Ensure we have string values
                    subject_name = str(subject_name).strip()
                    faculty_name = str(faculty_name).strip()
                    room = str(room).strip()
                    start_time = period.get("start", "")
                    end_time = period.get("end", "")
                    
                    time_str = ""
                    if start_time and end_time:
                        try:
                            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                            start = start_dt.strftime("%I:%M %p")
                            end = end_dt.strftime("%I:%M %p")
                            time_str = f"{start} - {end}"
                        except:
                            time_str = f"{start_time} - {end_time}"
                    
                    summary += f"Period {idx}\n"
                    summary += f"Subject: {subject_name}\n"
                    summary += f"Faculty: {faculty_name}\n"
                    summary += f"Room: {room}\n"
                    if time_str:
                        summary += f"Time: {time_str}\n"
                    summary += "\n"
        
        if not has_classes:
            return f"No classes scheduled for {date_str}"
        
        return summary.strip()
    
    def _format_subject_schedule(self, timetable_data: Dict[str, Any], subject_query: str, date_str: str) -> str:
        """Format schedule for a specific subject."""
        if not timetable_data or not timetable_data.get("output", {}).get("data"):
            return f"No timetable data available for {date_str}"
        
        # Normalize query - handle variations
        subject_query_normalized = subject_query.upper().strip()
        query_words = [w for w in subject_query_normalized.split() if w not in ['OF', 'THE', 'FOR', 'IN', 'SCHEDULE', 'WHEN', 'IS']]
        subject_query_normalized = ' '.join(query_words)
        
        found_periods = []
        
        for day in timetable_data["output"]["data"]:
            periods = day.get("Periods", [])
            for period in periods:
                # Extract subject name and code - handle different possible field names
                subject_name = period.get("SubNa") or period.get("subNa") or period.get("Sub_Name") or period.get("subjectName") or ""
                subject_code = period.get("SubCd") or period.get("subCd") or period.get("Sub_Code") or period.get("subjectCode") or ""
                
                # Convert to uppercase for matching
                subject_name = str(subject_name).upper().strip()
                subject_code = str(subject_code).upper().strip()
                
                # Exact or partial match
                if (subject_query_normalized in subject_name or 
                    subject_query_normalized in subject_code or
                    subject_code in subject_query_normalized or
                    any(word in subject_name for word in query_words if len(word) > 3)):
                    found_periods.append(period)
        
        if not found_periods:
            return f"Subject '{subject_query}' not found in timetable for {date_str}"
        
        summary = f"{subject_query} Schedule for {date_str}\n\n"
        
        for period in found_periods:
            # Extract subject name and other fields - handle different possible field names
            subject_name = period.get("SubNa") or period.get("subNa") or period.get("Sub_Name") or period.get("subjectName") or "Unknown Subject"
            faculty_name = period.get("StaffNm") or period.get("staffNm") or period.get("Staff_Name") or period.get("facultyName") or "Unknown Faculty"
            room = period.get("Location") or period.get("location") or period.get("Room") or "TBA"
            
            # Ensure we have string values
            subject_name = str(subject_name).strip()
            faculty_name = str(faculty_name).strip()
            room = str(room).strip()
            
            start_time = period.get("start", "")
            end_time = period.get("end", "")
            
            time_str = ""
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    start = start_dt.strftime("%I:%M %p")
                    end = end_dt.strftime("%I:%M %p")
                    time_str = f"{start} - {end}"
                except:
                    time_str = f"{start_time} - {end_time}"
            
            summary += f"Time: {time_str}\n"
            summary += f"Faculty: {faculty_name}\n"
            summary += f"Room: {room}\n\n"
        
        return summary.strip()
    
    def _format_time_schedule(self, timetable_data: Dict[str, Any], time_query: str, date_str: str) -> str:
        """Format what subject is scheduled at a specific time."""
        if not timetable_data or not timetable_data.get("output", {}).get("data"):
            return f"No timetable data available for {date_str}"
        
        # Parse time query (handle various formats like "10 am", "10:00 AM", "2 pm", "14:00")
        time_parts = time_query.upper().replace(":", " ").split()
        target_hour = None
        target_minute = 0
        
        for part in time_parts:
            if part.isdigit():
                num = int(part)
                if target_hour is None:
                    target_hour = num
                else:
                    target_minute = num
            elif "PM" in part and target_hour and target_hour < 12:
                target_hour += 12
            elif "AM" in part and target_hour == 12:
                target_hour = 0
        
        if target_hour is None:
            return f"Could not parse time '{time_query}'. Please use format like '10 AM' or '2:00 PM'"
        
        found_periods = []
        
        for day in timetable_data["output"]["data"]:
            periods = day.get("Periods", [])
            for period in periods:
                start_time = period.get("start", "")
                if start_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        period_hour = start_dt.hour
                        period_minute = start_dt.minute
                        
                        # Check if time matches (within 30 minutes)
                        if period_hour == target_hour and abs(period_minute - target_minute) <= 30:
                            found_periods.append(period)
                    except:
                        pass
        
        if not found_periods:
            return f"No class scheduled at {time_query} on {date_str}"
        
        summary = f"Classes at {time_query} on {date_str}\n\n"
        
        for period in found_periods:
            # Extract subject name and other fields - handle different possible field names
            subject_name = period.get("SubNa") or period.get("subNa") or period.get("Sub_Name") or period.get("subjectName") or "Unknown Subject"
            faculty_name = period.get("StaffNm") or period.get("staffNm") or period.get("Staff_Name") or period.get("facultyName") or "Unknown Faculty"
            room = period.get("Location") or period.get("location") or period.get("Room") or "TBA"
            
            # Ensure we have string values
            subject_name = str(subject_name).strip()
            faculty_name = str(faculty_name).strip()
            room = str(room).strip()
            
            start_time = period.get("start", "")
            end_time = period.get("end", "")
            
            time_str = ""
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    start = start_dt.strftime("%I:%M %p")
                    end = end_dt.strftime("%I:%M %p")
                    time_str = f"{start} - {end}"
                except:
                    time_str = f"{start_time} - {end_time}"
            
            summary += f"{subject_name}\n"
            summary += f"Time: {time_str}\n"
            summary += f"Faculty: {faculty_name}\n"
            summary += f"Room: {room}\n\n"
        
        return summary.strip()
    
    def _format_cafeteria_menu(self, menu_data: Dict[str, Any], meal_type: Optional[str] = None) -> str:
        """
        Format cafeteria menu data into readable summary.
        
        Args:
            menu_data: Raw menu data from API
            meal_type: Optional filter for specific meal ("breakfast", "lunch", "dinner", "snack")
        """
        if not menu_data or not menu_data.get("output", {}).get("data"):
            return "No cafeteria menu available for today"
        
        data = menu_data["output"]["data"]
        meal_list = data.get("oMealList", [])
        
        if not meal_list:
            return "No meals scheduled for today"
        
        # Normalize meal type filter
        meal_filter = None
        if meal_type:
            meal_filter = meal_type.lower()
            # Map common variations
            if meal_filter in ["breakfast", "morning"]:
                meal_filter = "breakfast"
            elif meal_filter in ["lunch", "afternoon"]:
                meal_filter = "lunch"
            elif meal_filter in ["dinner", "tonight", "evening", "night"]:
                meal_filter = "dinner"
            elif meal_filter in ["snack", "snacks"]:
                meal_filter = "snack"
        
        # Build summary
        if meal_filter:
            # Single meal response
            summary = ""
        else:
            # Full menu response
            summary = "Today's Cafeteria Menu\n\n"
            facility = data.get("facNme", "Cafeteria")
            summary += f"Location: {facility}\n\n"
        
        found_meal = False
        for meal in meal_list:
            meal_time = meal.get("mealTm", "").lower()
            meal_items = meal.get("msNme", "")
            
            # Check if this meal matches the filter
            if meal_filter:
                meal_match = False
                if meal_filter == "breakfast" and ("breakfast" in meal_time or "07" in meal_time or "08" in meal_time or "09" in meal_time):
                    meal_match = True
                elif meal_filter == "lunch" and ("lunch" in meal_time or "12" in meal_time or "1:00" in meal_time or "2:00" in meal_time or "3:00" in meal_time):
                    meal_match = True
                elif meal_filter == "dinner" and ("dinner" in meal_time or "8:00" in meal_time or "9:00" in meal_time or "10:00" in meal_time or "8:00 pm" in meal_time):
                    meal_match = True
                elif meal_filter == "snack" and ("snack" in meal_time or "5:00" in meal_time or "6:00" in meal_time):
                    meal_match = True
                
                if not meal_match:
                    continue
            
            found_meal = True
            
            # Format meal time (clean up)
            if meal_time:
                # Remove extra formatting, keep it simple
                clean_time = meal.get("mealTm", "").strip()
                if not meal_filter:
                    summary += f"{clean_time}\n"
                else:
                    # For single meal, include time in header
                    summary += f"{clean_time}\n\n"
            
            # Format items - remove kcal info and trailing dashes
            if meal_items:
                items = [item.strip() for item in meal_items.split('\n') if item.strip()]
                for item in items:
                    if item and item != '-':
                        # Remove kcal information (anything in parentheses with Kcal)
                        item_clean = re.sub(r'\s*\([^)]*Kcal[^)]*\)', '', item)
                        item_clean = re.sub(r'\s*\([^)]*kcal[^)]*\)', '', item_clean)
                        # Remove trailing dashes and spaces
                        item_clean = re.sub(r'[\s-]+$', '', item_clean.strip())
                        if item_clean:
                            summary += f"  • {item_clean}\n"
            
            summary += "\n"
        
        if meal_filter and not found_meal:
            meal_names = {
                "breakfast": "Breakfast",
                "lunch": "Lunch",
                "dinner": "Dinner",
                "snack": "Snack"
            }
            return f"No {meal_names.get(meal_filter, meal_filter)} menu available for today"
        
        return summary.strip()

