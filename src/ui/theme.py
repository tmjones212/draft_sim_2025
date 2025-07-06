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
    'pos_lb': '#8A2BE2',          # LB - Violet/Purple
    'pos_db': '#9370DB',          # DB - Medium Purple
    
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

# NFL Team Colors - Primary and secondary colors (adjusted for visibility)
TEAM_COLORS = {
    'BAL': ['#6B4C9A', '#FFB612'],  # Ravens: Purple, Gold
    'CIN': ['#FB4F14', '#FFFFFF'],  # Bengals: Orange, White
    'CLE': ['#FF3C00', '#964B00'],  # Browns: Orange, Brown
    'PIT': ['#FFB612', '#FFFFFF'],  # Steelers: Gold, White
    'BUF': ['#00338D', '#C60C30'],  # Bills: Blue, Red
    'MIA': ['#008E97', '#FC4C02'],  # Dolphins: Aqua, Orange
    'NE': ['#002244', '#C60C30'],  # Patriots: Navy, Red
    'NYJ': ['#125740', '#FFFFFF'],  # Jets: Green, White
    'HOU': ['#03202F', '#A71930'],  # Texans: Navy, Red
    'IND': ['#002C5F', '#A2AAAD'],  # Colts: Blue, Gray
    'JAX': ['#101820', '#D7A22A'],  # Jaguars: Black, Gold
    'TEN': ['#0C2340', '#4B92DB'],  # Titans: Navy, Light Blue
    'DEN': ['#FB4F14', '#002244'],  # Broncos: Orange, Navy
    'KC': ['#E31837', '#FFB81C'],  # Chiefs: Red, Yellow
    'LV': ['#A5ACAF', '#000000'],  # Raiders: Silver, Black (swapped for visibility)
    'LAC': ['#0080C6', '#FFC20E'],  # Chargers: Blue, Yellow
    'CHI': ['#0B162A', '#C83803'],  # Bears: Navy, Orange
    'DET': ['#0076B6', '#B0B7BC'],  # Lions: Blue, Silver
    'GB': ['#203731', '#FFB612'],  # Packers: Green, Gold
    'MIN': ['#4F2683', '#FFC62F'],  # Vikings: Purple, Gold
    'DAL': ['#003594', '#869397'],  # Cowboys: Blue, Silver
    'NYG': ['#0B2265', '#A71930'],  # Giants: Blue, Red
    'PHI': ['#004C54', '#A5ACAF'],  # Eagles: Green, Silver
    'WAS': ['#5A1414', '#FFB612'],  # Commanders: Burgundy, Gold
    'ATL': ['#A71930', '#A5ACAF'],  # Falcons: Red, Silver
    'CAR': ['#0085CA', '#BFC0BF'],  # Panthers: Blue, Silver
    'NO': ['#D3BC8D', '#FFFFFF'],  # Saints: Gold, White
    'TB': ['#D50A0A', '#FF7900'],  # Buccaneers: Red, Orange
    'ARI': ['#97233F', '#FFB612'],  # Cardinals: Red, Yellow
    'LAR': ['#003594', '#FFD100'],  # Rams: Blue, Gold
    'SF': ['#AA0000', '#B3995D'],  # 49ers: Red, Gold
    'SEA': ['#002244', '#69BE28'],  # Seahawks: Navy, Green
}

def get_team_color(team: str, secondary: bool = False) -> str:
    """Get the primary or secondary color for a specific team"""
    colors = TEAM_COLORS.get(team, ['#888888', '#CCCCCC'])  # Default gray if team not found
    return colors[1] if secondary and len(colors) > 1 else colors[0]