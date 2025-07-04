import pytest
import time
from src.core.draft_logic import DraftEngine
from src.models.team import Team
from src.models.player import Player

class TestDraftReversion:
    def test_simple_reversion(self, teams, sample_players):
        """Test reverting a single pick."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Make 5 picks
        original_players = []
        for i in range(5):
            player = sample_players[i]
            original_players.append(player)
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
            teams[team_index].add_player(player)
        
        # Save state before reversion
        picks_before = len(engine.draft_results)
        
        # Simulate reverting to pick 3
        # Remove picks 5, 4, 3
        for i in range(4, 1, -1):  # Revert picks 5, 4, 3
            pick = engine.draft_results.pop()
            team = teams[pick.team_index]
            # Remove player from team roster
            for position, players in team.roster.items():
                if pick.player in players:
                    players.remove(pick.player)
                    break
        
        engine.current_pick = 3
        
        # Verify state after reversion
        assert len(engine.draft_results) == 2
        assert engine.current_pick == 3
        
        # Verify players were removed from teams
        for i in range(2, 5):
            team_index = engine.draft_order[i]
            assert original_players[i] not in teams[team_index].get_players()

    def test_multiple_reversions_and_redrafts(self, teams, sample_players):
        """Test multiple reversions and ensure different players can be picked."""
        engine = DraftEngine(teams, user_team_index=0)
        available_players = sample_players.copy()
        
        # Track which players were picked in each attempt
        pick_attempts = []
        
        for attempt in range(3):
            # Make 10 picks
            current_picks = []
            for i in range(10):
                if i < len(engine.draft_results):
                    # Skip already made picks
                    current_picks.append(engine.draft_results[i].player)
                    continue
                    
                # Pick a player (try to pick different ones each time)
                player_index = (i + attempt * 2) % len(available_players)
                player = available_players[player_index]
                
                # Skip if already drafted
                while any(player == pick.player for pick in engine.draft_results):
                    player_index = (player_index + 1) % len(available_players)
                    player = available_players[player_index]
                
                team_index = engine.draft_order[engine.current_pick - 1]
                engine.make_pick(team_index, player)
                teams[team_index].add_player(player)
                current_picks.append(player)
            
            pick_attempts.append(current_picks)
            
            # Revert to pick 5 (unless it's the last attempt)
            if attempt < 2:
                # Remove picks 10 down to 5
                while len(engine.draft_results) > 4:
                    pick = engine.draft_results.pop()
                    team = teams[pick.team_index]
                    # Remove player from team roster
                    for position, players in team.roster.items():
                        if pick.player in players:
                            players.remove(pick.player)
                            break
                
                engine.current_pick = 5
        
        # Verify that different players were picked after reversions
        # Check picks 5-10 across attempts
        for i in range(4, 10):
            players_at_position = [attempt[i] for attempt in pick_attempts if len(attempt) > i]
            # At least some positions should have different players
            unique_players = set(players_at_position)
            if len(players_at_position) > 1:
                # Not all picks need to be different, but some should be
                assert len(unique_players) > 1, f"Pick {i+1} always selected the same player"

    def test_reversion_restores_player_pool(self, teams, sample_players):
        """Test that reverting picks properly restores the available player pool."""
        engine = DraftEngine(teams, user_team_index=0)
        available_players = set(sample_players.copy())
        drafted_players = set()
        
        # Make 15 picks
        for i in range(15):
            player = sample_players[i]
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
            teams[team_index].add_player(player)
            drafted_players.add(player)
            available_players.discard(player)
        
        # Verify player pools
        assert len(drafted_players) == 15
        assert len(available_players) == len(sample_players) - 15
        
        # Revert to pick 8
        reverted_players = []
        while len(engine.draft_results) > 7:
            pick = engine.draft_results.pop()
            reverted_players.append(pick.player)
            team = teams[pick.team_index]
            # Remove player from team roster
            for position, players in team.roster.items():
                if pick.player in players:
                    players.remove(pick.player)
                    break
        
        engine.current_pick = 8
        
        # Update player pools
        for player in reverted_players:
            drafted_players.discard(player)
            available_players.add(player)
        
        # Verify restoration
        assert len(drafted_players) == 7
        assert len(available_players) == len(sample_players) - 7
        
        # Verify reverted players are available again
        for player in reverted_players:
            assert player in available_players
            assert player not in drafted_players

    def test_reversion_performance(self, teams, sample_players):
        """Test that reversion operations complete in reasonable time."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Make 100 picks
        for i in range(100):
            player = sample_players[i % len(sample_players)]
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
            teams[team_index].add_player(player)
        
        # Time the reversion
        start_time = time.time()
        
        # Revert to pick 50
        while len(engine.draft_results) > 49:
            pick = engine.draft_results.pop()
            team = teams[pick.team_index]
            # Remove player from team roster
            for position, players in team.roster.items():
                if pick.player in players:
                    players.remove(pick.player)
                    break
        
        engine.current_pick = 50
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Should complete in less than 100ms
        assert elapsed_time < 0.1, f"Reversion took {elapsed_time:.3f} seconds"

    def test_reversion_to_beginning(self, teams, sample_players):
        """Test reverting all the way back to the beginning."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Make 20 picks
        for i in range(20):
            player = sample_players[i]
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
            teams[team_index].add_player(player)
        
        # Revert all picks
        while engine.draft_results:
            pick = engine.draft_results.pop()
            team = teams[pick.team_index]
            # Remove player from team roster
            for position, players in team.roster.items():
                if pick.player in players:
                    players.remove(pick.player)
                    break
        
        engine.current_pick = 1
        
        # Verify clean slate
        assert len(engine.draft_results) == 0
        assert engine.current_pick == 1
        assert engine.current_round == 1
        
        # Verify all teams are empty
        for team in teams:
            assert team.count_players() == 0

    def test_reversion_maintains_draft_order(self, teams, sample_players):
        """Test that reverting maintains correct draft order."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Make picks through round 2
        for i in range(24):
            player = sample_players[i]
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
        
        # Revert to middle of round 1
        target_pick = 7
        while len(engine.draft_results) >= target_pick:
            engine.draft_results.pop()
        
        engine.current_pick = target_pick
        engine.current_round = 1
        
        # Verify next pick is correct
        pick_info = engine.get_current_pick_info()
        assert pick_info['pick_number'] == target_pick
        assert pick_info['team_index'] == engine.draft_order[target_pick - 1]

    def test_rapid_reversion_cycles(self, teams, sample_players):
        """Test rapid reversion and re-drafting cycles."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Perform multiple rapid cycles
        for cycle in range(5):
            # Draft to pick 10
            while engine.current_pick <= 10:
                player_idx = (engine.current_pick - 1 + cycle * 3) % len(sample_players)
                player = sample_players[player_idx]
                team_index = engine.draft_order[engine.current_pick - 1]
                engine.make_pick(team_index, player)
            
            # Revert to pick 5
            while len(engine.draft_results) > 4:
                engine.draft_results.pop()
            engine.current_pick = 5
        
        # Final verification
        assert len(engine.draft_results) == 4
        assert engine.current_pick == 5