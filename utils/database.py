"""
Supabase database integration for user sessions and history storage.
Replaces SQLite with Supabase PostgreSQL backend.
"""
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from config import Config

logger = logging.getLogger(__name__)


class Database:
    """Database manager using Supabase for data persistence."""
    
    def __init__(self):
        """Initialize Supabase client."""
        if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
            raise ValueError("Supabase URL and KEY must be configured")
        
        self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        logger.info("Supabase client initialized")
    
    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user session data from Supabase.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            # Run synchronous Supabase call in thread pool
            def _fetch():
                return (
                    self.client.table("user_sessions")
                    .select("*")
                    .eq("user_id", str(user_id))
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
            
            response = await asyncio.to_thread(_fetch)
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching user session: {e}")
            return None
    
    async def save_user_session(
        self, 
        user_id: str, 
        session_data: Dict[str, Any],
        is_active: bool = True
    ) -> bool:
        """
        Save or update user session in Supabase.
        
        Args:
            user_id: Telegram user ID
            session_data: Session data dictionary
            is_active: Whether session is currently active
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                "user_id": str(user_id),
                "session_data": json.dumps(session_data),
                "is_active": is_active,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Check if session exists
            existing = await self.get_user_session(user_id)
            
            def _save():
                if existing:
                    # Update existing session
                    return (
                        self.client.table("user_sessions")
                        .update(data)
                        .eq("id", existing["id"])
                        .execute()
                    )
                else:
                    # Create new session
                    data["created_at"] = datetime.utcnow().isoformat()
                    return (
                        self.client.table("user_sessions")
                        .insert(data)
                        .execute()
                    )
            
            await asyncio.to_thread(_save)
            return True
        except Exception as e:
            logger.error(f"Error saving user session: {e}")
            return False
    
    async def save_interaction_history(
        self,
        user_id: str,
        intent: str,
        command_text: str,
        response_text: str,
        plan: Optional[List[Dict[str, Any]]] = None,
        success: bool = True
    ) -> bool:
        """
        Save interaction history to Supabase.
        
        Args:
            user_id: Telegram user ID
            intent: Detected intent
            command_text: Original user command
            response_text: Bot response
            plan: Generated action plan (optional)
            success: Whether interaction was successful
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                "user_id": str(user_id),
                "intent": intent,
                "command_text": command_text,
                "response_text": response_text,
                "plan": json.dumps(plan) if plan else None,
                "success": success,
                "created_at": datetime.utcnow().isoformat()
            }
            
            def _save():
                return (
                    self.client.table("interaction_history")
                    .insert(data)
                    .execute()
                )
            
            await asyncio.to_thread(_save)
            return True
        except Exception as e:
            logger.error(f"Error saving interaction history: {e}")
            return False
    
    async def get_user_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve user interaction history.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of records to retrieve
            
        Returns:
            List of interaction records
        """
        try:
            def _fetch():
                return (
                    self.client.table("interaction_history")
                    .select("*")
                    .eq("user_id", str(user_id))
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
            
            response = await asyncio.to_thread(_fetch)
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching user history: {e}")
            return []
    
    async def save_audit_log(
        self,
        session_id: str,
        action: str,
        decision_data: Dict[str, Any],
        confidence_score: float,
        reasoning: str
    ) -> bool:
        """
        Save audit log for explainability.
        
        Args:
            session_id: Session identifier
            action: Action taken
            decision_data: Decision details
            confidence_score: Confidence score (0-1)
            reasoning: Human-readable reasoning
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                "session_id": session_id,
                "action": action,
                "decision_data": json.dumps(decision_data),
                "confidence_score": confidence_score,
                "reasoning": reasoning,
                "created_at": datetime.utcnow().isoformat()
            }
            
            def _save():
                return (
                    self.client.table("audit_logs")
                    .insert(data)
                    .execute()
                )
            
            await asyncio.to_thread(_save)
            return True
        except Exception as e:
            logger.error(f"Error saving audit log: {e}")
            return False
    
    async def get_audit_logs(
        self, 
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of audit log records
        """
        try:
            def _fetch():
                return (
                    self.client.table("audit_logs")
                    .select("*")
                    .eq("session_id", session_id)
                    .order("created_at", desc=True)
                    .execute()
                )
            
            response = await asyncio.to_thread(_fetch)
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            return []


# Global database instance
db: Optional[Database] = None


def get_database() -> Database:
    """Get or create database instance."""
    global db
    if db is None:
        db = Database()
    return db

