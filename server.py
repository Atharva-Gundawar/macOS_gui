import traceback
from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage
from typing import List
from macapptree import get_tree_screenshot, get_app_bundle
import pyautogui

import time
import signal
import sys
import subprocess

def get_center_point(bbox):
    """Calculate center point from bounding box coordinates."""
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    return (center_x, center_y)

def extract_elements(tree):
    """
    Extract buttons and text areas from accessibility tree.
    Returns two lists containing center points of buttons and text areas.
    """
    buttons = []
    text_areas = []
    
    window_absolute_position = tree['absolute_position'].split(',')
    window_x = float(window_absolute_position[0])
    window_y = float(window_absolute_position[1])

    def traverse(node):
        # Check if node is a button
        if node.get('role') in ['AXButton', 'AXMenuButton'] and 'visible_bbox' in node:
            center = get_center_point(node['visible_bbox'])
            buttons.append({
                'center': (center[0] + window_x, center[1] + window_y),
                'description': node.get('description'),
                'role_description': node.get('role_description')
            })
        
        # Check if node is a text area
        elif node.get('role') == 'AXTextArea' and 'visible_bbox' in node:
            center = get_center_point(node['visible_bbox'])
            text_areas.append({
                'center': (center[0] + window_x, center[1] + window_y),
                'description': node.get('description'),
                'role_description': node.get('role_description')
            })

        # Recursively process children
        children = node.get('children', [])
        for child in children:
            traverse(child)

    traverse(tree)
    return buttons, text_areas

def get_ui_elements(tree_json):
    """
    Main function to get buttons and text areas from accessibility tree JSON.
    Returns:
        tuple: (buttons, text_areas) where each is a list of dictionaries containing
               center points and metadata for the UI elements
    """
    buttons, text_areas = extract_elements(tree_json)
    return buttons, text_areas

# Handle SIGINT (Ctrl+C) gracefully
def signal_handler(sig, frame):
    print("Shutting down server gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Create an MCP server with increased timeout
mcp = FastMCP(
    name="GUI-tools",
    host="127.0.0.1",
    port=5000,
    # Add this to make the server more resilient
    timeout=60  # Increase timeout to 60 seconds
)

@mcp.tool()
def get_screen_buttons_textarea(bundle_id: str) -> tuple[Image, str, str] | str:
    """Get the screenshot of the opened app, coordinates of its buttons and textarea. Needs the bundle id of the app.
    
    Args:
        bundle_id: str - The bundle id of the app to get the screenshot, buttons, and textarea of.
        
    Returns:
        tuple[Image, str, str]: A tuple containing the screenshot of the opened app, coordinates of its buttons, and coordinates of its textarea.
        
    Bundle ids:
        - Notes: com.apple.Notes
        - Voice Memos: com.apple.VoiceMemos
        - Mail: com.apple.Mail
        - Reminders: com.apple.reminders
        - Safari: com.apple.Safari
        - Maps: com.apple.Maps
        - Photos: com.apple.Photos
        - Music: com.apple.Music
        - Weather: com.apple.weather
        
    """
    try:
        # Check if bundle id is valid
        valid_bundle_ids = [
            "com.apple.Notes",
            "com.apple.VoiceMemos",
            "com.apple.Mail", 
            "com.apple.reminders",
            "com.apple.Safari",
            "com.apple.Maps",
            "com.apple.Photos",
            "com.apple.Music",
            "com.apple.weather"
        ]
        
        if bundle_id not in valid_bundle_ids:
            return f"Error: Invalid bundle ID. Please use one of: {', '.join(valid_bundle_ids)}"
        
        # Open the app using the app name
        print(f"Opening {bundle_id}")
        print(f"Running command: open -b {bundle_id}")
        subprocess.call(["open", "-b", bundle_id])
        time.sleep(5)
        bundle = get_app_bundle(bundle_id.split('.')[-1])
        
        # Get the screenshot of the opened app and its tree
        tree, im, im_seg = get_tree_screenshot(bundle)
        # Get the coordinates of the buttons and textarea
        buttons, text_areas = get_ui_elements(tree)
        # Return the screenshot, buttons, and textarea
        return im, buttons, text_areas
    
    except Exception as e:
        print(f"Error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
    
@mcp.tool()
def mouse_move_and_click(x: int, y: int) -> str:
    """Go to the given coordinates and click"""
    try:
        pyautogui.moveTo(x, y)
        pyautogui.click()
        return "Success"
    except Exception as e:
        return "Error: " + str(e)

@mcp.tool()
def type_text(text: str, press_enter_after: bool = True) -> str:
    """Type text at the current cursor position.
    
    Args:
        text: str - The text to type. Use backslash n to create a new line.
        press_enter_after: bool - Whether to press enter after typing the text.
    """
    try:
        # Split text by \n and type each line separately
        lines = text.split('\\n')
        for i, line in enumerate(lines):
            pyautogui.typewrite(line)
            # Press enter between lines, but not after the last line unless specified
            if i < len(lines) - 1 or press_enter_after:
                pyautogui.press('enter')
        return "Success"
    except Exception as e:
        return "Error: " + str(e)

if __name__ == "__main__":
    try:
        print("Starting MCP server 'GUI-tools' on 127.0.0.1:5000")
        # Use this approach to keep the server running
        mcp.run()
    except Exception as e:
        print(f"Error: {e}")
        # Sleep before exiting to give time for error logs
        time.sleep(5)