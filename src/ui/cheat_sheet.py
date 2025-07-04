import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Callable
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame, StyledButton
import json
import os


class CheatSheet(StyledFrame):
    def __init__(self, parent, players: List[Player], on_rankings_update: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg_type='primary', **kwargs)
        self.all_players = players
        self.on_rankings_update = on_rankings_update
        
        # Custom rankings and tiers
        self.custom_rankings = {}  # player_id -> custom_rank
        self.player_tiers = {}  # player_id -> tier
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
        self.selected_player = None
        self.tier_entries = {}
        
        self.setup_ui()
        self.load_rankings()
        self.update_display()
    
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
        
        # Instructions
        instructions = tk.Label(
            header_frame,
            text="(Drag rows to reorder • Click tier to cycle colors)",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 10, 'italic')
        )
        instructions.pack(side='left', padx=20)
        
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
            self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        
        self.canvas.bind('<MouseWheel>', on_mousewheel)
        self.scrollable_frame.bind('<MouseWheel>', on_mousewheel)
        
        # Create headers
        self.create_headers()
    
    def create_headers(self):
        header_frame = StyledFrame(self.scrollable_frame, bg_type='tertiary')
        header_frame.pack(fill='x', pady=(0, 5))
        
        # Column headers
        headers = [
            ("Rank", 60),
            ("Tier", 50),
            ("Pos", 45),
            ("Player", 200),
            ("Team", 45),
            ("ADP", 50),
            ("2024 Pts", 70),
            ("2025 Proj", 70),
        ]
        
        for text, width in headers:
            label = tk.Label(
                header_frame,
                text=text,
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10, 'bold'),
                width=width//8
            )
            label.pack(side='left', padx=5)
    
    def update_display(self):
        # Clear existing player frames
        for frame in self.player_frames:
            frame.destroy()
        self.player_frames = []
        self.tier_entries = {}
        
        # Get filtered and sorted players
        filtered_players = self.get_filtered_players()
        sorted_players = self.sort_players_by_custom_rank(filtered_players)
        
        # Create player rows
        for idx, player in enumerate(sorted_players):
            self.create_player_row(idx, player)
    
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
        
        # Custom rank entry
        rank_frame = tk.Frame(row_frame, bg=bg, width=60)
        rank_frame.pack(side='left', fill='y')
        rank_frame.pack_propagate(False)
        
        custom_rank = self.custom_rankings.get(player.player_id, idx + 1)
        rank_var = tk.StringVar(value=str(custom_rank))
        
        rank_entry = tk.Entry(
            rank_frame,
            textvariable=rank_var,
            bg=DARK_THEME['bg_hover'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            width=5,
            justify='center',
            bd=1,
            relief='flat'
        )
        rank_entry.pack(expand=True)
        rank_entry.bind('<Return>', lambda e: self.update_rank(player, rank_var.get()))
        rank_entry.bind('<FocusOut>', lambda e: self.update_rank(player, rank_var.get()))
        
        # Tier selector
        tier_frame = tk.Frame(row_frame, bg=bg, width=50)
        tier_frame.pack(side='left', fill='y')
        tier_frame.pack_propagate(False)
        
        current_tier = self.player_tiers.get(player.player_id, 0)
        tier_btn = tk.Button(
            tier_frame,
            text=str(current_tier) if current_tier > 0 else "-",
            bg=self.tier_colors.get(current_tier, bg),
            fg='black' if current_tier in [1, 2, 3, 5] else 'white',
            font=(DARK_THEME['font_family'], 10, 'bold'),
            bd=0,
            relief='flat',
            cursor='hand2',
            command=lambda p=player: self.cycle_tier(p)
        )
        tier_btn._tier_button = True  # Mark as tier button
        tier_btn.pack(expand=True, fill='both', padx=2, pady=2)
        self.tier_entries[player.player_id] = tier_btn
        
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
    
    def update_rank(self, player, new_rank_str):
        try:
            new_rank = int(new_rank_str)
            if new_rank < 1:
                new_rank = 1
            
            self.custom_rankings[player.player_id] = new_rank
            self.update_display()
            
            if self.on_rankings_update:
                self.on_rankings_update(self.custom_rankings, self.player_tiers)
        except ValueError:
            pass
    
    def cycle_tier(self, player):
        current_tier = self.player_tiers.get(player.player_id, 0)
        new_tier = (current_tier % 8) + 1 if current_tier < 8 else 0
        
        if new_tier == 0:
            if player.player_id in self.player_tiers:
                del self.player_tiers[player.player_id]
        else:
            self.player_tiers[player.player_id] = new_tier
        
        # Update button appearance
        if player.player_id in self.tier_entries:
            btn = self.tier_entries[player.player_id]
            if new_tier == 0:
                btn.config(
                    text="-",
                    bg=DARK_THEME['bg_tertiary'],
                    fg=DARK_THEME['text_primary']
                )
            else:
                btn.config(
                    text=str(new_tier),
                    bg=self.tier_colors.get(new_tier, DARK_THEME['bg_tertiary']),
                    fg='black' if new_tier in [1, 2, 3, 5] else 'white'
                )
        
        if self.on_rankings_update:
            self.on_rankings_update(self.custom_rankings, self.player_tiers)
    
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
                            if isinstance(child, tk.Entry):
                                child.delete(0, tk.END)
                                child.insert(0, str(i + 1))
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
                    # Only update if it's not a tier button
                    if not hasattr(widget, '_tier_button'):
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
                    # Rank entry
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Entry):
                            child.delete(0, tk.END)
                            child.insert(0, str(i + 1))
                            break
                            
                elif widget_index == 1 and isinstance(widget, tk.Frame):
                    # Tier button
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Button) and hasattr(child, '_tier_button'):
                            tier = self.player_tiers.get(player.player_id, 0)
                            if tier > 0:
                                child.config(
                                    text=str(tier),
                                    bg=self.tier_colors.get(tier),
                                    fg='black' if tier in [1, 2, 3, 5] else 'white'
                                )
                            else:
                                child.config(text="-", bg=frame.cget('bg'), fg=DARK_THEME['text_primary'])
                            child.config(command=lambda p=player: self.cycle_tier(p))
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
                    # 2024 Points
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            points = getattr(player, 'points_2024', 0)
                            child.config(text=f"{points:.0f}" if points else '-')
                            break
                            
                elif widget_index == 7 and isinstance(widget, tk.Frame):
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
        
        # Visual feedback - just highlight border of target row
        for i, frame in enumerate(self.player_frames):
            if i == target_index and frame != self.dragged_row:
                frame.configure(highlightbackground=DARK_THEME['accent_warning'], highlightthickness=2)
            else:
                frame.configure(highlightthickness=0)
    
    def end_drag(self, event):
        if not hasattr(self, 'dragged_row'):
            return
        
        # Reset visual feedback
        for frame in self.player_frames:
            frame.configure(highlightthickness=0)
        
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
        
        # Get current rankings
        filtered_players = self.get_filtered_players()
        sorted_players = self.sort_players_by_custom_rank(filtered_players)
        
        # Find current position of dragged player
        current_idx = None
        for i, p in enumerate(sorted_players):
            if p.player_id == self.dragged_player.player_id:
                current_idx = i
                break
        
        if current_idx is not None and target_index is not None:
            # Only reorder if position actually changed
            if current_idx != target_index:
                # Create new order of players
                players_in_view = [frame.player for frame in self.player_frames]
                
                # Move the player in the list
                player_to_move = players_in_view.pop(current_idx)
                
                # Adjust insertion point
                insert_idx = target_index
                if current_idx < target_index:
                    insert_idx -= 1
                
                players_in_view.insert(insert_idx, player_to_move)
                
                # Update only the affected range
                start_idx = min(current_idx, insert_idx)
                end_idx = max(current_idx, insert_idx) + 1
                
                # Just update the entire display - it's faster and cleaner
                # But do it in a way that doesn't destroy/recreate frames
                self._quick_refresh(players_in_view)
                
                # Update custom rankings
                self.custom_rankings = {}
                for i, player in enumerate(players_in_view):
                    self.custom_rankings[player.player_id] = i + 1
                
                # Defer the main page update
                if self.on_rankings_update:
                    self.after(1000, lambda: self.on_rankings_update(self.custom_rankings, self.player_tiers))
        
        # Clean up
        if hasattr(self, 'dragged_row'):
            delattr(self, 'dragged_row')
        if hasattr(self, 'dragged_player'):
            delattr(self, 'dragged_player')
        if hasattr(self, 'drag_start_y'):
            delattr(self, 'drag_start_y')
    
    def save_rankings(self):
        data = {
            'custom_rankings': self.custom_rankings,
            'player_tiers': self.player_tiers
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
                    
                    # Convert string keys back to proper format if needed
                    self.custom_rankings = {k: int(v) for k, v in self.custom_rankings.items()}
                    self.player_tiers = {k: int(v) for k, v in self.player_tiers.items()}
            except:
                pass
    
    def reset_rankings(self):
        if messagebox.askyesno("Reset Rankings", "Are you sure you want to reset all custom rankings and tiers?"):
            self.custom_rankings = {}
            self.player_tiers = {}
            self.update_display()
            
            if self.on_rankings_update:
                self.on_rankings_update(self.custom_rankings, self.player_tiers)