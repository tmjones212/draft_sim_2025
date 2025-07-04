#!/usr/bin/env python3
"""Generate CSV file with ADP data and formatted player names"""

import csv
import json
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.player_extensions import format_name

def get_nickname(name):
    """Get special nickname for player if available"""
    special_names = {
        "Amon-Ra St. Brown": "SUN GOD",
        "Brian Thomas Jr.": "BTJ",
        "Brian Thomas": "BTJ",
        "Justin Jefferson": "JJ", 
        "Christian McCaffrey": "CMC",
        "Jonathan Taylor": "JT",
        "Jayden Daniels": "JD",
        "Bijan Robinson": "BIJAN"
    }
    
    # Check exact match
    if name in special_names:
        return special_names[name]
    
    # Check partial matches
    name_lower = name.lower()
    if "bijan" in name_lower and "robinson" in name_lower:
        return "BIJAN"
    elif "amon" in name_lower and "ra" in name_lower:
        return "SUN GOD"
    elif "brian" in name_lower and "thomas" in name_lower:
        return "BTJ"
    elif "justin" in name_lower and "jefferson" in name_lower:
        return "JJ"
    elif "christian" in name_lower and "mccaffrey" in name_lower:
        return "CMC"
    elif "jonathan" in name_lower and "taylor" in name_lower:
        return "JT"
    elif "jayden" in name_lower and "daniels" in name_lower:
        return "JD"
    
    return None

def main():
    # Import the fetcher
    from src.utils.player_data_fetcher import fetch_adp_data, parse_player_data
    
    print("Fetching fresh ADP data from nfc.shgn.com...")
    
    # Fetch ADP data
    raw_data = fetch_adp_data()
    if not raw_data:
        print("Failed to fetch ADP data, falling back to local file")
        # Load player data from players_2025.json
        with open('src/data/players_2025.json', 'r') as f:
            data = json.load(f)
        players = data['players']
    else:
        # Parse the fetched data
        players = parse_player_data(raw_data)
        if not players:
            print("Failed to parse ADP data, falling back to local file")
            with open('src/data/players_2025.json', 'r') as f:
                data = json.load(f)
            players = data['players']
        else:
            print(f"Successfully fetched {len(players)} players with real ADPs")
    
    # Create player list with formatted names
    players_with_formatted = []
    
    for player in players:
        # Format the name
        formatted_name = format_name(player['name'])
        
        # Get nickname if available
        nickname = get_nickname(player['name'])
        
        # Create player entry
        player_entry = {
            'rank': player['rank'],
            'name': player['name'],
            'formatted_name': formatted_name,
            'nickname': nickname if nickname else '',
            'position': player['position'],
            'team': player.get('team', 'FA'),
            'adp': player['adp']
        }
        
        players_with_formatted.append(player_entry)
    
    # Write to CSV
    output_file = 'adp_data_formatted.csv'
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['rank', 'name', 'formatted_name', 'nickname', 'position', 'team', 'adp']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Write player data
        for player in players_with_formatted:
            writer.writerow(player)
    
    print(f"CSV file generated: {output_file}")
    print(f"Total players: {len(players_with_formatted)}")
    
    # Show first 25 players as preview
    print("\nPreview of top 25 players:")
    print(f"{'Rank':>4} | {'Formatted Name':<25} | {'Nickname':<10} | {'Pos':<4} | {'Team':<4} | {'ADP':>5}")
    print("-" * 80)
    for player in players_with_formatted[:25]:
        print(f"{player['rank']:4d} | {player['formatted_name']:<25} | {player['nickname']:<10} | {player['position']:<4} | {player['team']:<4} | {player['adp']:5.1f}")

if __name__ == "__main__":
    main()