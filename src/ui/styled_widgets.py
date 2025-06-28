"""Custom styled widgets for dark theme"""
import tkinter as tk
from tkinter import ttk
from .theme import DARK_THEME


class StyledFrame(tk.Frame):
    def __init__(self, parent, bg_type='primary', **kwargs):
        bg_color = DARK_THEME[f'bg_{bg_type}']
        super().__init__(parent, bg=bg_color, **kwargs)


class StyledLabel(tk.Label):
    def __init__(self, parent, text="", style='primary', size='md', **kwargs):
        defaults = {
            'bg': DARK_THEME['bg_primary'],
            'fg': DARK_THEME[f'text_{style}'],
            'font': (DARK_THEME['font_family'], DARK_THEME[f'font_size_{size}']),
        }
        defaults.update(kwargs)
        super().__init__(parent, text=text, **defaults)


class StyledButton(tk.Button):
    def __init__(self, parent, text="", **kwargs):
        defaults = {
            'bg': DARK_THEME['button_bg'],
            'fg': DARK_THEME['text_primary'],
            'activebackground': DARK_THEME['button_hover'],
            'activeforeground': DARK_THEME['text_primary'],
            'font': (DARK_THEME['font_family'], DARK_THEME['font_size_md']),
            'relief': 'flat',
            'cursor': 'hand2',
            'padx': 20,
            'pady': 8,
        }
        defaults.update(kwargs)
        super().__init__(parent, text=text, **defaults)
        
        # Bind hover effects
        self.bind('<Enter>', lambda e: self.config(bg=DARK_THEME['button_hover']))
        self.bind('<Leave>', lambda e: self.config(bg=DARK_THEME['button_bg']))


class PositionBadge(tk.Label):
    def __init__(self, parent, position, **kwargs):
        bg_color = DARK_THEME[f'pos_{position.lower()}']
        super().__init__(
            parent,
            text=position,
            bg=bg_color,
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=6,
            pady=2,
            **kwargs
        )