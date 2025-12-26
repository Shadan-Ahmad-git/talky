"""
State representation and transition management.
Handles world state modeling for planning algorithms.
"""
import logging
from typing import Dict, Any, Set, List
from copy import deepcopy

logger = logging.getLogger(__name__)


class State:
    """Represents the current world state."""
    
    def __init__(self, facts: Dict[str, Any] = None):
        """
        Initialize state with facts.
        
        Args:
            facts: Dictionary of state facts (e.g., {"weather_known": True, "location": "Mumbai"})
        """
        self.facts = facts or {}
        self.goals: Set[str] = set()
    
    def has_fact(self, fact_name: str) -> bool:
        """Check if state contains a fact."""
        return fact_name in self.facts
    
    def get_fact(self, fact_name: str, default: Any = None) -> Any:
        """Get fact value or default."""
        return self.facts.get(fact_name, default)
    
    def set_fact(self, fact_name: str, value: Any) -> None:
        """Set or update a fact."""
        self.facts[fact_name] = value
    
    def remove_fact(self, fact_name: str) -> None:
        """Remove a fact from state."""
        if fact_name in self.facts:
            del self.facts[fact_name]
    
    def add_goal(self, goal: str) -> None:
        """Add a goal to achieve."""
        self.goals.add(goal)
    
    def remove_goal(self, goal: str) -> None:
        """Remove a goal."""
        self.goals.discard(goal)
    
    def has_goal(self, goal: str) -> bool:
        """Check if state has a goal."""
        return goal in self.goals
    
    def is_goal_satisfied(self, goal: str) -> bool:
        """
        Check if a goal is satisfied in current state.
        
        Args:
            goal: Goal fact name
            
        Returns:
            True if goal is satisfied
        """
        return self.has_fact(goal) and self.get_fact(goal) is True
    
    def all_goals_satisfied(self) -> bool:
        """Check if all goals are satisfied."""
        return all(self.is_goal_satisfied(goal) for goal in self.goals)
    
    def copy(self) -> 'State':
        """Create a deep copy of the state."""
        new_state = State(deepcopy(self.facts))
        new_state.goals = self.goals.copy()
        return new_state
    
    def __eq__(self, other) -> bool:
        """Check equality of states."""
        if not isinstance(other, State):
            return False
        return self.facts == other.facts and self.goals == other.goals
    
    def __hash__(self) -> int:
        """Make state hashable for use in sets/dicts."""
        return hash((tuple(sorted(self.facts.items())), tuple(sorted(self.goals))))
    
    def __repr__(self) -> str:
        return f"State(facts={len(self.facts)}, goals={len(self.goals)})"


class StateManager:
    """Manages state transitions and validation."""
    
    def __init__(self):
        """Initialize state manager."""
        self.current_state = State()
        logger.info("State Manager initialized")
    
    def apply_action_effects(self, action: Dict[str, Any], state: State) -> State:
        """
        Apply action effects to a state.
        
        Args:
            action: Action dictionary with 'effects' key
            state: Current state
            
        Returns:
            New state with effects applied
        """
        new_state = state.copy()
        effects = action.get("effects", {})
        
        for fact_name, fact_value in effects.items():
            new_state.set_fact(fact_name, fact_value)
        
        logger.debug(f"Applied effects from {action.get('name')} to state")
        return new_state
    
    def check_preconditions(self, action: Dict[str, Any], state: State) -> bool:
        """
        Check if action preconditions are met in state.
        
        Args:
            action: Action dictionary with 'preconditions' key
            state: Current state
            
        Returns:
            True if all preconditions are satisfied
        """
        preconditions = action.get("preconditions", {})
        
        for fact_name, required_value in preconditions.items():
            if not state.has_fact(fact_name):
                return False
            if state.get_fact(fact_name) != required_value:
                return False
        
        return True
    
    def generate_successor_states(
        self, 
        state: State, 
        available_actions: List[Dict[str, Any]]
    ) -> List[tuple[State, Dict[str, Any]]]:
        """
        Generate all valid successor states from current state.
        
        Args:
            state: Current state
            available_actions: List of available actions
            
        Returns:
            List of (new_state, action) tuples
        """
        successors = []
        
        for action in available_actions:
            if self.check_preconditions(action, state):
                new_state = self.apply_action_effects(action, state)
                successors.append((new_state, action))
        
        return successors
    
    def set_current_state(self, state: State) -> None:
        """Set the current world state."""
        self.current_state = state
    
    def get_current_state(self) -> State:
        """Get the current world state."""
        return self.current_state

