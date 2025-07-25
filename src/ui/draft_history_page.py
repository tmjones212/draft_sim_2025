import tkinter as tk
from tkinter import ttk
import json
import os
from typing import List, Dict, Any, Optional
from .theme import DARK_THEME
from ..services.manager_notes_service import ManagerNotesService

class DraftHistoryPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.draft_data: List[Dict[str, Any]] = []
        self.filtered_data: List[Dict[str, Any]] = []
        self.sort_column = None
        self.sort_ascending = True
        self.manager_notes_service = ManagerNotesService()
        
        self.setup_ui()
        self.load_draft_history()
        
    def setup_ui(self):
        # Create filter frame
        filter_frame = tk.Frame(self, bg=DARK_THEME['bg_primary'])
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        # Year filter
        tk.Label(filter_frame, text="Year:", bg=DARK_THEME['bg_primary'], fg=DARK_THEME['text_secondary']).pack(side="left", padx=(0, 5))
        self.year_var = tk.StringVar()
        self.year_combo = ttk.Combobox(filter_frame, textvariable=self.year_var, width=10, state="readonly")
        self.year_combo.pack(side="left", padx=(0, 20))
        self.year_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        
        # Player filter
        tk.Label(filter_frame, text="Player:", bg=DARK_THEME['bg_primary'], fg=DARK_THEME['text_secondary']).pack(side="left", padx=(0, 5))
        self.player_var = tk.StringVar()
        self.player_entry = ttk.Entry(filter_frame, textvariable=self.player_var, width=20)
        self.player_entry.pack(side="left", padx=(0, 20))
        self.player_entry.bind("<KeyRelease>", lambda e: self.apply_filters())
        
        # Position filter
        tk.Label(filter_frame, text="Position:", bg=DARK_THEME['bg_primary'], fg=DARK_THEME['text_secondary']).pack(side="left", padx=(0, 5))
        self.position_var = tk.StringVar()
        self.position_combo = ttk.Combobox(filter_frame, textvariable=self.position_var, width=10, state="readonly")
        self.position_combo.pack(side="left", padx=(0, 20))
        self.position_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        
        # Manager filter
        tk.Label(filter_frame, text="Manager:", bg=DARK_THEME['bg_primary'], fg=DARK_THEME['text_secondary']).pack(side="left", padx=(0, 5))
        self.manager_var = tk.StringVar()
        self.manager_combo = ttk.Combobox(filter_frame, textvariable=self.manager_var, width=15, state="readonly")
        self.manager_combo.pack(side="left", padx=(0, 20))
        self.manager_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())
        
        # Clear filters button
        clear_btn = ttk.Button(filter_frame, text="Clear Filters", command=self.clear_filters)
        clear_btn.pack(side="left", padx=10)
        
        # Manager Notes button
        notes_btn = ttk.Button(filter_frame, text="Manager Notes", command=self.open_manager_notes)
        notes_btn.pack(side="left", padx=5)
        
        # Second filter row
        filter_frame2 = tk.Frame(self, bg=DARK_THEME['bg_primary'])
        filter_frame2.pack(fill="x", padx=10, pady=(0, 5))
        
        # Year >= filter
        tk.Label(filter_frame2, text="Year ≥:", bg=DARK_THEME['bg_primary'], fg=DARK_THEME['text_secondary']).pack(side="left", padx=(0, 5))
        self.year_min_var = tk.StringVar()
        self.year_min_entry = ttk.Entry(filter_frame2, textvariable=self.year_min_var, width=8)
        self.year_min_entry.pack(side="left", padx=(0, 20))
        self.year_min_entry.bind("<KeyRelease>", lambda e: self.apply_filters())
        
        # Pick <= filter
        tk.Label(filter_frame2, text="Pick ≤:", bg=DARK_THEME['bg_primary'], fg=DARK_THEME['text_secondary']).pack(side="left", padx=(0, 5))
        self.pick_max_var = tk.StringVar()
        self.pick_max_entry = ttk.Entry(filter_frame2, textvariable=self.pick_max_var, width=8)
        self.pick_max_entry.pack(side="left", padx=(0, 20))
        self.pick_max_entry.bind("<KeyRelease>", lambda e: self.apply_filters())
        
        # Round <= filter
        tk.Label(filter_frame2, text="Round ≤:", bg=DARK_THEME['bg_primary'], fg=DARK_THEME['text_secondary']).pack(side="left", padx=(0, 5))
        self.round_max_var = tk.StringVar()
        self.round_max_entry = ttk.Entry(filter_frame2, textvariable=self.round_max_var, width=8)
        self.round_max_entry.pack(side="left", padx=(0, 20))
        self.round_max_entry.bind("<KeyRelease>", lambda e: self.apply_filters())
        
        # Create treeview with scrollbars
        tree_frame = tk.Frame(self, bg=DARK_THEME['bg_primary'])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        columns = ("year", "round", "pick", "overall", "player", "position", "nfl_team", "manager")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", 
                                yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Configure scrollbars
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configure column headings
        headings = {
            "year": ("Year", 35),
            "round": ("Rd", 25),
            "pick": ("Pk", 25),
            "overall": ("Ovr", 30),
            "player": ("Player", 80),
            "position": ("Pos", 25),
            "nfl_team": ("Tm", 25),
            "manager": ("Manager", 60)
        }
        
        for col, (heading, width) in headings.items():
            self.tree.heading(col, text=heading, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=width, minwidth=20)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure treeview colors
        style.configure("Treeview",
                      background=DARK_THEME['bg_secondary'],
                      foreground=DARK_THEME['text_primary'],
                      fieldbackground=DARK_THEME['bg_secondary'],
                      bordercolor=DARK_THEME['border'],
                      borderwidth=1)
        style.configure("Treeview.Heading",
                      background=DARK_THEME['bg_tertiary'],
                      foreground=DARK_THEME['text_primary'],
                      borderwidth=1)
        style.map('Treeview.Heading',
                background=[('active', DARK_THEME['bg_hover'])])
        
        # Style for alternating rows
        self.tree.tag_configure("oddrow", background=DARK_THEME['bg_tertiary'])
        self.tree.tag_configure("evenrow", background=DARK_THEME['bg_secondary'])
        
    def load_draft_history(self):
        """Load draft history from JSON file"""
        try:
            file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "draft_picks_history.json")
            with open(file_path, 'r') as f:
                self.draft_data = json.load(f)
                self.filtered_data = self.draft_data.copy()
                
            # Populate filter options
            years = sorted(list(set(pick.get("year", 0) for pick in self.draft_data)), reverse=True)
            self.year_combo["values"] = ["All"] + [str(year) for year in years]
            self.year_var.set("All")
            
            positions = sorted(list(set(pick.get("position", "") for pick in self.draft_data)))
            self.position_combo["values"] = ["All"] + positions
            self.position_var.set("All")
            
            managers = sorted(list(set(pick.get("manager", "") for pick in self.draft_data)))
            self.manager_combo["values"] = ["All"] + managers
            self.manager_var.set("All")
            
            # Display initial data
            self.update_display()
            
        except Exception as e:
            print(f"Error loading draft history: {e}")
            
    def apply_filters(self):
        """Apply filters to the data"""
        self.filtered_data = self.draft_data.copy()
        
        # Year filter
        year = self.year_var.get()
        if year and year != "All":
            self.filtered_data = [pick for pick in self.filtered_data 
                                if str(pick.get("year", "")) == year]
        
        # Player filter
        player = self.player_var.get().strip().upper()
        if player:
            self.filtered_data = [pick for pick in self.filtered_data 
                                if player in pick.get("player_name", "").upper()]
        
        # Position filter
        position = self.position_var.get()
        if position and position != "All":
            self.filtered_data = [pick for pick in self.filtered_data 
                                if pick.get("position", "") == position]
        
        # Manager filter
        manager = self.manager_var.get()
        if manager and manager != "All":
            self.filtered_data = [pick for pick in self.filtered_data 
                                if pick.get("manager", "") == manager]
        
        # Year >= filter
        year_min = self.year_min_var.get().strip()
        if year_min:
            try:
                year_min_int = int(year_min)
                self.filtered_data = [pick for pick in self.filtered_data 
                                    if pick.get("year", 0) >= year_min_int]
            except ValueError:
                pass
        
        # Pick <= filter
        pick_max = self.pick_max_var.get().strip()
        if pick_max:
            try:
                pick_max_int = int(pick_max)
                self.filtered_data = [pick for pick in self.filtered_data 
                                    if pick.get("overall_pick", 999) <= pick_max_int]
            except ValueError:
                pass
        
        # Round <= filter
        round_max = self.round_max_var.get().strip()
        if round_max:
            try:
                round_max_int = int(round_max)
                self.filtered_data = [pick for pick in self.filtered_data 
                                    if pick.get("round", 999) <= round_max_int]
            except ValueError:
                pass
        
        self.update_display()
        
    def clear_filters(self):
        """Clear all filters"""
        self.year_var.set("All")
        self.player_var.set("")
        self.position_var.set("All")
        self.manager_var.set("All")
        self.year_min_var.set("")
        self.pick_max_var.set("")
        self.round_max_var.set("")
        self.apply_filters()
        
    def sort_by_column(self, column):
        """Sort data by the clicked column"""
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
            
        # Define sort keys for each column
        sort_keys = {
            "year": lambda x: x.get("year", 0),
            "round": lambda x: x.get("round", 0),
            "pick": lambda x: x.get("pick", 0),
            "overall": lambda x: x.get("overall_pick", 0),
            "player": lambda x: x.get("player_name", ""),
            "position": lambda x: x.get("position", ""),
            "nfl_team": lambda x: x.get("nfl_team", ""),
            "team": lambda x: x.get("team_name", ""),
            "manager": lambda x: x.get("manager", "")
        }
        
        self.filtered_data.sort(key=sort_keys[column], reverse=not self.sort_ascending)
        self.update_display()
        
        # Update column headers to show sort direction
        for col in self.tree["columns"]:
            heading = self.tree.heading(col)["text"].rstrip(" ↑↓")
            if col == column:
                heading += " ↑" if self.sort_ascending else " ↓"
            self.tree.heading(col, text=heading)
            
    def update_display(self):
        """Update the treeview display with filtered data"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add filtered data
        for i, pick in enumerate(self.filtered_data):
            values = (
                pick.get("year", ""),
                pick.get("round", ""),
                pick.get("pick", ""),
                pick.get("overall_pick", ""),
                pick.get("player_name", ""),
                pick.get("position", ""),
                pick.get("nfl_team", ""),
                pick.get("manager", "")
            )
            
            tag = "oddrow" if i % 2 == 1 else "evenrow"
            self.tree.insert("", "end", values=values, tags=(tag,))
    
    def open_manager_notes(self):
        """Open dialog to edit manager notes"""
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Manager Draft Habit Notes")
        dialog.geometry("600x500")
        dialog.configure(bg=DARK_THEME['bg_primary'])
        
        # Make dialog modal
        dialog.transient(self)
        dialog.grab_set()
        
        # Create main frame
        main_frame = tk.Frame(dialog, bg=DARK_THEME['bg_primary'])
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Instructions
        instructions = tk.Label(
            main_frame,
            text="Add notes about each manager's draft habits. These will appear when hovering over their name during the draft.",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            wraplength=560,
            justify="left"
        )
        instructions.pack(pady=(0, 10))
        
        # Create scrollable frame for manager entries
        canvas = tk.Canvas(main_frame, bg=DARK_THEME['bg_primary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=DARK_THEME['bg_primary'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Get unique managers from data
        managers = sorted(list(set(pick.get("manager", "") for pick in self.draft_data if pick.get("manager"))))
        
        # Create entry for each manager
        self.note_entries = {}
        for manager in managers:
            if not manager:
                continue
                
            # Manager frame
            manager_frame = tk.Frame(scrollable_frame, bg=DARK_THEME['bg_primary'])
            manager_frame.pack(fill="x", pady=5)
            
            # Manager label (show both archive and draft names)
            draft_name = self.manager_notes_service.get_draft_name(manager)
            label_text = f"{manager}"
            if draft_name != manager:
                label_text += f" ({draft_name})"
            
            label = tk.Label(
                manager_frame,
                text=label_text,
                bg=DARK_THEME['bg_primary'],
                fg=DARK_THEME['text_primary'],
                width=20,
                anchor="w"
            )
            label.pack(side="left", padx=(0, 10))
            
            # Note entry
            note_var = tk.StringVar(value=self.manager_notes_service.get_note(manager))
            entry = ttk.Entry(manager_frame, textvariable=note_var, width=50)
            entry.pack(side="left", fill="x", expand=True)
            self.note_entries[manager] = note_var
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Button frame
        button_frame = tk.Frame(dialog, bg=DARK_THEME['bg_primary'])
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Save button
        save_btn = ttk.Button(
            button_frame,
            text="Save",
            command=lambda: self.save_manager_notes(dialog)
        )
        save_btn.pack(side="right", padx=(5, 0))
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_btn.pack(side="right")
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def save_manager_notes(self, dialog):
        """Save all manager notes"""
        for manager, note_var in self.note_entries.items():
            self.manager_notes_service.set_note(manager, note_var.get())
        dialog.destroy()