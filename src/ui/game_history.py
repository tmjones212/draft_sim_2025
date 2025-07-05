import tkinter as tk
from tkinter import ttk
import json
import os
from typing import Dict, List, Optional
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from ..utils.player_extensions import format_name


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
        
        self.setup_ui()
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
        
        # Search box
        search_label = tk.Label(
            filter_frame,
            text="Search:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        search_label.pack(side='left', padx=(0, 5))
        
        search_entry = tk.Entry(
            filter_frame,
            textvariable=self.search_var,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            width=20
        )
        search_entry.pack(side='left', padx=(0, 20))
        self.search_var.trace('w', lambda *args: self.apply_filters())
        
        # Position filter
        pos_label = tk.Label(
            filter_frame,
            text="Position:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        pos_label.pack(side='left', padx=(0, 5))
        
        positions = ["ALL", "QB", "RB", "WR", "TE"]
        self.position_buttons = {}
        
        for pos in positions:
            if pos == "ALL":
                btn_bg = DARK_THEME['button_active'] if pos == self.selected_position else DARK_THEME['button_bg']
            else:
                btn_bg = get_position_color(pos) if pos == self.selected_position else DARK_THEME['button_bg']
            
            btn = tk.Button(
                filter_frame,
                text=pos,
                bg=btn_bg,
                fg='white',
                font=(DARK_THEME['font_family'], 9, 'bold'),
                bd=0,
                relief='flat',
                padx=12,
                pady=4,
                command=lambda p=pos: self.filter_by_position(p),
                cursor='hand2'
            )
            btn.pack(side='left', padx=2)
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
        
        # Table container
        table_container = StyledFrame(container, bg_type='secondary')
        table_container.pack(fill='both', expand=True)
        
        # Create treeview for table
        columns = ('player', 'pos', 'team', 'week', 'opp', 'pts', 'pass_yd', 'pass_td', 
                  'rush_yd', 'rush_td', 'rec', 'rec_yd', 'rec_td')
        
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show='tree headings',
            height=20
        )
        
        # Configure columns
        self.tree.column('#0', width=0, stretch=False)  # Hide tree column
        self.tree.column('player', width=180, anchor='w')
        self.tree.column('pos', width=50, anchor='center')
        self.tree.column('team', width=50, anchor='center')
        self.tree.column('week', width=50, anchor='center')
        self.tree.column('opp', width=50, anchor='center')
        self.tree.column('pts', width=70, anchor='center')
        self.tree.column('pass_yd', width=80, anchor='center')
        self.tree.column('pass_td', width=70, anchor='center')
        self.tree.column('rush_yd', width=80, anchor='center')
        self.tree.column('rush_td', width=70, anchor='center')
        self.tree.column('rec', width=50, anchor='center')
        self.tree.column('rec_yd', width=70, anchor='center')
        self.tree.column('rec_td', width=60, anchor='center')
        
        # Configure headings
        self.tree.heading('player', text='Player', command=lambda: self.sort_by('player'))
        self.tree.heading('pos', text='Pos', command=lambda: self.sort_by('pos'))
        self.tree.heading('team', text='Team', command=lambda: self.sort_by('team'))
        self.tree.heading('week', text='Wk', command=lambda: self.sort_by('week'))
        self.tree.heading('opp', text='Opp', command=lambda: self.sort_by('opp'))
        self.tree.heading('pts', text='Pts', command=lambda: self.sort_by('pts'))
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
        
    def apply_filters(self):
        """Apply all filters and update display"""
        search_text = self.search_var.get().lower()
        selected_week = self.week_var.get()
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Build filtered data
        rows = []
        
        for week, week_data in self.weekly_stats.items():
            # Skip if week filter is active
            if selected_week != "ALL" and str(week) != selected_week:
                continue
                
            for player_id, stats_list in week_data.items():
                if player_id not in self.player_lookup:
                    continue
                    
                player = self.player_lookup[player_id]
                
                # Position filter
                if self.selected_position != "ALL" and player.position != self.selected_position:
                    continue
                
                # Search filter
                if search_text and search_text not in player.name.lower():
                    continue
                
                # Process each game for this player
                for stat in stats_list:
                    stats = stat.get('stats', {})
                    
                    row = {
                        'player': format_name(player.name),
                        'pos': player.position,
                        'team': player.team or '-',
                        'week': week,
                        'opp': stat.get('opponent', '-'),
                        'pts': f"{stats.get('pts_ppr', 0):.1f}",
                        'pass_yd': int(stats.get('pass_yd', 0)) if player.position == 'QB' else '-',
                        'pass_td': int(stats.get('pass_td', 0)) if player.position == 'QB' else '-',
                        'rush_yd': int(stats.get('rush_yd', 0)),
                        'rush_td': int(stats.get('rush_rec_td', 0) - stats.get('rec_td', 0)) if player.position != 'QB' else int(stats.get('rush_td', 0)),
                        'rec': int(stats.get('rec', 0)) if player.position != 'QB' else '-',
                        'rec_yd': int(stats.get('rec_yd', 0)) if player.position != 'QB' else '-',
                        'rec_td': int(stats.get('rec_td', 0)) if player.position != 'QB' else '-',
                        '_pts_float': stats.get('pts_ppr', 0),  # For sorting
                        '_week_int': week  # For sorting
                    }
                    rows.append(row)
        
        # Sort if needed
        if self.sort_column:
            self.sort_rows(rows)
        
        # Add to tree
        for row in rows:
            values = (row['player'], row['pos'], row['team'], row['week'], row['opp'],
                     row['pts'], row['pass_yd'], row['pass_td'], row['rush_yd'], 
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
        self.status_label.config(text=f"Showing {len(rows)} games")
        
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
            elif self.sort_column in ['pass_yd', 'pass_td', 'rush_yd', 'rush_td', 'rec', 'rec_yd', 'rec_td']:
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
            self.sort_ascending = True
            
        self.apply_filters()
        
    def filter_by_position(self, position):
        """Filter by position"""
        self.selected_position = position
        
        # Update button appearances
        for pos, btn in self.position_buttons.items():
            if pos == position:
                if pos == "ALL":
                    btn.config(bg=DARK_THEME['button_active'])
                else:
                    btn.config(bg=get_position_color(pos))
            else:
                btn.config(bg=DARK_THEME['button_bg'])
                
        self.apply_filters()