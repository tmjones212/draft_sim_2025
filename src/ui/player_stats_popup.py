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
        if not self.player.weekly_stats_2024 or len(self.player.weekly_stats_2024) == 0:
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
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Table header
        header_row = tk.Frame(scrollable_frame, bg=DARK_THEME['bg_primary'], height=35)
        header_row.pack(fill='x', padx=10, pady=(10, 5))
        header_row.pack_propagate(False)
        
        # Header columns
        headers = [
            ('Week', 60),
            ('vs', 60),
            ('Points', 80),
        ]
        
        # Add position-specific headers
        if self.player.position == 'QB':
            headers.extend([
                ('Pass Yds', 80),
                ('Pass TD', 70),
                ('INT', 50),
                ('Rush Yds', 80),
                ('Rush TD', 70),
            ])
        elif self.player.position in ['RB', 'WR', 'TE']:
            headers.extend([
                ('Rush Yds', 80),
                ('Rush TD', 70),
                ('Rec', 50),
                ('Rec Yds', 80),
                ('Rec TD', 70),
            ])
        
        for header, width in headers:
            label = tk.Label(
                header_row,
                text=header,
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10, 'bold'),
                width=width // 8,
                anchor='center'
            )
            label.pack(side='left', padx=2)
        
        # Weekly data rows
        for i, week_data in enumerate(self.player.weekly_stats_2024):
            row_bg = DARK_THEME['bg_secondary'] if i % 2 == 0 else DARK_THEME['bg_tertiary']
            row = tk.Frame(scrollable_frame, bg=row_bg, height=30)
            row.pack(fill='x', padx=10, pady=1)
            row.pack_propagate(False)
            
            # Week number
            week_label = tk.Label(
                row,
                text=f"Week {week_data['week']}",
                bg=row_bg,
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10),
                width=60 // 8,
                anchor='center'
            )
            week_label.pack(side='left', padx=2)
            
            # Opponent
            opp_text = f"@ {week_data['opponent']}" if '@' in str(week_data.get('opponent', '')) else f"vs {week_data['opponent']}"
            opp_label = tk.Label(
                row,
                text=opp_text,
                bg=row_bg,
                fg=DARK_THEME['text_secondary'],
                font=(DARK_THEME['font_family'], 10),
                width=60 // 8,
                anchor='center'
            )
            opp_label.pack(side='left', padx=2)
            
            # Get stats data
            stats = week_data.get('stats', {})
            
            # Points (use custom scoring if available)
            points = stats.get('pts_custom', stats.get('pts_ppr', 0))
            points_label = tk.Label(
                row,
                text=f"{points:.1f}",
                bg=row_bg,
                fg=DARK_THEME['text_primary'],
                font=(DARK_THEME['font_family'], 10, 'bold'),
                width=80 // 8,
                anchor='center'
            )
            points_label.pack(side='left', padx=2)
            
            # Position-specific stats
            if self.player.position == 'QB':
                # Passing stats
                pass_yds = stats.get('pass_yd', 0)
                pass_td = stats.get('pass_td', 0)
                pass_int = stats.get('pass_int', 0)
                rush_yds = stats.get('rush_yd', 0)
                rush_td = stats.get('rush_td', 0)
                
                for value, width in [(f"{int(pass_yds)}", 80), (f"{int(pass_td)}", 70), 
                                    (f"{int(pass_int)}", 50), (f"{int(rush_yds)}", 80), 
                                    (f"{int(rush_td)}", 70)]:
                    label = tk.Label(
                        row,
                        text=value,
                        bg=row_bg,
                        fg=DARK_THEME['text_primary'],
                        font=(DARK_THEME['font_family'], 10),
                        width=width // 8,
                        anchor='center'
                    )
                    label.pack(side='left', padx=2)
                    
            elif self.player.position in ['RB', 'WR', 'TE']:
                # Rushing/Receiving stats
                rush_yds = stats.get('rush_yd', 0)
                rush_td = stats.get('rush_td', 0)
                rec = stats.get('rec', 0)
                rec_yds = stats.get('rec_yd', 0)
                rec_td = stats.get('rec_td', 0)
                
                for value, width in [(f"{int(rush_yds)}", 80), (f"{int(rush_td)}", 70),
                                    (f"{int(rec)}", 50), (f"{int(rec_yds)}", 80),
                                    (f"{int(rec_td)}", 70)]:
                    label = tk.Label(
                        row,
                        text=value,
                        bg=row_bg,
                        fg=DARK_THEME['text_primary'],
                        font=(DARK_THEME['font_family'], 10),
                        width=width // 8,
                        anchor='center'
                    )
                    label.pack(side='left', padx=2)
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
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
        close_btn.pack(pady=(20, 0))
        
    def close(self):
        self.window.grab_release()
        self.window.destroy()