import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional
from ..core import DraftPick
from ..models import Team
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame
from ..services.manager_notes_service import ManagerNotesService


class DraftBoard(StyledFrame):
    def __init__(self, parent, teams: Dict[int, Team], total_rounds: int, max_visible_rounds: int = 9, on_team_select=None, on_pick_click=None, image_service=None, on_pick_change=None, get_top_players=None, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.teams = teams
        self.num_teams = len(teams)
        self.total_rounds = total_rounds
        self.max_visible_rounds = max_visible_rounds
        self.pick_widgets: Dict[int, tk.Frame] = {}  # pick_number -> widget
        self.current_pick_num = 1
        self.on_team_select = on_team_select
        self.on_pick_click = on_pick_click
        self.on_pick_change = on_pick_change
        self.get_top_players = get_top_players
        self.selected_team_id = None
        self.team_buttons = {}  # team_id -> button widget
        self.draft_results = []  # Store draft picks
        self.image_service = image_service
        self.glow_animation_running = False
        self.canvas = None
        self.scrollable_frame = None
        self.manager_notes_service = ManagerNotesService()
        self.tooltip = None
        self.setup_ui()
        # Start glowing animation if no team selected
        if not self.selected_team_id:
            self.start_glow_animation()
        # Bind resize event
        self.bind('<Configure>', self.on_resize)
        # Track if we're currently resizing
        self._is_resizing = False
        
    def setup_ui(self):
        # Main container with padding
        container = StyledFrame(self, bg_type='secondary')
        container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Canvas for vertical scrolling only
        self.canvas = tk.Canvas(
            container,
            bg=DARK_THEME['bg_secondary'],
            highlightthickness=0
        )
        v_scrollbar = tk.Scrollbar(
            container,
            orient='vertical',
            command=self.canvas.yview,
            bg=DARK_THEME['bg_tertiary'],
            troughcolor=DARK_THEME['bg_secondary']
        )
        
        self.scrollable_frame = StyledFrame(self.canvas, bg_type='secondary')
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        # Grid layout
        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        
        self.canvas.bind('<MouseWheel>', on_mousewheel)
        self.scrollable_frame.bind('<MouseWheel>', on_mousewheel)
        
        # Create the draft grid
        self.create_draft_grid()
    
    def create_draft_grid(self):
        # Get actual available width
        self.update_idletasks()  # Force geometry update
        available_width = self.winfo_width()  # Use full width
        
        # Calculate column width to fill available space
        col_width = max(100, available_width // self.num_teams)
        
        row_height = 60  # Height for each pick
        header_height = 40
        button_height = 25
        
        # Team selection buttons
        for team_id in range(1, self.num_teams + 1):
            button_frame = StyledFrame(
                self.scrollable_frame,
                bg_type='secondary',
                width=col_width,
                height=button_height
            )
            button_frame.grid(row=0, column=team_id - 1, sticky='nsew', padx=2, pady=(0, 2))
            button_frame.grid_propagate(False)
            
            button = tk.Button(
                button_frame,
                text=f"Sit",
                bg=DARK_THEME['button_bg'],
                fg='white',
                font=(DARK_THEME['font_family'], 9),
                bd=1,
                relief='solid',
                command=lambda tid=team_id: self.select_team(tid),
                cursor='hand2'
            )
            button.pack(fill='both', expand=True)
            self.team_buttons[team_id] = button
        
        # Create storage for team labels
        self.team_labels = {}
        
        # Team headers
        for team_id in range(1, self.num_teams + 1):
            team = self.teams[team_id]
            
            header_frame = StyledFrame(
                self.scrollable_frame,
                bg_type='tertiary',
                relief='flat',
                width=col_width,
                height=header_height
            )
            header_frame.grid(row=1, column=team_id - 1, sticky='nsew', padx=2, pady=2)
            header_frame.grid_propagate(False)
            
            # Don't uppercase the team name so mappings work correctly
            team_label = tk.Label(
                header_frame,
                text=team.name,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 11, 'bold')
            )
            team_label.place(relx=0.5, rely=0.5, anchor='center')
            
            # Add hover functionality for manager notes
            team_label.bind("<Enter>", lambda e, name=team.name: self.show_manager_tooltip(e, name))
            team_label.bind("<Leave>", lambda e: self.hide_manager_tooltip())
            
            # Store reference to team label
            self.team_labels[team_id] = team_label
        
        # Create pick slots for visible rounds only
        pick_number = 1
        visible_rounds = min(self.total_rounds, self.max_visible_rounds)
        
        for round_num in range(1, self.total_rounds + 1):
            # Determine order for this round (with 3rd round reversal)
            if round_num == 1:
                order = list(range(1, self.num_teams + 1))  # 1→10
            elif round_num == 2 or round_num == 3:
                # Rounds 2 and 3 go the same direction (reverse)
                order = list(range(self.num_teams, 0, -1))  # 10→1
            else:
                # After round 3, normal snake draft resumes
                # Since round 3 went reverse, round 4 should go forward
                # Round 4: forward (1→10), Round 5: reverse (10→1), etc.
                if (round_num - 3) % 2 == 1:  # 4-3=1 (odd), so forward
                    order = list(range(1, self.num_teams + 1))
                else:  # 5-3=2 (even), so reverse
                    order = list(range(self.num_teams, 0, -1))
            
            # Create pick slots
            for pos, team_id in enumerate(order):
                pick_frame = StyledFrame(
                    self.scrollable_frame,
                    bg_type='tertiary',
                    relief='flat',
                    width=col_width,
                    height=row_height
                )
                pick_frame.grid(
                    row=round_num + 1,
                    column=team_id - 1,
                    sticky='nsew',
                    padx=2,
                    pady=2
                )
                pick_frame.grid_propagate(False)
                
                # Round/Pick label
                round_pick_label = tk.Label(
                    pick_frame,
                    text=f"R{round_num}.{pos + 1}",
                    bg=DARK_THEME['bg_tertiary'],
                    fg=DARK_THEME['text_muted'],
                    font=(DARK_THEME['font_family'], 8)
                )
                round_pick_label.place(x=5, y=5)
                
                # Pick number label
                pick_num_label = tk.Label(
                    pick_frame,
                    text=f"#{pick_number}",
                    bg=DARK_THEME['bg_tertiary'],
                    fg=DARK_THEME['text_muted'],
                    font=(DARK_THEME['font_family'], 8)
                )
                pick_num_label.place(relx=0.95, y=5, anchor='ne')
                
                # Store reference
                self.pick_widgets[pick_number] = pick_frame
                
                # Make pick clickable (but only for completed picks)
                def on_pick_click(event):
                    pass  # We'll handle clicks when the pick is actually made
                
                pick_frame.bind("<Button-1>", on_pick_click)
                
                # Bind mousewheel to pick frame
                if hasattr(self, 'canvas'):
                    pick_frame.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))
                
                pick_number += 1
        
        # Configure grid weights - make columns expand
        for i in range(self.num_teams):
            self.scrollable_frame.grid_columnconfigure(i, weight=1, minsize=col_width)
        for i in range(self.total_rounds + 2):
            if i == 0:
                self.scrollable_frame.grid_rowconfigure(i, minsize=button_height)
            elif i == 1:
                self.scrollable_frame.grid_rowconfigure(i, minsize=header_height)
            else:
                self.scrollable_frame.grid_rowconfigure(i, minsize=row_height)
    
    def select_team(self, team_id: int):
        """Handle team selection for user control"""
        self.selected_team_id = team_id
        
        # Stop glow animation when team is selected
        self.stop_glow_animation()
        
        # Update button appearances
        for tid, button in self.team_buttons.items():
            if tid == team_id:
                button.config(
                    bg=DARK_THEME['button_active'],
                    fg='white',
                    text='Sitting'
                )
            else:
                button.config(
                    bg=DARK_THEME['button_bg'],
                    fg='white',
                    text='Sit'
                )
        
        # Hide the sit row after selection
        self.hide_sit_row()
        
        # Notify parent if callback provided
        if self.on_team_select:
            self.on_team_select(team_id)
    
    def hide_sit_row(self):
        """Hide the row containing sit buttons"""
        for button in self.team_buttons.values():
            button.master.grid_forget()
    
    def show_sit_row(self):
        """Show the row containing sit buttons"""
        col_width = max(100, self.winfo_width() // self.num_teams)
        for team_id, button in self.team_buttons.items():
            button.master.grid(row=0, column=team_id - 1, sticky='nsew', padx=2, pady=(0, 2))
            button.master.config(width=col_width, height=25)
    
    def update_picks(self, picks: List[DraftPick], current_pick_num: int):
        self.current_pick_num = current_pick_num
        self.draft_results = picks  # Store all picks
        
        # Skip updates during resize
        if getattr(self, '_is_resizing', False):
            return
        
        # Only update new picks since last update
        if not hasattr(self, '_last_pick_count'):
            self._last_pick_count = 0
        
        # Defer the actual update to prevent jarring visual changes
        if not hasattr(self, '_update_pending') or not self._update_pending:
            self._update_pending = True
            self.after(10, lambda: self._do_update_picks(picks, current_pick_num))
    
    def _do_update_picks(self, picks: List[DraftPick], current_pick_num: int):
        """Actually perform the pick updates"""
        self._update_pending = False
        
        # Update only new picks
        new_picks = picks[self._last_pick_count:]
        for pick in new_picks:
            if pick.pick_number in self.pick_widgets:
                self.update_pick_slot(pick)
        
        self._last_pick_count = len(picks)
        
        # Only update cursors if picks have changed
        if new_picks:
            # Update cursor for newly completed picks only
            for pick in new_picks:
                if pick.pick_number in self.pick_widgets:
                    self.pick_widgets[pick.pick_number].config(cursor="hand2")
        
        # Only highlight if current pick changed
        if not hasattr(self, '_last_highlighted_pick') or self._last_highlighted_pick != current_pick_num:
            self.highlight_current_pick()
            self._last_highlighted_pick = current_pick_num
    
    def clear_picks_after(self, pick_number):
        """Clear all picks after a given pick number"""
        for pick_num in range(pick_number, len(self.pick_widgets) + 1):
            if pick_num in self.pick_widgets:
                pick_frame = self.pick_widgets[pick_num]
                # Clear all child widgets that are player content
                for widget in pick_frame.winfo_children():
                    if hasattr(widget, 'place_info'):
                        info = widget.place_info()
                        if info and 'y' in info and int(info['y']) > 15:
                            widget.destroy()
                # Reset the frame
                pick_frame.config(cursor="arrow", bg=DARK_THEME['bg_tertiary'], relief='flat')
    
    def update_pick_slot(self, pick: DraftPick):
        import time
        slot_start = time.time()
        
        pick_frame = self.pick_widgets[pick.pick_number]
        
        # Clear existing player info (if any)
        for widget in pick_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget.winfo_y() > 20:
                widget.destroy()
        
        # Create click handler for this pick
        def handle_pick_click(event):
            if self.on_pick_click and self.draft_results:
                if pick.pick_number <= len(self.draft_results):
                    self.on_pick_click(pick.pick_number)
        
        # Create right-click handler for changing picks
        def handle_right_click(event):
            if hasattr(self, 'on_pick_change') and self.draft_results:
                if pick.pick_number <= len(self.draft_results):
                    self.show_change_pick_menu(event, pick)
        
        # Player container with horizontal layout - use full width
        player_frame = StyledFrame(pick_frame, bg_type='tertiary')
        player_frame.place(x=2, y=20, relwidth=0.95, height=40)
        player_frame.bind("<Button-1>", handle_pick_click)
        player_frame.bind("<Button-3>", handle_right_click)
        
        # Create horizontal layout
        content_frame = tk.Frame(player_frame, bg=DARK_THEME['bg_tertiary'])
        content_frame.pack(fill='both', expand=True)
        content_frame.bind("<Button-1>", handle_pick_click)
        content_frame.bind("<Button-3>", handle_right_click)
        
        # Player image container (for player + team logo)
        image_container = tk.Frame(content_frame, bg=DARK_THEME['bg_tertiary'], width=40, height=32)
        image_container.pack(side='left', padx=(2, 5))
        image_container.pack_propagate(False)
        image_container.bind("<Button-1>", handle_pick_click)
        image_container.bind("<Button-3>", handle_right_click)
        
        # Always create placeholder first for consistent layout
        img_label = tk.Label(
            image_container,
            bg=DARK_THEME['bg_tertiary'],
            width=5,
            height=2
        )
        img_label.place(x=0, y=0, width=40, height=32)
        img_label.bind("<Button-1>", handle_pick_click)
        img_label.bind("<Button-3>", handle_right_click)
        
        # Load player image if available
        if self.image_service and pick.player.player_id:
            # Check cache first
            player_image = self.image_service.get_image(pick.player.player_id, size=(40, 32))
            if player_image:
                img_label.configure(image=player_image)
                img_label.image = player_image
            else:
                # Load async if not cached
                def update_player_image(photo):
                    if img_label.winfo_exists():
                        img_label.configure(image=photo)
                        img_label.image = photo
                
                self.image_service.load_image_async(
                    pick.player.player_id,
                    size=(40, 32),
                    callback=update_player_image,
                    widget=self
                )
            
            # Team logo overlay
            if pick.player.team:
                # Create placeholder for team logo
                logo_placeholder = tk.Label(
                    image_container,
                    bg=DARK_THEME['bg_tertiary'],
                    width=2,
                    height=2
                )
                logo_placeholder.place(x=26, y=14, width=16, height=16)
                logo_placeholder.bind("<Button-1>", handle_pick_click)
                logo_placeholder.bind("<Button-3>", handle_right_click)
                
                # Check cache for team logo
                team_logo = self.image_service.get_image(f"team_{pick.player.team}", size=(16, 16))
                if team_logo:
                    logo_placeholder.configure(image=team_logo)
                    logo_placeholder.image = team_logo
                else:
                    # Load async
                    def update_team_logo(photo):
                        if logo_placeholder.winfo_exists():
                            logo_placeholder.configure(image=photo)
                            logo_placeholder.image = photo
                    
                    self.image_service.load_image_async(
                        f"team_{pick.player.team}",
                        size=(16, 16),
                        callback=update_team_logo,
                        widget=self
                    )
        
        # Text container
        text_frame = tk.Frame(content_frame, bg=DARK_THEME['bg_tertiary'])
        text_frame.pack(side='left', fill='both', expand=True)
        text_frame.bind("<Button-1>", handle_pick_click)
        text_frame.bind("<Button-3>", handle_right_click)
        
        # Create a single line for name and position
        info_frame = tk.Frame(text_frame, bg=DARK_THEME['bg_tertiary'])
        info_frame.pack(fill='x')
        info_frame.bind("<Button-1>", handle_pick_click)
        info_frame.bind("<Button-3>", handle_right_click)
        
        # Player name
        name_label = tk.Label(
            info_frame,
            text=self.format_player_name(pick.player.name),
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 9, 'bold'),
            anchor='w'
        )
        name_label.pack(side='left', fill='x', expand=True)
        name_label.bind("<Button-1>", handle_pick_click)
        name_label.bind("<Button-3>", handle_right_click)
        
        # Position badge inline with name
        pos_frame = tk.Frame(
            info_frame,
            bg=get_position_color(pick.player.position),
            padx=4,
            pady=1
        )
        pos_frame.pack(side='right', padx=(5, 0))
        pos_frame.bind("<Button-1>", handle_pick_click)
        pos_frame.bind("<Button-3>", handle_right_click)
        
        pos_label = tk.Label(
            pos_frame,
            text=pick.player.position,
            bg=get_position_color(pick.player.position),
            fg='white',
            font=(DARK_THEME['font_family'], 7, 'bold')
        )
        pos_label.pack()
        pos_label.bind("<Button-1>", handle_pick_click)
        pos_label.bind("<Button-3>", handle_right_click)
        
        # Add bye week indicator in bottom right
        if pick.player.bye_week:
            bye_label = tk.Label(
                pick_frame,
                text=str(pick.player.bye_week),
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 7),
                padx=2,
                pady=0
            )
            bye_label.place(relx=1.0, rely=1.0, anchor='se', x=-2, y=-2)
            bye_label.bind("<Button-1>", handle_pick_click)
            bye_label.bind("<Button-3>", handle_right_click)
    
    def highlight_current_pick(self):
        # Remove previous highlights
        for pick_frame in self.pick_widgets.values():
            pick_frame.config(bg=DARK_THEME['bg_tertiary'], relief='flat')
        
        # Highlight current pick
        if self.current_pick_num in self.pick_widgets:
            current_frame = self.pick_widgets[self.current_pick_num]
            current_frame.config(
                bg=DARK_THEME['current_pick'],
                relief='solid',
                borderwidth=2
            )
    
    def start_glow_animation(self):
        """Start glowing animation for team selection buttons"""
        self.glow_animation_running = True
        self.glow_state = 0
        self.animate_glow()
    
    def stop_glow_animation(self):
        """Stop the glowing animation"""
        self.glow_animation_running = False
    
    def animate_glow(self):
        """Animate glowing effect on team buttons"""
        if not self.glow_animation_running or self.selected_team_id:
            return
        
        # Cycle through colors for a pulsing effect
        colors = [
            DARK_THEME['button_glow'],
            DARK_THEME['button_glow_alt'],
            DARK_THEME['button_bg']
        ]
        
        color_index = self.glow_state % len(colors)
        current_color = colors[color_index]
        
        # Apply glow to all control buttons
        for button in self.team_buttons.values():
            if button['text'] == 'Sit':  # Only glow unselected buttons
                button.config(bg=current_color)
        
        self.glow_state += 1
        
        # Schedule next animation frame
        if self.glow_animation_running:
            self.after(500, self.animate_glow)  # Pulse every 500ms
    
    def show_change_pick_menu(self, event, pick: DraftPick):
        """Show context menu for changing a draft pick"""
        if not self.on_pick_change:
            return
            
        # Create context menu
        context_menu = tk.Menu(self, tearoff=0, 
                             bg=DARK_THEME['bg_secondary'], 
                             fg=DARK_THEME['text_primary'],
                             activebackground=DARK_THEME['button_active'],
                             activeforeground='white')
        
        # Add "Change Pick" option with submenu
        change_menu = tk.Menu(context_menu, tearoff=0, 
                            bg=DARK_THEME['bg_secondary'], 
                            fg=DARK_THEME['text_primary'],
                            activebackground=DARK_THEME['button_active'],
                            activeforeground='white')
        context_menu.add_cascade(label="Change Pick", menu=change_menu)
        
        # Request top 10 available players using callback
        if self.get_top_players:
            top_players = self.get_top_players(10, pick.pick_number)
            
            for player in top_players:
                player_label = f"{player.name} - {player.position} (ADP: {int(player.adp) if player.adp else 'N/A'})"
                change_menu.add_command(
                    label=player_label,
                    command=lambda p=player: self.on_pick_change(pick.pick_number, p)
                )
        
        # Show menu at mouse position
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def format_player_name(self, name):
        """Format player names with special nicknames"""
        # Strip any whitespace and normalize the name
        name = name.strip()
        
        special_names = {
            "Amon-Ra St. Brown": "SUN GOD",
            "Brian Thomas Jr.": "BTJ",
            "Brian Thomas": "BTJ",  # Without Jr.
            "Justin Jefferson": "JJ",
            "Christian McCaffrey": "CMC",
            "Jonathan Taylor": "JT",
            "Jayden Daniels": "JD",
            "Bijan Robinson": "BIJAN"
        }
        
        # Check exact match first
        if name in special_names:
            return special_names[name]
        
        # Check if the name contains key parts for partial matching
        name_lower = name.lower()
        if "bijan" in name_lower and "robinson" in name_lower:
            return "BIJAN"
        elif "amon" in name_lower and "ra" in name_lower:
            return "SUN GOD"
        elif "brian" in name_lower and "thomas" in name_lower:
            return "BTJ"
        elif "justin" in name_lower and "jefferson" in name_lower:
            return "JJ"
        elif "christian" in name_lower and "mccaffrey" in name_lower:
            return "CMC"
        elif "jonathan" in name_lower and "taylor" in name_lower:
            return "JT"
        elif "jayden" in name_lower and "daniels" in name_lower:
            return "JD"
        
        # Default: First initial + last name
        parts = name.split()
        if len(parts) >= 2:
            # Handle suffixes like Jr., III, etc.
            if parts[-1] in ["Jr.", "Jr", "Sr.", "Sr", "II", "III", "IV", "V"]:
                if len(parts) >= 3:
                    return f"{parts[0][0]}. {parts[-2]}"
                else:
                    return name  # Fallback if only 2 parts with suffix
            else:
                return f"{parts[0][0]}. {parts[-1]}"
        return name  # Fallback for single-word names
    
    def on_resize(self, event):
        """Handle window resize events"""
        if not self.canvas or not self.scrollable_frame:
            return
            
        # Only respond to width changes
        if hasattr(self, '_last_width') and self._last_width == event.width:
            return
            
        self._last_width = event.width
        self._is_resizing = True
        
        # Cancel any pending resize
        if hasattr(self, '_resize_after_id'):
            self.after_cancel(self._resize_after_id)
        
        # Debounce resize updates - wait 50ms after dragging stops
        self._resize_after_id = self.after(50, lambda: self._do_resize(event.width))
    
    def _do_resize(self, width):
        """Actually perform the resize calculations"""
        if not self.canvas or not self.scrollable_frame:
            return
        
        # Calculate new column width
        available_width = width - 40  # Subtract padding and scrollbar
        new_col_width = max(120, available_width // self.num_teams)
        
        # Update all column widths
        for i in range(self.num_teams):
            self.scrollable_frame.grid_columnconfigure(i, minsize=new_col_width)
        
        # Update canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Clear resizing flag
        self._is_resizing = False
    
    def update_team_names(self, teams):
        """Update team names in the draft board headers"""
        for team_id, team in teams.items():
            if team_id in self.team_labels:
                self.team_labels[team_id].config(text=team.name)
                # Re-bind hover events with new team name
                self.team_labels[team_id].bind("<Enter>", lambda e, name=team.name: self.show_manager_tooltip(e, name))
                self.team_labels[team_id].bind("<Leave>", lambda e: self.hide_manager_tooltip())
    
    def set_user_team(self, team_id: int):
        """Set the user's team and update the UI accordingly"""
        self.select_team(team_id)
    
    def show_manager_tooltip(self, event, team_name):
        """Show tooltip with manager notes"""
        # Get the note for this manager
        note = self.manager_notes_service.get_note(team_name)
        
        if not note:
            return
        
        # Destroy any existing tooltip
        self.hide_manager_tooltip()
        
        # Create tooltip window
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        
        # Create label with note
        label = tk.Label(
            self.tooltip,
            text=note,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=5,
            wraplength=300,
            justify="left"
        )
        label.pack()
        
        # Position tooltip near the cursor
        x = event.widget.winfo_rootx() + event.x + 10
        y = event.widget.winfo_rooty() + event.y + 10
        self.tooltip.geometry(f"+{x}+{y}")
        
        # Ensure tooltip stays on top
        self.tooltip.lift()
    
    def hide_manager_tooltip(self):
        """Hide the manager tooltip"""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None