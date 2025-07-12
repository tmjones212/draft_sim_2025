import tkinter as tk
from tkinter import ttk
from typing import Optional, List
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class PlayerSelectionDialog:
    def __init__(self, parent, players: List[Player], current_player: Player, title="Select Player to Compare"):
        self.parent = parent
        self.players = [p for p in players if p.player_id != current_player.player_id]  # Exclude current player
        self.selected_player = None
        self.current_position_filter = "ALL"
        
        # Create dialog window
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.configure(bg=DARK_THEME['bg_primary'])
        
        # Hide window initially
        self.window.withdraw()
        
        # Set window size
        self.window.geometry("600x700")
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 300
        y = (self.window.winfo_screenheight() // 2) - 350
        self.window.geometry(f"600x700+{x}+{y}")
        
        # Show window
        self.window.deiconify()
        
        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()
        
        # Bind escape key to cancel
        self.window.bind('<Escape>', lambda e: self.cancel())
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = StyledFrame(self.window, bg_type='primary')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Select Player to Compare",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        title_label.pack(pady=(0, 15))
        
        # Search and filter frame
        controls_frame = tk.Frame(main_frame, bg=DARK_THEME['bg_primary'])
        controls_frame.pack(fill='x', pady=(0, 10))
        
        # Search box
        search_frame = tk.Frame(controls_frame, bg=DARK_THEME['bg_primary'])
        search_frame.pack(side='left', fill='x', expand=True)
        
        search_label = tk.Label(
            search_frame,
            text="Search:",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        search_label.pack(side='left', padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            bd=1,
            relief='solid',
            insertbackground=DARK_THEME['text_primary']
        )
        self.search_entry.pack(side='left', fill='x', expand=True)
        self.search_var.trace('w', lambda *args: self.filter_players())
        
        # Position filter
        positions = ["ALL", "QB", "RB", "WR", "TE", "FLEX"]
        for pos in positions:
            btn = tk.Button(
                controls_frame,
                text=pos,
                bg=DARK_THEME['button_bg'] if pos == "ALL" else DARK_THEME['bg_secondary'],
                fg='white' if pos == "ALL" else DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 9, 'bold'),
                bd=0,
                relief='flat',
                padx=12,
                pady=5,
                command=lambda p=pos: self.filter_by_position(p),
                cursor='hand2'
            )
            btn.pack(side='left', padx=(5, 0))
            
            # Store reference for updating colors
            setattr(self, f'pos_btn_{pos}', btn)
        
        # Player list frame
        list_frame = StyledFrame(main_frame, bg_type='secondary')
        list_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Create Treeview for player list
        columns = ('Name', 'Position', 'Team', 'ADP')
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='tree headings',
            selectmode='browse',
            height=20
        )
        
        # Configure columns
        self.tree.column('#0', width=0, stretch=False)
        self.tree.column('Name', width=200)
        self.tree.column('Position', width=80)
        self.tree.column('Team', width=80)
        self.tree.column('ADP', width=80)
        
        # Configure headings
        self.tree.heading('Name', text='Name')
        self.tree.heading('Position', text='Pos')
        self.tree.heading('Team', text='Team')
        self.tree.heading('ADP', text='ADP')
        
        # Style the treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', 
                       background=DARK_THEME['bg_secondary'],
                       foreground=DARK_THEME['text_primary'],
                       fieldbackground=DARK_THEME['bg_secondary'],
                       borderwidth=0)
        style.configure('Treeview.Heading',
                       background=DARK_THEME['bg_primary'],
                       foreground=DARK_THEME['text_primary'],
                       borderwidth=0)
        style.map('Treeview', 
                 background=[('selected', DARK_THEME['button_bg'])],
                 foreground=[('selected', 'white')])
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind double-click
        self.tree.bind('<Double-Button-1>', lambda e: self.select_player())
        
        # Buttons frame
        button_frame = tk.Frame(main_frame, bg=DARK_THEME['bg_primary'])
        button_frame.pack(fill='x')
        
        # Select button
        select_btn = tk.Button(
            button_frame,
            text='Select',
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold'),
            bd=0,
            relief='flat',
            padx=20,
            pady=8,
            command=self.select_player,
            cursor='hand2',
            activebackground=DARK_THEME['button_hover']
        )
        select_btn.pack(side='right', padx=(5, 0))
        
        # Cancel button
        cancel_btn = tk.Button(
            button_frame,
            text='Cancel',
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            bd=0,
            relief='flat',
            padx=20,
            pady=8,
            command=self.cancel,
            cursor='hand2',
            activebackground=DARK_THEME['bg_tertiary']
        )
        cancel_btn.pack(side='right')
        
        # Populate the list
        self.filter_players()
        
        # Focus on search
        self.search_entry.focus_set()
    
    def filter_by_position(self, position: str):
        """Filter players by position"""
        self.current_position_filter = position
        
        # Update button colors
        positions = ["ALL", "QB", "RB", "WR", "TE", "FLEX"]
        for pos in positions:
            btn = getattr(self, f'pos_btn_{pos}')
            if pos == position:
                btn.configure(bg=DARK_THEME['button_bg'], fg='white')
            else:
                btn.configure(bg=DARK_THEME['bg_secondary'], fg=DARK_THEME['text_secondary'])
        
        self.filter_players()
    
    def filter_players(self):
        """Filter players based on search and position"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        search_text = self.search_var.get().lower()
        
        # Filter players
        filtered_players = []
        for player in self.players:
            # Position filter
            if self.current_position_filter != "ALL":
                if self.current_position_filter == "FLEX":
                    if player.position not in ["RB", "WR", "TE"]:
                        continue
                elif player.position != self.current_position_filter:
                    continue
            
            # Search filter
            if search_text:
                if search_text not in player.format_name().lower():
                    continue
            
            filtered_players.append(player)
        
        # Sort by ADP
        filtered_players.sort(key=lambda p: p.adp if p.adp else 999)
        
        # Add to tree
        for i, player in enumerate(filtered_players[:100]):  # Limit to 100 for performance
            adp_text = str(int(player.adp)) if player.adp else "-"
            # Store player object directly as tag
            item_id = self.tree.insert('', 'end', values=(
                player.format_name(),
                player.position,
                player.team or '-',
                adp_text
            ))
            # Store player reference in a dictionary
            if not hasattr(self, '_player_map'):
                self._player_map = {}
            self._player_map[item_id] = player
    
    def select_player(self):
        """Select the currently highlighted player"""
        selection = self.tree.selection()
        print(f"Selection: {selection}")
        if selection:
            item_id = selection[0]
            # Get player from our map
            if hasattr(self, '_player_map') and item_id in self._player_map:
                self.selected_player = self._player_map[item_id]
                print(f"Selected player: {self.selected_player.format_name()}")
            else:
                print(f"Player not found in map for item_id: {item_id}")
            
            self.window.grab_release()
            self.window.destroy()
        else:
            print("No selection")
    
    def cancel(self):
        """Cancel the dialog"""
        self.selected_player = None
        self.window.grab_release()
        self.window.destroy()
    
    def get_selected_player(self) -> Optional[Player]:
        """Wait for dialog to close and return selected player"""
        self.window.wait_window()
        return self.selected_player