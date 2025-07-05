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
    'text_accent': '#bd66ff',      # Accent color (purple for stars)
    
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
    'button_active': '#2d7a4e',   # Active/success button (toned down green)
    'button_glow': '#58a7ff',     # Glowing button color
    'button_glow_alt': '#36ceb8', # Alternative glow color
    
    # Draft specific
    'pick_bg': '#1a1d24',         # Draft pick background
    'pick_border': '#2d3139',     # Draft pick border
    'current_pick': '#2d7a4e',    # Current pick highlight (toned down green)
    
    # Status colors
    'accent_success': '#2d7a4e',  # Success/good (green)
    'accent_warning': '#faae58',  # Warning/fair (orange)
    'accent_error': '#f8296d',    # Error/bad (red)
    
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

# NFL Team Colors - Primary color for each team (adjusted for visibility on dark background)
TEAM_COLORS = {
    'BAL': '#6B4C9A',  # Ravens Purple (brightened)
    'CIN': '#FB4F14',  # Bengals Orange
    'CLE': '#FF3C00',  # Browns Orange (using secondary color)
    'PIT': '#FFB612',  # Steelers Gold
    'BUF': '#00338D',  # Bills Blue
    'MIA': '#008E97',  # Dolphins Aqua
    'NE': '#C60C30',  # Patriots Red (using secondary)
    'NYJ': '#125740',  # Jets Green
    'HOU': '#A71930',  # Texans Red (using secondary)
    'IND': '#0080C6',  # Colts Blue (brightened)
    'JAX': '#006778',  # Jaguars Teal (using secondary)
    'TEN': '#4B92DB',  # Titans Light Blue (using secondary)
    'DEN': '#FB4F14',  # Broncos Orange
    'KC': '#E31837',   # Chiefs Red
    'LV': '#A5ACAF',  # Raiders Silver (using secondary)
    'LAC': '#0080C6',  # Chargers Blue
    'CHI': '#C83803',  # Bears Orange (using secondary)
    'DET': '#0076B6',  # Lions Blue
    'GB': '#FFB612',   # Packers Gold (using secondary)
    'MIN': '#4F2683',  # Vikings Purple
    'DAL': '#869397',  # Cowboys Silver (using secondary)
    'NYG': '#A71930',  # Giants Red (using secondary)
    'PHI': '#004C54',  # Eagles Green
    'WAS': '#FFB612',  # Commanders Gold (using secondary)
    'ATL': '#A71930',  # Falcons Red
    'CAR': '#0085CA',  # Panthers Blue
    'NO': '#D3BC8D',   # Saints Gold
    'TB': '#FF7900',   # Buccaneers Orange (using secondary)
    'ARI': '#97233F',  # Cardinals Red
    'LAR': '#FFD100',  # Rams Gold (using secondary)
    'SF': '#B3995D',   # 49ers Gold (using secondary)
    'SEA': '#69BE28',  # Seahawks Green (using secondary)
}

def get_team_color(team: str) -> str:
    """Get the primary color for a specific team"""
    return TEAM_COLORS.get(team, '#888888')  # Default gray if team not found