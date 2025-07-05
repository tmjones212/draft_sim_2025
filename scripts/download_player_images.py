#!/usr/bin/env python3
import os
import sys
import json
import requests
from time import sleep
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.player_extensions import format_name

def load_active_players():
    """Load player IDs for active fantasy-relevant players"""
    # Load the ADP data to get active player names
    adp_players = set()
    adp_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "adp_data_formatted.csv")
    
    if os.path.exists(adp_file):
        with open(adp_file, 'r') as f:
            next(f)  # Skip header
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    formatted_name = parts[2]  # formatted_name column
                    adp_players.add(formatted_name)
    
    print(f"Found {len(adp_players)} players in ADP data")
    
    # Load Sleeper player database
    players_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "players.json")
    with open(players_file, 'r') as f:
        sleeper_data = json.load(f)
    
    # Match ADP players to Sleeper IDs
    matched_players = []
    
    for player_id, player_data in sleeper_data.items():
        if player_data.get('active') and player_data.get('position') in ['QB', 'RB', 'WR', 'TE']:
            # Format the player's name
            full_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
            formatted = format_name(full_name)
            
            # Check if this player is in our ADP data
            if formatted in adp_players:
                matched_players.append({
                    'player_id': player_id,
                    'name': full_name,
                    'formatted_name': formatted,
                    'position': player_data.get('position'),
                    'team': player_data.get('team')
                })
    
    print(f"Matched {len(matched_players)} players with Sleeper IDs")
    return matched_players

def download_player_images(players, limit=None):
    """Download player images from Sleeper CDN"""
    # Create assets directory if it doesn't exist
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "player_images")
    os.makedirs(assets_dir, exist_ok=True)
    
    print(f"Downloading player images to {assets_dir}")
    print(f"Total players to download: {len(players) if not limit else min(limit, len(players))}")
    
    downloaded = 0
    skipped = 0
    failed = 0
    
    for i, player in enumerate(players):
        if limit and i >= limit:
            break
            
        player_id = player['player_id']
        filename = f"{player_id}.jpg"
        filepath = os.path.join(assets_dir, filename)
        
        # Skip if already downloaded
        if os.path.exists(filepath):
            skipped += 1
            if skipped % 50 == 0:
                print(f"  Skipped {skipped} existing images...")
            continue
        
        url = f"https://sleepercdn.com/content/nfl/players/{player_id}.jpg"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                downloaded += 1
                
                if downloaded % 10 == 0:
                    print(f"✓ Downloaded {downloaded} images... (latest: {player['name']})")
            else:
                failed += 1
                if response.status_code == 404:
                    # Create empty file to mark as checked
                    Path(filepath).touch()
                
            # Be nice to the server
            sleep(0.1)
            
        except Exception as e:
            failed += 1
            print(f"✗ Error downloading {player['name']} ({player_id}): {e}")
            # Create empty file to mark as checked
            Path(filepath).touch()
    
    print(f"\nDownload complete!")
    print(f"✓ Downloaded: {downloaded}")
    print(f"- Skipped (already exists): {skipped}")
    print(f"✗ Failed/No image: {failed}")
    print(f"Total processed: {downloaded + skipped + failed}")

def main():
    print("Fantasy Football Player Image Downloader")
    print("=" * 40)
    
    # Load active players
    players = load_active_players()
    
    if not players:
        print("No players found to download!")
        return
    
    # Check for command line arguments
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            download_player_images(players)
        else:
            try:
                limit = int(sys.argv[1])
                download_player_images(players, limit=limit)
            except ValueError:
                print(f"Invalid argument: {sys.argv[1]}")
                print("Usage: python download_player_images.py [--all | number]")
    else:
        # Interactive mode
        try:
            response = input(f"\nFound {len(players)} players. Download all? (y/n): ").strip().lower()
            if response != 'y':
                limit = int(input("How many to download? "))
                download_player_images(players, limit=limit)
            else:
                download_player_images(players)
        except KeyboardInterrupt:
            print("\n\nDownload cancelled by user.")
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()