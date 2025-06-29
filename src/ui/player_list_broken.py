import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Callable
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class PlayerList(StyledFrame):
    def __init__(self, parent, on_select: Optional[Callable] = None, on_draft: Optional[Callable] = None, image_service=None, **kwargs):
        super().__init__(parent, bg_type='secondary', **kwargs)
        self.on_select = on_select
        self.on_draft = on_draft
        self.players: List[Player] = []
        self.selected_index = None
        self.image_cache = {}  # Cache loaded images
        self.player_cards = []
        self.draft_enabled = False
        self.image_service = image_service
        self.all_players: List[Player] = []  # Store all players
        self.selected_position = "ALL"  # Current filter
        self.sort_by = "rank"  # Default sort by rank
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        container = StyledFrame(self, bg_type='secondary')
        container.pack(fill='both', expand=True)
        
        # Header with title and search
        header_frame = StyledFrame(container, bg_type='secondary')
        header_frame.pack(fill='x', pady=(0, 10))
        
        title = tk.Label(
            header_frame,
            text="AVAILABLE PLAYERS",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 11, 'bold')
        )
        title.pack(side='left')
        
        # Sort controls
        sort_frame = StyledFrame(header_frame, bg_type='secondary')
        sort_frame.pack(side='left', padx=20)
        
        sort_label = tk.Label(
            sort_frame,
            text="Sort:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        )
        sort_label.pack(side='left', padx=(0, 5))
        
        # Sort buttons
        self.sort_buttons = {}
        sort_options = [("Rank", "rank"), ("ADP", "adp")]
        
        for label, value in sort_options:
            btn = tk.Button(
                sort_frame,
                text=label,
                bg=DARK_THEME['button_active'] if value == "rank" else DARK_THEME['button_bg'],
                fg='white',
                font=(DARK_THEME['font_family'], 9),
                bd=1,
                relief='solid',
                padx=8,
                pady=2,
                command=lambda v=value: self.sort_players(v),
                cursor='hand2'
            )
            btn.pack(side='left', padx=2)
            self.sort_buttons[value] = btn
        
        # Position filter buttons
        filter_frame = StyledFrame(header_frame, bg_type='secondary')
        filter_frame.pack(side='right')
        
        # Add position filter buttons
        positions = ["ALL", "QB", "RB", "WR", "TE"]
        self.position_buttons = {}
        
        for pos in positions:
            btn = tk.Button(
                filter_frame,
                text=pos,
                bg=DARK_THEME['button_bg'] if pos != "ALL" else DARK_THEME['button_active'],
                fg='white',
                font=(DARK_THEME['font_family'], 9),
                bd=1,
                relief='solid',
                padx=10,
                pady=3,
                command=lambda p=pos: self.filter_by_position(p),
                cursor='hand2'
            )
            btn.pack(side='left', padx=2)
            self.position_buttons[pos] = btn
        
        # Table container
        self.create_table_view(container)
    
    def _removed_create_cards_view(self):
        """Create the horizontal scrollable cards view"""
        self.cards_container = StyledFrame(self.content_container, bg_type='secondary')
        
        # Horizontal scrollable container
        scroll_container = StyledFrame(self.cards_container, bg_type='secondary')
        scroll_container.pack(fill='both', expand=True)
        
        # Canvas for horizontal scrolling
        self.canvas = tk.Canvas(
            scroll_container,
            bg=DARK_THEME['bg_secondary'],
            highlightthickness=0,
            height=200
        )
        h_scrollbar = tk.Scrollbar(
            scroll_container,
            orient='horizontal',
            command=self.canvas.xview,
            bg=DARK_THEME['bg_tertiary'],
            troughcolor=DARK_THEME['bg_secondary']
        )
        
        self.scrollable_frame = StyledFrame(self.canvas, bg_type='secondary')
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        self.canvas.pack(side="top", fill="both", expand=True)
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Player cards container
        self.player_cards = []
    
    def create_table_view(self, parent):
        """Create the table view for players"""
        self.table_container = StyledFrame(parent, bg_type='secondary')
        self.table_container.pack(fill='both', expand=True)
        
        # Table with scrollbar
        table_scroll_container = StyledFrame(self.table_container, bg_type='secondary')
        table_scroll_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create Treeview for table
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure dark theme for Treeview
        style.configure("Treeview",
                       background=DARK_THEME['bg_tertiary'],
                       foreground=DARK_THEME['text_primary'],
                       fieldbackground=DARK_THEME['bg_tertiary'],
                       borderwidth=0,
                       font=(DARK_THEME['font_family'], 11),
                       rowheight=30)
        style.configure("Treeview.Heading",
                       background=DARK_THEME['bg_secondary'],
                       foreground=DARK_THEME['text_primary'],
                       borderwidth=1,
                       font=(DARK_THEME['font_family'], 11, 'bold'))
        style.map('Treeview', background=[('selected', DARK_THEME['button_active'])])
        
        # Create treeview with columns
        columns = ('rank', 'pos', 'name', 'team', 'adp')
        self.table = ttk.Treeview(table_scroll_container, columns=columns, show='headings', height=20)
        
        # Define column headings and widths
        self.table.heading('rank', text='Rank')
        self.table.heading('pos', text='Pos')
        self.table.heading('name', text='Name')
        self.table.heading('team', text='Team')
        self.table.heading('adp', text='ADP')
        
        self.table.column('rank', width=70, anchor='center')
        self.table.column('pos', width=60, anchor='center')
        self.table.column('name', width=300, anchor='w')
        self.table.column('team', width=80, anchor='center')
        self.table.column('adp', width=80, anchor='center')
        
        # Scrollbar for table
        table_scrollbar = tk.Scrollbar(table_scroll_container, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=table_scrollbar.set)
        
        self.table.pack(side='left', fill='both', expand=True)
        table_scrollbar.pack(side='right', fill='y')
        
        # Bind double-click to draft
        self.table.bind('<Double-Button-1>', self.on_table_double_click)
        self.table.bind('<<TreeviewSelect>>', self.on_table_select)
        
        # Make headers clickable for sorting
        self.table.heading('rank', text='Rank', command=lambda: self.sort_table_by('rank'))
        self.table.heading('pos', text='Pos', command=lambda: self.sort_table_by('position'))
        self.table.heading('name', text='Name', command=lambda: self.sort_table_by('name'))
        self.table.heading('team', text='Team', command=lambda: self.sort_table_by('team'))
        self.table.heading('adp', text='ADP', command=lambda: self.sort_table_by('adp'))
    
    def toggle_view_mode(self):
        """Toggle between cards and table view"""
        if self.view_mode == "cards":
            self.view_mode = "table"
            self.table_expanded = not self.table_expanded
            self.show_table_view()
            self.toggle_btn.config(text="⬆ Card View" if self.table_expanded else "⬇ Table View")
        else:
            self.view_mode = "cards"
            self.table_expanded = False
            self.show_cards_view()
            self.toggle_btn.config(text="⬇ Table View")
        
        # Update the display
        self.update_players(self.all_players)
    
    def show_cards_view(self):
        """Show the cards view and hide table view"""
        if hasattr(self, 'table_container'):
            self.table_container.pack_forget()
        self.cards_container.pack(fill='both', expand=True)
        self.content_container.configure(height=200)
    
    def show_table_view(self):
        """Show the table view and hide cards view"""
        self.cards_container.pack_forget()
        self.table_container.pack(fill='both', expand=True)
        # Adjust height based on expanded state
        if self.table_expanded:
            self.content_container.configure(height=400)
        else:
            self.content_container.configure(height=200)
    
    def update_players(self, players: List[Player], limit: int = 30):
        # Store all players
        self.all_players = players
        
        # Apply position filter
        if self.selected_position == "ALL":
            filtered_players = players
        else:
            filtered_players = [p for p in players if p.position == self.selected_position]
        
        # Apply sorting
        if self.sort_by == "adp":
            # Sort by ADP, putting players without ADP at the end
            filtered_players = sorted(filtered_players, 
                                    key=lambda p: p.adp if p.adp else float('inf'))
        else:  # Default sort by rank
            filtered_players = sorted(filtered_players, key=lambda p: p.rank)
        
        self.players = filtered_players
        self.selected_index = None
        
        # Check if we have the table components
        if hasattr(self, 'table_frame') and hasattr(self, 'table_canvas'):
            # Always update table view
            self.update_table_view()
    
    def remove_player_card(self, index: int):
        """Remove a specific player without refreshing all players"""
        if 0 <= index < len(self.players):
            self.players.pop(index)
            self.update_table_view()
    
    def remove_players(self, players_to_remove: List[Player]):
        """Remove multiple players from the list efficiently"""
        # Find indices of all players to remove
        indices_to_remove = []
        for player in players_to_remove:
            for i, p in enumerate(self.players):
                if p == player:
                    indices_to_remove.append(i)
                    break
        
        # Sort in reverse order so we remove from the end first
        indices_to_remove.sort(reverse=True)
        
        # Remove players and update table
        for index in indices_to_remove:
            if 0 <= index < len(self.players):
                self.players.pop(index)
        self.update_table_view()
    
    def create_player_card(self, index: int, player: Player) -> tk.Frame:
        # Player card container - vertical layout
        card = StyledFrame(
            self.scrollable_frame,
            bg_type='tertiary',
            relief='flat',
            width=130,
            height=180  # Adjusted for 40x40 image
        )
        card.pack_propagate(False)
        
        # Make card clickable and double-clickable
        def on_click(event):
            self.select_player(index)
        
        def on_double_click(event):
            self.select_player(index)
            if self.on_draft:
                self.on_draft()
        
        card.bind("<Button-1>", on_click)
        card.bind("<Double-Button-1>", on_double_click)
        
        # Inner container with padding
        inner = StyledFrame(card, bg_type='tertiary')
        inner.pack(fill='both', expand=True, padx=10, pady=8)
        inner.bind("<Button-1>", on_click)
        inner.bind("<Double-Button-1>", on_double_click)
        
        # Player image container (for player + team logo)
        image_container = tk.Frame(inner, bg=DARK_THEME['bg_tertiary'], width=40, height=32)
        image_container.pack(pady=(0, 5))
        image_container.bind("<Button-1>", lambda e: on_click(e))
        
        # Player image
        if self.image_service and player.player_id:
            # Player image
            player_image = self.image_service.get_image(player.player_id, size=(40, 32))
            if player_image:
                img_label = tk.Label(
                    image_container,
                    image=player_image,
                    bg=DARK_THEME['bg_tertiary']
                )
                img_label.image = player_image  # Keep reference
                img_label.place(x=0, y=0)
                img_label.bind("<Button-1>", lambda e: on_click(e))
            else:
                # Create placeholder
                img_label = tk.Label(
                    image_container,
                    bg=DARK_THEME['bg_tertiary'],
                    width=5,
                    height=2
                )
                img_label.place(x=0, y=0, width=40, height=32)
                img_label.bind("<Button-1>", lambda e: on_click(e))
                
                # Schedule image loading
                def update_player_image(photo):
                    if img_label.winfo_exists():
                        img_label.configure(image=photo)
                        img_label.image = photo
                
                self.image_service.load_image_async(
                    player.player_id,
                    size=(40, 32),
                    callback=update_player_image,
                    widget=self
                )
            
            # Team logo overlay
            if player.team:
                team_logo = self.image_service.get_image(f"team_{player.team}", size=(16, 16))
                if team_logo:
                    logo_label = tk.Label(
                        image_container,
                        image=team_logo,
                        bg=DARK_THEME['bg_tertiary']
                    )
                    logo_label.image = team_logo
                    logo_label.place(x=26, y=14)  # Position like Sleeper
                    logo_label.bind("<Button-1>", lambda e: on_click(e))
                else:
                    # Schedule team logo loading
                    def update_team_logo(photo):
                        if image_container.winfo_exists():
                            logo_label = tk.Label(
                                image_container,
                                image=photo,
                                bg=DARK_THEME['bg_tertiary']
                            )
                            logo_label.image = photo
                            logo_label.place(x=26, y=14)
                            logo_label.bind("<Button-1>", lambda e: on_click(e))
                    
                    # Load team logo using special ID
                    self.image_service.load_image_async(
                        f"team_{player.team}",
                        size=(16, 16),
                        callback=update_team_logo,
                        widget=self
                    )
        
        # Rank at top
        rank_label = tk.Label(
            inner,
            text=f"#{player.rank}",
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        rank_label.pack()
        rank_label.bind("<Button-1>", lambda e: on_click(e))
        
        # Position badge
        pos_frame = tk.Frame(
            inner,
            bg=get_position_color(player.position),
            padx=8,
            pady=3
        )
        pos_frame.pack(pady=8)
        
        pos_label = tk.Label(
            pos_frame,
            text=player.position,
            bg=get_position_color(player.position),
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold')
        )
        pos_label.pack()
        
        # Player name
        name_label = tk.Label(
            inner,
            text=player.name,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            wraplength=110
        )
        name_label.pack(fill='x')
        name_label.bind("<Button-1>", lambda e: on_click(e))
        
        # ADP display
        adp_label = tk.Label(
            inner,
            text=f"ADP: {player.adp:.1f}" if player.adp else "ADP: -",
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 9)
        )
        adp_label.pack(fill='x')
        adp_label.bind("<Button-1>", lambda e: on_click(e))
        
        # Draft button
        if self.on_draft:
            draft_btn = tk.Button(
                inner,
                text="DRAFT",
                bg=DARK_THEME['button_active'],
                fg='white',
                font=(DARK_THEME['font_family'], 8, 'bold'),
                relief='flat',
                cursor='hand2',
                command=lambda p=player: self.draft_specific_player(p),
                state='normal' if self.draft_enabled else 'disabled'
            )
            draft_btn.pack(pady=(5, 0))
            
            # Hover effect
            draft_btn.bind('<Enter>', lambda e: draft_btn.config(bg='#2ecc71'))
            draft_btn.bind('<Leave>', lambda e: draft_btn.config(bg=DARK_THEME['button_active']))
        
        # Remove ADP label if draft button is shown
        if not self.on_draft:
            value_label = tk.Label(
                inner,
                text=f"ADP: {player.adp}",
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 9)
            )
            value_label.pack(pady=(5, 0))
            value_label.bind("<Button-1>", on_click)
        
        return card
    
    
    def select_player(self, index: int):
        # Deselect previous
        if self.selected_index is not None and self.selected_index < len(self.player_cards):
            self.player_cards[self.selected_index].config(
                bg=DARK_THEME['bg_tertiary'],
                relief='flat',
                borderwidth=0
            )
        
        # Select new
        self.selected_index = index
        if index < len(self.player_cards):
            self.player_cards[index].config(
                bg=DARK_THEME['current_pick'],
                relief='solid',
                borderwidth=2
            )
        
        # Callback
        if self.on_select and index < len(self.players):
            self.on_select(self.players[index])
    
    def get_selected_player(self) -> Optional[Player]:
        if self.selected_index is not None and self.selected_index < len(self.players):
            return self.players[self.selected_index]
        return None
    
    def draft_player(self, index: int):
        """Draft a specific player by index"""
        self.select_player(index)
        if self.on_draft:
            self.on_draft()
    
    def draft_specific_player(self, player: Player):
        """Draft a specific player object directly"""
        # Find the player's current index
        for i, p in enumerate(self.players):
            if p == player:
                self.select_player(i)
                if self.on_draft:
                    self.on_draft()
                return
        # Player not found - might have been drafted already
        return
    
    def filter_by_position(self, position: str):
        """Filter players by position"""
        self.selected_position = position
        
        # Update button appearances
        for pos, btn in self.position_buttons.items():
            if pos == position:
                btn.config(bg=DARK_THEME['button_active'])
            else:
                btn.config(bg=DARK_THEME['button_bg'])
        
        # Refresh the player list with the filter applied
        self.update_players(self.all_players)
    
    def sort_players(self, sort_by: str):
        """Sort players by specified criteria"""
        self.sort_by = sort_by
        
        # Update button appearances
        for key, btn in self.sort_buttons.items():
            if key == sort_by:
                btn.config(bg=DARK_THEME['button_active'])
            else:
                btn.config(bg=DARK_THEME['button_bg'])
        
        # Refresh the player list with the new sort
        self.update_players(self.all_players)
    
    def set_draft_enabled(self, enabled: bool):
        """Enable or disable all draft buttons"""
        self.draft_enabled = enabled
        # Update all existing draft buttons
        for card in self.player_cards:
            # Find the draft button in the card's children
            for widget in card.winfo_children():
                if isinstance(widget, tk.Frame):  # Inner frame
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Button) and child.cget('text') == 'DRAFT':
                            child.config(state='normal' if enabled else 'disabled')
    
    def update_table_view(self):
        """Update the table view with current players"""
        # Clear existing items
        for item in self.table.get_children():
            self.table.delete(item)
        
        # Add players to table
        for i, player in enumerate(self.players):
            values = (
                f"#{player.rank}",
                player.position,
                player.name,
                player.team or '-',
                f"{player.adp:.1f}" if player.adp else '-'
            )
            self.table.insert('', 'end', values=values, tags=(player.position,))
        
        # Apply position colors to tags
        for pos in ['QB', 'RB', 'WR', 'TE']:
            self.table.tag_configure(pos, foreground=get_position_color(pos))
    
    def on_table_select(self, event):
        """Handle table row selection"""
        selection = self.table.selection()
        if selection:
            item = selection[0]
            index = self.table.index(item)
            if index < len(self.players):
                self.selected_index = index
                if self.on_select:
                    self.on_select(self.players[index])
    
    def on_table_double_click(self, event):
        """Handle double-click on table row to draft"""
        selection = self.table.selection()
        if selection and self.draft_enabled:
            item = selection[0]
            index = self.table.index(item)
            if index < len(self.players) and self.on_draft:
                self.selected_index = index
                self.on_draft()
    
    def sort_table_by(self, column: str):
        """Sort the table by the specified column"""
        # Sort the players list based on column
        if column == 'rank':
            self.players.sort(key=lambda p: p.rank)
        elif column == 'position':
            self.players.sort(key=lambda p: p.position)
        elif column == 'name':
            self.players.sort(key=lambda p: p.name)
        elif column == 'team':
            self.players.sort(key=lambda p: p.team if p.team else 'ZZZ')
        elif column == 'adp':
            self.players.sort(key=lambda p: p.adp if p.adp else float('inf'))
        
        # Update the table view
        self.update_table_view()
        row_frame = StyledFrame(
            self.table_frame,
            bg_type='tertiary' if index % 2 == 0 else 'secondary',
            relief='flat',
            height=50
        )
        row_frame.pack(fill='x', pady=1)
        row_frame.pack_propagate(False)
        
        # Make row clickable
        def on_row_click(event):
            self.selected_index = index
            if self.on_select:
                self.on_select(player)
        
        row_frame.bind("<Button-1>", on_row_click)
        
        # Get the actual background color
        bg_color = DARK_THEME['bg_tertiary'] if index % 2 == 0 else DARK_THEME['bg_secondary']
        
        # Image
        img_frame = tk.Frame(row_frame, bg=bg_color, width=60)
        img_frame.pack(side='left', fill='y')
        img_frame.pack_propagate(False)
        
        if self.image_service and player.player_id:
            player_image = self.image_service.get_image(player.player_id, size=(40, 32))
            if player_image:
                img_label = tk.Label(img_frame, image=player_image, bg=bg_color)
                img_label.image = player_image
                img_label.pack(expand=True)
                img_label.bind("<Button-1>", on_row_click)
        
        # Rank
        rank_label = tk.Label(
            row_frame,
            text=f"#{player.rank}",
            bg=bg_color,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11),
            width=7
        )
        rank_label.pack(side='left')
        rank_label.bind("<Button-1>", on_row_click)
        
        # Position
        pos_frame = tk.Frame(
            row_frame,
            bg=get_position_color(player.position),
            width=50
        )
        pos_frame.pack(side='left', padx=5, fill='y')
        pos_frame.pack_propagate(False)
        
        pos_label = tk.Label(
            pos_frame,
            text=player.position,
            bg=get_position_color(player.position),
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold')
        )
        pos_label.pack(expand=True)
        pos_label.bind("<Button-1>", on_row_click)
        
        # Name
        name_label = tk.Label(
            row_frame,
            text=player.name,
            bg=bg_color,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 11),
            width=25,
            anchor='w'
        )
        name_label.pack(side='left', padx=5)
        name_label.bind("<Button-1>", on_row_click)
        
        # Team
        team_label = tk.Label(
            row_frame,
            text=player.team or '-',
            bg=bg_color,
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10),
            width=7
        )
        team_label.pack(side='left')
        team_label.bind("<Button-1>", on_row_click)
        
        # ADP
        adp_label = tk.Label(
            row_frame,
            text=f"{player.adp:.1f}" if player.adp else '-',
            bg=bg_color,
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10),
            width=7
        )
        adp_label.pack(side='left')
        adp_label.bind("<Button-1>", on_row_click)
        
        # Draft button
        if self.on_draft:
            draft_btn = tk.Button(
                row_frame,
                text="DRAFT",
                bg=DARK_THEME['button_active'],
                fg='white',
                font=(DARK_THEME['font_family'], 9, 'bold'),
                relief='flat',
                cursor='hand2',
                command=lambda: self.draft_specific_player(player),
                state='normal' if self.draft_enabled else 'disabled'
            )
            draft_btn.pack(side='right', padx=10)
        
        self.player_rows.append(row_frame)
    
    
