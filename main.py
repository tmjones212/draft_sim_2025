import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import random
import threading

# Add the current directory to Python path for cross-platform compatibility
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import config
from src.models import Team
from src.core import DraftEngine
from src.ui import DraftBoard, PlayerList, RosterView
from src.ui.theme import DARK_THEME
from src.ui.styled_widgets import StyledFrame, StyledButton
from src.utils import generate_mock_players


class MockDraftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mock Draft Simulator 2025")
        # Optimized window size - wider for draft board and taller for better visibility
        self.root.geometry("1920x1080")
        self.root.configure(bg=DARK_THEME['bg_primary'])
        
        # Set minimum window size
        self.root.minsize(1800, 900)
        
        # Center the window on screen
        self.center_window()
        
        # Initialize draft components
        self.teams = self._create_teams()
        self.draft_engine = DraftEngine(
            num_teams=config.num_teams,
            roster_spots=config.roster_spots,
            draft_type=config.draft_type,
            reversal_round=config.reversal_round
        )
        
        # Initialize players as empty lists - will be loaded in background
        self.all_players = []
        self.available_players = []
        self.players_loaded = False
        
        # Initialize services
        from src.services import PlayerImageService
        self.image_service = PlayerImageService()
        
        # User control state
        self.user_team_id = None  # Which team the user controls
        self.manual_mode = False  # Whether user controls all picks
        
        # Draft reversion state
        self.draft_state_before_reversion = None
        self.players_before_reversion = None
        
        # Performance optimization
        self._position_counts_cache = {}  # Cache position counts per team
        
        # Setup UI
        self.setup_ui()
        self.setup_keyboard_shortcuts()
        
        # Show loading message
        self.show_loading_message()
        
        # Start loading players in background thread
        self.load_players_async()
    
    def _create_teams(self):
        teams = {}
        for i in range(1, config.num_teams + 1):
            teams[i] = Team(
                team_id=i,
                name=f"Team {i}",
                roster_spots=config.roster_spots
            )
        return teams
    
    def setup_ui(self):
        # Main container
        main_frame = StyledFrame(self.root, bg_type='primary')
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Header section
        header_frame = StyledFrame(main_frame, bg_type='primary')
        header_frame.pack(fill='x', pady=(0, 15))
        
        # Title and status container
        status_container = StyledFrame(header_frame, bg_type='primary')
        status_container.pack(side='left', fill='x', expand=True)
        
        self.status_label = tk.Label(
            status_container,
            text="",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 18, 'bold')
        )
        self.status_label.pack(anchor='w')
        
        self.on_clock_label = tk.Label(
            status_container,
            text="",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 13)
        )
        self.on_clock_label.pack(anchor='w', pady=(3, 0))
        
        # Button container
        button_container = StyledFrame(header_frame, bg_type='primary')
        button_container.pack(side='right')
        
        # Manual mode toggle
        self.manual_mode_var = tk.BooleanVar(value=self.manual_mode)
        self.manual_mode_check = tk.Checkbutton(
            button_container,
            text="Manual Mode",
            variable=self.manual_mode_var,
            command=self.toggle_manual_mode,
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            selectcolor=DARK_THEME['bg_tertiary'],
            activebackground=DARK_THEME['bg_primary'],
            activeforeground=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            bd=0,
            highlightthickness=0
        )
        self.manual_mode_check.pack(side='left', padx=(0, 20))
        
        # Undo button
        self.undo_button = StyledButton(
            button_container,
            text="UNDO",
            command=self.undo_reversion,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=20,
            pady=10,
            state='disabled'
        )
        self.undo_button.pack(side='left', padx=(0, 10))
        
        # Restart button
        self.restart_button = StyledButton(
            button_container,
            text="RESTART DRAFT",
            command=self.restart_draft,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=20,
            pady=10
        )
        self.restart_button.pack(side='left', padx=(0, 10))
        
        # Draft button (disabled until team selected)
        self.draft_button = StyledButton(
            button_container,
            text="DRAFT PLAYER",
            command=self.draft_player,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=25,
            pady=10,
            state='disabled'
        )
        self.draft_button.pack(side='left')
        
        # Main content area with draggable divider
        content_frame = StyledFrame(main_frame, bg_type='primary')
        content_frame.pack(fill='both', expand=True)
        
        # Create vertical PanedWindow for draggable divider
        # Using tk.PanedWindow instead of ttk for better performance control
        paned_window = tk.PanedWindow(
            content_frame, 
            orient='vertical',
            bg=DARK_THEME['bg_primary'],
            sashwidth=8,
            sashrelief='flat',
            borderwidth=0,
            opaqueresize=False  # Show outline while dragging for smoother performance
        )
        paned_window.pack(fill='both', expand=True)
        
        # Top section - Draft board and Roster
        top_frame = StyledFrame(paned_window, bg_type='primary')
        
        # Use grid for draft board and roster side by side
        top_frame.grid_rowconfigure(0, weight=1)
        top_frame.grid_columnconfigure(0, weight=1)  # Draft board column - expand to fill
        top_frame.grid_columnconfigure(1, weight=0, minsize=100)  # Roster column - fixed width
        
        # Draft board
        draft_panel = StyledFrame(top_frame, bg_type='secondary')
        draft_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        total_rounds = sum(config.roster_spots.values())
        self.draft_board = DraftBoard(
            draft_panel, 
            self.teams, 
            total_rounds, 
            max_visible_rounds=9,
            on_team_select=self.on_team_selected,
            on_pick_click=self.on_pick_clicked,
            image_service=self.image_service
        )
        self.draft_board.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Roster panel (narrow)
        roster_panel = StyledFrame(top_frame, bg_type='secondary')
        roster_panel.grid(row=0, column=1, sticky='nsew')
        
        self.roster_view = RosterView(roster_panel, self.teams)
        self.roster_view.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Bottom section - Available players
        player_panel = StyledFrame(paned_window, bg_type='secondary')
        
        self.player_list = PlayerList(player_panel, on_draft=self.draft_player, image_service=self.image_service)
        self.player_list.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Connect watch list to player list (bidirectional)
        if hasattr(self.roster_view, 'get_watch_list'):
            watch_list = self.roster_view.get_watch_list()
            self.player_list.set_watch_list_ref(watch_list)
            watch_list.set_player_list_ref(self.player_list)
        
        # Add frames to PanedWindow
        paned_window.add(top_frame, stretch='always')
        paned_window.add(player_panel, stretch='always')
        
        # Set initial sash position (65% for top, 35% for bottom - more room for player list)
        paned_window.update_idletasks()  # Ensure geometry is calculated
        paned_window.sash_place(0, 0, int(paned_window.winfo_height() * 0.65))
    
    def update_display(self, full_update=True):
        # Update status
        pick_num, round_num, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
        
        if self.draft_engine.is_draft_complete():
            self.status_label.config(text="Draft Complete!")
            self.on_clock_label.config(text="All picks have been made")
            self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
        else:
            # Show appropriate status based on mode and team selection
            if self.manual_mode:
                self.status_label.config(text=f"Round {round_num} • Pick {pick_in_round}")
                self.on_clock_label.config(text=f"On the Clock: {self.teams[team_on_clock].name}")
            elif not self.user_team_id:
                self.status_label.config(text="Select a team to control")
                self.on_clock_label.config(text="Click on a team name in the draft board")
            else:
                self.status_label.config(text=f"Round {round_num} • Pick {pick_in_round}")
                self.on_clock_label.config(text=f"On the Clock: {self.teams[team_on_clock].name}")
            
            # Enable draft button based on mode
            if self.manual_mode:
                # In manual mode, always enable
                self.draft_button.config(state="normal", bg=DARK_THEME['button_active'])
            elif self.user_team_id and team_on_clock == self.user_team_id:
                # Normal mode - only when it's user's turn
                self.draft_button.config(state="normal", bg=DARK_THEME['button_active'])
            else:
                self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
        
        
        # Update components
        if full_update:
            self.player_list.update_players(self.available_players)
            # Update draft button states based on mode
            self.player_list.set_draft_enabled(self.manual_mode or self.user_team_id is not None)
        
        # Always update draft board with just the last pick
        self.draft_board.update_picks(
            self.draft_engine.get_draft_results(),
            pick_num
        )
        
        # Only update the current team's roster
        if team_on_clock > 0 and team_on_clock != getattr(self, '_last_roster_team', None):
            self.roster_view.current_team_id = team_on_clock
            self.roster_view.team_var.set(f"Team {team_on_clock}")
            self.roster_view.update_roster_display()
            self._last_roster_team = team_on_clock
    
    def draft_player(self):
        import time
        self._draft_start_time = time.time()
        start_time = self._draft_start_time
        
        # Check if players are loaded
        if not self.players_loaded:
            messagebox.showinfo(
                "Loading",
                "Please wait for player data to finish loading.",
                parent=self.root
            )
            return
        
        # Check if user has selected a team first (only in normal mode)
        if not self.manual_mode and not self.user_team_id:
            messagebox.showwarning(
                "No Team Selected", 
                "Please select a team before drafting.",
                parent=self.root
            )
            return
        
        player = self.player_list.get_selected_player()
        if not player:
            messagebox.showwarning(
                "No Selection", 
                "Please select a player to draft.",
                parent=self.root
            )
            return
        
        print(f"\n=== USER DRAFT START ===")
        print(f"[{time.time()-start_time:.3f}s] Starting draft for {player.name}")
        
        _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
        current_team = self.teams[team_on_clock]
        
        try:
            # First make the pick in the engine
            print(f"[{time.time()-start_time:.3f}s] Making pick in engine...")
            self.draft_engine.make_pick(current_team, player)
            
            # Remove from available players list
            print(f"[{time.time()-start_time:.3f}s] Removing from available list...")
            if player in self.available_players:
                self.available_players.remove(player)
            
            # Remove player from UI immediately
            print(f"[{time.time()-start_time:.3f}s] Removing from UI...")
            self._remove_drafted_player(player)
            print(f"[{time.time()-start_time:.3f}s] UI removal complete")
            
            # Update draft board immediately
            print(f"[{time.time()-start_time:.3f}s] Updating draft board...")
            pick_info = self.draft_engine.get_current_pick_info()
            self.draft_board.update_picks(
                self.draft_engine.get_draft_results(),
                pick_info[0]
            )
            print(f"[{time.time()-start_time:.3f}s] Draft board updated")
            
            # Update roster view to show the new pick
            print(f"[{time.time()-start_time:.3f}s] Updating roster view...")
            self.roster_view.update_roster_display()
            print(f"[{time.time()-start_time:.3f}s] Roster view updated")
            
            # Show pick quality indicator
            current_pick_num = self.draft_engine.get_current_pick_info()[0] - 1  # -1 because pick was just made
            self.show_pick_quality(player, current_pick_num)
            
            # Check if we need to auto-draft next
            print(f"[{time.time()-start_time:.3f}s] Checking auto-draft...")
            
            # Schedule auto-draft to run after UI updates
            self.root.after(1, self.check_auto_draft)
            
            print(f"[{time.time()-start_time:.3f}s] Draft player complete (scheduled auto-draft)")
        except ValueError as e:
            messagebox.showerror(
                "Invalid Pick", 
                str(e),
                parent=self.root
            )
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for drafting"""
        # Enter or Space to draft selected player
        self.root.bind('<Return>', lambda e: self.draft_player())
        self.root.bind('<space>', lambda e: self.draft_player())
        
        # Arrow keys to navigate players
        self.root.bind('<Left>', lambda e: self.navigate_players(-1))
        self.root.bind('<Right>', lambda e: self.navigate_players(1))
        
        # Numbers 1-9 to quick-select top players
        for i in range(1, 10):
            self.root.bind(str(i), lambda e, idx=i-1: self.select_player_by_index(idx))
    
    def navigate_players(self, direction):
        """Navigate through player cards with arrow keys"""
        if not self.player_list.player_cards:
            return
            
        current = self.player_list.selected_index or 0
        new_index = current + direction
        
        if 0 <= new_index < len(self.player_list.player_cards):
            self.player_list.select_player(new_index)
    
    def select_player_by_index(self, index):
        """Select player by index (for number keys)"""
        if index < len(self.player_list.player_cards):
            self.player_list.select_player(index)
    
    def on_team_selected(self, team_id):
        """Handle team selection for user control"""
        self.user_team_id = team_id
        # Enable draft button
        self.draft_button.config(state='normal', bg=DARK_THEME['button_active'])
        # Enable player draft buttons
        self.player_list.set_draft_enabled(True)
        # Check if we need to auto-draft for current pick after UI updates
        self.root.after(1, self.check_auto_draft)
    
    def toggle_manual_mode(self):
        """Toggle manual mode on/off"""
        self.manual_mode = self.manual_mode_var.get()
        
        if self.manual_mode:
            # In manual mode, user controls all picks
            self.status_label.config(text="Manual Mode - You control all picks")
            # Always enable draft controls
            self.draft_button.config(state='normal', bg=DARK_THEME['button_active'])
            self.player_list.set_draft_enabled(True)
        else:
            # Normal mode - need to select a team
            if not self.user_team_id:
                self.status_label.config(text="Select a team to control")
                self.draft_button.config(state='disabled', bg=DARK_THEME['button_bg'])
                self.player_list.set_draft_enabled(False)
            else:
                # Update display to show correct status
                self.update_display(full_update=False)
    
    def _remove_drafted_player(self, player):
        """Remove a drafted player from the UI"""
        if self.player_list.selected_index is not None:
            # Find the actual index of this player
            actual_index = None
            for i, p in enumerate(self.player_list.players):
                if p == player:
                    actual_index = i
                    break
            
            if actual_index is not None:
                self.player_list.remove_player_card(actual_index)
                self.player_list.selected_index = None
        
        # Also remove from watch list if present
        watch_list = self.roster_view.get_watch_list()
        if watch_list and player.player_id:
            watch_list.remove_drafted_player(player.player_id)
    
    def check_auto_draft(self):
        """Check if current pick should be automated"""
        if self.draft_engine.is_draft_complete():
            return
            
        _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
        
        # In manual mode, always wait for user input
        if self.manual_mode:
            self.update_display(full_update=False)
            return
        
        # If user hasn't selected a team or it's not their turn, auto-draft
        if self.user_team_id is None or team_on_clock != self.user_team_id:
            # Process all auto-picks immediately
            self.auto_draft_until_user_turn()
    
    def auto_draft_until_user_turn(self):
        """Automatically draft for all teams until it's the user's turn"""
        picks_made = []
        
        while not self.draft_engine.is_draft_complete():
            _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
            
            # Stop if it's the user's turn (or manual mode)
            if self.manual_mode or (self.user_team_id is not None and team_on_clock == self.user_team_id):
                break
            
            # Make auto pick
            if not self.available_players:
                break
                
            current_team = self.teams[team_on_clock]
            pick_num = self.draft_engine.get_current_pick_info()[0]
            
            # Smart pick selection
            selected_player = self._select_computer_pick(current_team, pick_num)
            
            if selected_player:
                try:
                    self.draft_engine.make_pick(current_team, selected_player)
                    self.available_players.remove(selected_player)
                    picks_made.append((pick_num, current_team, selected_player))
                    
                    # Update position count cache
                    if current_team.id in self._position_counts_cache:
                        if selected_player.position in self._position_counts_cache[current_team.id]:
                            self._position_counts_cache[current_team.id][selected_player.position] += 1
                except ValueError:
                    # Pick failed, try next player
                    continue
        
        # Update everything at once after all auto-picks
        if picks_made:
            # Remove auto-drafted players from the UI
            players_to_remove = [player for _, _, player in picks_made]
            self.player_list.remove_players(players_to_remove)
            
            # Also remove from watch list
            watch_list = self.roster_view.get_watch_list()
            if watch_list:
                for player in players_to_remove:
                    if player.player_id:
                        watch_list.remove_drafted_player(player.player_id)
            
            # Check if it's the user's turn
            pick_num, round_num, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
            is_user_turn = self.user_team_id and team_on_clock == self.user_team_id
            
            # Always update draft board after auto-drafting (especially for reversion)
            self.draft_board.update_picks(
                self.draft_engine.get_draft_results(),
                pick_num
            )
            
            # Update status labels
            self.status_label.config(text=f"Round {round_num} • Pick {pick_in_round}")
            self.on_clock_label.config(text=f"On the Clock: {self.teams[team_on_clock].name}")
            
            # Enable draft button if it's user's turn
            if is_user_turn:
                self.draft_button.config(state="normal", bg=DARK_THEME['button_active'])
            else:
                self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
            
            # Update roster view to reflect all the auto-picks
            self.roster_view.update_roster_display()
            
            # Just update idle tasks, not full update
            self.root.update_idletasks()
    
    def _select_computer_pick(self, team, pick_num):
        """Select a player for computer team based on smart drafting logic"""
        # Quick path for very early picks
        if pick_num <= 3:
            # Just take best available for first 3 picks
            return self.available_players[0] if self.available_players else None
        
        # Get cached position counts or calculate
        if team.id in self._position_counts_cache:
            position_counts = self._position_counts_cache[team.id]
        else:
            position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DEF': 0, 'K': 0}
            for players in team.roster.values():
                for player in players:
                    if player.position in position_counts:
                        position_counts[player.position] += 1
            self._position_counts_cache[team.id] = position_counts
        
        # Early rounds (1-3) should be much tighter to ADP
        is_early_round = pick_num <= (3 * config.num_teams)
        
        # Special handling for elite players that should never fall
        for player in self.available_players[:5]:
            # Elite players that must go by certain picks
            if player.name == "JAMARR CHASE" and pick_num >= 2:
                return player  # Chase must go by 1.02
            elif player.adp <= 3 and pick_num >= player.adp + 1:
                return player  # Top 3 players shouldn't fall more than 1 spot
            elif player.adp <= 10 and pick_num >= player.adp + 3:
                return player  # Top 10 players shouldn't fall more than 3 spots
        
        # Determine how many players to consider based on pick
        if is_early_round:
            # Early rounds: only consider players within reasonable ADP range
            max_adp_reach = 5  # Won't reach more than 5 picks early
            consider_range = 8  # Look at top 8 available
        else:
            max_adp_reach = 15  # More flexibility later
            consider_range = 20  # Look at top 20 available
        
        # Filter players by position needs and ADP appropriateness
        eligible_players = []
        for i, player in enumerate(self.available_players[:consider_range]):
            pos = player.position
            
            # Check if pick is too much of a reach
            if player.adp > pick_num + max_adp_reach:
                continue  # Don't reach too far
            
            # Check position limits
            if pos == 'QB' and position_counts.get('QB', 0) >= 2:
                continue  # Max 2 QBs
            elif pos == 'RB' and position_counts.get('RB', 0) >= 5:
                continue  # Max 5 RBs
            elif pos == 'WR' and position_counts.get('WR', 0) >= 5:
                continue  # Max 5 WRs
            elif pos == 'TE' and position_counts.get('TE', 0) >= 1:
                continue  # Max 1 TE (special case)
            elif pos == 'DEF' and position_counts.get('DEF', 0) >= 1:
                continue  # Max 1 DEF
            elif pos == 'K' and position_counts.get('K', 0) >= 1:
                continue  # Max 1 K
            
            # Don't draft K/DEF before round 10
            if pos in ['K', 'DEF'] and pick_num < (10 * config.num_teams):
                continue
            
            eligible_players.append(player)
        
        if not eligible_players:
            # If no eligible players, take best available non-K/DEF
            for player in self.available_players:
                if player.position not in ['K', 'DEF'] or pick_num >= 120:
                    return player
            return self.available_players[0] if self.available_players else None
        
        # Simplified pick selection - use ADP-based probability
        if is_early_round:
            # Early rounds: pick mostly by ADP with small variance
            if len(eligible_players) == 1:
                return eligible_players[0]
            
            # 70% chance to take best ADP, 20% second best, 10% third
            rand = random.random()
            if rand < 0.7:
                return eligible_players[0]
            elif rand < 0.9 and len(eligible_players) > 1:
                return eligible_players[1]
            elif len(eligible_players) > 2:
                return eligible_players[2]
            else:
                return eligible_players[0]
        else:
            # Later rounds: more randomness but still favor better ADP
            if len(eligible_players) == 1:
                return eligible_players[0]
            
            # 50% best, 30% second, 15% third, 5% fourth+
            rand = random.random()
            if rand < 0.5:
                return eligible_players[0]
            elif rand < 0.8 and len(eligible_players) > 1:
                return eligible_players[1]
            elif rand < 0.95 and len(eligible_players) > 2:
                return eligible_players[2]
            elif len(eligible_players) > 3:
                return eligible_players[3]
            else:
                return eligible_players[0]
    
    def _get_position_counts(self, team):
        """Get count of players by position for a team"""
        position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DEF': 0, 'K': 0}
        
        for pos_slot, players in team.roster.items():
            for player in players:
                if player.position in position_counts:
                    position_counts[player.position] += 1
        
        return position_counts
    
    def _get_team_needs(self, team):
        """Determine team's positional needs based on roster construction"""
        needs = []
        
        # Count players by position across all roster spots
        position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DEF': 0, 'K': 0}
        
        for pos_slot, players in team.roster.items():
            for player in players:
                if player.position in position_counts:
                    position_counts[player.position] += 1
        
        # Get counts
        qb_count = position_counts['QB']
        rb_count = position_counts['RB']
        wr_count = position_counts['WR']
        te_count = position_counts['TE']
        def_count = position_counts['DEF']
        k_count = position_counts['K']
        
        # Determine needs in priority order
        # Starting positions first
        if qb_count < 1:
            needs.append('QB')
        if rb_count < 2:
            needs.extend(['RB'] * (2 - rb_count))
        if wr_count < 2:
            needs.extend(['WR'] * (2 - wr_count))
        if te_count < 1:
            needs.append('TE')
        
        # FLEX considerations (prefer RB/WR)
        flex_filled = max(0, rb_count - 2) + max(0, wr_count - 2) + max(0, te_count - 1)
        if flex_filled < 1:
            needs.extend(['RB', 'WR'])  # Prefer RB/WR for flex
        
        # Bench depth
        if rb_count < 4:
            needs.append('RB')
        if wr_count < 4:
            needs.append('WR')
        if qb_count < 2:
            needs.append('QB')
        
        # Late round needs
        if def_count < 1:
            needs.append('DEF')
        if k_count < 1:
            needs.append('K')
        
        return needs
    
    def restart_draft(self):
        """Reset the draft but keep user team selection"""
        # Save current user team selection
        saved_user_team = self.user_team_id
        
        # Reset teams
        self.teams = self._create_teams()
        
        # Reset draft engine
        self.draft_engine = DraftEngine(
            num_teams=config.num_teams,
            roster_spots=config.roster_spots,
            draft_type=config.draft_type,
            reversal_round=config.reversal_round
        )
        
        # Reset players - load in background if needed
        if self.players_loaded:
            # Already loaded, just reset the lists
            self.available_players = list(self.all_players)
        else:
            # Still loading, wait for it to complete
            self.available_players = []
        
        # Restore user team selection
        self.user_team_id = saved_user_team
        
        # Clear position count cache
        self._position_counts_cache.clear()
        
        # Reset draft board UI completely and efficiently
        self.draft_board.draft_results = []
        self.draft_board._last_pick_count = 0
        if hasattr(self.draft_board, '_last_highlighted_pick'):
            delattr(self.draft_board, '_last_highlighted_pick')
        if hasattr(self.draft_board, '_update_pending'):
            self.draft_board._update_pending = False
        
        # Clear all pick widgets content more efficiently
        for pick_num, pick_widget in self.draft_board.pick_widgets.items():
            # Clear any player info frames in one pass
            children = list(pick_widget.winfo_children())
            for widget in children:
                # Only destroy player info frames, not the pick number label
                if isinstance(widget, tk.Frame) and hasattr(widget, 'winfo_y'):
                    try:
                        if widget.winfo_y() > 20:  # Player info is below pick number
                            widget.destroy()
                    except:
                        # Widget might already be destroyed
                        pass
            # Reset background color
            pick_widget.config(bg=DARK_THEME['bg_tertiary'], relief='flat')
        
        # Reset player list efficiently
        self.player_list._initialized = False  # Force full refresh
        
        # Clear row frames efficiently
        old_rows = self.player_list.row_frames[:]
        self.player_list.row_frames = []
        
        # Move all rows to hidden pool for reuse
        for row in old_rows:
            row.pack_forget()
            self.player_list.hidden_rows.append(row)
        
        # Update display with full refresh
        self.update_display(full_update=True)
        
        # Force roster view to clear and update
        self.roster_view.current_team_id = None
        self.roster_view.update_roster_display()
        
        # Clear the watch list
        watch_list = self.roster_view.get_watch_list()
        if watch_list:
            watch_list.clear_all()
        
        # Reset last roster team tracking
        if hasattr(self, '_last_roster_team'):
            delattr(self, '_last_roster_team')
        
        # Update button states based on user team
        if self.user_team_id:
            # Check if it's user's turn at pick 1
            _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
            if team_on_clock == self.user_team_id:
                self.draft_button.config(state="normal", bg=DARK_THEME['button_active'])
            else:
                self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
        
        # Disable undo button
        self.undo_button.config(state='disabled')
        self.draft_state_before_reversion = None
        self.players_before_reversion = None
        
        # Highlight pick 1 on the draft board
        self.draft_board.highlight_current_pick()
        
        # Start auto-drafting from the beginning if needed
        self.check_auto_draft()
    
    def on_pick_clicked(self, pick_number):
        """Handle clicking on a completed pick to revert draft to that point"""
        current_pick = self.draft_engine.get_current_pick_info()[0]
        
        if pick_number >= current_pick:
            return  # Can't revert to future picks
        
        # Save current state for undo
        self.draft_state_before_reversion = {
            'picks': list(self.draft_engine.draft_results),
            'teams': self._save_team_state(),
            'current_pick': self.draft_engine.get_current_pick_info()[0],
            'watched_players': self._save_watch_list_state()
        }
        self.players_before_reversion = list(self.available_players)
        
        # Revert the draft immediately - no confirmation
        self._revert_to_pick(pick_number)
        
        # Enable undo button
        self.undo_button.config(state='normal')
    
    def undo_reversion(self):
        """Undo the last draft reversion"""
        if not self.draft_state_before_reversion:
            return
        
        # Restore the draft state
        self._restore_draft_state(self.draft_state_before_reversion)
        self.available_players = list(self.players_before_reversion)
        
        # Restore watch list state
        self._restore_watch_list_state(self.draft_state_before_reversion.get('watched_players', {}))
        
        # Update display
        self.update_display()
        
        # Disable undo button
        self.undo_button.config(state='disabled')
        self.draft_state_before_reversion = None
        self.players_before_reversion = None
        
        # Check if we need to auto-draft
        self.check_auto_draft()
    
    def _save_team_state(self):
        """Save current state of all teams"""
        state = {}
        for team_id, team in self.teams.items():
            # Deep copy roster with all players
            roster_copy = {}
            for pos, players in team.roster.items():
                roster_copy[pos] = list(players)
            state[team_id] = {
                'roster': roster_copy
            }
        return state
    
    def _save_watch_list_state(self):
        """Save current state of watch list"""
        watch_list = self.roster_view.get_watch_list()
        if watch_list:
            return {
                'players': list(watch_list.watched_players),
                'player_ids': set(watch_list.watched_player_ids)
            }
        return {'players': [], 'player_ids': set()}
    
    def _restore_watch_list_state(self, watch_state):
        """Restore watch list to a saved state"""
        watch_list = self.roster_view.get_watch_list()
        if watch_list and watch_state:
            # Clear current watch list
            watch_list.watched_players.clear()
            watch_list.watched_player_ids.clear()
            
            # Restore saved state
            watch_list.watched_players = list(watch_state['players'])
            watch_list.watched_player_ids = set(watch_state['player_ids'])
            
            # Update displays
            watch_list.update_display()
            
            # Update player list stars
            if self.player_list.watch_list_ref:
                self.player_list.watched_player_ids = set(watch_state['player_ids'])
                self.player_list._update_star_icons()
    
    def _revert_to_pick(self, target_pick_number):
        """Revert draft to specified pick number and auto-draft to user's turn"""
        # Get picks to keep/remove
        picks_to_keep = [p for p in self.draft_engine.draft_results if p.pick_number < target_pick_number]
        picks_to_remove = [p for p in self.draft_engine.draft_results if p.pick_number >= target_pick_number]
        
        # Reset draft results
        self.draft_engine.draft_results = picks_to_keep
        
        # Batch add removed players back
        players_to_add = [pick.player for pick in picks_to_remove if pick.player not in self.available_players]
        self.available_players.extend(players_to_add)
        self.available_players.sort(key=lambda p: p.rank)
        
        # Reset team rosters in one pass
        for team in self.teams.values():
            team.roster = {pos: [] for pos in team.roster}
        for pick in picks_to_keep:
            self.teams[pick.team_id].add_player(pick.player)
        
        # Clear position count cache since rosters changed
        self._position_counts_cache.clear()
        
        # Skip watch list update during reversion - do it at the end
        
        # Clear draft board picks
        self.draft_board.clear_picks_after(target_pick_number)
        self.draft_board._last_pick_count = len(picks_to_keep)
        self.draft_board.draft_results = picks_to_keep
        
        # Now immediately auto-draft until user's turn
        self._fast_auto_draft_to_user()
    
    def _fast_auto_draft_to_user(self):
        """Fast auto-draft until it's the user's turn"""
        picks_made = []
        
        # Make all picks without UI updates
        while not self.draft_engine.is_draft_complete():
            _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
            
            # Stop if it's the user's turn (or manual mode)
            if self.manual_mode or (self.user_team_id is not None and team_on_clock == self.user_team_id):
                break
            
            if not self.available_players:
                break
                
            current_team = self.teams[team_on_clock]
            selected_player = self._select_computer_pick(current_team, self.draft_engine.get_current_pick_info()[0])
            
            if selected_player:
                try:
                    self.draft_engine.make_pick(current_team, selected_player)
                    self.available_players.remove(selected_player)
                    picks_made.append(selected_player)
                    
                    # Update position count cache
                    if current_team.id in self._position_counts_cache:
                        if selected_player.position in self._position_counts_cache[current_team.id]:
                            self._position_counts_cache[current_team.id][selected_player.position] += 1
                except ValueError:
                    continue
        
        # Now do all UI updates at once
        if picks_made:
            # Update draft board once
            pick_num = self.draft_engine.get_current_pick_info()[0]
            self.draft_board.update_picks(self.draft_engine.get_draft_results(), pick_num)
        
        # Restore watch list from saved state
        watch_list = self.roster_view.get_watch_list()
        if watch_list and self.draft_state_before_reversion:
            original_watch_state = self.draft_state_before_reversion.get('watched_players', {})
            original_watched_ids = original_watch_state.get('player_ids', set())
            
            # Get all currently drafted player IDs
            all_drafted_ids = {pick.player.player_id for pick in self.draft_engine.draft_results if pick.player.player_id}
            
            # Restore watch list to original minus currently drafted
            watch_list.watched_player_ids = original_watched_ids - all_drafted_ids
            watch_list.watched_players = [p for p in self.available_players 
                                        if p.player_id in watch_list.watched_player_ids]
            watch_list.update_display()
            
            if self.player_list.watch_list_ref:
                self.player_list.watched_player_ids = watch_list.watched_player_ids.copy()
        
        # Update player list once
        self.player_list.update_players(self.available_players)
        
        # Update star icons
        self.player_list._update_star_icons()
        
        # Final status update
        self.update_display(full_update=False)
    
    
    def _restore_draft_state(self, state):
        """Restore a saved draft state"""
        # Reset teams
        for team_id, team_state in state['teams'].items():
            team = self.teams[team_id]
            # Deep copy the roster
            for pos, players in team_state['roster'].items():
                team.roster[pos] = list(players)
        
        # Restore picks
        self.draft_engine.draft_results = list(state['picks'])
        
        # Clear and redraw all picks
        for pick_widget in self.draft_board.pick_widgets.values():
            for widget in pick_widget.winfo_children():
                if isinstance(widget, tk.Frame) and widget.winfo_y() > 20:
                    widget.destroy()
        
        # Reset and redraw
        self.draft_board._last_pick_count = 0
        self.draft_board.update_picks(self.draft_engine.draft_results, state['current_pick'])
    
    def center_window(self):
        """Center the window on the screen"""
        # Update the window to get actual dimensions
        self.root.update_idletasks()
        
        # Get window dimensions
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate center position
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set window position
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def show_loading_message(self):
        """Show loading message in player list"""
        # Create a loading label in the player list
        loading_label = tk.Label(
            self.player_list,
            text="Loading player data...",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14)
        )
        loading_label.place(relx=0.5, rely=0.5, anchor='center')
        self.loading_label = loading_label
        
        # Update status labels
        self.status_label.config(text="Loading player data...")
        self.on_clock_label.config(text="Please wait...")
    
    def load_players_async(self):
        """Load players in a background thread"""
        def load_players():
            # Load players
            players = generate_mock_players()
            
            # Update the app state from the main thread
            self.root.after(0, lambda: self.on_players_loaded(players))
        
        # Start background thread
        thread = threading.Thread(target=load_players, daemon=True)
        thread.start()
    
    def on_players_loaded(self, players):
        """Called when players are loaded"""
        self.all_players = players
        self.available_players = list(players)
        self.players_loaded = True
        
        # Remove loading label
        if hasattr(self, 'loading_label'):
            self.loading_label.destroy()
        
        # Update display with loaded players
        self.update_display(full_update=True)
        
        # Don't auto-draft immediately - wait for user to select a team
        # Only show a message prompting user to select a team
        if not self.user_team_id:
            self.status_label.config(text="Select a team to control")
            self.on_clock_label.config(text="Click on a team name in the draft board")
    
    def show_pick_quality(self, player, pick_num):
        """Show a notification about pick quality"""
        # Calculate ADP difference
        adp_diff = pick_num - player.adp
        
        # Determine pick quality based on ADP
        if adp_diff < -10:
            quality = "MAJOR REACH"
            color = "#FF4444"
        elif adp_diff < -5:
            quality = "REACH"
            color = "#FF8844"
        elif adp_diff < 3:
            quality = "FAIR VALUE"
            color = "#FFDD44"
        elif adp_diff < 10:
            quality = "GOOD VALUE"
            color = "#44FF44"
        else:
            quality = "STEAL"
            color = "#00FF00"
        
        # Get VAR ranking among position
        var_rank = "N/A"
        if hasattr(player, 'var') and player.var is not None:
            # Find player's VAR rank at their position
            position_players = [p for p in self.all_players if p.position == player.position and hasattr(p, 'var') and p.var is not None]
            position_players.sort(key=lambda p: p.var, reverse=True)
            for i, p in enumerate(position_players):
                if p == player:
                    var_rank = f"#{i+1} {player.position}"
                    break
        
        # Create notification frame
        notification = tk.Frame(self.root, bg=DARK_THEME['bg_secondary'], relief='raised', bd=2)
        notification.place(relx=0.5, rely=0.9, anchor='center')
        
        # Title
        title_label = tk.Label(
            notification,
            text=f"PICK ANALYSIS: {player.name}",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        title_label.pack(padx=20, pady=(10, 5))
        
        # Quality indicator
        quality_label = tk.Label(
            notification,
            text=quality,
            bg=color,
            fg='black',
            font=(DARK_THEME['font_family'], 16, 'bold'),
            padx=20,
            pady=5
        )
        quality_label.pack(pady=5)
        
        # Details
        details_text = f"Pick #{pick_num} • ADP: {player.adp:.1f} ({adp_diff:+.1f})"
        if var_rank != "N/A":
            details_text += f" • VAR Rank: {var_rank}"
        
        details_label = tk.Label(
            notification,
            text=details_text,
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 11)
        )
        details_label.pack(padx=20, pady=(0, 10))
        
        # Auto-hide after 3 seconds
        self.root.after(3000, notification.destroy)


def main():
    root = tk.Tk()
    
    # Configure ttk styles for dark theme
    style = ttk.Style()
    style.theme_use('clam')
    
    # Configure colors
    style.configure('TFrame', background=DARK_THEME['bg_secondary'])
    style.configure('TLabel', background=DARK_THEME['bg_secondary'], foreground=DARK_THEME['text_primary'])
    style.configure('TNotebook', background=DARK_THEME['bg_secondary'], borderwidth=0)
    style.configure('TNotebook.Tab', 
                   background=DARK_THEME['bg_tertiary'],
                   foreground=DARK_THEME['text_secondary'],
                   padding=[12, 6])
    style.map('TNotebook.Tab',
             background=[('selected', DARK_THEME['bg_hover'])],
             foreground=[('selected', DARK_THEME['text_primary'])])
    
    MockDraftApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()