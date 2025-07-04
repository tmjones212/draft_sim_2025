import pytest
import random
from src.core.draft_logic import DraftEngine
from src.models.team import Team
from src.models.player import Player

class TestFullDraftScenarios:
    def test_complete_draft_simulation(self, teams, sample_players):
        """Test a complete 16-round draft."""
        engine = DraftEngine(teams, user_team_index=0)
        available_players = sample_players.copy()
        
        # Complete all 192 picks
        for i in range(192):
            team_index = engine.draft_order[i]
            # Find best available player that team can draft
            for player in available_players:
                if teams[team_index].can_draft_player(player):
                    if not any(pick.player == player for pick in engine.draft_results):
                        engine.make_pick(team_index, player)
                        teams[team_index].add_player(player)
                        break
        
        # Verify draft completion
        assert engine.is_draft_complete()
        assert len(engine.draft_results) == 192
        
        # Verify each team has 16 players
        for team in teams:
            assert team.count_players() == 16

    def test_user_team_auto_draft(self, teams, sample_players):
        """Test auto-drafting for user team when timer expires."""
        engine = DraftEngine(teams, user_team_index=0)
        available_players = sample_players.copy()
        
        # Simulate first 20 picks with user on auto-draft
        for i in range(20):
            team_index = engine.draft_order[i]
            
            # Auto-draft logic: pick best available by rank
            best_available = None
            for player in sorted(available_players, key=lambda p: p.rank):
                if teams[team_index].can_draft_player(player):
                    if not any(pick.player == player for pick in engine.draft_results):
                        best_available = player
                        break
            
            if best_available:
                engine.make_pick(team_index, best_available)
                teams[team_index].add_player(best_available)
        
        # Verify user team has picks
        user_picks = [p for p in engine.draft_results if p.team_index == 0]
        assert len(user_picks) >= 1  # User has pick 1

    def test_position_run_scenario(self, teams, sample_players):
        """Test a scenario where there's a run on a position."""
        engine = DraftEngine(teams, user_team_index=0)
        available_players = sample_players.copy()
        
        # Simulate first round with RB run
        for i in range(12):
            team_index = engine.draft_order[i]
            
            # First 8 teams take RBs if available
            if i < 8:
                rb_available = [p for p in available_players if p.position == "RB"
                              and not any(pick.player == p for pick in engine.draft_results)]
                if rb_available:
                    rb = sorted(rb_available, key=lambda p: p.rank)[0]
                    engine.make_pick(team_index, rb)
                    teams[team_index].add_player(rb)
                    continue
            
            # Other teams take best available
            for player in sorted(available_players, key=lambda p: p.rank):
                if not any(pick.player == player for pick in engine.draft_results):
                    engine.make_pick(team_index, player)
                    teams[team_index].add_player(player)
                    break
        
        # Verify RB scarcity
        round_1_picks = engine.draft_results[:12]
        rb_picks = [p for p in round_1_picks if p.player.position == "RB"]
        assert len(rb_picks) >= 6  # At least 6 RBs taken

    def test_zero_rb_strategy(self, teams, sample_players):
        """Test zero RB draft strategy for user team."""
        engine = DraftEngine(teams, user_team_index=0)
        available_players = sample_players.copy()
        
        # User avoids RBs in early rounds
        for i in range(60):  # First 5 rounds
            team_index = engine.draft_order[i]
            
            if team_index == 0:  # User team
                # Pick best non-RB
                non_rb_players = [p for p in available_players 
                                if p.position != "RB"
                                and not any(pick.player == p for pick in engine.draft_results)]
                if non_rb_players:
                    player = sorted(non_rb_players, key=lambda p: p.rank)[0]
                    engine.make_pick(team_index, player)
                    teams[team_index].add_player(player)
            else:
                # Other teams pick normally
                for player in sorted(available_players, key=lambda p: p.rank):
                    if teams[team_index].can_draft_player(player):
                        if not any(pick.player == player for pick in engine.draft_results):
                            engine.make_pick(team_index, player)
                            teams[team_index].add_player(player)
                            break
        
        # Verify user team has no RBs in first 5 picks
        user_picks = [p for p in engine.draft_results[:60] if p.team_index == 0]
        user_rbs = [p for p in user_picks if p.player.position == "RB"]
        assert len(user_rbs) == 0

    def test_bye_week_stacking(self, teams, sample_players):
        """Test avoiding too many players with same bye week."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Track bye weeks for user team
        user_bye_weeks = {}
        
        for i in range(48):  # First 4 rounds
            team_index = engine.draft_order[i]
            
            if team_index == 0:  # User team
                # Find player with least-used bye week
                candidates = []
                for player in sorted(sample_players, key=lambda p: p.rank):
                    if not any(pick.player == player for pick in engine.draft_results):
                        bye_count = user_bye_weeks.get(player.bye_week, 0)
                        if bye_count < 2:  # Limit 2 players per bye week
                            candidates.append(player)
                
                if candidates:
                    player = candidates[0]
                    engine.make_pick(team_index, player)
                    teams[team_index].add_player(player)
                    user_bye_weeks[player.bye_week] = user_bye_weeks.get(player.bye_week, 0) + 1
            else:
                # Other teams pick normally
                for player in sorted(sample_players, key=lambda p: p.rank):
                    if not any(pick.player == player for pick in engine.draft_results):
                        engine.make_pick(team_index, player)
                        teams[team_index].add_player(player)
                        break
        
        # Verify bye week distribution
        assert all(count <= 2 for count in user_bye_weeks.values())

    def test_reversion_during_draft(self, teams, sample_players):
        """Test reverting picks during an active draft."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Make 30 picks
        for i in range(30):
            player = sample_players[i]
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
            teams[team_index].add_player(player)
        
        # Save state
        picks_before_reversion = len(engine.draft_results)
        
        # Revert to pick 15
        while len(engine.draft_results) > 14:
            pick = engine.draft_results.pop()
            team = teams[pick.team_index]
            for position, players in team.roster.items():
                if pick.player in players:
                    players.remove(pick.player)
                    break
        engine.current_pick = 15
        
        # Continue draft with different picks
        for i in range(14, 30):
            # Pick different players
            player = sample_players[i + 20]  # Offset to get different players
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
            teams[team_index].add_player(player)
        
        # Verify we're back to same number of picks
        assert len(engine.draft_results) == picks_before_reversion

    def test_late_round_strategy(self, teams, sample_players):
        """Test late round draft strategy (handcuffs, upside picks)."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Complete first 12 rounds normally
        for i in range(144):  # 12 rounds
            player = sample_players[i % len(sample_players)]
            team_index = engine.draft_order[i]
            engine.make_pick(team_index, player)
            teams[team_index].add_player(player)
        
        # In late rounds, test picking backups/handcuffs
        # (In real implementation, would check for RB handcuffs)
        for i in range(144, 192):
            team_index = engine.draft_order[i]
            
            # Pick players with lower ADPs (upside picks)
            available = [p for p in sample_players 
                       if not any(pick.player == p for pick in engine.draft_results)]
            if available:
                # Sort by ADP difference from rank (upside)
                upside_picks = sorted(available, key=lambda p: p.rank - p.adp, reverse=True)
                if upside_picks:
                    player = upside_picks[0]
                    engine.make_pick(team_index, player)
                    teams[team_index].add_player(player)
        
        assert engine.is_draft_complete()

    def test_mixed_draft_with_reversions(self, teams, sample_players):
        """Test realistic draft with multiple reversions and different strategies."""
        engine = DraftEngine(teams, user_team_index=0)
        reversion_count = 0
        
        # Draft with occasional reversions
        target_pick = 1
        while not engine.is_draft_complete() and target_pick <= 100:
            # Make picks up to target
            while engine.current_pick <= target_pick and not engine.is_draft_complete():
                team_index = engine.draft_order[engine.current_pick - 1]
                
                # Find available player
                for player in sample_players:
                    if not any(pick.player == player for pick in engine.draft_results):
                        if teams[team_index].can_draft_player(player):
                            engine.make_pick(team_index, player)
                            teams[team_index].add_player(player)
                            break
            
            # Occasionally revert (simulate user changing mind)
            if target_pick > 10 and random.random() < 0.3:
                revert_to = max(1, target_pick - random.randint(3, 8))
                
                while len(engine.draft_results) > revert_to - 1:
                    pick = engine.draft_results.pop()
                    team = teams[pick.team_index]
                    for position, players in team.roster.items():
                        if pick.player in players:
                            players.remove(pick.player)
                            break
                
                engine.current_pick = revert_to
                target_pick = revert_to
                reversion_count += 1
            else:
                target_pick += random.randint(5, 15)
        
        # Verify draft state is consistent
        assert len(engine.draft_results) == engine.current_pick - 1
        assert reversion_count > 0  # Should have done some reversions