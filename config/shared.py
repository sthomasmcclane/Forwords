#!/usr/bin/env python3
"""
Shared configuration utilities for Forwords
Used by both GUI and CLI versions
"""

import os
import random
from pathlib import Path

# Get the directory where this script is located
CONFIG_DIR = Path(__file__).parent

def load_colors():
    """Load color definitions from config/colors.txt"""
    colors = {}
    colors_file = CONFIG_DIR / 'colors.txt'
    
    if colors_file.exists():
        with open(colors_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    colors[key.strip()] = value.strip()
    
    return colors

def load_prompts():
    """Load prompt components from config/prompts.txt"""
    prompts = {}
    prompts_file = CONFIG_DIR / 'prompts.txt'
    
    if prompts_file.exists():
        with open(prompts_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    prompts[key.strip()] = [item.strip() for item in value.split(',')]
    
    return prompts

def generate_style_prompt():
    """Generate a random writing style prompt using the shared components"""
    prompts = load_prompts()
    
    if not prompts:
        return "Write a story with your own style."
    
    # Select random components
    voice = random.choice(prompts.get('VOICE', ['conversational']))
    tone = random.choice(prompts.get('TONE', ['neutral']))
    pace = random.choice(prompts.get('PACE', ['steadily']))
    pov = random.choice(prompts.get('POV', ['first-person']))
    tense = random.choice(prompts.get('TENSE', ['present']))
    genre = random.choice(prompts.get('GENRE', ['contemporary']))
    setting = random.choice(prompts.get('SETTING', ['urban']))
    
    return f"Write a {tone} {genre} story set in a {setting} environment. Use a {voice} voice with {pace} pacing in {tense}-tense from a {pov} perspective."

def get_banner_colors():
    """Get banner color mappings for GUI"""
    colors = load_colors()
    return {
        'BLUE': colors.get('BLUE', '#1a73e8'),
        'RED': colors.get('RED', '#ea4335'),
        'GREEN': colors.get('GREEN', '#34a853'),
        'YELLOW': colors.get('YELLOW', '#fbbc05'),
        'MAGENTA': colors.get('MAGENTA', '#d93025'),
        'CYAN': colors.get('CYAN', '#4285f4'),
        'WHITE': colors.get('WHITE', '#ffffff')
    }

def get_theme_colors():
    """Get theme color mappings for GUI"""
    colors = load_colors()
    return {
        'light': {
            'window': colors.get('LIGHT_WINDOW', '#ffffff'),
            'text': colors.get('LIGHT_TEXT', '#000000'),
            'banner': colors.get('LIGHT_BANNER', '#1a73e8'),
            'input_bg': colors.get('LIGHT_INPUT_BG', '#ffffff'),
            'input_text': colors.get('LIGHT_INPUT_TEXT', '#000000'),
            'button_bg': colors.get('LIGHT_BUTTON_BG', '#f0f0f0'),
            'button_text': colors.get('LIGHT_BUTTON_TEXT', '#000000')
        },
        'dark': {
            'window': colors.get('DARK_WINDOW', '#2d2d2d'),
            'text': colors.get('DARK_TEXT', '#ffffff'),
            'banner': colors.get('DARK_BANNER', '#8ab4f8'),
            'input_bg': colors.get('DARK_INPUT_BG', '#3d3d3d'),
            'input_text': colors.get('DARK_INPUT_TEXT', '#ffffff'),
            'button_bg': colors.get('DARK_BUTTON_BG', '#3d3d3d'),
            'button_text': colors.get('DARK_BUTTON_TEXT', '#ffffff')
        }
    } 