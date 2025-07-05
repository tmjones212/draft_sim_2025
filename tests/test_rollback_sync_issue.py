import unittest
import tkinter as tk
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.player_list import PlayerList
from src.models import Player
from src.core.draft_logic import DraftEngine


class TestRollbackSyncIssue(unittest.TestCase):
    """Specific test for the issue where drafted players show as available after rollback"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Create specific players that were showing incorrectly
        self.jamarr_chase = Player(
            player_id="chase_001",
            name="Ja'Marr Chase", 
            position="WR",
            team="CIN",
            rank=3,
            adp=3.0
        )
        
        self.bijan_robinson = Player(
            player_id="robinson_001",
            name="Bijan Robinson",
            position="RB", 
            team="ATL",
            rank=2,
            adp=2.0
        )
        
        # Create more players to fill out the draft
        self.all_players = [self.jamarr_chase, self.bijan_robinson]
        
        for i in range(3, 200):
            player = Player(
                player_id=f"player_{i}",
                name=f"Player {i}",
                position=['QB', 'RB', 'WR', 'TE'][i % 4],
                team=f"TM{i % 32}",
                rank=i,
                adp=float(i)
            )
            self.all_players.append(player)
            
        self.available_players = list(self.all_players)
        self.player_list = PlayerList(self.root)
        
    def tearDown(self):
        self.root.destroy()
        
    def test_early_picks_dont_reappear_in_round_7(self):
        """Test that early round picks don't show as available in later rounds"""
        # Initial update
        self.player_list.update_players(self.available_players)
        
        # Simulate first two picks (Chase and Bijan)
        early_picks = [self.jamarr_chase, self.bijan_robinson]
        for player in early_picks:
            self.available_players.remove(player)
            self.player_list.remove_players([player])
            
        # Verify they're gone
        self.assertNotIn(self.jamarr_chase, self.player_list.players)
        self.assertNotIn(self.bijan_robinson, self.player_list.players)
        
        # Make more picks to get to round 7 (pick ~75)
        picks_made = list(early_picks)
        for i in range(73):  # 75 total picks
            if self.available_players:
                player = self.available_players.pop(0)
                picks_made.append(player)
                self.player_list.remove_players([player])
        
        # We're now in round 7
        # Verify early picks are still not showing
        self.assertNotIn(self.jamarr_chase, self.player_list.players)
        self.assertNotIn(self.bijan_robinson, self.player_list.players)
        
        # Check displayed rows
        for row in self.player_list.row_frames:
            if hasattr(row, 'player'):
                self.assertNotEqual(row.player.name, "Ja'Marr Chase")
                self.assertNotEqual(row.player.name, "Bijan Robinson")
                
        # Now rollback to pick 50
        # Add back picks 50-75
        rollback_players = picks_made[49:]  # Last 25 picks
        picks_made = picks_made[:49]
        
        for player in rollback_players:
            if player not in early_picks:  # Don't add back Chase/Bijan
                self.available_players.append(player)
                
        self.available_players.sort(key=lambda p: p.rank)
        self.player_list.update_players(self.available_players, force_refresh=True)
        
        # Verify Chase and Bijan are STILL not available
        self.assertNotIn(self.jamarr_chase, self.player_list.players)
        self.assertNotIn(self.bijan_robinson, self.player_list.players)
        
        # Verify in displayed rows too
        for row in self.player_list.row_frames:
            if hasattr(row, 'player'):
                self.assertNotEqual(row.player.name, "Ja'Marr Chase")
                self.assertNotEqual(row.player.name, "Bijan Robinson")
                
    def test_multiple_rollback_cycles(self):
        """Test multiple cycles of picks and rollbacks"""
        self.player_list.update_players(self.available_players)
        
        # Track what should be drafted
        permanently_drafted = []
        
        # First cycle - draft top 10
        for i in range(10):
            player = self.available_players.pop(0)
            permanently_drafted.append(player)
            self.player_list.remove_players([player])
            
        # Verify top players are gone
        self.assertNotIn(self.jamarr_chase, self.player_list.players)
        self.assertNotIn(self.bijan_robinson, self.player_list.players)
        
        # Make 20 more picks
        temp_picks = []
        for i in range(20):
            player = self.available_players.pop(0)
            temp_picks.append(player)
            self.player_list.remove_players([player])
            
        # Rollback the 20 picks
        for player in temp_picks:
            self.available_players.append(player)
        self.available_players.sort(key=lambda p: p.rank)
        self.player_list.update_players(self.available_players, force_refresh=True)
        
        # Verify permanently drafted are still gone
        for player in permanently_drafted:
            self.assertNotIn(player, self.player_list.players)
            
        # Make 30 more picks
        more_picks = []
        for i in range(30):
            if self.available_players:
                player = self.available_players.pop(0)
                more_picks.append(player)
                self.player_list.remove_players([player])
                
        # Rollback 15 of them
        for i in range(15):
            player = more_picks.pop()
            self.available_players.append(player)
            
        self.available_players.sort(key=lambda p: p.rank)
        self.player_list.update_players(self.available_players, force_refresh=True)
        
        # Final verification - original top picks should never reappear
        self.assertNotIn(self.jamarr_chase, self.player_list.players)
        self.assertNotIn(self.bijan_robinson, self.player_list.players)
        
        # Check all rows
        for row in self.player_list.row_frames:
            if hasattr(row, 'player'):
                self.assertNotIn(row.player, permanently_drafted)


if __name__ == '__main__':
    unittest.main(verbosity=2)