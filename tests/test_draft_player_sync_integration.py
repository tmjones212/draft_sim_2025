import unittest
import tkinter as tk
from unittest.mock import Mock, MagicMock
import sys
import os
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.player_list import PlayerList
from src.models import Player, Team
from src.core.draft_logic import DraftEngine
from src.services.player_service import PlayerService
import config


class TestDraftPlayerSyncIntegration(unittest.TestCase):
    """Integration test for draft engine and player list synchronization"""
    
    def setUp(self):
        """Set up test environment with real draft engine"""
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Load real players
        self.player_service = PlayerService()
        self.all_players = self.player_service.load_players()
        self.available_players = list(self.all_players)
        
        # Create draft engine
        self.draft_engine = DraftEngine(
            num_teams=12,
            roster_spots=config.roster_spots,
            draft_type='snake',
            reversal_round=3
        )
        
        # Create teams
        self.teams = {}
        for i in range(1, 13):
            self.teams[i] = Team(i, f"Team {i}")
            
        # Create player list widget
        self.player_list = PlayerList(self.root)
        self.player_list.update_players(self.available_players)
        
    def tearDown(self):
        self.root.destroy()
        
    def _make_pick(self, player):
        """Simulate making a pick"""
        pick_num, _, _, team_id = self.draft_engine.get_current_pick_info()
        
        # Make the pick in draft engine
        self.draft_engine.make_pick(team_id, player, pick_num)
        
        # Add to team roster
        self.teams[team_id].add_player(player)
        
        # Remove from available
        if player in self.available_players:
            self.available_players.remove(player)
            
        # Update player list
        self.player_list.remove_players([player])
        
    def _revert_to_pick(self, target_pick):
        """Simulate reverting to a specific pick"""
        # Get picks to remove
        picks_to_remove = [p for p in self.draft_engine.draft_results if p.pick_number >= target_pick]
        
        # Reset draft results
        self.draft_engine.draft_results = [p for p in self.draft_engine.draft_results if p.pick_number < target_pick]
        
        # Reset team rosters
        for team in self.teams.values():
            team.roster = {pos: [] for pos in team.roster}
            
        # Re-add kept picks to rosters
        for pick in self.draft_engine.draft_results:
            self.teams[pick.team_id].add_player(pick.player)
            
        # Add removed players back to available
        players_to_restore = [pick.player for pick in picks_to_remove]
        for player in players_to_restore:
            if player not in self.available_players:
                self.available_players.append(player)
                
        # Sort by rank
        self.available_players.sort(key=lambda p: p.rank)
        
        # Force refresh player list
        self.player_list.update_players(self.available_players, force_refresh=True)
        
    def test_full_draft_simulation(self):
        """Simulate a full draft with picks and reverts"""
        picks_made = []
        
        # Make 50 picks
        for i in range(50):
            # Get best available player
            player = self.available_players[0]
            self._make_pick(player)
            picks_made.append((i + 1, player))
            
            # Verify player is not in available list
            self.assertNotIn(player, self.player_list.players)
            
            # Verify all displayed players are actually available
            for row in self.player_list.row_frames:
                if hasattr(row, 'player'):
                    self.assertIn(row.player, self.available_players)
                    self.assertNotIn(row.player, [p[1] for p in picks_made])
        
        # Revert to pick 25
        self._revert_to_pick(25)
        
        # Verify picks 25-50 are available again
        for pick_num, player in picks_made[24:]:  # picks 25-50
            self.assertIn(player, self.available_players)
            self.assertIn(player, self.player_list.players)
            
        # Verify picks 1-24 are still drafted
        for pick_num, player in picks_made[:24]:  # picks 1-24
            self.assertNotIn(player, self.available_players)
            self.assertNotIn(player, self.player_list.players)
            
        # Make 20 more picks
        new_picks = []
        for i in range(20):
            player = self.available_players[0]
            self._make_pick(player)
            new_picks.append(player)
            
        # Revert to pick 35
        self._revert_to_pick(35)
        
        # Verify latest picks are available
        for player in new_picks[10:]:  # Last 10 picks should be available
            self.assertIn(player, self.available_players)
            
    def test_random_pick_patterns(self):
        """Test random patterns of picks and reverts"""
        all_picks = []
        
        for round_num in range(5):
            # Make 5-15 random picks
            picks_this_round = random.randint(5, 15)
            round_picks = []
            
            for _ in range(picks_this_round):
                if self.available_players:
                    # Sometimes pick best available, sometimes random
                    if random.random() < 0.7:
                        player = self.available_players[0]
                    else:
                        player = random.choice(self.available_players[:10])
                    
                    self._make_pick(player)
                    pick_num = len(all_picks) + 1
                    all_picks.append((pick_num, player))
                    round_picks.append(player)
            
            # Verify all picks are removed
            for _, player in all_picks:
                self.assertNotIn(player, self.player_list.players)
                
            # Sometimes revert
            if random.random() < 0.5 and len(all_picks) > 10:
                revert_to = random.randint(max(1, len(all_picks) - 15), len(all_picks) - 5)
                self._revert_to_pick(revert_to)
                
                # Update all_picks to reflect reversion
                reverted_picks = [p for p in all_picks if p[0] >= revert_to]
                all_picks = [p for p in all_picks if p[0] < revert_to]
                
                # Verify reverted picks are available
                for _, player in reverted_picks:
                    self.assertIn(player, self.available_players)
                    
    def test_position_filtering_after_revert(self):
        """Test position filtering stays correct after reverting"""
        # Draft all QBs in first 3 rounds
        qbs_drafted = []
        picks_made = 0
        
        for player in list(self.available_players):
            if player.position == 'QB' and picks_made < 36:  # 3 rounds
                self._make_pick(player)
                qbs_drafted.append(player)
                picks_made += 1
                
                # Fill with other players to advance pick number
                if self.draft_engine.get_current_pick_info()[0] <= 36:
                    for other in list(self.available_players):
                        if other.position != 'QB':
                            self._make_pick(other)
                            picks_made += 1
                            break
        
        # Filter to show only QBs
        self.player_list.filter_by_position('QB')
        
        # Verify no drafted QBs are shown
        for row in self.player_list.row_frames:
            if hasattr(row, 'player'):
                self.assertNotIn(row.player, qbs_drafted)
                
        # Revert to before any QBs were drafted
        self._revert_to_pick(1)
        
        # Filter QBs again
        self.player_list.filter_by_position('QB')
        
        # Verify all QBs are available
        available_qbs = [p for p in self.player_list.players if p.position == 'QB']
        for qb in qbs_drafted:
            self.assertIn(qb, available_qbs)
            
    def test_search_functionality_after_picks(self):
        """Test search works correctly with picks and reverts"""
        # Make some picks
        for i in range(25):
            player = self.available_players[0]
            self._make_pick(player)
            
        # Search for a specific player who hasn't been drafted
        target_player = None
        for player in self.available_players:
            if 'cooper' in player.name.lower():
                target_player = player
                break
                
        if target_player:
            # Simulate search
            self.player_list.search_var.set('cooper')
            self.player_list.on_search_changed()
            
            # Verify target player is in results
            self.assertIn(target_player, self.player_list.players)
            
            # Draft the player
            self._make_pick(target_player)
            
            # Search again - should not find the player
            self.player_list.search_var.set('cooper')
            self.player_list.on_search_changed()
            
            # Verify player is not in results
            self.assertNotIn(target_player, self.player_list.players)


if __name__ == '__main__':
    # Run with minimal output
    unittest.main(verbosity=1)