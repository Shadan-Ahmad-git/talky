"""
A* Search Algorithm implementation for optimal action planning.
Generates optimal action sequences to achieve goal states.
"""
import logging
import heapq
from typing import List, Dict, Any, Optional, Set
from planning.knowledge_base import KnowledgeBase
from planning.state_manager import State, StateManager

logger = logging.getLogger(__name__)


class Node:
    """Node in the search graph for A* algorithm."""
    
    def __init__(
        self,
        state: State,
        parent: Optional['Node'] = None,
        action: Optional[Dict[str, Any]] = None,
        g_cost: float = 0.0,
        h_cost: float = 0.0
    ):
        self.state = state
        self.parent = parent
        self.action = action
        self.g_cost = g_cost  # Cost from start to this node
        self.h_cost = h_cost  # Heuristic cost to goal
        self.f_cost = g_cost + h_cost  # Total estimated cost
    
    def __lt__(self, other):
        """Compare nodes for priority queue (lower f_cost is better)."""
        return self.f_cost < other.f_cost
    
    def __eq__(self, other):
        """Check node equality based on state."""
        if not isinstance(other, Node):
            return False
        return self.state == other.state
    
    def __hash__(self):
        """Make node hashable."""
        return hash(self.state)


class AStarPlanner:
    """A* search planner for generating optimal action plans."""
    
    def __init__(self, knowledge_base: KnowledgeBase, state_manager: StateManager):
        """
        Initialize A* planner.
        
        Args:
            knowledge_base: Knowledge base with action definitions
            state_manager: State manager for state transitions
        """
        self.kb = knowledge_base
        self.state_manager = state_manager
        logger.info("A* Planner initialized")
    
    def plan(
        self, 
        current_state: State, 
        goal_state: State,
        max_iterations: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Generate optimal action plan using A* search.
        
        Args:
            current_state: Starting state
            goal_state: Goal state to achieve
            max_iterations: Maximum search iterations
            
        Returns:
            List of actions to execute (empty if no plan found)
        """
        logger.info("Starting A* planning")
        
        # Check if goal is already satisfied at start
        if self._is_goal_reached(current_state, goal_state):
            logger.warning("Goal already satisfied at start - no actions needed")
            return []  # Return empty plan if goal already satisfied
        
        # Initialize search
        start_node = Node(
            state=current_state.copy(),
            g_cost=0.0,
            h_cost=self.calculate_heuristic(current_state, goal_state)
        )
        
        open_set = [start_node]  # Priority queue
        closed_set: Set[State] = set()
        visited_states: Set[State] = {start_node.state}
        
        iteration = 0
        
        while open_set and iteration < max_iterations:
            iteration += 1
            
            # Get node with lowest f_cost
            current_node = heapq.heappop(open_set)
            
            # Check if goal is reached
            if self._is_goal_reached(current_node.state, goal_state):
                logger.info(f"Goal reached after {iteration} iterations")
                return self.reconstruct_path(current_node)
            
            # Add to closed set
            closed_set.add(current_node.state)
            
            # Generate successors
            available_actions = self.kb.get_available_actions()
            successors = self.state_manager.generate_successor_states(
                current_node.state,
                available_actions
            )
            
            logger.debug(f"Iteration {iteration}: Found {len(successors)} valid successor actions")
            
            for new_state, action in successors:
                # Skip if already visited
                if new_state in closed_set:
                    continue
                
                # Calculate costs
                action_cost = self.kb.estimate_action_cost(action, current_node.state.facts)
                new_g_cost = current_node.g_cost + action_cost
                new_h_cost = self.calculate_heuristic(new_state, goal_state)
                
                # Create new node
                new_node = Node(
                    state=new_state,
                    parent=current_node,
                    action=action,
                    g_cost=new_g_cost,
                    h_cost=new_h_cost
                )
                
                # Add to open set if not visited or has better cost
                if new_state not in visited_states:
                    heapq.heappush(open_set, new_node)
                    visited_states.add(new_state)
                else:
                    # Check if we found a better path
                    for i, existing_node in enumerate(open_set):
                        if existing_node.state == new_state and new_node.f_cost < existing_node.f_cost:
                            open_set[i] = new_node
                            heapq.heapify(open_set)
                            break
        
        logger.warning(f"No plan found after {iteration} iterations")
        return []
    
    def calculate_heuristic(self, state: State, goal_state: State) -> float:
        """
        Calculate heuristic (estimated cost to goal).
        
        Args:
            state: Current state
            goal_state: Goal state
            
        Returns:
            Estimated cost to reach goal
        """
        # Count unsatisfied goals
        unsatisfied_goals = 0
        for goal in goal_state.goals:
            if not state.is_goal_satisfied(goal):
                unsatisfied_goals += 1
        
        # Estimate cost based on number of unsatisfied goals
        # Assume average action cost of 2.0
        estimated_actions = unsatisfied_goals * 1.5
        return estimated_actions * 2.0
    
    def _is_goal_reached(self, state: State, goal_state: State) -> bool:
        """
        Check if goal state is reached.
        
        Args:
            state: Current state
            goal_state: Goal state (contains the goals to check)
            
        Returns:
            True if all goals from goal_state are satisfied in current state
        """
        # If no goals, return False (we need at least one goal to reach)
        if not goal_state.goals:
            return False
        
        # Check if current state satisfies all goals in goal_state
        for goal in goal_state.goals:
            if not state.is_goal_satisfied(goal):
                logger.debug(f"Goal '{goal}' not satisfied. State has fact: {state.has_fact(goal)}, value: {state.get_fact(goal)}")
                return False
        
        logger.debug(f"All goals satisfied: {goal_state.goals}")
        return True
    
    def generate_successors(
        self, 
        state: State
    ) -> List[tuple[State, Dict[str, Any]]]:
        """
        Generate all valid successor states.
        
        Args:
            state: Current state
            
        Returns:
            List of (new_state, action) tuples
        """
        available_actions = self.kb.get_available_actions()
        return self.state_manager.generate_successor_states(state, available_actions)
    
    def reconstruct_path(self, goal_node: Node) -> List[Dict[str, Any]]:
        """
        Reconstruct action sequence from goal node.
        
        Args:
            goal_node: Final node in search path
            
        Returns:
            List of actions from start to goal
        """
        path = []
        current = goal_node
        
        while current.parent is not None:
            if current.action:
                path.insert(0, current.action)
            current = current.parent
        
        logger.info(f"Reconstructed path with {len(path)} actions")
        return path
    
    def validate_plan(
        self, 
        plan: List[Dict[str, Any]], 
        initial_state: State
    ) -> bool:
        """
        Validate that plan is executable from initial state.
        
        Args:
            plan: List of actions
            initial_state: Starting state
            
        Returns:
            True if plan is valid
        """
        current_state = initial_state.copy()
        
        for action in plan:
            if not self.state_manager.check_preconditions(action, current_state):
                logger.warning(f"Plan validation failed at action: {action.get('name')}")
                return False
            
            current_state = self.state_manager.apply_action_effects(action, current_state)
        
        return True
    
    def generate_alternative_plans(
        self, 
        state: State, 
        goal_state: State,
        num_alternatives: int = 3
    ) -> List[List[Dict[str, Any]]]:
        """
        Generate alternative plans (if available).
        
        Args:
            state: Current state
            goal_state: Goal state
            num_alternatives: Number of alternative plans to generate
            
        Returns:
            List of alternative plans
        """
        # For now, return single optimal plan
        # Could be extended to find k-best plans
        plan = self.plan(state, goal_state)
        return [plan] if plan else []

