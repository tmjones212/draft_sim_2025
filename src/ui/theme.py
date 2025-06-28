"""Dark theme configuration for the draft simulator"""

DARK_THEME = {
    # Main colors
    'bg_primary': '#0e1117',      # Main background
    'bg_secondary': '#1a1d24',    # Secondary background (panels)
    'bg_tertiary': '#252830',     # Tertiary background (cards)
    'bg_hover': '#2d3139',        # Hover state
    
    # Text colors
    'text_primary': '#ffffff',     # Primary text
    'text_secondary': '#8b92a8',   # Secondary text
    'text_muted': '#5a6171',       # Muted text
    
    # Position colors (matching Sleeper)
    'pos_qb': '#f8296d',          # QB - Pink/Red
    'pos_rb': '#36ceb8',          # RB - Teal
    'pos_wr': '#58a7ff',          # WR - Blue
    'pos_te': '#faae58',          # TE - Orange
    'pos_def': '#bd66ff',         # DEF - Purple
    'pos_k': '#bd66ff',           # K - Purple
    
    # UI elements
    'border': '#2d3139',          # Border color
    'divider': '#1e2127',         # Divider lines
    'button_bg': '#5a6171',       # Button background
    'button_hover': '#6b7280',    # Button hover
    'button_active': '#4ade80',   # Active/success button
    
    # Draft specific
    'pick_bg': '#1a1d24',         # Draft pick background
    'pick_border': '#2d3139',     # Draft pick border
    'current_pick': '#4ade80',    # Current pick highlight
    
    # Fonts
    'font_family': 'Segoe UI',
    'font_size_sm': 11,
    'font_size_md': 12,
    'font_size_lg': 14,
    'font_size_xl': 16,
}

def get_position_color(position: str) -> str:
    """Get the color for a specific position"""
    pos_key = f'pos_{position.lower()}'
    return DARK_THEME.get(pos_key, DARK_THEME['text_secondary'])