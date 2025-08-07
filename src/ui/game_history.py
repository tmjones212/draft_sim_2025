import tkinter as tk
from tkinter import ttk
import json
import os
import statistics
from typing import Dict, List, Optional
from PIL import Image, ImageTk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .theme import DARK_THEME, get_position_color, get_team_color
from .styled_widgets import StyledFrame
from ..utils.player_extensions import format_name
from ..config.scoring import SCORING_CONFIG
from ..services.vegas_props_service import VegasPropsService

# Teams with dome stadiums
DOME_TEAMS = {'ATL', 'DET', 'MIN', 'NO', 'LV', 'ARI', 'AZ', 'DAL', 'HOU', 'IND'}


class GameHistory(StyledFrame):
    def __init__(self, parent, all_players, player_pool_service=None, on_draft=None, **kwargs):
        super().__init__(parent, bg_type='primary', **kwargs)
        self.all_players = all_players
        self.player_pool_service = player_pool_service
        self.on_draft = on_draft
        self.player_lookup = {p.player_id: p for p in all_players if hasattr(p, 'player_id')}
        self.weekly_stats = {}
        self.filtered_players = []
        
        # UI state
        self.selected_position = "OFF"
        self.selected_week = "ALL"
        self.sort_column = 'pts'  # Default sort by points
        self.sort_ascending = False  # Default descending
        self.search_var = tk.StringVar()
        self.view_mode = "summarized"  # "detailed" or "summarized"
        self.min_games_var = tk.IntVar(value=1)  # Minimum games filter
        
        # Vegas props columns checkboxes
        self.show_vegas_yards_var = tk.BooleanVar(value=False)  # Smart yards (position-specific)
        self.show_vegas_pass_var = tk.BooleanVar(value=False)
        self.show_vegas_rush_var = tk.BooleanVar(value=False)
        self.show_vegas_rec_var = tk.BooleanVar(value=False)
        self.vegas_props_service = VegasPropsService()
        
        # Filter history for back button
        self.filter_history = []
        self.current_filter_state = None
        
        # Graph data
        self.graph_players = {}  # player_id -> {name, weeks, points, color}
        self.graph_canvas = None
        self.figure = None
        self.week_range_start = 1
        self.week_range_end = 18
        self.last_clicked_item = None  # Track last clicked item for shift+click
        self.graph_metric = "points"  # Default metric for graph
        
        self.setup_ui()
        self.update_column_visibility()  # Set initial column visibility
        self.update_sort_arrows()  # Show initial sort direction
        self.load_weekly_stats()
        # Store original sash position (will be set by default paned window behavior)
        self._original_sash_pos = None
        
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
        
        # Vegas props checkboxes in header (only show in summarized mode)
        self.vegas_frame = tk.Frame(header_frame, bg=DARK_THEME['bg_secondary'])
        
        vegas_separator = tk.Frame(self.vegas_frame, width=30, bg=DARK_THEME['bg_secondary'])
        vegas_separator.pack(side='left')
        
        vegas_label = tk.Label(
            self.vegas_frame,
            text="Vegas:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 11)
        )
        vegas_label.pack(side='left', padx=(0, 8))
        
        self.vegas_yards_check = tk.Checkbutton(
            self.vegas_frame,
            text="Yards",
            variable=self.show_vegas_yards_var,
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            selectcolor=DARK_THEME['bg_tertiary'],
            activebackground=DARK_THEME['bg_secondary'],
            activeforeground=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            command=self.update_vegas_columns
        )
        self.vegas_yards_check.pack(side='left', padx=5)
        
        self.vegas_pass_check = tk.Checkbutton(
            self.vegas_frame,
            text="Pass",
            variable=self.show_vegas_pass_var,
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            selectcolor=DARK_THEME['bg_tertiary'],
            activebackground=DARK_THEME['bg_secondary'],
            activeforeground=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            command=self.update_vegas_columns
        )
        self.vegas_pass_check.pack(side='left', padx=5)
        
        self.vegas_rush_check = tk.Checkbutton(
            self.vegas_frame,
            text="Rush",
            variable=self.show_vegas_rush_var,
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            selectcolor=DARK_THEME['bg_tertiary'],
            activebackground=DARK_THEME['bg_secondary'],
            activeforeground=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            command=self.update_vegas_columns
        )
        self.vegas_rush_check.pack(side='left', padx=5)
        
        self.vegas_rec_check = tk.Checkbutton(
            self.vegas_frame,
            text="Rec",
            variable=self.show_vegas_rec_var,
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            selectcolor=DARK_THEME['bg_tertiary'],
            activebackground=DARK_THEME['bg_secondary'],
            activeforeground=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            command=self.update_vegas_columns
        )
        self.vegas_rec_check.pack(side='left', padx=5)
        
        # Show Vegas frame only in summarized mode
        if self.view_mode == "summarized":
            self.vegas_frame.pack(side='left')
        
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
        
        positions = ["ALL", "OFF", "QB", "RB", "WR", "TE", "FLEX", "IDP", "DB", "LB"]
        self.position_buttons = {}
        
        # Create position buttons container (single row)
        pos_container = tk.Frame(filter_frame, bg=DARK_THEME['bg_secondary'])
        pos_container.pack(side='left', padx=(0, 20))
        
        # Main positions only
        for pos in positions:
            if pos == "ALL":
                btn_bg = DARK_THEME['button_active'] if pos == self.selected_position else DARK_THEME['button_bg']
            elif pos in ["OFF", "FLEX", "IDP"]:
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
        
        # Show Available checkbox
        self.show_available_var = tk.BooleanVar(value=False)
        self.show_available_check = tk.Checkbutton(
            filter_frame,
            text="Show Available",
            variable=self.show_available_var,
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            selectcolor=DARK_THEME['bg_tertiary'],
            activebackground=DARK_THEME['bg_secondary'],
            activeforeground=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            command=self.apply_filters
        )
        self.show_available_check.pack(side='left', padx=(20, 0))
        
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
        
        # Minimum games filter (only shown in summarized view)
        self.games_filter_frame = tk.Frame(filter_frame, bg=DARK_THEME['bg_secondary'])
        self.games_filter_frame.pack(side='left', padx=(20, 0))
        
        self.games_label = tk.Label(
            self.games_filter_frame,
            text="Min Games:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        self.games_label.pack(side='left', padx=(0, 5))
        
        self.games_spinbox = tk.Spinbox(
            self.games_filter_frame,
            from_=1,
            to=17,
            textvariable=self.min_games_var,
            width=3,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            command=self.on_min_games_changed
        )
        self.games_spinbox.pack(side='left')
        
        # Initially hide games filter
        self.games_filter_frame.pack_forget()
        
        # Create paned window for table and graph
        self.paned_window = tk.PanedWindow(
            container,
            orient='horizontal',
            bg=DARK_THEME['bg_secondary'],
            sashwidth=8,
            sashrelief='flat',
            borderwidth=0
        )
        self.paned_window.pack(fill='both', expand=True)
        
        # Table container (left side)
        table_container = StyledFrame(self.paned_window, bg_type='secondary')
        self.paned_window.add(table_container, minsize=600)
        
        # Graph container (right side)
        graph_container = StyledFrame(self.paned_window, bg_type='secondary')
        self.paned_window.add(graph_container, minsize=400)
        
        # Create treeview for table
        columns = ('player', 'pos', 'rank', 'team', 'week', 'opp', 'pts', 'median', 'avg', 'snaps', 'pts_per_snap', 'comp', 'pass_yd', 'pass_td', 
                  'rush_yd', 'rush_td', 'tgt', 'rec', 'rec_yd', 'rec_td', 'vegas_yards', 'vegas_pass', 'vegas_rush', 'vegas_rec')
        
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show='tree headings',
            height=20
        )
        
        # Configure columns with proper initial widths
        self.tree.column('#0', width=0, stretch=False)  # Hide tree column
        self.tree.column('player', width=150, anchor='w', stretch=False)
        self.tree.column('pos', width=40, anchor='center', stretch=False)
        self.tree.column('rank', width=55, anchor='center', stretch=False)
        self.tree.column('team', width=45, anchor='center', stretch=False)
        self.tree.column('week', width=40, anchor='center', stretch=False)
        self.tree.column('opp', width=65, anchor='center', stretch=False)
        self.tree.column('pts', width=55, anchor='center', stretch=False)
        self.tree.column('median', width=55, anchor='center', stretch=False)
        self.tree.column('avg', width=55, anchor='center', stretch=False)
        self.tree.column('snaps', width=55, anchor='center', stretch=False)
        self.tree.column('pts_per_snap', width=65, anchor='center', stretch=False)
        self.tree.column('comp', width=55, anchor='center', stretch=False)
        self.tree.column('pass_yd', width=70, anchor='center', stretch=False)
        self.tree.column('pass_td', width=65, anchor='center', stretch=False)
        self.tree.column('rush_yd', width=70, anchor='center', stretch=False)
        self.tree.column('rush_td', width=65, anchor='center', stretch=False)
        self.tree.column('tgt', width=40, anchor='center', stretch=False)
        self.tree.column('rec', width=45, anchor='center', stretch=False)
        self.tree.column('rec_yd', width=65, anchor='center', stretch=False)
        self.tree.column('rec_td', width=60, anchor='center', stretch=False)
        self.tree.column('vegas_yards', width=80, anchor='center', stretch=False)
        self.tree.column('vegas_pass', width=80, anchor='center', stretch=False)
        self.tree.column('vegas_rush', width=80, anchor='center', stretch=False)
        self.tree.column('vegas_rec', width=80, anchor='center', stretch=False)
        
        # Configure headings
        self.tree.heading('player', text='Player', command=lambda: self.sort_by('player'))
        self.tree.heading('pos', text='Pos', command=lambda: self.sort_by('pos'))
        self.tree.heading('rank', text='Rank', command=lambda: self.sort_by('rank'))
        self.tree.heading('team', text='Team', command=lambda: self.sort_by('team'))
        self.tree.heading('week', text='Wk', command=lambda: self.sort_by('week'))
        self.tree.heading('opp', text='Opp', command=lambda: self.sort_by('opp'))
        self.tree.heading('pts', text='Pts', command=lambda: self.sort_by('pts'))
        self.tree.heading('median', text='Med', command=lambda: self.sort_by('median'))
        self.tree.heading('avg', text='Avg', command=lambda: self.sort_by('avg'))
        self.tree.heading('snaps', text='Snaps', command=lambda: self.sort_by('snaps'))
        self.tree.heading('pts_per_snap', text='Pts/Snap', command=lambda: self.sort_by('pts_per_snap'))
        self.tree.heading('comp', text='Comp', command=lambda: self.sort_by('comp'))
        self.tree.heading('pass_yd', text='Pass Yds', command=lambda: self.sort_by('pass_yd'))
        self.tree.heading('pass_td', text='Pass TD', command=lambda: self.sort_by('pass_td'))
        self.tree.heading('rush_yd', text='Rush Yds', command=lambda: self.sort_by('rush_yd'))
        self.tree.heading('rush_td', text='Rush TD', command=lambda: self.sort_by('rush_td'))
        self.tree.heading('tgt', text='Tgt', command=lambda: self.sort_by('tgt'))
        self.tree.heading('rec', text='Rec', command=lambda: self.sort_by('rec'))
        self.tree.heading('rec_yd', text='Rec Yds', command=lambda: self.sort_by('rec_yd'))
        self.tree.heading('rec_td', text='Rec TD', command=lambda: self.sort_by('rec_td'))
        self.tree.heading('vegas_yards', text='Vegas Yds', command=lambda: self.sort_by('vegas_yards'))
        self.tree.heading('vegas_pass', text='Vegas Pass', command=lambda: self.sort_by('vegas_pass'))
        self.tree.heading('vegas_rush', text='Vegas Rush', command=lambda: self.sort_by('vegas_rush'))
        self.tree.heading('vegas_rec', text='Vegas Rec', command=lambda: self.sort_by('vegas_rec'))
        
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
        
        # Bind right-click and left-click
        self.tree.bind('<Button-3>', self.on_right_click)
        self.tree.bind('<Button-1>', self.on_left_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_selection_change)
        
        # Setup graph
        self.setup_graph(graph_container)
        
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
        """Load all weekly stats data from aggregated file"""
        # Try to load from aggregated file first
        stats_file = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'aggregated_player_stats_2024.json')
        stats_file = os.path.abspath(stats_file)
        
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    all_player_data = json.load(f)
                
                # Reorganize data by week
                for player_id, player_data in all_player_data.items():
                    if player_id not in self.player_lookup:
                        continue
                    
                    player = self.player_lookup[player_id]
                    weekly_stats = player_data.get('weekly_stats', [])
                    
                    for week_data in weekly_stats:
                        week = week_data.get('week', 0)
                        if week < 1 or week > 18:
                            continue
                        
                        if week not in self.weekly_stats:
                            self.weekly_stats[week] = {}
                        
                        # Store the week data directly (not in a list)
                        # This ensures only one entry per player per week
                        self.weekly_stats[week][player_id] = week_data
                
                self.apply_filters()
                self.status_label.config(text=f"Loaded {len(self.weekly_stats)} weeks of game data")
                return
            except Exception as e:
                print(f"Error loading aggregated stats: {e}")
        
        # Fallback to old method if aggregated file doesn't exist
        stats_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'stats_data')
        stats_dir = os.path.abspath(stats_dir)
        
        if not os.path.exists(stats_dir):
            self.status_label.config(text="Stats data not found")
            return
            
        # Load all weeks and positions
        for week in range(1, 19):
            self.weekly_stats[week] = {}
            
            for position in ['qb', 'rb', 'wr', 'te', 'db', 'lb']:
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
        
        # Defensive scoring for LB and DB
        if position in ['LB', 'DB']:
            # IDP stats use different field names
            solo_tackles = stats.get('idp_tkl_solo', 0)
            total_tackles = stats.get('idp_tkl', 0)
            assist_tackles = max(0, total_tackles - solo_tackles)  # Calculate assists
            
            points += solo_tackles * SCORING_CONFIG.get('tackle_solo', 1.75)
            points += assist_tackles * SCORING_CONFIG.get('tackle_assist', 1.0)
            points += stats.get('idp_sack', 0) * SCORING_CONFIG.get('sack', 4.0)
            points += stats.get('idp_int', 0) * SCORING_CONFIG.get('int', 6.0)
            points += stats.get('idp_ff', 0) * SCORING_CONFIG.get('ff', 4.0)
            points += stats.get('idp_fr', 0) * SCORING_CONFIG.get('fr', 3.0)
            points += stats.get('idp_def_td', 0) * SCORING_CONFIG.get('def_td', 6.0)
            points += stats.get('idp_safety', 0) * SCORING_CONFIG.get('safety', 2.0)
            points += stats.get('idp_pass_def', 0) * SCORING_CONFIG.get('pass_defended', 1.5)
            return points
        
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
    
    def on_min_games_changed(self):
        """Handle minimum games filter changes"""
        self.apply_filters()
        
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
            # Get Vegas props if in summarized mode
            vegas_yards = '-'
            vegas_pass = '-'
            vegas_rush = '-'
            vegas_rec = '-'
            
            if self.view_mode == "summarized":
                player_name = row['player']
                position = row['pos']
                props = self.vegas_props_service.get_player_props(player_name)
                
                # Smart yards - position-specific
                if position == 'QB' and 'passing_yards' in props:
                    vegas_yards = f"{props['passing_yards'].prop_value:.0f}"
                elif position == 'RB' and 'rushing_yards' in props:
                    vegas_yards = f"{props['rushing_yards'].prop_value:.0f}"
                elif position in ['WR', 'TE'] and 'receiving_yards' in props:
                    vegas_yards = f"{props['receiving_yards'].prop_value:.0f}"
                
                # Individual columns
                if 'passing_yards' in props:
                    vegas_pass = f"{props['passing_yards'].prop_value:.0f}"
                if 'rushing_yards' in props:
                    vegas_rush = f"{props['rushing_yards'].prop_value:.0f}"
                if 'receiving_yards' in props:
                    vegas_rec = f"{props['receiving_yards'].prop_value:.0f}"
            
            values = (row['player'], row['pos'], row.get('rank', '-'), row['team'], row['week'], row['opp'],
                     row['pts'], row.get('median', '-'), row.get('avg', '-'), row['snaps'], row.get('pts_per_snap', '-'), row['comp'], row['pass_yd'], row['pass_td'], row['rush_yd'], 
                     row['rush_td'], row.get('tgt', '-'), row['rec'], row['rec_yd'], row['rec_td'], vegas_yards, vegas_pass, vegas_rush, vegas_rec)
            
            # Add row with position-based colors
            position = row['pos']
            tags = (f'pos_{position}',)
            
            self.tree.insert('', 'end', values=values, tags=tags)
        
        # Add totals row if filtering by single player
        if self.should_show_totals(rows):
            self.add_totals_row(rows)
        
        # Configure tag colors for positions
        position_colors = {
            'QB': '#FF5E5B',  # Pink/Red
            'RB': '#23CDCD',  # Teal
            'WR': '#5E9BFF',  # Blue
            'TE': '#FF8C42',  # Orange
            'LB': '#9370DB',  # Medium Purple
            'DB': '#20B2AA'   # Light Sea Green
        }
        
        # Configure each position tag with a darker shade for better readability
        for pos, color in position_colors.items():
            # Create a darker version of the color by mixing with background
            self.tree.tag_configure(f'pos_{pos}', background=self.blend_colors(color, DARK_THEME['bg_secondary'], 0.3))
        
        # Configure special tags
        self.tree.tag_configure('totals', background=DARK_THEME['button_active'], foreground='white')
        self.tree.tag_configure('separator', background=DARK_THEME['bg_primary'])
        
        # Update status
        self.status_label.config(text=f"Showing {len(rows)} {'seasons' if self.view_mode == 'summarized' else 'games'}")
    
    def build_detailed_data(self, search_text, selected_week):
        """Build data for detailed view (individual games)"""
        rows = []
        
        # First pass: collect all games by week and position for ranking
        week_position_data = {}  # {week: {position: [(player_id, pts)]}}
        
        for week, week_data in self.weekly_stats.items():
            if selected_week != "ALL" and str(week) != selected_week:
                continue
                
            week_position_data[week] = {}
            
            for player_id, stats_data in week_data.items():
                if player_id not in self.player_lookup:
                    continue
                    
                player = self.player_lookup[player_id]
                position = player.position
                
                # Handle both single stat object and list of stats
                stats_list = stats_data if isinstance(stats_data, list) else [stats_data]
                
                for stat in stats_list:
                    stats = stat.get('stats', {})
                    # Only count if player actually played
                    if int(stats.get('off_snp', 0)) > 0:
                        custom_pts = self.calculate_custom_points(stats, position)
                        
                        if position not in week_position_data[week]:
                            week_position_data[week][position] = []
                        week_position_data[week][position].append((player_id, custom_pts))
                        break  # Only one game per week
        
        # Sort each position by points descending for ranking
        for week in week_position_data:
            for position in week_position_data[week]:
                week_position_data[week][position].sort(key=lambda x: x[1], reverse=True)
        
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
                        
                        # Skip games where player didn't play (0 snaps)
                        # Use defensive snaps for DB/LB, offensive snaps for others
                        if player.position in ['DB', 'LB']:
                            if int(stats.get('def_snp', 0)) == 0:
                                continue
                        else:
                            if int(stats.get('off_snp', 0)) == 0:
                                continue
                        
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
                        
                        # Calculate pts per snap
                        # Use defensive snaps for LB/DB, offensive snaps for others
                        if player.position in ['LB', 'DB']:
                            snaps = int(stats.get('def_snp', 0))
                        else:
                            snaps = int(stats.get('off_snp', 0))
                        pts_per_snap = custom_pts / snaps if snaps > 0 else 0
                        
                        # Find rank for this player
                        rank = '-'
                        if week in week_position_data and player.position in week_position_data[week]:
                            for idx, (pid, pts) in enumerate(week_position_data[week][player.position]):
                                if pid == player_id and abs(pts - custom_pts) < 0.01:  # Account for float precision
                                    rank = f"{player.position}{idx + 1}"
                                    break
                        
                        row = {
                            'player': format_name(player.name),
                            'pos': player.position,
                            'rank': rank,
                            'team': player.team or '-',
                            'week': week,
                            'opp': opponent_display,
                            'pts': f"{custom_pts:.1f}",
                            'snaps': snaps,
                            'pts_per_snap': f"{pts_per_snap:.3f}" if snaps > 0 else '-',
                            'comp': int(stats.get('pass_cmp', 0)) if player.position == 'QB' else '-',
                            'pass_yd': int(stats.get('pass_yd', 0)) if player.position == 'QB' else '-',
                            'pass_td': int(stats.get('pass_td', 0)) if player.position == 'QB' else '-',
                            'rush_yd': int(stats.get('rush_yd', 0)),
                            'rush_td': max(0, int(stats.get('rush_td', 0))),
                            'tgt': int(stats.get('rec_tgt', 0)) if player.position != 'QB' else '-',
                            'rec': int(stats.get('rec', 0)) if player.position != 'QB' else '-',
                            'rec_yd': int(stats.get('rec_yd', 0)) if player.position != 'QB' else '-',
                            'rec_td': int(stats.get('rec_td', 0)) if player.position != 'QB' else '-',
                            '_pts_float': custom_pts,  # For sorting
                            '_week_int': week,  # For sorting
                            '_pts_per_snap_float': pts_per_snap,  # For sorting
                            '_rank_int': int(rank[2:]) if rank != '-' else 999  # For sorting
                        }
                        rows.append(row)
        else:
            # Normal filtering without roster position
            for week, week_data in self.weekly_stats.items():
                # Skip if week filter is active
                if selected_week != "ALL" and str(week) != selected_week:
                    continue
                
                for player_id, stats_data in week_data.items():
                    if player_id not in self.player_lookup:
                        continue
                        
                    player = self.player_lookup[player_id]
                    
                    # Position filter
                    if self.selected_position == "FLEX":
                        if player.position not in ["RB", "WR", "TE"]:
                            continue
                    elif self.selected_position == "IDP":
                        if player.position not in ["DB", "LB"]:
                            continue
                    elif self.selected_position == "OFF":
                        if player.position not in ["QB", "RB", "WR", "TE"]:
                            continue
                    elif self.selected_position != "ALL" and player.position != self.selected_position:
                        continue
                    
                    # Search filter
                    if search_text and search_text not in player.name.lower():
                        continue
                    
                    # Show Available filter (only undrafted players)
                    if self.show_available_var.get() and self.player_pool_service:
                        if not self.player_pool_service.is_player_available(player):
                            continue
                    
                    # Handle both single stat object and list of stats
                    stats_list = stats_data if isinstance(stats_data, list) else [stats_data]
                    
                    # Process each game for this player
                    for stat in stats_list:
                        stats = stat.get('stats', {})
                        
                        # Skip games where player didn't play (0 snaps)
                        # Use defensive snaps for DB/LB, offensive snaps for others
                        if player.position in ['DB', 'LB']:
                            if int(stats.get('def_snp', 0)) == 0:
                                continue
                        else:
                            if int(stats.get('off_snp', 0)) == 0:
                                continue
                        
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
                        
                        # Calculate pts per snap
                        # Use defensive snaps for LB/DB, offensive snaps for others
                        if player.position in ['LB', 'DB']:
                            snaps = int(stats.get('def_snp', 0))
                        else:
                            snaps = int(stats.get('off_snp', 0))
                        pts_per_snap = custom_pts / snaps if snaps > 0 else 0
                        
                        # Find rank for this player
                        rank = '-'
                        if week in week_position_data and player.position in week_position_data[week]:
                            for idx, (pid, pts) in enumerate(week_position_data[week][player.position]):
                                if pid == player_id and abs(pts - custom_pts) < 0.01:  # Account for float precision
                                    rank = f"{player.position}{idx + 1}"
                                    break
                        
                        row = {
                            'player': format_name(player.name),
                            'pos': player.position,
                            'rank': rank,
                            'team': player.team or '-',
                            'week': week,
                            'opp': opponent_display,
                            'pts': f"{custom_pts:.1f}",
                            'snaps': snaps,
                            'pts_per_snap': f"{pts_per_snap:.3f}" if snaps > 0 else '-',
                            'comp': int(stats.get('pass_cmp', 0)) if player.position == 'QB' else '-',
                            'pass_yd': int(stats.get('pass_yd', 0)) if player.position == 'QB' else '-',
                            'pass_td': int(stats.get('pass_td', 0)) if player.position == 'QB' else '-',
                            'rush_yd': int(stats.get('rush_yd', 0)),
                            'rush_td': max(0, int(stats.get('rush_td', 0))),
                            'tgt': int(stats.get('rec_tgt', 0)) if player.position != 'QB' else '-',
                            'rec': int(stats.get('rec', 0)) if player.position != 'QB' else '-',
                            'rec_yd': int(stats.get('rec_yd', 0)) if player.position != 'QB' else '-',
                            'rec_td': int(stats.get('rec_td', 0)) if player.position != 'QB' else '-',
                            '_pts_float': custom_pts,  # For sorting
                            '_week_int': week,  # For sorting
                            '_pts_per_snap_float': pts_per_snap,  # For sorting
                            '_rank_int': int(rank[2:]) if rank != '-' else 999  # For sorting
                        }
                        rows.append(row)
        
        return rows
    
    def build_summarized_data(self, search_text, selected_week):
        """Build data for summarized view (season totals)"""
        rows = []
        player_totals = {}
        position_season_totals = {}  # {position: [(player_id, total_pts)]} for ranking
        
        # Aggregate data by player
        for week, week_data in self.weekly_stats.items():
            # Skip if week filter is active
            if selected_week != "ALL" and str(week) != selected_week:
                continue
            
            for player_id, stats_data in week_data.items():
                if player_id not in self.player_lookup:
                    continue
                    
                player = self.player_lookup[player_id]
                
                # Position filter
                if self.selected_position == "FLEX":
                    if player.position not in ["RB", "WR", "TE"]:
                        continue
                elif self.selected_position == "IDP":
                    if player.position not in ["DB", "LB"]:
                        continue
                elif self.selected_position == "OFF":
                    if player.position not in ["QB", "RB", "WR", "TE"]:
                        continue
                elif self.selected_position != "ALL" and player.position != self.selected_position:
                    continue
                
                # Search filter
                if search_text and search_text not in player.name.lower():
                    continue
                
                # Show Available filter (only undrafted players)
                if self.show_available_var.get() and self.player_pool_service:
                    if not self.player_pool_service.is_player_available(player):
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
                        'tgt': 0,
                        'rec': 0,
                        'rec_yd': 0,
                        'rec_td': 0,
                        'game_points': []  # Track individual game points for median/avg
                    }
                
                # Handle both single stat object and list of stats
                stats_list = stats_data if isinstance(stats_data, list) else [stats_data]
                
                # Aggregate stats
                for stat in stats_list:
                    stats = stat.get('stats', {})
                    totals = player_totals[player_id]
                    
                    # Only count as a game if player actually played (had snaps)
                    # Use defensive snaps for LB/DB, offensive snaps for others
                    if player.position in ['LB', 'DB']:
                        game_snaps = int(stats.get('def_snp', 0))
                    else:
                        game_snaps = int(stats.get('off_snp', 0))
                        
                    if game_snaps == 0:
                        continue
                    
                    totals['games'] += 1
                    # Calculate custom points for this game
                    custom_pts = self.calculate_custom_points(stats, player.position)
                    totals['pts'] += custom_pts
                    
                    # Track game points if player had meaningful participation
                    # (20+ snaps OR 20+ points)
                    if game_snaps >= 20 or custom_pts >= 20:
                        totals['game_points'].append(custom_pts)
                    
                    totals['snaps'] += game_snaps
                    if player.position == 'QB':
                        totals['comp'] += int(stats.get('pass_cmp', 0))
                        totals['pass_yd'] += int(stats.get('pass_yd', 0))
                        totals['pass_td'] += int(stats.get('pass_td', 0))
                    totals['rush_yd'] += int(stats.get('rush_yd', 0))
                    totals['rush_td'] += int(stats.get('rush_td', 0))
                    if player.position != 'QB':
                        totals['tgt'] += int(stats.get('rec_tgt', 0))
                        totals['rec'] += int(stats.get('rec', 0))
                        totals['rec_yd'] += int(stats.get('rec_yd', 0))
                        totals['rec_td'] += int(stats.get('rec_td', 0))
        
        # Collect season totals by position for ranking
        for player_id, totals in player_totals.items():
            position = totals['pos']
            if position not in position_season_totals:
                position_season_totals[position] = []
            position_season_totals[position].append((player_id, totals['pts']))
        
        # Sort each position by total points descending
        for position in position_season_totals:
            position_season_totals[position].sort(key=lambda x: x[1], reverse=True)
        
        # Convert to rows
        for player_id, totals in player_totals.items():
            # Apply minimum games filter
            if totals['games'] < self.min_games_var.get():
                continue
                
            # Calculate median and average from games with meaningful participation
            if totals['game_points']:
                median_pts = statistics.median(totals['game_points'])
                avg_pts = statistics.mean(totals['game_points'])
            else:
                median_pts = 0
                avg_pts = 0
            
            # Calculate average pts per snap
            avg_pts_per_snap = totals['pts'] / totals['snaps'] if totals['snaps'] > 0 else 0
            
            # Find season rank
            rank = '-'
            position = totals['pos']
            if position in position_season_totals:
                for idx, (pid, pts) in enumerate(position_season_totals[position]):
                    if pid == player_id:
                        rank = f"{position}{idx + 1}"
                        break
            
            row = {
                'player': totals['player'],
                'pos': totals['pos'],
                'rank': rank,
                'team': totals['team'],
                'week': f"{totals['games']}g",  # Show games played
                'opp': '2024',  # Show year instead of opponent
                'pts': f"{totals['pts']:.1f}",
                'median': f"{median_pts:.1f}" if median_pts > 0 else '-',
                'avg': f"{avg_pts:.1f}" if avg_pts > 0 else '-',
                'snaps': totals['snaps'] if totals['snaps'] > 0 else '-',
                'pts_per_snap': f"{avg_pts_per_snap:.3f}" if totals['snaps'] > 0 else '-',
                'comp': totals['comp'] if totals['comp'] > 0 else '-',
                'pass_yd': totals['pass_yd'] if totals['pass_yd'] > 0 else '-',
                'pass_td': totals['pass_td'] if totals['pass_td'] > 0 else '-',
                'rush_yd': totals['rush_yd'] if totals['rush_yd'] > 0 else '-',
                'rush_td': totals['rush_td'] if totals['rush_td'] > 0 else '-',
                'tgt': totals['tgt'] if totals['tgt'] > 0 else '-',
                'rec': totals['rec'] if totals['rec'] > 0 else '-',
                'rec_yd': totals['rec_yd'] if totals['rec_yd'] > 0 else '-',
                'rec_td': totals['rec_td'] if totals['rec_td'] > 0 else '-',
                '_pts_float': totals['pts'],  # For sorting
                '_week_int': totals['games'],  # For sorting
                '_median_float': median_pts,  # For sorting
                '_avg_float': avg_pts,  # For sorting
                '_pts_per_snap_float': avg_pts_per_snap,  # For sorting
                '_rank_int': int(rank[2:]) if rank != '-' else 999  # For sorting
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
            elif self.sort_column == 'median':
                return row.get('_median_float', 0)
            elif self.sort_column == 'avg':
                return row.get('_avg_float', 0)
            elif self.sort_column == 'pts_per_snap':
                return row.get('_pts_per_snap_float', 0)
            elif self.sort_column == 'rank':
                # Sort by rank number first, then position
                rank = row.get('rank', '-')
                if rank == '-':
                    return (999, 'ZZZ')
                # Extract position (e.g., 'QB') and number (e.g., '1') from 'QB1'
                pos = ''.join(c for c in rank if c.isalpha())
                num = ''.join(c for c in rank if c.isdigit())
                return (int(num) if num else 999, pos)
            elif self.sort_column in ['snaps', 'comp', 'pass_yd', 'pass_td', 'rush_yd', 'rush_td', 'tgt', 'rec', 'rec_yd', 'rec_td']:
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
            # Rank column should sort ascending first
            if column == 'rank':
                self.sort_ascending = True
            else:
                self.sort_ascending = False
        
        # Update all column headers to show sort arrows
        self.update_sort_arrows()
        self.apply_filters()
    
    def update_sort_arrows(self):
        """Update column headers to show sort direction arrows"""
        # Define column header text
        headers = {
            'player': 'Player',
            'pos': 'Pos',
            'rank': 'Rank',
            'team': 'Team',
            'week': 'Wk',
            'opp': 'Opp',
            'pts': 'Pts',
            'median': 'Med',
            'avg': 'Avg',
            'snaps': 'Snaps',
            'pts_per_snap': 'Pts/Snap',
            'comp': 'Comp',
            'pass_yd': 'Pass Yds',
            'pass_td': 'Pass TD',
            'rush_yd': 'Rush Yds',
            'rush_td': 'Rush TD',
            'tgt': 'Tgt',
            'rec': 'Rec',
            'rec_yd': 'Rec Yds',
            'rec_td': 'Rec TD'
        }
        
        # Update each column header
        for col, text in headers.items():
            if col == self.sort_column:
                # Add arrow to sorted column
                arrow = ' ↑' if self.sort_ascending else ' ↓'
                self.tree.heading(col, text=text + arrow)
            else:
                # Remove arrow from other columns
                self.tree.heading(col, text=text)
        
    def filter_by_position(self, position):
        """Filter by position"""
        self.selected_position = position
        
        # Update button appearances
        for pos, btn in self.position_buttons.items():
            if pos == position:
                if pos == "ALL":
                    btn.config(bg=DARK_THEME['button_active'])
                elif pos in ["OFF", "FLEX", "IDP"]:
                    btn.config(bg=DARK_THEME['button_active'])
                else:
                    btn.config(bg=get_position_color(pos))
            else:
                btn.config(bg=DARK_THEME['button_bg'])
        
        # Update column visibility
        self.update_column_visibility()
        self.apply_filters()
    
    def update_vegas_columns(self):
        """Update Vegas column visibility based on checkboxes"""
        # Update column visibility
        self.update_column_visibility()
        # Adjust table width based on visible columns
        self.adjust_table_width()
        # Refresh data to show Vegas values
        if self.view_mode == "summarized":
            self.apply_filters()
    
    def adjust_table_width(self):
        """Adjust the paned window sash position based on visible Vegas columns"""
        # Store original position on first call
        if self._original_sash_pos is None:
            try:
                # Wait a bit for the UI to settle, then get the default position
                self.after(100, self._store_and_adjust_width)
                return
            except:
                pass
        
        # Count Vegas columns
        vegas_columns_count = 0
        if self.view_mode == "summarized":
            if self.show_vegas_yards_var.get():
                vegas_columns_count += 1
            if self.show_vegas_pass_var.get():
                vegas_columns_count += 1
            if self.show_vegas_rush_var.get():
                vegas_columns_count += 1
            if self.show_vegas_rec_var.get():
                vegas_columns_count += 1
        
        # Calculate new width
        if self._original_sash_pos and self._original_sash_pos > 0:
            additional_width = vegas_columns_count * 80
            new_table_width = self._original_sash_pos + additional_width
            self._update_sash_position(new_table_width)
    
    def _store_and_adjust_width(self):
        """Store original width and then adjust"""
        try:
            current_pos = self.paned_window.sash_coord(0)[0]
            if current_pos > 100:  # Valid position
                self._original_sash_pos = current_pos
                self.adjust_table_width()  # Now adjust with stored position
        except:
            self._original_sash_pos = 850  # Fallback default
    
    def _update_sash_position(self, table_width):
        """Internal method to update sash position"""
        try:
            # Get the current window width
            window_width = self.paned_window.winfo_width()
            if window_width > 100:  # Make sure window is rendered
                # Set the sash position to give the table the desired width
                # Leave at least 400 pixels for the graph
                max_table_width = window_width - 400
                actual_table_width = min(table_width, max_table_width)
                self.paned_window.sash_place(0, actual_table_width, 0)
        except:
            pass  # Ignore errors if window not ready
    
    def set_view_mode(self, mode):
        """Set the view mode (detailed or summarized)"""
        self.view_mode = mode
        
        # Update button appearances
        if mode == "detailed":
            self.detailed_btn.config(bg=DARK_THEME['button_active'])
            self.summarized_btn.config(bg=DARK_THEME['button_bg'])
            # Hide games filter and Vegas checkboxes
            self.games_filter_frame.pack_forget()
            self.vegas_frame.pack_forget()
        else:
            self.detailed_btn.config(bg=DARK_THEME['button_bg'])
            self.summarized_btn.config(bg=DARK_THEME['button_active'])
            # Show games filter
            self.games_filter_frame.pack(side='left', padx=(20, 0))
            # Show Vegas checkboxes in header
            self.vegas_frame.pack(side='left')
        
        # Update column visibility for new mode
        self.update_column_visibility()
        # Only adjust table width if we have Vegas columns showing
        if mode == "summarized" and any([self.show_vegas_yards_var.get(), 
                                         self.show_vegas_pass_var.get(),
                                         self.show_vegas_rush_var.get(),
                                         self.show_vegas_rec_var.get()]):
            self.adjust_table_width()
        self.apply_filters()
    
    def update_column_visibility(self):
        """Show/hide columns based on selected position"""
        # First, set base column widths that should always be consistent
        self.tree.column('player', width=150, stretch=False)
        self.tree.column('pos', width=40, stretch=False)
        self.tree.column('rank', width=55, stretch=False)
        self.tree.column('team', width=45, stretch=False)
        self.tree.column('week', width=40, stretch=False)
        self.tree.column('opp', width=65, stretch=False)
        self.tree.column('pts', width=55, stretch=False)
        self.tree.column('snaps', width=55, stretch=False)
        self.tree.column('pts_per_snap', width=65, stretch=False)
        
        # Show/hide median and avg columns based on view mode
        if self.view_mode == "summarized":
            self.tree.column('median', width=55, stretch=False)
            self.tree.column('avg', width=55, stretch=False)
            # Show/hide Vegas columns based on checkboxes
            self.tree.column('vegas_yards', width=80 if self.show_vegas_yards_var.get() else 0, stretch=False)
            self.tree.column('vegas_pass', width=80 if self.show_vegas_pass_var.get() else 0, stretch=False)
            self.tree.column('vegas_rush', width=80 if self.show_vegas_rush_var.get() else 0, stretch=False)
            self.tree.column('vegas_rec', width=80 if self.show_vegas_rec_var.get() else 0, stretch=False)
        else:
            self.tree.column('median', width=0, stretch=False)
            self.tree.column('avg', width=0, stretch=False)
            # Hide Vegas columns in detailed view
            self.tree.column('vegas_yards', width=0, stretch=False)
            self.tree.column('vegas_pass', width=0, stretch=False)
            self.tree.column('vegas_rush', width=0, stretch=False)
            self.tree.column('vegas_rec', width=0, stretch=False)
        
        # Define which columns are relevant for each position
        qb_columns = ['comp', 'pass_yd', 'pass_td', 'rush_yd', 'rush_td']
        skill_columns = ['rush_yd', 'rush_td', 'rec', 'rec_yd', 'rec_td']
        
        if self.selected_position == "QB":
            # Show QB columns, hide receiving columns
            self.tree.column('comp', width=55, stretch=False)
            self.tree.column('pass_yd', width=70, stretch=False)
            self.tree.column('pass_td', width=65, stretch=False)
            self.tree.column('rush_yd', width=70, stretch=False)
            self.tree.column('rush_td', width=65, stretch=False)
            # Hide receiving columns
            self.tree.column('tgt', width=0, stretch=False)
            self.tree.column('rec', width=0, stretch=False)
            self.tree.column('rec_yd', width=0, stretch=False)
            self.tree.column('rec_td', width=0, stretch=False)
        elif self.selected_position in ["RB", "WR", "TE", "FLEX"]:
            # Hide passing columns
            self.tree.column('comp', width=0, stretch=False)
            self.tree.column('pass_yd', width=0, stretch=False)
            self.tree.column('pass_td', width=0, stretch=False)
            # Show skill position columns
            self.tree.column('rush_yd', width=70, stretch=False)
            self.tree.column('rush_td', width=65, stretch=False)
            self.tree.column('tgt', width=40, stretch=False)
            self.tree.column('rec', width=45, stretch=False)
            self.tree.column('rec_yd', width=65, stretch=False)
            self.tree.column('rec_td', width=60, stretch=False)
        elif self.selected_position == "OFF":
            # Show all offensive columns
            self.tree.column('comp', width=55, stretch=False)
            self.tree.column('pass_yd', width=70, stretch=False)
            self.tree.column('pass_td', width=65, stretch=False)
            self.tree.column('rush_yd', width=70, stretch=False)
            self.tree.column('rush_td', width=65, stretch=False)
            self.tree.column('tgt', width=40, stretch=False)
            self.tree.column('rec', width=45, stretch=False)
            self.tree.column('rec_yd', width=65, stretch=False)
            self.tree.column('rec_td', width=60, stretch=False)
        elif self.selected_position in ["DB", "LB", "IDP"]:
            # For defensive positions, we would need to show defensive stats
            # For now, hide all offensive columns
            self.tree.column('comp', width=0, stretch=False)
            self.tree.column('pass_yd', width=0, stretch=False)
            self.tree.column('pass_td', width=0, stretch=False)
            self.tree.column('rush_yd', width=0, stretch=False)
            self.tree.column('rush_td', width=0, stretch=False)
            self.tree.column('tgt', width=0, stretch=False)
            self.tree.column('rec', width=0, stretch=False)
            self.tree.column('rec_yd', width=0, stretch=False)
            self.tree.column('rec_td', width=0, stretch=False)
        else:  # ALL
            # Show all columns with appropriate widths
            self.tree.column('comp', width=55, stretch=False)
            self.tree.column('pass_yd', width=70, stretch=False)
            self.tree.column('pass_td', width=65, stretch=False)
            self.tree.column('rush_yd', width=70, stretch=False)
            self.tree.column('rush_td', width=65, stretch=False)
            self.tree.column('tgt', width=40, stretch=False)
            self.tree.column('rec', width=45, stretch=False)
            self.tree.column('rec_yd', width=65, stretch=False)
            self.tree.column('rec_td', width=60, stretch=False)
    
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
        self.selected_position = "OFF"
        self.week_var.set("ALL")
        self.location_var.set("ALL")
        self.venue_var.set("ALL")
        self.show_available_var.set(False)
        
        # Update button appearances
        for pos, btn in self.position_buttons.items():
            if pos == "OFF":
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
        
        # Skip if it's a totals row
        if 'TOTALS' in str(player_name):
            return
        
        # Find the player object
        player = None
        for p in self.all_players:
            if format_name(p.name) == player_name:
                player = p
                break
        
        # Create context menu
        menu = tk.Menu(self, tearoff=0,
                      bg=DARK_THEME['bg_secondary'],
                      fg=DARK_THEME['text_primary'],
                      activebackground=DARK_THEME['button_active'],
                      activeforeground='white')
        
        # Add draft option if player is available and draft callback exists
        if player and self.on_draft and self.player_pool_service:
            if self.player_pool_service.is_player_available(player):
                menu.add_command(label=f"Draft {player_name}",
                                command=lambda: self._draft_player(player),
                                font=(DARK_THEME['font_family'], 10, 'bold'))
                menu.add_separator()
        
        menu.add_command(label=f"Filter: {player_name}",
                        command=lambda: self.filter_by_player(player_name))
        menu.add_separator()
        menu.add_command(label="Clear Filters",
                        command=self.clear_filters)
        
        # Show menu
        menu.post(event.x_root, event.y_root)
    
    def _draft_player(self, player):
        """Handle drafting a player from the context menu"""
        if self.on_draft:
            # Call the draft callback with the player
            self.on_draft(player)
    
    def filter_by_player(self, player_name):
        """Filter to show only a specific player"""
        self.save_filter_state()
        
        # Set search to player name
        self.search_var.set(player_name)
        
        # Apply the filter
        self.apply_filters()
    
    def should_show_totals(self, rows):
        """Check if we should show totals row (single player in detailed view)"""
        if self.view_mode == "summarized":
            return False  # Don't show totals in summarized view
        
        if not rows:
            return False
            
        # Check if all rows are for the same player
        player_names = set(row['player'] for row in rows)
        return len(player_names) == 1 and len(rows) > 1
    
    def add_totals_row(self, rows):
        """Add a totals row for single player view"""
        if not rows:
            return
            
        # Initialize totals
        totals = {
            'pts': 0.0,
            'snaps': 0,
            'comp': 0,
            'pass_yd': 0,
            'pass_td': 0,
            'rush_yd': 0,
            'rush_td': 0,
            'tgt': 0,
            'rec': 0,
            'rec_yd': 0,
            'rec_td': 0,
            'games': 0
        }
        
        # Sum up the stats
        for row in rows:
            totals['games'] += 1
            
            # Points (handle float)
            try:
                totals['pts'] += float(row['pts'])
            except:
                pass
                
            # Integer stats
            for stat in ['snaps', 'comp', 'pass_yd', 'pass_td', 'rush_yd', 'rush_td', 'tgt', 'rec', 'rec_yd', 'rec_td']:
                val = row.get(stat, '-')
                if isinstance(val, (int, float)):
                    totals[stat] += int(val)
                elif val != '-':
                    try:
                        totals[stat] += int(val)
                    except:
                        pass
        
        # Calculate averages
        avg_pts = totals['pts'] / totals['games'] if totals['games'] > 0 else 0
        avg_snaps = totals['snaps'] / totals['games'] if totals['games'] > 0 else 0
        avg_pts_per_snap = totals['pts'] / totals['snaps'] if totals['snaps'] > 0 else 0
        
        # Create totals row
        player_name = rows[0]['player']
        position = rows[0]['pos']
        
        # Format values
        def format_stat(val, is_zero_allowed=True):
            if val == 0 and not is_zero_allowed:
                return '-'
            return str(int(val)) if val > 0 or is_zero_allowed else '-'
        
        values = (
            f"TOTALS ({totals['games']} games)",  # Player
            position,  # Pos
            '-',  # Rank
            '-',  # Team
            '-',  # Week
            '-',  # Opp
            f"{totals['pts']:.1f}",  # Pts
            '-',  # Median
            f"{avg_pts:.1f}",  # Avg
            format_stat(totals['snaps']),  # Snaps
            f"{avg_pts_per_snap:.3f}" if totals['snaps'] > 0 else '-',  # Pts/Snap
            format_stat(totals['comp']) if position == 'QB' else '-',  # Comp
            format_stat(totals['pass_yd']) if position == 'QB' else '-',  # Pass Yd
            format_stat(totals['pass_td']) if position == 'QB' else '-',  # Pass TD
            format_stat(totals['rush_yd']),  # Rush Yd
            format_stat(totals['rush_td']),  # Rush TD
            format_stat(totals['tgt']) if position != 'QB' else '-',  # Tgt
            format_stat(totals['rec']) if position != 'QB' else '-',  # Rec
            format_stat(totals['rec_yd']) if position != 'QB' else '-',  # Rec Yd
            format_stat(totals['rec_td']) if position != 'QB' else '-',  # Rec TD
            '-',  # Vegas Yards
            '-',  # Vegas Pass
            '-',  # Vegas Rush
            '-'   # Vegas Rec
        )
        
        # Add separator row
        self.tree.insert('', 'end', values=('', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''), tags=('separator',))
        
        # Add totals row
        self.tree.insert('', 'end', values=values, tags=('totals',))
        
        # Style separator
        self.tree.tag_configure('separator', background=DARK_THEME['bg_primary'])
    
    def setup_graph(self, container):
        """Setup the matplotlib graph"""
        # Graph title
        self.graph_title_label = tk.Label(
            container,
            text="POINTS BY WEEK",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        self.graph_title_label.pack(pady=(10, 5))
        
        # Metric dropdown frame
        metric_frame = StyledFrame(container, bg_type='secondary')
        metric_frame.pack(pady=(0, 5))
        
        # Metric label
        metric_label = tk.Label(
            metric_frame,
            text="Metric:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10, 'bold')
        )
        metric_label.pack(side='left', padx=(0, 5))
        
        # Metric dropdown
        self.metric_var = tk.StringVar(value="points")
        self.metric_dropdown = ttk.Combobox(
            metric_frame,
            textvariable=self.metric_var,
            values=[
                "points", "snaps", "pass_yd", "rush_yd", "rec_yd",
                "pass_td", "rush_td", "rec_td", "rec", "pass_cmp",
                "rush_att", "rec_tgt"
            ],
            state='readonly',
            width=12,
            font=(DARK_THEME['font_family'], 9)
        )
        self.metric_dropdown.pack(side='left')
        self.metric_dropdown.bind('<<ComboboxSelected>>', self.on_metric_changed)
        
        # Instructions
        info_label = tk.Label(
            container,
            text="Click player to graph • Ctrl+Click to add/remove • Shift+Click to select range",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        )
        info_label.pack(pady=(0, 5))
        
        # Week range controls (moved above graph)
        range_frame = StyledFrame(container, bg_type='secondary')
        range_frame.pack(fill='x', padx=10, pady=(5, 5))
        
        # Range label
        range_label = tk.Label(
            range_frame,
            text="WEEK RANGE:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10, 'bold')
        )
        range_label.pack(side='left', padx=(0, 10))
        
        # Preset buttons
        presets = [
            ("All", 1, 18),
            ("First Half", 1, 9),
            ("Last Half", 10, 18),
            ("Q1", 1, 4),
            ("Q2", 5, 9),
            ("Q3", 10, 13),
            ("Q4", 14, 18),
            ("Playoffs", 15, 18)
        ]
        
        for text, start, end in presets:
            btn = tk.Button(
                range_frame,
                text=text,
                bg=DARK_THEME['button_bg'] if not (self.week_range_start == start and self.week_range_end == end) else DARK_THEME['button_active'],
                fg='white',
                font=(DARK_THEME['font_family'], 8, 'bold'),
                bd=0,
                relief='flat',
                padx=8,
                pady=2,
                command=lambda s=start, e=end, t=text: self.set_week_range(s, e, t),
                cursor='hand2'
            )
            btn.pack(side='left', padx=2)
            setattr(self, f'range_btn_{text.replace(" ", "_").lower()}', btn)
        
        # Custom range controls
        custom_frame = StyledFrame(container, bg_type='secondary')
        custom_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        tk.Label(
            custom_frame,
            text="Custom:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        ).pack(side='left', padx=(0, 5))
        
        self.start_var = tk.StringVar(value="1")
        self.start_spinbox = tk.Spinbox(
            custom_frame,
            from_=1,
            to=18,
            textvariable=self.start_var,
            width=3,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 9),
            command=self.on_custom_range_changed
        )
        self.start_spinbox.pack(side='left')
        
        tk.Label(
            custom_frame,
            text="to",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        ).pack(side='left', padx=5)
        
        self.end_var = tk.StringVar(value="18")
        self.end_spinbox = tk.Spinbox(
            custom_frame,
            from_=1,
            to=18,
            textvariable=self.end_var,
            width=3,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 9),
            command=self.on_custom_range_changed
        )
        self.end_spinbox.pack(side='left')
        
        # Clear button
        clear_btn = tk.Button(
            custom_frame,
            text="CLEAR GRAPH",
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold'),
            bd=0,
            relief='flat',
            padx=12,
            pady=4,
            command=self.clear_graph,
            cursor='hand2'
        )
        clear_btn.pack(side='left', padx=(20, 0))
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(6, 4), dpi=100, facecolor=DARK_THEME['bg_secondary'])
        self.ax = self.figure.add_subplot(111)
        
        # Style the plot
        self.ax.set_facecolor(DARK_THEME['bg_tertiary'])
        self.ax.spines['bottom'].set_color(DARK_THEME['text_secondary'])
        self.ax.spines['top'].set_color(DARK_THEME['text_secondary'])
        self.ax.spines['left'].set_color(DARK_THEME['text_secondary'])
        self.ax.spines['right'].set_color(DARK_THEME['text_secondary'])
        self.ax.tick_params(colors=DARK_THEME['text_secondary'])
        self.ax.xaxis.label.set_color(DARK_THEME['text_secondary'])
        self.ax.yaxis.label.set_color(DARK_THEME['text_secondary'])
        
        # Create canvas
        self.graph_canvas = FigureCanvasTkAgg(self.figure, master=container)
        self.graph_canvas.draw()
        self.graph_canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Initialize empty plot
        self.update_graph()
    
    def on_left_click(self, event):
        """Handle left click on tree item"""
        # Identify the row
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        # Get player info from the row
        values = self.tree.item(item, 'values')
        if not values or values[0] == '' or 'TOTALS' in str(values[0]):
            return
            
        player_name = values[0]
        
        # Check if Shift is pressed
        if event.state & 0x1:  # Shift key
            # Select range of players
            if self.last_clicked_item:
                self.select_player_range(self.last_clicked_item, item)
            else:
                # No previous selection, just add this one
                self.add_player_to_graph(player_name, add_to_selection=False)
        # Check if Ctrl is pressed
        elif event.state & 0x4:  # Ctrl key
            # Add to existing selection
            self.add_player_to_graph(player_name, add_to_selection=True)
        else:
            # Replace selection
            self.add_player_to_graph(player_name, add_to_selection=False)
        
        # Remember this item for next shift+click
        self.last_clicked_item = item
    
    def on_selection_change(self, event):
        """Handle selection changes in the tree"""
        # Only auto-manage graph if we have selections (selection-based mode)
        if not self.tree.selection():
            return
            
        # Get all unique player names from selected rows
        selected_players = set()
        for item in self.tree.selection():
            values = self.tree.item(item, 'values')
            if values and values[0] and values[0] != '' and 'TOTALS' not in str(values[0]):
                selected_players.add(values[0])
        
        # Check each graphed player to see if they should be removed
        players_to_remove = []
        for player_id, player_data in self.graph_players.items():
            player_name = player_data['name']
            # If player is not in selected players, mark for removal
            if player_name not in selected_players:
                players_to_remove.append(player_id)
        
        # Remove players that are no longer selected
        if players_to_remove:
            for player_id in players_to_remove:
                del self.graph_players[player_id]
            self.update_graph()
    
    def add_player_to_graph(self, player_name, add_to_selection=False):
        """Add a player to the graph"""
        # Find player ID
        player_id = None
        for pid, player in self.player_lookup.items():
            if format_name(player.name) == player_name:
                player_id = pid
                break
                
        if not player_id:
            return
            
        # Clear existing if not adding to selection
        if not add_to_selection:
            self.graph_players.clear()
            
        # Check if already in graph - handle toggle behavior for Ctrl+clicking
        if player_id in self.graph_players:
            if add_to_selection:
                # Check if this player has any selected rows in the table
                has_selected_row = False
                for item in self.tree.selection():
                    values = self.tree.item(item, 'values')
                    if values and values[0] == player_name:
                        has_selected_row = True
                        break
                
                # If no rows are selected, remove from graph (toggle off)
                if not has_selected_row:
                    del self.graph_players[player_id]
                    self.update_graph()
                    return
                # If rows are selected, keep in graph but don't re-add
                else:
                    return
            else:
                # Non-Ctrl click on already graphed player - just return
                return
            
        # Collect player's weekly data for ALL weeks (1-18)
        weeks = []
        points = []
        snaps = []  # Track snaps for each week
        metric_data = []  # Track selected metric data
        
        for week in range(1, 19):  # All weeks 1-18
            week_points = 0  # Default to 0
            week_snaps = 0   # Default to 0
            week_metric = 0  # Default to 0
            
            if week in self.weekly_stats and player_id in self.weekly_stats[week]:
                stats_data = self.weekly_stats[week][player_id]
                # Handle both single stat object and list of stats
                stats_list = stats_data if isinstance(stats_data, list) else [stats_data]
                
                for stat in stats_list:
                    stats = stat.get('stats', {})
                    # Check defensive snaps for DB/LB, offensive snaps for others
                    player = self.player_lookup[player_id]
                    if player.position in ['DB', 'LB']:
                        week_snaps = int(stats.get('def_snp', 0))
                    else:
                        week_snaps = int(stats.get('off_snp', 0))
                    # Only count if player actually played (had snaps)
                    if week_snaps > 0:
                        # Calculate custom points
                        week_points = self.calculate_custom_points(stats, player.position)
                        # Get metric data
                        if self.graph_metric == "snaps":
                            week_metric = week_snaps
                        elif self.graph_metric == "points":
                            week_metric = week_points
                        else:
                            # Get raw stat value
                            week_metric = float(stats.get(self.graph_metric, 0))
                        break  # Only one game per week
            
            weeks.append(week)
            points.append(week_points)
            snaps.append(week_snaps)
            metric_data.append(week_metric)
        
        # Calculate standard deviation for games with 5+ snaps
        points_for_std = [points[i] for i in range(len(points)) if snaps[i] >= 5]
        std_dev = statistics.stdev(points_for_std) if len(points_for_std) > 1 else 0
        
        # Always add all 18 weeks
        if weeks and points:
            # Check how many players from this team are already in the graph
            player = self.player_lookup[player_id]
            team_count = sum(1 for pid, pdata in self.graph_players.items() if pdata['team'] == player.team)
            
            # Alternate between primary and secondary colors
            # 0 players -> primary, 1 player -> secondary, 2 players -> primary, etc.
            use_secondary = (team_count % 2) == 1
            color = get_team_color(player.team, secondary=use_secondary)
            
            # Store data
            self.graph_players[player_id] = {
                'name': player_name,
                'weeks': weeks,
                'points': points,
                'snaps': snaps,
                'metric_data': metric_data,
                'std_dev': std_dev,
                'color': color,
                'position': player.position,
                'team': player.team
            }
            
            # Update graph
            self.update_graph()
    
    def update_graph(self):
        """Update the matplotlib graph"""
        self.ax.clear()
        
        if not self.graph_players:
            # Empty graph
            self.ax.text(0.5, 0.5, 'Click on players to graph their stats',
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=self.ax.transAxes,
                        color=DARK_THEME['text_secondary'],
                        fontsize=12)
            self.ax.set_xlim(self.week_range_start - 0.5, self.week_range_end + 0.5)
            self.ax.set_ylim(0, 50)
        else:
            # Track teams and assign different markers to players from same team
            team_player_count = {}
            markers = ['o', 's', '^', 'D', 'v', '*', 'p', 'X', 'h', '+']
            player_markers = {}
            
            # First pass: count players per team and assign markers
            for player_id, data in self.graph_players.items():
                team = data['team']
                if team not in team_player_count:
                    team_player_count[team] = 0
                marker_index = team_player_count[team] % len(markers)
                player_markers[player_id] = markers[marker_index]
                team_player_count[team] += 1
            
            # Plot each player
            for player_id, data in self.graph_players.items():
                # Create label with team and standard deviation
                label = f"{data['name']} ({data['team']}) σ={data['std_dev']:.1f}"
                marker = player_markers[player_id]
                
                # Plot using the selected metric
                plot_data = data['metric_data'] if 'metric_data' in data else data['points']
                self.ax.plot(data['weeks'], plot_data, 
                           marker=marker, linewidth=2, markersize=8,
                           color=data['color'], 
                           label=label)
            
            # Calculate correlation if exactly 2 players
            legend_title = None
            if len(self.graph_players) == 2:
                player_ids = list(self.graph_players.keys())
                p1_data = self.graph_players[player_ids[0]]
                p2_data = self.graph_players[player_ids[1]]
                
                # Get data and snaps for both players
                p1_metric = p1_data.get('metric_data', p1_data['points'])
                p2_metric = p2_data.get('metric_data', p2_data['points'])
                p1_snaps = p1_data.get('snaps', [])
                p2_snaps = p2_data.get('snaps', [])
                
                # Find weeks where both players had 15+ snaps
                valid_weeks = []
                p1_valid = []
                p2_valid = []
                
                for i in range(len(p1_metric)):
                    if i < len(p1_snaps) and i < len(p2_snaps):
                        if p1_snaps[i] >= 15 and p2_snaps[i] >= 15:
                            valid_weeks.append(i + 1)  # Week number
                            p1_valid.append(p1_metric[i])
                            p2_valid.append(p2_metric[i])
                
                # Calculate correlation if we have at least 3 valid weeks
                if len(p1_valid) >= 3:
                    try:
                        correlation = statistics.correlation(p1_valid, p2_valid)
                        legend_title = f'Correlation: {correlation:.3f} ({len(valid_weeks)} weeks)'
                    except:
                        # If correlation fails (e.g., constant values), no title
                        pass
            
            # Add legend with proper marker sizes
            legend = self.ax.legend(loc='upper left', frameon=True, 
                                  facecolor=DARK_THEME['bg_secondary'],
                                  edgecolor=DARK_THEME['text_secondary'],
                                  markerscale=1.2,  # Make markers in legend slightly larger
                                  title=legend_title)
            
            # Set legend title color if we have one
            if legend_title:
                legend.get_title().set_color(DARK_THEME['text_primary'])
            
            for text in legend.get_texts():
                text.set_color(DARK_THEME['text_primary'])
            
            # Grid
            self.ax.grid(True, alpha=0.3, color=DARK_THEME['text_secondary'])
            
            # Set x-axis to show selected week range
            self.ax.set_xlim(self.week_range_start - 0.5, self.week_range_end + 0.5)
            self.ax.set_xticks(range(self.week_range_start, self.week_range_end + 1))
            
            # Set y-axis to start at 0
            self.ax.set_ylim(bottom=0)
        
        # Labels
        self.ax.set_xlabel('Week', color=DARK_THEME['text_primary'])
        # Update y-axis label based on metric
        metric_labels = {
            'points': 'Points',
            'snaps': 'Snaps',
            'pass_yd': 'Passing Yards',
            'rush_yd': 'Rushing Yards',
            'rec_yd': 'Receiving Yards',
            'pass_td': 'Passing TDs',
            'rush_td': 'Rushing TDs',
            'rec_td': 'Receiving TDs',
            'rec': 'Receptions',
            'pass_cmp': 'Completions',
            'rush_att': 'Rush Attempts',
            'rec_tgt': 'Targets'
        }
        ylabel = metric_labels.get(self.graph_metric, self.graph_metric.replace('_', ' ').title())
        self.ax.set_ylabel(ylabel, color=DARK_THEME['text_primary'])
        
        # Redraw
        self.figure.tight_layout()
        self.graph_canvas.draw()
    
    def clear_graph(self):
        """Clear all players from the graph"""
        self.graph_players.clear()
        self.update_graph()
    
    def select_player_range(self, start_item, end_item):
        """Select all players between start and end items"""
        # Get all items in the tree
        all_items = self.tree.get_children()
        
        # Find indices of start and end
        try:
            start_idx = all_items.index(start_item)
            end_idx = all_items.index(end_item)
        except ValueError:
            return
            
        # Make sure start is before end
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
            
        # Clear existing selection and add all players in range
        self.graph_players.clear()
        
        # Add each player in the range
        for idx in range(start_idx, end_idx + 1):
            item = all_items[idx]
            values = self.tree.item(item, 'values')
            
            # Skip empty rows and totals
            if values and values[0] and values[0] != '' and 'TOTALS' not in str(values[0]):
                player_name = values[0]
                self.add_player_to_graph(player_name, add_to_selection=True)
    
    def set_week_range(self, start, end, button_text):
        """Set the week range for the graph"""
        self.week_range_start = start
        self.week_range_end = end
        
        # Update all range buttons
        for preset_text in ["all", "first_half", "last_half", "q1", "q2", "q3", "q4", "playoffs"]:
            btn = getattr(self, f'range_btn_{preset_text.replace(" ", "_").lower()}', None)
            if btn:
                btn.config(bg=DARK_THEME['button_bg'])
        
        # Highlight active button
        active_btn = getattr(self, f'range_btn_{button_text.replace(" ", "_").lower()}', None)
        if active_btn:
            active_btn.config(bg=DARK_THEME['button_active'])
        
        # Update spinboxes
        self.start_var.set(str(start))
        self.end_var.set(str(end))
        
        # Redraw graph
        self.update_graph()
    
    def on_metric_changed(self, event=None):
        """Handle metric dropdown change"""
        self.graph_metric = self.metric_var.get()
        
        # Update graph title
        metric_titles = {
            'points': 'POINTS BY WEEK',
            'snaps': 'SNAPS BY WEEK',
            'pass_yd': 'PASSING YARDS BY WEEK',
            'rush_yd': 'RUSHING YARDS BY WEEK',
            'rec_yd': 'RECEIVING YARDS BY WEEK',
            'pass_td': 'PASSING TDS BY WEEK',
            'rush_td': 'RUSHING TDS BY WEEK',
            'rec_td': 'RECEIVING TDS BY WEEK',
            'rec': 'RECEPTIONS BY WEEK',
            'pass_cmp': 'COMPLETIONS BY WEEK',
            'rush_att': 'RUSH ATTEMPTS BY WEEK',
            'rec_tgt': 'TARGETS BY WEEK'
        }
        title = metric_titles.get(self.graph_metric, self.graph_metric.replace('_', ' ').upper() + ' BY WEEK')
        self.graph_title_label.config(text=title)
        
        # Re-add all players with new metric
        players_to_readd = list(self.graph_players.keys())
        self.graph_players.clear()
        
        for player_id in players_to_readd:
            player = self.player_lookup.get(player_id)
            if player:
                self.add_player_to_graph(format_name(player.name), add_to_selection=True)
    
    def blend_colors(self, color1, color2, ratio=0.5):
        """Blend two colors together"""
        # Convert hex to RGB
        r1 = int(color1[1:3], 16)
        g1 = int(color1[3:5], 16)
        b1 = int(color1[5:7], 16)
        
        r2 = int(color2[1:3], 16)
        g2 = int(color2[3:5], 16)
        b2 = int(color2[5:7], 16)
        
        # Blend
        r = int(r1 * ratio + r2 * (1 - ratio))
        g = int(g1 * ratio + g2 * (1 - ratio))
        b = int(b1 * ratio + b2 * (1 - ratio))
        
        # Convert back to hex
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def on_custom_range_changed(self):
        """Handle custom range spinbox changes"""
        try:
            start = int(self.start_var.get())
            end = int(self.end_var.get())
            
            # Validate range
            if start < 1:
                start = 1
                self.start_var.set("1")
            if end > 18:
                end = 18
                self.end_var.set("18")
            if start > end:
                start = end
                self.start_var.set(str(end))
                
            self.week_range_start = start
            self.week_range_end = end
            
            # Update all preset buttons to inactive
            for preset_text in ["all", "first_half", "last_half", "q1", "q2", "q3", "q4", "playoffs"]:
                btn = getattr(self, f'range_btn_{preset_text}', None)
                if btn:
                    btn.config(bg=DARK_THEME['button_bg'])
            
            # Redraw graph
            self.update_graph()
        except ValueError:
            pass  # Ignore invalid input
    
