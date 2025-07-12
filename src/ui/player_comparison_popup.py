import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, List
import os
from PIL import Image, ImageTk
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from ..config.scoring import SCORING_CONFIG


class PlayerComparisonPopup:
    def __init__(self, parent, player1: Player, player2: Player, image_service=None, all_players=None):
        self.player1 = player1
        self.player2 = player2
        self.parent = parent
        self.image_service = image_service
        self.all_players = all_players
        
        # Create popup window
        self.window = tk.Toplevel(parent)
        self.window.title(f"Comparing {player1.format_name()} vs {player2.format_name()}")
        self.window.configure(bg=DARK_THEME['bg_primary'])
        
        # Hide window initially to prevent flashing
        self.window.withdraw()
        
        # Set window size - wider and taller to show all weeks
        self.window.geometry("1400x900")
        
        # Center the window
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        window_width = 1400
        window_height = 900
        
        # Make sure window fits on screen
        if window_width > screen_width - 100:
            window_width = screen_width - 100
        if window_height > screen_height - 100:
            window_height = screen_height - 100
        
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
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
        
        # Title and dropdowns container
        header_container = tk.Frame(main_frame, bg=DARK_THEME['bg_primary'])
        header_container.pack(fill='x', pady=(0, 20))
        
        # Title
        title_label = tk.Label(
            header_container,
            text="Player Comparison",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 18, 'bold')
        )
        title_label.pack()
        
        # Dropdown container
        dropdown_container = tk.Frame(header_container, bg=DARK_THEME['bg_primary'])
        dropdown_container.pack(fill='x', pady=(15, 0))
        
        # Create player lists for dropdowns
        if self.all_players:
            player_names = [p.format_name() for p in self.all_players]
            self.player_dict = {p.format_name(): p for p in self.all_players}
        else:
            player_names = [self.player1.format_name(), self.player2.format_name()]
            self.player_dict = {
                self.player1.format_name(): self.player1,
                self.player2.format_name(): self.player2
            }
        
        # Left player dropdown
        left_dropdown_frame = tk.Frame(dropdown_container, bg=DARK_THEME['bg_primary'])
        left_dropdown_frame.pack(side='left', expand=True, fill='x', padx=(0, 10))
        
        self.player1_var = tk.StringVar(value=self.player1.format_name())
        player1_dropdown = ttk.Combobox(
            left_dropdown_frame,
            textvariable=self.player1_var,
            values=player_names,
            state='readonly',
            width=30
        )
        player1_dropdown.pack()
        player1_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_player_changed(1))
        
        # VS label
        vs_label = tk.Label(
            dropdown_container,
            text="VS",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        vs_label.pack(side='left', padx=20)
        
        # Right player dropdown
        right_dropdown_frame = tk.Frame(dropdown_container, bg=DARK_THEME['bg_primary'])
        right_dropdown_frame.pack(side='left', expand=True, fill='x', padx=(10, 0))
        
        self.player2_var = tk.StringVar(value=self.player2.format_name())
        player2_dropdown = ttk.Combobox(
            right_dropdown_frame,
            textvariable=self.player2_var,
            values=player_names,
            state='readonly',
            width=30
        )
        player2_dropdown.pack()
        player2_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_player_changed(2))
        
        # Container for both player cards
        cards_container = tk.Frame(main_frame, bg=DARK_THEME['bg_primary'])
        cards_container.pack(fill='both', expand=True)
        
        # Create frames for each player card
        self.left_card_container = tk.Frame(cards_container, bg=DARK_THEME['bg_primary'])
        self.left_card_container.pack(side='left', fill='both', expand=True)
        
        # Separator
        separator = tk.Frame(cards_container, bg=DARK_THEME['border'], width=2)
        separator.pack(side='left', fill='y', padx=10)
        
        self.right_card_container = tk.Frame(cards_container, bg=DARK_THEME['bg_primary'])
        self.right_card_container.pack(side='left', fill='both', expand=True)
        
        # Store weekly data for comparison
        self.player1_weekly_data = {}
        self.player2_weekly_data = {}
        
        # Create player cards - create both initially to populate data
        self.create_player_card(self.left_card_container, self.player1, 1)
        self.create_player_card(self.right_card_container, self.player2, 2)
        
        # Recreate first player's card now that we have second player's data for comparison
        self.create_player_card(self.left_card_container, self.player1, 1)
        
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
        close_btn.pack(pady=(20, 0))
        
    def create_player_card(self, parent, player: Player, player_num: int):
        """Create a player stats card"""
        # Clear existing content
        for widget in parent.winfo_children():
            widget.destroy()
        
        card_frame = StyledFrame(parent, bg_type='secondary')
        card_frame.pack(fill='both', expand=True)
        
        # Header with player info
        header_frame = StyledFrame(card_frame, bg_type='tertiary')
        header_frame.pack(fill='x', padx=10, pady=10)
        
        # Player info container
        info_container = tk.Frame(header_frame, bg=DARK_THEME['bg_tertiary'])
        info_container.pack(fill='x', padx=10, pady=(0, 10))
        
        # Left side: Player image
        image_frame = tk.Frame(info_container, bg=DARK_THEME['bg_tertiary'])
        image_frame.pack(side='left', padx=(0, 15))
        
        # Player image
        image_label = tk.Label(
            image_frame,
            bg=DARK_THEME['bg_primary'],
            width=80,
            height=64,
            text="",
            relief='flat'
        )
        image_label.pack()
        
        # Load player image
        if self.image_service and player.player_id:
            player_image = self.image_service.get_image(player.player_id, size=(80, 64))
            if player_image:
                image_label.configure(image=player_image)
                image_label.image = player_image
            else:
                # Try to load async
                def update_image(photo):
                    if image_label.winfo_exists():
                        image_label.configure(image=photo)
                        image_label.image = photo
                
                self.image_service.load_image_async(
                    player.player_id,
                    size=(80, 64),
                    callback=update_image,
                    widget=self.window
                )
        
        # Right side: Player info
        info_frame = tk.Frame(info_container, bg=DARK_THEME['bg_tertiary'])
        info_frame.pack(side='left', fill='both', expand=True)
        
        # Player name and position
        name_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_tertiary'])
        name_frame.pack(anchor='w')
        
        name_label = tk.Label(
            name_frame,
            text=player.format_name(),
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 16, 'bold')
        )
        name_label.pack(side='left', padx=(0, 10))
        
        # Position badge
        pos_bg = get_position_color(player.position)
        pos_label = tk.Label(
            name_frame,
            text=player.position,
            bg=pos_bg,
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=8,
            pady=2
        )
        pos_label.pack(side='left')
        
        # Team with logo
        if player.team:
            team_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_tertiary'])
            team_frame.pack(anchor='w', pady=(5, 0))
            
            # Team logo
            logo_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'team_logos', f'{player.team.lower()}.png')
            if os.path.exists(logo_path):
                try:
                    img = Image.open(logo_path)
                    img = img.resize((24, 24), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    logo_label = tk.Label(team_frame, image=photo, bg=DARK_THEME['bg_tertiary'])
                    logo_label.image = photo
                    logo_label.pack(side='left', padx=(0, 5))
                except Exception:
                    pass
            
            team_label = tk.Label(
                team_frame,
                text=player.team,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 12)
            )
            team_label.pack(side='left')
        
        # Season totals and projections
        stats_text_lines = []
        if player.points_2024:
            stats_text_lines.append(f"2024: {player.points_2024:.1f} pts | {player.games_2024} games | {player.points_2024/player.games_2024:.1f} ppg")
        
        # Add 2025 projection if available
        if hasattr(player, 'points_2025_proj') and player.points_2025_proj:
            stats_text_lines.append(f"2025 Projection: {player.points_2025_proj:.1f} pts")
        
        for text in stats_text_lines:
            stats_label = tk.Label(
                info_frame,
                text=text,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10)
            )
            stats_label.pack(anchor='w', pady=(2, 0))
        
        # Stats table with scrollbar for all games
        self.create_stats_table(card_frame, player, player_num)
        
    def create_stats_table(self, parent, player: Player, player_num: int):
        """Create the weekly stats table with comparison coloring"""
        stats_frame = tk.Frame(parent, bg=DARK_THEME['bg_secondary'])
        stats_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Check if we have weekly stats
        if not hasattr(player, 'weekly_stats_2024') or not player.weekly_stats_2024:
            no_stats_label = tk.Label(
                stats_frame,
                text="No weekly stats available",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 12)
            )
            no_stats_label.pack(expand=True)
            return
        
        # Define column widths
        col_widths = {
            'week': 35,
            'opp': 50,
            'points': 50,
            'snaps': 45,
            'pass_yds': 55,
            'pass_td': 40,
            'rush_yds': 55,
            'rush_td': 40,
            'tgt': 30,
            'rec': 30,
            'rec_yds': 55,
            'rec_td': 40,
        }
        
        # Header row
        header_row = tk.Frame(stats_frame, bg=DARK_THEME['bg_primary'], height=25)
        header_row.pack(fill='x', pady=(0, 2))
        header_row.pack_propagate(False)
        
        # Create header cells
        def create_header_cell(text, width):
            cell = tk.Frame(header_row, bg=DARK_THEME['bg_primary'], width=width, height=25)
            cell.pack(side='left', padx=1)
            cell.pack_propagate(False)
            label = tk.Label(
                cell,
                text=text,
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 9, 'bold')
            )
            label.pack(expand=True)
        
        # Common headers
        create_header_cell('Wk', col_widths['week'])
        create_header_cell('Opp', col_widths['opp'])
        create_header_cell('Pts', col_widths['points'])
        create_header_cell('Snp', col_widths['snaps'])
        
        # Position-specific headers
        if player.position == 'QB':
            create_header_cell('PYds', col_widths['pass_yds'])
            create_header_cell('PTD', col_widths['pass_td'])
            create_header_cell('RYds', col_widths['rush_yds'])
            create_header_cell('RTD', col_widths['rush_td'])
        elif player.position in ['RB', 'WR', 'TE']:
            create_header_cell('RYds', col_widths['rush_yds'])
            create_header_cell('RTD', col_widths['rush_td'])
            create_header_cell('Tgt', col_widths['tgt'])
            create_header_cell('Rec', col_widths['rec'])
            create_header_cell('YDs', col_widths['rec_yds'])
            create_header_cell('TD', col_widths['rec_td'])
        
        # Create container for data rows (no scrolling needed with taller window)
        data_container = tk.Frame(stats_frame, bg=DARK_THEME['bg_secondary'])
        data_container.pack(fill='both', expand=True)
        
        # Process weekly data
        weekly_totals = {
            'points': 0, 'snaps': 0, 'games': 0,
            'pass_yds': 0, 'pass_td': 0, 'rush_yds': 0, 'rush_td': 0,
            'tgt': 0, 'rec': 0, 'rec_yds': 0, 'rec_td': 0
        }
        
        # Create a dictionary of weekly stats for easy lookup
        week_stats_dict = {}
        if hasattr(player, 'weekly_stats_2024') and player.weekly_stats_2024:
            for week_data in player.weekly_stats_2024:
                week_stats_dict[week_data['week']] = week_data
        
        # Display all weeks 1-18 (regular season)
        for week_num in range(1, 19):
            week_count = week_num
            
            # Check if this is bye week
            is_bye_week = hasattr(player, 'bye_week') and player.bye_week == week_num
            
            # Get week data if available
            week_data = week_stats_dict.get(week_num, None)
            if week_data:
                stats = week_data.get('stats', {})
                opponent = week_data.get('opponent', 'DNP')
                # Check if player actually played
                played = stats.get('off_snp', 0) > 0 or stats.get('def_snp', 0) > 0
            else:
                stats = {}
                opponent = 'BYE' if is_bye_week else 'DNP'
                played = False
            
            # Calculate points and snaps
            points = stats.get('pts_ppr', 0) if played else 0
            snaps = (stats.get('off_snp', 0) or stats.get('def_snp', 0)) if played else 0
            
            row_bg = DARK_THEME['bg_tertiary'] if week_count % 2 == 0 else DARK_THEME['bg_secondary']
            row = tk.Frame(data_container, bg=row_bg, height=22)
            row.pack(fill='x', pady=0.5)
            row.pack_propagate(False)
            
            # Store week data for comparison
            week_key = f"week_{week_num}"
            if player_num == 1:
                self.player1_weekly_data[week_key] = {
                    'points': points,
                    'snaps': snaps,
                    'stats': stats
                }
            else:
                self.player2_weekly_data[week_key] = {
                    'points': points,
                    'snaps': snaps,
                    'stats': stats
                }
            
            # Get comparison data
            other_player_data = self.player2_weekly_data if player_num == 1 else self.player1_weekly_data
            compare_data = other_player_data.get(week_key, {})
            
            # Helper to create cells with comparison coloring
            def create_cell(text, width, value=None, stat_name=None):
                cell = tk.Frame(row, bg=row_bg, width=width, height=22)
                cell.pack(side='left', padx=1)
                cell.pack_propagate(False)
                
                # Determine color based on comparison
                fg = DARK_THEME['text_primary']
                if value is not None and stat_name and compare_data:
                    # Get other player's value
                    if stat_name == 'points':
                        other_value = compare_data.get('points', 0)
                    elif stat_name == 'snaps':
                        other_value = compare_data.get('snaps', 0)
                    else:
                        other_value = compare_data.get('stats', {}).get(stat_name, 0)
                    
                    # Color based on comparison (only if both players played that week)
                    # Check if both players have data for this week
                    both_played = value > 0 or other_value > 0
                    if stat_name in ['points', 'snaps'] and both_played:
                        # For points and snaps, only color if both have non-zero values
                        if value > 0 and other_value > 0:
                            if value > other_value:
                                fg = '#00ff00'  # Green
                            elif value < other_value:
                                fg = '#ff4444'  # Red
                    elif stat_name not in ['points', 'snaps'] and both_played:
                        # For other stats, color even if one is zero (e.g., 0 TDs vs 1 TD)
                        if value > other_value:
                            fg = '#00ff00'  # Green
                        elif value < other_value:
                            fg = '#ff4444'  # Red
                
                label = tk.Label(
                    cell,
                    text=text,
                    bg=row_bg,
                    fg=fg,
                    font=(DARK_THEME['font_family'], 9)
                )
                label.pack(expand=True)
            
            # Week
            create_cell(f"{week_num}", col_widths['week'])
            
            # Opponent with logo
            opp_cell = tk.Frame(row, bg=row_bg, width=col_widths['opp'], height=22)
            opp_cell.pack(side='left', padx=1)
            opp_cell.pack_propagate(False)
            
            if opponent not in ['BYE', 'DNP'] and opponent:
                # Try to load team logo
                logo_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'team_logos', f'{opponent.lower()}.png')
                if os.path.exists(logo_path):
                    try:
                        img = Image.open(logo_path)
                        img = img.resize((18, 18), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        
                        logo_label = tk.Label(opp_cell, image=photo, bg=row_bg)
                        logo_label.image = photo  # Keep reference
                        logo_label.pack(expand=True)
                    except Exception:
                        # Fallback to text
                        opp_label = tk.Label(opp_cell, text=opponent, bg=row_bg, fg=DARK_THEME['text_primary'], font=(DARK_THEME['font_family'], 9))
                        opp_label.pack(expand=True)
                else:
                    # No logo found
                    opp_label = tk.Label(opp_cell, text=opponent, bg=row_bg, fg=DARK_THEME['text_primary'], font=(DARK_THEME['font_family'], 9))
                    opp_label.pack(expand=True)
            else:
                # BYE or DNP
                opp_label = tk.Label(opp_cell, text=opponent, bg=row_bg, fg=DARK_THEME['text_muted'], font=(DARK_THEME['font_family'], 9))
                opp_label.pack(expand=True)
            create_cell(f"{points:.1f}", col_widths['points'], points, 'points')
            create_cell(f"{int(snaps)}", col_widths['snaps'], snaps, 'snaps')
            
            # Update totals only if player played
            if played:
                weekly_totals['points'] += points
                weekly_totals['snaps'] += int(snaps)
                weekly_totals['games'] += 1
            
            # Position-specific stats
            if player.position == 'QB':
                pass_yds = stats.get('pass_yd', 0) if played else 0
                pass_td = stats.get('pass_td', 0) if played else 0
                rush_yds = stats.get('rush_yd', 0) if played else 0
                rush_td = stats.get('rush_td', 0) if played else 0
                
                create_cell(f"{int(pass_yds)}", col_widths['pass_yds'], pass_yds, 'pass_yd')
                create_cell(f"{int(pass_td)}", col_widths['pass_td'], pass_td, 'pass_td')
                create_cell(f"{int(rush_yds)}", col_widths['rush_yds'], rush_yds, 'rush_yd')
                create_cell(f"{int(rush_td)}", col_widths['rush_td'], rush_td, 'rush_td')
                
                if played:
                    weekly_totals['pass_yds'] += int(pass_yds)
                    weekly_totals['pass_td'] += int(pass_td)
                    weekly_totals['rush_yds'] += int(rush_yds)
                    weekly_totals['rush_td'] += int(rush_td)
                
            elif player.position in ['RB', 'WR', 'TE']:
                rush_yds = stats.get('rush_yd', 0) if played else 0
                rush_td = stats.get('rush_td', 0) if played else 0
                tgt = stats.get('rec_tgt', 0) if played else 0
                rec = stats.get('rec', 0) if played else 0
                rec_yds = stats.get('rec_yd', 0) if played else 0
                rec_td = stats.get('rec_td', 0) if played else 0
                
                create_cell(f"{int(rush_yds)}", col_widths['rush_yds'], rush_yds, 'rush_yd')
                create_cell(f"{int(rush_td)}", col_widths['rush_td'], rush_td, 'rush_td')
                create_cell(f"{int(tgt)}", col_widths['tgt'], tgt, 'rec_tgt')
                create_cell(f"{int(rec)}", col_widths['rec'], rec, 'rec')
                create_cell(f"{int(rec_yds)}", col_widths['rec_yds'], rec_yds, 'rec_yd')
                create_cell(f"{int(rec_td)}", col_widths['rec_td'], rec_td, 'rec_td')
                
                if played:
                    weekly_totals['rush_yds'] += int(rush_yds)
                    weekly_totals['rush_td'] += int(rush_td)
                    weekly_totals['tgt'] += int(tgt)
                    weekly_totals['rec'] += int(rec)
                    weekly_totals['rec_yds'] += int(rec_yds)
                    weekly_totals['rec_td'] += int(rec_td)
        
        # Add totals row at bottom of scrollable area
        separator = tk.Frame(data_container, bg=DARK_THEME['border'], height=2)
        separator.pack(fill='x', pady=(5, 0))
        
        totals_row = tk.Frame(data_container, bg=DARK_THEME['bg_primary'], height=25)
        totals_row.pack(fill='x', pady=(5, 5))
        totals_row.pack_propagate(False)
        
        def create_total_cell(text, width, bold=True):
            cell = tk.Frame(totals_row, bg=DARK_THEME['bg_primary'], width=width, height=25)
            cell.pack(side='left', padx=1)
            cell.pack_propagate(False)
            label = tk.Label(
                cell,
                text=text,
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 9, 'bold' if bold else 'normal')
            )
            label.pack(expand=True)
        
        # Totals
        create_total_cell('Total', col_widths['week'])
        create_total_cell('', col_widths['opp'])
        create_total_cell(f"{weekly_totals['points']:.1f}", col_widths['points'])
        create_total_cell(f"{int(weekly_totals['snaps'])}", col_widths['snaps'])
        
        if player.position == 'QB':
            create_total_cell(f"{int(weekly_totals['pass_yds'])}", col_widths['pass_yds'])
            create_total_cell(f"{int(weekly_totals['pass_td'])}", col_widths['pass_td'])
            create_total_cell(f"{int(weekly_totals['rush_yds'])}", col_widths['rush_yds'])
            create_total_cell(f"{int(weekly_totals['rush_td'])}", col_widths['rush_td'])
        elif player.position in ['RB', 'WR', 'TE']:
            create_total_cell(f"{int(weekly_totals['rush_yds'])}", col_widths['rush_yds'])
            create_total_cell(f"{int(weekly_totals['rush_td'])}", col_widths['rush_td'])
            create_total_cell(f"{int(weekly_totals['tgt'])}", col_widths['tgt'])
            create_total_cell(f"{int(weekly_totals['rec'])}", col_widths['rec'])
            create_total_cell(f"{int(weekly_totals['rec_yds'])}", col_widths['rec_yds'])
            create_total_cell(f"{int(weekly_totals['rec_td'])}", col_widths['rec_td'])
    
    def close(self):
        self.window.grab_release()
        self.window.destroy()
    
    def on_player_changed(self, player_num: int):
        """Handle dropdown selection change"""
        # Get selected player name
        selected_name = self.player1_var.get() if player_num == 1 else self.player2_var.get()
        
        # Get player object
        selected_player = self.player_dict.get(selected_name)
        if not selected_player:
            return
        
        # Update the player and recreate both cards (to update comparison colors)
        if player_num == 1:
            self.player1 = selected_player
        else:
            self.player2 = selected_player
        
        # Clear weekly data for fresh comparison
        self.player1_weekly_data = {}
        self.player2_weekly_data = {}
        
        # Recreate both cards to update comparison colors
        self.create_player_card(self.left_card_container, self.player1, 1)
        self.create_player_card(self.right_card_container, self.player2, 2)
        
        # Update window title
        self.window.title(f"Comparing {self.player1.format_name()} vs {self.player2.format_name()}")