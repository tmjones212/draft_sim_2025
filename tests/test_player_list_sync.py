import unittest
import sys
import os
from unittest.mock import Mock, patch

# Try to import tkinter, skip tests if not available
try:
    import tkinter as tk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.player_list import PlayerList
from src.models import Player
from src.core.draft_logic import DraftEngine
import config


class TestPlayerListSync(unittest.TestCase):
    """Test that player list stays synchronized during drafts and rollbacks"""
    
    def setUp(self):
        """Set up test environment"""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide window during tests
        
        # Create mock players with unique IDs
        self.all_players = []
        positions = ['QB', 'RB', 'WR', 'TE']
        for i in range(200):
            player = Player(
                player_id=f"player_{i}",
                name=f"Player {i}",
                position=positions[i % 4],
                team=f"TM{i % 32}",
                rank=i + 1,
                adp=i + 1.0
            )
            self.all_players.append(player)
        
        # Create player list widget
        self.player_list = PlayerList(self.root)
        self.available_players = list(self.all_players)
        self.drafted_players = []
        
        # Create draft engine
        self.draft_engine = DraftEngine(
            num_teams=config.num_teams,
            roster_spots=config.roster_spots,
            draft_type=config.draft_type,
            reversal_round=config.reversal_round
        )
        
    def tearDown(self):
        """Clean up after tests"""
        self.root.destroy()
        
    def test_basic_draft_sync(self):
        """Test that drafting a player removes them from available list"""
        # Update player list
        self.player_list.update_players(self.available_players)
        
        # Draft first player
        player_to_draft = self.available_players[0]
        self.available_players.remove(player_to_draft)
        self.drafted_players.append(player_to_draft)
        
        # Remove from player list
        self.player_list.remove_players([player_to_draft])
        
        # Verify player is not in the list
        self.assertNotIn(player_to_draft, self.player_list.players)
        self.assertEqual(len(self.player_list.players), 199)
        
        # Verify displayed rows don't contain the drafted player
        for row in self.player_list.row_frames:
            if hasattr(row, 'player'):
                self.assertNotEqual(row.player.player_id, player_to_draft.player_id)
                
    def test_multiple_picks_and_rollback(self):
        """Test multiple picks followed by rollback"""
        self.player_list.update_players(self.available_players)
        
        # Make 10 picks
        picks_made = []
        for i in range(10):
            player = self.available_players.pop(0)
            picks_made.append(player)
            self.drafted_players.append(player)
            self.player_list.remove_players([player])
        
        # Verify all picked players are removed
        for player in picks_made:
            self.assertNotIn(player, self.player_list.players)
        
        # Rollback 5 picks
        for i in range(5):
            player = picks_made.pop()
            self.drafted_players.remove(player)
            self.available_players.insert(0, player)  # Add back to top
            
        # Update player list with force refresh
        self.available_players.sort(key=lambda p: p.rank)
        self.player_list.update_players(self.available_players, force_refresh=True)
        
        # Verify rolled back players are available again
        for i in range(5):
            player = self.all_players[9-i]  # Players 9,8,7,6,5 should be available
            self.assertIn(player, self.player_list.players)
            
        # Verify still-drafted players are not available
        for i in range(5):
            player = self.all_players[i]  # Players 0-4 should still be drafted
            self.assertNotIn(player, self.player_list.players)
            
    def test_rapid_pick_rollback_cycles(self):
        """Test rapid cycles of picks and rollbacks"""
        self.player_list.update_players(self.available_players)
        
        # Do 5 cycles of pick/rollback
        for cycle in range(5):
            # Pick 20 players
            cycle_picks = []
            for i in range(20):
                if self.available_players:
                    player = self.available_players.pop(0)
                    cycle_picks.append(player)
                    self.drafted_players.append(player)
            
            # Remove all at once
            self.player_list.remove_players(cycle_picks)
            
            # Verify they're gone
            for player in cycle_picks:
                self.assertNotIn(player, self.player_list.players)
            
            # Rollback 10 of them
            rollback_players = []
            for i in range(10):
                if cycle_picks:
                    player = cycle_picks.pop()
                    self.drafted_players.remove(player)
                    rollback_players.append(player)
                    self.available_players.append(player)
            
            # Sort and update with force refresh
            self.available_players.sort(key=lambda p: p.rank)
            self.player_list.update_players(self.available_players, force_refresh=True)
            
            # Verify rollback worked
            for player in rollback_players:
                self.assertIn(player, self.player_list.players)
            
            # Verify still-drafted players remain drafted
            for player in cycle_picks:
                self.assertNotIn(player, self.player_list.players)
                
    def test_displayed_rows_match_data(self):
        """Test that displayed rows always match underlying data"""
        self.player_list.update_players(self.available_players)
        
        # Make some picks
        for i in range(15):
            player = self.available_players.pop(0)
            self.drafted_players.append(player)
            self.player_list.remove_players([player])
        
        # Check all displayed rows
        displayed_player_ids = set()
        for row in self.player_list.row_frames:
            if hasattr(row, 'player') and row.player:
                displayed_player_ids.add(row.player.player_id)
                # Verify this player is in the available list
                self.assertIn(row.player, self.player_list.players)
        
        # Verify no drafted players are displayed
        for player in self.drafted_players:
            self.assertNotIn(player.player_id, displayed_player_ids)
            
    def test_search_filter_with_rollback(self):
        """Test that search works correctly after rollbacks"""
        self.player_list.update_players(self.available_players)
        
        # Draft some RBs
        drafted_rbs = []
        for player in list(self.available_players):
            if player.position == 'RB' and len(drafted_rbs) < 5:
                self.available_players.remove(player)
                drafted_rbs.append(player)
                self.drafted_players.append(player)
        
        self.player_list.remove_players(drafted_rbs)
        
        # Filter by RB position
        self.player_list.filter_by_position('RB')
        
        # Verify no drafted RBs are shown
        for row in self.player_list.row_frames:
            if hasattr(row, 'player'):
                self.assertNotIn(row.player, drafted_rbs)
                
        # Rollback the RBs
        for player in drafted_rbs:
            self.available_players.append(player)
            self.drafted_players.remove(player)
            
        self.available_players.sort(key=lambda p: p.rank)
        self.player_list.update_players(self.available_players, force_refresh=True)
        self.player_list.filter_by_position('RB')
        
        # Verify rolled back RBs are now visible
        visible_rbs = []
        for row in self.player_list.row_frames:
            if hasattr(row, 'player') and row.player.position == 'RB':
                visible_rbs.append(row.player)
                
        for player in drafted_rbs:
            self.assertIn(player, self.player_list.players)
            
    def test_boundary_conditions(self):
        """Test edge cases like drafting all players"""
        self.player_list.update_players(self.available_players)
        
        # Draft almost all players
        while len(self.available_players) > 5:
            player = self.available_players.pop(0)
            self.drafted_players.append(player)
            
        self.player_list.update_players(self.available_players, force_refresh=True)
        
        # Verify only 5 players shown
        self.assertEqual(len(self.player_list.players), 5)
        self.assertLessEqual(len(self.player_list.row_frames), 5)
        
        # Rollback all picks
        self.available_players = list(self.all_players)
        self.drafted_players = []
        self.player_list.update_players(self.available_players, force_refresh=True)
        
        # Verify all players are back
        self.assertEqual(len(self.player_list.players), 200)
        

class TestPlayerListPerformance(unittest.TestCase):
    """Test performance of player list operations"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.player_list = PlayerList(self.root)
        
        # Create large player pool
        self.players = []
        for i in range(500):
            player = Player(
                player_id=f"perf_player_{i}",
                name=f"Performance Player {i}",
                position=['QB', 'RB', 'WR', 'TE'][i % 4],
                team=f"TM{i % 32}",
                rank=i + 1,
                adp=i + 1.0
            )
            self.players.append(player)
            
    def tearDown(self):
        self.root.destroy()
        
    def test_single_removal_performance(self):
        """Test that single player removal is fast"""
        import time
        
        self.player_list.update_players(self.players)
        
        # Time single removal
        player_to_remove = self.players[15]  # Remove from middle of displayed list
        
        start_time = time.time()
        self.player_list.remove_players([player_to_remove])
        end_time = time.time()
        
        removal_time = end_time - start_time
        
        # Should be very fast (under 50ms)
        self.assertLess(removal_time, 0.05, f"Single removal took {removal_time:.3f}s, should be under 0.05s")
        
        # Verify player was removed
        self.assertNotIn(player_to_remove, self.player_list.players)
        

if __name__ == '__main__':
    unittest.main()