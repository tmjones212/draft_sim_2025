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
from src.services.draft_trade_service import DraftTradeService
from src.ui.trade_dialog import TradeDialog
# from src.services.draft_history_manager import DraftHistoryManager  # Removed - using templates


class MockDraftApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mock Draft Simulator 2025")
        # Optimized window size - wider for draft board and taller for better visibility
        self.root.geometry("1920x1080")
        self.root.configure(bg=DARK_THEME['bg_primary'])
        
        # Set minimum window size - reduced for better compatibility
        self.root.minsize(1400, 800)
        
        # Center the window on screen after UI loads
        self.root.after(100, self.center_window)
        
        # Initialize draft preset manager first (needed by _create_teams)
        self.draft_preset_manager = DraftPresetManager()
        # Always update/create the default preset to ensure latest configuration
        self.draft_preset_manager.create_default_preset()
        
        # Initialize draft trade service
        self.trade_service = DraftTradeService()
        
        # Add default trade between Eric and Johnson
        # Johnson (now slot 4, was slot 9) swaps 6th and 8th round picks with Eric (now slot 9, was slot 4)
        # Johnson gets Eric's 6th and 8th round picks
        # Eric gets Johnson's 6th and 8th round picks
        self.trade_service.add_trade(4, [6, 8], 9, [6, 8])  # Team IDs: Johnson is team 4, Eric is team 9
        
        # Initialize draft components
        self.teams = self._create_teams()
        self.draft_engine = DraftEngine(
            num_teams=config.num_teams,
            roster_spots=config.roster_spots,
            draft_type=config.draft_type,
            reversal_round=config.reversal_round,
            trade_service=self.trade_service
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
        self.cheat_sheet = None
        self._cheat_sheet_needs_sync = False
        
        # Template manager
        self.template_manager = TemplateManager()
        
        # Draft save manager
        self.draft_save_manager = DraftSaveManager()
        
        # Draft history manager for ongoing drafts
        # self.draft_history_manager = DraftHistoryManager()  # Removed - using templates
        
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
        
        # Initialize flags
        self.loading_draft = False
        
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
        
        # New Draft button
        self.new_draft_button = StyledButton(
            button_container,
            text="NEW DRAFT",
            command=self.start_new_draft,
            bg=DARK_THEME['button_active'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=20,
            pady=10
        )
        self.new_draft_button.pack(side='left', padx=(0, 10))
        
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
        
        # Trades button
        self.trades_button = StyledButton(
            button_container,
            text="TRADES",
            command=self.show_trades_dialog,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=20,
            pady=10
        )
        self.trades_button.pack(side='left', padx=(0, 10))
        
        # Update NFC ADP button
        self.update_nfc_button = StyledButton(
            button_container,
            text="UPDATE NFC ADP",
            command=self.update_nfc_adp,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=20,
            pady=10
        )
        self.update_nfc_button.pack(side='left', padx=(0, 10))
        
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
            text="VIEW/LOAD",
            command=self.load_template,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10),
            padx=15,
            pady=8,
            state='normal'  # Always enabled to allow viewing
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
            image_service=self.image_service,
            on_draft_name_change=self.on_draft_name_change,
            trade_service=self.trade_service,
            # on_draft_load removed - using templates instead
            get_draft_list=self.get_draft_list
        )
        self.draft_board.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Roster panel (narrow)
        roster_panel = StyledFrame(top_frame, bg_type='secondary')
        roster_panel.grid(row=0, column=1, sticky='nsew')
        
        self.roster_view = RosterView(roster_panel, self.teams)
        self.roster_view.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Bottom section - Available players
        player_panel = StyledFrame(paned_window, bg_type='secondary')
        
        self.player_list = PlayerList(player_panel, on_draft=self.draft_player, on_adp_change=self.on_adp_change, image_service=self.image_service, parent_app=self)
        self.player_list.pack(fill='both', expand=True, padx=10, pady=10)
        self.player_list.set_preset_manager(self.draft_preset_manager)
        
        # Apply custom rankings if they were already loaded
        if hasattr(self, 'custom_rankings') and hasattr(self, 'player_tiers'):
            self.player_list.set_custom_rankings(self.custom_rankings, self.player_tiers)
        
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
            
            # If force refresh, rebuild the drafted players set
            if force_refresh:
                self.player_list.drafted_players.clear()
                for pick in self.draft_engine.draft_results:
                    if hasattr(pick.player, 'player_id'):
                        self.player_list.drafted_players.add(pick.player)
            
            self.player_list.update_players(self.available_players, force_refresh=force_refresh)
            # Update draft button states based on mode
            self.player_list.set_draft_enabled(self.manual_mode or self.user_team_id is not None)
        
        # Always update draft board with just the last pick
        self.draft_board.update_picks(
            self.draft_engine.get_draft_results(),
            pick_num
        )
        
        # Update position counts display
        self.roster_view.update_position_counts(self.draft_engine.get_draft_results())
        
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
        
        # Don't auto-start draft session until we have 10 picks
        # This prevents empty drafts from being saved
        
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
        # Get current pick info
        current_pick, current_round, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
        current_team = self.teams[team_on_clock]
        
        try:
            # First make the pick in the engine
            self.draft_engine.make_pick(current_team, player)
            
            # Remove from available players list
            if player in self.available_players:
                self.available_players.remove(player)
            
            # Update player pool service
            if self.player_pool:
                self.player_pool.draft_player(player)
            
            # Remove player from UI immediately
            self._remove_drafted_player(player)
            
            # Update draft board immediately
            pick_info = self.draft_engine.get_current_pick_info()
            self.draft_board.update_picks(
                self.draft_engine.get_draft_results(),
                pick_info[0]
            )
            
            # Update roster view to show the new pick
            self.roster_view.update_roster_display()
            
            # Update position counts
            self.roster_view.update_position_counts(self.draft_engine.get_draft_results())
            
            # Update draft history if it exists
            if self.draft_history:
                last_pick = self.draft_engine.draft_results[-1]
                self.draft_history.add_pick(last_pick)
            
            
            # Schedule auto-draft to run immediately
            self.root.after(1, self.check_auto_draft)
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
        # Don't auto-draft while loading a saved draft
        if hasattr(self, 'loading_draft') and self.loading_draft:
            return
            
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
        # Don't auto-draft while loading a saved draft
        if hasattr(self, 'loading_draft') and self.loading_draft:
            return
            
        picks_made = []
        
        # Pre-calculate all picks in a batch for speed
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
        
        # Batch update everything at once for better performance
        if picks_made:
            # Remove all auto-drafted players from the UI in one batch
            players_to_remove = [player for _, _, player in picks_made]
            self.player_list.remove_players(players_to_remove, force_refresh=False)
            
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
            
            # Get final pick info
            pick_num, round_num, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
            is_user_turn = self.user_team_id and team_on_clock == self.user_team_id
            
            # Update draft board once
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
            
            # Update roster view once
            self.roster_view.update_roster_display()
            
            # Update position counts
            self.roster_view.update_position_counts(self.draft_engine.get_draft_results())
    
    def _select_computer_pick(self, team, pick_num):
        """Select a player for computer team based on smart drafting logic"""
        # Check preset exclusions first
        active_preset = self.draft_preset_manager.get_active_preset()
        
        # Calculate current round for round restrictions
        current_round = ((pick_num - 1) // config.num_teams) + 1
        
        # Check for forced picks first
        if active_preset:
            forced_player_name = active_preset.get_forced_pick(team.name, pick_num)
            if forced_player_name:
                # Find and return the forced player
                for player in self.available_players:
                    if format_name(player.name).upper() == forced_player_name.upper():
                        return player
        
        # Special logic for Luan in round 3 (pick 21)
        if team.name.upper() == "LUAN" and pick_num == 21:
            # Priority order: DRAKE LONDON > DERRICK HENRY > CHASE BROWN > any QB (NOT McBride)
            priority_players = [
                "DRAKE LONDON",
                "DERRICK HENRY", 
                "CHASE BROWN"
            ]
            
            # Check for priority players first
            for priority_name in priority_players:
                for player in self.available_players:
                    if format_name(player.name).upper() == priority_name:
                        # 90% chance to take the priority player if available
                        if random.random() < 0.9:
                            return player
            
            # If none of the priority players are available or random didn't select them,
            # look for any QB with 70% chance
            for player in self.available_players[:15]:  # Look at top 15 available
                if player.position == 'QB' and random.random() < 0.7:
                    return player
        
        # Quick path for very early picks
        if pick_num <= 3:
            # Check preset exclusions and round restrictions even for early picks
            for player in self.available_players:
                if active_preset and active_preset.is_player_excluded(team.name, player.name):
                    continue  # Skip excluded player
                if active_preset and active_preset.is_player_restricted(team.name, player.name, current_round):
                    continue  # Skip round-restricted player
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
            
            # Check round restrictions
            if active_preset and active_preset.is_player_restricted(team.name, player.name, current_round):
                continue  # Skip round-restricted player
            
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
                # Check round restrictions even in fallback
                if active_preset and active_preset.is_player_restricted(team.name, player.name, current_round):
                    continue  # Skip round-restricted player
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
    
    def load_cheat_sheet_tiers(self):
        """Load cheat sheet tiers and build custom rankings"""
        import os
        import json
        
        # Use absolute path to ensure consistency
        # main.py is at project root, so just use dirname once
        base_dir = os.path.dirname(__file__)
        tier_file = os.path.join(base_dir, 'data', 'cheat_sheet_tiers.json')
        
        custom_rankings = {}
        player_tiers = {}
        
        if os.path.exists(tier_file):
            try:
                with open(tier_file, 'r') as f:
                    tiers = json.load(f)
                    
                overall_rank = 1
                
                # EXACTLY match cheat sheet's notify_rankings_update logic
                # Process Tier tiers first (none will exist in default file)
                for tier_num in range(1, 16):
                    tier_name = f"Tier {tier_num}"
                    if tier_name in tiers:
                        players_in_tier = tiers[tier_name]
                        for player_id in players_in_tier:
                            custom_rankings[player_id] = overall_rank
                            player_tiers[player_id] = tier_num
                            overall_rank += 1
                
                # Then process Round tiers (this is what our default file has)
                for round_num in range(1, 16):
                    round_name = f"Round {round_num}"
                    if round_name in tiers:
                        players_in_round = tiers[round_name]
                        for player_id in players_in_round:
                            if player_id not in custom_rankings:  # Don't override
                                custom_rankings[player_id] = overall_rank
                                player_tiers[player_id] = 0  # Match cheat sheet: 0 for round-based
                                overall_rank += 1
                
                self.custom_rankings = custom_rankings
                self.player_tiers = player_tiers
                
                # Update player list if it exists
                if hasattr(self, 'player_list'):
                    self.player_list.set_custom_rankings(custom_rankings, player_tiers)
                    
            except Exception as e:
                print(f"Error loading cheat sheet tiers: {e}")
                self.custom_rankings = {}
                self.player_tiers = {}
        else:
            # No saved tiers - create default rankings based on ADP
            self._create_default_custom_rankings()
    
    def _create_default_custom_rankings(self):
        """Create default custom rankings based on ADP when no tiers file exists"""
        if not hasattr(self, 'all_players') or not self.all_players:
            self.custom_rankings = {}
            self.player_tiers = {}
            return
        
        import os
        import json
        
        # Create default tiers structure matching cheat sheet
        tiers = {}
        for i in range(1, 16):
            tiers[f"Round {i}"] = []
        
        # Sort players by ADP and assign to rounds
        sorted_players = sorted(self.all_players, key=lambda p: p.adp if p.adp else 999)
        
        players_per_round = 12
        for i, player in enumerate(sorted_players[:180]):  # 15 rounds * 12 teams
            round_num = (i // players_per_round) + 1
            if round_num <= 15:
                round_key = f"Round {round_num}"
                tiers[round_key].append(player.player_id)
        
        # Save the default tiers file
        # main.py is at project root
        base_dir = os.path.dirname(__file__)
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        tier_file = os.path.join(data_dir, 'cheat_sheet_tiers.json')
        
        try:
            with open(tier_file, 'w') as f:
                json.dump(tiers, f, indent=2)
            print(f"Created default cheat sheet tiers at {tier_file}")
        except Exception as e:
            print(f"Error creating default tiers: {e}")
        
        # Process the tiers using EXACT same logic as load_cheat_sheet_tiers
        custom_rankings = {}
        player_tiers = {}
        overall_rank = 1
        
        # Process Tier tiers first (won't exist in default)
        for tier_num in range(1, 16):
            tier_name = f"Tier {tier_num}"
            if tier_name in tiers:
                players_in_tier = tiers[tier_name]
                for player_id in players_in_tier:
                    custom_rankings[player_id] = overall_rank
                    player_tiers[player_id] = tier_num
                    overall_rank += 1
        
        # Then process Round tiers
        for round_num in range(1, 16):
            round_name = f"Round {round_num}"
            if round_name in tiers:
                players_in_round = tiers[round_name]
                for player_id in players_in_round:
                    if player_id not in custom_rankings:
                        custom_rankings[player_id] = overall_rank
                        player_tiers[player_id] = 0  # 0 for round-based, matching cheat sheet
                        overall_rank += 1
        
        self.custom_rankings = custom_rankings
        self.player_tiers = player_tiers
        
        # Update player list if it exists
        if hasattr(self, 'player_list'):
            self.player_list.set_custom_rankings(custom_rankings, player_tiers)
    
    def on_cheat_sheet_update(self, custom_rankings, player_tiers):
        """Called when cheat sheet rankings are updated"""
        self.custom_rankings = custom_rankings
        self.player_tiers = player_tiers
        
        # Update player list to show custom rankings
        if hasattr(self, 'player_list'):
            self.player_list.set_custom_rankings(custom_rankings, player_tiers)
            # Don't do a full refresh - just update the CR column if needed
            if self.player_list.sort_by == 'custom_rank':
                # Only if actively sorting by custom rank, do a refresh
                self.player_list.update_players(self.available_players)
            # Otherwise, don't refresh at all - the CR column will update next time the list refreshes
    
    def on_adp_change(self):
        """Called when ADP values are changed via UI"""
        # Re-sort available players by ADP to maintain proper draft order
        self.available_players.sort(key=lambda p: p.adp if p.adp else 999)
        
        # Mark that ADP has changed and needs refresh
        self._adp_needs_refresh = True
        
        # If we're currently on the Draft tab, refresh immediately
        if hasattr(self, 'notebook') and self.notebook.tab('current')['text'] == 'Draft':
            if hasattr(self, 'player_list') and self.player_list:
                self.player_list.update_players(self.available_players, force_refresh=True)
                self._adp_needs_refresh = False
    
    def update_nfc_adp(self):
        """Fetch and update NFC ADP data"""
        try:
            from tkinter import messagebox
            
            # Update NFC ADP data via player list
            if hasattr(self, 'player_list') and self.player_list:
                success = self.player_list.update_nfc_adp()
                
                if success:
                    messagebox.showinfo(
                        "NFC ADP Updated",
                        "Successfully updated NFC ADP data from the last 10 days.",
                        parent=self.root
                    )
                else:
                    messagebox.showwarning(
                        "Update Failed",
                        "Failed to fetch NFC ADP data. Please check your internet connection.",
                        parent=self.root
                    )
            else:
                messagebox.showwarning(
                    "Not Ready",
                    "Please wait for players to load before updating NFC ADP.",
                    parent=self.root
                )
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                f"An error occurred while updating NFC ADP: {str(e)}",
                parent=self.root
            )
    
    def start_new_draft(self):
        """Start a completely new draft - clear everything"""
        # Confirm with user
        if self.draft_engine.draft_results:
            result = messagebox.askyesno(
                "Start New Draft",
                "Are you sure you want to start a new draft? Current draft will be saved in history.",
                parent=self.root
            )
            if not result:
                return
        
        # Clear user team selection BEFORE restarting draft to prevent auto-drafting
        self.user_team_id = None
        self.manual_mode = False
        
        # Reset everything (with skip_confirmation=True since we already asked)
        self.restart_draft(skip_confirmation=True)
        
        # Clear draft name
        self.draft_board.set_draft_name("")
        
        # Reset UI elements
        self.draft_board.selected_team_id = None
        self.draft_board.stop_glow_animation()
        self.draft_board.start_glow_animation()
        
        # Update team buttons to show "Sit" again
        for team_id, button in self.draft_board.team_buttons.items():
            button.config(
                text="Sit",
                bg=DARK_THEME['button_bg']
            )
        
        # Show draft spot banner
        self.draft_spot_banner.pack(fill='x', pady=(10, 0))
        
        # Disable draft button
        self.draft_button.config(state='disabled', bg=DARK_THEME['button_disabled'])
        
        # Disable player draft buttons
        # Disable draft buttons if the method exists
        if hasattr(self.player_list, 'disable_draft_buttons'):
            self.player_list.disable_draft_buttons()
    
    def restart_draft(self, skip_confirmation=False):
        """Reset the draft but keep user team selection
        
        Args:
            skip_confirmation: If True, skip the confirmation dialog
        """
        # Ask for confirmation unless skipped
        if not skip_confirmation:
            if not messagebox.askyesno("Restart Draft", "Are you sure you want to restart the draft?"):
                return
        
        # Save current user team selection (only save if not None, to allow start_new_draft to clear it)
        saved_user_team = self.user_team_id
        
        # Reset draft saved flag
        self._draft_saved = False
        
        # Reset teams
        self.teams = self._create_teams()
        
        # Reset draft engine (keep trade service)
        self.draft_engine = DraftEngine(
            num_teams=config.num_teams,
            roster_spots=config.roster_spots,
            draft_type=config.draft_type,
            reversal_round=config.reversal_round,
            trade_service=self.trade_service
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
        
        # Only start a new draft session if we're not loading a draft
        if not hasattr(self, 'loading_draft') or not self.loading_draft:
            pass  # Draft history removed - using templates
        
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
        
        # Start auto-drafting from the beginning if needed (only if user has a team selected)
        if self.user_team_id is not None:
            self.check_auto_draft()
    
    def repick_spot(self):
        """Reset the draft and clear user team selection to allow repicking"""
        # Reset teams
        self.teams = self._create_teams()
        
        # Reset draft engine (keep trade service)
        self.draft_engine = DraftEngine(
            num_teams=config.num_teams,
            roster_spots=config.roster_spots,
            draft_type=config.draft_type,
            reversal_round=config.reversal_round,
            trade_service=self.trade_service
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
        
        # Update roster view to reflect the change
        self.roster_view.update_roster_display()
        
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
        
        # Update roster view to show restored state
        self.roster_view.update_roster_display()
        
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
        
        # Update draft history to remove reverted picks
        # self.draft_history_manager.remove_picks_after(target_pick_number - 1)  # Removed
        
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
        
        # Clear drafted players set and update player list
        self.player_list.drafted_players.clear()
        # Add back the players that are still drafted after reversion
        for pick in self.draft_engine.draft_results:
            if hasattr(pick.player, 'player_id'):
                self.player_list.drafted_players.add(pick.player)
        
        # Update player list once
        self.player_list.update_players(self.available_players, force_refresh=True)
        
        # Update star icons
        self.player_list._update_star_icons()
        
        # Update roster view to reflect the reverted state
        self.roster_view.update_roster_display()
        
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
        
        # Only start a new draft session if we're not loading a draft
        if not hasattr(self, 'loading_draft') or not self.loading_draft:
            pass  # Draft history removed - using templates
        
        # Remove loading label
        if hasattr(self, 'loading_label'):
            self.loading_label.destroy()
        
        # Load cheat sheet tiers to populate CR column
        self.load_cheat_sheet_tiers()
        
        # Update display with loaded players (only if UI is ready)
        if hasattr(self, 'player_list'):
            # Force refresh to ensure custom rankings are displayed
            self.update_display(full_update=True, force_refresh=True)
        
        # Check if preset should set user team (only if UI is ready)
        if hasattr(self, 'draft_board'):
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
                            if hasattr(self, 'draft_spot_banner'):
                                self.draft_spot_banner.pack_forget()
                            break
        
        # Don't auto-draft immediately - wait for user to select a team
        # Only show a message prompting user to select a team
        if hasattr(self, 'status_label') and not self.user_team_id:
            self.status_label.config(text="Select a team to control")
            if hasattr(self, 'on_clock_label'):
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
                    on_adp_change=self.on_adp_change,
                    player_list_ref=self.player_list
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
            if hasattr(self, 'cheat_sheet') and self.cheat_sheet and hasattr(self, 'player_list'):
                self.player_list.set_cheat_sheet_ref(self.cheat_sheet)
            
            if hasattr(self, '_cheat_sheet_needs_sync') and self._cheat_sheet_needs_sync and hasattr(self, 'cheat_sheet') and self.cheat_sheet:
                # Sync rankings when switching back to draft tab
                self._cheat_sheet_needs_sync = False
                # Update the display to show updated rounds
                if hasattr(self, 'player_list'):
                    self.player_list.update_table_view()
            
            # Check if ADP was changed in ADP tab and needs refresh
            if hasattr(self, '_adp_needs_refresh') and self._adp_needs_refresh:
                self._adp_needs_refresh = False
                if hasattr(self, 'player_list') and self.player_list:
                    self.player_list.update_players(self.available_players, force_refresh=True)
    
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
        # Enable delete button when template is selected (load button is always enabled)
        if self.template_var.get():
            self.delete_template_button.config(state='normal')
        else:
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
                watch_list=watch_list,
                trade_service=self.trade_service
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
    
    def show_template_viewer(self, filter_player=None):
        """Show dialog with all templates and their team rosters
        
        Args:
            filter_player: Optional player to filter templates by (only show templates with this player drafted)
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Template Viewer")
        dialog.geometry("1400x900")
        dialog.configure(bg=DARK_THEME['bg_primary'])
        
        # Center dialog on parent
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog on parent window
        dialog.update_idletasks()
        x = (self.root.winfo_x() + (self.root.winfo_width() // 2) - 700)
        y = (self.root.winfo_y() + (self.root.winfo_height() // 2) - 450)
        dialog.geometry(f"1400x900+{x}+{y}")
        
        # Main container with padding
        main_frame = tk.Frame(dialog, bg=DARK_THEME['bg_primary'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create notebook for different views
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)
        
        # Tab 1: Template List View
        list_view_frame = tk.Frame(notebook, bg=DARK_THEME['bg_primary'])
        notebook.add(list_view_frame, text="Template List")
        
        # Tab 2: Side-by-Side Comparison
        comparison_frame = tk.Frame(notebook, bg=DARK_THEME['bg_primary'])
        notebook.add(comparison_frame, text="Compare Templates")
        
        # Title for list view
        if filter_player:
            title_text = f"Templates where you drafted {filter_player.name} - Click to preview, Double-click to load"
        else:
            title_text = "Template Viewer - Drag to reorder, Click to preview, Double-click to load"
        
        title_label = tk.Label(
            list_view_frame,
            text=title_text,
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        title_label.pack(pady=(10, 5))
        
        # Add filter controls
        filter_frame = tk.Frame(list_view_frame, bg=DARK_THEME['bg_primary'])
        filter_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Position filter
        tk.Label(
            filter_frame,
            text="Filter by early picks:",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        ).pack(side='left', padx=(0, 10))
        
        filter_var = tk.StringVar(value="All")
        filter_options = [
            "All",
            "R1 RB", "R1 WR", "R1 TE", "R1 QB",
            "RB-RB (R1-2)", "WR-WR (R1-2)", "RB-WR (R1-2)", "WR-RB (R1-2)",
            "3 RBs (R1-3)", "3 WRs (R1-3)", "Zero RB (R1-3)"
        ]
        
        filter_menu = ttk.Combobox(
            filter_frame,
            textvariable=filter_var,
            values=filter_options,
            state='readonly',
            width=20
        )
        filter_menu.pack(side='left')
        
        # Clear filter button
        clear_filter_btn = tk.Button(
            filter_frame,
            text="Clear Filter",
            bg=DARK_THEME['button_bg'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 9),
            command=lambda: filter_var.set("All"),
            activebackground=DARK_THEME['button_active'],
            borderwidth=0,
            padx=10,
            pady=3
        )
        clear_filter_btn.pack(side='left', padx=10)
        
        # Create paned window for template list and team view
        paned = tk.PanedWindow(
            list_view_frame,
            orient='horizontal',
            bg=DARK_THEME['bg_secondary'],
            sashwidth=8,
            showhandle=False
        )
        paned.pack(fill='both', expand=True)
        
        # Left side - Template list
        left_frame = tk.Frame(paned, bg=DARK_THEME['bg_secondary'])
        paned.add(left_frame, minsize=350)
        
        # Template list header
        list_header = tk.Label(
            left_frame,
            text="Available Templates",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        list_header.pack(pady=(10, 5))
        
        # Template listbox with scrollbar (with drag-and-drop support)
        list_container = tk.Frame(left_frame, bg=DARK_THEME['bg_secondary'])
        list_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(list_container, bg=DARK_THEME['bg_tertiary'])
        scrollbar.pack(side='right', fill='y')
        
        template_listbox = tk.Listbox(
            list_container,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11),
            selectmode='single',
            yscrollcommand=scrollbar.set,
            highlightthickness=0,
            selectbackground=DARK_THEME['button_active'],
            selectforeground=DARK_THEME['text_primary']
        )
        template_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=template_listbox.yview)
        
        # Variables for drag-and-drop
        drag_start_index = None
        template_order = []  # Store template order
        
        # Right side - Team roster view and notes
        right_frame = tk.Frame(paned, bg=DARK_THEME['bg_secondary'])
        paned.add(right_frame, minsize=700)
        
        # Create vertical paned window for roster and notes
        right_paned = tk.PanedWindow(
            right_frame,
            orient='vertical',
            bg=DARK_THEME['bg_secondary'],
            sashwidth=8,
            showhandle=False
        )
        right_paned.pack(fill='both', expand=True)
        
        # Top frame for roster
        roster_frame = tk.Frame(right_paned, bg=DARK_THEME['bg_secondary'])
        right_paned.add(roster_frame, minsize=350)
        
        # Team roster header
        roster_header = tk.Label(
            roster_frame,
            text="Your Team in Selected Template",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        roster_header.pack(pady=(10, 5))
        
        # Roster display area with scrollbar
        roster_container = tk.Frame(roster_frame, bg=DARK_THEME['bg_secondary'])
        roster_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        roster_scroll = tk.Scrollbar(roster_container, bg=DARK_THEME['bg_tertiary'])
        roster_scroll.pack(side='right', fill='y')
        
        roster_text = tk.Text(
            roster_container,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            wrap='word',
            yscrollcommand=roster_scroll.set,
            state='disabled',
            height=25
        )
        roster_text.pack(side='left', fill='both', expand=True)
        roster_scroll.config(command=roster_text.yview)
        
        # Bottom frame for notes
        notes_frame = tk.Frame(right_paned, bg=DARK_THEME['bg_secondary'])
        right_paned.add(notes_frame, minsize=150)
        
        # Notes header with save button
        notes_header_frame = tk.Frame(notes_frame, bg=DARK_THEME['bg_secondary'])
        notes_header_frame.pack(fill='x', pady=(10, 5), padx=10)
        
        notes_header = tk.Label(
            notes_header_frame,
            text="Template Notes",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        notes_header.pack(side='left')
        
        save_notes_btn = tk.Button(
            notes_header_frame,
            text="Save Notes",
            bg=DARK_THEME['button_bg'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 9),
            command=lambda: save_notes(),
            activebackground=DARK_THEME['button_active'],
            borderwidth=0,
            padx=10,
            pady=3
        )
        save_notes_btn.pack(side='right')
        
        # Notes text area
        notes_container = tk.Frame(notes_frame, bg=DARK_THEME['bg_secondary'])
        notes_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        notes_scroll = tk.Scrollbar(notes_container, bg=DARK_THEME['bg_tertiary'])
        notes_scroll.pack(side='right', fill='y')
        
        notes_text = tk.Text(
            notes_container,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            wrap='word',
            yscrollcommand=notes_scroll.set,
            height=8
        )
        notes_text.pack(side='left', fill='both', expand=True)
        notes_scroll.config(command=notes_text.yview)
        
        # Store template data
        templates = self.template_manager.list_templates()
        template_data = {}
        template_metadata = {}  # Store extra info about templates
        current_template_filename = None
        
        def check_template_filter(template, filter_type):
            """Check if template matches the selected filter"""
            if filter_type == "All":
                return True
            
            user_team_id = template.user_settings.get('user_team_id')
            
            # Get player data
            player_dict = {p['player_id']: p for p in template.player_pool['all_players']}
            
            # Get user's first 3 picks
            user_picks = []
            for pick in template.draft_results:
                if pick['team_id'] == user_team_id and pick['player_id']:
                    if pick['player_id'] in player_dict:
                        p = player_dict[pick['player_id']]
                        user_picks.append({
                            'round': pick['round'],
                            'position': p['position'],
                            'name': p['name']
                        })
                    if len(user_picks) >= 3:
                        break
            
            if not user_picks:
                return False
            
            # Check filters
            if filter_type == "R1 RB":
                return len(user_picks) > 0 and user_picks[0]['round'] == 1 and user_picks[0]['position'] == 'RB'
            elif filter_type == "R1 WR":
                return len(user_picks) > 0 and user_picks[0]['round'] == 1 and user_picks[0]['position'] == 'WR'
            elif filter_type == "R1 TE":
                return len(user_picks) > 0 and user_picks[0]['round'] == 1 and user_picks[0]['position'] == 'TE'
            elif filter_type == "R1 QB":
                return len(user_picks) > 0 and user_picks[0]['round'] == 1 and user_picks[0]['position'] == 'QB'
            elif filter_type == "RB-RB (R1-2)":
                return (len(user_picks) >= 2 and 
                       user_picks[0]['position'] == 'RB' and 
                       user_picks[1]['position'] == 'RB')
            elif filter_type == "WR-WR (R1-2)":
                return (len(user_picks) >= 2 and 
                       user_picks[0]['position'] == 'WR' and 
                       user_picks[1]['position'] == 'WR')
            elif filter_type == "RB-WR (R1-2)":
                return (len(user_picks) >= 2 and 
                       user_picks[0]['position'] == 'RB' and 
                       user_picks[1]['position'] == 'WR')
            elif filter_type == "WR-RB (R1-2)":
                return (len(user_picks) >= 2 and 
                       user_picks[0]['position'] == 'WR' and 
                       user_picks[1]['position'] == 'RB')
            elif filter_type == "3 RBs (R1-3)":
                rb_count = sum(1 for p in user_picks[:3] if p['position'] == 'RB')
                return rb_count == 3
            elif filter_type == "3 WRs (R1-3)":
                wr_count = sum(1 for p in user_picks[:3] if p['position'] == 'WR')
                return wr_count == 3
            elif filter_type == "Zero RB (R1-3)":
                rb_count = sum(1 for p in user_picks[:3] if p['position'] == 'RB')
                return rb_count == 0
            
            return False
        
        def load_templates_to_list():
            """Load templates into the listbox based on current filter"""
            nonlocal template_order
            
            # Clear listbox
            template_listbox.delete(0, 'end')
            
            # Get current filter
            current_filter = filter_var.get()
            
            # Load templates
            templates_found = 0
            temp_list = []
            
            for t in templates:
                # Load template data
                template = self.template_manager.load_template(t['filename'])
                if template:
                    should_include = True
                    
                    # Check if we should filter by player
                    if filter_player and filter_player.player_id:
                        # Get the user's team ID from this template
                        user_team_id = template.user_settings.get('user_team_id')
                        
                        # Check if this player was drafted BY THE USER in this template
                        player_on_user_team = False
                        target_id = str(filter_player.player_id)
                        
                        # Check all draft picks by the user's team
                        for pick in template.draft_results:
                            # Only check picks made by the user's team
                            if pick.get('team_id') == user_team_id and pick.get('player_id'):
                                if str(pick['player_id']) == target_id:
                                    player_on_user_team = True
                                    break
                        
                        should_include = player_on_user_team
                    
                    # Apply position filter
                    if should_include and current_filter != "All":
                        should_include = check_template_filter(template, current_filter)
                    
                    if should_include:
                        template_data[t['name']] = template
                        template_metadata[t['name']] = t
                        temp_list.append(t['name'])
                        templates_found += 1
            
            # Use saved order if available, otherwise alphabetical
            if template_order:
                # Reorder based on saved order
                ordered_list = []
                for name in template_order:
                    if name in temp_list:
                        ordered_list.append(name)
                # Add any new templates not in order
                for name in temp_list:
                    if name not in ordered_list:
                        ordered_list.append(name)
                temp_list = ordered_list
            else:
                template_order = temp_list[:]
            
            # Populate listbox with grade info
            for name in temp_list:
                template = template_data.get(name)
                if template and template.grade:
                    # Add grade to display
                    display_name = f"{name} [Grade: {template.grade}]"
                else:
                    display_name = name
                template_listbox.insert('end', display_name)
            
            return templates_found
        
        # Load templates initially
        templates_found = load_templates_to_list()
        
        # Show appropriate message based on results
        if templates_found == 0:
            if filter_player:
                template_listbox.insert('end', f'No templates where you drafted {filter_player.name}')
                template_listbox.insert('end', '')
                template_listbox.insert('end', 'This player is either:')
                template_listbox.insert('end', '  • Not on your team in any saved template')
                template_listbox.insert('end', '  • Drafted by other teams')
            else:
                template_listbox.insert('end', 'No saved templates found')
                template_listbox.insert('end', '')
                template_listbox.insert('end', 'Save a template using the')
                template_listbox.insert('end', 'Save Template button to see it here')
        
        def on_template_select(event=None):
            """Display selected template's team roster and notes"""
            nonlocal current_template_filename
            
            selection = template_listbox.curselection()
            if not selection:
                return
            
            display_name = template_listbox.get(selection[0])
            # Extract template name (remove grade suffix if present)
            if ' [Grade:' in display_name:
                template_name = display_name.split(' [Grade:')[0]
            else:
                template_name = display_name
            template = template_data.get(template_name)
            
            # Get the filename for this template
            current_template_filename = None
            for t in templates:
                if t['name'] == template_name:
                    current_template_filename = t['filename']
                    break
            
            if not template:
                return
            
            # Get user team ID from template
            user_team_id = template.user_settings.get('user_team_id', 0)
            
            # Clear and update roster display
            roster_text.config(state='normal')
            roster_text.delete('1.0', 'end')
            
            # Get team data
            team_data = template.team_states.get(str(user_team_id))
            
            if team_data:
                roster_text.insert('end', f"Team: {team_data['name']}\n\n", 'header')
                
                # Get player data
                player_dict = {p['player_id']: p for p in template.player_pool['all_players']}
                
                # Show players in draft order by looking at draft results
                roster_text.insert('end', "Your Picks (in draft order):\n\n", 'subheader')
                
                player_count = 0
                for pick in template.draft_results:
                    # Check if this pick belongs to the user's team
                    if pick['team_id'] == user_team_id and pick['player_id']:
                        if pick['player_id'] in player_dict:
                            player_count += 1
                            p = player_dict[pick['player_id']]
                            
                            # Format: Round.Pick - Player Name (POS) - Team - ADP
                            round_num = pick['round']
                            pick_in_round = pick['pick_in_round']
                            
                            pick_info = f"{round_num}.{pick_in_round:02d}"
                            player_info = f"{pick_info} - {p['name']} ({p['position']}) - {p['team']}"
                            if p.get('adp'):
                                player_info += f" (ADP: {p['adp']:.0f})"
                            
                            roster_text.insert('end', f"{player_info}\n", 'player')
                
                if player_count == 0:
                    roster_text.insert('end', "No players drafted yet.\n", 'player')
                
                # Show draft info
                current_pick = template.draft_config.get('current_pick', {})
                if current_pick:
                    roster_text.insert('end', f"\n\nDraft Status:\n", 'position')
                    roster_text.insert('end', f"  Round {current_pick.get('round', 0)}, "
                                             f"Pick {current_pick.get('pick_in_round', 0)}\n", 'player')
                    roster_text.insert('end', f"  Overall Pick #{current_pick.get('pick_number', 0)}\n", 'player')
            else:
                roster_text.insert('end', "No team data found in this template.\n")
            
            # Configure text tags for styling
            roster_text.tag_config('header', font=(DARK_THEME['font_family'], 12, 'bold'),
                                 foreground=DARK_THEME['text_primary'])
            roster_text.tag_config('subheader', font=(DARK_THEME['font_family'], 11, 'bold'),
                                 foreground=DARK_THEME['button_active'])
            roster_text.tag_config('player', font=(DARK_THEME['font_family'], 10),
                                 foreground=DARK_THEME['text_primary'])
            
            roster_text.config(state='disabled')
            
            # Display notes
            notes_text.delete('1.0', 'end')
            if template:
                notes_text.insert('1.0', template.notes)
        
        # Function to save notes
        def save_notes():
            if current_template_filename:
                notes_content = notes_text.get('1.0', 'end-1c')
                if self.template_manager.update_template_notes(current_template_filename, notes_content):
                    # Update the template data in memory
                    selection = template_listbox.curselection()
                    if selection:
                        display_name = template_listbox.get(selection[0])
                        # Extract template name (remove grade suffix if present)
                        if ' [Grade:' in display_name:
                            template_name = display_name.split(' [Grade:')[0]
                        else:
                            template_name = display_name
                        if template_name in template_data:
                            template_data[template_name].notes = notes_content
                    messagebox.showinfo("Success", "Notes saved successfully")
                else:
                    messagebox.showerror("Error", "Failed to save notes")
            else:
                messagebox.showwarning("No Selection", "Please select a template first")
        
        # Bind selection event
        template_listbox.bind('<<ListboxSelect>>', on_template_select)
        
        # Bind filter change
        def on_filter_change(*args):
            load_templates_to_list()
            # Auto-select first if available
            if template_listbox.size() > 0:
                template_listbox.selection_set(0)
                on_template_select()
        
        filter_var.trace_add('write', on_filter_change)
        
        # Add drag-and-drop functionality
        def on_drag_start(event):
            nonlocal drag_start_index
            # Get the index of the item under the cursor
            drag_start_index = template_listbox.nearest(event.y)
            template_listbox.selection_clear(0, 'end')
            template_listbox.selection_set(drag_start_index)
        
        def on_drag_motion(event):
            if drag_start_index is None:
                return
            
            # Get current position
            current_index = template_listbox.nearest(event.y)
            
            # Visual feedback - highlight the position
            template_listbox.selection_clear(0, 'end')
            template_listbox.selection_set(current_index)
        
        def on_drag_release(event):
            nonlocal drag_start_index, template_order
            
            if drag_start_index is None:
                return
            
            # Get the index where we're dropping
            drop_index = template_listbox.nearest(event.y)
            
            if drag_start_index != drop_index:
                # Get the item being moved
                item = template_listbox.get(drag_start_index)
                
                # Update template_order
                template_order.pop(drag_start_index)
                template_order.insert(drop_index, item)
                
                # Save order to file
                save_template_order()
                
                # Refresh the list
                load_templates_to_list()
                
                # Re-select the moved item
                template_listbox.selection_set(drop_index)
                on_template_select()
            
            drag_start_index = None
        
        def save_template_order():
            """Save template order to a file"""
            import json
            import os
            
            order_file = os.path.join(
                os.path.dirname(__file__),
                "data", "template_order.json"
            )
            
            try:
                os.makedirs(os.path.dirname(order_file), exist_ok=True)
                with open(order_file, 'w') as f:
                    json.dump(template_order, f)
            except Exception as e:
                print(f"Error saving template order: {e}")
        
        def load_template_order():
            """Load template order from file"""
            import json
            import os
            
            order_file = os.path.join(
                os.path.dirname(__file__),
                "data", "template_order.json"
            )
            
            if os.path.exists(order_file):
                try:
                    with open(order_file, 'r') as f:
                        return json.load(f)
                except:
                    pass
            return []
        
        # Load saved template order
        template_order = load_template_order()
        
        # Bind drag events
        template_listbox.bind('<Button-1>', on_drag_start)
        template_listbox.bind('<B1-Motion>', on_drag_motion)
        template_listbox.bind('<ButtonRelease-1>', on_drag_release)
        
        # Bind double-click to load
        def on_double_click(event=None):
            """Load template on double-click"""
            selection = template_listbox.curselection()
            if selection:
                display_name = template_listbox.get(selection[0])
                # Extract template name (remove grade suffix if present)
                if ' [Grade:' in display_name:
                    template_name = display_name.split(' [Grade:')[0]
                else:
                    template_name = display_name
                template = template_data.get(template_name)
                if template:
                    dialog.destroy()  # Close dialog first
                    self.apply_template(template)
                    messagebox.showinfo("Success", f"Template '{template_name}' loaded successfully")
        
        template_listbox.bind('<Double-Button-1>', on_double_click)
        
        # Button frame at bottom of list view
        button_frame = tk.Frame(list_view_frame, bg=DARK_THEME['bg_primary'])
        button_frame.pack(pady=(15, 0))
        
        def load_selected():
            """Load the selected template"""
            selection = template_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a template to load")
                return
            
            display_name = template_listbox.get(selection[0])
            # Extract template name (remove grade suffix if present)
            if ' [Grade:' in display_name:
                template_name = display_name.split(' [Grade:')[0]
            else:
                template_name = display_name
            template = template_data.get(template_name)
            
            if template:
                dialog.destroy()  # Close dialog first
                self.apply_template(template)
                messagebox.showinfo("Success", f"Template '{template_name}' loaded successfully")
        
        # Load button
        load_btn = StyledButton(
            button_frame,
            text="LOAD SELECTED",
            command=load_selected,
            bg=DARK_THEME['button_active'],
            font=(DARK_THEME['font_family'], 11, 'bold'),
            padx=20,
            pady=10
        )
        load_btn.pack(side='left', padx=5)
        
        # Delete button
        def delete_selected():
            """Delete the selected template"""
            selection = template_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a template to delete")
                return
            
            display_name = template_listbox.get(selection[0])
            # Extract template name (remove grade suffix if present)
            if ' [Grade:' in display_name:
                template_name = display_name.split(' [Grade:')[0]
            else:
                template_name = display_name
            
            # Confirm deletion
            result = messagebox.askyesno(
                "Delete Template",
                f"Are you sure you want to delete the template '{template_name}'?",
                parent=dialog
            )
            
            if result:
                # Find template file
                for t in templates:
                    if t['name'] == template_name:
                        success = self.template_manager.delete_template(t['filename'])
                        if success:
                            # Remove from listbox and data
                            template_listbox.delete(selection[0])
                            del template_data[template_name]
                            # Clear roster display
                            roster_text.config(state='normal')
                            roster_text.delete('1.0', 'end')
                            roster_text.config(state='disabled')
                            # Update main dropdown
                            self.update_template_dropdown()
                            messagebox.showinfo("Success", f"Template '{template_name}' deleted")
                        break
        
        delete_btn = StyledButton(
            button_frame,
            text="DELETE",
            command=delete_selected,
            bg='#d32f2f',
            font=(DARK_THEME['font_family'], 11),
            padx=20,
            pady=10
        )
        delete_btn.pack(side='left', padx=5)
        
        # Close button
        close_btn = StyledButton(
            button_frame,
            text="CLOSE",
            command=dialog.destroy,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11),
            padx=20,
            pady=10
        )
        close_btn.pack(side='left', padx=5)
        
        # Auto-select first template if available
        if template_listbox.size() > 0:
            template_listbox.selection_set(0)
            on_template_select()
        
        # Setup comparison view
        self._setup_comparison_view(comparison_frame, template_data, templates)
    
    def _setup_comparison_view(self, parent_frame, template_data, templates):
        """Setup the side-by-side comparison view for templates"""
        # Title
        title_label = tk.Label(
            parent_frame,
            text="Compare Templates Side-by-Side",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        title_label.pack(pady=(10, 5))
        
        # Instructions
        instructions = tk.Label(
            parent_frame,
            text="Select up to 4 templates to compare their rosters",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        instructions.pack(pady=(0, 10))
        
        # Filter frame
        filter_frame = tk.Frame(parent_frame, bg=DARK_THEME['bg_primary'])
        filter_frame.pack(fill='x', padx=20, pady=(0, 5))
        
        # Early picks filter
        tk.Label(
            filter_frame,
            text="Filter by early picks:",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        ).pack(side='left', padx=(0, 10))
        
        filter_var = tk.StringVar(value="All")
        filter_options = [
            "All",
            "R1 RB", "R1 WR", "R1 TE", "R1 QB",
            "RB-RB (R1-2)", "WR-WR (R1-2)", "RB-WR (R1-2)", "WR-RB (R1-2)",
            "RB (R1-3)", "WR (R1-3)", "TE (R1-3)", "QB (R1-3)"
        ]
        
        filter_dropdown = ttk.Combobox(
            filter_frame,
            textvariable=filter_var,
            values=filter_options,
            state='readonly',
            width=20
        )
        filter_dropdown.set('All')
        filter_dropdown.pack(side='left')
        
        # Template selection frame
        selection_frame = tk.Frame(parent_frame, bg=DARK_THEME['bg_primary'])
        selection_frame.pack(fill='x', padx=20, pady=10)
        
        # Get ALL templates for comparison view (not filtered)
        all_templates = self.template_manager.list_templates()
        template_names = []
        all_template_data = {}
        
        # Load all template data - only include templates with at least 4 user picks
        for t in all_templates:
            template = self.template_manager.load_template(t['filename'])
            if template:
                # Check if user has at least 4 picks
                user_team_id = template.user_settings.get('user_team_id', 0)
                user_picks = [pick for pick in template.draft_results if pick['team_id'] == user_team_id]
                
                # Only include templates where user has made at least 4 picks
                if len(user_picks) >= 4:
                    template_names.append(t['name'])
                    all_template_data[t['name']] = template
        
        # Template dropdowns
        selected_templates = []
        template_dropdowns = []  # Store dropdown widgets for updating
        
        for i in range(4):
            col_frame = tk.Frame(selection_frame, bg=DARK_THEME['bg_primary'])
            col_frame.pack(side='left', padx=10)
            
            tk.Label(
                col_frame,
                text=f"Template {i+1}:",
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 9)
            ).pack()
            
            template_var = tk.StringVar()
            template_dropdown = ttk.Combobox(
                col_frame,
                textvariable=template_var,
                values=['None'] + template_names,
                state='readonly',
                width=25
            )
            template_dropdown.set('None')
            template_dropdown.pack()
            # Auto-update comparison when template is selected
            template_dropdown.bind('<<ComboboxSelected>>', lambda e: update_comparison())
            selected_templates.append(template_var)
            template_dropdowns.append(template_dropdown)
        
        def update_template_filter():
            """Update template dropdowns based on early picks filter"""
            filter_value = filter_var.get()
            filtered_names = []
            
            for name, template in all_template_data.items():
                if filter_value == "All":
                    filtered_names.append(name)
                else:
                    # Check early picks for this template
                    user_team_id = template.user_settings.get('user_team_id', 0)
                    players = {p['player_id']: p for p in template.player_pool['all_players']}
                    
                    # Get first 3 rounds of picks for user
                    early_picks = []
                    for pick in template.draft_results:
                        if pick['team_id'] == user_team_id and pick['round'] <= 3:
                            if pick['player_id'] in players:
                                p = players[pick['player_id']]
                                early_picks.append((pick['round'], p['position']))
                    
                    # Check if matches filter
                    if filter_value == "R1 RB" and len(early_picks) > 0 and early_picks[0][1] == 'RB':
                        filtered_names.append(name)
                    elif filter_value == "R1 WR" and len(early_picks) > 0 and early_picks[0][1] == 'WR':
                        filtered_names.append(name)
                    elif filter_value == "R1 TE" and len(early_picks) > 0 and early_picks[0][1] == 'TE':
                        filtered_names.append(name)
                    elif filter_value == "R1 QB" and len(early_picks) > 0 and early_picks[0][1] == 'QB':
                        filtered_names.append(name)
                    elif filter_value == "RB-RB (R1-2)" and len(early_picks) >= 2 and early_picks[0][1] == 'RB' and early_picks[1][1] == 'RB':
                        filtered_names.append(name)
                    elif filter_value == "WR-WR (R1-2)" and len(early_picks) >= 2 and early_picks[0][1] == 'WR' and early_picks[1][1] == 'WR':
                        filtered_names.append(name)
                    elif filter_value == "RB-WR (R1-2)" and len(early_picks) >= 2 and early_picks[0][1] == 'RB' and early_picks[1][1] == 'WR':
                        filtered_names.append(name)
                    elif filter_value == "WR-RB (R1-2)" and len(early_picks) >= 2 and early_picks[0][1] == 'WR' and early_picks[1][1] == 'RB':
                        filtered_names.append(name)
                    elif filter_value == "RB (R1-3)" and len(early_picks) >= 3:
                        rb_count = sum(1 for _, pos in early_picks[:3] if pos == 'RB')
                        if rb_count >= 2:
                            filtered_names.append(name)
                    elif filter_value == "WR (R1-3)" and len(early_picks) >= 3:
                        wr_count = sum(1 for _, pos in early_picks[:3] if pos == 'WR')
                        if wr_count >= 2:
                            filtered_names.append(name)
                    elif filter_value == "TE (R1-3)" and len(early_picks) >= 3:
                        te_count = sum(1 for _, pos in early_picks[:3] if pos == 'TE')
                        if te_count >= 1:
                            filtered_names.append(name)
                    elif filter_value == "QB (R1-3)" and len(early_picks) >= 3:
                        qb_count = sum(1 for _, pos in early_picks[:3] if pos == 'QB')
                        if qb_count >= 1:
                            filtered_names.append(name)
            
            # Update all dropdowns with filtered values
            for dropdown in template_dropdowns:
                current_val = dropdown.get()
                # Always keep current selection if it's not 'None'
                # The filter only affects what new selections are available
                if current_val and current_val != 'None':
                    # Keep the current selection and add it to the dropdown if needed
                    if current_val in filtered_names:
                        dropdown['values'] = ['None'] + sorted(filtered_names)
                    else:
                        # Add current selection to the list even if it doesn't match filter
                        dropdown['values'] = ['None', current_val] + sorted(filtered_names)
                    dropdown.set(current_val)
                else:
                    # Only update if nothing selected
                    dropdown['values'] = ['None'] + sorted(filtered_names)
                    dropdown.set('None')
        
        # Bind filter change to update function
        filter_dropdown.bind('<<ComboboxSelected>>', lambda e: update_template_filter())
        
        # Comparison display area
        display_frame = tk.Frame(parent_frame, bg=DARK_THEME['bg_secondary'])
        display_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Canvas for scrolling
        canvas = tk.Canvas(display_frame, bg=DARK_THEME['bg_secondary'], highlightthickness=0)
        scrollbar = tk.Scrollbar(display_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DARK_THEME['bg_secondary'])
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        def edit_template_grade(template_name):
            """Open dialog to edit template grade"""
            # Find the template filename
            template_filename = None
            for t in all_templates:
                if t['name'] == template_name:
                    template_filename = t['filename']
                    break
            
            if not template_filename:
                return
            
            # Get current grade
            current_grade = all_template_data[template_name].grade
            
            # Create dialog
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Edit Grade - {template_name}")
            dialog.configure(bg=DARK_THEME['bg_primary'])
            
            # Set size and center the dialog
            dialog_width = 300
            dialog_height = 150
            
            # Get screen dimensions
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()
            
            # Calculate center position
            x = (screen_width // 2) - (dialog_width // 2)
            y = (screen_height // 2) - (dialog_height // 2)
            
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            
            # Make dialog modal
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Grade input
            tk.Label(
                dialog,
                text="Enter grade (1-100) or leave empty to clear:",
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10)
            ).pack(pady=10)
            
            grade_var = tk.StringVar(value=str(current_grade) if current_grade else "")
            grade_entry = tk.Entry(
                dialog,
                textvariable=grade_var,
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 11),
                width=10
            )
            grade_entry.pack(pady=5)
            grade_entry.focus()
            
            def save_grade():
                grade_text = grade_var.get().strip()
                if grade_text:
                    try:
                        grade = int(grade_text)
                        if 1 <= grade <= 100:
                            if self.template_manager.update_template_grade(template_filename, grade):
                                # Update local data
                                all_template_data[template_name].grade = grade
                                update_comparison()
                                dialog.destroy()
                        else:
                            messagebox.showwarning("Invalid Grade", "Grade must be between 1 and 100")
                    except ValueError:
                        messagebox.showwarning("Invalid Grade", "Please enter a valid number")
                else:
                    # Clear grade
                    if self.template_manager.update_template_grade(template_filename, None):
                        all_template_data[template_name].grade = None
                        update_comparison()
                        dialog.destroy()
            
            # Buttons
            button_frame = tk.Frame(dialog, bg=DARK_THEME['bg_primary'])
            button_frame.pack(pady=15)
            
            tk.Button(
                button_frame,
                text="Save",
                bg=DARK_THEME['button_active'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10),
                command=save_grade,
                borderwidth=0,
                padx=20,
                pady=5
            ).pack(side='left', padx=5)
            
            tk.Button(
                button_frame,
                text="Cancel",
                bg=DARK_THEME['button_bg'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10),
                command=dialog.destroy,
                borderwidth=0,
                padx=20,
                pady=5
            ).pack(side='left', padx=5)
            
            # Bind Enter key to save
            grade_entry.bind('<Return>', lambda e: save_grade())
        
        def update_comparison():
            """Simple table display"""
            # Clear current display
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            
            # Get selected templates
            active_templates = []
            for var in selected_templates:
                name = var.get()
                if name and name != 'None' and name in all_template_data:
                    active_templates.append((name, all_template_data[name]))
            
            if not active_templates:
                tk.Label(
                    scrollable_frame,
                    text="Select templates above to compare",
                    bg=DARK_THEME['bg_secondary'],
                    fg=DARK_THEME['text_muted'],
                    font=(DARK_THEME['font_family'], 12)
                ).pack(pady=50)
                return
            
            # SIMPLE TABLE
            main_frame = tk.Frame(scrollable_frame, bg=DARK_THEME['bg_secondary'])
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # Display grades and notes for selected templates
            info_frame = tk.Frame(main_frame, bg=DARK_THEME['bg_secondary'])
            info_frame.pack(fill='x', pady=(0, 15))
            
            for idx, (name, template) in enumerate(active_templates):
                col_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_secondary'])
                col_frame.pack(side='left', padx=20)
                
                # Template name with grade
                grade_text = f" (Grade: {template.grade})" if template.grade else ""
                name_label = tk.Label(
                    col_frame,
                    text=f"{name}{grade_text}",
                    bg=DARK_THEME['bg_secondary'],
                    fg=DARK_THEME['text_primary'] if not template.grade else (
                        '#4CAF50' if template.grade >= 80 else
                        '#FFC107' if template.grade >= 60 else
                        '#F44336'
                    ),
                    font=(DARK_THEME['font_family'], 11, 'bold')
                )
                name_label.pack()
                
                # Notes preview (first 100 chars)
                if template.notes:
                    notes_preview = template.notes[:100] + "..." if len(template.notes) > 100 else template.notes
                    notes_label = tk.Label(
                        col_frame,
                        text=f"Notes: {notes_preview}",
                        bg=DARK_THEME['bg_secondary'],
                        fg=DARK_THEME['text_secondary'],
                        font=(DARK_THEME['font_family'], 9),
                        wraplength=300,
                        justify='left'
                    )
                    notes_label.pack()
                
                # Edit grade button
                edit_grade_btn = tk.Button(
                    col_frame,
                    text="Edit Grade",
                    bg=DARK_THEME['button_bg'],
                    fg=DARK_THEME['text_primary'],
                    font=(DARK_THEME['font_family'], 9),
                    command=lambda n=name: edit_template_grade(n),
                    borderwidth=0,
                    padx=10,
                    pady=2
                )
                edit_grade_btn.pack(pady=2)
            
            # Define consistent column widths
            pick_col_width = 10
            template_col_width = 35
            col_padding = 3
            
            # Header row
            header_frame = tk.Frame(main_frame, bg=DARK_THEME['bg_tertiary'])
            header_frame.pack(fill='x', pady=(0, 5))
            
            # Pick header
            pick_header = tk.Label(header_frame, text="Pick", bg=DARK_THEME['bg_tertiary'], fg='white', 
                    font=('Arial', 12, 'bold'), width=pick_col_width, anchor='w')
            pick_header.pack(side='left', padx=col_padding, pady=10)
            
            # Template headers
            for name, _ in active_templates:
                template_header = tk.Label(header_frame, text=name[:30], bg=DARK_THEME['bg_tertiary'], fg='white',
                        font=('Arial', 12, 'bold'), width=template_col_width, anchor='w')
                template_header.pack(side='left', padx=col_padding, pady=10)
            
            # Get picks for each template  
            template_picks = {}
            max_picks = 0
            
            for name, template in active_templates:
                user_team_id = template.user_settings.get('user_team_id', 0) 
                players = {p['player_id']: p for p in template.player_pool['all_players']}
                
                picks = []
                for pick in template.draft_results:
                    if pick['team_id'] == user_team_id and pick['player_id'] in players:
                        p = players[pick['player_id']]
                        picks.append(f"{p['name']} ({p['position']})")
                
                template_picks[name] = picks
                max_picks = max(max_picks, len(picks))
            
            # Display rows
            for i in range(max_picks):
                row_frame = tk.Frame(main_frame, bg=DARK_THEME['bg_primary'] if i % 2 == 0 else DARK_THEME['bg_secondary'])
                row_frame.pack(fill='x', pady=1)
                
                # Pick number - same width as header
                pick_label = tk.Label(row_frame, text=f"{i+1}", bg=row_frame['bg'], fg='white',
                        font=('Arial', 11), width=pick_col_width, anchor='w')
                pick_label.pack(side='left', padx=col_padding, pady=6)
                
                # Each template's pick - same width as header
                for name, _ in active_templates:
                    picks = template_picks.get(name, [])
                    text = picks[i] if i < len(picks) else "-"
                    data_label = tk.Label(row_frame, text=text, bg=row_frame['bg'], fg='white',
                            font=('Arial', 11), width=template_col_width, anchor='w')
                    data_label.pack(side='left', padx=col_padding, pady=6)
            
            # Update canvas scroll region
            scrollable_frame.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox('all'))
        
        # Compare button
        compare_btn = tk.Button(
            selection_frame,
            text="COMPARE",
            bg=DARK_THEME['button_active'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            command=update_comparison,
            activebackground=DARK_THEME['button_hover'],
            borderwidth=0,
            padx=20,
            pady=5
        )
        compare_btn.pack(side='left', padx=20)
        
        # Initial empty display
        update_comparison()
    
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
                    # Clear selection and disable delete button only
                    self.template_var.set("")
                    self.delete_template_button.config(state='disabled')
                else:
                    messagebox.showerror("Error", "Failed to delete template")
            else:
                messagebox.showerror("Error", "Template file not found")
    
    def load_template(self):
        """Load a selected template"""
        selected = self.template_var.get()
        if not selected:
            # Show template viewer dialog if no template selected
            self.show_template_viewer()
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
        # Reset the draft completely before applying template
        self.restart_draft(skip_confirmation=True)
        
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
                bye_week=p_data.get('bye_week'),
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
        
        # Clear and restore ALL draft picks from template
        self.draft_engine.draft_results = []
        for pick_data in template.draft_results:
            if pick_data['player_id'] and pick_data['player_id'] in player_lookup:
                player = player_lookup[pick_data['player_id']]
                pick = DraftPick(
                    pick_number=pick_data['pick_number'],
                    round=pick_data['round'],
                    pick_in_round=pick_data['pick_in_round'],
                    team_id=pick_data['team_id'],
                    player=player
                )
                self.draft_engine.draft_results.append(pick)
        
        # Restore trades if present
        if hasattr(template, 'trades') and template.trades:
            self.trade_service.clear_trades()
            for trade in template.trades:
                self.trade_service.add_trade(
                    trade['team1_id'], trade['team1_rounds'],
                    trade['team2_id'], trade['team2_rounds']
                )
        
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
        
        # Update draft board with current pick number
        pick_num, _, _, _ = self.draft_engine.get_current_pick_info()
        self.draft_board.update_picks(self.draft_engine.draft_results, pick_num)
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
    
    # Draft save/load removed - using templates/presets instead
    
    def placeholder_for_removed_methods(self):
        """Placeholder for removed save/load methods"""
        pass
    
    # The following methods were removed, now using templates/presets:
    # - save_draft_manually
    # - view_saved_drafts  
    # - load_draft_history
    # - _generate_draft_name_from_picks
    # - _save_draft_history_pick
    
    def show_preset_dialog(self):
        """View saved draft files"""
        # Get draft history (ongoing drafts)
        draft_history = self.draft_history_manager.get_draft_list()
        print(f"Found {len(draft_history)} saved drafts")
        
        # Also get completed drafts
        saved_drafts = self.draft_save_manager.get_saved_drafts()
        
        if not draft_history and not saved_drafts:
            messagebox.showinfo(
                "No Saved Drafts",
                "No drafts found.\n\nDrafts are automatically saved as you make picks.",
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
        
        # Combine and display all drafts
        all_drafts = []
        
        # Add draft history (ongoing drafts)
        for draft in draft_history:
            all_drafts.append({
                'type': 'history',
                'name': draft['name'],
                'id': draft['id'],
                'modified': draft.get('modified', ''),
                'picks': draft.get('picks_count', 0),
                'user_team': draft.get('user_team', 'No Team')
            })
        
        # Add completed drafts
        for draft in saved_drafts:
            all_drafts.append({
                'type': 'completed',
                'name': draft.get('filename', 'Unknown'),
                'timestamp': draft.get('timestamp', ''),
                'picks': draft.get('total_picks', 0),
                'user_team': draft.get('user_team', 'Observer')
            })
        
        # Sort by date (most recent first)
        all_drafts.sort(key=lambda x: x.get('modified') or x.get('timestamp', ''), reverse=True)
        
        # Display all drafts
        for i, draft_info in enumerate(all_drafts):
            # Row background
            row_bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
            
            row = tk.Frame(drafts_frame, bg=row_bg, height=60)
            row.pack(fill='x', pady=1)
            row.pack_propagate(False)
            
            # Draft info
            info_frame = tk.Frame(row, bg=row_bg)
            info_frame.pack(side='left', fill='both', expand=True, padx=10)
            
            # Draft name
            draft_name = draft_info.get('name', draft_info.get('filename', 'Unknown Draft'))
            name_label = tk.Label(
                info_frame,
                text=draft_name,
                bg=row_bg,
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 11, 'bold')
            )
            name_label.pack(anchor='w', pady=(5, 0))
            
            # Team and mode info
            info_text = f"Team: {draft_info.get('user_team', 'Unknown')} | "
            manual_mode = draft_info.get('manual_mode', False)
            info_text += f"Mode: {'Manual' if manual_mode else 'Normal'} | "
            info_text += f"Picks: {draft_info.get('total_picks', draft_info.get('picks', 0))}"
            
            info_label = tk.Label(
                info_frame,
                text=info_text,
                bg=row_bg,
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 9)
            )
            info_label.pack(anchor='w')
            
            # View/Load button
            if draft_info.get('type') == 'history':
                btn_text = "LOAD"
                btn_command = lambda d=draft_info: self.load_draft_history(d['id'])
            else:
                btn_text = "VIEW"
                btn_command = lambda f=draft_info.get('name', draft_info.get('filename')): self.view_draft_details(f)
            
            view_btn = StyledButton(
                row,
                text=btn_text,
                command=btn_command,
                bg=DARK_THEME['button_bg'],
                font=(DARK_THEME['font_family'], 9),
                padx=15,
                pady=5
            )
            view_btn.pack(side='right', padx=5)
            
            # Delete button
            if draft_info.get('type') == 'history':
                delete_btn = StyledButton(
                    row,
                    text="DELETE",
                    command=lambda d=draft_info, dlg=dialog: self.delete_draft(d['id'], dlg),
                    bg='#D32F2F',  # Red color
                    font=(DARK_THEME['font_family'], 9),
                    padx=15,
                    pady=5
                )
                delete_btn.pack(side='right', padx=5)
        
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
    
    def show_trades_dialog(self):
        """Show dialog for configuring draft pick trades"""
        def on_apply():
            # Reset draft to apply trades
            if self.draft_engine.draft_results:
                response = messagebox.askyesno(
                    "Apply Trades",
                    "Applying trades will restart the draft. Continue?",
                    parent=self.root
                )
                if response:
                    self.restart_draft()
            # Update draft board to show traded picks and refresh borders
            self.draft_board.update_display()
            # Also notify the board that trades have been updated
            self.draft_board.on_trades_updated()
        
        def on_trade_added():
            """Called immediately when a trade is added/removed in the dialog"""
            # Rebuild the board to show trade indicators and update borders
            self.draft_board.update_display()
            # Also update the border highlights for the user's picks
            if self.draft_board.selected_team_id:
                self.draft_board.on_trades_updated()
        
        TradeDialog(
            self.root,
            num_teams=config.num_teams,
            total_rounds=self.draft_engine.total_rounds,
            trade_service=self.trade_service,
            on_apply=on_apply,
            on_trade_added=on_trade_added
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
    
    def on_draft_name_change(self, draft_name):
        """Handle draft name change from UI"""
        self.draft_history_manager.update_draft_name(draft_name)
    
    def get_draft_list(self):
        """Get list of saved drafts for dropdown"""
        return self.draft_history_manager.get_draft_list()
    
    def delete_draft(self, draft_id, dialog):
        """Delete a saved draft"""
        result = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this draft?",
            parent=dialog
        )
        
        if result:
            # Delete the draft file
            import os
            draft_file = os.path.join(
                os.path.dirname(__file__),
                "data", "draft_history",
                f"{draft_id}.json"
            )
            
            if os.path.exists(draft_file):
                os.remove(draft_file)
                messagebox.showinfo(
                    "Draft Deleted",
                    "Draft has been deleted successfully.",
                    parent=dialog
                )
                # Refresh the dialog
                dialog.destroy()
                self.view_saved_drafts()
            else:
                messagebox.showerror(
                    "Error",
                    "Draft file not found.",
                    parent=dialog
                )
    
    def load_draft_history(self, draft_id):
        """Load a saved draft from history"""
        print(f"Loading draft: {draft_id}")
        draft_data = self.draft_history_manager.load_draft(draft_id)
        if not draft_data:
            messagebox.showerror("Error", "Could not load draft", parent=self.root)
            return
        
        print(f"Draft data loaded: {draft_data.get('name')} with {len(draft_data.get('picks', []))} picks")
        
        # Temporarily disable auto-draft
        self.loading_draft = True
        
        # Save the draft_id and name so they don't get overwritten
        saved_draft_id = self.draft_history_manager.current_draft_id
        saved_draft_name = draft_data.get('name', 'Untitled')
        
        # Clear current draft
        self.restart_draft()
        
        # Restore the draft_id and name we're loading
        self.draft_history_manager.current_draft_id = saved_draft_id
        self.draft_history_manager.current_draft_name = saved_draft_name
        
        # Update draft name in UI
        self.draft_board.set_draft_name(draft_data.get('name', ''))
        
        # Restore team names if saved
        teams_data = draft_data.get('teams', {})
        for team_id_str, team_data in teams_data.items():
            team_id = int(team_id_str)
            if team_id in self.teams:
                self.teams[team_id].name = team_data['name']
        self.draft_board.update_team_names(self.teams)
        
        # Restore user team selection
        if draft_data.get('user_team_id'):
            self.user_team_id = draft_data['user_team_id']
            self.draft_board.select_team(self.user_team_id)
            # Don't call on_team_selected as it starts a new draft session
        
        # Restore manual mode
        if draft_data.get('manual_mode'):
            self.manual_mode = True
            self.draft_board.set_manual_mode(True)
        
        # Restore picks
        picks = draft_data.get('picks', [])
        print(f"Restoring {len(picks)} picks...")
        picks_restored = 0
        
        for pick_data in picks:
            # Find the player
            player = None
            player_id = pick_data.get('player', {}).get('player_id')
            
            if not player_id:
                print(f"Warning: Pick missing player_id: {pick_data}")
                continue
                
            for p in self.all_players:
                if p.player_id == player_id:
                    player = p
                    break
            
            if player:
                # Make the pick
                team_id = pick_data['team_id']
                team = self.teams[team_id]
                self.draft_engine.make_pick(team, player)
                
                # Remove from available players
                if player in self.available_players:
                    self.available_players.remove(player)
                
                # Update player pool
                if self.player_pool:
                    self.player_pool.draft_player(player)
                
                # Remove from UI
                self._remove_drafted_player(player)
                picks_restored += 1
                print(f"Restored pick {picks_restored}: {player.name} to Team {team_id}")
            else:
                print(f"Warning: Could not find player with ID {player_id}")
        
        # Update UI
        pick_info = self.draft_engine.get_current_pick_info()
        self.draft_board.update_picks(
            self.draft_engine.get_draft_results(),
            pick_info[0]
        )
        self.roster_view.update_roster_display()
        
        # Update draft history display
        if self.draft_history:
            for pick in self.draft_engine.draft_results:
                self.draft_history.add_pick(pick)
        
        # Update the display fully
        self.update_display(full_update=True)
        
        # Re-enable auto-draft
        self.loading_draft = False
        
        # Show success message with actual pick count
        picks_loaded = len(self.draft_engine.draft_results)
        messagebox.showinfo(
            "Draft Loaded", 
            f"Loaded draft: {draft_data.get('name', 'Untitled')}\n{picks_loaded} picks restored.",
            parent=self.root
        )
    
    def _generate_draft_name_from_picks(self):
        """Generate draft name from player last names"""
        import random
        
        # Get user's picks only
        user_picks = []
        if self.user_team_id is not None:
            user_picks = [pick for pick in self.draft_engine.draft_results 
                         if pick.team_id == self.user_team_id]
        
        # If no user picks yet, use all picks
        if not user_picks:
            user_picks = self.draft_engine.draft_results[:3]  # First 3 picks
        
        # Extract last names
        last_names = []
        for pick in user_picks[:3]:  # Use up to first 3 picks
            player_name = pick.player.name
            # Get last name (last word in the name)
            last_name = player_name.split()[-1] if player_name else "Player"
            last_names.append(last_name)
        
        # Create name from last names
        if last_names:
            draft_name = "-".join(last_names)
            # Add random number for uniqueness
            draft_name += f"-{random.randint(100, 999)}"
        else:
            from datetime import datetime
            draft_name = f"Draft-{datetime.now().strftime('%m%d')}-{random.randint(100, 999)}"
        
        return draft_name
    
    def _save_draft_history_pick(self, pick):
        """Save a pick to draft history"""
        # Only start saving after 10 picks
        if len(self.draft_engine.draft_results) >= 10:
            # Initialize draft session if not already started
            if not self.draft_history_manager.current_draft_id:
                draft_name = self._generate_draft_name_from_picks()
                self.draft_history_manager.start_new_draft(draft_name=draft_name)
                
                # Save team configuration
                self.draft_history_manager.save_team_config(
                    self.teams,
                    user_team_id=self.user_team_id,
                    manual_mode=self.manual_mode
                )
                
                # Save all previous picks
                for prev_pick in self.draft_engine.draft_results[:-1]:
                    self.draft_history_manager.save_pick(
                        prev_pick,
                        user_team_id=self.user_team_id,
                        manual_mode=self.manual_mode
                    )
            
            # Save the current pick
            self.draft_history_manager.save_pick(
                pick,
                user_team_id=self.user_team_id,
                manual_mode=self.manual_mode
            )
            
            # Update draft name every 10 picks or so
            if len(self.draft_engine.draft_results) % 10 == 0:
                new_name = self._generate_draft_name_from_picks()
                self.draft_history_manager.update_draft_name(new_name)


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