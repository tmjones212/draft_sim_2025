import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Callable
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame, StyledButton
import json
import os
import threading


class CheatSheet(StyledFrame):
    def __init__(self, parent, players: List[Player], on_rankings_update: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg_type='primary', **kwargs)
        self.all_players = players
        self.on_rankings_update = on_rankings_update
        
        # Custom rankings and tiers
        self.custom_rankings = {}  # player_id -> custom_rank
        self.player_tiers = {}  # player_id -> tier
        self.tier_breaks = set()  # Set of indices after which tier breaks appear
        
        
        self.tier_colors = {
            1: '#FFD700',  # Gold
            2: '#C0C0C0',  # Silver
            3: '#CD7F32',  # Bronze
            4: '#4169E1',  # Royal Blue
            5: '#32CD32',  # Lime Green
            6: '#FF6347',  # Tomato
            7: '#9370DB',  # Medium Purple
            8: '#20B2AA',  # Light Sea Green
        }
        
        # UI elements
        self.player_frames = []
        self.tier_separators = []  # Clickable tier separators
        self.selected_player = None
        self.tier_entries = {}
        self._last_clicked_index = None
        
        self.setup_ui()
        self.load_rankings()
        
        # Defer initial display for faster load
        self.after(1, self.update_display)
    
    def setup_ui(self):
        # Header
        header_frame = StyledFrame(self, bg_type='secondary')
        header_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        title_label = tk.Label(
            header_frame,
            text="CHEAT SHEET",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 16, 'bold')
        )
        title_label.pack(side='left', padx=10, pady=5)
        
        # No mode toggle needed - always in tiers mode
        
        # Instructions
        instructions_label = tk.Label(
            header_frame,
            text="(Top 100 Players • Drag to reorder • Click between rows to create tiers)",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 10, 'italic')
        )
        instructions_label.pack(side='left', padx=10)
        
        # Save button
        save_btn = StyledButton(
            header_frame,
            text="SAVE",
            command=self.save_rankings,
            bg=DARK_THEME['button_active'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=15,
            pady=5
        )
        save_btn.pack(side='right', padx=10)
        
        # Reset button
        reset_btn = StyledButton(
            header_frame,
            text="RESET",
            command=self.reset_rankings,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=15,
            pady=5
        )
        reset_btn.pack(side='right', padx=5)
        
        # Position filter
        filter_frame = StyledFrame(self, bg_type='secondary')
        filter_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(
            filter_frame,
            text="Position:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 11)
        ).pack(side='left', padx=(10, 5))
        
        self.position_var = tk.StringVar(value="ALL")
        positions = ["ALL", "QB", "RB", "WR", "TE", "FLEX", "DEF", "K"]
        
        for pos in positions:
            btn = tk.Button(
                filter_frame,
                text=pos,
                command=lambda p=pos: self.filter_position(p),
                bg=DARK_THEME['button_bg'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10),
                bd=0,
                padx=10,
                pady=3,
                cursor='hand2'
            )
            btn.pack(side='left', padx=2)
            
            if pos != "ALL" and pos != "FLEX":
                pos_color = get_position_color(pos)
                btn.config(bg=pos_color, activebackground=pos_color)
        
        # Main content area with scrolling
        content_frame = StyledFrame(self, bg_type='primary')
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(
            content_frame,
            bg=DARK_THEME['bg_primary'],
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            content_frame,
            orient='vertical',
            command=self.canvas.yview,
            bg=DARK_THEME['bg_tertiary']
        )
        
        self.scrollable_frame = StyledFrame(self.canvas, bg_type='primary')
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            # Only scroll if canvas has focus or mouse is over it
            self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            return "break"  # Prevent event propagation
        
        # Bind to multiple events for better compatibility
        self.canvas.bind('<MouseWheel>', on_mousewheel)
        self.canvas.bind('<Button-4>', lambda e: self.canvas.yview_scroll(-1, 'units'))
        self.canvas.bind('<Button-5>', lambda e: self.canvas.yview_scroll(1, 'units'))
        
        # Set focus when mouse enters
        self.canvas.bind('<Enter>', lambda e: self.canvas.focus_set())
        self.scrollable_frame.bind('<Enter>', lambda e: self.canvas.focus_set())
        
        # Create headers
        self.create_headers()
    
    
    def create_headers(self):
        # Clear existing header if any
        if hasattr(self, 'header_frame'):
            self.header_frame.destroy()
        
        self.header_frame = StyledFrame(self.scrollable_frame, bg_type='tertiary')
        self.header_frame.pack(fill='x', pady=(0, 5))
        
        # Column headers
        headers = [
            ("Rank", 60),
            ("Tier", 50),
            ("Pos", 45),
            ("Player", 200),
            ("Team", 45),
            ("ADP", 50),
            ("VAR", 55),
            ("2024 Pts", 70),
            ("2025 Proj", 70),
        ]
        
        for text, width in headers:
            label = tk.Label(
                self.header_frame,
                text=text,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10, 'bold'),
                width=width//8
            )
            label.pack(side='left', padx=5)
    
    def update_display(self, force_full_refresh=False):
        # For dragging, use quick refresh if possible
        if hasattr(self, '_dragging') and self._dragging:
            return  # Don't update during drag
        
        # Performance optimization: Store scroll position
        scroll_pos = self.canvas.canvasy(0) if hasattr(self, 'canvas') else 0
            
        # Clear existing frames - we need to rebuild to get proper layout
        for frame in self.player_frames:
            frame.destroy()
        for sep in self.tier_separators:
            sep.destroy()
        self.player_frames = []
        self.tier_separators = []
        self.tier_entries = {}
        
        # Get filtered and sorted players
        filtered_players = self.get_filtered_players()
        sorted_players = self.sort_players_by_custom_rank(filtered_players)
        
        # Limit to top 100 players
        sorted_players = sorted_players[:100]
        
        # Update player tiers based on tier breaks
        self.update_player_tiers_from_breaks(sorted_players)
        
        # Create player rows with tier separators
        for idx, player in enumerate(sorted_players):
            # Add clickable area between players (except before first player)
            if idx > 0:
                self.create_tier_click_area(idx)
            
            # Add tier separator after the click area if needed
            if idx in self.tier_breaks:
                self.create_tier_separator(idx)
            
            self.create_player_row(idx, player)
        
        # Update scroll region
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Restore scroll position
        if scroll_pos:
            self.canvas.yview_moveto(scroll_pos / self.canvas.winfo_height())
        
        # Bind mouse wheel only once on first display
        if not hasattr(self, '_mousewheel_bound'):
            self.bind_mousewheel_to_children()
            self._mousewheel_bound = True
    
    
    def get_filtered_players(self):
        position = self.position_var.get()
        
        if position == "ALL":
            return self.all_players
        elif position == "FLEX":
            return [p for p in self.all_players if p.position in ["RB", "WR", "TE"]]
        else:
            return [p for p in self.all_players if p.position == position]
    
    def sort_players_by_custom_rank(self, players):
        # Sort by custom rank if available, otherwise by default rank
        def get_sort_key(player):
            if player.player_id in self.custom_rankings:
                return self.custom_rankings[player.player_id]
            return player.rank + 1000  # Put unranked players at the end
        
        return sorted(players, key=get_sort_key)
    
    def create_tier_separator(self, idx):
        """Create a visible tier break line"""
        separator = tk.Frame(
            self.scrollable_frame,
            bg=DARK_THEME['accent_warning'],
            height=3,
            cursor='hand2'
        )
        separator.pack(fill='x', pady=5)
        separator.tier_index = idx  # Store which tier break this is
        separator.is_tier_line = True  # Mark as actual tier line
        
        # Make it clickable to remove
        def on_click(e):
            # Remove this tier break
            if idx in self.tier_breaks:
                self.tier_breaks.remove(idx)
                self._last_clicked_index = idx
                self.refresh_tier_displays()
                
                # Set flag to sync when user switches tabs
                if hasattr(self.master.master.master, '_cheat_sheet_needs_sync'):
                    self.master.master.master._cheat_sheet_needs_sync = True
        
        def on_enter(e):
            separator.configure(bg='#ff6b35')  # Lighter orange on hover
        
        def on_leave(e):
            separator.configure(bg=DARK_THEME['accent_warning'])
        
        separator.bind('<Button-1>', on_click)
        separator.bind('<Enter>', on_enter)
        separator.bind('<Leave>', on_leave)
        
        # Add tooltip
        tooltip = tk.Label(
            separator,
            text="Click to remove tier",
            bg=DARK_THEME['accent_warning'],
            fg='black',
            font=(DARK_THEME['font_family'], 8)
        )
        
        def show_tooltip(e):
            tooltip.place(relx=0.5, rely=0.5, anchor='center')
            separator.configure(height=20)
        
        def hide_tooltip(e):
            tooltip.place_forget()
            separator.configure(height=3)
        
        separator.bind('<Enter>', lambda e: (on_enter(e), show_tooltip(e)))
        separator.bind('<Leave>', lambda e: (on_leave(e), hide_tooltip(e)))
        
        self.tier_separators.append(separator)
    
    def update_tier_separator_lines(self):
        """Update only the orange tier separator lines"""
        # Remove existing tier lines
        for sep in self.tier_separators[:]:
            if hasattr(sep, 'is_tier_line') and sep.is_tier_line:
                sep.destroy()
                self.tier_separators.remove(sep)
        
        # Get all children for positioning
        children = list(self.scrollable_frame.winfo_children())
        
        # Add new tier lines at the correct positions
        for tier_idx in sorted(self.tier_breaks):
            # Find the click area for this index
            insert_after = None
            for i, child in enumerate(children):
                if hasattr(child, 'tier_index') and child.tier_index == tier_idx:
                    insert_after = i
                    break
            
            if insert_after is not None:
                # Create new separator
                separator = tk.Frame(
                    self.scrollable_frame,
                    bg=DARK_THEME['accent_warning'],
                    height=3
                )
                separator.tier_index = tier_idx
                separator.is_tier_line = True
                
                # Pack it after the click area
                if insert_after + 1 < len(children):
                    separator.pack(fill='x', pady=5, before=children[insert_after + 1])
                else:
                    separator.pack(fill='x', pady=5)
                
                self.tier_separators.append(separator)
    
    def quick_update_separator_at_index(self, idx):
        """Quickly add or remove a separator at a specific index"""
        if idx is None:
            return
            
        # Find and remove existing separator if we're removing
        if idx not in self.tier_breaks:
            for sep in self.tier_separators[:]:
                if hasattr(sep, 'is_tier_line') and sep.is_tier_line and sep.tier_index == idx:
                    sep.destroy()
                    self.tier_separators.remove(sep)
                    return
        else:
            # Adding a new separator - find the click area
            children = list(self.scrollable_frame.winfo_children())
            for i, child in enumerate(children):
                if hasattr(child, 'tier_index') and child.tier_index == idx:
                    # Create separator immediately after this click area
                    # Create separator with click handler
                    separator = tk.Frame(
                        self.scrollable_frame,
                        bg=DARK_THEME['accent_warning'],
                        height=3,
                        cursor='hand2'
                    )
                    separator.tier_index = idx
                    separator.is_tier_line = True
                    
                    # Make it clickable
                    def make_click_handler(sep_idx):
                        def on_click(e):
                            if sep_idx in self.tier_breaks:
                                self.tier_breaks.remove(sep_idx)
                                self._last_clicked_index = sep_idx
                                self.refresh_tier_displays()
                                if hasattr(self.master.master.master, '_cheat_sheet_needs_sync'):
                                    self.master.master.master._cheat_sheet_needs_sync = True
                        return on_click
                    
                    separator.bind('<Button-1>', make_click_handler(idx))
                    
                    # Simple hover effects
                    def on_enter(e):
                        separator.configure(bg='#ff6b35')
                    
                    def on_leave(e):
                        separator.configure(bg=DARK_THEME['accent_warning'])
                    
                    separator.bind('<Enter>', on_enter)
                    separator.bind('<Leave>', on_leave)
                    
                    if i + 1 < len(children):
                        separator.pack(fill='x', pady=5, before=children[i + 1])
                    else:
                        separator.pack(fill='x', pady=5)
                    
                    self.tier_separators.append(separator)
                    return
    
    def _update_tier_numbers(self):
        """Update tier numbers efficiently"""
        # Simple tier assignment based on tier breaks
        current_tier = 1
        
        # Update labels directly from player frames (already sorted)
        for i, frame in enumerate(self.player_frames):
            if i > 0 and i in self.tier_breaks:
                current_tier += 1
                if current_tier > 8:
                    current_tier = 8
            
            # Update tier for this player
            player = frame.player
            self.player_tiers[player.player_id] = current_tier
            
            # Update label if exists
            if player.player_id in self.tier_entries:
                label = self.tier_entries[player.player_id]
                label.config(
                    text=str(current_tier),
                    bg=self.tier_colors.get(current_tier, DARK_THEME['bg_tertiary']),
                    fg='black' if current_tier in [1, 2, 3, 5] else 'white'
                )
    
    def refresh_tier_displays(self):
        """Instantly update tier displays"""
        # First, quickly add/remove the visual separator line
        self.quick_update_separator_at_index(self._last_clicked_index)
        
        # Then update tier numbers in the background
        self.after_idle(self._update_tier_numbers)
    
    def update_player_tiers_from_breaks(self, sorted_players):
        """Update player tiers based on tier break positions"""
        # Clear existing tiers
        self.player_tiers = {}
        
        # Assign tiers based on tier breaks
        current_tier = 1
        for idx, player in enumerate(sorted_players):
            self.player_tiers[player.player_id] = current_tier
            # If there's a tier break after this player, increment tier
            if idx + 1 in self.tier_breaks:
                current_tier += 1
                if current_tier > 8:  # Max 8 tiers
                    current_tier = 8
    
    def bind_mousewheel_to_children(self):
        """Bind mouse wheel scrolling to all child widgets"""
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            return "break"
        
        # Set focus handler
        def on_enter(event):
            self.canvas.focus_set()
        
        # Bind to canvas and scrollable frame only - more efficient
        self.canvas.bind('<MouseWheel>', on_mousewheel)
        self.scrollable_frame.bind('<MouseWheel>', on_mousewheel)
        self.canvas.bind('<Enter>', on_enter)
    
    def _bind_mousewheel_recursive(self, widget, scroll_callback, enter_callback):
        """Recursively bind mouse wheel to all children"""
        for child in widget.winfo_children():
            child.bind('<MouseWheel>', scroll_callback)
            child.bind('<Enter>', enter_callback)
            self._bind_mousewheel_recursive(child, scroll_callback, enter_callback)
    
    def create_tier_click_area(self, idx):
        """Create a clickable area between players to add tier breaks"""
        click_area = tk.Frame(
            self.scrollable_frame,
            bg=DARK_THEME['bg_primary'],
            height=6,
            cursor='hand2'
        )
        click_area.pack(fill='x')
        
        # Store the index for this click area
        click_area.tier_index = idx
        
        # Create visual indicator container
        indicator = tk.Frame(click_area, bg=DARK_THEME['bg_primary'])
        
        # Create dashed line effect with multiple small frames
        for i in range(0, 100, 10):
            dash = tk.Frame(
                indicator,
                bg=DARK_THEME['accent_warning'],
                width=5,
                height=2
            )
            dash.place(relx=i/100, rely=0.5, anchor='w')
        
        # Add text hint
        hint_text = tk.Label(
            indicator,
            text="Click to add tier",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['accent_warning'],
            font=(DARK_THEME['font_family'], 8)
        )
        hint_text.place(relx=0.5, rely=0.5, anchor='center')
        
        # Hover effect
        def on_enter(e):
            if idx not in self.tier_breaks:
                # Show indicator
                click_area.configure(bg='#2a2a2a', height=20)
                indicator.configure(bg='#2a2a2a')
                hint_text.configure(bg='#2a2a2a')
                indicator.place(relx=0.5, rely=0.5, relwidth=0.95, relheight=0.8, anchor='center')
        
        def on_leave(e):
            if idx not in self.tier_breaks:
                # Hide indicator
                click_area.configure(bg=DARK_THEME['bg_primary'], height=6)
                indicator.place_forget()
        
        def on_click(e):
            self._last_clicked_index = idx
            
            if idx in self.tier_breaks:
                # Remove tier break
                self.tier_breaks.remove(idx)
            else:
                # Add tier break
                self.tier_breaks.add(idx)
            
            # Instant visual update
            self.refresh_tier_displays()
            
            # Set flag to sync when user switches tabs (instant UI)
            if hasattr(self.master.master.master, '_cheat_sheet_needs_sync'):
                self.master.master.master._cheat_sheet_needs_sync = True
        
        click_area.bind('<Enter>', on_enter)
        click_area.bind('<Leave>', on_leave)
        click_area.bind('<Button-1>', on_click)
        
        # Add to tier separators list so we can track it
        self.tier_separators.append(click_area)
    
    def create_player_row(self, idx, player):
        bg = DARK_THEME['bg_tertiary'] if idx % 2 == 0 else DARK_THEME['bg_secondary']
        
        row_frame = tk.Frame(
            self.scrollable_frame,
            bg=bg,
            height=35,
            cursor='hand2'  # Show it's draggable
        )
        row_frame.pack(fill='x', pady=1)
        row_frame.pack_propagate(False)
        
        # Store player reference
        row_frame.player = player
        
        # Make entire row draggable (but not interactive elements)
        def bind_drag_events(widget):
            if not isinstance(widget, (tk.Entry, tk.Button)):
                widget.bind('<Button-1>', lambda e: self.start_drag(e, row_frame))
                widget.bind('<B1-Motion>', self.on_drag)
                widget.bind('<ButtonRelease-1>', self.end_drag)
        
        # Bind to frame
        bind_drag_events(row_frame)
        
        # Add hover effect
        def on_enter(e):
            if not hasattr(self, 'dragged_row') or self.dragged_row != row_frame:
                row_frame.config(bg=DARK_THEME['bg_hover'])
                for widget in row_frame.winfo_children():
                    if isinstance(widget, tk.Frame) and not hasattr(widget.winfo_children()[0] if widget.winfo_children() else None, '_is_star_button'):
                        widget.config(bg=DARK_THEME['bg_hover'])
                    elif isinstance(widget, tk.Label):
                        widget.config(bg=DARK_THEME['bg_hover'])
        
        def on_leave(e):
            if not hasattr(self, 'dragged_row') or self.dragged_row != row_frame:
                row_frame.config(bg=bg)
                for widget in row_frame.winfo_children():
                    if isinstance(widget, tk.Frame) and not hasattr(widget.winfo_children()[0] if widget.winfo_children() else None, '_is_star_button'):
                        widget.config(bg=bg)
                    elif isinstance(widget, tk.Label):
                        widget.config(bg=bg)
        
        row_frame.bind('<Enter>', on_enter)
        row_frame.bind('<Leave>', on_leave)
        
        
        # Custom rank display (non-editable)
        rank_frame = tk.Frame(row_frame, bg=bg, width=60)
        rank_frame.pack(side='left', fill='y')
        rank_frame.pack_propagate(False)
        bind_drag_events(rank_frame)
        
        custom_rank = self.custom_rankings.get(player.player_id, idx + 1)
        
        rank_label = tk.Label(
            rank_frame,
            text=str(custom_rank),
            bg=bg,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            anchor='center'
        )
        rank_label.pack(expand=True)
        bind_drag_events(rank_label)
        
        # Tier/Round display
        tier_frame = tk.Frame(row_frame, bg=bg, width=50)
        tier_frame.pack(side='left', fill='y')
        tier_frame.pack_propagate(False)
        bind_drag_events(tier_frame)
        
        # Show tier
        current_tier = self.player_tiers.get(player.player_id, 0)
        tier_label = tk.Label(
            tier_frame,
            text=str(current_tier) if current_tier > 0 else "-",
            bg=self.tier_colors.get(current_tier, bg),
            fg='black' if current_tier in [1, 2, 3, 5] else 'white',
            font=(DARK_THEME['font_family'], 10, 'bold')
        )
        
        tier_label.pack(expand=True, fill='both', padx=2, pady=2)
        tier_label._tier_label = True  # Mark as tier label
        self.tier_entries[player.player_id] = tier_label
        bind_drag_events(tier_label)
        
        # Position
        pos_frame = tk.Frame(row_frame, bg=bg, width=45)
        pos_frame.pack(side='left', fill='y')
        pos_frame.pack_propagate(False)
        bind_drag_events(pos_frame)
        
        pos_color = get_position_color(player.position)
        pos_label = tk.Label(
            pos_frame,
            text=player.position,
            bg=pos_color,
            fg='white',
            font=(DARK_THEME['font_family'], 9, 'bold')
        )
        pos_label.pack(expand=True)
        bind_drag_events(pos_label)
        
        # Player name
        name_frame = tk.Frame(row_frame, bg=bg, width=200)
        name_frame.pack(side='left', fill='y')
        name_frame.pack_propagate(False)
        bind_drag_events(name_frame)
        
        name_label = tk.Label(
            name_frame,
            text=player.format_name(),
            bg=bg,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            anchor='w'
        )
        name_label.pack(side='left', padx=5)
        bind_drag_events(name_label)
        
        # Team
        team_label = self.create_cell(row_frame, player.team or '-', 45, bg)
        bind_drag_events(team_label)
        
        # ADP
        adp_label = self.create_cell(row_frame, f"{player.adp:.1f}" if player.adp else '-', 50, bg)
        bind_drag_events(adp_label)
        
        # VAR
        var = getattr(player, 'var', None)
        var_label = self.create_cell(row_frame, f"{var:.1f}" if var is not None else '-', 55, bg)
        bind_drag_events(var_label)
        
        # 2024 Points
        points = getattr(player, 'points_2024', 0)
        points_label = self.create_cell(row_frame, f"{points:.0f}" if points else '-', 70, bg)
        bind_drag_events(points_label)
        
        # 2025 Projection
        proj = getattr(player, 'points_2025_proj', 0)
        proj_label = self.create_cell(row_frame, f"{proj:.0f}" if proj else '-', 70, bg)
        bind_drag_events(proj_label)
        
        self.player_frames.append(row_frame)
    
    def create_cell(self, parent, text, width, bg):
        cell_frame = tk.Frame(parent, bg=bg, width=width)
        cell_frame.pack(side='left', fill='y')
        cell_frame.pack_propagate(False)
        
        label = tk.Label(
            cell_frame,
            text=text,
            bg=bg,
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            anchor='center'
        )
        label.pack(expand=True)
        
        return cell_frame  # Return frame so we can bind events to it
    
    
    def cycle_tier(self, player):
        # Tiers are now managed by tier breaks
        pass
    
    def filter_position(self, position):
        self.position_var.set(position)
        self.update_display()
    
    def _reorder_frames_only(self, new_order):
        """Efficiently reorder frames without recreating them"""
        # Create a mapping of player_id to frame
        player_to_frame = {}
        for frame in self.player_frames:
            player_to_frame[frame.player.player_id] = frame
        
        # Hide all frames
        for frame in self.player_frames:
            frame.pack_forget()
        
        # Reorder the frames list
        new_frames = []
        for i, player in enumerate(new_order):
            if player.player_id in player_to_frame:
                frame = player_to_frame[player.player_id]
                new_frames.append(frame)
                
                # Update the rank display in the frame
                for widget in frame.winfo_children():
                    if isinstance(widget, tk.Frame) and widget.winfo_width() == 60:  # Rank frame
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Label) and not hasattr(child, '_tier_label'):
                                child.config(text=str(i + 1))
                                break
                        break
                
                # Update background color
                bg = DARK_THEME['bg_tertiary'] if i % 2 == 0 else DARK_THEME['bg_secondary']
                frame.configure(bg=bg)
                
                # Update all child widgets' backgrounds
                self._update_frame_background(frame, bg)
                
                # Repack the frame
                frame.pack(fill='x', pady=1)
        
        self.player_frames = new_frames
    
    def _update_frame_background(self, frame, bg):
        """Recursively update background colors in a frame"""
        for widget in frame.winfo_children():
            try:
                # Skip buttons and entries
                if isinstance(widget, tk.Entry):
                    continue
                elif isinstance(widget, tk.Button):
                    widget.configure(bg=bg, activebackground=bg)
                elif isinstance(widget, tk.Frame):
                    # Check if it's a position frame (has colored background)
                    has_position = False
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and child.cget('bg') in ['#f8296d', '#36ceb8', '#58a7ff', '#faae58', '#bd66ff']:
                            has_position = True
                            break
                    
                    if not has_position:
                        widget.configure(bg=bg)
                        self._update_frame_background(widget, bg)
                elif isinstance(widget, tk.Label):
                    # Check if it's a position label
                    current_bg = widget.cget('bg')
                    if current_bg not in ['#f8296d', '#36ceb8', '#58a7ff', '#faae58', '#bd66ff']:
                        widget.configure(bg=bg)
            except:
                pass
    
    def _quick_refresh(self, new_player_order):
        """Quickly refresh the display without destroying frames"""
        # Ensure we have enough frames
        while len(self.player_frames) < len(new_player_order):
            # This shouldn't happen in drag/drop but just in case
            self.create_player_row(len(self.player_frames), new_player_order[len(self.player_frames)])
        
        # Update each frame with new player data
        for i, player in enumerate(new_player_order):
            if i >= len(self.player_frames):
                break
                
            frame = self.player_frames[i]
            frame.player = player
            
            # Update all the display elements
            widget_index = 0
            for widget in frame.winfo_children():
                if widget_index == 0 and isinstance(widget, tk.Frame):
                    # Rank label
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and not hasattr(child, '_tier_label'):
                            child.config(text=str(i + 1))
                            break
                            
                elif widget_index == 1 and isinstance(widget, tk.Frame):
                    # Tier/Round label
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and hasattr(child, '_tier_label'):
                            # Update tier display
                            tier = self.player_tiers.get(player.player_id, 0)
                            if tier > 0:
                                child.config(
                                    text=str(tier),
                                    bg=self.tier_colors.get(tier),
                                    fg='black' if tier in [1, 2, 3, 5] else 'white'
                                )
                            else:
                                child.config(text="-", bg=frame.cget('bg'), fg=DARK_THEME['text_primary'])
                            break
                            
                elif widget_index == 2 and isinstance(widget, tk.Frame):
                    # Position
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            child.config(text=player.position, bg=get_position_color(player.position))
                            break
                            
                elif widget_index == 3 and isinstance(widget, tk.Frame):
                    # Name
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            child.config(text=player.format_name())
                            break
                            
                elif widget_index == 4 and isinstance(widget, tk.Frame):
                    # Team
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            child.config(text=player.team or '-')
                            break
                            
                elif widget_index == 5 and isinstance(widget, tk.Frame):
                    # ADP
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            child.config(text=f"{player.adp:.1f}" if player.adp else '-')
                            break
                            
                elif widget_index == 6 and isinstance(widget, tk.Frame):
                    # VAR
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            var = getattr(player, 'var', None)
                            child.config(text=f"{var:.1f}" if var is not None else '-')
                            break
                            
                elif widget_index == 7 and isinstance(widget, tk.Frame):
                    # 2024 Points
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            points = getattr(player, 'points_2024', 0)
                            child.config(text=f"{points:.0f}" if points else '-')
                            break
                            
                elif widget_index == 8 and isinstance(widget, tk.Frame):
                    # 2025 Projection
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            proj = getattr(player, 'points_2025_proj', 0)
                            child.config(text=f"{proj:.0f}" if proj else '-')
                            break
                            
                widget_index += 1
    
    def start_drag(self, event, row_frame):
        # Minimal state storage
        self.dragged_row = row_frame
        self.dragged_player = row_frame.player
        self.drag_start_y = event.y_root
        self.drag_start_index = self.player_frames.index(row_frame)
        self._dragging = True
        
        # Simple visual feedback - dim the text
        row_frame.configure(bg=DARK_THEME['bg_hover'])
    
    def on_drag(self, event):
        if not hasattr(self, 'dragged_row'):
            return
        
        # Find target position based on mouse
        mouse_y = event.y_root
        target_index = None
        
        for i, frame in enumerate(self.player_frames):
            if frame == self.dragged_row:
                continue
            frame_top = frame.winfo_rooty()
            if mouse_y < frame_top + 18:  # Half row height
                target_index = i
                break
        
        if target_index is None:
            target_index = len(self.player_frames) - 1
        
        # Clear previous drop indicator
        if hasattr(self, 'drop_indicator'):
            self.drop_indicator.destroy()
        
        # Create drop indicator line
        if target_index is not None:
            # Get the position where the indicator should appear
            if target_index < len(self.player_frames):
                target_frame = self.player_frames[target_index]
                y_pos = target_frame.winfo_y() - 2
            else:
                # Dropping at the end
                last_frame = self.player_frames[-1]
                y_pos = last_frame.winfo_y() + last_frame.winfo_height() + 2
            
            # Create a bright line to show drop position
            self.drop_indicator = tk.Frame(
                self.scrollable_frame,
                bg='#FF5E5B',  # Bright red
                height=3,
                borderwidth=0
            )
            self.drop_indicator.place(x=10, y=y_pos, relwidth=0.95)
            
            # Also highlight the dragged row more prominently
            self.dragged_row.configure(bg=DARK_THEME['bg_hover'])
    
    def end_drag(self, event):
        if not hasattr(self, 'dragged_row'):
            return
        
        # Reset visual feedback
        if hasattr(self, 'drop_indicator'):
            self.drop_indicator.destroy()
            delattr(self, 'drop_indicator')
        
        # Restore dragged row appearance
        current_idx = self.player_frames.index(self.dragged_row)
        bg = DARK_THEME['bg_tertiary'] if current_idx % 2 == 0 else DARK_THEME['bg_secondary']
        self.dragged_row.configure(bg=bg)
        
        # Find final position
        mouse_y = event.y_root
        target_index = None
        
        for i, frame in enumerate(self.player_frames):
            frame_top = frame.winfo_rooty()
            if mouse_y < frame_top + 18:
                target_index = i
                break
        
        if target_index is None:
            target_index = len(self.player_frames) - 1
        
        # Get current players and find dragged player
        players_in_view = [frame.player for frame in self.player_frames]
        current_idx = None
        for i, frame in enumerate(self.player_frames):
            if frame == self.dragged_row:
                current_idx = i
                break
        
        if current_idx is not None and target_index is not None and current_idx != target_index:
            # Handle tier-based dragging  
            self._handle_tier_drag(current_idx, target_index, players_in_view)
        
        # Clean up
        self._dragging = False
        if hasattr(self, 'dragged_row'):
            delattr(self, 'dragged_row')
        if hasattr(self, 'dragged_player'):
            delattr(self, 'dragged_player')
        if hasattr(self, 'drag_start_y'):
            delattr(self, 'drag_start_y')
    
    
    def _handle_tier_drag(self, current_idx, target_idx, players_in_view):
        """Handle dragging in tiers mode - properly manage tier assignments"""
        # Find which tier the target position is in
        target_tier = 1
        for i in range(target_idx):
            if i in self.tier_breaks:
                target_tier += 1
        
        # Get the dragged player
        dragged_player = players_in_view[current_idx]
        
        # Simple reordering within the same tier
        if current_idx < target_idx:
            # Moving down
            players_in_view.insert(target_idx, players_in_view.pop(current_idx))
        else:
            # Moving up
            players_in_view.insert(target_idx, players_in_view.pop(current_idx))
        
        # Update custom rankings based on new order
        self.custom_rankings = {}
        for i, player in enumerate(players_in_view):
            self.custom_rankings[player.player_id] = i + 1
        
        # Update tier assignments based on tier breaks
        self.player_tiers = {}
        current_tier = 1
        for i, player in enumerate(players_in_view):
            self.player_tiers[player.player_id] = current_tier
            if i + 1 in self.tier_breaks:
                current_tier += 1
                if current_tier > 8:
                    current_tier = 8
        
        # Full refresh to update display properly
        self.update_display()
        
        # Set flag to sync
        if hasattr(self.master.master.master, '_cheat_sheet_needs_sync'):
            self.master.master.master._cheat_sheet_needs_sync = True
    
    def save_rankings(self):
        data = {
            'custom_rankings': self.custom_rankings,
            'player_tiers': self.player_tiers,
            'tier_breaks': list(self.tier_breaks)
        }
        
        # Save to file
        cheat_sheet_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'cheat_sheet.json')
        os.makedirs(os.path.dirname(cheat_sheet_path), exist_ok=True)
        
        with open(cheat_sheet_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        messagebox.showinfo("Success", "Cheat sheet saved successfully!")
    
    def load_rankings(self):
        cheat_sheet_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'cheat_sheet.json')
        
        if os.path.exists(cheat_sheet_path):
            try:
                with open(cheat_sheet_path, 'r') as f:
                    data = json.load(f)
                    self.custom_rankings = data.get('custom_rankings', {})
                    self.player_tiers = data.get('player_tiers', {})
                    self.tier_breaks = set(data.get('tier_breaks', []))
                    
                    # Convert string keys back to proper format if needed
                    self.custom_rankings = {k: int(v) for k, v in self.custom_rankings.items()}
                    self.player_tiers = {k: int(v) for k, v in self.player_tiers.items()}
            except:
                pass
    
    def reset_rankings(self):
        if messagebox.askyesno("Reset Rankings", "Are you sure you want to reset all custom rankings and tiers?"):
            self.custom_rankings = {}
            self.player_tiers = {}
            self.tier_breaks = set()
            self.update_display()
            
            if self.on_rankings_update:
                self.on_rankings_update(self.custom_rankings, self.player_tiers)