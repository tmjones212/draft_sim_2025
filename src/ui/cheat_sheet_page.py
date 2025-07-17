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
    def __init__(self, parent, players: List[Player], **kwargs):
        super().__init__(parent, bg_type='primary', **kwargs)
        self.all_players = players
        
        # Configuration
        self.image_size = (90, 72)  # Same as ADP page
        
        # State
        self.player_images = {}  # Cache player images
        self.player_widgets = {}  # Map player_id to widget
        self.drag_data = None  # Current drag information
        self.drop_indicator = None
        self.tiers = self.load_tiers()  # Load saved tiers or create default
        
        self.setup_ui()
        # Delay initial display to ensure UI is ready
        self.after(10, self.update_display)
    
    def load_tiers(self) -> Dict[str, List[str]]:
        """Load saved tiers from file or create default tiers"""
        tier_file = os.path.join('data', 'cheat_sheet_tiers.json')
        if os.path.exists(tier_file):
            try:
                with open(tier_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default tiers
        return {
            "Elite": [],
            "Tier 1": [],
            "Tier 2": [],
            "Tier 3": [],
            "Tier 4": [],
            "Tier 5": [],
            "Sleepers": [],
            "Avoid": []
        }
    
    def save_tiers(self):
        """Save tiers to file"""
        os.makedirs('data', exist_ok=True)
        tier_file = os.path.join('data', 'cheat_sheet_tiers.json')
        with open(tier_file, 'w') as f:
            json.dump(self.tiers, f, indent=2)
    
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
        
        self.tiers_canvas.bind('<MouseWheel>', on_mousewheel)
        self.tiers_canvas.bind('<Button-4>', lambda e: self.tiers_canvas.yview_scroll(-1, 'units'))
        self.tiers_canvas.bind('<Button-5>', lambda e: self.tiers_canvas.yview_scroll(1, 'units'))
    
    def create_available_panel(self, parent):
        """Create the available players panel"""
        avail_frame = StyledFrame(parent, bg_type='secondary')
        parent.add(avail_frame)
        
        # Header
        header = tk.Label(
            avail_frame,
            text="AVAILABLE PLAYERS",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        header.pack(pady=10)
        
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
        
        self.avail_canvas.bind('<MouseWheel>', on_mousewheel)
        self.avail_canvas.bind('<Button-4>', lambda e: self.avail_canvas.yview_scroll(-1, 'units'))
        self.avail_canvas.bind('<Button-5>', lambda e: self.avail_canvas.yview_scroll(1, 'units'))
    
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
        
        # Display tiers
        tier_colors = {
            "Elite": '#FF5E5B',      # Red
            "Tier 1": '#FFB347',     # Orange
            "Tier 2": '#FFD700',     # Gold
            "Tier 3": '#4ECDC4',     # Teal
            "Tier 4": '#7B68EE',     # Purple
            "Tier 5": '#87CEEB',     # Sky Blue
            "Sleepers": '#90EE90',   # Light Green
            "Avoid": '#DC143C'       # Crimson
        }
        
        for tier_name, player_ids in self.tiers.items():
            self.create_tier_section(tier_name, player_ids, tier_colors.get(tier_name, '#808080'))
        
        # Display available players (not in any tier)
        available_players = [p for p in self.all_players if p.player_id not in tiered_player_ids]
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
    
    def create_tier_section(self, tier_name: str, player_ids: List[str], color: str):
        """Create a tier section with header and players"""
        # Tier header
        header_frame = tk.Frame(self.tiers_scrollable, bg=DARK_THEME['bg_primary'], height=35)
        header_frame.pack(fill='x', padx=0, pady=(5, 2))
        
        # Tier label
        tier_label = tk.Label(
            header_frame,
            text=f"{tier_name.upper()} ({len(player_ids)})",
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
        
        # Minimum height to show drop zone even when empty
        min_height = 150
        tier_frame.configure(height=max(min_height, ((len(player_ids) + 9) // 10) * 150))
        tier_frame.pack_propagate(False)
        
        # Get player objects
        players = []
        for player_id in player_ids:
            player = next((p for p in self.all_players if p.player_id == player_id), None)
            if player:
                players.append(player)
        
        # Create player widgets
        players_per_row = 10  # Same as ADP page
        for i, player in enumerate(players):
            row = i // players_per_row
            col = i % players_per_row
            self.create_player_widget(tier_frame, player, tier_name, row, col)
    
    def create_player_widget(self, parent: tk.Frame, player: Player, tier_name: Optional[str], 
                           row: int, col: int, is_available: bool = False):
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
            widget_width = 1.0 / 10 - 0.001
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
        
        # Player name
        name_label = tk.Label(
            player_frame,
            text=player.format_name() if hasattr(player, 'format_name') else player.name,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            wraplength=120 if is_available else 300
        )
        name_label.pack(pady=(2, 5))
        
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
        
        # Player name
        name_label = tk.Label(
            float_frame,
            text=player.format_name() if hasattr(player, 'format_name') else player.name,
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
    
    def handle_drop(self, source: tk.Widget, target: tk.Widget):
        """Handle dropping a player"""
        if not hasattr(source, 'player'):
            return
        
        player = source.player
        source_tier = source.tier_name if hasattr(source, 'tier_name') else None
        
        # Determine target tier
        if hasattr(target, 'tier_name'):
            # Dropped on a tier frame
            target_tier = target.tier_name
        elif hasattr(target, 'player') and hasattr(target, 'tier_name'):
            # Dropped on another player
            target_tier = target.tier_name
        elif target == self.avail_scrollable:
            # Dropped back to available
            target_tier = None
        else:
            return
        
        # Remove from source tier
        if source_tier:
            if player.player_id in self.tiers[source_tier]:
                self.tiers[source_tier].remove(player.player_id)
        
        # Add to target tier
        if target_tier:
            if player.player_id not in self.tiers[target_tier]:
                self.tiers[target_tier].append(player.player_id)
        
        # Save and refresh
        self.save_tiers()
        self.update_display()
    
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
    
    def reset_tiers(self):
        """Reset to default tiers"""
        if messagebox.askyesno("Reset Tiers", "Reset to default tiers? This will clear all custom rankings."):
            self.tiers = {
                "Elite": [],
                "Tier 1": [],
                "Tier 2": [],
                "Tier 3": [],
                "Tier 4": [],
                "Tier 5": [],
                "Sleepers": [],
                "Avoid": []
            }
            self.save_tiers()
            self.update_display()