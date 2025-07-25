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
from src.models import Team, Player
from src.models.draft_preset import PlayerExclusion
from src.core import DraftEngine, DraftPick
from src.core.template_manager import TemplateManager
from src.ui import DraftBoard, PlayerList, RosterView, GameHistory, DraftHistory, DraftHistoryPage
from src.ui.cheat_sheet_page import CheatSheetPage
from src.ui.theme import DARK_THEME
from src.ui.styled_widgets import StyledFrame, StyledButton
from src.utils import generate_mock_players
from src.utils.player_extensions import format_name
from src.services.player_pool_service import PlayerPoolService
from src.services.draft_save_manager import DraftSaveManager
from src.services.draft_preset_manager import DraftPresetManager


class MockDraftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mock Draft Simulator 2025")
        # Optimized window size - wider for draft board and taller for better visibility
        self.root.geometry("1920x1080")
        self.root.configure(bg=DARK_THEME['bg_primary'])
        
        # Set minimum window size
        self.root.minsize(1800, 900)
        
        # Center the window on screen after UI loads
        self.root.after(100, self.center_window)
        
        # Initialize draft preset manager first (needed by _create_teams)
        self.draft_preset_manager = DraftPresetManager()
        # Create default preset if no presets exist
        if not self.draft_preset_manager.list_preset_names():
            self.draft_preset_manager.create_default_preset()
        
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
        
        # Initialize player pool service (will be populated when players load)
        self.player_pool = None
        
        # Defer image service initialization
        self.image_service = None
        
        # User control state
        self.user_team_id = None  # Which team the user controls
        self.manual_mode = False  # Whether user controls all picks
        
        # Draft reversion state
        self.draft_state_before_reversion = None
        self.players_before_reversion = None
        
        # Performance optimization
        self._position_counts_cache = {}  # Cache position counts per team
        
        # Cheat sheet data
        self.custom_rankings = {}
        self.player_tiers = {}
        
        # Template manager
        self.template_manager = TemplateManager()
        
        # Draft save manager
        self.draft_save_manager = DraftSaveManager()
        
        # Quick loading indicator
        loading_label = tk.Label(
            self.root,
            text="Loading...",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 16)
        )
        loading_label.pack(expand=True)
        self.quick_loading = loading_label
        
        # Start loading players immediately
        self.load_players_async()
        
        # Defer UI setup slightly to show window faster
        self.root.after(1, self.setup_ui_deferred)
    
    def setup_ui_deferred(self):
        """Setup UI components after window is shown"""
        # Remove quick loading
        if hasattr(self, 'quick_loading'):
            self.quick_loading.destroy()
        
        # Setup UI
        self.setup_ui()
        self.setup_keyboard_shortcuts()
        
        # Show loading message for players
        self.show_loading_message()
    
    def _create_teams(self):
        teams = {}
        active_preset = self.draft_preset_manager.get_active_preset()
        
        for i in range(1, config.num_teams + 1):
            # Get team name from preset if available
            if active_preset and active_preset.enabled:
                team_name = active_preset.get_team_name(i - 1)  # 0-based index
            else:
                team_name = f"Team {i}"
            
            teams[i] = Team(
                team_id=i,
                name=team_name,
                roster_spots=config.roster_spots
            )
        return teams
    
    def setup_ui(self):
        # Initialize image service lazily
        if self.image_service is None:
            from src.services import PlayerImageService
            self.image_service = PlayerImageService()
        
        # Main container
        main_frame = StyledFrame(self.root, bg_type='primary')
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Header section
        header_frame = StyledFrame(main_frame, bg_type='primary')
        header_frame.pack(fill='x', pady=(0, 10))
        
        # Title and status container
        status_container = StyledFrame(header_frame, bg_type='primary')
        status_container.pack(side='left', fill='x', expand=True)
        
        self.status_label = tk.Label(
            status_container,
            text="",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        self.status_label.pack(anchor='w')
        
        self.on_clock_label = tk.Label(
            status_container,
            text="",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 11)
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
            padx=15,
            pady=5,
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
        
        # View Saved Drafts button
        self.view_saved_button = StyledButton(
            button_container,
            text="VIEW SAVED",
            command=self.view_saved_drafts,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=20,
            pady=10
        )
        self.view_saved_button.pack(side='left', padx=(0, 10))
        
        # Preset button
        self.preset_button = StyledButton(
            button_container,
            text="PRESETS",
            command=self.show_preset_dialog,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=20,
            pady=10
        )
        self.preset_button.pack(side='left', padx=(0, 10))
        
        # Repick Spot button
        self.repick_button = StyledButton(
            button_container,
            text="REPICK SPOT",
            command=self.repick_spot,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=20,
            pady=10
        )
        self.repick_button.pack(side='left', padx=(0, 10))
        
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
        
        # Template controls separator
        separator = tk.Frame(button_container, width=20, bg=DARK_THEME['bg_primary'])
        separator.pack(side='left')
        
        # Template dropdown
        template_label = tk.Label(
            button_container,
            text="Templates:",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        template_label.pack(side='left', padx=(0, 5))
        
        self.template_var = tk.StringVar()
        self.template_dropdown = ttk.Combobox(
            button_container,
            textvariable=self.template_var,
            width=20,
            state='readonly',
            font=(DARK_THEME['font_family'], 10)
        )
        self.template_dropdown.pack(side='left', padx=(0, 5))
        self.template_dropdown.bind('<<ComboboxSelected>>', self.on_template_selected)
        
        # Load template button
        self.load_template_button = StyledButton(
            button_container,
            text="LOAD",
            command=self.load_template,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10),
            padx=15,
            pady=8,
            state='disabled'
        )
        self.load_template_button.pack(side='left', padx=(0, 5))
        
        # Delete template button
        self.delete_template_button = StyledButton(
            button_container,
            text="DELETE",
            command=self.delete_template,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10),
            padx=15,
            pady=8,
            state='disabled'
        )
        self.delete_template_button.pack(side='left', padx=(0, 10))
        
        # Save template button
        self.save_template_button = StyledButton(
            button_container,
            text="SAVE AS...",
            command=self.save_template,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10),
            padx=15,
            pady=8
        )
        self.save_template_button.pack(side='left')
        
        # Main content area - Notebook for tabs
        content_frame = StyledFrame(main_frame, bg_type='primary')
        content_frame.pack(fill='both', expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Bind tab change event
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)
        
        # Tab 1: Draft
        draft_tab = StyledFrame(self.notebook, bg_type='primary')
        self.notebook.add(draft_tab, text="Draft")
        
        # Banner for "CHOOSE A DRAFT SPOT"
        self.draft_spot_banner = StyledFrame(draft_tab, bg_type='secondary')
        self.draft_spot_banner.pack(fill='x', padx=50, pady=20)
        
        banner_label = tk.Label(
            self.draft_spot_banner,
            text="CHOOSE A DRAFT SPOT",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 24, 'bold')
        )
        banner_label.pack(pady=15)
        
        banner_hint = tk.Label(
            self.draft_spot_banner,
            text="Click a 'Sit' button above any team to select your draft position",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 12)
        )
        banner_hint.pack(pady=(0, 15))
        
        # Create vertical PanedWindow for draggable divider in draft tab
        paned_window = tk.PanedWindow(
            draft_tab, 
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
            max_visible_rounds=3,
            on_team_select=self.on_team_selected,
            on_pick_click=self.on_pick_clicked,
            on_pick_change=self.on_pick_changed,
            get_top_players=self.get_top_available_players,
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
        
        self.player_list = PlayerList(player_panel, on_draft=self.draft_player, on_adp_change=self.on_adp_change, image_service=self.image_service)
        self.player_list.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Connect watch list to player list (bidirectional)
        if hasattr(self.roster_view, 'get_watch_list'):
            watch_list = self.roster_view.get_watch_list()
            self.player_list.set_watch_list_ref(watch_list)
            watch_list.set_player_list_ref(self.player_list)
        
        # Add frames to PanedWindow
        paned_window.add(top_frame, stretch='always')
        paned_window.add(player_panel, stretch='always')
        
        # Defer sash positioning to avoid layout calculations during startup
        self.root.after(50, lambda: self._set_sash_position(paned_window))
        
        # Tab 2: Cheat Sheet (defer creation)
        self.cheat_sheet_container = StyledFrame(self.notebook, bg_type='primary')
        self.notebook.add(self.cheat_sheet_container, text="Cheat Sheet")
        self._cheat_sheet_needs_sync = False
        self.cheat_sheet = None  # Will be created on first access
        
        # Tab 3: Stats (defer creation)
        self.game_history_container = StyledFrame(self.notebook, bg_type='primary')
        self.notebook.add(self.game_history_container, text="Stats")
        self.game_history = None  # Will be created on first access
        
        # Draft History tab
        self.draft_history_container = StyledFrame(self.notebook, bg_type='primary')
        self.notebook.add(self.draft_history_container, text="Draft History")
        self.draft_history = None  # Will be created on first access
        
        # ADP tab
        self.adp_container = StyledFrame(self.notebook, bg_type='primary')
        self.notebook.add(self.adp_container, text="ADP")
        self.adp_page = None  # Will be created on first access
        
        # Draft History Archive tab
        self.draft_history_archive_container = StyledFrame(self.notebook, bg_type='primary')
        self.notebook.add(self.draft_history_archive_container, text="Prev. Drafts")
        self.draft_history_archive = None  # Will be created on first access
    
    def update_display(self, full_update=True, force_refresh=False):
        # Update status
        pick_num, round_num, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
        
        if self.draft_engine.is_draft_complete():
            self.status_label.config(text="Draft Complete!")
            self.on_clock_label.config(text="All picks have been made")
            self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
            
            # Save the completed draft
            if not hasattr(self, '_draft_saved') or not self._draft_saved:
                self._save_completed_draft()
                self._draft_saved = True
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
            # Update draft context for BPA calculations
            current_pick = len(self.draft_engine.draft_results) + 1
            user_team = self.teams.get(self.user_team_id) if self.user_team_id else None
            self.player_list.set_draft_context(current_pick, user_team)
            
            self.player_list.update_players(self.available_players, force_refresh=force_refresh)
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
        
        # Make the pick using the shared method
        self._make_pick(player)
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for drafting"""
        # Removed global Enter/Space bindings that interfere with search inputs
        # Users can still draft via double-click or the Draft button
        
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
    
    def _set_sash_position(self, paned_window):
        """Set sash position after layout is complete"""
        paned_window.update_idletasks()
        height = paned_window.winfo_height()
        if height > 1:  # Ensure we have a valid height
            paned_window.sash_place(0, 0, int(height * 0.45))  # Reduced from 65% to 45%
    
    def on_team_selected(self, team_id):
        """Handle team selection for user control"""
        self.user_team_id = team_id
        
        # Check if preset is active - if so, don't rename teams
        active_preset = self.draft_preset_manager.get_active_preset()
        if not active_preset or not active_preset.enabled:
            # Only rename teams if no preset is active
            # Rename other teams to league member names
            league_names = ["Luan", "Joey", "Jerwan", "Karwan", "Johnson", "Erich", "Stan", "Pat", "Peter"]
            random.shuffle(league_names)  # Randomize the assignment
            
            name_index = 0
            for tid, team in self.teams.items():
                if tid != team_id:  # Don't rename the user's team
                    if name_index < len(league_names):
                        team.name = league_names[name_index]
                        name_index += 1
            
            # Update the draft board with new team names
            self.draft_board.update_team_names(self.teams)
        
        # Hide the banner when team is selected
        self.draft_spot_banner.pack_forget()
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
            # Hide the banner in manual mode
            self.draft_spot_banner.pack_forget()
        else:
            # Normal mode - need to select a team
            if not self.user_team_id:
                self.status_label.config(text="Select a team to control")
                self.draft_button.config(state='disabled', bg=DARK_THEME['button_bg'])
                self.player_list.set_draft_enabled(False)
                # Show the banner if no team selected
                self.draft_spot_banner.pack(fill='x', padx=50, pady=20, before=self.notebook.winfo_children()[0].winfo_children()[-1])
            else:
                # Update display to show correct status
                self.update_display(full_update=False)
    
    def draft_specific_player(self, player):
        """Draft a specific player object directly (e.g., from Game History)"""
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
        
        # Check if it's the user's turn
        current_pick, current_round, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
        if not self.manual_mode and team_on_clock.team_id != self.user_team_id:
            messagebox.showwarning(
                "Not Your Turn", 
                f"It's {team_on_clock.name}'s turn to pick.",
                parent=self.root
            )
            return
        
        # Check if player is available
        if player not in self.available_players:
            messagebox.showwarning(
                "Player Unavailable", 
                f"{player.name} has already been drafted.",
                parent=self.root
            )
            return
        
        # Make the pick directly
        self._make_pick(player)
    
    def _make_pick(self, player):
        """Make a draft pick for the given player"""
        import time
        start_time = time.time()
        
        # Get current pick info
        current_pick, current_round, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
        current_team = self.teams[team_on_clock]
        
        try:
            # First make the pick in the engine
            print(f"[{time.time()-start_time:.3f}s] Making pick in engine...")
            self.draft_engine.make_pick(current_team, player)
            
            # Remove from available players list
            print(f"[{time.time()-start_time:.3f}s] Removing from available list...")
            if player in self.available_players:
                self.available_players.remove(player)
            
            # Update player pool service
            if self.player_pool:
                self.player_pool.draft_player(player)
            
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
            
            # Update draft history if it exists
            if self.draft_history:
                last_pick = self.draft_engine.draft_results[-1]
                self.draft_history.add_pick(last_pick)
            
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
    
    def _remove_drafted_player(self, player):
        """Remove a drafted player from the UI"""
        # Always remove the player from the list, regardless of selection
        self.player_list.remove_players([player])
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
            
            # Update player pool service
            if self.player_pool:
                for player in players_to_remove:
                    self.player_pool.draft_player(player)
            
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
        # Check preset exclusions first
        active_preset = self.draft_preset_manager.get_active_preset()
        
        # Quick path for very early picks
        if pick_num <= 3:
            # Check preset exclusions even for early picks
            for player in self.available_players:
                if active_preset and active_preset.is_player_excluded(team.name, player.name):
                    continue  # Skip excluded player
                return player  # Return first non-excluded player
            return None
        
        # Get cached position counts or calculate
        if team.id in self._position_counts_cache:
            position_counts = self._position_counts_cache[team.id]
        else:
            position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DEF': 0, 'K': 0, 'LB': 0, 'DB': 0}
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
        
        # Special handling for Joe Burrow - must be taken by pick 21
        if pick_num >= 21:
            for player in self.available_players:
                if format_name(player.name) == "JOE BURROW":
                    return player
        
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
            
            # Check preset exclusions
            if active_preset and active_preset.is_player_excluded(team.name, player.name):
                continue  # Skip excluded player
            
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
            elif pos == 'LB' and position_counts.get('LB', 0) >= 4:
                continue  # Max 4 LBs
            elif pos == 'DB' and position_counts.get('DB', 0) >= 4:
                continue  # Max 4 DBs
            
            # Don't draft K/DEF/LB/DB before round 10
            if pos in ['K', 'DEF', 'LB', 'DB'] and pick_num < (10 * config.num_teams):
                continue
            
            eligible_players.append(player)
        
        if not eligible_players:
            # If no eligible players, take best available non-K/DEF
            for player in self.available_players:
                # Check preset exclusions even in fallback
                if active_preset and active_preset.is_player_excluded(team.name, player.name):
                    continue  # Skip excluded player
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
    
    def get_top_available_players(self, count=5, pick_number=None):
        """Get the top N available players by ADP, or players drafted after given pick"""
        if pick_number is None:
            # Normal case - just return available players
            return self.available_players[:count] if self.available_players else []
        
        # For change pick - include available players and players drafted after this pick
        eligible_players = []
        
        # Add all available players
        eligible_players.extend(self.available_players)
        
        # Add players drafted after this pick
        for i in range(pick_number, len(self.draft_engine.draft_results)):
            pick = self.draft_engine.draft_results[i]
            if pick.player not in eligible_players:
                eligible_players.append(pick.player)
        
        # Sort by ADP and return top N
        eligible_players.sort(key=lambda p: p.adp if p.adp else 999)
        return eligible_players[:count]
    
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
    
    def on_cheat_sheet_update(self, custom_rankings, player_tiers):
        """Called when cheat sheet rankings are updated"""
        self.custom_rankings = custom_rankings
        self.player_tiers = player_tiers
        
        # Update player list to show custom rankings
        if hasattr(self, 'player_list'):
            self.player_list.set_custom_rankings(custom_rankings, player_tiers)
            # Only update if we're currently sorting by custom rank
            if self.player_list.sort_by == 'custom_rank':
                self.player_list.update_players(self.available_players)
            else:
                # Just update the custom rank display without full refresh
                self.player_list.update_table_view()
    
    def on_adp_change(self):
        """Called when ADP values are changed via UI"""
        # Re-sort available players by ADP to maintain proper draft order
        self.available_players.sort(key=lambda p: p.adp if p.adp else 999)
    
    def restart_draft(self):
        """Reset the draft but keep user team selection"""
        # Save current user team selection
        saved_user_team = self.user_team_id
        
        # Reset draft saved flag
        self._draft_saved = False
        
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
            # Apply custom ADP values before sorting
            from src.services.custom_adp_manager import CustomADPManager
            adp_manager = CustomADPManager()
            adp_manager.apply_custom_adp_to_players(self.all_players)
            # Sort by ADP for proper draft order
            self.available_players = sorted(list(self.all_players), key=lambda p: p.adp if p.adp else 999)
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
        
        # Clear all pick widgets content using the draft board's method
        self.draft_board.clear_picks_after(1)  # Clear all picks starting from pick 1
        
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
        self.update_display(full_update=True, force_refresh=True)
        
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
        
        # Clear draft history if it exists
        if self.draft_history:
            self.draft_history.clear_history()
        
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
    
    def repick_spot(self):
        """Reset the draft and clear user team selection to allow repicking"""
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
            # Apply custom ADP values before sorting
            from src.services.custom_adp_manager import CustomADPManager
            adp_manager = CustomADPManager()
            adp_manager.apply_custom_adp_to_players(self.all_players)
            # Sort by ADP for proper draft order
            self.available_players = sorted(list(self.all_players), key=lambda p: p.adp if p.adp else 999)
        else:
            # Still loading, wait for it to complete
            self.available_players = []
        
        # Clear user team selection - this is the key difference from restart_draft
        self.user_team_id = None
        
        # Clear position count cache
        self._position_counts_cache.clear()
        
        # Reset draft board UI completely
        self.draft_board.draft_results = []
        self.draft_board._last_pick_count = 0
        if hasattr(self.draft_board, '_last_highlighted_pick'):
            delattr(self.draft_board, '_last_highlighted_pick')
        if hasattr(self.draft_board, '_update_pending'):
            self.draft_board._update_pending = False
        
        # Clear all pick widgets content using the draft board's method
        self.draft_board.clear_picks_after(1)  # Clear all picks starting from pick 1
        
        # Reset all team selection buttons
        for team_id, button in self.draft_board.team_buttons.items():
            button.config(
                bg=DARK_THEME['button_bg'],
                fg='white',
                text='Sit'
            )
        
        # Show the sit row again
        self.draft_board.show_sit_row()
        
        # Start glow animation again since no team is selected
        self.draft_board.selected_team_id = None
        self.draft_board.start_glow_animation()
        
        # Reset player list
        self.player_list._initialized = False
        old_rows = self.player_list.row_frames[:]
        self.player_list.row_frames = []
        
        for row in old_rows:
            row.pack_forget()
            self.player_list.hidden_rows.append(row)
        
        # Disable draft controls since no team is selected
        self.draft_button.config(state='disabled', bg=DARK_THEME['button_bg'])
        self.player_list.set_draft_enabled(False)
        
        # Show the "CHOOSE A DRAFT SPOT" banner again
        self.draft_spot_banner.pack(fill='x', padx=50, pady=20, before=self.notebook.winfo_children()[0].winfo_children()[-1])
        
        # Update display with full refresh
        self.update_display(full_update=True, force_refresh=True)
        
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
        
        # Disable undo button
        self.undo_button.config(state='disabled')
        self.draft_state_before_reversion = None
        self.players_before_reversion = None
        
        # Highlight pick 1 on the draft board
        self.draft_board.highlight_current_pick()
        
        # Show status prompting user to select a team
        self.status_label.config(text="Select a team to control")
        self.on_clock_label.config(text="Click on a team name in the draft board")
    
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
    
    def on_pick_changed(self, pick_number, new_player):
        """Handle changing a draft pick to a different player"""
        current_pick = self.draft_engine.get_current_pick_info()[0]
        if pick_number >= current_pick:
            return  # Can't change future picks
        
        print(f"\n=== CHANGE PICK ===")
        print(f"Changing pick {pick_number} to {new_player.name}")
        
        # Save current state for undo
        self.draft_state_before_reversion = {
            'picks': list(self.draft_engine.draft_results),
            'teams': self._save_team_state(),
            'current_pick': current_pick,
            'watched_players': self._save_watch_list_state()
        }
        self.players_before_reversion = list(self.available_players)
        
        # Get the original pick details
        original_pick = self.draft_engine.draft_results[pick_number - 1]
        original_team_id = original_pick.team_id
        
        # Check if new player was already drafted
        already_drafted_at = None
        for i, pick in enumerate(self.draft_engine.draft_results):
            if pick.player.player_id == new_player.player_id:
                already_drafted_at = i + 1  # Convert to 1-based pick number
                print(f"Player {new_player.name} was already drafted at pick {already_drafted_at}")
                break
        
        # First, revert to the pick we want to change (skip auto-draft!)
        print(f"Reverting to pick {pick_number}...")
        self._revert_to_pick(pick_number, skip_auto_draft=True)
        
        # Verify we're at the right pick
        current = self.draft_engine.get_current_pick_info()
        print(f"Now at pick {current[0]}, team {current[3]} on clock")
        
        # Make the specific pick
        print(f"Making pick: {new_player.name}")
        self._make_pick(new_player)
        
        # Handle the case where the player was already drafted
        if already_drafted_at and already_drafted_at > pick_number:
            if not self.manual_mode:
                # In non-manual mode, auto-draft until user's turn
                print(f"Auto-drafting from pick {pick_number + 1} to user's turn...")
                self.root.after(100, self.auto_draft_until_user_turn)
            else:
                # In manual mode, revert to where player was originally drafted
                print(f"Manual mode: Reverting to pick {already_drafted_at} where {new_player.name} was originally")
                self.root.after(100, lambda: self._revert_to_pick(already_drafted_at, skip_auto_draft=True))
        else:
            # No conflict, just need to auto-draft if not in manual mode
            if not self.manual_mode:
                print(f"Auto-drafting remaining picks...")
                self.root.after(100, self.auto_draft_until_user_turn)
        
        # Enable undo button
        self.undo_button.config(state='normal')
        print("=== CHANGE PICK COMPLETE ===\n")
    
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
        self.update_display(force_refresh=True)
        
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
    
    def _revert_to_pick(self, target_pick_number, skip_auto_draft=False):
        """Revert draft to specified pick number and auto-draft to user's turn"""
        # Get picks to keep/remove
        picks_to_keep = [p for p in self.draft_engine.draft_results if p.pick_number < target_pick_number]
        picks_to_remove = [p for p in self.draft_engine.draft_results if p.pick_number >= target_pick_number]
        
        # Reset draft results
        self.draft_engine.draft_results = picks_to_keep
        
        # Rebuild available players list from scratch to ensure consistency
        # Start with all players
        self.available_players = list(self.all_players)
        
        # Remove players that are still drafted (in picks_to_keep)
        drafted_player_ids = {pick.player.player_id for pick in picks_to_keep}
        self.available_players = [p for p in self.available_players if p.player_id not in drafted_player_ids]
        
        # Apply custom ADP values before sorting
        from src.services.custom_adp_manager import CustomADPManager
        adp_manager = CustomADPManager()
        adp_manager.apply_custom_adp_to_players(self.available_players)
        
        # Sort by ADP for proper draft order
        self.available_players.sort(key=lambda p: p.adp if p.adp else 999)
        
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
        
        # Now immediately auto-draft until user's turn (unless skipped)
        if not skip_auto_draft:
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
                    # Only remove if player is actually in the list
                    if selected_player in self.available_players:
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
        self.player_list.update_players(self.available_players, force_refresh=True)
        
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
            try:
                # Load players
                players = generate_mock_players()
                print(f"Successfully loaded {len(players)} players")
            except Exception as e:
                print(f"ERROR loading players: {e}")
                import traceback
                traceback.print_exc()
                # Return empty list on error
                players = []
            
            # Update the app state from the main thread
            self.root.after(0, lambda: self.on_players_loaded(players))
        
        # Start background thread
        thread = threading.Thread(target=load_players, daemon=True)
        thread.start()
    
    def on_players_loaded(self, players):
        """Called when players are loaded"""
        self.all_players = players
        
        # Apply custom ADP values before sorting
        from src.services.custom_adp_manager import CustomADPManager
        adp_manager = CustomADPManager()
        adp_manager.apply_custom_adp_to_players(players)
        
        # Sort available players by ADP for proper draft order
        self.available_players = sorted(list(players), key=lambda p: p.adp if p.adp else 999)
        self.players_loaded = True
        
        # Initialize player pool service
        self.player_pool = PlayerPoolService(players)
        
        # Remove loading label
        if hasattr(self, 'loading_label'):
            self.loading_label.destroy()
        
        # Don't create cheat sheet until tab is accessed
        
        # Update display with loaded players
        self.update_display(full_update=True)
        
        # Check if preset should set user team
        active_preset = self.draft_preset_manager.get_active_preset()
        if active_preset and active_preset.enabled:
            user_team_name = active_preset.get_user_team_name()
            if user_team_name:
                # Find the team ID for the user's team
                for team_id, team in self.teams.items():
                    if team.name == user_team_name:
                        self.user_team_id = team_id
                        # Update draft board to show user control
                        self.draft_board.set_user_team(team_id)
                        # Hide the draft spot banner since preset handles it
                        self.draft_spot_banner.pack_forget()
                        break
        
        # Don't auto-draft immediately - wait for user to select a team
        # Only show a message prompting user to select a team
        if not self.user_team_id:
            self.status_label.config(text="Select a team to control")
            self.on_clock_label.config(text="Click on a team name in the draft board")
    
    def on_tab_changed(self, event):
        """Handle tab change events"""
        selected_tab = self.notebook.select()
        tab_text = self.notebook.tab(selected_tab, "text")
        
        # Clean up any lingering tooltips from player list
        if hasattr(self, 'player_list') and self.player_list:
            self.player_list.cleanup_tooltips()
        
        if tab_text == "Cheat Sheet":
            # Create cheat sheet on first access
            if self.cheat_sheet is None and self.players_loaded:
                self.cheat_sheet = CheatSheetPage(
                    self.cheat_sheet_container,
                    self.all_players,
                    draft_app=self
                )
                self.cheat_sheet.pack(fill='both', expand=True)
                
                # Connect cheat sheet to player list for round display
                if hasattr(self, 'player_list'):
                    self.player_list.set_cheat_sheet_ref(self.cheat_sheet)
            
            if self.cheat_sheet:
                # Force focus to cheat sheet for mouse wheel scrolling
                self.root.after(10, lambda: self.cheat_sheet.focus_set())
        elif tab_text == "Stats":
            # Create game history on first access
            if self.game_history is None and self.players_loaded:
                self.game_history = GameHistory(
                    self.game_history_container,
                    self.all_players,
                    player_pool_service=self.player_pool,
                    on_draft=self.draft_specific_player
                )
                self.game_history.pack(fill='both', expand=True)
            
            if self.game_history:
                # Force focus for scrolling
                self.root.after(10, lambda: self.game_history.focus_set())
        elif tab_text == "Draft History":
            # Create draft history on first access
            if self.draft_history is None:
                self.draft_history = DraftHistory(self.draft_history_container)
                self.draft_history.pack(fill='both', expand=True)
                # Initialize with current draft data
                self.draft_history.update_draft_history(self.draft_engine.draft_results, self.teams)
            
            if self.draft_history:
                # Update with latest draft data
                self.draft_history.update_draft_history(self.draft_engine.draft_results, self.teams)
                # Force focus for scrolling
                self.root.after(10, lambda: self.draft_history.focus_set())
        elif tab_text == "Prev. Drafts":
            # Create draft history archive on first access
            if self.draft_history_archive is None:
                self.draft_history_archive = DraftHistoryPage(self.draft_history_archive_container)
                self.draft_history_archive.pack(fill='both', expand=True)
            
            if self.draft_history_archive:
                # Force focus for scrolling
                self.root.after(10, lambda: self.draft_history_archive.focus_set())
        elif tab_text == "ADP":
            # Check if players are loaded
            if not self.players_loaded:
                # Show loading message
                if not hasattr(self, 'adp_loading_label'):
                    self.adp_loading_label = tk.Label(
                        self.adp_container,
                        text="Loading player data...",
                        bg=DARK_THEME['bg_primary'],
                        fg=DARK_THEME['text_secondary'],
                        font=(DARK_THEME['font_family'], 14)
                    )
                    self.adp_loading_label.place(relx=0.5, rely=0.5, anchor='center')
                    
                # Track loading attempts
                if not hasattr(self, 'adp_loading_attempts'):
                    self.adp_loading_attempts = 0
                self.adp_loading_attempts += 1
                
                # After 10 attempts (5 seconds), show error message
                if self.adp_loading_attempts > 10:
                    if hasattr(self, 'adp_loading_label'):
                        self.adp_loading_label.config(
                            text="Failed to load player data. Please restart the application."
                        )
                    print("ERROR: Failed to load players after 10 attempts")
                    return
                    
                # Check again in a moment
                self.root.after(500, lambda: self.on_tab_changed(None))
                return
            
            # Remove loading label if it exists
            if hasattr(self, 'adp_loading_label'):
                self.adp_loading_label.destroy()
                delattr(self, 'adp_loading_label')
            
            # Create ADP page on first access
            if self.adp_page is None:
                print(f"Creating ADPPage with {len(self.all_players)} players")
                # Debug: Show sample players
                if self.all_players:
                    print(f"Sample players being passed to ADPPage:")
                    for p in self.all_players[:3]:
                        print(f"  - {p.format_name()} ({p.position}) ADP: {p.adp}")
                else:
                    print("WARNING: No players available for ADPPage!")
                    
                from src.ui.adp_page import ADPPage
                self.adp_page = ADPPage(
                    self.adp_container,
                    self.all_players,
                    on_adp_change=self.on_adp_change
                )
                self.adp_page.pack(fill='both', expand=True)
            
            if self.adp_page:
                # Update with latest player data in case it changed
                self.adp_page.all_players = self.all_players
                self.adp_page.update_display()
                # Force focus for scrolling
                self.root.after(10, lambda: self.adp_page.focus_set())
        elif tab_text == "Draft":
            # Update player list with cheat sheet rounds when switching back
            if self.cheat_sheet and hasattr(self, 'player_list'):
                self.player_list.set_cheat_sheet_ref(self.cheat_sheet)
            
            if self._cheat_sheet_needs_sync and self.cheat_sheet:
                # Sync rankings when switching back to draft tab
                self._cheat_sheet_needs_sync = False
                # Update the display to show updated rounds
                if hasattr(self, 'player_list'):
                    self.player_list.update_table_view()
    
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
    
    def update_template_dropdown(self):
        """Update the template dropdown with available templates"""
        templates = self.template_manager.list_templates()
        template_names = [t["name"] for t in templates]
        self.template_dropdown['values'] = template_names
        if not template_names:
            self.template_var.set("")
    
    def on_template_selected(self, event=None):
        """Handle template selection from dropdown"""
        # Enable load and delete buttons when template is selected
        if self.template_var.get():
            self.load_template_button.config(state='normal')
            self.delete_template_button.config(state='normal')
        else:
            self.load_template_button.config(state='disabled')
            self.delete_template_button.config(state='disabled')
    
    def save_template(self):
        """Save current draft state as a template"""
        # Ask user for template name
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Template")
        dialog.geometry("400x150")
        dialog.configure(bg=DARK_THEME['bg_secondary'])
        
        # Center dialog on parent
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog on parent window
        dialog.update_idletasks()
        x = (self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2))
        y = (self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2))
        dialog.geometry(f"+{x}+{y}")
        
        # Name input
        label = tk.Label(
            dialog,
            text="Template Name:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11)
        )
        label.pack(pady=(20, 5))
        
        name_var = tk.StringVar()
        entry = tk.Entry(
            dialog,
            textvariable=name_var,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11),
            width=30
        )
        entry.pack(pady=5)
        entry.focus()
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=DARK_THEME['bg_secondary'])
        button_frame.pack(pady=20)
        
        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter a template name")
                return
            
            # Get watch list from roster view
            watch_list = []
            wl = self.roster_view.get_watch_list()
            if wl:
                watch_list = [p.player_id for p in wl.watched_players]
            
            success = self.template_manager.save_template(
                name=name,
                draft_engine=self.draft_engine,
                teams=list(self.teams.values()),
                available_players=self.available_players,
                all_players=self.all_players,
                user_team_id=self.user_team_id,
                manual_mode=self.manual_mode,
                custom_rankings=self.custom_rankings,
                player_tiers=self.player_tiers,
                watch_list=watch_list
            )
            
            if success:
                messagebox.showinfo("Success", f"Template '{name}' saved successfully")
                self.update_template_dropdown()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to save template")
        
        save_btn = StyledButton(
            button_frame,
            text="SAVE",
            command=save,
            bg=DARK_THEME['button_active'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=20,
            pady=8
        )
        save_btn.pack(side='left', padx=5)
        
        cancel_btn = StyledButton(
            button_frame,
            text="CANCEL",
            command=dialog.destroy,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10),
            padx=20,
            pady=8
        )
        cancel_btn.pack(side='left', padx=5)
        
        # Save on Enter
        entry.bind('<Return>', lambda e: save())
    
    def delete_template(self):
        """Delete the selected template"""
        selected = self.template_var.get()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a template to delete")
            return
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Delete Template",
            f"Are you sure you want to delete the template '{selected}'?",
            parent=self.root
        )
        
        if result:
            # Find the template file
            templates = self.template_manager.list_templates()
            template_file = None
            for t in templates:
                if t["name"] == selected:
                    template_file = t["filename"]
                    break
            
            if template_file:
                success = self.template_manager.delete_template(template_file)
                if success:
                    messagebox.showinfo("Success", f"Template '{selected}' deleted successfully")
                    self.update_template_dropdown()
                    # Clear selection and disable buttons
                    self.template_var.set("")
                    self.load_template_button.config(state='disabled')
                    self.delete_template_button.config(state='disabled')
                else:
                    messagebox.showerror("Error", "Failed to delete template")
            else:
                messagebox.showerror("Error", "Template file not found")
    
    def load_template(self):
        """Load a selected template"""
        selected = self.template_var.get()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a template to load")
            return
        
        # Find the template file
        templates = self.template_manager.list_templates()
        template_file = None
        for t in templates:
            if t["name"] == selected:
                template_file = t["filename"]
                break
        
        if not template_file:
            messagebox.showerror("Error", "Template file not found")
            return
        
        # Load the template
        template = self.template_manager.load_template(template_file)
        if not template:
            messagebox.showerror("Error", "Failed to load template")
            return
        
        # Apply the template state
        self.apply_template(template)
        messagebox.showinfo("Success", f"Template '{selected}' loaded successfully")
    
    def apply_template(self, template):
        """Apply a loaded template to restore draft state"""
        # Reset teams and draft engine with saved config
        config_data = template.draft_config
        self.teams = self._create_teams()
        self.draft_engine = DraftEngine(
            num_teams=config_data.get('num_teams', config.num_teams),
            roster_spots=config_data.get('roster_spots', config.roster_spots),
            draft_type=config_data.get('draft_type', config.draft_type),
            reversal_round=config_data.get('reversal_round', config.reversal_round)
        )
        
        # Restore player pool
        player_dict = {p['player_id']: p for p in template.player_pool['all_players']}
        self.all_players = []
        for p_data in template.player_pool['all_players']:
            player = Player(
                name=p_data['name'],
                position=p_data['position'],
                team=p_data.get('team', ''),
                bye_week=p_data.get('bye_week', 0),
                points_2024=p_data.get('points_2024', 0),
                points_2025_proj=p_data.get('points_2025_proj', 0),
                var=p_data.get('var', 0),
                rank=p_data.get('rank', 999),
                adp=p_data.get('adp', 999),
                games_2024=p_data.get('games_2024'),
                position_rank_2024=p_data.get('position_rank_2024'),
                position_rank_proj=p_data.get('position_rank_proj'),
                weekly_stats_2024=p_data.get('weekly_stats_2024')
            )
            player.player_id = p_data['player_id']
            self.all_players.append(player)
        
        # Create player lookup
        player_lookup = {p.player_id: p for p in self.all_players}
        
        # Restore available players
        self.available_players = [
            player_lookup[pid] for pid in template.player_pool['available_player_ids']
            if pid in player_lookup
        ]
        
        # Restore team names and rosters
        for team_id_str, team_data in template.team_states.items():
            team_id = int(team_id_str)
            if team_id in self.teams:
                team = self.teams[team_id]
                team.name = team_data['name']
                
                # Clear and restore roster
                for pos in team.roster:
                    team.roster[pos] = []
                
                for position, player_ids in team_data['roster'].items():
                    if position in team.roster:
                        team.roster[position] = [
                            player_lookup[pid] for pid in player_ids
                            if pid in player_lookup
                        ]
        
        # Restore draft picks
        for pick_data in template.draft_results:
            if pick_data['player_id'] and pick_data['player_id'] in player_lookup:
                player = player_lookup[pick_data['player_id']]
                team_id = pick_data['team_id']
                if team_id in self.teams:
                    self.draft_engine.make_pick(self.teams[team_id], player)
        
        # Restore user settings
        user_settings = template.user_settings
        self.user_team_id = user_settings.get('user_team_id')
        self.manual_mode = user_settings.get('manual_mode', False)
        self.manual_mode_var.set(self.manual_mode)
        self.custom_rankings = user_settings.get('custom_rankings', {})
        self.player_tiers = user_settings.get('player_tiers', {})
        
        # Apply custom rankings to player list if loaded
        if self.custom_rankings and hasattr(self, 'player_list'):
            self.player_list.custom_rankings = self.custom_rankings
        
        # Restore watch list
        watch_list_ids = user_settings.get('watch_list', [])
        if watch_list_ids and hasattr(self, 'roster_view'):
            wl = self.roster_view.get_watch_list()
            if wl:
                for player_id in watch_list_ids:
                    if player_id in player_lookup:
                        wl.add_player(player_lookup[player_id])
        
        # Update UI
        self.update_display(full_update=True, force_refresh=True)
        
        # Update draft board
        self.draft_board.update_picks(self.draft_engine.draft_results)
        self.draft_board.highlight_current_pick()
        
        # Update status
        if self.user_team_id:
            self.update_draft_status()
            # Hide draft spot banner
            if hasattr(self, 'draft_spot_banner'):
                self.draft_spot_banner.pack_forget()
        else:
            self.status_label.config(text="Select a team to control")
            self.on_clock_label.config(text="Click on a team name in the draft board")
        
        # Enable/disable buttons based on state
        if self.user_team_id:
            _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
            if team_on_clock == self.user_team_id:
                self.draft_button.config(state="normal", bg=DARK_THEME['button_active'])
            else:
                self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
        
        # Check for auto-draft
        self.check_auto_draft()
    
    def setup_ui_deferred(self):
        """Setup UI components after window is shown"""
        # Remove quick loading
        if hasattr(self, 'quick_loading'):
            self.quick_loading.destroy()
        
        # Setup UI
        self.setup_ui()
        self.setup_keyboard_shortcuts()
        
        # Update template dropdown
        self.update_template_dropdown()
        
        # Show loading message for players
        self.show_loading_message()
    
    def _save_completed_draft(self):
        """Save the completed draft to JSON"""
        try:
            filename = self.draft_save_manager.save_draft(
                self.draft_engine.draft_results,
                self.teams,
                self.user_team_id,
                self.manual_mode
            )
            
            # Show success message
            messagebox.showinfo(
                "Draft Saved",
                f"Draft saved successfully!\n\nFile: {filename}",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Save Error",
                f"Failed to save draft: {str(e)}",
                parent=self.root
            )
    
    def view_saved_drafts(self):
        """View saved draft files"""
        saved_drafts = self.draft_save_manager.get_saved_drafts()
        
        if not saved_drafts:
            messagebox.showinfo(
                "No Saved Drafts",
                "No saved drafts found.\n\nDrafts are automatically saved when completed.",
                parent=self.root
            )
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Saved Drafts")
        dialog.geometry("600x400")
        dialog.configure(bg=DARK_THEME['bg_primary'])
        
        # Header
        header = tk.Label(
            dialog,
            text="SAVED DRAFTS",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        header.pack(pady=10)
        
        # List frame
        list_frame = StyledFrame(dialog, bg_type='secondary')
        list_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # Scrollable list
        canvas = tk.Canvas(list_frame, bg=DARK_THEME['bg_secondary'], highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=canvas.yview)
        
        drafts_frame = tk.Frame(canvas, bg=DARK_THEME['bg_secondary'])
        drafts_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        canvas_window = canvas.create_window((0, 0), window=drafts_frame, anchor='nw')
        
        # Make drafts frame expand to canvas width
        def configure_canvas(event):
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        canvas.bind('<Configure>', configure_canvas)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Display saved drafts
        for i, draft_info in enumerate(saved_drafts):
            # Row background
            row_bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
            
            row = tk.Frame(drafts_frame, bg=row_bg, height=60)
            row.pack(fill='x', pady=1)
            row.pack_propagate(False)
            
            # Draft info
            info_frame = tk.Frame(row, bg=row_bg)
            info_frame.pack(side='left', fill='both', expand=True, padx=10)
            
            # Filename and timestamp
            filename_label = tk.Label(
                info_frame,
                text=draft_info['filename'],
                bg=row_bg,
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 11, 'bold')
            )
            filename_label.pack(anchor='w', pady=(5, 0))
            
            # Team and mode info
            info_text = f"Team: {draft_info['user_team']} | "
            info_text += f"Mode: {'Manual' if draft_info['manual_mode'] else 'Normal'} | "
            info_text += f"Picks: {draft_info['total_picks']}"
            
            info_label = tk.Label(
                info_frame,
                text=info_text,
                bg=row_bg,
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 9)
            )
            info_label.pack(anchor='w')
            
            # View button
            view_btn = StyledButton(
                row,
                text="VIEW",
                command=lambda f=draft_info['filename']: self.view_draft_details(f),
                bg=DARK_THEME['button_bg'],
                font=(DARK_THEME['font_family'], 9),
                padx=15,
                pady=5
            )
            view_btn.pack(side='right', padx=10)
        
        # Close button
        close_btn = StyledButton(
            dialog,
            text="CLOSE",
            command=dialog.destroy,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11),
            padx=30,
            pady=10
        )
        close_btn.pack(pady=(0, 20))
    
    def view_draft_details(self, filename):
        """View details of a saved draft"""
        try:
            draft_data = self.draft_save_manager.load_draft(filename)
            
            # Create detail window
            detail_window = tk.Toplevel(self.root)
            detail_window.title(f"Draft Details - {filename}")
            detail_window.geometry("800x600")
            detail_window.configure(bg=DARK_THEME['bg_primary'])
            
            # Notebook for different views
            notebook = ttk.Notebook(detail_window)
            notebook.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Summary tab
            summary_frame = StyledFrame(notebook, bg_type='secondary')
            notebook.add(summary_frame, text="Summary")
            
            # Create summary text
            summary_text = tk.Text(
                summary_frame,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10),
                wrap='word',
                padx=10,
                pady=10
            )
            summary_text.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Add summary content
            summary = draft_data.get('summary', {})
            summary_content = f"Draft Date: {draft_data.get('timestamp', 'Unknown')}\n\n"
            
            if 'user_team' in summary:
                summary_content += f"Your Team: {summary['user_team']['name']}\n"
                summary_content += "Positions Drafted:\n"
                for pos, count in summary['user_team']['positions_drafted'].items():
                    summary_content += f"  {pos}: {count}\n"
                summary_content += "\n"
            
            summary_content += f"Total Rounds: {summary.get('total_rounds', 0)}\n\n"
            
            if summary.get('value_picks'):
                summary_content += "Best Value Picks:\n"
                for pick in summary['value_picks'][:5]:
                    summary_content += f"  Pick #{pick['pick']}: {pick['player']} (ADP {pick['adp']}, +{pick['value']} value)\n"
                summary_content += "\n"
            
            if summary.get('reach_picks'):
                summary_content += "Biggest Reaches:\n"
                for pick in summary['reach_picks'][:5]:
                    summary_content += f"  Pick #{pick['pick']}: {pick['player']} (ADP {pick['adp']}, -{pick['reach']} reach)\n"
            
            summary_text.insert('1.0', summary_content)
            summary_text.config(state='disabled')
            
            # Picks tab
            picks_frame = StyledFrame(notebook, bg_type='secondary')
            notebook.add(picks_frame, text="All Picks")
            
            # Create picks text
            picks_text = tk.Text(
                picks_frame,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_primary'],
                font=('Courier', 10),
                wrap='none',
                padx=10,
                pady=10
            )
            picks_scroll = tk.Scrollbar(picks_frame, command=picks_text.yview)
            picks_text.config(yscrollcommand=picks_scroll.set)
            
            picks_text.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
            picks_scroll.pack(side='right', fill='y', padx=(0, 10), pady=10)
            
            # Add picks content
            picks_content = "Pick  Round  Team                  Position  Player\n"
            picks_content += "-" * 70 + "\n"
            
            teams_dict = {t['id']: t['name'] for t in draft_data.get('teams', [])}
            
            for pick in draft_data.get('picks', []):
                team_name = teams_dict.get(pick['team_id'], 'Unknown')
                picks_content += f"{pick['pick_number']:>4}  {pick['round']:>5}.{pick['pick_in_round']:02d}  "
                picks_content += f"{team_name:<20}  {pick['player']['position']:<8}  "
                picks_content += f"{pick['player']['name']}\n"
            
            picks_text.insert('1.0', picks_content)
            picks_text.config(state='disabled')
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load draft details: {str(e)}",
                parent=self.root
            )
    
    def show_preset_dialog(self):
        """Show dialog for managing draft presets"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Draft Presets")
        dialog.geometry("600x500")
        dialog.configure(bg=DARK_THEME['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        header = tk.Label(
            dialog,
            text="Draft Presets",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        header.pack(pady=10)
        
        # Active preset display
        active_preset = self.draft_preset_manager.get_active_preset()
        active_name = self.draft_preset_manager.active_preset_name or "None"
        
        active_frame = StyledFrame(dialog, bg_type='secondary')
        active_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        active_label = tk.Label(
            active_frame,
            text=f"Active Preset: {active_name}",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11)
        )
        active_label.pack(pady=5)
        
        # Preset list
        list_frame = StyledFrame(dialog, bg_type='secondary')
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Listbox for presets
        listbox = tk.Listbox(
            list_frame,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            selectbackground=DARK_THEME['bg_secondary'],
            selectforeground=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            height=10
        )
        listbox.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Populate listbox
        preset_names = self.draft_preset_manager.list_preset_names()
        for name in preset_names:
            listbox.insert(tk.END, name)
        
        # Button frame
        button_frame = StyledFrame(dialog, bg_type='primary')
        button_frame.pack(fill='x', padx=20, pady=10)
        
        def activate_preset():
            selection = listbox.curselection()
            if selection:
                preset_name = listbox.get(selection[0])
                preset = self.draft_preset_manager.get_preset(preset_name)
                if preset:
                    preset.enabled = True
                    self.draft_preset_manager.create_preset(preset_name, preset)
                    self.draft_preset_manager.set_active_preset(preset_name)
                    active_label.config(text=f"Active Preset: {preset_name}")
                    messagebox.showinfo(
                        "Preset Activated",
                        f"'{preset_name}' is now active. Restart the draft to apply changes.",
                        parent=dialog
                    )
        
        def deactivate_preset():
            self.draft_preset_manager.set_active_preset(None)
            active_label.config(text="Active Preset: None")
            messagebox.showinfo(
                "Preset Deactivated",
                "No preset is active. Restart the draft to apply changes.",
                parent=dialog
            )
        
        def edit_preset():
            selection = listbox.curselection()
            if selection:
                preset_name = listbox.get(selection[0])
                preset = self.draft_preset_manager.get_preset(preset_name)
                if preset:
                    self.show_preset_editor(preset_name, preset, dialog)
        
        # Buttons
        activate_btn = StyledButton(
            button_frame,
            text="ACTIVATE",
            command=activate_preset,
            bg=DARK_THEME['button_active'],
            font=(DARK_THEME['font_family'], 10),
            padx=15,
            pady=5
        )
        activate_btn.pack(side='left', padx=5)
        
        deactivate_btn = StyledButton(
            button_frame,
            text="DEACTIVATE",
            command=deactivate_preset,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10),
            padx=15,
            pady=5
        )
        deactivate_btn.pack(side='left', padx=5)
        
        edit_btn = StyledButton(
            button_frame,
            text="EDIT",
            command=edit_preset,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10),
            padx=15,
            pady=5
        )
        edit_btn.pack(side='left', padx=5)
        
        # Close button
        close_btn = StyledButton(
            dialog,
            text="CLOSE",
            command=dialog.destroy,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11),
            padx=30,
            pady=10
        )
        close_btn.pack(pady=(0, 20))
    
    def show_preset_editor(self, preset_name, preset, parent_dialog):
        """Show preset editor dialog"""
        editor = tk.Toplevel(parent_dialog)
        editor.title(f"Edit Preset: {preset_name}")
        editor.geometry("500x600")
        editor.configure(bg=DARK_THEME['bg_primary'])
        editor.transient(parent_dialog)
        editor.grab_set()
        
        # Header
        header = tk.Label(
            editor,
            text=f"Editing: {preset_name}",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        header.pack(pady=10)
        
        # Draft order section
        order_label = tk.Label(
            editor,
            text="Draft Order (one name per line):",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10)
        )
        order_label.pack(pady=(10, 5))
        
        order_text = tk.Text(
            editor,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            height=12,
            width=40
        )
        order_text.pack(padx=20, pady=(0, 10))
        
        # Insert current draft order
        for name in preset.draft_order:
            order_text.insert(tk.END, name + '\n')
        
        # User position
        pos_frame = StyledFrame(editor, bg_type='secondary')
        pos_frame.pack(fill='x', padx=20, pady=10)
        
        pos_label = tk.Label(
            pos_frame,
            text=f"Your Position: {preset.user_position + 1} ({preset.draft_order[preset.user_position] if preset.user_position < len(preset.draft_order) else 'N/A'})",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10)
        )
        pos_label.pack(pady=5)
        
        # Exclusions section
        exc_label = tk.Label(
            editor,
            text="Player Exclusions:",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10)
        )
        exc_label.pack(pady=(10, 5))
        
        exc_text = tk.Text(
            editor,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            height=6,
            width=40
        )
        exc_text.pack(padx=20, pady=(0, 10))
        
        # Insert current exclusions
        for exc in preset.player_exclusions:
            if exc.enabled:
                exc_text.insert(tk.END, f"{exc.team_name}: {exc.player_name}\n")
        
        # Save button
        def save_preset():
            # Parse draft order
            draft_order = [line.strip() for line in order_text.get(1.0, tk.END).split('\n') if line.strip()]
            
            # Parse exclusions
            exclusions = []
            for line in exc_text.get(1.0, tk.END).split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        team_name = parts[0].strip()
                        player_name = parts[1].strip()
                        if team_name and player_name:
                            exclusions.append(PlayerExclusion(team_name, player_name, True))
            
            # Update preset
            preset.draft_order = draft_order
            preset.player_exclusions = exclusions
            
            # Save
            self.draft_preset_manager.create_preset(preset_name, preset)
            
            messagebox.showinfo(
                "Preset Saved",
                f"'{preset_name}' has been updated.",
                parent=editor
            )
            editor.destroy()
        
        save_btn = StyledButton(
            editor,
            text="SAVE",
            command=save_preset,
            bg=DARK_THEME['button_active'],
            font=(DARK_THEME['font_family'], 11),
            padx=30,
            pady=10
        )
        save_btn.pack(pady=(0, 20))


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
    
    # Configure Combobox for templates
    style.configure('TCombobox',
                   fieldbackground=DARK_THEME['bg_tertiary'],
                   background=DARK_THEME['bg_tertiary'],
                   foreground=DARK_THEME['text_primary'],
                   borderwidth=0,
                   arrowcolor=DARK_THEME['text_secondary'])
    style.map('TCombobox',
             fieldbackground=[('readonly', DARK_THEME['bg_tertiary'])],
             foreground=[('readonly', DARK_THEME['text_primary'])])
    
    MockDraftApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()