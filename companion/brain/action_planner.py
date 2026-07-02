"""
companion/brain/action_planner.py
==================================
Desktop Action Planner for AI Autonomy.
Plans and executes desktop operations (click, type, open apps).
Uses xdotool for native Linux automation.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Optional, Literal
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ActionPlan:
    """Represents a planned desktop action."""
    action_type: Literal["open_app", "click", "type", "scroll", "switch_window", "close_window"]
    target: str  # App name, coordinates, text, etc.
    params: dict = None
    safe_mode: bool = True  # Require confirmation if True
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}

class ActionPlanner:
    """
    Plans and executes desktop actions based on AI decisions.
    
    Features:
    - Open/close applications
    - Mouse click at coordinates
    - Type text into active window
    - Scroll up/down
    - Switch between windows
    - Safe mode for dangerous actions
    """
    
    def __init__(self, safe_mode: bool = True) -> None:
        self.safe_mode = safe_mode
        self._execution_lock = asyncio.Lock()
        self._pending_confirmations: list[ActionPlan] = []
    
    async def execute(self, plan: ActionPlan) -> bool:
        """Execute an action plan."""
        async with self._execution_lock:
            try:
                # Check safe mode
                if self.safe_mode and plan.safe_mode:
                    logger.warning(f"Safe mode: Action '{plan.action_type}' requires confirmation")
                    self._pending_confirmations.append(plan)
                    return False  # Waiting for human confirmation
                
                # Execute based on action type
                if plan.action_type == "open_app":
                    return await self._open_application(plan.target)
                elif plan.action_type == "click":
                    return await self._click(plan.target, plan.params)
                elif plan.action_type == "type":
                    return await self._type_text(plan.target, plan.params)
                elif plan.action_type == "scroll":
                    return await self._scroll(plan.params)
                elif plan.action_type == "switch_window":
                    return await self._switch_window(plan.target)
                elif plan.action_type == "close_window":
                    return await self._close_window(plan.target)
                else:
                    logger.error(f"Unknown action type: {plan.action_type}")
                    return False
                    
            except Exception as e:
                logger.error(f"Action execution failed: {e}")
                return False
    
    async def _open_application(self, app_name: str) -> bool:
        """Open an application by name."""
        try:
            # Try to find and launch the app
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "search", "--name", app_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await proc.communicate()
            
            if stdout.strip():
                # Window already exists, activate it
                window_id = stdout.decode().strip().split('\n')[0]
                await asyncio.create_subprocess_exec("xdotool", "windowactivate", window_id)
                logger.info(f"Activated existing window: {app_name}")
                return True
            
            # Launch new instance
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "search", "--onlyvisible", "--name", ".*",
                stdout=asyncio.subprocess.PIPE
            )
            # Just try to run the app directly
            proc = await asyncio.create_subprocess_exec(app_name.lower())
            logger.info(f"Launched application: {app_name}")
            return True
            
        except FileNotFoundError:
            logger.error(f"Application not found: {app_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to open app: {e}")
            return False
    
    async def _click(self, target: str, params: dict) -> bool:
        """Click at specified coordinates or on element."""
        try:
            x = params.get("x", 0)
            y = params.get("y", 0)
            button = params.get("button", 1)  # 1=left, 2=middle, 3=right
            
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "mousemove", str(x), str(y), "click", str(button)
            )
            await proc.wait()
            
            logger.info(f"Clicked at ({x}, {y}) with button {button}")
            return True
            
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False
    
    async def _type_text(self, text: str, params: dict) -> bool:
        """Type text into active window."""
        try:
            delay = params.get("delay", 50)  # ms between keystrokes
            
            # Escape special characters
            safe_text = text.replace("\\", "\\\\").replace("'", "\\'")
            
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "type", "--delay", str(delay), safe_text
            )
            await proc.wait()
            
            logger.info(f"Typed text: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return False
    
    async def _scroll(self, params: dict) -> bool:
        """Scroll up or down."""
        try:
            direction = params.get("direction", "down")  # "up" or "down"
            amount = params.get("amount", 3)  # Number of scroll units
            
            button = 4 if direction == "up" else 5  # 4=up, 5=down
            
            for _ in range(amount):
                proc = await asyncio.create_subprocess_exec(
                    "xdotool", "click", str(button)
                )
                await proc.wait()
                await asyncio.sleep(0.1)
            
            logger.info(f"Scrolled {direction} {amount} times")
            return True
            
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False
    
    async def _switch_window(self, target: str) -> bool:
        """Switch to window matching target name."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "search", "--name", target,
                stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            
            if not stdout.strip():
                logger.warning(f"No window found matching: {target}")
                return False
            
            window_id = stdout.decode().strip().split('\n')[0]
            
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "windowactivate", window_id
            )
            await proc.wait()
            
            logger.info(f"Switched to window: {target}")
            return True
            
        except Exception as e:
            logger.error(f"Window switch failed: {e}")
            return False
    
    async def _close_window(self, target: str) -> bool:
        """Close window matching target name."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "search", "--name", target,
                stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            
            if not stdout.strip():
                logger.warning(f"No window found matching: {target}")
                return False
            
            window_id = stdout.decode().strip().split('\n')[0]
            
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "windowclose", window_id
            )
            await proc.wait()
            
            logger.info(f"Closed window: {target}")
            return True
            
        except Exception as e:
            logger.error(f"Window close failed: {e}")
            return False
    
    def confirm_action(self, index: int = 0) -> bool:
        """Confirm a pending action (for safe mode)."""
        if not self._pending_confirmations:
            return False
        
        if index < 0 or index >= len(self._pending_confirmations):
            return False
        
        plan = self._pending_confirmations.pop(index)
        plan.safe_mode = False
        
        # Execute asynchronously
        asyncio.create_task(self.execute(plan))
        return True
    
    def cancel_pending(self) -> None:
        """Cancel all pending confirmations."""
        self._pending_confirmations.clear()
        logger.info("Cancelled all pending actions")


# Singleton instance
_planner_instance: Optional[ActionPlanner] = None

def get_action_planner() -> Optional[ActionPlanner]:
    """Get the global ActionPlanner instance."""
    global _planner_instance
    return _planner_instance

def create_action_planner(safe_mode: bool = True) -> ActionPlanner:
    """Create the global ActionPlanner instance."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = ActionPlanner(safe_mode)
    return _planner_instance
