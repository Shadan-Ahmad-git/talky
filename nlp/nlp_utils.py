"""
Natural Language Processing utilities.
Text preprocessing and normalization functions.
"""
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def is_detailed_request(text: str) -> bool:
    """
    Check if user is asking for a detailed explanation.
    
    Args:
        text: User query text
        
    Returns:
        True if detailed request detected
    """
    normalized = normalize_text(text)
    
    # Keywords that indicate detailed requests
    detailed_keywords = [
        "explain", "tell me more", "detailed", "breakdown", "analyze",
        "why", "how", "what does this mean", "elaborate", "describe",
        "interpret", "clarify", "understand", "meaning", "reason",
        "cause", "compare", "difference", "better", "worse"
    ]
    
    for keyword in detailed_keywords:
        if keyword in normalized:
            return True
    
    return False


def is_follow_up_question(text: str) -> bool:
    """
    Check if user query is a follow-up question referring to previous context.
    
    Args:
        text: User query text
        
    Returns:
        True if follow-up detected
    """
    normalized = normalize_text(text)
    
    # Patterns that indicate follow-ups
    follow_up_patterns = [
        r"^what about",
        r"^tell me more",
        r"^explain",
        r"^why",
        r"^how",
        r"^what does",
        r"^can you",
        r"^what is",
        r"^is it",
        r"^are they",
        r"^will it",
        r"^and (what|how|why|when|where)",
        r"^(also|plus|additionally|furthermore)",
        r"^(it|that|this|they|them) (is|are|was|were|will|can|should)",
        r"^(it|that|this|they|them) (seems|looks|appears)",
        r"^(the|my|this|that) (attendance|timetable|schedule|menu)",
        r"^i want to know about",
        r"^i want to (know|learn|find out)",
        r"^tell me about (its|their|it|them|that|this)",
        r"^what about (its|their|it|them|that|this)",
        r"^(its|their|it|them) (placement|admission|program|course|faculty|campus)",
        r"^what are (his|her|their|its)",
        r"^what (is|are) (his|her|their|its)",
        r"^(his|her|their|its) (policies|plans|views|ideas|opinions|statements|platform)",
        r"add.*(for|to|about|regarding).*(that|this|it|them)",
        r"(that|this|it|them).*to (my )?todo",
        r"add.*(that|this|it)"
    ]
    
    for pattern in follow_up_patterns:
        if re.search(pattern, normalized):
            return True
    
    return False


def normalize_text(text: str) -> str:
    """
    Normalize text for processing.
    
    Args:
        text: Raw input text
        
    Returns:
        Normalized text
    """
    # Convert to lowercase
    text = text.lower().strip()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?]', '', text)
    
    return text


def extract_entities(text: str, entity_types: List[str]) -> Dict[str, Any]:
    """
    Extract named entities from text using simple pattern matching.
    
    Args:
        text: Input text
        entity_types: List of entity types to extract
        
    Returns:
        Dictionary mapping entity types to extracted values
    """
    entities = {}
    normalized = normalize_text(text)
    
    # Date patterns
    if "date" in entity_types or "datetime" in entity_types:
        date_patterns = [
            r'\b(friday|saturday|sunday|monday|tuesday|wednesday|thursday)\b',
            r'\b(today|tomorrow|yesterday)\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        ]
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            dates.extend(matches)
        if dates:
            entities["date"] = dates[0]
    
    # Location patterns
    if "location" in entity_types:
        # Simple: look for capitalized words (may be locations)
        location_patterns = [
            r'\b(in|at|to|for|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(weather|temperature|climate)\b',
        ]
        locations = []
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            # Extract location from match (could be tuple or string)
            for match in matches:
                if isinstance(match, tuple):
                    # Take the location part (usually second element)
                    loc = match[1] if len(match) > 1 else match[0]
                else:
                    loc = match
                if loc.lower() not in ['weather', 'temperature', 'climate']:
                    locations.append(loc)
        if locations:
            entities["location"] = locations[0]
    
    # Subject code patterns (like CSET208, CSET305, etc.)
    if "subject" in entity_types:
        # Match subject codes (e.g., CSET208, CSET305-P)
        subject_code_patterns = [
            r'\b([A-Z]{2,}\d{3}(?:-[A-Z])?)\b',  # CSET208, CSET305-P
            r'\b(?:subject|for|in|attendance|schedule|when is|time for)\s+([A-Z]{2,}\d{3}(?:-[A-Z])?)\b',
        ]
        subjects = []
        for pattern in subject_code_patterns:
            matches = re.findall(pattern, text)
            subjects.extend(matches)
        
        # Also try to match subject names (if code not found)
        if not subjects:
            # Common subject name patterns - look for capitalized multi-word phrases
            subject_name_patterns = [
                r'\b(?:attendance|schedule|when is|time for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',
            ]
            for pattern in subject_name_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # Filter out common words
                    if match.lower() not in ['attendance', 'schedule', 'for', 'the', 'when', 'is', 'time', 'what']:
                        subjects.append(match)
        
        if subjects:
            entities["subject"] = subjects[0]
    
    # Time patterns
    if "time" in entity_types:
        time_patterns = [
            r'\b(\d{1,2})\s*(?:am|pm|AM|PM)\b',
            r'\b(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)\b',
            r'\b(at|what.*at)\s+(\d{1,2})\s*(?:am|pm|AM|PM)\b',
            r'\b(at|what.*at)\s+(\d{1,2}):(\d{2})\s*(?:am|pm|AM|PM)\b',
        ]
        times = []
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Reconstruct time string
                    parts = [p for p in match if p]
                    hour = None
                    minute = "00"
                    ampm = "AM"
                    
                    for part in parts:
                        if part.isdigit():
                            if hour is None:
                                hour = part
                            else:
                                minute = part.zfill(2)
                        elif "PM" in part.upper():
                            ampm = "PM"
                        elif "AM" in part.upper():
                            ampm = "AM"
                    
                    if hour:
                        if ":" in str(match):
                            times.append(f"{hour}:{minute} {ampm}")
                        else:
                            times.append(f"{hour} {ampm}")
                else:
                    times.append(match)
        
        if times:
            # Clean up and format - take first match
            time_str = times[0]
            # Extract hour and am/pm
            hour_match = re.search(r'(\d{1,2})', time_str)
            ampm_match = re.search(r'(am|pm|AM|PM)', time_str, re.IGNORECASE)
            if hour_match:
                hour = hour_match.group(1)
                ampm = ampm_match.group(1).upper() if ampm_match else "AM"
                # Check if there's a minute component
                minute_match = re.search(r':(\d{2})', time_str)
                if minute_match:
                    entities["time"] = f"{hour}:{minute_match.group(1)} {ampm}"
                else:
                    entities["time"] = f"{hour} {ampm}"
    
    # Email patterns
    if "email" in entity_types:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            entities["email"] = emails[0]
    
    return entities


def tokenize(text: str) -> List[str]:
    """
    Simple tokenization of text.
    
    Args:
        text: Input text
        
    Returns:
        List of tokens
    """
    normalized = normalize_text(text)
    return normalized.split()


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple similarity between two texts.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    tokens1 = set(tokenize(text1))
    tokens2 = set(tokenize(text2))
    
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    
    return len(intersection) / len(union) if union else 0.0

