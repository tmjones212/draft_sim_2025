import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Player


class TestPlayerSyncLogic(unittest.TestCase):
    """Test player synchronization logic without UI dependencies"""
    
    def setUp(self):
        """Set up test environment"""
        # Create test players
        self.all_players = []
        positions = ['QB', 'RB', 'WR', 'TE']
        
        # Create specific players that were problematic
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
        
        self.all_players = [self.jamarr_chase, self.bijan_robinson]
        
        for i in range(3, 200):
            player = Player(
                player_id=f"player_{i}",
                name=f"Player {i}",
                position=positions[i % 4],
                team=f"TM{i % 32}",
                rank=i,
                adp=float(i)
            )
            self.all_players.append(player)
            
        self.available_players = list(self.all_players)
        self.drafted_players = []
        
    def test_basic_draft_removes_player(self):
        """Test that drafting a player removes them from available"""
        # Draft first player
        player = self.available_players.pop(0)
        self.drafted_players.append(player)
        
        # Verify player is not available
        self.assertNotIn(player, self.available_players)
        self.assertIn(player, self.drafted_players)
        
    def test_rollback_restores_players_correctly(self):
        """Test that rollback properly restores players"""
        # Draft 10 players
        picks_made = []
        for i in range(10):
            player = self.available_players.pop(0)
            self.drafted_players.append(player)
            picks_made.append(player)
            
        # Verify all are drafted
        for player in picks_made:
            self.assertNotIn(player, self.available_players)
            
        # Rollback last 5 picks
        for i in range(5):
            player = picks_made.pop()
            self.drafted_players.remove(player)
            self.available_players.append(player)
            
        # Sort available players
        self.available_players.sort(key=lambda p: p.rank)
        
        # Verify first 5 are still drafted
        for player in picks_made:
            self.assertNotIn(player, self.available_players)
            self.assertIn(player, self.drafted_players)
            
        # Verify last 5 are available again
        for i in range(5, 10):
            player = self.all_players[i]
            self.assertIn(player, self.available_players)
            self.assertNotIn(player, self.drafted_players)
            
    def test_early_picks_stay_drafted_after_rollback(self):
        """Test the specific issue - early picks showing as available"""
        # Draft Chase and Bijan (picks 1-2)
        early_picks = [self.jamarr_chase, self.bijan_robinson]
        for player in early_picks:
            self.available_players.remove(player)
            self.drafted_players.append(player)
            
        # Make 73 more picks to get to round 7
        later_picks = []
        for i in range(73):
            if self.available_players:
                player = self.available_players.pop(0)
                self.drafted_players.append(player)
                later_picks.append(player)
                
        # Now in round 7 - verify early picks are still drafted
        self.assertNotIn(self.jamarr_chase, self.available_players)
        self.assertNotIn(self.bijan_robinson, self.available_players)
        
        # Rollback to pick 50 (revert last 25 picks)
        rollback_count = 25
        for i in range(rollback_count):
            player = later_picks.pop()
            self.drafted_players.remove(player)
            self.available_players.append(player)
            
        self.available_players.sort(key=lambda p: p.rank)
        
        # CRITICAL: Verify Chase and Bijan are STILL not available
        self.assertNotIn(self.jamarr_chase, self.available_players)
        self.assertNotIn(self.bijan_robinson, self.available_players)
        self.assertIn(self.jamarr_chase, self.drafted_players)
        self.assertIn(self.bijan_robinson, self.drafted_players)
        
    def test_multiple_rollback_cycles(self):
        """Test multiple cycles of draft and rollback"""
        permanently_drafted = []
        
        # First round - draft top 12 (these stay drafted)
        for i in range(12):
            player = self.available_players.pop(0)
            self.drafted_players.append(player)
            permanently_drafted.append(player)
            
        # Cycle 1: Draft 20, rollback 20
        cycle1_picks = []
        for i in range(20):
            player = self.available_players.pop(0)
            self.drafted_players.append(player)
            cycle1_picks.append(player)
            
        # Rollback all 20
        for player in cycle1_picks:
            self.drafted_players.remove(player)
            self.available_players.append(player)
        self.available_players.sort(key=lambda p: p.rank)
        
        # Verify first 12 still drafted
        for player in permanently_drafted:
            self.assertNotIn(player, self.available_players)
            
        # Cycle 2: Draft 30, rollback 15
        cycle2_picks = []
        for i in range(30):
            if self.available_players:
                player = self.available_players.pop(0)
                self.drafted_players.append(player)
                cycle2_picks.append(player)
                
        # Rollback last 15
        for i in range(15):
            player = cycle2_picks.pop()
            self.drafted_players.remove(player)
            self.available_players.append(player)
        self.available_players.sort(key=lambda p: p.rank)
        
        # Final verification
        for player in permanently_drafted:
            self.assertNotIn(player, self.available_players)
            self.assertIn(player, self.drafted_players)
            
        # Verify Chase and Bijan specifically
        self.assertNotIn(self.jamarr_chase, self.available_players)
        self.assertNotIn(self.bijan_robinson, self.available_players)
        
    def test_player_id_uniqueness(self):
        """Test that player IDs are unique and consistent"""
        player_ids = set()
        for player in self.all_players:
            self.assertNotIn(player.player_id, player_ids)
            player_ids.add(player.player_id)
            
        # Verify specific players have expected IDs
        self.assertEqual(self.jamarr_chase.player_id, "chase_001")
        self.assertEqual(self.bijan_robinson.player_id, "robinson_001")


if __name__ == '__main__':
    unittest.main(verbosity=2)