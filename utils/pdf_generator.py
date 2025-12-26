"""
PDF report generator for attendance, timetable, and cafeteria menu.
"""
import logging
from io import BytesIO
from typing import Dict, Any, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generate PDF reports for various data types."""
    
    def __init__(self):
        """Initialize PDF generator."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        # Heading style
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=8,
            spaceBefore=12
        )
        
        # Normal text style
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            leading=14
        )
    
    def generate_attendance_pdf(self, attendance_data: Dict[str, Any]) -> BytesIO:
        """
        Generate PDF report for attendance data.
        
        Args:
            attendance_data: Raw attendance data from ERP API
            
        Returns:
            BytesIO buffer containing PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        
        # Title
        title = Paragraph("Attendance Report", self.title_style)
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Date
        date_str = datetime.now().strftime("%B %d, %Y")
        date_para = Paragraph(f"Generated on: {date_str}", self.normal_style)
        story.append(date_para)
        story.append(Spacer(1, 0.3*inch))
        
        if not attendance_data or not attendance_data.get("output", {}).get("data"):
            story.append(Paragraph("No attendance data available.", self.normal_style))
            doc.build(story)
            buffer.seek(0)
            return buffer
        
        data = attendance_data["output"]["data"]
        
        # Overall statistics
        overall_percentage = data.get("OvrAllPrcntg", 0)
        current_month_percentage = data.get("CurMnthPrcntg", 0)
        overall_present = data.get("OvrAllPCnt", 0)
        overall_total = data.get("OvrAllCnt", 0)
        current_month_present = data.get("CurMPCnt", 0)
        current_month_total = data.get("CurMCnt", 0)
        
        # Summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Overall Attendance', f"{overall_percentage}% ({overall_present} out of {overall_total} classes)"],
            ['This Month', f"{current_month_percentage}% ({current_month_present} out of {current_month_total} classes)"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Subject-wise breakdown
        subjects = data.get("subjectList", [])
        if subjects:
            story.append(Paragraph("Subject Details", self.heading_style))
            
            # Subject table header
            subject_data = [['Subject Code', 'Subject Name', 'Attendance %', 'Present', 'Absent', 'Total']]
            
            for subject in subjects:
                subj_code = str(subject.get("SubjCd") or subject.get("subjCd") or subject.get("Subj_Code") or "N/A")
                subj_name = str(subject.get("SubjNm") or subject.get("subjNm") or subject.get("Subj_Name") or "N/A")
                attendance_pct = subject.get("OvrAllPrcntg", 0)
                present = subject.get("prsentCnt", 0)
                absent = subject.get("absentCnt", 0)
                total = subject.get("all", 0)
                
                subject_data.append([
                    subj_code[:15],  # Truncate long codes
                    subj_name[:25],  # Truncate long names
                    f"{attendance_pct}%",
                    str(present),
                    str(absent),
                    str(total)
                ])
            
            subject_table = Table(subject_data, colWidths=[1.2*inch, 2*inch, 0.8*inch, 0.7*inch, 0.7*inch, 0.7*inch])
            subject_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            story.append(subject_table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_timetable_pdf(self, timetable_data: Dict[str, Any], date_str: str) -> BytesIO:
        """
        Generate PDF report for timetable data.
        
        Args:
            timetable_data: Raw timetable data from ERP API
            date_str: Date string for the timetable
            
        Returns:
            BytesIO buffer containing PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        
        # Title
        title = Paragraph(f"Timetable Report - {date_str}", self.title_style)
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Date
        gen_date = datetime.now().strftime("%B %d, %Y")
        date_para = Paragraph(f"Generated on: {gen_date}", self.normal_style)
        story.append(date_para)
        story.append(Spacer(1, 0.3*inch))
        
        if not timetable_data or not timetable_data.get("output", {}).get("data"):
            story.append(Paragraph(f"No timetable data available for {date_str}.", self.normal_style))
            doc.build(story)
            buffer.seek(0)
            return buffer
        
        timetable_list = timetable_data["output"]["data"]
        has_classes = False
        
        for day in timetable_list:
            periods = day.get("Periods", [])
            if periods:
                has_classes = True
                for idx, period in enumerate(periods, 1):
                    subject_name = str(period.get("SubNa") or period.get("subNa") or period.get("Sub_Name") or "Unknown Subject")
                    faculty_name = str(period.get("StaffNm") or period.get("staffNm") or period.get("Staff_Name") or "Unknown Faculty")
                    room = str(period.get("Location") or period.get("location") or "TBA")
                    
                    start_time = period.get("start", "")
                    end_time = period.get("end", "")
                    
                    time_str = ""
                    if start_time and end_time:
                        try:
                            from datetime import datetime as dt
                            start_dt = dt.fromisoformat(start_time.replace('Z', '+00:00'))
                            end_dt = dt.fromisoformat(end_time.replace('Z', '+00:00'))
                            start = start_dt.strftime("%I:%M %p")
                            end = end_dt.strftime("%I:%M %p")
                            time_str = f"{start} - {end}"
                        except:
                            time_str = f"{start_time} - {end_time}"
                    
                    # Period header
                    period_title = Paragraph(f"Period {idx}", self.heading_style)
                    story.append(period_title)
                    
                    # Period details table
                    period_data = [
                        ['Subject', subject_name],
                        ['Faculty', faculty_name],
                        ['Room', room],
                        ['Time', time_str]
                    ]
                    
                    period_table = Table(period_data, colWidths=[1.5*inch, 5*inch])
                    period_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    
                    story.append(period_table)
                    story.append(Spacer(1, 0.2*inch))
        
        if not has_classes:
            story.append(Paragraph(f"No classes scheduled for {date_str}.", self.normal_style))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_cafeteria_pdf(self, menu_data: Dict[str, Any], meal_type: Optional[str] = None) -> BytesIO:
        """
        Generate PDF report for cafeteria menu.
        
        Args:
            menu_data: Raw menu data from ERP API
            meal_type: Optional filter for specific meal
            
        Returns:
            BytesIO buffer containing PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        
        # Title
        if meal_type:
            title_text = f"Cafeteria Menu - {meal_type.capitalize()}"
        else:
            title_text = "Cafeteria Menu"
        
        title = Paragraph(title_text, self.title_style)
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Date
        date_str = datetime.now().strftime("%B %d, %Y")
        date_para = Paragraph(f"Date: {date_str}", self.normal_style)
        story.append(date_para)
        story.append(Spacer(1, 0.3*inch))
        
        if not menu_data or not menu_data.get("output", {}).get("data"):
            story.append(Paragraph("No cafeteria menu available.", self.normal_style))
            doc.build(story)
            buffer.seek(0)
            return buffer
        
        data = menu_data["output"]["data"]
        facility = data.get("facNme", "Cafeteria")
        facility_para = Paragraph(f"Location: {facility}", self.normal_style)
        story.append(facility_para)
        story.append(Spacer(1, 0.2*inch))
        
        meal_list = data.get("oMealList", [])
        if not meal_list:
            story.append(Paragraph("No meals scheduled for today.", self.normal_style))
            doc.build(story)
            buffer.seek(0)
            return buffer
        
        # Normalize meal filter
        meal_filter = None
        if meal_type:
            meal_filter = meal_type.lower()
            if meal_filter in ["breakfast", "morning"]:
                meal_filter = "breakfast"
            elif meal_filter in ["lunch", "afternoon"]:
                meal_filter = "lunch"
            elif meal_filter in ["dinner", "tonight", "evening", "night"]:
                meal_filter = "dinner"
            elif meal_filter in ["snack", "snacks"]:
                meal_filter = "snack"
        
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
            
            # Meal time header
            clean_time = meal.get("mealTm", "").strip()
            meal_header = Paragraph(clean_time, self.heading_style)
            story.append(meal_header)
            
            # Format items
            if meal_items:
                import re
                items = [item.strip() for item in meal_items.split('\n') if item.strip()]
                items_clean = []
                for item in items:
                    if item and item != '-':
                        # Remove kcal information and trailing dashes
                        item_clean = re.sub(r'\s*\([^)]*Kcal[^)]*\)', '', item)
                        item_clean = re.sub(r'\s*\([^)]*kcal[^)]*\)', '', item_clean)
                        item_clean = re.sub(r'[\s-]+$', '', item_clean.strip())
                        if item_clean:
                            items_clean.append(item_clean)
                
                if items_clean:
                    for item in items_clean:
                        item_para = Paragraph(f"• {item}", self.normal_style)
                        story.append(item_para)
            
            story.append(Spacer(1, 0.2*inch))
        
        if meal_filter and not found_meal:
            meal_names = {
                "breakfast": "Breakfast",
                "lunch": "Lunch",
                "dinner": "Dinner",
                "snack": "Snack"
            }
            no_meal_para = Paragraph(f"No {meal_names.get(meal_filter, meal_filter)} menu available for today.", self.normal_style)
            story.append(no_meal_para)
        
        doc.build(story)
        buffer.seek(0)
        return buffer

