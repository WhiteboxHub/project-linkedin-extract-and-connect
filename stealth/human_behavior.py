# stealth/human_behavior.py
"""
Human behavior simulation for natural interactions.
Provides realistic mouse movements, typing, scrolling, and pauses.
"""

import random
import time
import logging
from typing import Optional, Tuple, List
import numpy as np
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc

from .timing import (
    get_typing_delay,
    get_scroll_delay,
    get_click_delay,
    random_pause as timing_random_pause,
    reading_pause as timing_reading_pause,
)

logger = logging.getLogger(__name__)


class HumanBehavior:
    """Simulates natural human interactions with the browser."""
    
    def __init__(self):
        """Initialize human behavior simulator."""
        self.last_action_time = time.time()
    
    def _generate_bezier_curve(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        num_points: int = 20
    ) -> List[Tuple[int, int]]:
        """
        Generate a Bezier curve for natural mouse movement.
        
        Args:
            start: Starting (x, y) coordinates
            end: Ending (x, y) coordinates
            num_points: Number of points in the curve
            
        Returns:
            List of (x, y) coordinates along the curve
        """
        # Generate control points for cubic Bezier curve
        x0, y0 = start
        x3, y3 = end
        
        # Add randomness to control points
        x1 = x0 + (x3 - x0) * random.uniform(0.2, 0.4)
        y1 = y0 + (y3 - y0) * random.uniform(-0.3, 0.3)
        
        x2 = x0 + (x3 - x0) * random.uniform(0.6, 0.8)
        y2 = y0 + (y3 - y0) * random.uniform(-0.3, 0.3)
        
        # Generate curve points
        points = []
        for i in range(num_points):
            t = i / (num_points - 1)
            
            # Cubic Bezier formula
            x = (1-t)**3 * x0 + 3*(1-t)**2*t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x3
            y = (1-t)**3 * y0 + 3*(1-t)**2*t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y3
            
            points.append((int(x), int(y)))
        
        return points
    
    def move_to_element(
        self,
        driver: uc.Chrome,
        element: WebElement,
        smooth: bool = True
    ) -> None:
        """
        Move mouse to element with natural movement.
        
        Args:
            driver: Chrome driver instance
            element: Target element
            smooth: Whether to use smooth Bezier curve movement
        """
        try:
            if smooth:
                # Get element location
                location = element.location
                size = element.size
                
                # Target center of element
                target_x = location['x'] + size['width'] // 2
                target_y = location['y'] + size['height'] // 2
                
                logger.debug(f"Moving mouse to element at ({target_x}, {target_y})")
                
                # Use ActionChains for smooth movement
                actions = ActionChains(driver)
                actions.move_to_element(element).perform()
            else:
                # Simple move
                actions = ActionChains(driver)
                actions.move_to_element(element).perform()
            
            # Small delay after movement
            time.sleep(random.uniform(0.1, 0.3))
            
        except Exception as e:
            logger.error(f"Error moving to element: {e}")
            raise
    
    def human_click(
        self,
        driver: uc.Chrome,
        element: WebElement,
        move_first: bool = True
    ) -> None:
        """
        Click element with human-like behavior.
        
        Args:
            driver: Chrome driver instance
            element: Element to click
            move_first: Whether to move to element first
        """
        try:
            # Pre-click pause (hesitation)
            time.sleep(get_click_delay())
            
            if move_first:
                self.move_to_element(driver, element)
            
            # Click
            logger.debug("Clicking element")
            element.click()
            
            # Post-click pause
            time.sleep(random.uniform(0.2, 0.5))
            
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            raise
    
    def human_type(
        self,
        element: WebElement,
        text: str,
        clear_first: bool = True
    ) -> None:
        """
        Type text with variable human-like speed.
        
        Args:
            element: Input element
            text: Text to type
            clear_first: Whether to clear field first
        """
        try:
            if clear_first:
                element.clear()
                time.sleep(random.uniform(0.1, 0.3))
            
            logger.debug(f"Typing text: {text[:20]}...")
            
            # Type character by character with variable delays
            for char in text:
                element.send_keys(char)
                time.sleep(get_typing_delay())
            
            # Pause after typing
            time.sleep(random.uniform(0.3, 0.7))
            
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            raise
    
    def random_scroll(
        self,
        driver: uc.Chrome,
        direction: str = "down",
        amount: Optional[int] = None
    ) -> None:
        """
        Scroll with natural patterns.
        
        Args:
            driver: Chrome driver instance
            direction: "up" or "down"
            amount: Scroll amount in pixels (random if None)
        """
        try:
            if amount is None:
                # Random scroll amount (200-600 pixels)
                amount = random.randint(200, 600)
            
            # Negative for up, positive for down
            scroll_amount = amount if direction == "down" else -amount
            
            logger.debug(f"Scrolling {direction} by {amount}px")
            
            # Smooth scroll with easing
            steps = random.randint(5, 10)
            for i in range(steps):
                step_amount = scroll_amount // steps
                driver.execute_script(f"window.scrollBy(0, {step_amount});")
                time.sleep(get_scroll_delay() / steps)
            
            # Pause after scrolling
            time.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            raise
    
    def random_mouse_movement(self, driver: uc.Chrome) -> None:
        """
        Perform random mouse movement to simulate natural behavior.
        
        Args:
            driver: Chrome driver instance
        """
        try:
            # Random movement within viewport
            viewport_width = driver.execute_script("return window.innerWidth;")
            viewport_height = driver.execute_script("return window.innerHeight;")
            
            # Random target within central 80% of viewport
            target_x = random.randint(int(viewport_width * 0.1), int(viewport_width * 0.9))
            target_y = random.randint(int(viewport_height * 0.1), int(viewport_height * 0.9))
            
            logger.debug(f"Random mouse movement to ({target_x}, {target_y})")
            
            # Move using JavaScript (more reliable than ActionChains for random movement)
            driver.execute_script(f"""
                var event = new MouseEvent('mousemove', {{
                    'view': window,
                    'bubbles': true,
                    'cancelable': true,
                    'clientX': {target_x},
                    'clientY': {target_y}
                }});
                document.dispatchEvent(event);
            """)
            
            time.sleep(random.uniform(0.1, 0.3))
            
        except Exception as e:
            logger.debug(f"Random mouse movement failed (non-critical): {e}")
    
    def random_pause(self, min_seconds: float = 0.5, max_seconds: float = 3.0) -> None:
        """
        Pause for a random duration.
        
        Args:
            min_seconds: Minimum pause duration
            max_seconds: Maximum pause duration
        """
        timing_random_pause(min_seconds, max_seconds)
    
    def reading_pause(self, text: str) -> None:
        """
        Pause based on text length to simulate reading.
        
        Args:
            text: Text content to "read"
        """
        timing_reading_pause(text)
    
    def natural_delay(self) -> None:
        """
        Add a natural delay between actions.
        Ensures minimum time between actions to avoid detection.
        """
        elapsed = time.time() - self.last_action_time
        min_delay = 0.5  # Minimum 500ms between actions
        
        if elapsed < min_delay:
            time.sleep(min_delay - elapsed)
        
        self.last_action_time = time.time()
