"""Tests for draft reversion functionality"""
import unittest
from unittest.mock import Mock, patch
from src.models.player import Player
from src.models.team import Team
from src.core.draft_logic import DraftPick
from src.core.draft_engine import DraftEngine
import tkinter as tk


class TestDraftReversion(unittest.TestCase):
    """Test cases for draft reversion and player availability"""
    
    def setUp(self):
        """Set up test data"""
        # Create mock players
        self.player1 = Player(
            player_id="1",
            name="Saquon Barkley", 
            position="RB",
            team="PHI",
            rank=5,
            adp=5.0,
            projection=250.0
        )
        self.player2 = Player(
            player_id="2",
            name="Jahmyr Gibbs",
            position="RB", 
            team="DET",
            rank=6,
            adp=6.0,
            projection=240.0
        )
        self.player3 = Player(
            player_id="3",
            name="Malik Nabers",
            position="WR",
            team="NYG", 
            rank=7,
            adp=7.0,
            projection=230.0
        )
        
        # Create teams
        self.teams = {}
        for i in range(1, 13):
            self.teams[i] = Team(
                id=i,
                name=f"Team {i}",
                draft_position=i
            )
            
    @patch('tkinter.Tk')
    def test_revert_draft_restores_players(self, mock_tk):
        """Test that reverting draft properly restores players to available list"""
        from main import DraftApp
        
        # Create a minimal mock root window
        mock_root = Mock()
        mock_tk.return_value = mock_root
        
        # Mock the necessary tkinter widgets
        with patch('main.tk.Frame'), \
             patch('main.tk.Label'), \
             patch('main.tk.Button'), \
             patch('main.ttk.Button'), \
             patch('main.tk.StringVar'), \
             patch('main.tk.Toplevel'), \
             patch('main.messagebox'):
            
            # Create app instance with mocked components
            app = DraftApp(mock_root)
            app.teams = self.teams
            app.user_team_id = 1
            app.manual_mode = False
            
            # Set up initial available players
            app.available_players = [self.player1, self.player2, self.player3]
            
            # Mock draft engine with some picks
            app.draft_engine = Mock(spec=DraftEngine)
            app.draft_engine.draft_results = [
                DraftPick(1, 1, self.player1),
                DraftPick(2, 2, self.player2),
                DraftPick(3, 3, self.player3)
            ]
            app.draft_engine.get_current_pick_info.return_value = (4, 1, 4, 4)
            app.draft_engine.is_draft_complete.return_value = False
            
            # Mock the UI components
            app.draft_board = Mock()
            app.player_list = Mock()
            app.roster_view = Mock()
            app.roster_view.get_watch_list.return_value = None
            app.undo_button = Mock()
            
            # Clear available players to simulate picks being made
            app.available_players = []
            
            # Test reverting to pick 1 (should restore all 3 players)
            app._revert_to_pick(1)
            
            # Check that all 3 players are back in available list
            available_ids = {p.player_id for p in app.available_players}
            self.assertIn("1", available_ids, "Player 1 should be restored")
            self.assertIn("2", available_ids, "Player 2 should be restored")
            self.assertIn("3", available_ids, "Player 3 should be restored")
            self.assertEqual(len(app.available_players), 3)
            
    @patch('tkinter.Tk')
    def test_revert_draft_no_duplicate_players(self, mock_tk):
        """Test that reverting draft doesn't create duplicate players"""
        from main import DraftApp
        
        mock_root = Mock()
        mock_tk.return_value = mock_root
        
        with patch('main.tk.Frame'), \
             patch('main.tk.Label'), \
             patch('main.tk.Button'), \
             patch('main.ttk.Button'), \
             patch('main.tk.StringVar'), \
             patch('main.tk.Toplevel'), \
             patch('main.messagebox'):
            
            app = DraftApp(mock_root)
            app.teams = self.teams
            app.user_team_id = 1
            app.manual_mode = False
            
            # Start with player3 still available
            app.available_players = [self.player3]
            
            # Mock draft with first 2 picks made
            app.draft_engine = Mock(spec=DraftEngine)
            app.draft_engine.draft_results = [
                DraftPick(1, 1, self.player1),
                DraftPick(2, 2, self.player2),
                DraftPick(3, 3, self.player3)
            ]
            app.draft_engine.get_current_pick_info.return_value = (4, 1, 4, 4)
            app.draft_engine.is_draft_complete.return_value = False
            
            # Mock UI components
            app.draft_board = Mock()
            app.player_list = Mock()
            app.roster_view = Mock()
            app.roster_view.get_watch_list.return_value = None
            app.undo_button = Mock()
            
            # Revert to pick 2 (should restore player2 and player3 but not duplicate player3)
            app._revert_to_pick(2)
            
            # Count occurrences of each player
            player3_count = sum(1 for p in app.available_players if p.player_id == "3")
            self.assertEqual(player3_count, 1, "Player 3 should not be duplicated")
            
            # Check total count
            self.assertEqual(len(app.available_players), 2, "Should have exactly 2 players")
            
    @patch('tkinter.Tk') 
    def test_auto_draft_after_revert_handles_missing_players(self, mock_tk):
        """Test that auto-draft after revert handles players that may not be in available list"""
        from main import DraftApp
        
        mock_root = Mock()
        mock_tk.return_value = mock_root
        
        with patch('main.tk.Frame'), \
             patch('main.tk.Label'), \
             patch('main.tk.Button'), \
             patch('main.ttk.Button'), \
             patch('main.tk.StringVar'), \
             patch('main.tk.Toplevel'), \
             patch('main.messagebox'):
            
            app = DraftApp(mock_root)
            app.teams = self.teams
            app.user_team_id = 5  # User is pick 5
            app.manual_mode = False
            
            # Set available players
            app.available_players = [self.player1, self.player2]
            
            # Mock draft engine
            app.draft_engine = Mock(spec=DraftEngine)
            app.draft_engine.draft_results = []
            app.draft_engine.is_draft_complete.return_value = False
            app.draft_engine.get_current_pick_info.side_effect = [
                (1, 1, 1, 1),  # First call
                (2, 1, 2, 2),  # Second call
                (3, 1, 3, 3),  # Third call
                (4, 1, 4, 4),  # Fourth call
                (5, 1, 5, 5),  # Fifth call - user's turn
            ]
            
            # Mock UI components
            app.draft_board = Mock()
            app.player_list = Mock()
            app.roster_view = Mock()
            app.roster_view.get_watch_list.return_value = None
            app._position_counts_cache = {}
            
            # Mock the computer pick selection
            app._select_computer_pick = Mock()
            app._select_computer_pick.side_effect = [self.player1, self.player2, None, None]
            
            # Run auto draft
            app._fast_auto_draft_to_user()
            
            # Should complete without errors even when players aren't found
            self.assertEqual(len(app.available_players), 0, "All available players should be drafted")


if __name__ == '__main__':
    unittest.main()