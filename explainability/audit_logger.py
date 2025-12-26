"""
Audit logger for tracking decisions and reasoning.
Maintains audit trail for explainability.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from utils.database import get_database

logger = logging.getLogger(__name__)


class AuditLogger:
    """Logs audit trail for AI decisions."""
    
    def __init__(self):
        """Initialize audit logger."""
        self.db = get_database()
        logger.info("Audit Logger initialized")
    
    async def log_intent_classification(
        self,
        session_id: str,
        user_input: str,
        detected_intents: List[Dict[str, Any]],
        selected_intent: str,
        confidence: float
    ) -> None:
        """
        Log intent classification decision.
        
        Args:
            session_id: Session identifier
            user_input: Original user input
            detected_intents: All detected intents
            selected_intent: Selected intent
            confidence: Confidence score
        """
        decision_data = {
            "user_input": user_input,
            "detected_intents": detected_intents,
            "selected_intent": selected_intent
        }
        
        reasoning = (
            f"Classified user input as '{selected_intent}' "
            f"with {confidence:.0%} confidence. "
            f"Considered {len(detected_intents)} possible intent(s)."
        )
        
        await self.db.save_audit_log(
            session_id=session_id,
            action="intent_classification",
            decision_data=decision_data,
            confidence_score=confidence,
            reasoning=reasoning
        )
    
    async def log_planning_decision(
        self,
        session_id: str,
        plan: List[Dict[str, Any]],
        initial_state: Dict[str, Any],
        goal_state: Dict[str, Any],
        planning_time: float
    ) -> None:
        """
        Log planning decision.
        
        Args:
            session_id: Session identifier
            plan: Generated action plan
            initial_state: Initial state
            goal_state: Goal state
            planning_time: Time taken for planning
        """
        decision_data = {
            "plan": plan,
            "initial_state": initial_state,
            "goal_state": goal_state,
            "planning_time": planning_time
        }
        
        reasoning = (
            f"Generated plan with {len(plan)} action(s) "
            f"to reach goal state. Planning took {planning_time:.2f}s."
        )
        
        await self.db.save_audit_log(
            session_id=session_id,
            action="planning",
            decision_data=decision_data,
            confidence_score=0.9,  # High confidence for valid plans
            reasoning=reasoning
        )
    
    async def log_action_execution(
        self,
        session_id: str,
        action: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """
        Log action execution.
        
        Args:
            session_id: Session identifier
            action: Executed action
            result: Execution result
        """
        decision_data = {
            "action": action,
            "result": result
        }
        
        success = result.get("success", False)
        reasoning = (
            f"Executed action '{action.get('name')}' "
            f"with {'success' if success else 'failure'}."
        )
        
        await self.db.save_audit_log(
            session_id=session_id,
            action="execution",
            decision_data=decision_data,
            confidence_score=1.0 if success else 0.0,
            reasoning=reasoning
        )
    
    async def get_audit_trail(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of audit log entries
        """
        return await self.db.get_audit_logs(session_id)
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())

