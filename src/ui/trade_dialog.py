import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from .theme import DARK_THEME
from .styled_widgets import StyledFrame, StyledButton
from ..services.draft_trade_service import DraftTradeService


class TradeDialog:
    """Dialog for configuring draft pick trades"""
    
    def __init__(self, parent, num_teams: int, total_rounds: int, 
                 trade_service: DraftTradeService, on_apply: Optional[Callable] = None):
        self.parent = parent
        self.num_teams = num_teams
        self.total_rounds = total_rounds
        self.trade_service = trade_service
        self.on_apply = on_apply
        
        # Create the dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Configure Draft Pick Trades")
        self.dialog.geometry("800x600")
        self.dialog.configure(bg=DARK_THEME['bg_primary'])
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"800x600+{x}+{y}")
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = StyledFrame(self.dialog, bg_type='primary')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Draft Pick Trades",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Trade configuration section
        config_frame = StyledFrame(main_frame, bg_type='secondary')
        config_frame.pack(fill='x', pady=(0, 20))
        
        # Quick trade setup for the specific scenario
        quick_frame = StyledFrame(config_frame, bg_type='secondary')
        quick_frame.pack(fill='x', padx=20, pady=20)
        
        quick_label = tk.Label(
            quick_frame,
            text="Quick Trade Setup:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        quick_label.pack(anchor='w', pady=(0, 10))
        
        # Example trade button
        example_button = StyledButton(
            quick_frame,
            text="Team 8 (1st, 4th, 10th) ⇄ Team 7 (2nd, 3rd, 11th)",
            command=self.add_example_trade,
            bg=DARK_THEME['button_active'],
            font=(DARK_THEME['font_family'], 11),
            padx=20,
            pady=10
        )
        example_button.pack(pady=5)
        
        # Custom trade configuration
        custom_frame = StyledFrame(config_frame, bg_type='secondary')
        custom_frame.pack(fill='x', padx=20, pady=20)
        
        custom_label = tk.Label(
            custom_frame,
            text="Custom Trade:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        custom_label.pack(anchor='w', pady=(0, 10))
        
        # Team and round selection
        selection_frame = tk.Frame(custom_frame, bg=DARK_THEME['bg_secondary'])
        selection_frame.pack(fill='x')
        
        # Team 1 selection
        team1_frame = tk.Frame(selection_frame, bg=DARK_THEME['bg_secondary'])
        team1_frame.pack(side='left', padx=10)
        
        tk.Label(
            team1_frame,
            text="Team 1:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary']
        ).pack()
        
        self.team1_var = tk.StringVar(value="1")
        team1_dropdown = ttk.Combobox(
            team1_frame,
            textvariable=self.team1_var,
            values=[str(i) for i in range(1, self.num_teams + 1)],
            width=10,
            state='readonly'
        )
        team1_dropdown.pack(pady=5)
        
        tk.Label(
            team1_frame,
            text="Rounds to trade:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary']
        ).pack(pady=(10, 5))
        
        # Team 1 round checkboxes
        self.team1_rounds = {}
        team1_rounds_frame = tk.Frame(team1_frame, bg=DARK_THEME['bg_secondary'])
        team1_rounds_frame.pack()
        
        for r in range(1, min(self.total_rounds + 1, 13)):  # Show first 12 rounds
            var = tk.BooleanVar()
            cb = tk.Checkbutton(
                team1_rounds_frame,
                text=f"R{r}",
                variable=var,
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_primary'],
                selectcolor=DARK_THEME['bg_tertiary']
            )
            cb.grid(row=(r-1)//4, column=(r-1)%4, padx=2, pady=2)
            self.team1_rounds[r] = var
        
        # Arrow
        arrow_label = tk.Label(
            selection_frame,
            text="⇄",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 20)
        )
        arrow_label.pack(side='left', padx=20)
        
        # Team 2 selection
        team2_frame = tk.Frame(selection_frame, bg=DARK_THEME['bg_secondary'])
        team2_frame.pack(side='left', padx=10)
        
        tk.Label(
            team2_frame,
            text="Team 2:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary']
        ).pack()
        
        self.team2_var = tk.StringVar(value="2")
        team2_dropdown = ttk.Combobox(
            team2_frame,
            textvariable=self.team2_var,
            values=[str(i) for i in range(1, self.num_teams + 1)],
            width=10,
            state='readonly'
        )
        team2_dropdown.pack(pady=5)
        
        tk.Label(
            team2_frame,
            text="Rounds to trade:",
            bg=DARK_THEME['bg_secondary'],
            fg=DARK_THEME['text_secondary']
        ).pack(pady=(10, 5))
        
        # Team 2 round checkboxes
        self.team2_rounds = {}
        team2_rounds_frame = tk.Frame(team2_frame, bg=DARK_THEME['bg_secondary'])
        team2_rounds_frame.pack()
        
        for r in range(1, min(self.total_rounds + 1, 13)):  # Show first 12 rounds
            var = tk.BooleanVar()
            cb = tk.Checkbutton(
                team2_rounds_frame,
                text=f"R{r}",
                variable=var,
                bg=DARK_THEME['bg_secondary'],
                fg=DARK_THEME['text_primary'],
                selectcolor=DARK_THEME['bg_tertiary']
            )
            cb.grid(row=(r-1)//4, column=(r-1)%4, padx=2, pady=2)
            self.team2_rounds[r] = var
        
        # Add trade button
        add_button = StyledButton(
            custom_frame,
            text="Add Trade",
            command=self.add_custom_trade,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11),
            padx=20,
            pady=8
        )
        add_button.pack(pady=(20, 0))
        
        # Current trades list
        trades_label = tk.Label(
            main_frame,
            text="Current Trades:",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 12, 'bold')
        )
        trades_label.pack(anchor='w', pady=(0, 10))
        
        # Trades listbox
        listbox_frame = StyledFrame(main_frame, bg_type='secondary')
        listbox_frame.pack(fill='both', expand=True)
        
        self.trades_listbox = tk.Listbox(
            listbox_frame,
            bg=DARK_THEME['bg_tertiary'],
            fg=DARK_THEME['text_primary'],
            font=(DARK_THEME['font_family'], 10),
            selectbackground=DARK_THEME['button_active'],
            selectforeground='white',
            height=8
        )
        self.trades_listbox.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Update the trades list
        self.update_trades_list()
        
        # Button frame
        button_frame = tk.Frame(main_frame, bg=DARK_THEME['bg_primary'])
        button_frame.pack(fill='x', pady=(20, 0))
        
        # Clear all button
        clear_button = StyledButton(
            button_frame,
            text="Clear All",
            command=self.clear_all_trades,
            bg=DARK_THEME['button_danger'],
            font=(DARK_THEME['font_family'], 11),
            padx=20,
            pady=10
        )
        clear_button.pack(side='left', padx=(0, 10))
        
        # Cancel button
        cancel_button = StyledButton(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            bg=DARK_THEME['button_bg'],
            font=(DARK_THEME['font_family'], 11),
            padx=20,
            pady=10
        )
        cancel_button.pack(side='right', padx=(10, 0))
        
        # Apply button
        apply_button = StyledButton(
            button_frame,
            text="Apply Trades",
            command=self.apply_trades,
            bg=DARK_THEME['button_active'],
            font=(DARK_THEME['font_family'], 11),
            padx=20,
            pady=10
        )
        apply_button.pack(side='right')
    
    def add_example_trade(self):
        """Add the example trade (Team 8's 1st+4th+10th for Team 7's 2nd+3rd+11th)"""
        self.trade_service.add_trade(8, [1, 4, 10], 7, [2, 3, 11])
        self.update_trades_list()
        messagebox.showinfo(
            "Trade Added",
            "Added trade: Team 8 (R1, R4, R10) ⇄ Team 7 (R2, R3, R11)"
        )
    
    def add_custom_trade(self):
        """Add a custom trade based on the current selections"""
        team1 = int(self.team1_var.get())
        team2 = int(self.team2_var.get())
        
        if team1 == team2:
            messagebox.showerror("Error", "Cannot trade with the same team")
            return
        
        team1_rounds = [r for r, var in self.team1_rounds.items() if var.get()]
        team2_rounds = [r for r, var in self.team2_rounds.items() if var.get()]
        
        if not team1_rounds or not team2_rounds:
            messagebox.showerror("Error", "Please select rounds to trade for both teams")
            return
        
        self.trade_service.add_trade(team1, team1_rounds, team2, team2_rounds)
        self.update_trades_list()
        
        # Clear selections
        for var in self.team1_rounds.values():
            var.set(False)
        for var in self.team2_rounds.values():
            var.set(False)
    
    def clear_all_trades(self):
        """Clear all trades"""
        self.trade_service.clear_trades()
        self.update_trades_list()
    
    def update_trades_list(self):
        """Update the trades listbox with current trades"""
        self.trades_listbox.delete(0, tk.END)
        for summary in self.trade_service.get_trades_summary():
            self.trades_listbox.insert(tk.END, summary)
    
    def apply_trades(self):
        """Apply the trades and close the dialog"""
        if self.on_apply:
            self.on_apply()
        self.dialog.destroy()