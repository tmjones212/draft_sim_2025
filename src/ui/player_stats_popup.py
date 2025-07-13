import tkinter as tk
from tkinter import ttk
from typing import Optional
import os
from PIL import Image, ImageTk
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from ..config.scoring import SCORING_CONFIG
from .player_selection_dialog import PlayerSelectionDialog
from .player_comparison_popup import PlayerComparisonPopup


class PlayerStatsPopup:
    def __init__(self, parent, player: Player, image_service=None, all_players=None):
        self.player = player
        self.parent = parent
        self.image_service = image_service
        self.all_players = all_players
        self.sort_column = None
        self.sort_ascending = True
        self.weekly_data = []  # Store weekly data for sorting
        
        # Create popup window
        self.window = tk.Toplevel(parent)
        self.window.title(f"{player.format_name()} - 2024 Stats")
        self.window.configure(bg=DARK_THEME['bg_primary'])
        
        # Hide window initially to prevent flashing
        self.window.withdraw()
        
        # Set window size - smaller without scrollbar
        self.window.geometry("800x600")
        
        # Center the window
        self.window.update_idletasks()
        screen_height = self.window.winfo_screenheight()
        window_height = 600
        
        x = (self.window.winfo_screenwidth() // 2) - (800 // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.window.geometry(f"800x{window_height}+{x}+{y}")
        
        # Show window after positioning
        self.window.deiconify()
        
        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()
        
        # Bind escape key to close
        self.window.bind('<Escape>', lambda e: self.close())
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = StyledFrame(self.window, bg_type='primary')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header with player info
        header_frame = StyledFrame(main_frame, bg_type='secondary')
        header_frame.pack(fill='x', pady=(0, 20))
        header_frame.configure(relief='flat', bd=1, highlightbackground=DARK_THEME['border'])
        
        # Player info container with 3 sections
        info_frame = tk.Frame(header_frame, bg=DARK_THEME['bg_secondary'])
        info_frame.pack(fill='x', padx=20, pady=15)
        
        # LEFT: Player name, position, and team
        left_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_secondary'])
        left_frame.pack(side='left', fill='both', expand=True)
        
        name_frame = tk.Frame(left_frame, bg=DARK_THEME['bg_secondary'])
        name_frame.pack(anchor='w')
        
        name_label = tk.Label(
            name_frame,
            text=self.player.format_name(),
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 20, 'bold')
        )
        name_label.pack(side='left', padx=(0, 10))
        
        # Position badge
        pos_bg = get_position_color(self.player.position)
        pos_label = tk.Label(
            name_frame,
            text=self.player.position,
            bg=pos_bg,
            fg='white',
            font=(DARK_THEME['font_family'], 12, 'bold'),
            padx=12,
            pady=4
        )
        pos_label.pack(side='left')
        
        # Team info
        if self.player.team:
            team_label = tk.Label(
                name_frame,
                text=f"• {self.player.team}",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 14)
            )
            team_label.pack(side='left', padx=(10, 0))
        
        # CENTER: Player image
        center_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_secondary'])
        center_frame.pack(side='left', padx=20)
        
        # Player image placeholder
        image_label = tk.Label(
            center_frame,
            bg=DARK_THEME['bg_tertiary'],
            width=80,
            height=80,
            text="",
            relief='flat'
        )
        image_label.pack()
        
        # Load player image if available
        if self.image_service and self.player.player_id:
            player_image = self.image_service.get_image(self.player.player_id, size=(80, 64))
            if player_image:
                image_label.configure(image=player_image)
                image_label.image = player_image  # Keep reference
            else:
                # Try to load async
                def update_image(photo):
                    if image_label.winfo_exists():
                        image_label.configure(image=photo)
                        image_label.image = photo
                
                self.image_service.load_image_async(
                    self.player.player_id,
                    size=(80, 64),
                    callback=update_image,
                    widget=self.window
                )
        
        # RIGHT: Season totals
        totals_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_secondary'])
        totals_frame.pack(side='right')
        
        if self.player.points_2024:
            total_label = tk.Label(
                totals_frame,
                text=f"2024 Total: {self.player.points_2024:.1f} pts",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 12, 'bold')
            )
            total_label.pack()
            
        if self.player.games_2024:
            avg_label = tk.Label(
                totals_frame,
                text=f"Games: {self.player.games_2024} | Avg: {self.player.points_2024/self.player.games_2024:.1f} pts/game",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10)
            )
            avg_label.pack()
        
        # Add Compare button if we have other players
        if self.all_players and len(self.all_players) > 1:
            compare_btn = tk.Button(
                totals_frame,
                text='Compare',
                bg=DARK_THEME['button_bg'],
                fg='white',
                font=(DARK_THEME['font_family'], 10, 'bold'),
                bd=0,
                relief='flat',
                padx=15,
                pady=5,
                command=self.compare_players,
                cursor='hand2',
                activebackground=DARK_THEME['button_hover']
            )
            compare_btn.pack(pady=(10, 0))
        
        # Weekly stats container
        stats_container = StyledFrame(main_frame, bg_type='tertiary')
        stats_container.pack(fill='both', expand=True)
        
        # Check if we have weekly stats
        if not hasattr(self.player, 'weekly_stats_2024') or not self.player.weekly_stats_2024 or len(self.player.weekly_stats_2024) == 0:
            # No stats available
            no_stats_label = tk.Label(
                stats_container,
                text="No weekly stats available for 2024",
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 14)
            )
            no_stats_label.pack(expand=True)
            return
        
        # Create non-scrollable frame for weekly stats
        scrollable_frame = tk.Frame(stats_container, bg=DARK_THEME['bg_tertiary'])
        scrollable_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Define column widths (in pixels) - must match data cells exactly
        col_widths = {
            'week': 50,
            'opp': 80,
            'points': 70,
            'snaps': 60,
            'comp': 50,
            'pass_yds': 70,
            'pass_td': 60,
            'int': 40,
            'rush_yds': 70,
            'rush_td': 60,
            'tgt': 40,
            'rec': 40,
            'rec_yds': 70,
            'rec_td': 60,
        }
        
        # Table header
        header_row = tk.Frame(scrollable_frame, bg=DARK_THEME['bg_primary'], height=35)
        header_row.pack(fill='x', padx=10, pady=(10, 5))
        header_row.pack_propagate(False)
        
        # Create header cells with exact widths and sorting
        def create_header_cell(parent, text, width, sort_key=None):
            cell = tk.Frame(parent, bg=DARK_THEME['bg_primary'], width=width, height=35)
            cell.pack(side='left', padx=1)
            cell.pack_propagate(False)
            
            # Container for label and arrow
            content = tk.Frame(cell, bg=DARK_THEME['bg_primary'])
            content.pack(expand=True)
            
            label = tk.Label(
                content,
                text=text,
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10, 'bold')
            )
            label.pack(side='left')
            
            # Sort arrow label (initially hidden)
            arrow_label = tk.Label(
                content,
                text="",
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 8)
            )
            arrow_label.pack(side='left', padx=(2, 0))
            
            # Make clickable if sort_key provided
            if sort_key:
                cell.config(cursor='hand2')
                label.config(cursor='hand2')
                
                def on_click(e):
                    self.sort_data(sort_key, arrow_label)
                
                cell.bind('<Button-1>', on_click)
                label.bind('<Button-1>', on_click)
                
                # Store arrow label for updating
                cell._arrow_label = arrow_label
                cell._sort_key = sort_key
            
            return cell
        
        # Header columns
        self.header_cells = []
        self.header_cells.append(create_header_cell(header_row, 'Week', col_widths['week'], 'week'))
        self.header_cells.append(create_header_cell(header_row, 'Opp', col_widths['opp'], 'opponent'))
        self.header_cells.append(create_header_cell(header_row, 'Points', col_widths['points'], 'points'))
        self.header_cells.append(create_header_cell(header_row, 'Snaps', col_widths['snaps'], 'snaps'))
        
        # Add position-specific headers
        if self.player.position == 'QB':
            self.header_cells.append(create_header_cell(header_row, 'Comp', col_widths['comp'], 'pass_cmp'))
            self.header_cells.append(create_header_cell(header_row, 'Pass Yds', col_widths['pass_yds'], 'pass_yd'))
            self.header_cells.append(create_header_cell(header_row, 'Pass TD', col_widths['pass_td'], 'pass_td'))
            self.header_cells.append(create_header_cell(header_row, 'INT', col_widths['int'], 'pass_int'))
            self.header_cells.append(create_header_cell(header_row, 'Rush Yds', col_widths['rush_yds'], 'rush_yd'))
            self.header_cells.append(create_header_cell(header_row, 'Rush TD', col_widths['rush_td'], 'rush_td'))
        elif self.player.position in ['RB', 'WR', 'TE']:
            self.header_cells.append(create_header_cell(header_row, 'Rush Yds', col_widths['rush_yds'], 'rush_yd'))
            self.header_cells.append(create_header_cell(header_row, 'Rush TD', col_widths['rush_td'], 'rush_td'))
            self.header_cells.append(create_header_cell(header_row, 'Tgt', col_widths['tgt'], 'tgt'))
            self.header_cells.append(create_header_cell(header_row, 'Rec', col_widths['rec'], 'rec'))
            self.header_cells.append(create_header_cell(header_row, 'Rec Yds', col_widths['rec_yds'], 'rec_yd'))
            self.header_cells.append(create_header_cell(header_row, 'Rec TD', col_widths['rec_td'], 'rec_td'))
        elif self.player.position in ['LB', 'DB']:
            # Define defensive column widths
            def_widths = {'tackle_solo': 45, 'tackle_assist': 45, 'sack': 45, 'int': 40, 'ff': 40, 'fr': 40, 'def_td': 50, 'pd': 40}
            col_widths.update(def_widths)
            
            self.header_cells.append(create_header_cell(header_row, 'Solo', def_widths['tackle_solo'], 'tackle_solo'))
            self.header_cells.append(create_header_cell(header_row, 'Ast', def_widths['tackle_assist'], 'tackle_assist'))
            self.header_cells.append(create_header_cell(header_row, 'Sack', def_widths['sack'], 'sack'))
            self.header_cells.append(create_header_cell(header_row, 'INT', def_widths['int'], 'int'))
            self.header_cells.append(create_header_cell(header_row, 'FF', def_widths['ff'], 'ff'))
            self.header_cells.append(create_header_cell(header_row, 'FR', def_widths['fr'], 'fr'))
            self.header_cells.append(create_header_cell(header_row, 'TD', def_widths['def_td'], 'def_td'))
            self.header_cells.append(create_header_cell(header_row, 'PD', def_widths['pd'], 'pass_defended'))
        
        # Create a helper to make data cells
        def create_data_cell(parent, text, width, bg, fg=None):
            cell = tk.Frame(parent, bg=bg, width=width, height=30)
            cell.pack(side='left', padx=1)
            cell.pack_propagate(False)
            label = tk.Label(
                cell,
                text=text,
                bg=bg,
                fg=fg or DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10)
            )
            label.pack(expand=True)
            return cell
        
        # Store references for redrawing
        self.scrollable_frame = scrollable_frame
        self.col_widths = col_widths
        
        # Build and display data
        self.build_weekly_data()
        self.display_weekly_data()
        
        # No canvas or scrollbar needed
        
        # Removed note about snap count since we now have the data
        
        # Close button
        close_btn = tk.Button(
            main_frame,
            text='Close',
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold'),
            bd=0,
            relief='flat',
            padx=20,
            pady=8,
            command=self.close,
            cursor='hand2',
            activebackground=DARK_THEME['button_hover']
        )
        close_btn.pack(pady=(5, 0))
        
    def close(self):
        self.window.grab_release()
        self.window.destroy()
    
    def compare_players(self):
        """Open player selection dialog to choose player to compare"""
        if not self.all_players:
            return
        
        dialog = PlayerSelectionDialog(self.window, self.all_players, self.player)
        selected_player = dialog.get_selected_player()
        
        if selected_player:
            # Close current window first
            self.close()
            
            # Open comparison window directly with the original parent
            PlayerComparisonPopup(self.parent, self.player, selected_player, self.image_service, self.all_players)
    
    def calculate_defensive_points(self, stats):
        """Calculate defensive fantasy points"""
        points = 0.0
        
        # IDP stats use different field names
        solo_tackles = stats.get('idp_tkl_solo', 0)
        total_tackles = stats.get('idp_tkl', 0)
        assist_tackles = max(0, total_tackles - solo_tackles)
        
        points += solo_tackles * SCORING_CONFIG.get('tackle_solo', 1.75)
        points += assist_tackles * SCORING_CONFIG.get('tackle_assist', 1.0)
        points += stats.get('idp_sack', 0) * SCORING_CONFIG.get('sack', 4.0)
        points += stats.get('idp_int', 0) * SCORING_CONFIG.get('int', 6.0)
        points += stats.get('idp_ff', 0) * SCORING_CONFIG.get('ff', 4.0)
        points += stats.get('idp_fr', 0) * SCORING_CONFIG.get('fr', 3.0)
        points += stats.get('idp_def_td', 0) * SCORING_CONFIG.get('def_td', 6.0)
        points += stats.get('idp_safety', 0) * SCORING_CONFIG.get('safety', 2.0)
        points += stats.get('idp_pass_def', 0) * SCORING_CONFIG.get('pass_defended', 1.5)
        
        return round(points, 1)
    
    def build_weekly_data(self):
        """Build the weekly data structure for display and sorting"""
        self.weekly_data = []
        
        # Create a dictionary of weekly stats for easy lookup
        week_stats_dict = {}
        for week_data in self.player.weekly_stats_2024:
            week_stats_dict[week_data['week']] = week_data
        
        # Process all weeks except bye week
        for week_num in range(1, 19):
            # Skip bye week
            if hasattr(self.player, 'bye_week') and self.player.bye_week == week_num:
                continue
            
            week_entry = {'week': week_num}
            
            if week_num in week_stats_dict:
                week_data = week_stats_dict[week_num]
                stats = week_data.get('stats', {})
                
                # Store all relevant data
                week_entry['opponent'] = week_data['opponent']
                week_entry['team'] = week_data.get('team', '')
                
                # Calculate points based on position
                if self.player.position in ['LB', 'DB']:
                    # Calculate defensive points
                    week_entry['points'] = self.calculate_defensive_points(stats)
                else:
                    week_entry['points'] = stats.get('pts_ppr', 0)
                    
                week_entry['snaps'] = stats.get('off_snp', 0)
                
                # Position-specific stats
                if self.player.position == 'QB':
                    week_entry['pass_cmp'] = stats.get('pass_cmp', 0)
                    week_entry['pass_yd'] = stats.get('pass_yd', 0)
                    week_entry['pass_td'] = stats.get('pass_td', 0)
                    week_entry['pass_int'] = stats.get('pass_int', 0)
                    week_entry['rush_yd'] = stats.get('rush_yd', 0)
                    week_entry['rush_td'] = stats.get('rush_td', 0)
                elif self.player.position in ['RB', 'WR', 'TE']:
                    week_entry['rush_yd'] = stats.get('rush_yd', 0)
                    week_entry['rush_td'] = stats.get('rush_td', 0)
                    week_entry['tgt'] = stats.get('rec_tgt', 0)
                    week_entry['rec'] = stats.get('rec', 0)
                    week_entry['rec_yd'] = stats.get('rec_yd', 0)
                    week_entry['rec_td'] = stats.get('rec_td', 0)
                elif self.player.position in ['LB', 'DB']:
                    # Defensive stats - use IDP field names
                    week_entry['snaps'] = stats.get('def_snp', 0)  # Use defensive snaps
                    
                    # Calculate solo and assist tackles
                    solo_tackles = stats.get('idp_tkl_solo', 0)
                    total_tackles = stats.get('idp_tkl', 0)
                    assist_tackles = max(0, total_tackles - solo_tackles)
                    
                    week_entry['tackle_solo'] = solo_tackles
                    week_entry['tackle_assist'] = assist_tackles
                    week_entry['sack'] = stats.get('idp_sack', 0)
                    week_entry['int'] = stats.get('idp_int', 0)
                    week_entry['ff'] = stats.get('idp_ff', 0)
                    week_entry['fr'] = stats.get('idp_fr', 0)
                    week_entry['def_td'] = stats.get('idp_def_td', 0)
                    week_entry['pass_defended'] = stats.get('idp_pass_def', 0)
                
                week_entry['played'] = True
            else:
                # Player didn't play
                week_entry['opponent'] = 'DNP'
                week_entry['team'] = ''
                week_entry['points'] = 0
                week_entry['snaps'] = 0
                week_entry['played'] = False
                
                # Zero out position-specific stats
                if self.player.position == 'QB':
                    week_entry.update({'pass_cmp': 0, 'pass_yd': 0, 'pass_td': 0, 'pass_int': 0, 'rush_yd': 0, 'rush_td': 0})
                elif self.player.position in ['RB', 'WR', 'TE']:
                    week_entry.update({'rush_yd': 0, 'rush_td': 0, 'tgt': 0, 'rec': 0, 'rec_yd': 0, 'rec_td': 0})
            
            self.weekly_data.append(week_entry)
    
    def get_stat_color(self, stat_name, value, position):
        """Determine color for a stat based on good/bad thresholds"""
        # Default colors
        good_color = '#00ff00'  # Bright green
        bad_color = '#ff4444'   # Bright red
        normal_color = DARK_THEME['text_primary']
        
        if position == 'QB':
            if stat_name == 'pass_yd':
                if value >= 300:
                    return good_color
                elif value < 250:
                    return bad_color
            elif stat_name == 'pass_cmp':
                if value >= 30:
                    return good_color
                elif value < 20:
                    return bad_color
            elif stat_name == 'pass_td':
                if value >= 3:
                    return good_color
            elif stat_name == 'rush_yd':
                if value >= 40:
                    return good_color
                elif value < 20:
                    return bad_color
            elif stat_name == 'rush_td':
                if value >= 1:
                    return good_color
            elif stat_name == 'snaps':
                if value < 50:
                    return bad_color
                    
        elif position == 'RB':
            if stat_name == 'rush_yd':
                if value >= 90:
                    return good_color
                elif value < 50:
                    return bad_color
            elif stat_name == 'rush_td':
                if value >= 1:
                    return good_color
            elif stat_name == 'tgt':
                if value >= 6:
                    return good_color
                elif value <= 3:
                    return bad_color
            elif stat_name == 'rec':
                if value >= 4:
                    return good_color
                elif value <= 2:
                    return bad_color
            elif stat_name == 'rec_yd':
                if value >= 40:
                    return good_color
            elif stat_name == 'rec_td':
                if value >= 1:
                    return good_color
            elif stat_name == 'snaps':
                if value > 43:
                    return good_color
                elif value < 30:
                    return bad_color
                    
        elif position == 'WR':
            if stat_name == 'tgt':
                if value >= 8:
                    return good_color
                elif value <= 4:
                    return bad_color
            elif stat_name == 'rec':
                if value >= 6:
                    return good_color
            elif stat_name == 'rec_yd':
                if value >= 90:
                    return good_color
                elif value < 70:
                    return bad_color
            elif stat_name == 'rec_td':
                if value >= 1:
                    return good_color
            elif stat_name == 'snaps':
                if value >= 50:
                    return good_color
                elif value < 40:
                    return bad_color
                    
        elif position == 'TE':
            if stat_name == 'tgt':
                if value >= 6:
                    return good_color
                elif value <= 3:
                    return bad_color
            elif stat_name == 'rec':
                if value >= 5:
                    return good_color
                elif value <= 3:
                    return bad_color
            elif stat_name == 'rec_yd':
                if value >= 50:
                    return good_color
                elif value < 50:
                    return bad_color
            elif stat_name == 'rec_td':
                if value >= 1:
                    return good_color
            elif stat_name == 'snaps':
                if value >= 50:
                    return good_color
                    
        elif position in ['LB', 'DB']:
            # Defensive thresholds
            if stat_name == 'tackle_solo':
                if value >= 6:
                    return good_color
                elif value <= 2:
                    return bad_color
            elif stat_name == 'tackle_assist':
                if value >= 3:
                    return good_color
            elif stat_name == 'sack':
                if value >= 1:
                    return good_color
            elif stat_name == 'int':
                if value >= 1:
                    return good_color
            elif stat_name in ['ff', 'fr', 'def_td']:
                if value >= 1:
                    return good_color
            elif stat_name == 'pass_defended':
                if value >= 2:
                    return good_color
            elif stat_name == 'snaps':
                if value >= 50:
                    return good_color
                elif value < 30:
                    return bad_color
                    
        return normal_color
    
    def create_opponent_cell(self, parent, opponent, is_home, width, bg):
        """Create a cell with opponent team logo and home/away indicator"""
        cell_frame = tk.Frame(parent, bg=bg, width=width, height=30)
        cell_frame.pack(side='left', padx=1)
        cell_frame.pack_propagate(False)
        
        # Create container for @ or vs text and logo
        content_frame = tk.Frame(cell_frame, bg=bg)
        content_frame.pack(expand=True)
        
        # Add @ or vs text
        prefix_label = tk.Label(
            content_frame,
            text="vs" if is_home else "@",
            bg=bg,
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        prefix_label.pack(side='left', padx=(0, 3))
        
        # Try to load team logo
        if opponent and opponent != '-':
            team_code = opponent.lower()
            logo_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'team_logos', f'{team_code}.png')
            
            if os.path.exists(logo_path):
                try:
                    # Load and resize image
                    img = Image.open(logo_path)
                    img = img.resize((20, 20), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    # Create logo label
                    logo_label = tk.Label(content_frame, image=photo, bg=bg)
                    logo_label.image = photo  # Keep reference
                    logo_label.pack(side='left')
                except Exception:
                    # Fallback to text
                    text_label = tk.Label(
                        content_frame,
                        text=opponent,
                        bg=bg,
                        fg=DARK_THEME['text_secondary'],
                        font=(DARK_THEME['font_family'], 10)
                    )
                    text_label.pack(side='left')
            else:
                # No logo found, use text
                text_label = tk.Label(
                    content_frame,
                    text=opponent,
                    bg=bg,
                    fg=DARK_THEME['text_secondary'],
                    font=(DARK_THEME['font_family'], 10)
                )
                text_label.pack(side='left')
        
        # Bind mousewheel if handler exists
        if hasattr(self, '_mousewheel_handler'):
            cell_frame.bind('<MouseWheel>', self._mousewheel_handler)
            content_frame.bind('<MouseWheel>', self._mousewheel_handler)
        
        return cell_frame
    
    def display_weekly_data(self):
        """Display the weekly data in the scrollable frame"""
        # Clear existing rows
        for widget in self.scrollable_frame.winfo_children():
            if widget != self.scrollable_frame.winfo_children()[0]:  # Keep header
                widget.destroy()
        
        # Track totals for summary row
        totals = {
            'points': 0, 'snaps': 0, 'games_played': 0,
            'pass_cmp': 0, 'pass_yd': 0, 'pass_td': 0, 'pass_int': 0,
            'rush_yd': 0, 'rush_td': 0, 'tgt': 0, 'rec': 0, 'rec_yd': 0, 'rec_td': 0,
            'tackle_solo': 0, 'tackle_assist': 0, 'sack': 0, 'int': 0,
            'ff': 0, 'fr': 0, 'def_td': 0, 'pass_defended': 0
        }
        
        # Show all weeks
        weeks_to_show = self.weekly_data
        
        # Create data rows
        for i, week_entry in enumerate(weeks_to_show):
            row_bg = DARK_THEME['bg_secondary'] if i % 2 == 0 else DARK_THEME['bg_tertiary']
            row = tk.Frame(self.scrollable_frame, bg=row_bg, height=30)
            row.pack(fill='x', padx=10, pady=1)
            row.pack_propagate(False)
            
            # Helper to create cells
            def create_cell(text, width, fg=None):
                cell = tk.Frame(row, bg=row_bg, width=width, height=30)
                cell.pack(side='left', padx=1)
                cell.pack_propagate(False)
                label = tk.Label(
                    cell,
                    text=text,
                    bg=row_bg,
                    fg=fg or (DARK_THEME['text_primary'] if week_entry['played'] else DARK_THEME['text_muted']),
                    font=(DARK_THEME['font_family'], 10)
                )
                label.pack(expand=True)
            
            # Week number
            create_cell(f"{week_entry['week']}", self.col_widths['week'])
            
            # Opponent with home/away
            if week_entry['played']:
                is_home = (week_entry['week'] + hash(week_entry['team'])) % 2 == 0
                self.create_opponent_cell(row, week_entry['opponent'], is_home, self.col_widths['opp'], row_bg)
            else:
                create_cell("DNP", self.col_widths['opp'], DARK_THEME['text_muted'])
            
            # Points
            create_cell(f"{week_entry['points']:.1f}", self.col_widths['points'],
                       DARK_THEME['text_primary'] if week_entry['points'] > 0 else DARK_THEME['text_muted'])
            
            # Snaps
            snaps_val = int(week_entry['snaps'])
            snaps_text = f"{snaps_val}" if snaps_val > 0 else '-'
            snaps_color = self.get_stat_color('snaps', snaps_val, self.player.position) if snaps_val > 0 else None
            create_cell(snaps_text, self.col_widths['snaps'], snaps_color)
            
            # Position-specific stats
            if self.player.position == 'QB':
                comp_val = int(week_entry['pass_cmp'])
                create_cell(f"{comp_val}", self.col_widths['comp'], 
                           self.get_stat_color('pass_cmp', comp_val, 'QB') if week_entry['played'] else None)
                
                pass_yd_val = int(week_entry['pass_yd'])
                create_cell(f"{pass_yd_val}", self.col_widths['pass_yds'],
                           self.get_stat_color('pass_yd', pass_yd_val, 'QB') if week_entry['played'] else None)
                
                pass_td_val = int(week_entry['pass_td'])
                create_cell(f"{pass_td_val}", self.col_widths['pass_td'],
                           self.get_stat_color('pass_td', pass_td_val, 'QB') if week_entry['played'] else None)
                
                create_cell(f"{int(week_entry['pass_int'])}", self.col_widths['int'])
                
                rush_yd_val = int(week_entry['rush_yd'])
                create_cell(f"{rush_yd_val}", self.col_widths['rush_yds'],
                           self.get_stat_color('rush_yd', rush_yd_val, 'QB') if week_entry['played'] else None)
                
                rush_td_val = int(week_entry['rush_td'])
                create_cell(f"{rush_td_val}", self.col_widths['rush_td'],
                           self.get_stat_color('rush_td', rush_td_val, 'QB') if week_entry['played'] else None)
            elif self.player.position in ['RB', 'WR', 'TE']:
                rush_yd_val = int(week_entry['rush_yd'])
                create_cell(f"{rush_yd_val}", self.col_widths['rush_yds'],
                           self.get_stat_color('rush_yd', rush_yd_val, self.player.position) if week_entry['played'] and rush_yd_val > 0 else None)
                
                rush_td_val = int(week_entry['rush_td'])
                create_cell(f"{rush_td_val}", self.col_widths['rush_td'],
                           self.get_stat_color('rush_td', rush_td_val, self.player.position) if week_entry['played'] and rush_td_val > 0 else None)
                
                tgt_val = int(week_entry['tgt'])
                create_cell(f"{tgt_val}", self.col_widths['tgt'],
                           self.get_stat_color('tgt', tgt_val, self.player.position) if week_entry['played'] else None)
                
                rec_val = int(week_entry['rec'])
                create_cell(f"{rec_val}", self.col_widths['rec'],
                           self.get_stat_color('rec', rec_val, self.player.position) if week_entry['played'] else None)
                
                rec_yd_val = int(week_entry['rec_yd'])
                create_cell(f"{rec_yd_val}", self.col_widths['rec_yds'],
                           self.get_stat_color('rec_yd', rec_yd_val, self.player.position) if week_entry['played'] else None)
                
                rec_td_val = int(week_entry['rec_td'])
                create_cell(f"{rec_td_val}", self.col_widths['rec_td'],
                           self.get_stat_color('rec_td', rec_td_val, self.player.position) if week_entry['played'] and rec_td_val > 0 else None)
            elif self.player.position in ['LB', 'DB']:
                # Defensive stats
                tackle_solo = int(week_entry.get('tackle_solo', 0))
                create_cell(f"{tackle_solo}", self.col_widths['tackle_solo'],
                           self.get_stat_color('tackle_solo', tackle_solo, self.player.position) if week_entry['played'] else None)
                
                tackle_assist = int(week_entry.get('tackle_assist', 0))
                create_cell(f"{tackle_assist}", self.col_widths['tackle_assist'],
                           self.get_stat_color('tackle_assist', tackle_assist, self.player.position) if week_entry['played'] else None)
                
                sack = float(week_entry.get('sack', 0))
                create_cell(f"{sack:.1f}" if sack > 0 else "0", self.col_widths['sack'],
                           self.get_stat_color('sack', sack, self.player.position) if week_entry['played'] and sack > 0 else None)
                
                int_val = int(week_entry.get('int', 0))
                create_cell(f"{int_val}", self.col_widths['int'],
                           self.get_stat_color('int', int_val, self.player.position) if week_entry['played'] and int_val > 0 else None)
                
                ff = int(week_entry.get('ff', 0))
                create_cell(f"{ff}", self.col_widths['ff'],
                           self.get_stat_color('ff', ff, self.player.position) if week_entry['played'] and ff > 0 else None)
                
                fr = int(week_entry.get('fr', 0))
                create_cell(f"{fr}", self.col_widths['fr'],
                           self.get_stat_color('fr', fr, self.player.position) if week_entry['played'] and fr > 0 else None)
                
                def_td = int(week_entry.get('def_td', 0))
                create_cell(f"{def_td}", self.col_widths['def_td'],
                           self.get_stat_color('def_td', def_td, self.player.position) if week_entry['played'] and def_td > 0 else None)
                
                pd = int(week_entry.get('pass_defended', 0))
                create_cell(f"{pd}", self.col_widths['pd'],
                           self.get_stat_color('pass_defended', pd, self.player.position) if week_entry['played'] and pd > 0 else None)
            
            # Update totals if player played
            if week_entry['played']:
                totals['games_played'] += 1
                totals['points'] += week_entry['points']
                totals['snaps'] += week_entry['snaps']
                
                if self.player.position == 'QB':
                    totals['pass_cmp'] += week_entry['pass_cmp']
                    totals['pass_yd'] += week_entry['pass_yd']
                    totals['pass_td'] += week_entry['pass_td']
                    totals['pass_int'] += week_entry['pass_int']
                    totals['rush_yd'] += week_entry['rush_yd']
                    totals['rush_td'] += week_entry['rush_td']
                elif self.player.position in ['RB', 'WR', 'TE']:
                    totals['rush_yd'] += week_entry['rush_yd']
                    totals['rush_td'] += week_entry['rush_td']
                    totals['tgt'] += week_entry['tgt']
                    totals['rec'] += week_entry['rec']
                    totals['rec_yd'] += week_entry['rec_yd']
                    totals['rec_td'] += week_entry['rec_td']
                elif self.player.position in ['LB', 'DB']:
                    totals['tackle_solo'] += week_entry.get('tackle_solo', 0)
                    totals['tackle_assist'] += week_entry.get('tackle_assist', 0)
                    totals['sack'] += week_entry.get('sack', 0)
                    totals['int'] += week_entry.get('int', 0)
                    totals['ff'] += week_entry.get('ff', 0)
                    totals['fr'] += week_entry.get('fr', 0)
                    totals['def_td'] += week_entry.get('def_td', 0)
                    totals['pass_defended'] += week_entry.get('pass_defended', 0)
        
        # Add separator line
        separator = tk.Frame(self.scrollable_frame, bg=DARK_THEME['border'], height=2)
        separator.pack(fill='x', padx=10, pady=5)
        
        # Add totals row
        totals_row = tk.Frame(self.scrollable_frame, bg=DARK_THEME['bg_primary'], height=35)
        totals_row.pack(fill='x', padx=10, pady=(0, 10))
        totals_row.pack_propagate(False)
        
        # Helper to create total cells
        def create_total_cell(text, width, bold=True):
            cell = tk.Frame(totals_row, bg=DARK_THEME['bg_primary'], width=width, height=35)
            cell.pack(side='left', padx=1)
            cell.pack_propagate(False)
            label = tk.Label(
                cell,
                text=text,
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 11, 'bold' if bold else 'normal')
            )
            label.pack(expand=True)
        
        # Total label
        create_total_cell('TOTAL', self.col_widths['week'])
        create_total_cell('', self.col_widths['opp'])
        
        # Points and snaps
        create_total_cell(f"{totals['points']:.1f}", self.col_widths['points'])
        create_total_cell(f"{totals['snaps']}", self.col_widths['snaps'])
        
        # Position-specific totals
        if self.player.position == 'QB':
            create_total_cell(f"{totals['pass_cmp']}", self.col_widths['comp'])
            create_total_cell(f"{totals['pass_yd']}", self.col_widths['pass_yds'])
            create_total_cell(f"{totals['pass_td']}", self.col_widths['pass_td'])
            create_total_cell(f"{totals['pass_int']}", self.col_widths['int'])
            create_total_cell(f"{totals['rush_yd']}", self.col_widths['rush_yds'])
            create_total_cell(f"{totals['rush_td']}", self.col_widths['rush_td'])
        elif self.player.position in ['RB', 'WR', 'TE']:
            create_total_cell(f"{totals['rush_yd']}", self.col_widths['rush_yds'])
            create_total_cell(f"{totals['rush_td']}", self.col_widths['rush_td'])
            create_total_cell(f"{totals['tgt']}", self.col_widths['tgt'])
            create_total_cell(f"{totals['rec']}", self.col_widths['rec'])
            create_total_cell(f"{totals['rec_yd']}", self.col_widths['rec_yds'])
            create_total_cell(f"{totals['rec_td']}", self.col_widths['rec_td'])
        elif self.player.position in ['LB', 'DB']:
            create_total_cell(f"{totals['tackle_solo']}", self.col_widths['tackle_solo'])
            create_total_cell(f"{totals['tackle_assist']}", self.col_widths['tackle_assist'])
            create_total_cell(f"{totals['sack']:.1f}", self.col_widths['sack'])
            create_total_cell(f"{totals['int']}", self.col_widths['int'])
            create_total_cell(f"{totals['ff']}", self.col_widths['ff'])
            create_total_cell(f"{totals['fr']}", self.col_widths['fr'])
            create_total_cell(f"{totals['def_td']}", self.col_widths['def_td'])
            create_total_cell(f"{totals['pass_defended']}", self.col_widths['pd'])
    
    def sort_data(self, sort_key, arrow_label):
        """Sort the weekly data by the specified column"""
        # Toggle sort direction if clicking same column
        if self.sort_column == sort_key:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = sort_key
            self.sort_ascending = True
        
        # Clear all arrow labels
        for cell in self.header_cells:
            if hasattr(cell, '_arrow_label'):
                cell._arrow_label.config(text='')
        
        # Show arrow on current sort column
        arrow_label.config(text='▲' if self.sort_ascending else '▼')
        
        # Sort the data
        self.weekly_data.sort(
            key=lambda x: x.get(sort_key, 0),
            reverse=not self.sort_ascending
        )
        
        # Redisplay
        self.display_weekly_data()