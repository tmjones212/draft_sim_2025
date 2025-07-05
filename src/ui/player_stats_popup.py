import tkinter as tk
from tkinter import ttk
from typing import Optional
from ..models import Player
from .theme import DARK_THEME, get_position_color
from .styled_widgets import StyledFrame


class PlayerStatsPopup:
    def __init__(self, parent, player: Player):
        self.player = player
        self.parent = parent
        
        # Create popup window
        self.window = tk.Toplevel(parent)
        self.window.title(f"{player.format_name()} - 2024 Stats")
        self.window.configure(bg=DARK_THEME['bg_primary'])
        
        # Set window size and position
        self.window.geometry("800x600")
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"800x600+{x}+{y}")
        
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
        
        # Player info container
        info_frame = tk.Frame(header_frame, bg=DARK_THEME['bg_secondary'])
        info_frame.pack(fill='x', padx=20, pady=15)
        
        # Player name and position
        name_frame = tk.Frame(info_frame, bg=DARK_THEME['bg_secondary'])
        name_frame.pack(side='left')
        
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
        
        # Season totals on the right
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
        
        # Create header cells with exact widths
        def create_header_cell(parent, text, width):
            cell = tk.Frame(parent, bg=DARK_THEME['bg_primary'], width=width, height=35)
            cell.pack(side='left', padx=1)
            cell.pack_propagate(False)
            label = tk.Label(
                cell,
                text=text,
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10, 'bold')
            )
            label.pack(expand=True)
            return cell
        
        # Header columns
        create_header_cell(header_row, 'Week', col_widths['week'])
        create_header_cell(header_row, 'Opp', col_widths['opp'])
        create_header_cell(header_row, 'Points', col_widths['points'])
        create_header_cell(header_row, 'Snaps', col_widths['snaps'])
        
        # Add position-specific headers
        if self.player.position == 'QB':
            create_header_cell(header_row, 'Pass Yds', col_widths['pass_yds'])
            create_header_cell(header_row, 'Pass TD', col_widths['pass_td'])
            create_header_cell(header_row, 'INT', col_widths['int'])
            create_header_cell(header_row, 'Rush Yds', col_widths['rush_yds'])
            create_header_cell(header_row, 'Rush TD', col_widths['rush_td'])
        elif self.player.position in ['RB', 'WR', 'TE']:
            create_header_cell(header_row, 'Rush Yds', col_widths['rush_yds'])
            create_header_cell(header_row, 'Rush TD', col_widths['rush_td'])
            create_header_cell(header_row, 'Rec', col_widths['rec'])
            create_header_cell(header_row, 'Rec Yds', col_widths['rec_yds'])
            create_header_cell(header_row, 'Rec TD', col_widths['rec_td'])
        
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
        
        # Create a dictionary of weekly stats for easy lookup
        week_stats_dict = {}
        for week_data in self.player.weekly_stats_2024:
            week_stats_dict[week_data['week']] = week_data
        
        # Show all weeks except bye week
        row_index = 0
        for week_num in range(1, 19):
            # Skip bye week
            if hasattr(self.player, 'bye_week') and self.player.bye_week == week_num:
                continue
                
            row_bg = DARK_THEME['bg_secondary'] if row_index % 2 == 0 else DARK_THEME['bg_tertiary']
            row = tk.Frame(scrollable_frame, bg=row_bg, height=30)
            row.pack(fill='x', padx=10, pady=1)
            row.pack_propagate(False)
            row_index += 1
            
            # Check if player played this week
            if week_num in week_stats_dict:
                week_data = week_stats_dict[week_num]
                stats = week_data.get('stats', {})
                
                # Week number
                create_data_cell(row, f"{week_num}", col_widths['week'], row_bg)
                
                # Opponent with home/away indicator
                opponent = week_data['opponent']
                # Simple heuristic: alternate home/away each week for each team
                # In a real implementation, this would come from schedule data
                is_home = (week_num + hash(week_data.get('team', ''))) % 2 == 0
                opponent_display = f"vs {opponent}" if is_home else f"@ {opponent}"
                create_data_cell(row, opponent_display, col_widths['opp'], row_bg, DARK_THEME['text_secondary'])
                
                # Points
                points = stats.get('pts_ppr', 0)
                create_data_cell(row, f"{points:.1f}", col_widths['points'], row_bg, DARK_THEME['text_primary'] if points > 0 else DARK_THEME['text_muted'])
                
                # Snap count
                snaps = stats.get('off_snp', 0)
                create_data_cell(row, f"{int(snaps)}" if snaps > 0 else '-', col_widths['snaps'], row_bg)
                
                # Position-specific stats
                if self.player.position == 'QB':
                    pass_yds = stats.get('pass_yd', 0)
                    pass_td = stats.get('pass_td', 0)
                    pass_int = stats.get('pass_int', 0)
                    rush_yds = stats.get('rush_yd', 0)
                    rush_td = stats.get('rush_td', 0)
                    
                    create_data_cell(row, f"{int(pass_yds)}", col_widths['pass_yds'], row_bg)
                    create_data_cell(row, f"{int(pass_td)}", col_widths['pass_td'], row_bg)
                    create_data_cell(row, f"{int(pass_int)}", col_widths['int'], row_bg)
                    create_data_cell(row, f"{int(rush_yds)}", col_widths['rush_yds'], row_bg)
                    create_data_cell(row, f"{int(rush_td)}", col_widths['rush_td'], row_bg)
                    
                elif self.player.position in ['RB', 'WR', 'TE']:
                    rush_yds = stats.get('rush_yd', 0)
                    rush_td = stats.get('rush_td', 0)
                    rec = stats.get('rec', 0)
                    rec_yds = stats.get('rec_yd', 0)
                    rec_td = stats.get('rec_td', 0)
                    
                    create_data_cell(row, f"{int(rush_yds)}", col_widths['rush_yds'], row_bg)
                    create_data_cell(row, f"{int(rush_td)}", col_widths['rush_td'], row_bg)
                    create_data_cell(row, f"{int(rec)}", col_widths['rec'], row_bg)
                    create_data_cell(row, f"{int(rec_yds)}", col_widths['rec_yds'], row_bg)
                    create_data_cell(row, f"{int(rec_td)}", col_widths['rec_td'], row_bg)
            else:
                # Player didn't play this week - show zeros
                create_data_cell(row, f"{week_num}", col_widths['week'], row_bg)
                create_data_cell(row, "DNP", col_widths['opp'], row_bg, DARK_THEME['text_muted'])
                create_data_cell(row, "0.0", col_widths['points'], row_bg, DARK_THEME['text_muted'])
                create_data_cell(row, "0", col_widths['snaps'], row_bg, DARK_THEME['text_muted'])
                
                # Position-specific zeros
                if self.player.position == 'QB':
                    for width in [col_widths['pass_yds'], col_widths['pass_td'], col_widths['int'], 
                                 col_widths['rush_yds'], col_widths['rush_td']]:
                        create_data_cell(row, "0", width, row_bg, DARK_THEME['text_muted'])
                elif self.player.position in ['RB', 'WR', 'TE']:
                    for width in [col_widths['rush_yds'], col_widths['rush_td'], col_widths['rec'], 
                                 col_widths['rec_yds'], col_widths['rec_td']]:
                        create_data_cell(row, "0", width, row_bg, DARK_THEME['text_muted'])
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True, padx=(10, 0))
        scrollbar.pack(side='right', fill='y', padx=(0, 10))
        
        # Force update to ensure everything is displayed
        self.window.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Note about snap count
        note_label = tk.Label(
            main_frame,
            text="Note: Snap count data is not currently available",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_muted'],
            font=(DARK_THEME['font_family'], 9, 'italic')
        )
        note_label.pack(pady=(10, 5))
        
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