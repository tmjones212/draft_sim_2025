#!/usr/bin/env python3
"""Minimal test UI to verify player stats popup"""

import tkinter as tk
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.player_generator import generate_mock_players
from src.ui.player_stats_popup import PlayerStatsPopup
from src.ui.theme import DARK_THEME

def main():
    # Create main window
    root = tk.Tk()
    root.title("Test Player Stats Popup")
    root.geometry("400x300")
    root.configure(bg=DARK_THEME['bg_primary'])
    
    # Generate players
    print("Generating players...")
    players = generate_mock_players()
    
    # Find players with stats
    players_with_stats = []
    for player in players[:20]:
        if hasattr(player, 'weekly_stats_2024') and player.weekly_stats_2024:
            players_with_stats.append(player)
    
    print(f"Found {len(players_with_stats)} players with stats")
    
    # Create buttons for each player
    label = tk.Label(
        root,
        text="Click a player to see their 2024 stats:",
        bg=DARK_THEME['bg_primary'],
        fg=DARK_THEME['text_primary'],
        font=('Arial', 12, 'bold')
    )
    label.pack(pady=10)
    
    frame = tk.Frame(root, bg=DARK_THEME['bg_primary'])
    frame.pack(fill='both', expand=True, padx=20, pady=10)
    
    for i, player in enumerate(players_with_stats[:5]):
        btn = tk.Button(
            frame,
            text=f"{player.name} ({player.position})",
            bg=DARK_THEME['button_bg'],
            fg='white',
            font=('Arial', 10),
            command=lambda p=player: show_stats(root, p),
            cursor='hand2'
        )
        btn.pack(fill='x', pady=5)
        
        # Debug info
        weeks = len(player.weekly_stats_2024)
        info = tk.Label(
            frame,
            text=f"  → {weeks} weeks of data",
            bg=DARK_THEME['bg_primary'],
            fg=DARK_THEME['text_secondary'],
            font=('Arial', 9)
        )
        info.pack()
    
    # Run
    root.mainloop()

def show_stats(parent, player):
    print(f"\nShowing stats for {player.name}")
    print(f"Has weekly_stats_2024: {hasattr(player, 'weekly_stats_2024')}")
    print(f"Weekly stats count: {len(player.weekly_stats_2024) if hasattr(player, 'weekly_stats_2024') else 0}")
    if hasattr(player, 'weekly_stats_2024') and player.weekly_stats_2024:
        print(f"First week: {player.weekly_stats_2024[0]}")
    PlayerStatsPopup(parent, player)

if __name__ == "__main__":
    main()