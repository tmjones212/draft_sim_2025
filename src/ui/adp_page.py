import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import List, Dict, Tuple, Optional
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame, StyledButton
from ..services.custom_adp_manager import CustomADPManager
import os
from PIL import Image, ImageTk
import math


class ADPPage(StyledFrame):
    def __init__(self, parent, players: List[Player], on_adp_change: Optional[callable] = None, **kwargs):
        super().__init__(parent, bg_type='primary', **kwargs)
        self.all_players = players
        self.on_adp_change = on_adp_change
        self.custom_adp_manager = CustomADPManager()
        
        # Configuration
        self.players_per_row = 10  # ALL players in a round on ONE row (10 per round)
        self.max_rounds = 20
        self.image_size = (90, 72)  # Larger images for visibility
        
        # State
        self.player_images = {}  # Cache player images
        self.player_widgets = {}  # Map player_id to widget
        self.drag_data = None  # Current drag information
        self.drop_indicator = None
        
        self.setup_ui()
        self.load_player_images()
        # Delay initial display to ensure UI is ready
        self.after(10, self.update_display)
    
    def setup_ui(self):
        # Header
        header_frame = StyledFrame(self, bg_type='secondary')
        header_frame.pack(fill='x', padx=0, pady=(5, 5))
        
        title_label = tk.Label(
            header_frame,
            text="ADP RANKINGS",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 16, 'bold')
        )
        title_label.pack(side='left', padx=10, pady=5)
        
        # Instructions
        instructions_label = tk.Label(
            header_frame,
            text="(Drag players to adjust ADP rankings • Changes apply to mock drafts)",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 10, 'italic')
        )
        instructions_label.pack(side='left', padx=10)
        
        # Reset button
        reset_btn = StyledButton(
            header_frame,
            text="RESET ADP",
            command=self.reset_adp,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 10, 'bold'),
            padx=15,
            pady=5
        )
        reset_btn.pack(side='right', padx=10)
        
        # Main content area with scrolling
        content_frame = StyledFrame(self, bg_type='primary')
        content_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
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
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Make scrollable frame fill canvas width
        def configure_frame_width(event=None):
            canvas_width = self.canvas.winfo_width()
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.canvas.bind('<Configure>', configure_frame_width)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            return "break"
        
        # Bind mousewheel to everything
        def bind_mousewheel_to_all(widget):
            widget.bind('<MouseWheel>', on_mousewheel)
            widget.bind('<Button-4>', lambda e: self.canvas.yview_scroll(-1, 'units'))
            widget.bind('<Button-5>', lambda e: self.canvas.yview_scroll(1, 'units'))
        
        # Bind to self (the entire ADP page)
        bind_mousewheel_to_all(self)
        bind_mousewheel_to_all(self.canvas)
        bind_mousewheel_to_all(self.scrollable_frame)
        
        # Store the binding function so we can use it on dynamically created widgets
        self.bind_mousewheel = bind_mousewheel_to_all
    
    def load_player_images(self):
        """Pre-load player images for better performance"""
        # This will be populated as we create player widgets
        pass
    
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
    
    def update_display(self, quick_refresh=False):
        """Update the ADP display"""
        print(f"ADPPage update_display: {len(self.all_players)} players")
        
        # Debug: Check if we have any players
        if not self.all_players:
            print("WARNING: No players to display in ADP page!")
            # Show a message to the user
            msg_label = tk.Label(
                self.scrollable_frame,
                text="No players loaded. Please check data files.",
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 14)
            )
            msg_label.pack(pady=50)
            return
        
        if not quick_refresh:
            # Full rebuild - clear existing widgets
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            self.player_widgets.clear()
        
        # Sort players by ADP
        sorted_players = sorted(self.all_players, key=lambda p: p.adp if p.adp else 999)
        print(f"Sorted {len(sorted_players)} players")
        
        # Debug: Show players around the round boundaries
        print(f"\nPlayers around Round 1/2 boundary:")
        for i, p in enumerate(sorted_players):
            if 8 <= p.adp <= 13:
                print(f"  ADP {p.adp}: {p.format_name()} - Goes to Round {1 if p.adp <= 10 else 2}")
        
        # Group players by ADP ranges for display
        rounds = {}
        for player in sorted_players:
            if player.adp:
                # Group by ADP ranges: 1-10, 11-20, etc.
                # Round 1: ADP 1.0 to 10.999...
                # Round 2: ADP 11.0 to 20.999...
                if player.adp <= 10:
                    round_num = 1
                elif player.adp <= 20:
                    round_num = 2
                elif player.adp <= 30:
                    round_num = 3
                else:
                    round_num = int((player.adp - 1) / 10) + 1
                
                if round_num not in rounds:
                    rounds[round_num] = []
                rounds[round_num].append(player)
        
        # Display rounds
        max_round = max(rounds.keys()) if rounds else 15
        rounds_to_display = max(15, max_round)
        
        for round_num in range(1, rounds_to_display + 1):
            players_in_round = rounds.get(round_num, [])
            
            # Skip empty rounds after round 10 if no players
            if round_num > 10 and not players_in_round:
                continue
            
            if not quick_refresh:
                # Create round header with player count
                self.create_round_header(round_num, len(players_in_round))
                
                # Create round content frame
                round_frame = StyledFrame(self.scrollable_frame, bg_type='secondary')
                round_frame.pack(fill='x', padx=0, pady=(0, 5))  # NO side padding - use FULL width
                # Fixed height - ONE ROW ONLY
                frame_height = 150  # Reduced height - was too tall
                round_frame.configure(height=frame_height)
                round_frame.pack_propagate(False)
                round_frame.round_num = round_num
                
                # Bind mouse wheel to round frame
                if hasattr(self, 'bind_mousewheel'):
                    self.bind_mousewheel(round_frame)
            else:
                # Find existing round frame
                round_frame = None
                for child in self.scrollable_frame.winfo_children():
                    if hasattr(child, 'round_num') and child.round_num == round_num:
                        round_frame = child
                        break
                if not round_frame:
                    continue
            
            # Create player widgets in this round - ALL ON ONE ROW
            # For display, we show the ADP range this round represents
            adp_start = (round_num - 1) * 10 + 1
            adp_end = round_num * 10
            print(f"Round {round_num} (ADP {adp_start}-{adp_end}): {len(players_in_round)} players")
            if players_in_round:
                print(f"  First 5: {[p.format_name() + f' (ADP {p.adp})' for p in players_in_round[:5]]}")
                if len(players_in_round) > 10:
                    print(f"  Players 11+: {[p.format_name() + f' (ADP {p.adp})' for p in players_in_round[10:]]}")
            
            # Pass total count so widgets can size properly
            total_in_round = len(players_in_round)
            
            # Determine if this round goes left-to-right or right-to-left
            if round_num == 1:
                reverse_order = False  # Forward
            elif round_num == 2 or round_num == 3:
                reverse_order = True  # Reverse (both rounds 2 and 3)
            else:
                # After round 3, normal snake draft
                reverse_order = (round_num % 2 == 1)  # Odd rounds reverse
            
            # Create player widgets in the appropriate order
            if reverse_order:
                # Right to left - reverse the player order
                for i, player in enumerate(reversed(players_in_round)):
                    self.create_player_widget(round_frame, player, round_num, player.adp, i, 0, i, total_in_round)
            else:
                # Left to right - normal order
                for i, player in enumerate(players_in_round):
                    self.create_player_widget(round_frame, player, round_num, player.adp, i, 0, i, total_in_round)
        
        # Update the canvas scroll region after adding all content
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def create_round_header(self, round_num: int, player_count: int = 0):
        """Create a round header with player count"""
        header_frame = tk.Frame(self.scrollable_frame, bg=DARK_THEME['bg_primary'], height=30)
        header_frame.pack(fill='x', padx=0, pady=(2, 2))  # NO side padding
        
        # Determine round color
        if round_num <= 3:
            color = '#FF5E5B'  # Red
        elif round_num <= 6:
            color = '#FFB347'  # Orange
        elif round_num <= 9:
            color = '#4ECDC4'  # Teal
        elif round_num <= 12:
            color = '#7B68EE'  # Purple
        else:
            color = '#808080'  # Gray
        
        # Round label with player count
        round_label = tk.Label(
            header_frame,
            text=f"ROUND {round_num} ({player_count})",
            bg=color,
            fg='white',
            font=(DARK_THEME['font_family'], 12, 'bold'),
            padx=15,
            pady=5
        )
        round_label.pack(side='left', padx=10)
        
        # ADP range label with direction arrow
        adp_start = (round_num - 1) * 10 + 1
        adp_end = round_num * 10
        
        # Determine draft direction based on 3rd round reversal rules
        if round_num == 1:
            direction_arrow = "→"  # Forward
        elif round_num == 2 or round_num == 3:
            direction_arrow = "←"  # Reverse (both rounds 2 and 3)
        else:
            # After round 3, normal snake draft
            if round_num % 2 == 0:
                direction_arrow = "→"  # Forward
            else:
                direction_arrow = "←"  # Reverse
        
        adp_label = tk.Label(
            header_frame,
            text=f"ADP {adp_start}-{adp_end}",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 10)
        )
        adp_label.pack(side='left', padx=10)
        
        # Larger arrow label
        arrow_label = tk.Label(
            header_frame,
            text=direction_arrow,
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 16, 'bold')
        )
        arrow_label.pack(side='left', padx=5)
        
        # Bind mouse wheel to header elements
        if hasattr(self, 'bind_mousewheel'):
            self.bind_mousewheel(header_frame)
            self.bind_mousewheel(round_label)
            self.bind_mousewheel(adp_label)
            self.bind_mousewheel(arrow_label)
    
    def create_player_widget(self, parent: tk.Frame, player: Player, round_num: int, pick_num: int, position: int, row: int = 0, col: int = 0, total_in_round: int = None):
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
        # Position based on total players in this round
        if total_in_round is None:
            total_in_round = 10  # Default
        widget_width = 1.0 / total_in_round - 0.001  # Tiny gap to maximize width
        widget_height = 145  # Reduced height - was too tall
        player_frame.place(
            relx=col / total_in_round,
            rely=0,
            relwidth=widget_width,
            height=widget_height
        )
        
        # Store player reference
        player_frame.player = player
        player_frame.pick_num = pick_num
        player_frame.round_num = round_num
        self.player_widgets[player.player_id] = player_frame
        
        # ADP number
        adp_label = tk.Label(
            player_frame,
            text=f"{int(pick_num)}" if pick_num else "N/A",
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_secondary'],
            font=(DARK_THEME['font_family'], 14, 'bold')
        )
        adp_label.pack(pady=(4, 2))
        
        # Player image or placeholder
        image = self.get_player_image(player)
        if image:
            image_label = tk.Label(
                player_frame,
                image=image,
                bg=DARK_THEME['bg_tertiary']
            )
            image_label.image = image  # Keep reference
            image_label.pack(pady=2)
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
            badge.pack(pady=5)
        
        # Player full name
        name_label = tk.Label(
            player_frame,
            text=player.format_name() if hasattr(player, 'format_name') else player.name,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            wraplength=300  # Much wider wrap so names don't break
        )
        name_label.pack(pady=(2, 5))
        
        # Make draggable
        self.make_draggable(player_frame)
        
        # Right-click context menu
        def on_right_click(event):
            # Create context menu
            context_menu = tk.Menu(player_frame, tearoff=0, bg=DARK_THEME['bg_tertiary'], fg=DARK_THEME['text_primary'])
            context_menu.add_command(
                label=f"Edit ADP ({int(player.adp) if player.adp else 'N/A'})",
                command=lambda: self.edit_player_adp(player)
            )
            context_menu.post(event.x_root, event.y_root)
        
        # Bind right-click to player frame and all its children
        def bind_right_click(widget):
            widget.bind('<Button-3>', on_right_click)  # Button-3 is right-click
            for child in widget.winfo_children():
                bind_right_click(child)
        
        bind_right_click(player_frame)
        
        # Bind mouse wheel scrolling to this widget and all children
        if hasattr(self, 'bind_mousewheel'):
            def bind_wheel_recursive(w):
                self.bind_mousewheel(w)
                for child in w.winfo_children():
                    bind_wheel_recursive(child)
            bind_wheel_recursive(player_frame)
        
        # Hover effect
        def on_enter(e):
            if not self.drag_data or self.drag_data['widget'] != player_frame:
                player_frame.configure(highlightbackground='#4ECDC4', highlightthickness=2)
        
        def on_leave(e):
            if not self.drag_data or self.drag_data['widget'] != player_frame:
                player_frame.configure(highlightbackground=DARK_THEME['border'], highlightthickness=1)
        
        player_frame.bind('<Enter>', on_enter)
        player_frame.bind('<Leave>', on_leave)
    
    def create_empty_slot(self, parent: tk.Frame, round_num: int, pick_num: int, position: int, row: int = 0, col: int = 0):
        """Create an empty slot that can receive drops"""
        slot_frame = tk.Frame(
            parent,
            bg=DARK_THEME['bg_primary'],
            relief='solid',
            borderwidth=1,
            highlightbackground=DARK_THEME['bg_tertiary'],
            highlightthickness=1
        )
        widget_width = 1 / self.players_per_row - 0.01
        widget_height = 140
        slot_frame.place(
            relx=col / self.players_per_row,
            rely=row * widget_height / parent.winfo_reqheight() if parent.winfo_reqheight() > 0 else row * 0.5,
            relwidth=widget_width,
            height=widget_height
        )
        
        # Store slot info
        slot_frame.is_empty = True
        slot_frame.pick_num = pick_num
        slot_frame.round_num = round_num
        
        # Pick number
        pick_label = tk.Label(
            slot_frame,
            text=f"{pick_num}",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 9)
        )
        pick_label.pack(expand=True)
    
    def make_draggable(self, widget: tk.Widget):
        """Make a widget draggable"""
        def start_drag(event):
            if hasattr(widget, 'player'):
                self.drag_data = {
                    'widget': widget,
                    'player': widget.player,
                    'start_x': event.x_root,
                    'start_y': event.y_root,
                    'offset_x': event.x,
                    'offset_y': event.y
                }
                # Visual feedback - make it semi-transparent
                widget.configure(highlightbackground='#FF5E5B', highlightthickness=3)
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(fg=DARK_THEME['text_muted'])
                # Lift widget
                widget.lift()
        
        def on_drag(event):
            if self.drag_data:
                # Update drop indicator
                self.update_drop_indicator(event.x_root, event.y_root)
        
        def end_drag(event):
            if self.drag_data:
                # Find drop target
                x, y = event.x_root, event.y_root
                target = self.find_drop_target(x, y)
                
                if target and target != self.drag_data['widget']:
                    self.handle_drop(self.drag_data['widget'], target)
                
                # Reset visual state (check if widget still exists)
                try:
                    self.drag_data['widget'].configure(
                        highlightbackground=DARK_THEME['border'],
                        highlightthickness=1
                    )
                    for child in self.drag_data['widget'].winfo_children():
                        if isinstance(child, tk.Label):
                            child.configure(fg=DARK_THEME['text_primary'])
                except tk.TclError:
                    # Widget was destroyed during refresh
                    pass
                
                # Clear drop indicator
                if self.drop_indicator:
                    self.drop_indicator.destroy()
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
    
    def update_drop_indicator(self, x: int, y: int):
        """Update visual feedback for drop location"""
        target = self.find_drop_target(x, y)
        
        if self.drop_indicator:
            self.drop_indicator.destroy()
            self.drop_indicator = None
        
        if target and target != self.drag_data['widget']:
            # Create drop indicator
            self.drop_indicator = tk.Frame(
                target.master,
                bg='#4ECDC4',
                height=140,
                width=5
            )
            
            # Position indicator
            target_x = target.winfo_x()
            if hasattr(target, 'player'):
                # Show indicator on the side where the player will be inserted
                if self.drag_data['widget'].pick_num < target.pick_num:
                    self.drop_indicator.place(x=target_x - 2, y=0, height=140)
                else:
                    self.drop_indicator.place(x=target_x + target.winfo_width() - 3, y=0, height=140)
            else:
                # Empty slot - show in middle
                self.drop_indicator.place(x=target_x + target.winfo_width()//2 - 2, y=0, height=140)
    
    def find_drop_target(self, x: int, y: int) -> Optional[tk.Widget]:
        """Find the widget under the given coordinates"""
        # Convert to canvas coordinates
        canvas_x = self.canvas.canvasx(x - self.canvas.winfo_rootx())
        canvas_y = self.canvas.canvasy(y - self.canvas.winfo_rooty())
        
        # Check all player widgets and empty slots
        for widget in self.scrollable_frame.winfo_children():
            if isinstance(widget, StyledFrame):  # Round frame
                for child in widget.winfo_children():
                    if isinstance(child, tk.Frame) and (hasattr(child, 'player') or hasattr(child, 'is_empty')):
                        wx = child.winfo_x() + widget.winfo_x()
                        wy = child.winfo_y() + widget.winfo_y()
                        ww = child.winfo_width()
                        wh = child.winfo_height()
                        
                        if wx <= canvas_x <= wx + ww and wy <= canvas_y <= wy + wh:
                            return child
        
        return None
    
    def handle_drop(self, source: tk.Widget, target: tk.Widget):
        """Handle dropping a player on a new position"""
        if not hasattr(source, 'player'):
            return
        
        player = source.player
        old_pick = source.pick_num
        old_round = source.round_num
        
        # Determine new pick number and round
        if hasattr(target, 'player'):
            new_pick = target.pick_num
            new_round = target.round_num
        else:
            # Empty slot
            new_pick = target.pick_num
            new_round = target.round_num
        
        if old_pick == new_pick:
            return
        
        # Get all players sorted by current ADP
        sorted_players = sorted(self.all_players, key=lambda p: p.adp if p.adp else 999)
        
        # Find the target ADP position based on the drop location
        if hasattr(target, 'player'):
            # Dropped on another player
            target_player = target.player
            target_index = sorted_players.index(target_player)
            
            # Check if we're moving within the same round
            source_round = old_round
            target_round = new_round
            
            # Simpler approach: determine where we're inserting based on visual feedback
            # The drop indicator shows on the left or right of the target
            
            # Remove the dragged player from consideration
            players_without_dragged = [p for p in sorted_players if p.player_id != player.player_id]
            
            # Find where we're inserting based on the drag direction
            if self.drag_data['widget'].pick_num < target.pick_num:
                # Dragging down/right - insert AFTER the target
                # Find target in the list without the dragged player
                target_idx = None
                for i, p in enumerate(players_without_dragged):
                    if p.player_id == target_player.player_id:
                        target_idx = i
                        break
                
                if target_idx is not None and target_idx < len(players_without_dragged) - 1:
                    # Insert between target and next
                    new_adp = (players_without_dragged[target_idx].adp + players_without_dragged[target_idx + 1].adp) / 2.0
                else:
                    # Insert after last
                    new_adp = target_player.adp + 0.5
            else:
                # Dragging up/left - insert BEFORE the target
                # Find target in the list without the dragged player
                target_idx = None
                for i, p in enumerate(players_without_dragged):
                    if p.player_id == target_player.player_id:
                        target_idx = i
                        break
                
                if target_idx is not None and target_idx > 0:
                    # Insert between previous and target
                    new_adp = (players_without_dragged[target_idx - 1].adp + players_without_dragged[target_idx].adp) / 2.0
                else:
                    # Insert at beginning
                    new_adp = max(0.5, target_player.adp - 0.5)
            
            # Keep within round boundaries if moving within same round
            if source_round == target_round:
                round_min = (target_round - 1) * 10 + 1
                round_max = target_round * 10
                new_adp = max(round_min, min(new_adp, round_max - 0.01))
        else:
            # Dropped on empty slot - use the round's ADP range
            new_adp = (new_round - 1) * 10 + 5  # Middle of the round
        
        # Only update the moved player's ADP, not everyone's
        player.adp = new_adp
        self.custom_adp_manager.set_custom_adp(player.player_id, new_adp)
        
        # Notify callback
        if self.on_adp_change:
            self.on_adp_change()
        
        # Quick refresh - only update the affected rounds
        self.quick_update_rounds([old_round, new_round])
    
    def quick_update_rounds(self, rounds_to_update):
        """Quickly update only specific rounds without full rebuild"""
        # Sort players by ADP
        sorted_players = sorted(self.all_players, key=lambda p: p.adp if p.adp else 999)
        
        # Group players by rounds
        rounds = {}
        for player in sorted_players:
            if player.adp:
                if player.adp <= 10:
                    round_num = 1
                elif player.adp <= 20:
                    round_num = 2
                elif player.adp <= 30:
                    round_num = 3
                else:
                    round_num = int((player.adp - 1) / 10) + 1
                
                if round_num not in rounds:
                    rounds[round_num] = []
                rounds[round_num].append(player)
        
        # Update only the affected rounds
        for round_num in set(rounds_to_update):
            if round_num is None:
                continue
                
            # Find the round frame
            round_frame = None
            for child in self.scrollable_frame.winfo_children():
                if isinstance(child, StyledFrame) and hasattr(child, 'round_num') and child.round_num == round_num:
                    round_frame = child
                    break
            
            if round_frame:
                # Clear existing player widgets in this round
                for widget in round_frame.winfo_children():
                    if isinstance(widget, tk.Frame) and hasattr(widget, 'player'):
                        widget.destroy()
                
                # Re-create player widgets for this round
                players_in_round = rounds.get(round_num, [])
                total_in_round = len(players_in_round)
                
                # Determine if this round goes left-to-right or right-to-left
                if round_num == 1:
                    reverse_order = False  # Forward
                elif round_num == 2 or round_num == 3:
                    reverse_order = True  # Reverse (both rounds 2 and 3)
                else:
                    # After round 3, normal snake draft
                    reverse_order = (round_num % 2 == 1)  # Odd rounds reverse
                
                # Create player widgets in the appropriate order
                if reverse_order:
                    # Right to left - reverse the player order
                    for i, player in enumerate(reversed(players_in_round)):
                        self.create_player_widget(round_frame, player, round_num, player.adp, i, 0, i, total_in_round)
                else:
                    # Left to right - normal order
                    for i, player in enumerate(players_in_round):
                        self.create_player_widget(round_frame, player, round_num, player.adp, i, 0, i, total_in_round)
                
                # Update the round header with new count
                # Find and update the header
                for child in self.scrollable_frame.winfo_children():
                    if isinstance(child, tk.Frame) and child != round_frame:
                        # Check if this is the header for our round
                        for label in child.winfo_children():
                            if isinstance(label, tk.Label) and f"ROUND {round_num}" in label.cget("text"):
                                label.config(text=f"ROUND {round_num} ({total_in_round})")
                                break
    
    def edit_player_adp(self, player: Player):
        """Show dialog to edit player's ADP value"""
        current_adp = player.adp if player.adp else 999
        
        # Determine current round
        old_round = self._get_round_from_adp(current_adp)
        
        # Create a simple dialog to input new ADP
        new_adp = simpledialog.askfloat(
            "Edit ADP",
            f"Enter new ADP for {player.format_name()}\n(Current: {current_adp:.1f})",
            initialvalue=current_adp,
            minvalue=1.0,
            maxvalue=300.0,
            parent=self
        )
        
        if new_adp is not None and new_adp != current_adp:
            # Update the player's ADP
            player.adp = new_adp
            self.custom_adp_manager.set_custom_adp(player.player_id, new_adp)
            
            # Notify callback
            if self.on_adp_change:
                self.on_adp_change()
            
            # Determine new round
            new_round = self._get_round_from_adp(new_adp)
            
            # Only refresh affected rounds
            rounds_to_update = [old_round, new_round] if old_round != new_round else [old_round]
            self.quick_update_rounds(rounds_to_update)
    
    def _get_round_from_adp(self, adp: float) -> int:
        """Get the round number from an ADP value"""
        if adp <= 10:
            return 1
        elif adp <= 20:
            return 2
        elif adp <= 30:
            return 3
        else:
            return int((adp - 1) / 10) + 1
    
    def reset_adp(self):
        """Reset all custom ADP values"""
        if messagebox.askyesno("Reset ADP", "Are you sure you want to reset all custom ADP values to defaults?"):
            self.custom_adp_manager.reset_all()
            
            # Reload players to get original ADP values
            if self.on_adp_change:
                self.on_adp_change()
            
            # Refresh display
            self.update_display()