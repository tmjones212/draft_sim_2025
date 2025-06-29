import tkinter as tk
from tkinter import ttk, messagebox
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
        
        # Search box
        search_frame = StyledFrame(header_frame, bg_type='secondary')
        search_frame.pack(side='left', padx=20)
        
        search_label = tk.Label(
            search_frame,
            text="Search:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 9)
        )
        search_label.pack(side='left', padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            width=20
        )
        self.search_entry.pack(side='left')
        self.search_var.trace('w', lambda *args: self.on_search_changed())
        
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
    
    def create_table_view(self, parent):
        """Create the table view for players"""
        self.table_container = StyledFrame(parent, bg_type='secondary')
        self.table_container.pack(fill='both', expand=True)
        
        # Header with darker background and border
        header_border = tk.Frame(self.table_container, bg=DARK_THEME['border'], height=37)
        header_border.pack(fill='x', padx=10, pady=(10, 0))
        
        header_container = tk.Frame(header_border, bg=DARK_THEME['bg_tertiary'], height=35)
        header_container.pack(fill='both', expand=True, padx=1, pady=1)
        header_container.pack_propagate(False)
        
        # Column headers with exact pixel widths matching the cells
        headers = [
            ('Rank', 70),
            ('Pos', 60),
            ('Name', 300),
            ('Team', 80),
            ('ADP', 80),
            ('', 100)       # Draft button
        ]
        
        for text, width in headers:
            header_frame = tk.Frame(header_container, bg=DARK_THEME['bg_tertiary'], width=width)
            header_frame.pack(side='left', fill='y')
            header_frame.pack_propagate(False)
            
            header = tk.Label(
                header_frame,
                text=text,
                bg=DARK_THEME['bg_tertiary'],
                fg='white',
                font=(DARK_THEME['font_family'], 12, 'bold'),
                anchor='center' if text != 'Name' else 'w'
            )
            header.pack(expand=True)
        
        # Scrollable content
        content_container = StyledFrame(self.table_container, bg_type='secondary')
        content_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(
            content_container, 
            bg=DARK_THEME['bg_secondary'], 
            highlightthickness=0,
            height=400
        )
        scrollbar = tk.Scrollbar(content_container, orient='vertical', command=self.canvas.yview)
        
        self.table_frame = tk.Frame(self.canvas, bg=DARK_THEME['bg_secondary'])
        self.table_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.table_frame, anchor='nw')
        
        # Make table frame expand to canvas width
        def configure_canvas(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.canvas.bind('<Configure>', configure_canvas)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mouse wheel scrolling - bind to all child widgets
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            
        self.canvas.bind('<MouseWheel>', on_mousewheel)
        self.table_frame.bind('<MouseWheel>', on_mousewheel)
        
        # Bind mousewheel to all children as they're created
        self._mousewheel_handler = on_mousewheel
        
        # Store row frames
        self.row_frames = []
        self.selected_row = None
    
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
        
        # Always update table view
        self.update_table_view()
    
    def remove_player_card(self, index: int):
        """Remove a specific player without refreshing all players"""
        if 0 <= index < len(self.players):
            # Remove from data
            self.players.pop(index)
            
            # Just remove the specific row from UI
            if 0 <= index < len(self.row_frames):
                self.row_frames[index].destroy()
                self.row_frames.pop(index)
                
            # Update indices for remaining rows
            for i in range(index, len(self.row_frames)):
                # Update the click handler to use new index
                new_index = i
                row = self.row_frames[i]
                
                # Update background color for alternating rows
                bg = DARK_THEME['bg_tertiary'] if new_index % 2 == 0 else DARK_THEME['bg_secondary']
                row.configure(bg=bg)
                
                # Update all child widgets' backgrounds
                for widget in row.winfo_children():
                    if isinstance(widget, tk.Frame):
                        widget.configure(bg=bg)
                        for child in widget.winfo_children():
                            if hasattr(child, 'configure') and not isinstance(child, tk.Button):
                                try:
                                    child.configure(bg=bg)
                                except:
                                    pass
    
    def remove_players(self, players_to_remove: List[Player]):
        """Remove multiple players from the list efficiently"""
        if not players_to_remove:
            return
            
        # Create a set for O(1) lookup
        players_to_remove_set = set(players_to_remove)
        
        # Find indices to remove
        indices_to_remove = []
        for i, player in enumerate(self.players):
            if player in players_to_remove_set:
                indices_to_remove.append(i)
        
        # Sort in reverse to remove from end first
        indices_to_remove.sort(reverse=True)
        
        # Remove from data and UI
        for idx in indices_to_remove:
            self.players.pop(idx)
            if idx < len(self.row_frames):
                self.row_frames[idx].destroy()
                self.row_frames.pop(idx)
        
        # Fix alternating colors for remaining rows
        for i, row in enumerate(self.row_frames):
            bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
            row.configure(bg=bg)
            for widget in row.winfo_children():
                if isinstance(widget, tk.Frame):
                    widget.configure(bg=bg)
                    for child in widget.winfo_children():
                        if hasattr(child, 'configure') and not isinstance(child, tk.Button):
                            try:
                                child.configure(bg=bg)
                            except:
                                pass
    
    def select_player(self, index: int):
        """Select a player by index"""
        if index >= len(self.players):
            return
            
        self.selected_index = index
        
        # Callback
        if self.on_select:
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
    
    def update_table_view(self):
        """Update the table view with current players"""
        # Clear existing rows
        for row in self.row_frames:
            row.destroy()
        self.row_frames = []
        
        # Limit display to first 100 players for performance
        max_display = min(100, len(self.players))
        
        # Show limited players
        for i in range(max_display):
            self.create_player_row(i, self.players[i])
        
        # If there are more players, show a message
        if len(self.players) > max_display:
            more_label = tk.Label(
                self.table_frame,
                text=f"... and {len(self.players) - max_display} more players. Use search to find specific players.",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10, 'italic')
            )
            more_label.pack(pady=10)
        
        # Update canvas scroll region after adding all rows
        self.table_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def get_display_players(self):
        """Get top 10 players ensuring at least one from each main position"""
        # Check if we have players
        if not self.players:
            return []
            
        # If searching, show matching players
        search_text = self.search_var.get().lower() if hasattr(self, 'search_var') else ""
        if search_text:
            matching = [p for p in self.players if search_text in p.name.lower()]
            return matching[:10]
        
        # Get top 10 players but ensure at least one from each position
        all_top_players = self.players[:10]
        positions_needed = {'QB', 'RB', 'WR', 'TE'}
        positions_found = set()
        
        # Check which positions are already in top 10
        for player in all_top_players:
            positions_found.add(player.position)
        
        # If we're missing any positions, add the top player from each missing position
        if positions_found != positions_needed:
            result = list(all_top_players)
            for pos in positions_needed - positions_found:
                # Find the best player of this position
                pos_players = [p for p in self.players if p.position == pos]
                if pos_players:
                    # Remove the worst player from result and add this position player
                    if len(result) >= 10:
                        result.pop()
                    result.append(pos_players[0])
            
            # Re-sort by rank to maintain order
            result.sort(key=lambda p: p.rank)
            return result[:10]
        
        return all_top_players
    
    def create_player_row(self, index, player):
        """Create a row with player data"""
        # Row container
        bg = DARK_THEME['bg_tertiary'] if index % 2 == 0 else DARK_THEME['bg_secondary']
        row = tk.Frame(
            self.table_frame,
            bg=bg,
            height=35,
            relief='flat',
            bd=0
        )
        row.pack(fill='x', pady=1)
        row.pack_propagate(False)
        
        # Store the player reference on the row
        row.player = player
        row.index = index
        
        # Make row selectable
        def select_row(e=None):
            # Find current index of this player
            current_index = None
            for i, p in enumerate(self.players):
                if p == row.player:
                    current_index = i
                    break
            
            if current_index is not None:
                self.select_row(current_index)
                if self.on_select:
                    self.on_select(row.player)
        
        row.bind('<Button-1>', select_row)
        
        # Bind mousewheel to this row
        if hasattr(self, '_mousewheel_handler'):
            row.bind('<MouseWheel>', self._mousewheel_handler)
        
        # Rank
        self.create_cell(row, f"#{player.rank}", 70, bg, select_row)
        
        # Position
        pos_frame = tk.Frame(row, bg=bg, width=60)
        pos_frame.pack(side='left', fill='y')
        pos_frame.pack_propagate(False)
        
        pos_inner = tk.Frame(pos_frame, bg=get_position_color(player.position), padx=8, pady=2)
        pos_inner.pack(expand=True)
        pos_label = tk.Label(pos_inner, text=player.position, bg=get_position_color(player.position), 
                            fg='white', font=(DARK_THEME['font_family'], 10, 'bold'))
        pos_label.pack()
        pos_frame.bind('<Button-1>', select_row)
        
        # Bind mousewheel
        if hasattr(self, '_mousewheel_handler'):
            pos_frame.bind('<MouseWheel>', self._mousewheel_handler)
            pos_inner.bind('<MouseWheel>', self._mousewheel_handler)
            pos_label.bind('<MouseWheel>', self._mousewheel_handler)
        
        # Name
        self.create_cell(row, player.name, 300, bg, select_row, anchor='w')
        
        # Team
        self.create_cell(row, player.team or '-', 80, bg, select_row)
        
        # ADP
        self.create_cell(row, f"{player.adp:.1f}" if player.adp else '-', 80, bg, select_row)
        
        # Draft button
        if self.draft_enabled:
            btn_frame = tk.Frame(row, bg=bg, width=100)
            btn_frame.pack(side='left', fill='y')
            btn_frame.pack_propagate(False)
            
            draft_btn = tk.Button(
                btn_frame,
                text='DRAFT',
                bg=DARK_THEME['button_active'],
                fg='white',
                font=(DARK_THEME['font_family'], 9, 'bold'),
                relief='flat',
                cursor='hand2',
                command=lambda p=player: self.draft_specific_player(p)
            )
            draft_btn.pack(expand=True)
            
            # Bind mousewheel
            if hasattr(self, '_mousewheel_handler'):
                btn_frame.bind('<MouseWheel>', self._mousewheel_handler)
                draft_btn.bind('<MouseWheel>', self._mousewheel_handler)
        
        self.row_frames.append(row)
    
    def create_cell(self, parent, text, width, bg, click_handler, anchor='center'):
        """Create a table cell with exact pixel width"""
        cell_frame = tk.Frame(parent, bg=bg, width=width)
        cell_frame.pack(side='left', fill='y')
        cell_frame.pack_propagate(False)
        
        cell = tk.Label(
            cell_frame,
            text=text,
            bg=bg,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            anchor=anchor
        )
        cell.pack(expand=True, fill='both')
        cell.bind('<Button-1>', click_handler)
        
        # Bind mousewheel
        if hasattr(self, '_mousewheel_handler'):
            cell_frame.bind('<MouseWheel>', self._mousewheel_handler)
            cell.bind('<MouseWheel>', self._mousewheel_handler)
        
        return cell
    
    def on_search_changed(self):
        """Handle search text changes"""
        search_text = self.search_var.get().lower()
        if search_text:
            # Filter players based on search
            filtered = [p for p in self.all_players if search_text in p.name.lower()]
            self.players = filtered
        else:
            # Show all players based on current filters
            self.update_players(self.all_players)
            return
        
        self.update_table_view()
    
    def select_row(self, index):
        """Highlight selected row"""
        self.selected_index = index
        selected_player = self.players[index] if index < len(self.players) else None
        
        for i, row in enumerate(self.row_frames):
            # Check if this row contains the selected player
            is_selected = hasattr(row, 'player') and row.player == selected_player
            
            if is_selected:
                row.configure(bg=DARK_THEME['button_active'])
                for widget in row.winfo_children():
                    if isinstance(widget, tk.Label):
                        widget.configure(bg=DARK_THEME['button_active'])
                    elif isinstance(widget, tk.Frame) and not any(isinstance(child, tk.Button) for child in widget.winfo_children()):
                        widget.configure(bg=DARK_THEME['button_active'])
                        # Update position badge background
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Frame) and hasattr(row, 'player'):
                                # Keep position color for inner frame
                                continue
                            elif isinstance(child, tk.Label):
                                try:
                                    child.configure(bg=DARK_THEME['button_active'])
                                except:
                                    pass
            else:
                bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
                row.configure(bg=bg)
                for widget in row.winfo_children():
                    if isinstance(widget, tk.Label) and not widget.winfo_class() == 'Button':
                        widget.configure(bg=bg)
                    elif isinstance(widget, tk.Frame) and not any(isinstance(child, tk.Button) for child in widget.winfo_children()):
                        widget.configure(bg=bg)
                        # Update children of frames
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Label) and child.winfo_class() != 'Button':
                                try:
                                    child.configure(bg=bg)
                                except:
                                    pass
    
    def add_player_image(self, item, player):
        """Add player image to the table row"""
        # Get image
        player_image = self.image_service.get_image(player.player_id, size=(30, 24))
        if player_image:
            # Schedule image placement after the table is rendered
            self.after(10, lambda: self.place_image_on_row(item, player_image))
    
    def place_image_on_row(self, item, image):
        """Place image on the specific row"""
        try:
            # Get the bounding box of the item
            bbox = self.table.bbox(item, column='space')
            if bbox:
                x, y, width, height = bbox
                # Create label with image
                img_label = tk.Label(self.table, image=image, bg=DARK_THEME['bg_tertiary'])
                img_label.image = image  # Keep reference
                img_label.place(x=x+10, y=y+3, width=30, height=24)
                self.image_labels.append(img_label)
                self.image_references.append(image)
        except:
            pass  # Item might not be visible
    
    def on_table_scroll(self, event):
        """Handle table scroll to update image positions"""
        # Re-update the table view to reposition images
        self.after(10, self.reposition_images)
    
    def reposition_images(self):
        """Reposition all images after scroll"""
        # Clear existing image labels
        if hasattr(self, 'image_labels'):
            for label in self.image_labels:
                label.destroy()
        self.image_labels = []
        
        # Re-add images for visible items
        for i, (item, player) in enumerate(zip(self.table.get_children(), self.players)):
            if self.image_service and player.player_id:
                player_image = self.image_service.get_image(player.player_id, size=(30, 24))
                if player_image:
                    self.place_image_on_row(item, player_image)
    
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