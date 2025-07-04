import pytest
import time
import random
from src.core.draft_logic import DraftEngine
from src.models.team import Team
from src.models.player import Player

class TestPerformance:
    def test_draft_pick_performance(self, teams, sample_players):
        """Test that making picks is performant."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Time 100 picks
        start_time = time.time()
        
        for i in range(100):
            player = sample_players[i % len(sample_players)]
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
            teams[team_index].add_player(player)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Should complete in less than 100ms (1ms per pick)
        assert elapsed_time < 0.1, f"100 picks took {elapsed_time:.3f} seconds"
        
        # Calculate average time per pick
        avg_time_per_pick = elapsed_time / 100
        assert avg_time_per_pick < 0.001, f"Average time per pick: {avg_time_per_pick*1000:.2f}ms"

    def test_reversion_performance_scaling(self, teams, sample_players):
        """Test reversion performance with different draft depths."""
        test_cases = [
            (50, 0.05),    # 50 picks, 50ms limit
            (100, 0.1),    # 100 picks, 100ms limit
            (150, 0.15),   # 150 picks, 150ms limit
        ]
        
        for num_picks, time_limit in test_cases:
            engine = DraftEngine(teams, user_team_index=0)
            
            # Make picks
            for i in range(num_picks):
                player = sample_players[i % len(sample_players)]
                team_index = engine.draft_order[i]
                engine.make_pick(team_index, player)
                teams[team_index].add_player(player)
            
            # Time reverting to half way
            target_pick = num_picks // 2
            start_time = time.time()
            
            while len(engine.draft_results) > target_pick - 1:
                pick = engine.draft_results.pop()
                team = teams[pick.team_index]
                # Remove player from team roster
                for position, players in team.roster.items():
                    if pick.player in players:
                        players.remove(pick.player)
                        break
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            assert elapsed_time < time_limit, \
                f"Reverting {num_picks//2} picks from {num_picks} took {elapsed_time:.3f}s (limit: {time_limit}s)"

    def test_repeated_reversion_performance(self, teams, sample_players):
        """Test performance of multiple reversions (simulating user going back and forth)."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Make initial 50 picks
        for i in range(50):
            player = sample_players[i % len(sample_players)]
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
            teams[team_index].add_player(player)
        
        # Time 10 reversion cycles
        start_time = time.time()
        
        for cycle in range(10):
            # Revert to pick 30
            while len(engine.draft_results) > 29:
                pick = engine.draft_results.pop()
                team = teams[pick.team_index]
                for position, players in team.roster.items():
                    if pick.player in players:
                        players.remove(pick.player)
                        break
            engine.current_pick = 30
            
            # Re-draft to pick 50
            for i in range(29, 50):
                player = sample_players[(i + cycle) % len(sample_players)]
                team_index = engine.draft_order[i]
                engine.make_pick(team_index, player)
                teams[team_index].add_player(player)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 10 cycles should complete in under 1 second
        assert elapsed_time < 1.0, f"10 reversion cycles took {elapsed_time:.3f} seconds"

    def test_player_pool_search_performance(self, sample_players):
        """Test performance of searching/filtering large player pools."""
        # Create a large player pool (1000 players)
        large_player_pool = []
        positions = ["QB", "RB", "WR", "TE"]
        teams = ["KC", "BUF", "SF", "DAL", "MIA", "PHI", "CIN", "JAX"]
        
        for i in range(1000):
            player = Player(
                name=f"Player {i}",
                position=positions[i % 4],
                rank=i + 1,
                adp=float(i + 1) + random.random(),
                team=teams[i % 8],
                bye_week=(i % 14) + 1,
                position_rank=(i // 4) + 1
            )
            large_player_pool.append(player)
        
        # Test various filter operations
        operations = [
            # Position filter
            lambda: [p for p in large_player_pool if p.position == "RB"],
            # Rank range filter
            lambda: [p for p in large_player_pool if 100 <= p.rank <= 200],
            # Team filter
            lambda: [p for p in large_player_pool if p.team == "KC"],
            # Bye week filter
            lambda: [p for p in large_player_pool if p.bye_week == 6],
            # Complex filter
            lambda: [p for p in large_player_pool 
                    if p.position in ["RB", "WR"] and p.rank <= 100],
            # Sort by ADP
            lambda: sorted(large_player_pool, key=lambda p: p.adp),
            # Sort by rank
            lambda: sorted(large_player_pool, key=lambda p: p.rank),
        ]
        
        for i, operation in enumerate(operations):
            start_time = time.time()
            result = operation()
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Each operation should complete in under 10ms
            assert elapsed_time < 0.01, \
                f"Operation {i} took {elapsed_time*1000:.2f}ms (limit: 10ms)"

    def test_random_draft_simulation_performance(self, teams, sample_players):
        """Test performance of a complete random draft with reversions."""
        engine = DraftEngine(teams, user_team_index=0)
        available_players = sample_players.copy()
        random.shuffle(available_players)
        
        start_time = time.time()
        picks_made = 0
        reversions_made = 0
        
        # Run for 1 second max
        while time.time() - start_time < 1.0 and not engine.is_draft_complete():
            # 20% chance to revert if we have picks
            if len(engine.draft_results) > 5 and random.random() < 0.2:
                # Revert random number of picks (1-10)
                revert_count = random.randint(1, min(10, len(engine.draft_results) - 5))
                
                for _ in range(revert_count):
                    pick = engine.draft_results.pop()
                    team = teams[pick.team_index]
                    for position, players in team.roster.items():
                        if pick.player in players:
                            players.remove(pick.player)
                            break
                
                engine.current_pick -= revert_count
                reversions_made += 1
            else:
                # Make a pick
                team_index = engine.draft_order[engine.current_pick - 1]
                # Find an undrafted player
                for player in available_players:
                    if not any(pick.player == player for pick in engine.draft_results):
                        engine.make_pick(team_index, player)
                        teams[team_index].add_player(player)
                        picks_made += 1
                        break
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Should make reasonable progress
        assert picks_made > 50, f"Only made {picks_made} picks in {elapsed_time:.2f}s"
        print(f"Performance test: {picks_made} picks, {reversions_made} reversions in {elapsed_time:.2f}s")

    def test_memory_usage_after_reversions(self, teams, sample_players):
        """Test that memory is properly freed after reversions."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Make and revert picks many times
        for cycle in range(20):
            # Make 50 picks
            for i in range(50):
                player = sample_players[(i + cycle * 2) % len(sample_players)]
                team_index = engine.draft_order[engine.current_pick - 1]
                engine.make_pick(team_index, player)
                teams[team_index].add_player(player)
            
            # Revert all picks
            while engine.draft_results:
                pick = engine.draft_results.pop()
                team = teams[pick.team_index]
                for position, players in team.roster.items():
                    if pick.player in players:
                        players.remove(pick.player)
                        break
            engine.current_pick = 1
        
        # Verify clean state
        assert len(engine.draft_results) == 0
        assert engine.current_pick == 1
        assert all(team.count_players() == 0 for team in teams)