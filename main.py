import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import random

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
        # Optimized window size - wider for draft board
        self.root.geometry("1920x900")
        self.root.configure(bg=DARK_THEME['bg_primary'])
        
        # Set minimum window size
        self.root.minsize(1800, 800)
        
        # Initialize draft components
        self.teams = self._create_teams()
        self.draft_engine = DraftEngine(
            num_teams=config.num_teams,
            roster_spots=config.roster_spots,
            draft_type=config.draft_type,
            reversal_round=config.reversal_round
        )
        
        # Initialize players
        self.all_players = generate_mock_players()
        self.available_players = list(self.all_players)
        
        # Initialize services
        from src.services import PlayerImageService
        self.image_service = PlayerImageService()
        
        # User control state
        self.user_team_id = None  # Which team the user controls
        
        # Draft reversion state
        self.draft_state_before_reversion = None
        self.players_before_reversion = None
        
        # Setup UI
        self.setup_ui()
        self.setup_keyboard_shortcuts()
        
        # Defer initial display update to speed up load
        self.root.after(10, lambda: self.update_display())
    
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
        paned_window = ttk.PanedWindow(content_frame, orient='vertical')
        paned_window.pack(fill='both', expand=True)
        
        # Configure PanedWindow style
        style = ttk.Style()
        style.configure('Sash', sashthickness=8)
        style.configure('TPanedwindow', background=DARK_THEME['bg_primary'])
        
        # Top section - Draft board and Roster
        top_frame = StyledFrame(paned_window, bg_type='primary')
        
        # Use grid for draft board and roster side by side
        top_frame.grid_rowconfigure(0, weight=1)
        top_frame.grid_columnconfigure(0, weight=1)  # Draft board column - expand to fill
        top_frame.grid_columnconfigure(1, weight=0, minsize=250)  # Roster column - fixed width
        
        # Draft board
        draft_panel = StyledFrame(top_frame, bg_type='secondary')
        draft_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        
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
        
        # Add frames to PanedWindow
        paned_window.add(top_frame, weight=3)
        paned_window.add(player_panel, weight=1)
    
    def update_display(self, full_update=True):
        # Update status
        pick_num, round_num, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
        
        if self.draft_engine.is_draft_complete():
            self.status_label.config(text="Draft Complete!")
            self.on_clock_label.config(text="All picks have been made")
            self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
        else:
            self.status_label.config(text=f"Round {round_num} • Pick {pick_in_round}")
            self.on_clock_label.config(text=f"On the Clock: {self.teams[team_on_clock].name}")
            
            # Only enable draft button if it's user's turn and they've selected a team
            if self.user_team_id and team_on_clock == self.user_team_id:
                self.draft_button.config(state="normal", bg=DARK_THEME['button_active'])
            else:
                self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
        
        # Update components
        if full_update:
            self.player_list.update_players(self.available_players)
            # Update draft button states based on team selection
            self.player_list.set_draft_enabled(self.user_team_id is not None)
        
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
        # Check if user has selected a team first
        if not self.user_team_id:
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
        
        _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
        current_team = self.teams[team_on_clock]
        
        try:
            # First make the pick in the engine
            self.draft_engine.make_pick(current_team, player)
            
            # Remove from available players list
            if player in self.available_players:
                self.available_players.remove(player)
            
            # Remove the drafted player from the UI immediately
            if self.player_list.selected_index is not None:
                # Find the actual index of this player in case it changed
                actual_index = None
                for i, p in enumerate(self.player_list.players):
                    if p == player:
                        actual_index = i
                        break
                
                if actual_index is not None:
                    self.player_list.remove_player_card(actual_index)
                    self.player_list.selected_index = None
            
            # Update draft board with new pick immediately
            self.draft_board.update_picks(
                self.draft_engine.get_draft_results(),
                self.draft_engine.get_current_pick_info()[0]
            )
            
            # Check if we need to auto-draft next
            self.check_auto_draft()
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
        # Check if we need to auto-draft for current pick
        self.check_auto_draft()
    
    def check_auto_draft(self):
        """Check if current pick should be automated"""
        if self.draft_engine.is_draft_complete():
            return
            
        _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
        
        # If user hasn't selected a team or it's not their turn, auto-draft
        if self.user_team_id is None or team_on_clock != self.user_team_id:
            # Process all auto-picks until it's the user's turn again
            self.auto_draft_until_user_turn()
    
    def auto_draft_until_user_turn(self):
        """Automatically draft for all teams until it's the user's turn"""
        picks_made = []
        
        while not self.draft_engine.is_draft_complete():
            _, _, _, team_on_clock = self.draft_engine.get_current_pick_info()
            
            # Stop if it's the user's turn
            if self.user_team_id is not None and team_on_clock == self.user_team_id:
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
                    
                    # Debug print
                    adp_diff = pick_num - selected_player.adp
                    print(f"Pick #{pick_num}: {current_team.name} selects {selected_player.name} ({selected_player.position}) "
                          f"- ADP: {selected_player.adp:.1f} (diff: {adp_diff:+.1f})")
                except ValueError:
                    # Pick failed, try next player
                    continue
        
        # Update everything at once after all auto-picks
        if picks_made:
            # Remove auto-drafted players from the UI
            players_to_remove = [player for _, _, player in picks_made]
            self.player_list.remove_players(players_to_remove)
            
            # Update draft board with all new picks
            self.draft_board.update_picks(
                self.draft_engine.get_draft_results(),
                self.draft_engine.get_current_pick_info()[0]
            )
            
            # Update status labels
            pick_num, round_num, pick_in_round, team_on_clock = self.draft_engine.get_current_pick_info()
            self.status_label.config(text=f"Round {round_num} • Pick {pick_in_round}")
            self.on_clock_label.config(text=f"On the Clock: {self.teams[team_on_clock].name}")
            
            # Enable draft button if it's user's turn
            if self.user_team_id and team_on_clock == self.user_team_id:
                self.draft_button.config(state="normal", bg=DARK_THEME['button_active'])
            else:
                self.draft_button.config(state="disabled", bg=DARK_THEME['button_bg'])
    
    def _select_computer_pick(self, team, pick_num):
        """Select a player for computer team based on smart drafting logic"""
        # Get team's current roster
        roster_needs = self._get_team_needs(team)
        
        # Count current players by position
        position_counts = self._get_position_counts(team)
        
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
        
        # Calculate pick value for each player based on ADP
        player_values = []
        for player in eligible_players:
            # Calculate how good the value is (negative = reach, positive = value)
            adp_diff = pick_num - player.adp
            
            # Adjust value based on roster need
            need_multiplier = 1.0
            if player.position in roster_needs[:2]:  # Top 2 needs
                need_multiplier = 1.2 if is_early_round else 1.3
            elif player.position in roster_needs[:3]:  # Top 3 needs
                need_multiplier = 1.1 if is_early_round else 1.15
            
            # Calculate probability - much tighter in early rounds
            if is_early_round:
                # Early rounds: heavily favor players near their ADP
                if adp_diff > 5:  # Great value
                    base_prob = 0.5
                elif adp_diff > 2:  # Good value
                    base_prob = 0.4
                elif adp_diff > -2:  # Fair value (within 2 picks)
                    base_prob = 0.35
                elif adp_diff > -5:  # Slight reach
                    base_prob = 0.15
                else:  # Big reach
                    base_prob = 0.02
            else:
                # Later rounds: more flexibility
                if adp_diff > 10:  # Great value
                    base_prob = 0.4
                elif adp_diff > 5:  # Good value
                    base_prob = 0.3
                elif adp_diff > -3:  # Fair value
                    base_prob = 0.25
                elif adp_diff > -10:  # Slight reach
                    base_prob = 0.1
                else:  # Big reach
                    base_prob = 0.02
            
            final_prob = base_prob * need_multiplier
            player_values.append((player, final_prob))
        
        # Normalize probabilities
        total_prob = sum(prob for _, prob in player_values)
        if total_prob > 0:
            player_values = [(p, prob/total_prob) for p, prob in player_values]
        else:
            # Fallback to equal probability
            player_values = [(p, 1.0/len(player_values)) for p, _ in player_values]
        
        # Select player based on weighted random choice
        rand = random.random()
        cumulative = 0
        for player, prob in player_values:
            cumulative += prob
            if rand <= cumulative:
                return player
        
        # Fallback
        return player_values[0][0] if player_values else None
    
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
        
        # Reset players
        self.all_players = generate_mock_players()
        self.available_players = list(self.all_players)
        
        # Restore user team selection
        self.user_team_id = saved_user_team
        
        # Reset UI
        self.draft_board.draft_results = []
        self.draft_board._last_pick_count = 0
        
        # Clear all pick widgets
        for pick_widget in self.draft_board.pick_widgets.values():
            for widget in pick_widget.winfo_children():
                if isinstance(widget, tk.Frame) and widget.winfo_y() > 20:
                    widget.destroy()
        
        # Update display
        self.update_display()
        
        # Force roster view to update
        self.roster_view.update_roster_display()
        
        # Re-enable draft button
        self.draft_button.config(state="normal", bg=DARK_THEME['button_active'])
        
        # Disable undo button
        self.undo_button.config(state='disabled')
        self.draft_state_before_reversion = None
        self.players_before_reversion = None
        
        # Start auto-drafting from the beginning
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
            'current_pick': self.draft_engine.get_current_pick_info()[0]
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
    
    def _revert_to_pick(self, target_pick_number):
        """Revert draft to specified pick number"""
        # Keep only picks before the target
        picks_to_keep = [p for p in self.draft_engine.draft_results if p.pick_number < target_pick_number]
        
        # Reset teams
        for team in self.teams.values():
            team.roster = {pos: [] for pos in team.roster}
        
        # Reset available players
        self.available_players = list(self.all_players)
        
        # Replay kept picks
        self.draft_engine.draft_results = []
        for pick in picks_to_keep:
            team = self.teams[pick.team_id]
            team.add_player(pick.player)
            self.draft_engine.draft_results.append(pick)
            self.available_players.remove(pick.player)
        
        # Clear visual picks after the target
        for pick_num in range(target_pick_number, len(self.draft_board.pick_widgets) + 1):
            if pick_num in self.draft_board.pick_widgets:
                pick_frame = self.draft_board.pick_widgets[pick_num]
                for widget in pick_frame.winfo_children():
                    if isinstance(widget, tk.Frame) and widget.winfo_y() > 20:
                        widget.destroy()
        
        # Reset the last pick count
        self.draft_board._last_pick_count = len(picks_to_keep)
        
        # Update display
        self.update_display()
        
        # Check if we need to auto-draft
        self.check_auto_draft()
    
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