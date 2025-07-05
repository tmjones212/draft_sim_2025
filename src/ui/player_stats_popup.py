import tkinter as tk
from tkinter import ttk
from typing import Optional
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class PlayerStatsPopup:
    def __init__(self, parent, player: Player, image_service=None):
        self.player = player
        self.parent = parent
        self.image_service = image_service
        self.sort_column = None
        self.sort_ascending = True
        self.weekly_data = []  # Store weekly data for sorting
        
        # Create popup window
        self.window = tk.Toplevel(parent)
        self.window.title(f"{player.format_name()} - 2024 Stats")
        self.window.configure(bg=DARK_THEME['bg_primary'])
        
        # Hide window initially to prevent flashing
        self.window.withdraw()
        
        # Set window size
        self.window.geometry("800x600")
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"800x600+{x}+{y}")
        
        # Show window after positioning
        self.window.deiconify()
        
        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()
        
        # Bind escape key to close
        self.window.bind('<Escape>', lambda e: self.close())
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = StyledFrame(self.window, bg_type='primary')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header with player info
        header_frame = StyledFrame(main_frame, bg_type='secondary')
        header_frame.pack(fill='x', pady=(0, 20))
        header_frame.configure(relief='flat', bd=1, highlightbackground=DARK_THEME['border'])
        
        # Player info container with 3 sections
        info_frame = tk.Frame(header_frame, bg=DARK_THEME['bg_secondary'])
        info_frame.pack(fill='x', padx=20, pady=15)
        
        # LEFT: Player name, position, and team
        left_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_secondary'])
        left_frame.pack(side='left', fill='both', expand=True)
        
        name_frame = tk.Frame(left_frame, bg=DARK_THEME['bg_secondary'])
        name_frame.pack(anchor='w')
        
        name_label = tk.Label(
            name_frame,
            text=self.player.format_name(),
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 20, 'bold')
        )
        name_label.pack(side='left', padx=(0, 10))
        
        # Position badge
        pos_bg = get_position_color(self.player.position)
        pos_label = tk.Label(
            name_frame,
            text=self.player.position,
            bg=pos_bg,
            fg='white',
            font=(DARK_THEME['font_family'], 12, 'bold'),
            padx=12,
            pady=4
        )
        pos_label.pack(side='left')
        
        # Team info
        if self.player.team:
            team_label = tk.Label(
                name_frame,
                text=f"• {self.player.team}",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 14)
            )
            team_label.pack(side='left', padx=(10, 0))
        
        # CENTER: Player image
        center_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_secondary'])
        center_frame.pack(side='left', padx=20)
        
        # Player image placeholder
        image_label = tk.Label(
            center_frame,
            bg=DARK_THEME['bg_tertiary'],
            width=80,
            height=80,
            text="",
            relief='flat'
        )
        image_label.pack()
        
        # Load player image if available
        if self.image_service and self.player.player_id:
            player_image = self.image_service.get_image(self.player.player_id, size=(80, 64))
            if player_image:
                image_label.configure(image=player_image)
                image_label.image = player_image  # Keep reference
            else:
                # Try to load async
                def update_image(photo):
                    if image_label.winfo_exists():
                        image_label.configure(image=photo)
                        image_label.image = photo
                
                self.image_service.load_image_async(
                    self.player.player_id,
                    size=(80, 64),
                    callback=update_image,
                    widget=self.window
                )
        
        # RIGHT: Season totals
        totals_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_secondary'])
        totals_frame.pack(side='right')
        
        if self.player.points_2024:
            total_label = tk.Label(
                totals_frame,
                text=f"2024 Total: {self.player.points_2024:.1f} pts",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 12, 'bold')
            )
            total_label.pack()
            
        if self.player.games_2024:
            avg_label = tk.Label(
                totals_frame,
                text=f"Games: {self.player.games_2024} | Avg: {self.player.points_2024/self.player.games_2024:.1f} pts/game",
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10)
            )
            avg_label.pack()
        
        # Weekly stats container
        stats_container = StyledFrame(main_frame, bg_type='tertiary')
        stats_container.pack(fill='both', expand=True)
        
        # Check if we have weekly stats
        if not hasattr(self.player, 'weekly_stats_2024') or not self.player.weekly_stats_2024 or len(self.player.weekly_stats_2024) == 0:
            # No stats available
            no_stats_label = tk.Label(
                stats_container,
                text="No weekly stats available for 2024",
                bg=DARK_THEME['bg_tertiary'],
                fg=DARK_THEME['text_muted'],
                font=(DARK_THEME['font_family'], 14)
            )
            no_stats_label.pack(expand=True)
            return
        
        # Create scrollable frame for weekly stats
        canvas = tk.Canvas(stats_container, bg=DARK_THEME['bg_tertiary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(stats_container, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DARK_THEME['bg_tertiary'])
        
        # Create window in canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Configure canvas scrolling
        def configure_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Update window width to match canvas
            canvas_width = event.width if event else canvas.winfo_width()
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        scrollable_frame.bind("<Configure>", configure_scroll)
        canvas.bind("<Configure>", configure_scroll)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel to canvas and all child widgets
        canvas.bind("<MouseWheel>", on_mousewheel)
        # Also bind to the popup window itself
        self.window.bind("<MouseWheel>", on_mousewheel)
        
        # Define column widths (in pixels) - must match data cells exactly
        col_widths = {
            'week': 50,
            'opp': 80,
            'points': 70,
            'snaps': 60,
            'pass_yds': 70,
            'pass_td': 60,
            'int': 40,
            'rush_yds': 70,
            'rush_td': 60,
            'rec': 40,
            'rec_yds': 70,
            'rec_td': 60,
        }
        
        # Table header
        header_row = tk.Frame(scrollable_frame, bg=DARK_THEME['bg_primary'], height=35)
        header_row.pack(fill='x', padx=10, pady=(10, 5))
        header_row.pack_propagate(False)
        
        # Create header cells with exact widths and sorting
        def create_header_cell(parent, text, width, sort_key=None):
            cell = tk.Frame(parent, bg=DARK_THEME['bg_primary'], width=width, height=35)
            cell.pack(side='left', padx=1)
            cell.pack_propagate(False)
            
            # Container for label and arrow
            content = tk.Frame(cell, bg=DARK_THEME['bg_primary'])
            content.pack(expand=True)
            
            label = tk.Label(
                content,
                text=text,
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10, 'bold')
            )
            label.pack(side='left')
            
            # Sort arrow label (initially hidden)
            arrow_label = tk.Label(
                content,
                text="",
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 8)
            )
            arrow_label.pack(side='left', padx=(2, 0))
            
            # Make clickable if sort_key provided
            if sort_key:
                cell.config(cursor='hand2')
                label.config(cursor='hand2')
                
                def on_click(e):
                    self.sort_data(sort_key, arrow_label)
                
                cell.bind('<Button-1>', on_click)
                label.bind('<Button-1>', on_click)
                
                # Store arrow label for updating
                cell._arrow_label = arrow_label
                cell._sort_key = sort_key
            
            return cell
        
        # Header columns
        self.header_cells = []
        self.header_cells.append(create_header_cell(header_row, 'Week', col_widths['week'], 'week'))
        self.header_cells.append(create_header_cell(header_row, 'Opp', col_widths['opp'], 'opponent'))
        self.header_cells.append(create_header_cell(header_row, 'Points', col_widths['points'], 'points'))
        self.header_cells.append(create_header_cell(header_row, 'Snaps', col_widths['snaps'], 'snaps'))
        
        # Add position-specific headers
        if self.player.position == 'QB':
            self.header_cells.append(create_header_cell(header_row, 'Pass Yds', col_widths['pass_yds'], 'pass_yd'))
            self.header_cells.append(create_header_cell(header_row, 'Pass TD', col_widths['pass_td'], 'pass_td'))
            self.header_cells.append(create_header_cell(header_row, 'INT', col_widths['int'], 'pass_int'))
            self.header_cells.append(create_header_cell(header_row, 'Rush Yds', col_widths['rush_yds'], 'rush_yd'))
            self.header_cells.append(create_header_cell(header_row, 'Rush TD', col_widths['rush_td'], 'rush_td'))
        elif self.player.position in ['RB', 'WR', 'TE']:
            self.header_cells.append(create_header_cell(header_row, 'Rush Yds', col_widths['rush_yds'], 'rush_yd'))
            self.header_cells.append(create_header_cell(header_row, 'Rush TD', col_widths['rush_td'], 'rush_td'))
            self.header_cells.append(create_header_cell(header_row, 'Rec', col_widths['rec'], 'rec'))
            self.header_cells.append(create_header_cell(header_row, 'Rec Yds', col_widths['rec_yds'], 'rec_yd'))
            self.header_cells.append(create_header_cell(header_row, 'Rec TD', col_widths['rec_td'], 'rec_td'))
        
        # Create a helper to make data cells
        def create_data_cell(parent, text, width, bg, fg=None):
            cell = tk.Frame(parent, bg=bg, width=width, height=30)
            cell.pack(side='left', padx=1)
            cell.pack_propagate(False)
            label = tk.Label(
                cell,
                text=text,
                bg=bg,
                fg=fg or DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10)
            )
            label.pack(expand=True)
            return cell
        
        # Store references for redrawing
        self.scrollable_frame = scrollable_frame
        self.col_widths = col_widths
        
        # Build and display data
        self.build_weekly_data()
        self.display_weekly_data()
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True, padx=(10, 0))
        scrollbar.pack(side='right', fill='y', padx=(0, 10))
        
        # Force update to ensure everything is displayed
        self.window.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Removed note about snap count since we now have the data
        
        # Close button
        close_btn = tk.Button(
            main_frame,
            text='Close',
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=(DARK_THEME['font_family'], 10, 'bold'),
            bd=0,
            relief='flat',
            padx=20,
            pady=8,
            command=self.close,
            cursor='hand2',
            activebackground=DARK_THEME['button_hover']
        )
        close_btn.pack(pady=(5, 0))
        
    def close(self):
        self.window.grab_release()
        self.window.destroy()
    
    def build_weekly_data(self):
        """Build the weekly data structure for display and sorting"""
        self.weekly_data = []
        
        # Create a dictionary of weekly stats for easy lookup
        week_stats_dict = {}
        for week_data in self.player.weekly_stats_2024:
            week_stats_dict[week_data['week']] = week_data
        
        # Process all weeks except bye week
        for week_num in range(1, 19):
            # Skip bye week
            if hasattr(self.player, 'bye_week') and self.player.bye_week == week_num:
                continue
            
            week_entry = {'week': week_num}
            
            if week_num in week_stats_dict:
                week_data = week_stats_dict[week_num]
                stats = week_data.get('stats', {})
                
                # Store all relevant data
                week_entry['opponent'] = week_data['opponent']
                week_entry['team'] = week_data.get('team', '')
                week_entry['points'] = stats.get('pts_ppr', 0)
                week_entry['snaps'] = stats.get('off_snp', 0)
                
                # Position-specific stats
                if self.player.position == 'QB':
                    week_entry['pass_yd'] = stats.get('pass_yd', 0)
                    week_entry['pass_td'] = stats.get('pass_td', 0)
                    week_entry['pass_int'] = stats.get('pass_int', 0)
                    week_entry['rush_yd'] = stats.get('rush_yd', 0)
                    week_entry['rush_td'] = stats.get('rush_td', 0)
                elif self.player.position in ['RB', 'WR', 'TE']:
                    week_entry['rush_yd'] = stats.get('rush_yd', 0)
                    week_entry['rush_td'] = stats.get('rush_td', 0)
                    week_entry['rec'] = stats.get('rec', 0)
                    week_entry['rec_yd'] = stats.get('rec_yd', 0)
                    week_entry['rec_td'] = stats.get('rec_td', 0)
                
                week_entry['played'] = True
            else:
                # Player didn't play
                week_entry['opponent'] = 'DNP'
                week_entry['team'] = ''
                week_entry['points'] = 0
                week_entry['snaps'] = 0
                week_entry['played'] = False
                
                # Zero out position-specific stats
                if self.player.position == 'QB':
                    week_entry.update({'pass_yd': 0, 'pass_td': 0, 'pass_int': 0, 'rush_yd': 0, 'rush_td': 0})
                elif self.player.position in ['RB', 'WR', 'TE']:
                    week_entry.update({'rush_yd': 0, 'rush_td': 0, 'rec': 0, 'rec_yd': 0, 'rec_td': 0})
            
            self.weekly_data.append(week_entry)
    
    def display_weekly_data(self):
        """Display the weekly data in the scrollable frame"""
        # Clear existing rows
        for widget in self.scrollable_frame.winfo_children():
            if widget != self.scrollable_frame.winfo_children()[0]:  # Keep header
                widget.destroy()
        
        # Create data rows
        for i, week_entry in enumerate(self.weekly_data):
            row_bg = DARK_THEME['bg_secondary'] if i % 2 == 0 else DARK_THEME['bg_tertiary']
            row = tk.Frame(self.scrollable_frame, bg=row_bg, height=30)
            row.pack(fill='x', padx=10, pady=1)
            row.pack_propagate(False)
            
            # Helper to create cells
            def create_cell(text, width, fg=None):
                cell = tk.Frame(row, bg=row_bg, width=width, height=30)
                cell.pack(side='left', padx=1)
                cell.pack_propagate(False)
                label = tk.Label(
                    cell,
                    text=text,
                    bg=row_bg,
                    fg=fg or (DARK_THEME['text_primary'] if week_entry['played'] else DARK_THEME['text_muted']),
                    font=(DARK_THEME['font_family'], 10)
                )
                label.pack(expand=True)
            
            # Week number
            create_cell(f"{week_entry['week']}", self.col_widths['week'])
            
            # Opponent with home/away
            if week_entry['played']:
                is_home = (week_entry['week'] + hash(week_entry['team'])) % 2 == 0
                opponent_display = f"vs {week_entry['opponent']}" if is_home else f"@ {week_entry['opponent']}"
                create_cell(opponent_display, self.col_widths['opp'], DARK_THEME['text_secondary'])
            else:
                create_cell("DNP", self.col_widths['opp'], DARK_THEME['text_muted'])
            
            # Points
            create_cell(f"{week_entry['points']:.1f}", self.col_widths['points'],
                       DARK_THEME['text_primary'] if week_entry['points'] > 0 else DARK_THEME['text_muted'])
            
            # Snaps
            snaps_text = f"{int(week_entry['snaps'])}" if week_entry['snaps'] > 0 else '-'
            create_cell(snaps_text, self.col_widths['snaps'])
            
            # Position-specific stats
            if self.player.position == 'QB':
                create_cell(f"{int(week_entry['pass_yd'])}", self.col_widths['pass_yds'])
                create_cell(f"{int(week_entry['pass_td'])}", self.col_widths['pass_td'])
                create_cell(f"{int(week_entry['pass_int'])}", self.col_widths['int'])
                create_cell(f"{int(week_entry['rush_yd'])}", self.col_widths['rush_yds'])
                create_cell(f"{int(week_entry['rush_td'])}", self.col_widths['rush_td'])
            elif self.player.position in ['RB', 'WR', 'TE']:
                create_cell(f"{int(week_entry['rush_yd'])}", self.col_widths['rush_yds'])
                create_cell(f"{int(week_entry['rush_td'])}", self.col_widths['rush_td'])
                create_cell(f"{int(week_entry['rec'])}", self.col_widths['rec'])
                create_cell(f"{int(week_entry['rec_yd'])}", self.col_widths['rec_yds'])
                create_cell(f"{int(week_entry['rec_td'])}", self.col_widths['rec_td'])
    
    def sort_data(self, sort_key, arrow_label):
        """Sort the weekly data by the specified column"""
        # Toggle sort direction if clicking same column
        if self.sort_column == sort_key:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = sort_key
            self.sort_ascending = True
        
        # Clear all arrow labels
        for cell in self.header_cells:
            if hasattr(cell, '_arrow_label'):
                cell._arrow_label.config(text='')
        
        # Show arrow on current sort column
        arrow_label.config(text='▲' if self.sort_ascending else '▼')
        
        # Sort the data
        self.weekly_data.sort(
            key=lambda x: x.get(sort_key, 0),
            reverse=not self.sort_ascending
        )
        
        # Redisplay
        self.display_weekly_data()