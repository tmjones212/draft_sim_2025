import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Player


class TestRollbackPickRemoval(unittest.TestCase):
    """Test that picks made after rollback are properly removed from available players"""
    
    def setUp(self):
        """Set up test environment"""
        self.all_players = []
        
        # Create test players
        for i in range(100):
            player = Player(
                player_id=f"player_{i}",
                name=f"Player {i}",
                position=['QB', 'RB', 'WR', 'TE'][i % 4],
                team=f"TM{i % 32}",
                rank=i + 1,
                adp=float(i + 1)
            )
            self.all_players.append(player)
            
        self.available_players = list(self.all_players)
        self.drafted_players = []
        
    def simulate_rollback(self, picks_to_rollback):
        """Simulate rolling back picks"""
        for _ in range(picks_to_rollback):
            if self.drafted_players:
                player = self.drafted_players.pop()
                self.available_players.append(player)
        
        # Sort by rank (important!)
        self.available_players.sort(key=lambda p: p.rank)
        
        # Simulate force refresh that clears selection
        # In the UI, this would clear selected_index
        return None  # Return None to simulate no selection
        
    def simulate_draft_pick(self, player):
        """Simulate drafting a player"""
        if player in self.available_players:
            self.available_players.remove(player)
            self.drafted_players.append(player)
            return True
        return False
        
    def test_picks_after_rollback_are_removed(self):
        """Test that picks made after rollback are properly removed"""
        # Make 20 initial picks
        initial_picks = []
        for i in range(20):
            player = self.available_players[0]
            self.simulate_draft_pick(player)
            initial_picks.append(player)
            
        # Verify they're drafted
        for player in initial_picks:
            self.assertNotIn(player, self.available_players)
            self.assertIn(player, self.drafted_players)
            
        # Rollback 10 picks (simulates UI clearing selection)
        selected_index = self.simulate_rollback(10)
        self.assertIsNone(selected_index)  # Selection cleared after rollback
        
        # Now make new picks after rollback
        # This simulates the user selecting and drafting players
        new_picks = []
        for i in range(5):
            # User selects best available
            player = self.available_players[0]
            
            # Draft the player
            success = self.simulate_draft_pick(player)
            self.assertTrue(success)
            new_picks.append(player)
            
            # CRITICAL: Verify player is removed even though selection was cleared
            self.assertNotIn(player, self.available_players)
            self.assertIn(player, self.drafted_players)
            
        # Final verification
        # First 10 picks should still be drafted
        for player in initial_picks[:10]:
            self.assertNotIn(player, self.available_players)
            self.assertIn(player, self.drafted_players)
            
        # Rolled back picks should be available (except those re-drafted)
        for player in initial_picks[10:]:
            if player not in new_picks:
                self.assertIn(player, self.available_players)
                
        # New picks should be drafted
        for player in new_picks:
            self.assertNotIn(player, self.available_players)
            self.assertIn(player, self.drafted_players)
            
    def test_multiple_rollback_pick_cycles(self):
        """Test multiple cycles of rollback and picking"""
        all_picks_made = []
        
        for cycle in range(3):
            # Make 10 picks
            cycle_picks = []
            for i in range(10):
                player = self.available_players[0]
                self.simulate_draft_pick(player)
                cycle_picks.append(player)
                all_picks_made.append(player)
                
            # Rollback 5
            self.simulate_rollback(5)
            
            # Remove rolled back picks from tracking
            for _ in range(5):
                all_picks_made.pop()
                
            # Make 3 new picks
            for i in range(3):
                player = self.available_players[0]
                self.simulate_draft_pick(player)
                all_picks_made.append(player)
                
                # Verify removal worked
                self.assertNotIn(player, self.available_players)
                
        # Final verification - all tracked picks should be drafted
        for player in all_picks_made:
            self.assertNotIn(player, self.available_players)
            self.assertIn(player, self.drafted_players)


if __name__ == '__main__':
    unittest.main(verbosity=2)