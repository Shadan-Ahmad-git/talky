"""
Explanation engine for generating human-readable explanations.
Provides transparency and explainability for AI decisions.
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ExplanationEngine:
    """Generates explanations for AI agent decisions."""
    
    def __init__(self):
        """Initialize explanation engine."""
        logger.info("Explanation Engine initialized")
    
    def explain_plan(
        self, 
        plan: List[Dict[str, Any]], 
        original_intent: str
    ) -> str:
        """
        Generate explanation for an action plan.
        
        Args:
            plan: List of actions in the plan
            original_intent: Original user intent
            
        Returns:
            Human-readable explanation
        """
        if not plan:
            return "I couldn't generate a plan for your request. Please try rephrasing."
        
        # For single action plans, skip the verbose explanation
        if len(plan) == 1:
            return ""  # Will show results directly
        
        # Only show explanation for multi-step plans
        explanation_parts = []
        for i, action in enumerate(plan, 1):
            action_name = action.get("name", "Unknown")
            description = action.get("description", "Perform action")
            # Make it concise
            explanation_parts.append(f"{i}. {description}")
        
        return "\n".join(explanation_parts) if explanation_parts else ""
    
    def explain_decision(
        self, 
        action: Dict[str, Any], 
        alternatives: List[Dict[str, Any]] = None
    ) -> str:
        """
        Explain why a specific action was chosen.
        
        Args:
            action: Chosen action
            alternatives: Alternative actions that were considered
            
        Returns:
            Decision explanation
        """
        action_name = action.get("name", "Unknown")
        cost = action.get("cost", 0)
        
        explanation = f"I chose to execute '{action_name}' because it:"
        explanation += f"\n- Has a reasonable cost ({cost})"
        explanation += f"\n- Meets all required preconditions"
        
        if alternatives:
            explanation += f"\n- Was selected over {len(alternatives)} alternative(s)"
        
        return explanation
    
    def explain_reasoning_path(
        self, 
        decision_chain: List[Dict[str, Any]]
    ) -> str:
        """
        Explain the reasoning path that led to a decision.
        
        Args:
            decision_chain: Chain of decisions and reasoning steps
            
        Returns:
            Reasoning path explanation
        """
        if not decision_chain:
            return "No reasoning path available."
        
        explanation = "Here's how I reasoned through your request:\n\n"
        
        for i, step in enumerate(decision_chain, 1):
            step_type = step.get("type", "decision")
            description = step.get("description", "")
            confidence = step.get("confidence", 0.0)
            
            explanation += f"{i}. {step_type.title()}: {description}"
            if confidence > 0:
                explanation += f" (confidence: {confidence:.0%})"
            explanation += "\n"
        
        return explanation
    
    def provide_alternative_explanations(
        self, 
        action: Dict[str, Any]
    ) -> List[str]:
        """
        Provide alternative explanations for an action.
        
        Args:
            action: Action to explain
            
        Returns:
            List of alternative explanations
        """
        action_name = action.get("name", "Unknown")
        
        alternatives = [
            f"'{action_name}' was selected as the most efficient option.",
            f"This action fulfills your request by executing '{action_name}'.",
            f"I determined that '{action_name}' is the best course of action."
        ]
        
        return alternatives
    
    def format_execution_results(
        self,
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Format execution results into readable explanation.
        
        Args:
            results: List of execution results
            
        Returns:
            Formatted explanation
        """
        if not results:
            return "No actions were executed."
        
        formatted_results = []
        
        for result in results:
            action_name = result.get("action", "Unknown")
            execution_result = result.get("result", {})
            success = execution_result.get("success", False)
            
            if success:
                # Format result based on action type - make it concise and natural
                # Check for pre-formatted result first (most actions now provide this)
                if "result" in execution_result:
                    result_text = execution_result.get("result", "")
                    if isinstance(result_text, str) and len(result_text) > 0:
                        # Show the formatted result directly - it's already concise
                        formatted_results.append(result_text)
                        continue
                
                # Fallback formatting for actions without pre-formatted results
                if "temperature" in execution_result and "location" in execution_result:
                    # Weather format - concise
                    location = execution_result.get("location", "Unknown")
                    temp = execution_result.get("temperature", "N/A")
                    formatted_results.append(f"🌤️ {location}: {temp}°C")
                elif "location" in execution_result:
                    formatted_results.append(f"Location: {execution_result.get('location')}")
                elif "temperature" in execution_result:
                    formatted_results.append(f"Temperature: {execution_result.get('temperature')}°C")
                else:
                    formatted_results.append(f"✓ {action_name} completed")
            else:
                error = execution_result.get("error", "Unknown error")
                formatted_results.append(f"✗ Failed: {error}")
        
        return "\n\n".join(formatted_results)

