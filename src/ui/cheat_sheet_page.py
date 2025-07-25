import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import List, Dict, Tuple, Optional
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame, StyledButton
import os
from PIL import Image, ImageTk
import json


class CheatSheetPage(StyledFrame):
    def __init__(self, parent, players: List[Player], draft_app=None, **kwargs):
        super().__init__(parent, bg_type='primary', **kwargs)
        self.all_players = players
        self.draft_app = draft_app
        
        # Configuration
        self.image_size = (90, 72)  # Same as ADP page
        
        # Nickname mappings
        self.nicknames = {
            'AMON-RA ST. BROWN': 'Sun God',
            'AMON RA ST BROWN': 'Sun God',
            'JAMESON WILLIAMS': 'Jamo',
            'JUSTIN JEFFERSON': 'JJ',
            'JA\'MARR CHASE': 'Chase',
            'CEEDEE LAMB': 'CD',
            'TYREEK HILL': 'Cheetah',
            'CHRISTIAN MCCAFFREY': 'CMC',
            'JONATHAN TAYLOR': 'JT',
            'BREECE HALL': 'Breece',
            'BIJAN ROBINSON': 'Bijan',
            'JAHMYR GIBBS': 'Gibbs',
            'CHRIS OLAVE': 'Olave',
            'BRANDON AIYUK': 'Aiyuk',
            'DEEBO SAMUEL': 'Deebo',
            'AJ BROWN': 'AJB',
            'DAVANTE ADAMS': 'Tae',
            'STEFON DIGGS': 'Diggs',
            'CALVIN RIDLEY': 'Ridley',
            'DK METCALF': 'DK',
            'MIKE EVANS': 'Evans',
            'AMARI COOPER': 'Coop',
            'JAYLEN WADDLE': 'Waddle',
            'CHRISTIAN WATSON': 'Watson',
            'TEE HIGGINS': 'Tee',
            'MICHAEL PITTMAN': 'MPJ',
            'JAHAN DOTSON': 'JD',
            'TRAVIS KELCE': 'Kelce',
            'MARK ANDREWS': 'Mandrews',
            'TJ HOCKENSON': 'Hock',
            'KYLE PITTS': 'Pitts',
            'DARREN WALLER': 'Waller',
            'GEORGE KITTLE': 'Kittle',
            'DALLAS GOEDERT': 'Goedert',
            'JOSH ALLEN': 'JA17',
            'JALEN HURTS': 'Hurts',
            'PATRICK MAHOMES': 'Mahomes',
            'LAMAR JACKSON': 'Lamar',
            'JOE BURROW': 'Joey B',
            'JUSTIN HERBERT': 'Herbie',
            'TREVOR LAWRENCE': 'TLaw',
            'DANIEL JONES': 'Danny Dimes',
            'JORDAN LOVE': 'Love',
            'CJ STROUD': 'CJ',
            'ANTHONY RICHARDSON': 'AR',
            'BRYCE YOUNG': 'BY',
            'WILL LEVIS': 'Levis'
        }
        
        # State
        self.player_images = {}  # Cache player images
        self.player_widgets = {}  # Map player_id to widget
        self.drag_data = None  # Current drag information
        self.drop_indicator = None
        self.tiers = self.load_tiers()  # Load saved tiers or create default
        
        self.setup_ui()
        # Delay initial display to ensure UI is ready
        self.after(10, self.update_display)
        
        # Set up recursive mouse wheel binding after initial display
        self.after(100, self.setup_recursive_mousewheel)
    
    def get_short_name(self, player: Player) -> str:
        """Get short name (nickname or last name) for a player"""
        # First check for nicknames using formatted name
        formatted = player.format_name() if hasattr(player, 'format_name') else player.name.upper()
        
        # Check if we have a nickname for this player
        if formatted in self.nicknames:
            return self.nicknames[formatted]
        
        # Otherwise, extract last name
        # Remove any parenthetical info first
        name = player.name.split('(')[0].strip()
        
        # Handle special suffixes
        name = name.replace(' JR', '').replace(' SR', '').replace(' III', '').replace(' II', '').replace(' IV', '').replace(' V', '')
        
        # Split and get last part
        parts = name.split()
        if len(parts) > 1:
            # For names like "Amon-Ra St. Brown", we want "St. Brown"
            if len(parts) >= 3 and parts[-2].lower() in ['st', 'st.', 'de', 'van', 'von']:
                return f"{parts[-2]} {parts[-1]}"
            else:
                return parts[-1]
        else:
            return name
    
    def setup_recursive_mousewheel(self):
        """Recursively bind mouse wheel events to all widgets"""
        def bind_mousewheel_to_widget(widget, canvas):
            """Bind mouse wheel events to a widget and all its children"""
            def on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
                return "break"
            
            # Bind to this widget
            widget.bind('<MouseWheel>', on_mousewheel)
            widget.bind('<Button-4>', lambda e: canvas.yview_scroll(-1, 'units'))
            widget.bind('<Button-5>', lambda e: canvas.yview_scroll(1, 'units'))
            widget.bind('<Enter>', lambda e: canvas.focus_set())
            
            # Recursively bind to all children
            for child in widget.winfo_children():
                bind_mousewheel_to_widget(child, canvas)
        
        # Bind to tiers area
        if hasattr(self, 'tiers_scrollable') and hasattr(self, 'tiers_canvas'):
            bind_mousewheel_to_widget(self.tiers_scrollable, self.tiers_canvas)
        
        # Bind to available players area
        if hasattr(self, 'avail_scrollable') and hasattr(self, 'avail_canvas'):
            bind_mousewheel_to_widget(self.avail_scrollable, self.avail_canvas)
    
    def load_tiers(self) -> Dict[str, List[str]]:
        """Load saved tiers from file or create default tiers"""
        # Use absolute path to ensure consistency
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        tier_file = os.path.join(base_dir, 'data', 'cheat_sheet_tiers.json')
        
        if os.path.exists(tier_file):
            try:
                with open(tier_file, 'r') as f:
                    loaded_tiers = json.load(f)
                    print(f"Loaded cheat sheet tiers from {tier_file}")
                    # Ensure it's a dict with list values
                    if isinstance(loaded_tiers, dict):
                        # Check if we need to migrate from old tier names
                        if "Elite" in loaded_tiers or "Tier 1" in loaded_tiers:
                            print("Migrating from old tier names to round names")
                            return self.migrate_old_tiers(loaded_tiers)
                        return loaded_tiers
            except Exception as e:
                print(f"Error loading cheat sheet tiers: {e}")
        
        # Default tiers - named by rounds
        print("Using default cheat sheet tiers")
        return {
            "Round 1": [],
            "Round 2": [],
            "Round 3": [],
            "Round 4": [],
            "Round 5": [],
            "Round 6": [],
            "Round 7": [],
            "Round 8": [],
            "Round 9": [],
            "Round 10": [],
            "Round 11": [],
            "Round 12": [],
            "Round 13": [],
            "Round 14": [],
            "Round 15": []
        }
    
    def migrate_old_tiers(self, old_tiers: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Migrate from old tier names to round names"""
        new_tiers = {}
        
        # Mapping of old names to new names
        name_mapping = {
            "Elite": "Round 1",
            "Tier 1": "Round 2", 
            "Tier 2": "Round 3",
            "Tier 3": "Round 4",
            "Tier 4": "Round 5",
            "Tier 5": "Round 6",
            "Sleepers": "Round 7",
            "Avoid": "Round 8"
        }
        
        # Migrate existing data
        for old_name, players in old_tiers.items():
            new_name = name_mapping.get(old_name, old_name)
            if new_name.startswith("Round"):
                new_tiers[new_name] = players
        
        # Add any missing rounds
        for i in range(1, 16):
            round_name = f"Round {i}"
            if round_name not in new_tiers:
                new_tiers[round_name] = []
        
        # Save the migrated data
        self.tiers = new_tiers
        self.save_tiers()
        
        return new_tiers
    
    def save_tiers(self):
        """Save tiers to file"""
        # Use absolute path to ensure consistency
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        tier_file = os.path.join(data_dir, 'cheat_sheet_tiers.json')
        try:
            with open(tier_file, 'w') as f:
                json.dump(self.tiers, f, indent=2)
            print(f"Saved cheat sheet tiers to {tier_file}")
            
            # Notify draft app that tiers have changed
            if hasattr(self, 'draft_app') and self.draft_app:
                self.draft_app._cheat_sheet_needs_sync = True
        except Exception as e:
            print(f"Error saving cheat sheet tiers: {e}")
            # Try to show error to user
            try:
                from tkinter import messagebox
                messagebox.showerror("Save Error", f"Failed to save cheat sheet: {e}")
            except:
                pass
    
    def setup_ui(self):
        # Header
        header_frame = StyledFrame(self, bg_type='secondary')
        header_frame.pack(fill='x', padx=0, pady=(5, 5))
        
        title_label = tk.Label(
            header_frame,
            text="CHEAT SHEET",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 16, 'bold')
        )
        title_label.pack(side='left', padx=10, pady=5)
        
        # Instructions
        instructions_label = tk.Label(
            header_frame,
            text="(Drag players between tiers • Right-click to add/remove tiers)",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 10, 'italic')
        )
        instructions_label.pack(side='left', padx=10)
        
        # Button frame
        btn_frame = tk.Frame(header_frame, bg=DARK_THEME['bg_secondary'])
        btn_frame.pack(side='right', padx=10)
        
        # Add tier button
        add_tier_btn = StyledButton(
            btn_frame,
            text="ADD TIER",
            command=self.add_tier,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=15,
            pady=5
        )
        add_tier_btn.pack(side='left', padx=5)
        
        # Reset button
        reset_btn = StyledButton(
            btn_frame,
            text="RESET",
            command=self.reset_tiers,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=15,
            pady=5
        )
        reset_btn.pack(side='left', padx=5)
        
        # Show available only checkbox
        self.show_available_only = tk.BooleanVar(value=False)
        available_check = tk.Checkbutton(
            header_frame,
            text="Show Available Only",
            variable=self.show_available_only,
            command=self.update_display,
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            selectcolor=DARK_THEME['bg_tertiary'],
            activebackground=DARK_THEME['bg_secondary']
        )
        available_check.pack(side='right', padx=(5, 20))
        
        # Main content area with scrolling
        content_frame = StyledFrame(self, bg_type='primary')
        content_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Create two panels: tiers (left) and available players (right)
        paned = tk.PanedWindow(
            content_frame,
            orient='horizontal',
            bg=DARK_THEME['bg_primary'],
            sashrelief='raised',
            sashwidth=5
        )
        paned.pack(fill='both', expand=True)
        
        # Left panel - Tiers
        self.create_tiers_panel(paned)
        
        # Right panel - Available players
        self.create_available_panel(paned)
        
        # Set sash position (70% for tiers, 30% for available)
        def set_sash_position():
            width = paned.winfo_width()
            if width > 1:
                paned.sash_place(0, int(width * 0.7), 0)
        self.after(200, set_sash_position)
    
    def create_tiers_panel(self, parent):
        """Create the tiers panel with scrolling"""
        tiers_frame = StyledFrame(parent, bg_type='primary')
        parent.add(tiers_frame)
        
        # Canvas for scrolling
        self.tiers_canvas = tk.Canvas(
            tiers_frame,
            bg=DARK_THEME['bg_primary'],
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            tiers_frame,
            orient='vertical',
            command=self.tiers_canvas.yview,
            bg=DARK_THEME['bg_tertiary']
        )
        
        self.tiers_scrollable = StyledFrame(self.tiers_canvas, bg_type='primary')
        self.tiers_scrollable.bind(
            "<Configure>",
            lambda e: self.tiers_canvas.configure(scrollregion=self.tiers_canvas.bbox("all"))
        )
        
        self.tiers_canvas_window = self.tiers_canvas.create_window((0, 0), window=self.tiers_scrollable, anchor="nw")
        
        # Make scrollable frame fill canvas width
        def configure_frame_width(event=None):
            canvas_width = self.tiers_canvas.winfo_width()
            self.tiers_canvas.itemconfig(self.tiers_canvas_window, width=canvas_width)
        
        self.tiers_canvas.bind('<Configure>', configure_frame_width)
        self.tiers_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.tiers_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            self.tiers_canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            return "break"
        
        # Bind to canvas, scrollable frame, and all children
        self.tiers_canvas.bind('<MouseWheel>', on_mousewheel)
        self.tiers_canvas.bind('<Button-4>', lambda e: self.tiers_canvas.yview_scroll(-1, 'units'))
        self.tiers_canvas.bind('<Button-5>', lambda e: self.tiers_canvas.yview_scroll(1, 'units'))
        
        self.tiers_scrollable.bind('<MouseWheel>', on_mousewheel)
        self.tiers_scrollable.bind('<Button-4>', lambda e: self.tiers_canvas.yview_scroll(-1, 'units'))
        self.tiers_scrollable.bind('<Button-5>', lambda e: self.tiers_canvas.yview_scroll(1, 'units'))
        
        # Set focus when mouse enters
        self.tiers_canvas.bind('<Enter>', lambda e: self.tiers_canvas.focus_set())
        self.tiers_scrollable.bind('<Enter>', lambda e: self.tiers_canvas.focus_set())
    
    def create_available_panel(self, parent):
        """Create the available players panel"""
        avail_frame = StyledFrame(parent, bg_type='secondary')
        parent.add(avail_frame)
        
        # Header with controls
        header_frame = tk.Frame(avail_frame, bg=DARK_THEME['bg_secondary'])
        header_frame.pack(fill='x', pady=(5, 5))
        
        header = tk.Label(
            header_frame,
            text="AVAILABLE PLAYERS",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        header.pack(pady=5)
        
        # Controls frame
        controls_frame = tk.Frame(header_frame, bg=DARK_THEME['bg_secondary'])
        controls_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        # Reorganize button
        reorganize_btn = StyledButton(
            controls_frame,
            text="REORGANIZE",
            command=self.reorganize_available_players,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 9),
            padx=10,
            pady=3
        )
        reorganize_btn.pack(side='left', padx=2)
        
        # Position filter buttons
        self.avail_position_var = tk.StringVar(value="ALL")
        positions = ["ALL", "QB", "RB", "WR", "TE"]
        
        tk.Label(
            controls_frame,
            text="Filter:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        ).pack(side='left', padx=(10, 5))
        
        for pos in positions:
            btn = tk.Button(
                controls_frame,
                text=pos,
                command=lambda p=pos: self.filter_available_position(p),
                bg=DARK_THEME['button_bg'] if pos == "ALL" else get_position_color(pos),
                fg=DARK_THEME['text_primary'] if pos == "ALL" else 'white',
                font=(DARK_THEME['font_family'], 8),
                bd=0,
                padx=8,
                pady=2,
                cursor='hand2'
            )
            btn.pack(side='left', padx=1)
        
        # Canvas for scrolling
        self.avail_canvas = tk.Canvas(
            avail_frame,
            bg=DARK_THEME['bg_secondary'],
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            avail_frame,
            orient='vertical',
            command=self.avail_canvas.yview,
            bg=DARK_THEME['bg_tertiary']
        )
        
        self.avail_scrollable = StyledFrame(self.avail_canvas, bg_type='secondary')
        self.avail_scrollable.bind(
            "<Configure>",
            lambda e: self.avail_canvas.configure(scrollregion=self.avail_canvas.bbox("all"))
        )
        
        self.avail_canvas_window = self.avail_canvas.create_window((0, 0), window=self.avail_scrollable, anchor="nw")
        
        # Make scrollable frame fill canvas width
        def configure_frame_width(event=None):
            canvas_width = self.avail_canvas.winfo_width()
            self.avail_canvas.itemconfig(self.avail_canvas_window, width=canvas_width)
        
        self.avail_canvas.bind('<Configure>', configure_frame_width)
        self.avail_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.avail_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            self.avail_canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            return "break"
        
        # Bind to canvas and scrollable frame
        self.avail_canvas.bind('<MouseWheel>', on_mousewheel)
        self.avail_canvas.bind('<Button-4>', lambda e: self.avail_canvas.yview_scroll(-1, 'units'))
        self.avail_canvas.bind('<Button-5>', lambda e: self.avail_canvas.yview_scroll(1, 'units'))
        
        # Also bind to the scrollable frame and set focus on enter
        self.avail_scrollable.bind('<MouseWheel>', on_mousewheel)
        self.avail_scrollable.bind('<Button-4>', lambda e: self.avail_canvas.yview_scroll(-1, 'units'))
        self.avail_scrollable.bind('<Button-5>', lambda e: self.avail_canvas.yview_scroll(1, 'units'))
        
        # Set focus when mouse enters
        self.avail_canvas.bind('<Enter>', lambda e: self.avail_canvas.focus_set())
        self.avail_scrollable.bind('<Enter>', lambda e: self.avail_canvas.focus_set())
    
    def calculate_snake_draft_picks(self, draft_position: int, num_teams: int, num_rounds: int) -> List[int]:
        """Calculate all picks for a given draft position in a snake draft with 3rd round reversal"""
        picks = []
        for round_num in range(1, num_rounds + 1):
            if round_num == 1:
                # Round 1: Normal order (1-10)
                pick = draft_position
            elif round_num == 2:
                # Round 2: Reverse order (10-1)
                pick = num_teams + (num_teams - draft_position + 1)
            elif round_num == 3:
                # Round 3: Same as round 2 (3rd round reversal)
                pick = 2 * num_teams + (num_teams - draft_position + 1)
            else:
                # Rounds 4+: Continue normal snake pattern
                if round_num % 2 == 0:  # Even rounds (4, 6, 8, etc.)
                    pick = (round_num - 1) * num_teams + draft_position
                else:  # Odd rounds (5, 7, 9, etc.)
                    pick = round_num * num_teams - draft_position + 1
            picks.append(pick)
        return picks
    
    def get_player_image(self, player: Player) -> Optional[ImageTk.PhotoImage]:
        """Get or create player image"""
        if player.player_id in self.player_images:
            return self.player_images[player.player_id]
        
        # Try to load player image
        image_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'assets', 'player_images',
            f"{player.player_id}.jpg"
        )
        
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img = img.resize(self.image_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.player_images[player.player_id] = photo
                return photo
            except:
                pass
        
        return None
    
    def update_display(self):
        """Update the display with current tiers"""
        # Clear existing widgets
        for widget in self.tiers_scrollable.winfo_children():
            widget.destroy()
        for widget in self.avail_scrollable.winfo_children():
            widget.destroy()
        self.player_widgets.clear()
        
        # Get all player IDs that are in tiers
        tiered_player_ids = set()
        for tier_players in self.tiers.values():
            tiered_player_ids.update(tier_players)
        
        # Display tiers - colors for rounds
        tier_colors = {
            "Round 1": '#FF5E5B',      # Red
            "Round 2": '#FFB347',      # Orange
            "Round 3": '#FFD700',      # Gold
            "Round 4": '#4ECDC4',      # Teal
            "Round 5": '#7B68EE',      # Purple
            "Round 6": '#87CEEB',      # Sky Blue
            "Round 7": '#90EE90',      # Light Green
            "Round 8": '#FF69B4',      # Hot Pink
            "Round 9": '#DDA0DD',      # Plum
            "Round 10": '#F0E68C',     # Khaki
            "Round 11": '#B0C4DE',     # Light Steel Blue
            "Round 12": '#F4A460',     # Sandy Brown
            "Round 13": '#D3D3D3',     # Light Gray
            "Round 14": '#98FB98',     # Pale Green
            "Round 15": '#FFE4B5'      # Moccasin
        }
        
        for tier_name, player_ids in self.tiers.items():
            self.create_tier_section(tier_name, player_ids, tier_colors.get(tier_name, '#808080'))
        
        # Display available players (not in any tier)
        available_players = [p for p in self.all_players if p.player_id not in tiered_player_ids]
        
        # Filter out drafted players if show_available_only is checked
        if hasattr(self, 'show_available_only') and self.show_available_only.get():
            try:
                if self.draft_app and hasattr(self.draft_app, 'draft_engine'):
                    drafted_ids = {pick.player.player_id for pick in self.draft_app.draft_engine.draft_history}
                    available_players = [p for p in available_players if p.player_id not in drafted_ids]
            except:
                pass
        
        # Apply position filter if active
        if hasattr(self, 'avail_position_var') and self.avail_position_var.get() != "ALL":
            pos_filter = self.avail_position_var.get()
            available_players = [p for p in available_players if p.position == pos_filter]
        
        # Sort by ADP
        available_players.sort(key=lambda p: p.adp if p.adp else 999)
        
        # Create player widgets in a grid
        players_per_row = 3
        widget_height = 145
        spacing = 5
        
        if available_players:
            total_rows = (len(available_players) + players_per_row - 1) // players_per_row
            # Set minimum height for scrollable frame to contain all widgets
            min_height = total_rows * (widget_height + spacing) + 20
            self.avail_scrollable.configure(height=min_height)
            
            for i, player in enumerate(available_players):
                row = i // players_per_row
                col = i % players_per_row
                self.create_player_widget(self.avail_scrollable, player, None, row, col, is_available=True)
        else:
            # Show message when no available players
            empty_label = tk.Label(
                self.avail_scrollable,
                text="All players are assigned to tiers",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 12)
            )
            empty_label.pack(pady=50)
        
        # Update scroll regions
        self.tiers_scrollable.update_idletasks()
        self.tiers_canvas.configure(scrollregion=self.tiers_canvas.bbox("all"))
        self.avail_scrollable.update_idletasks()
        self.avail_canvas.configure(scrollregion=self.avail_canvas.bbox("all"))
        
        # Re-bind mouse wheel events to new widgets
        self.after(10, self.setup_recursive_mousewheel)
    
    def create_tier_section(self, tier_name: str, player_ids: List[str], color: str):
        """Create a round section with header and players"""
        # Round header
        header_frame = tk.Frame(self.tiers_scrollable, bg=DARK_THEME['bg_primary'], height=35)
        header_frame.pack(fill='x', padx=0, pady=(5, 2))
        
        # Get the specific pick number for this round
        my_pick_num = None
        try:
            # Extract round number from tier name (e.g., "Round 1" -> 1)
            if tier_name.startswith("Round "):
                round_num = int(tier_name.split(" ")[1])
                
                # Try to get draft position from draft app
                draft_pos = None
                
                if self.draft_app and hasattr(self.draft_app, 'user_team_id') and self.draft_app.user_team_id is not None:
                    # Teams dict uses integer keys, user_team_id is an integer
                    # Find the position based on sorted team IDs
                    sorted_team_ids = sorted(self.draft_app.teams.keys())
                    for i, team_id in enumerate(sorted_team_ids):
                        if team_id == self.draft_app.user_team_id:
                            draft_pos = i + 1  # 1-based position
                            break
                else:
                    # Default to position 8 if no team selected
                    draft_pos = 8
                    
                if draft_pos:
                        # Calculate snake draft picks (10 team league)
                        my_picks = self.calculate_snake_draft_picks(draft_pos, 10, 20)
                        if round_num <= len(my_picks):
                            my_pick_num = my_picks[round_num - 1]  # 0-based index
        except Exception as e:
            print(f"Error getting pick number: {e}")
        
        # Round label with pick info
        tier_text = f"{tier_name} ({len(player_ids)})"
        if my_pick_num:
            tier_text = f"{tier_name} - Pick {my_pick_num}"
        
        tier_label = tk.Label(
            header_frame,
            text=tier_text,
            bg=color,
            fg='white',
            font=(DARK_THEME['font_family'], 12, 'bold'),
            padx=15,
            pady=5
        )
        tier_label.pack(side='left', padx=10)
        
        # Right-click menu for tier operations
        tier_menu = tk.Menu(tier_label, tearoff=0)
        tier_menu.add_command(label="Rename Tier", command=lambda: self.rename_tier(tier_name))
        tier_menu.add_command(label="Delete Tier", command=lambda: self.delete_tier(tier_name))
        tier_menu.add_separator()
        tier_menu.add_command(label="Clear Tier", command=lambda: self.clear_tier(tier_name))
        
        def show_tier_menu(event):
            tier_menu.post(event.x_root, event.y_root)
        
        tier_label.bind("<Button-3>", show_tier_menu)  # Right-click
        tier_label.bind("<Button-2>", show_tier_menu)  # Middle-click for Mac
        
        # Tier content frame
        tier_frame = StyledFrame(self.tiers_scrollable, bg_type='secondary')
        tier_frame.pack(fill='x', padx=0, pady=(0, 5))
        tier_frame.tier_name = tier_name
        
        # Get player objects in the order they appear in the tier
        players = []
        # Get list of drafted players if needed
        drafted_ids = set()
        if hasattr(self, 'show_available_only') and self.show_available_only.get():
            # Get drafted player IDs from draft app if available
            try:
                if self.draft_app and hasattr(self.draft_app, 'draft_engine'):
                    drafted_ids = {pick.player.player_id for pick in self.draft_app.draft_engine.draft_history}
            except:
                pass
        
        for player_id in player_ids:
            # Skip drafted players if show_available_only is checked
            if player_id in drafted_ids:
                continue
            player = next((p for p in self.all_players if p.player_id == player_id), None)
            if player:
                players.append(player)
        
        # Calculate height based on number of rows needed
        players_per_row = 10  # Same as ADP page
        num_rows = max(1, (len(players) + players_per_row - 1) // players_per_row)
        row_height = 150
        frame_height = num_rows * row_height + 10  # Add padding
        
        tier_frame.configure(height=frame_height)
        tier_frame.pack_propagate(False)
        
        # Create player widgets in order
        # Calculate starting rank based on previous tiers
        starting_rank = 1
        for t_name, t_players in self.tiers.items():
            if t_name == tier_name:
                break
            starting_rank += len(t_players)
        
        for i, player in enumerate(players):
            row = i // players_per_row
            col = i % players_per_row
            rank = starting_rank + i
            self.create_player_widget(tier_frame, player, tier_name, row, col, rank=rank)
    
    def create_player_widget(self, parent: tk.Frame, player: Player, tier_name: Optional[str], 
                           row: int, col: int, is_available: bool = False, rank: Optional[int] = None):
        """Create a draggable player widget"""
        # Player container
        player_frame = tk.Frame(
            parent,
            bg=DARK_THEME['bg_tertiary'],
            relief='solid',
            borderwidth=1,
            highlightbackground=DARK_THEME['border'],
            highlightthickness=1
        )
        
        # Position based on grid
        if is_available:
            # Available players panel - 3 per row
            widget_width = 1.0 / 3 - 0.01
            widget_height = 145
            # Calculate absolute y position based on row
            y_position = row * (widget_height + 5)
            player_frame.place(
                relx=col / 3,
                y=y_position,
                relwidth=widget_width,
                height=widget_height
            )
        else:
            # Tier panel - 10 per row
            widget_width = 1.0 / 10 - 0.005  # Slightly smaller to create more gap
            widget_height = 145
            player_frame.place(
                relx=col / 10,
                rely=row * widget_height / parent.winfo_reqheight() if parent.winfo_reqheight() > 0 else row * 0.15,
                relwidth=widget_width,
                height=widget_height
            )
        
        # Store player reference
        player_frame.player = player
        player_frame.tier_name = tier_name
        player_frame.is_available = is_available
        self.player_widgets[player.player_id] = player_frame
        
        # Player image or placeholder
        image = self.get_player_image(player)
        if image:
            image_label = tk.Label(
                player_frame,
                image=image,
                bg=DARK_THEME['bg_tertiary']
            )
            image_label.image = image  # Keep reference
            image_label.pack(pady=(10, 2))
        else:
            # Position badge as placeholder
            pos_color = get_position_color(player.position)
            badge = tk.Label(
                player_frame,
                text=player.position,
                bg=pos_color,
                fg='white',
                font=(DARK_THEME['font_family'], 12, 'bold'),
                width=5,
                height=2
            )
            badge.pack(pady=(15, 5))
        
        # Player name - use short name (nickname or last name)
        if is_available:
            # For available players, show name with ADP
            name_text = f"{self.get_short_name(player)}\n({int(player.adp) if player.adp else 'N/A'})"
        else:
            name_text = self.get_short_name(player)
        
        name_label = tk.Label(
            player_frame,
            text=name_text,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10 if not is_available else 9),
            wraplength=120 if is_available else 300
        )
        name_label.pack(pady=(2, 2))
        
        # Rank number (only for tiered players, not available)
        if not is_available and rank is not None:
            rank_label = tk.Label(
                player_frame,
                text=f"#{rank}",
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 9, 'bold')
            )
            rank_label.pack(pady=(0, 3))
        
        # Make draggable
        self.make_draggable(player_frame)
        
        # Hover effect
        def on_enter(e):
            if not self.drag_data or self.drag_data['widget'] != player_frame:
                player_frame.configure(highlightbackground='#4ECDC4', highlightthickness=2)
        
        def on_leave(e):
            if not self.drag_data or self.drag_data['widget'] != player_frame:
                player_frame.configure(highlightbackground=DARK_THEME['border'], highlightthickness=1)
        
        player_frame.bind('<Enter>', on_enter)
        player_frame.bind('<Leave>', on_leave)
    
    def make_draggable(self, widget: tk.Widget):
        """Make a widget draggable"""
        def start_drag(event):
            if hasattr(widget, 'player'):
                # Create floating player widget
                self.create_floating_player(widget.player, event.x_root, event.y_root)
                
                self.drag_data = {
                    'widget': widget,
                    'player': widget.player,
                    'start_x': event.x_root,
                    'start_y': event.y_root,
                    'offset_x': event.x,
                    'offset_y': event.y,
                    'source_tier': widget.tier_name if hasattr(widget, 'tier_name') else None
                }
                # Visual feedback - make original widget semi-transparent
                widget.configure(highlightbackground=DARK_THEME['border'], highlightthickness=1)
                # Fade the original widget
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(fg=DARK_THEME['text_muted'])
                        # Make background labels semi-transparent looking
                        current_bg = child.cget('bg')
                        if current_bg == DARK_THEME['bg_tertiary']:
                            child._original_bg = current_bg
                            child.configure(bg=DARK_THEME['bg_secondary'])
        
        def on_drag(event):
            if self.drag_data:
                # Update floating player position
                if hasattr(self, 'floating_player'):
                    x = event.x_root - 45  # Center the floating widget on cursor
                    y = event.y_root - 45
                    self.floating_player.geometry(f"+{x}+{y}")
                
                # Update drop indicator
                self.update_drop_indicator(event.x_root, event.y_root)
        
        def end_drag(event):
            if self.drag_data:
                # Find drop target
                x, y = event.x_root, event.y_root
                target = self.find_drop_target(x, y)
                
                if target:
                    self.handle_drop(self.drag_data['widget'], target)
                
                # Reset visual state
                try:
                    self.drag_data['widget'].configure(
                        highlightbackground=DARK_THEME['border'],
                        highlightthickness=1
                    )
                    # Restore child widget colors
                    for child in self.drag_data['widget'].winfo_children():
                        if isinstance(child, tk.Label):
                            child.configure(fg=DARK_THEME['text_primary'])
                            # Restore background color
                            if child.cget('bg') == DARK_THEME['bg_secondary'] and hasattr(child, '_original_bg'):
                                child.configure(bg=child._original_bg)
                except tk.TclError:
                    pass
                
                # Clear floating player
                if hasattr(self, 'floating_player'):
                    try:
                        self.floating_player.destroy()
                    except:
                        pass
                    delattr(self, 'floating_player')
                
                # Clear drop indicator
                if self.drop_indicator and hasattr(self.drop_indicator, 'destroy'):
                    try:
                        self.drop_indicator.destroy()
                    except:
                        pass
                    self.drop_indicator = None
                
                self.drag_data = None
        
        # Bind to all children too
        def bind_recursive(w):
            w.bind('<Button-1>', start_drag)
            w.bind('<B1-Motion>', on_drag)
            w.bind('<ButtonRelease-1>', end_drag)
            for child in w.winfo_children():
                bind_recursive(child)
        
        bind_recursive(widget)
    
    def create_floating_player(self, player: Player, x: int, y: int):
        """Create a floating player widget that follows the mouse"""
        # Create a toplevel window for the floating player
        self.floating_player = tk.Toplevel(self)
        self.floating_player.overrideredirect(True)  # Remove window decorations
        self.floating_player.attributes('-topmost', True)  # Keep on top
        
        # Make it semi-transparent on Windows
        try:
            self.floating_player.attributes('-alpha', 0.8)
        except:
            pass
        
        # Create the player widget content
        float_frame = tk.Frame(
            self.floating_player,
            bg=DARK_THEME['bg_tertiary'],
            relief='solid',
            borderwidth=2,
            highlightbackground='#FF5E5B',
            highlightthickness=2
        )
        float_frame.pack()
        
        # Add player image or placeholder
        image = self.get_player_image(player)
        if image:
            image_label = tk.Label(
                float_frame,
                image=image,
                bg=DARK_THEME['bg_tertiary']
            )
            image_label.image = image  # Keep reference
            image_label.pack(pady=(5, 2))
        else:
            # Position badge as placeholder
            pos_color = get_position_color(player.position)
            badge = tk.Label(
                float_frame,
                text=player.position,
                bg=pos_color,
                fg='white',
                font=(DARK_THEME['font_family'], 10, 'bold'),
                width=4,
                height=2
            )
            badge.pack(pady=(5, 2))
        
        # Player name - use short name (nickname or last name)
        name_label = tk.Label(
            float_frame,
            text=self.get_short_name(player),
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 9),
            wraplength=120
        )
        name_label.pack(pady=(2, 5))
        
        # Position the floating window
        self.floating_player.geometry(f"+{x-45}+{y-45}")
        
        # Ensure it's visible
        self.floating_player.update()
    
    def update_drop_indicator(self, x: int, y: int):
        """Update visual feedback for drop location"""
        target = self.find_drop_target(x, y)
        
        # Clean up previous indicator
        if self.drop_indicator and hasattr(self.drop_indicator, 'destroy'):
            try:
                self.drop_indicator.destroy()
            except:
                pass
            self.drop_indicator = None
        
        if target and target != self.drag_data['widget']:
            try:
                if hasattr(target, 'player'):
                    # Dropping on another player - show indicator
                    self.drop_indicator = tk.Frame(
                        target.master,
                        bg='#4ECDC4',
                        height=140,
                        width=5
                    )
                    target_x = target.winfo_x()
                    self.drop_indicator.place(x=target_x - 2, y=target.winfo_y(), height=140)
                elif hasattr(target, 'tier_name') and isinstance(target, StyledFrame):
                    # Dropping on a tier frame - create a visual overlay
                    self.drop_indicator = tk.Frame(
                        target,
                        bg='#4ECDC4',
                        height=3
                    )
                    self.drop_indicator.pack(side='bottom', fill='x', pady=2)
            except:
                # Widget might have been destroyed
                self.drop_indicator = None
    
    def find_drop_target(self, x: int, y: int) -> Optional[tk.Widget]:
        """Find the widget under the given coordinates"""
        # Check tier frames
        canvas_x = self.tiers_canvas.canvasx(x - self.tiers_canvas.winfo_rootx())
        canvas_y = self.tiers_canvas.canvasy(y - self.tiers_canvas.winfo_rooty())
        
        for widget in self.tiers_scrollable.winfo_children():
            if isinstance(widget, StyledFrame) and hasattr(widget, 'tier_name'):
                wx = widget.winfo_x()
                wy = widget.winfo_y()
                ww = widget.winfo_width()
                wh = widget.winfo_height()
                
                if wx <= canvas_x <= wx + ww and wy <= canvas_y <= wy + wh:
                    # Check if we're over a player in this tier
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Frame) and hasattr(child, 'player'):
                            cx = child.winfo_x() + wx
                            cy = child.winfo_y() + wy
                            cw = child.winfo_width()
                            ch = child.winfo_height()
                            
                            if cx <= canvas_x <= cx + cw and cy <= canvas_y <= cy + ch:
                                return child
                    
                    # Otherwise, we're over the tier itself
                    return widget
        
        # Check available players panel
        avail_x = self.avail_canvas.canvasx(x - self.avail_canvas.winfo_rootx())
        avail_y = self.avail_canvas.canvasy(y - self.avail_canvas.winfo_rooty())
        
        if self.avail_canvas.winfo_rootx() <= x <= self.avail_canvas.winfo_rootx() + self.avail_canvas.winfo_width():
            return self.avail_scrollable  # Dropping back to available
        
        return None
    
    def update_ranks_after_tier(self, starting_tier: str):
        """Update only the rank labels for tiers after the given tier"""
        # Find which tiers need updating
        found_starting_tier = False
        tiers_to_update = []
        
        for tier_name in self.tiers.keys():
            if found_starting_tier:
                tiers_to_update.append(tier_name)
            elif tier_name == starting_tier:
                found_starting_tier = True
        
        # Calculate the starting rank for the first tier to update
        starting_rank = 1
        for tier_name, player_ids in self.tiers.items():
            if tier_name in tiers_to_update:
                break
            starting_rank += len(player_ids)
        
        # Update rank labels in each affected tier
        current_rank = starting_rank
        for tier_name in tiers_to_update:
            # Find the tier frame
            tier_frame = None
            for widget in self.tiers_scrollable.winfo_children():
                if isinstance(widget, StyledFrame) and hasattr(widget, 'tier_name') and widget.tier_name == tier_name:
                    tier_frame = widget
                    break
            
            if tier_frame:
                # Update rank labels for all players in this tier
                player_widgets = [w for w in tier_frame.winfo_children() if hasattr(w, 'player')]
                for widget in player_widgets:
                    # Find the rank label in this widget
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and child.cget('text').startswith('#'):
                            child.config(text=f"#{current_rank}")
                            current_rank += 1
                            break
    
    def refresh_single_tier(self, tier_name: str):
        """Refresh only a single tier without touching the rest of the UI"""
        # Find the tier frame
        tier_frame = None
        for widget in self.tiers_scrollable.winfo_children():
            if isinstance(widget, StyledFrame) and hasattr(widget, 'tier_name') and widget.tier_name == tier_name:
                tier_frame = widget
                break
        
        if not tier_frame:
            return
        
        # Clear existing player widgets in this tier only
        for widget in tier_frame.winfo_children():
            if hasattr(widget, 'player'):
                widget.destroy()
                if widget.player.player_id in self.player_widgets:
                    del self.player_widgets[widget.player.player_id]
        
        # Get the current player order from the tier
        player_ids = self.tiers.get(tier_name, [])
        
        # Recreate player widgets in the correct order
        players_per_row = 10
        # Calculate starting rank based on previous tiers
        starting_rank = 1
        for t_name, t_players in self.tiers.items():
            if t_name == tier_name:
                break
            starting_rank += len(t_players)
        
        # Collect actual player objects
        actual_players = []
        for i, player_id in enumerate(player_ids):
            player = next((p for p in self.all_players if p.player_id == player_id), None)
            if player:
                actual_players.append(player)
                row = i // players_per_row
                col = i % players_per_row
                rank = starting_rank + i
                self.create_player_widget(tier_frame, player, tier_name, row, col, rank=rank)
        
        # Update tier frame height based on actual number of players
        num_rows = max(1, (len(actual_players) + players_per_row - 1) // players_per_row)
        row_height = 150
        frame_height = num_rows * row_height + 10
        tier_frame.configure(height=frame_height)
        
        # Update only the tier's scroll region if needed
        self.tiers_scrollable.update_idletasks()
        self.tiers_canvas.configure(scrollregion=self.tiers_canvas.bbox("all"))
        
        # Re-bind mouse wheel events
        self.after(10, self.setup_recursive_mousewheel)
    
    def smart_refresh_player(self, source_widget: tk.Widget, player: Player, source_tier: Optional[str], target_tier: Optional[str], target: tk.Widget):
        """Smart refresh that only moves the specific player widget"""
        # First, remove the source widget
        source_widget.destroy()
        if player.player_id in self.player_widgets:
            del self.player_widgets[player.player_id]
        
        # Create new widget in the target location
        if target_tier:
            # Find the target tier frame
            tier_frame = None
            if hasattr(target, 'tier_name') and isinstance(target, StyledFrame):
                tier_frame = target
            else:
                # Find the tier frame by name
                for widget in self.tiers_scrollable.winfo_children():
                    if isinstance(widget, StyledFrame) and hasattr(widget, 'tier_name') and widget.tier_name == target_tier:
                        tier_frame = widget
                        break
            
            if tier_frame:
                # Count existing players in this tier
                player_count = len([w for w in tier_frame.winfo_children() if hasattr(w, 'player')])
                row = player_count // 10
                col = player_count % 10
                
                # Calculate rank
                starting_rank = 1
                for t_name, t_players in self.tiers.items():
                    if t_name == target_tier:
                        break
                    starting_rank += len(t_players)
                rank = starting_rank + player_count
                
                self.create_player_widget(tier_frame, player, target_tier, row, col, rank=rank)
                
                # Update tier frame height
                num_rows = max(1, ((player_count + 1) + 9) // 10)
                row_height = 150
                frame_height = num_rows * row_height + 10
                tier_frame.configure(height=frame_height)
        else:
            # Moving to available players
            # Find position in available list
            available_widgets = [w for w in self.avail_scrollable.winfo_children() 
                               if hasattr(w, 'player') and not isinstance(w, tk.Label)]
            player_count = len(available_widgets)
            row = player_count // 3
            col = player_count % 3
            self.create_player_widget(self.avail_scrollable, player, None, row, col, is_available=True)
        
        # Update scroll regions if needed
        self.tiers_scrollable.update_idletasks()
        self.tiers_canvas.configure(scrollregion=self.tiers_canvas.bbox("all"))
        self.avail_scrollable.update_idletasks()
        self.avail_canvas.configure(scrollregion=self.avail_canvas.bbox("all"))
        
        # Re-bind mouse wheel events
        self.after(10, self.setup_recursive_mousewheel)
    
    def handle_drop(self, source: tk.Widget, target: tk.Widget):
        """Handle dropping a player"""
        if not hasattr(source, 'player'):
            return
        
        player = source.player
        source_tier = source.tier_name if hasattr(source, 'tier_name') else None
        
        # Determine target tier and position
        target_tier = None
        insert_position = None
        
        if hasattr(target, 'tier_name'):
            # Dropped on a tier frame or another player in a tier
            target_tier = target.tier_name
            if hasattr(target, 'player'):
                # Dropped on another player - find its position
                if target_tier in self.tiers:
                    try:
                        insert_position = self.tiers[target_tier].index(target.player.player_id)
                    except ValueError:
                        insert_position = len(self.tiers[target_tier])
        elif target == self.avail_scrollable:
            # Dropped back to available
            target_tier = None
        else:
            return
        
        # Remove from source tier (but remember the position if same tier)
        old_position = None
        if source_tier:
            if player.player_id in self.tiers[source_tier]:
                old_position = self.tiers[source_tier].index(player.player_id)
                self.tiers[source_tier].remove(player.player_id)
        
        # Add to target tier at the correct position
        if target_tier:
            if source_tier == target_tier and old_position is not None and insert_position is not None:
                # Same tier reordering - adjust position if needed
                if old_position < insert_position:
                    insert_position -= 1  # Adjust for removal
            
            # Insert at specific position or append
            if insert_position is not None:
                self.tiers[target_tier].insert(insert_position, player.player_id)
            else:
                self.tiers[target_tier].append(player.player_id)
        
        # Save and refresh
        self.save_tiers()
        
        # For same-tier moves, only refresh that tier
        if source_tier == target_tier:
            self.refresh_single_tier(target_tier)
        else:
            # Different tier - use smart refresh but also update ranks in subsequent tiers
            self.smart_refresh_player(source, player, source_tier, target_tier, target)
            
            # Update ranks in all tiers after the affected tier
            if target_tier:
                # Moving to a tier - update tiers after target
                self.update_ranks_after_tier(target_tier)
            elif source_tier:
                # Moving from a tier to available - update tiers after source
                self.update_ranks_after_tier(source_tier)
    
    def add_tier(self):
        """Add a new tier"""
        name = simpledialog.askstring("Add Tier", "Enter tier name:")
        if name and name not in self.tiers:
            self.tiers[name] = []
            self.save_tiers()
            self.update_display()
    
    def rename_tier(self, old_name: str):
        """Rename a tier"""
        new_name = simpledialog.askstring("Rename Tier", f"Enter new name for '{old_name}':", initialvalue=old_name)
        if new_name and new_name != old_name and new_name not in self.tiers:
            self.tiers[new_name] = self.tiers.pop(old_name)
            self.save_tiers()
            self.update_display()
    
    def delete_tier(self, tier_name: str):
        """Delete a tier"""
        if messagebox.askyesno("Delete Tier", f"Are you sure you want to delete the '{tier_name}' tier?"):
            del self.tiers[tier_name]
            self.save_tiers()
            self.update_display()
    
    def clear_tier(self, tier_name: str):
        """Clear all players from a tier"""
        if messagebox.askyesno("Clear Tier", f"Remove all players from the '{tier_name}' tier?"):
            self.tiers[tier_name] = []
            self.save_tiers()
            self.update_display()
    
    def reorganize_available_players(self):
        """Reorganize available players to remove gaps"""
        # Clear and recreate all available player widgets
        for widget in self.avail_scrollable.winfo_children():
            if hasattr(widget, 'player') and not isinstance(widget, tk.Label):
                widget.destroy()
                if widget.player.player_id in self.player_widgets:
                    del self.player_widgets[widget.player.player_id]
        
        # Get all available players (not in any tier)
        tiered_player_ids = set()
        for tier_players in self.tiers.values():
            tiered_player_ids.update(tier_players)
        
        available_players = [p for p in self.all_players if p.player_id not in tiered_player_ids]
        
        # Apply position filter if active
        if hasattr(self, 'avail_position_var') and self.avail_position_var.get() != "ALL":
            pos_filter = self.avail_position_var.get()
            available_players = [p for p in available_players if p.position == pos_filter]
        
        # Sort by ADP
        available_players.sort(key=lambda p: p.adp if p.adp else 999)
        
        # Recreate widgets in proper grid positions
        players_per_row = 3
        widget_height = 145
        spacing = 5
        
        if available_players:
            total_rows = (len(available_players) + players_per_row - 1) // players_per_row
            min_height = total_rows * (widget_height + spacing) + 20
            self.avail_scrollable.configure(height=min_height)
            
            for i, player in enumerate(available_players):
                row = i // players_per_row
                col = i % players_per_row
                self.create_player_widget(self.avail_scrollable, player, None, row, col, is_available=True)
        
        # Update scroll region
        self.avail_scrollable.update_idletasks()
        self.avail_canvas.configure(scrollregion=self.avail_canvas.bbox("all"))
        
        # Re-bind mouse wheel events
        self.after(10, self.setup_recursive_mousewheel)
    
    def filter_available_position(self, position: str):
        """Filter available players by position"""
        self.avail_position_var.set(position)
        self.reorganize_available_players()
    
    def reset_tiers(self):
        """Reset to default tiers"""
        if messagebox.askyesno("Reset Tiers", "Reset to default tiers? This will clear all custom rankings."):
            self.tiers = {
                "Round 1": [],
                "Round 2": [],
                "Round 3": [],
                "Round 4": [],
                "Round 5": [],
                "Round 6": [],
                "Round 7": [],
                "Round 8": [],
                "Round 9": [],
                "Round 10": [],
                "Round 11": [],
                "Round 12": [],
                "Round 13": [],
                "Round 14": [],
                "Round 15": []
            }
            self.save_tiers()
            self.update_display()
    
    def get_player_round(self, player_id: str) -> Optional[int]:
        """Get the round number for a player based on their tier assignment"""
        for tier_name, player_ids in self.tiers.items():
            if player_id in player_ids:
                # Extract round number from tier name (e.g., "Round 1" -> 1)
                if tier_name.startswith("Round "):
                    try:
                        return int(tier_name.split(" ")[1])
                    except (ValueError, IndexError):
                        pass
        return None