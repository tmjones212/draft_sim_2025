import tkinter as tk
from tkinter import ttk
import json
import os
from typing import Dict, List, Optional
from PIL import Image, ImageTk
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from ..utils.player_extensions import format_name
from ..config.scoring import SCORING_CONFIG

# Teams with dome stadiums
DOME_TEAMS = {'ATL', 'DET', 'MIN', 'NO', 'LV', 'ARI', 'AZ', 'DAL', 'HOU', 'IND'}


class GameHistory(StyledFrame):
    def __init__(self, parent, all_players, **kwargs):
        super().__init__(parent, bg_type='primary', **kwargs)
        self.all_players = all_players
        self.player_lookup = {p.player_id: p for p in all_players if hasattr(p, 'player_id')}
        self.weekly_stats = {}
        self.filtered_players = []
        
        # UI state
        self.selected_position = "ALL"
        self.selected_week = "ALL"
        self.sort_column = None
        self.sort_ascending = True
        self.search_var = tk.StringVar()
        self.view_mode = "detailed"  # "detailed" or "summarized"
        
        # Filter history for back button
        self.filter_history = []
        self.current_filter_state = None
        
        self.setup_ui()
        self.update_column_visibility()  # Set initial column visibility
        self.load_weekly_stats()
        
    def setup_ui(self):
        # Main container
        container = StyledFrame(self, bg_type='secondary')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        header_frame = StyledFrame(container, bg_type='secondary')
        header_frame.pack(fill='x', pady=(0, 10))
        
        title = tk.Label(
            header_frame,
            text="2024 SEASON GAME HISTORY",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        title.pack(side='left')
        
        # Filters row
        filter_frame = StyledFrame(container, bg_type='secondary')
        filter_frame.pack(fill='x', pady=(0, 10))
        
        # Search box with real-time filtering
        search_label = tk.Label(
            filter_frame,
            text="Search:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        search_label.pack(side='left', padx=(0, 5))
        
        self.search_entry = tk.Entry(
            filter_frame,
            textvariable=self.search_var,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            width=20
        )
        self.search_entry.pack(side='left', padx=(0, 20))
        self.search_var.trace('w', lambda *args: self.on_search_changed())
        
        # Position filter
        pos_label = tk.Label(
            filter_frame,
            text="Position:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        pos_label.pack(side='left', padx=(0, 5))
        
        positions = ["ALL", "QB", "RB", "WR", "TE", "FLEX"]
        self.position_buttons = {}
        
        # Create position buttons container (single row)
        pos_container = tk.Frame(filter_frame, bg=DARK_THEME['bg_secondary'])
        pos_container.pack(side='left', padx=(0, 20))
        
        # Main positions only
        for pos in positions:
            if pos == "ALL":
                btn_bg = DARK_THEME['button_active'] if pos == self.selected_position else DARK_THEME['button_bg']
            elif pos == "FLEX":
                btn_bg = DARK_THEME['button_active'] if pos == self.selected_position else DARK_THEME['button_bg']
            else:
                btn_bg = get_position_color(pos) if pos == self.selected_position else DARK_THEME['button_bg']
            
            btn = tk.Button(
                pos_container,
                text=pos,
                bg=btn_bg,
                fg='white',
                font=(DARK_THEME['font_family'], 9, 'bold'),
                bd=0,
                relief='flat',
                padx=10,
                pady=3,
                command=lambda p=pos: self.filter_by_position(p),
                cursor='hand2'
            )
            btn.pack(side='left', padx=1)
            self.position_buttons[pos] = btn
        
        # Week filter
        week_label = tk.Label(
            filter_frame,
            text="Week:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        week_label.pack(side='left', padx=(20, 5))
        
        self.week_var = tk.StringVar(value="ALL")
        self.week_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.week_var,
            values=["ALL"] + [str(i) for i in range(1, 19)],
            width=8,
            state='readonly',
            font=(DARK_THEME['font_family'], 10)
        )
        self.week_dropdown.pack(side='left')
        self.week_dropdown.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Home/Away filter
        home_away_label = tk.Label(
            filter_frame,
            text="Location:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        home_away_label.pack(side='left', padx=(20, 5))
        
        self.location_var = tk.StringVar(value="ALL")
        self.location_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.location_var,
            values=["ALL", "HOME", "AWAY"],
            width=8,
            state='readonly',
            font=(DARK_THEME['font_family'], 10)
        )
        self.location_dropdown.pack(side='left')
        self.location_dropdown.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Dome/Outside filter
        dome_label = tk.Label(
            filter_frame,
            text="Venue:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        dome_label.pack(side='left', padx=(20, 5))
        
        self.venue_var = tk.StringVar(value="ALL")
        self.venue_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=self.venue_var,
            values=["ALL", "DOME", "OUTSIDE"],
            width=10,
            state='readonly',
            font=(DARK_THEME['font_family'], 10)
        )
        self.venue_dropdown.pack(side='left')
        self.venue_dropdown.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Clear filter button
        self.clear_button = tk.Button(
            filter_frame,
            text="CLEAR",
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold'),
            bd=0,
            relief='flat',
            padx=12,
            pady=4,
            command=self.clear_filters,
            cursor='hand2'
        )
        self.clear_button.pack(side='left', padx=(20, 5))
        
        # Back button
        self.back_button = tk.Button(
            filter_frame,
            text="← BACK",
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold'),
            bd=0,
            relief='flat',
            padx=12,
            pady=4,
            command=self.go_back,
            cursor='hand2',
            state='disabled'
        )
        self.back_button.pack(side='left', padx=5)
        
        # View mode toggle buttons
        view_separator = tk.Frame(filter_frame, width=20, bg=DARK_THEME['bg_secondary'])
        view_separator.pack(side='left')
        
        view_label = tk.Label(
            filter_frame,
            text="View:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        view_label.pack(side='left', padx=(0, 5))
        
        self.detailed_btn = tk.Button(
            filter_frame,
            text="DETAILED",
            bg=DARK_THEME['button_active'],
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold'),
            bd=0,
            relief='flat',
            padx=10,
            pady=4,
            command=lambda: self.set_view_mode("detailed"),
            cursor='hand2'
        )
        self.detailed_btn.pack(side='left', padx=1)
        
        self.summarized_btn = tk.Button(
            filter_frame,
            text="SUMMARIZED",
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold'),
            bd=0,
            relief='flat',
            padx=10,
            pady=4,
            command=lambda: self.set_view_mode("summarized"),
            cursor='hand2'
        )
        self.summarized_btn.pack(side='left', padx=1)
        
        # Table container
        table_container = StyledFrame(container, bg_type='secondary')
        table_container.pack(fill='both', expand=True)
        
        # Create treeview for table
        columns = ('player', 'pos', 'team', 'week', 'opp', 'pts', 'snaps', 'comp', 'pass_yd', 'pass_td', 
                  'rush_yd', 'rush_td', 'rec', 'rec_yd', 'rec_td')
        
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show='tree headings',
            height=20
        )
        
        # Configure columns
        self.tree.column('#0', width=0, stretch=False)  # Hide tree column
        self.tree.column('player', width=140, anchor='w')
        self.tree.column('pos', width=35, anchor='center')
        self.tree.column('team', width=35, anchor='center')
        self.tree.column('week', width=35, anchor='center')
        self.tree.column('opp', width=50, anchor='center')
        self.tree.column('pts', width=50, anchor='center')
        self.tree.column('snaps', width=45, anchor='center')
        self.tree.column('comp', width=45, anchor='center')
        self.tree.column('pass_yd', width=60, anchor='center')
        self.tree.column('pass_td', width=50, anchor='center')
        self.tree.column('rush_yd', width=60, anchor='center')
        self.tree.column('rush_td', width=50, anchor='center')
        self.tree.column('rec', width=35, anchor='center')
        self.tree.column('rec_yd', width=55, anchor='center')
        self.tree.column('rec_td', width=45, anchor='center')
        
        # Configure headings
        self.tree.heading('player', text='Player', command=lambda: self.sort_by('player'))
        self.tree.heading('pos', text='Pos', command=lambda: self.sort_by('pos'))
        self.tree.heading('team', text='Team', command=lambda: self.sort_by('team'))
        self.tree.heading('week', text='Wk', command=lambda: self.sort_by('week'))
        self.tree.heading('opp', text='Opp', command=lambda: self.sort_by('opp'))
        self.tree.heading('pts', text='Pts', command=lambda: self.sort_by('pts'))
        self.tree.heading('snaps', text='Snaps', command=lambda: self.sort_by('snaps'))
        self.tree.heading('comp', text='Comp', command=lambda: self.sort_by('comp'))
        self.tree.heading('pass_yd', text='Pass Yds', command=lambda: self.sort_by('pass_yd'))
        self.tree.heading('pass_td', text='Pass TD', command=lambda: self.sort_by('pass_td'))
        self.tree.heading('rush_yd', text='Rush Yds', command=lambda: self.sort_by('rush_yd'))
        self.tree.heading('rush_td', text='Rush TD', command=lambda: self.sort_by('rush_td'))
        self.tree.heading('rec', text='Rec', command=lambda: self.sort_by('rec'))
        self.tree.heading('rec_yd', text='Rec Yds', command=lambda: self.sort_by('rec_yd'))
        self.tree.heading('rec_td', text='Rec TD', command=lambda: self.sort_by('rec_td'))
        
        # Style configuration
        style = ttk.Style()
        style.configure('Treeview', 
                       background=DARK_THEME['bg_secondary'],
                       foreground=DARK_THEME['text_primary'],
                       fieldbackground=DARK_THEME['bg_secondary'],
                       borderwidth=0,
                       font=(DARK_THEME['font_family'], 10))
        style.configure('Treeview.Heading',
                       background=DARK_THEME['bg_tertiary'],
                       foreground=DARK_THEME['text_primary'],
                       font=(DARK_THEME['font_family'], 10, 'bold'))
        style.map('Treeview',
                 background=[('selected', DARK_THEME['button_active'])],
                 foreground=[('selected', 'white')])
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(table_container, orient='vertical', command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_container, orient='horizontal', command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Pack everything
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Bind right-click
        self.tree.bind('<Button-3>', self.on_right_click)
        
        # Status label
        self.status_label = tk.Label(
            container,
            text="Loading game history...",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        )
        self.status_label.pack(pady=5)
        
    def load_weekly_stats(self):
        """Load all weekly stats data"""
        stats_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'stats_data')
        stats_dir = os.path.abspath(stats_dir)
        
        if not os.path.exists(stats_dir):
            self.status_label.config(text="Stats data not found")
            return
            
        # Load all weeks and positions
        for week in range(1, 19):
            self.weekly_stats[week] = {}
            
            for position in ['qb', 'rb', 'wr', 'te']:
                filename = f"2024_{week}_{position}.json"
                filepath = os.path.join(stats_dir, filename)
                
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            for player_stat in data:
                                player_id = player_stat.get('player_id')
                                if player_id and player_id in self.player_lookup:
                                    if player_id not in self.weekly_stats[week]:
                                        self.weekly_stats[week][player_id] = []
                                    self.weekly_stats[week][player_id].append(player_stat)
                    except Exception as e:
                        print(f"Error loading {filename}: {e}")
        
        self.apply_filters()
        self.status_label.config(text=f"Loaded {len(self.weekly_stats)} weeks of game data")
    
    def calculate_custom_points(self, stats, position):
        """Calculate custom fantasy points based on our scoring rules"""
        points = 0.0
        
        # Passing points
        if position == 'QB':
            points += stats.get('pass_cmp', 0) * SCORING_CONFIG['pass_completion']
            points += stats.get('pass_yd', 0) * SCORING_CONFIG['pass_yard']
            points += stats.get('pass_td', 0) * SCORING_CONFIG['touchdown']
            
            # Pass bonus
            if stats.get('pass_yd', 0) >= 300:
                points += SCORING_CONFIG['bonus_pass_300_yards']
        
        # Rushing points (all positions)
        points += stats.get('rush_yd', 0) * SCORING_CONFIG['rush_yard']
        points += stats.get('rush_td', 0) * SCORING_CONFIG['touchdown']
        
        # Rush bonus
        if stats.get('rush_yd', 0) >= 100:
            points += SCORING_CONFIG['bonus_rush_100_yards']
        
        # Receiving points (non-QBs)
        if position != 'QB':
            points += stats.get('rec', 0) * SCORING_CONFIG['reception']
            points += stats.get('rec_yd', 0) * SCORING_CONFIG['rec_yard']
            points += stats.get('rec_td', 0) * SCORING_CONFIG['touchdown']
            
            # Rec bonus
            if stats.get('rec_yd', 0) >= 100:
                points += SCORING_CONFIG['bonus_rec_100_yards']
        
        return points
        
    def apply_filters(self):
        """Apply all filters and update display"""
        # Save current filter state
        self.save_filter_state()
        
        search_text = self.search_var.get().lower()
        selected_week = self.week_var.get()
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Build filtered data
        if self.view_mode == "summarized":
            rows = self.build_summarized_data(search_text, selected_week)
        else:
            rows = self.build_detailed_data(search_text, selected_week)
        
        # Sort if needed
        if self.sort_column:
            self.sort_rows(rows)
        
        # Add to tree
        for row in rows:
            values = (row['player'], row['pos'], row['team'], row['week'], row['opp'],
                     row['pts'], row['snaps'], row['comp'], row['pass_yd'], row['pass_td'], row['rush_yd'], 
                     row['rush_td'], row['rec'], row['rec_yd'], row['rec_td'])
            
            # Add row with alternating colors
            tags = ()
            if len(self.tree.get_children()) % 2 == 0:
                tags = ('even',)
            else:
                tags = ('odd',)
                
            self.tree.insert('', 'end', values=values, tags=tags)
        
        # Configure tag colors
        self.tree.tag_configure('even', background=DARK_THEME['bg_tertiary'])
        self.tree.tag_configure('odd', background=DARK_THEME['bg_secondary'])
        
        # Update status
        self.status_label.config(text=f"Showing {len(rows)} {'seasons' if self.view_mode == 'summarized' else 'games'}")
    
    def build_detailed_data(self, search_text, selected_week):
        """Build data for detailed view (individual games)"""
        rows = []
        
        # Normal filtering
        if False:  # Removed roster position filtering
            for week, week_data in self.weekly_stats.items():
                # Skip if week filter is active
                if selected_week != "ALL" and str(week) != selected_week:
                    continue
                
                # Get all players of the selected position for this week
                week_position_scores = []
                for player_id, stats_list in week_data.items():
                    if player_id not in self.player_lookup:
                        continue
                    player = self.player_lookup[player_id]
                    if player.position == self.selected_position:
                        for stat in stats_list:
                            pts = stat.get('stats', {}).get('pts_ppr', 0)
                            week_position_scores.append((player_id, pts))
                
                # Sort by points to get ranks
                week_position_scores.sort(key=lambda x: x[1], reverse=True)
                position_ranks = {pid: rank+1 for rank, (pid, _) in enumerate(week_position_scores)}
                
                # Extract rank number from filter (e.g., "RB1" -> 1)
                target_rank = int(self.roster_position_filter[-1])
                
                # Process players for this week
                for player_id, stats_list in week_data.items():
                    if player_id not in self.player_lookup:
                        continue
                    
                    player = self.player_lookup[player_id]
                    
                    # Check if this player has the target rank
                    if position_ranks.get(player_id, 999) != target_rank:
                        continue
                    
                    # Search filter
                    if search_text and search_text not in player.name.lower():
                        continue
                    
                    # Process the game
                    for stat in stats_list:
                        stats = stat.get('stats', {})
                        opponent = stat.get('opponent', '')
                        player_team = stat.get('team', player.team)
                        
                        # Apply location filter (HOME/AWAY)
                        if self.location_var.get() != "ALL":
                            # Determine if home or away game
                            # We'll use week + team hash to determine home/away (simplified logic)
                            is_home = (week + hash(player_team)) % 2 == 0
                            
                            if self.location_var.get() == "HOME" and not is_home:
                                continue
                            elif self.location_var.get() == "AWAY" and is_home:
                                continue
                        
                        # Apply venue filter (DOME/OUTSIDE)
                        if self.venue_var.get() != "ALL":
                            # Check if game is in a dome
                            # Game is in dome if either team plays in a dome and it's their home game
                            is_home = (week + hash(player_team)) % 2 == 0
                            
                            if is_home:
                                # Home game - check if player's team has a dome
                                game_in_dome = player_team in DOME_TEAMS
                            else:
                                # Away game - check if opponent has a dome
                                game_in_dome = opponent in DOME_TEAMS
                            
                            if self.venue_var.get() == "DOME" and not game_in_dome:
                                continue
                            elif self.venue_var.get() == "OUTSIDE" and game_in_dome:
                                continue
                        
                        # Calculate custom points
                        custom_pts = self.calculate_custom_points(stats, player.position)
                        
                        # Format opponent with home/away indicator
                        is_home = (week + hash(player_team)) % 2 == 0
                        opponent_display = f"vs {opponent}" if is_home else f"@ {opponent}"
                        
                        row = {
                            'player': format_name(player.name),
                            'pos': player.position,
                            'team': player.team or '-',
                            'week': week,
                            'opp': opponent_display,
                            'pts': f"{custom_pts:.1f}",
                            'snaps': int(stats.get('off_snp', 0)),
                            'comp': int(stats.get('pass_cmp', 0)) if player.position == 'QB' else '-',
                            'pass_yd': int(stats.get('pass_yd', 0)) if player.position == 'QB' else '-',
                            'pass_td': int(stats.get('pass_td', 0)) if player.position == 'QB' else '-',
                            'rush_yd': int(stats.get('rush_yd', 0)),
                            'rush_td': max(0, int(stats.get('rush_td', 0))),
                            'rec': int(stats.get('rec', 0)) if player.position != 'QB' else '-',
                            'rec_yd': int(stats.get('rec_yd', 0)) if player.position != 'QB' else '-',
                            'rec_td': int(stats.get('rec_td', 0)) if player.position != 'QB' else '-',
                            '_pts_float': custom_pts,  # For sorting
                            '_week_int': week  # For sorting
                        }
                        rows.append(row)
        else:
            # Normal filtering without roster position
            for week, week_data in self.weekly_stats.items():
                # Skip if week filter is active
                if selected_week != "ALL" and str(week) != selected_week:
                    continue
                
                for player_id, stats_list in week_data.items():
                    if player_id not in self.player_lookup:
                        continue
                        
                    player = self.player_lookup[player_id]
                    
                    # Position filter
                    if self.selected_position == "FLEX":
                        if player.position not in ["RB", "WR", "TE"]:
                            continue
                    elif self.selected_position != "ALL" and player.position != self.selected_position:
                        continue
                    
                    # Search filter
                    if search_text and search_text not in player.name.lower():
                        continue
                    
                    # Process each game for this player
                    for stat in stats_list:
                        stats = stat.get('stats', {})
                        opponent = stat.get('opponent', '')
                        player_team = stat.get('team', player.team)
                        
                        # Apply location filter (HOME/AWAY)
                        if self.location_var.get() != "ALL":
                            # Determine if home or away game
                            # We'll use week + team hash to determine home/away (simplified logic)
                            is_home = (week + hash(player_team)) % 2 == 0
                            
                            if self.location_var.get() == "HOME" and not is_home:
                                continue
                            elif self.location_var.get() == "AWAY" and is_home:
                                continue
                        
                        # Apply venue filter (DOME/OUTSIDE)
                        if self.venue_var.get() != "ALL":
                            # Check if game is in a dome
                            # Game is in dome if either team plays in a dome and it's their home game
                            is_home = (week + hash(player_team)) % 2 == 0
                            
                            if is_home:
                                # Home game - check if player's team has a dome
                                game_in_dome = player_team in DOME_TEAMS
                            else:
                                # Away game - check if opponent has a dome
                                game_in_dome = opponent in DOME_TEAMS
                            
                            if self.venue_var.get() == "DOME" and not game_in_dome:
                                continue
                            elif self.venue_var.get() == "OUTSIDE" and game_in_dome:
                                continue
                        
                        # Calculate custom points
                        custom_pts = self.calculate_custom_points(stats, player.position)
                        
                        # Format opponent with home/away indicator
                        is_home = (week + hash(player_team)) % 2 == 0
                        opponent_display = f"vs {opponent}" if is_home else f"@ {opponent}"
                        
                        row = {
                            'player': format_name(player.name),
                            'pos': player.position,
                            'team': player.team or '-',
                            'week': week,
                            'opp': opponent_display,
                            'pts': f"{custom_pts:.1f}",
                            'snaps': int(stats.get('off_snp', 0)),
                            'comp': int(stats.get('pass_cmp', 0)) if player.position == 'QB' else '-',
                            'pass_yd': int(stats.get('pass_yd', 0)) if player.position == 'QB' else '-',
                            'pass_td': int(stats.get('pass_td', 0)) if player.position == 'QB' else '-',
                            'rush_yd': int(stats.get('rush_yd', 0)),
                            'rush_td': max(0, int(stats.get('rush_td', 0))),
                            'rec': int(stats.get('rec', 0)) if player.position != 'QB' else '-',
                            'rec_yd': int(stats.get('rec_yd', 0)) if player.position != 'QB' else '-',
                            'rec_td': int(stats.get('rec_td', 0)) if player.position != 'QB' else '-',
                            '_pts_float': custom_pts,  # For sorting
                            '_week_int': week  # For sorting
                        }
                        rows.append(row)
        
        return rows
    
    def build_summarized_data(self, search_text, selected_week):
        """Build data for summarized view (season totals)"""
        rows = []
        player_totals = {}
        
        # Aggregate data by player
        for week, week_data in self.weekly_stats.items():
            # Skip if week filter is active
            if selected_week != "ALL" and str(week) != selected_week:
                continue
            
            for player_id, stats_list in week_data.items():
                if player_id not in self.player_lookup:
                    continue
                    
                player = self.player_lookup[player_id]
                
                # Position filter
                if self.selected_position == "FLEX":
                    if player.position not in ["RB", "WR", "TE"]:
                        continue
                elif self.selected_position != "ALL" and player.position != self.selected_position:
                    continue
                
                # Search filter
                if search_text and search_text not in player.name.lower():
                    continue
                
                # Initialize player totals if needed
                if player_id not in player_totals:
                    player_totals[player_id] = {
                        'player': format_name(player.name),
                        'pos': player.position,
                        'team': player.team or '-',
                        'games': 0,
                        'pts': 0,
                        'snaps': 0,
                        'comp': 0,
                        'pass_yd': 0,
                        'pass_td': 0,
                        'rush_yd': 0,
                        'rush_td': 0,
                        'rec': 0,
                        'rec_yd': 0,
                        'rec_td': 0
                    }
                
                # Aggregate stats
                for stat in stats_list:
                    stats = stat.get('stats', {})
                    totals = player_totals[player_id]
                    totals['games'] += 1
                    # Calculate custom points for this game
                    custom_pts = self.calculate_custom_points(stats, player.position)
                    totals['pts'] += custom_pts
                    totals['snaps'] += int(stats.get('off_snp', 0))
                    if player.position == 'QB':
                        totals['comp'] += int(stats.get('pass_cmp', 0))
                        totals['pass_yd'] += int(stats.get('pass_yd', 0))
                        totals['pass_td'] += int(stats.get('pass_td', 0))
                    totals['rush_yd'] += int(stats.get('rush_yd', 0))
                    totals['rush_td'] += int(stats.get('rush_td', 0))
                    if player.position != 'QB':
                        totals['rec'] += int(stats.get('rec', 0))
                        totals['rec_yd'] += int(stats.get('rec_yd', 0))
                        totals['rec_td'] += int(stats.get('rec_td', 0))
        
        # Convert to rows
        for player_id, totals in player_totals.items():
            row = {
                'player': totals['player'],
                'pos': totals['pos'],
                'team': totals['team'],
                'week': f"{totals['games']}g",  # Show games played
                'opp': '2024',  # Show year instead of opponent
                'pts': f"{totals['pts']:.1f}",
                'snaps': totals['snaps'] if totals['snaps'] > 0 else '-',
                'comp': totals['comp'] if totals['comp'] > 0 else '-',
                'pass_yd': totals['pass_yd'] if totals['pass_yd'] > 0 else '-',
                'pass_td': totals['pass_td'] if totals['pass_td'] > 0 else '-',
                'rush_yd': totals['rush_yd'] if totals['rush_yd'] > 0 else '-',
                'rush_td': totals['rush_td'] if totals['rush_td'] > 0 else '-',
                'rec': totals['rec'] if totals['rec'] > 0 else '-',
                'rec_yd': totals['rec_yd'] if totals['rec_yd'] > 0 else '-',
                'rec_td': totals['rec_td'] if totals['rec_td'] > 0 else '-',
                '_pts_float': totals['pts'],  # For sorting
                '_week_int': totals['games']  # For sorting
            }
            rows.append(row)
        
        return rows
        
    def sort_rows(self, rows):
        """Sort rows by current sort column"""
        if not self.sort_column:
            return
            
        # Define sort keys for special columns
        def get_sort_key(row):
            if self.sort_column == 'week':
                return row['_week_int']
            elif self.sort_column == 'pts':
                return row['_pts_float']
            elif self.sort_column in ['snaps', 'comp', 'pass_yd', 'pass_td', 'rush_yd', 'rush_td', 'rec', 'rec_yd', 'rec_td']:
                val = row[self.sort_column]
                return 0 if val == '-' else int(val)
            else:
                return row[self.sort_column]
        
        rows.sort(key=get_sort_key, reverse=not self.sort_ascending)
        
    def sort_by(self, column):
        """Handle column header click for sorting"""
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = False
            
        self.apply_filters()
        
    def filter_by_position(self, position):
        """Filter by position"""
        self.selected_position = position
        
        # Update button appearances
        for pos, btn in self.position_buttons.items():
            if pos == position:
                if pos == "ALL":
                    btn.config(bg=DARK_THEME['button_active'])
                elif pos == "FLEX":
                    btn.config(bg=DARK_THEME['button_active'])
                else:
                    btn.config(bg=get_position_color(pos))
            else:
                btn.config(bg=DARK_THEME['button_bg'])
        
        # Update column visibility
        self.update_column_visibility()
        self.apply_filters()
    
    def set_view_mode(self, mode):
        """Set the view mode (detailed or summarized)"""
        self.view_mode = mode
        
        # Update button appearances
        if mode == "detailed":
            self.detailed_btn.config(bg=DARK_THEME['button_active'])
            self.summarized_btn.config(bg=DARK_THEME['button_bg'])
        else:
            self.detailed_btn.config(bg=DARK_THEME['button_bg'])
            self.summarized_btn.config(bg=DARK_THEME['button_active'])
        
        self.apply_filters()
    
    def update_column_visibility(self):
        """Show/hide columns based on selected position"""
        # Define which columns are relevant for each position
        qb_columns = ['comp', 'pass_yd', 'pass_td', 'rush_yd', 'rush_td']
        skill_columns = ['rush_yd', 'rush_td', 'rec', 'rec_yd', 'rec_td']
        
        if self.selected_position == "QB":
            # Show QB columns, hide receiving columns
            for col in qb_columns:
                if col == 'comp':
                    self.tree.column(col, width=60)
                else:
                    self.tree.column(col, width=80 if 'yd' in col else 70)
            for col in ['rec', 'rec_yd', 'rec_td']:
                self.tree.column(col, width=0, stretch=False)
        elif self.selected_position in ["RB", "WR", "TE"]:
            # Show skill position columns, hide passing columns
            for col in ['comp', 'pass_yd', 'pass_td']:
                self.tree.column(col, width=0, stretch=False)
            for col in skill_columns:
                if col == 'rec':
                    self.tree.column(col, width=50)
                else:
                    self.tree.column(col, width=80 if 'yd' in col else 70)
        elif self.selected_position == "FLEX":
            # Show skill position columns, hide passing columns
            for col in ['comp', 'pass_yd', 'pass_td']:
                self.tree.column(col, width=0, stretch=False)
            for col in skill_columns:
                if col == 'rec':
                    self.tree.column(col, width=50)
                else:
                    self.tree.column(col, width=80 if 'yd' in col else 70)
        else:  # ALL
            # Show all columns with default widths
            self.tree.column('comp', width=60)
            self.tree.column('pass_yd', width=80)
            self.tree.column('pass_td', width=70)
            self.tree.column('rush_yd', width=80)
            self.tree.column('rush_td', width=70)
            self.tree.column('rec', width=50)
            self.tree.column('rec_yd', width=70)
            self.tree.column('rec_td', width=60)
    
    def save_filter_state(self):
        """Save current filter state to history"""
        state = {
            'search': self.search_var.get(),
            'position': self.selected_position,
            'week': self.week_var.get()
        }
        
        # Only save if different from current state
        if self.current_filter_state != state:
            if self.current_filter_state:
                self.filter_history.append(self.current_filter_state)
            self.current_filter_state = state
            
            # Enable/disable back button
            self.back_button.config(state='normal' if self.filter_history else 'disabled')
    
    def clear_filters(self):
        """Clear all filters"""
        self.save_filter_state()
        
        self.search_var.set('')
        self.selected_position = "ALL"
        self.week_var.set("ALL")
        self.location_var.set("ALL")
        self.venue_var.set("ALL")
        
        # Update button appearances
        for pos, btn in self.position_buttons.items():
            if pos == "ALL":
                btn.config(bg=DARK_THEME['button_active'])
            else:
                btn.config(bg=DARK_THEME['button_bg'])
        
        self.apply_filters()
    
    def go_back(self):
        """Go back to previous filter state"""
        if self.filter_history:
            # Save current state for redo if needed
            prev_state = self.filter_history.pop()
            
            # Apply previous state
            self.search_var.set(prev_state['search'])
            self.selected_position = prev_state['position']
            self.week_var.set(prev_state['week'])
            
            # Update UI
            for pos, btn in self.position_buttons.items():
                if pos == self.selected_position:
                    if pos == "ALL":
                        btn.config(bg=DARK_THEME['button_active'])
                    else:
                        btn.config(bg=get_position_color(pos))
                else:
                    btn.config(bg=DARK_THEME['button_bg'])
            
            self.current_filter_state = prev_state
            self.back_button.config(state='normal' if self.filter_history else 'disabled')
            
            self.apply_filters()
    
    def on_search_changed(self):
        """Handle search text changes with debouncing"""
        # Cancel any pending search
        if hasattr(self, '_search_after_id'):
            self.after_cancel(self._search_after_id)
        
        # Schedule new search after 300ms
        self._search_after_id = self.after(300, self.apply_filters)
    
    def on_right_click(self, event):
        """Handle right-click on tree item"""
        # Identify the row
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        # Select the item
        self.tree.selection_set(item)
        
        # Get player name from the row
        values = self.tree.item(item, 'values')
        if not values:
            return
        
        player_name = values[0]  # First column is player name
        
        # Create context menu
        menu = tk.Menu(self, tearoff=0,
                      bg=DARK_THEME['bg_secondary'],
                      fg=DARK_THEME['text_primary'],
                      activebackground=DARK_THEME['button_active'],
                      activeforeground='white')
        
        menu.add_command(label=f"Filter: {player_name}",
                        command=lambda: self.filter_by_player(player_name))
        menu.add_separator()
        menu.add_command(label="Clear Filters",
                        command=self.clear_filters)
        
        # Show menu
        menu.post(event.x_root, event.y_root)
    
    def filter_by_player(self, player_name):
        """Filter to show only a specific player"""
        self.save_filter_state()
        
        # Set search to player name
        self.search_var.set(player_name)
        
        # Apply the filter
        self.apply_filters()
    
