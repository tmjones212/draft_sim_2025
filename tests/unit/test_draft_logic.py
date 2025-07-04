import pytest
from src.core.draft_logic import DraftEngine, DraftPick
from src.models.team import Team
from src.models.player import Player

class TestDraftEngine:
    def test_initialization(self, teams):
        """Test draft engine initialization."""
        engine = DraftEngine(teams, user_team_index=0)
        assert len(engine.teams) == 12
        assert engine.user_team_index == 0
        assert engine.current_pick == 1
        assert engine.current_round == 1
        assert len(engine.draft_order) == 192  # 12 teams * 16 rounds
        assert len(engine.draft_results) == 0

    def test_snake_draft_order_with_3rd_round_reversal(self, teams):
        """Test snake draft order with 3rd round reversal."""
        engine = DraftEngine(teams, user_team_index=0)
        
        # Round 1: Normal order (1-12)
        round_1 = engine.draft_order[0:12]
        assert round_1 == list(range(12))
        
        # Round 2: Reversed order (12-1) 
        round_2 = engine.draft_order[12:24]
        assert round_2 == list(range(11, -1, -1))
        
        # Round 3: Same as round 2 (12-1) due to 3rd round reversal
        round_3 = engine.draft_order[24:36]
        assert round_3 == list(range(11, -1, -1))
        
        # Round 4: Normal order (1-12)
        round_4 = engine.draft_order[36:48]
        assert round_4 == list(range(12))

    def test_make_pick_success(self, draft_engine, sample_players):
        """Test making a successful pick."""
        player = sample_players[0]
        team_index = 0
        
        draft_engine.make_pick(team_index, player)
        
        assert len(draft_engine.draft_results) == 1
        pick = draft_engine.draft_results[0]
        assert pick.pick_number == 1
        assert pick.round == 1
        assert pick.team_index == 0
        assert pick.player == player
        assert draft_engine.current_pick == 2

    def test_make_multiple_picks(self, draft_engine, sample_players):
        """Test making multiple picks in sequence."""
        for i in range(5):
            current_team_index = draft_engine.draft_order[i]
            draft_engine.make_pick(current_team_index, sample_players[i])
        
        assert len(draft_engine.draft_results) == 5
        assert draft_engine.current_pick == 6
        assert draft_engine.current_round == 1

    def test_round_transitions(self, draft_engine, sample_players):
        """Test transitions between rounds."""
        # Make 12 picks (complete round 1)
        for i in range(12):
            current_team_index = draft_engine.draft_order[i]
            draft_engine.make_pick(current_team_index, sample_players[i])
        
        assert draft_engine.current_round == 2
        assert draft_engine.current_pick == 13
        
        # Make another 12 picks (complete round 2)
        for i in range(12, 24):
            current_team_index = draft_engine.draft_order[i]
            draft_engine.make_pick(current_team_index, sample_players[i])
        
        assert draft_engine.current_round == 3
        assert draft_engine.current_pick == 25

    def test_is_draft_complete(self, draft_engine, sample_players):
        """Test draft completion detection."""
        assert not draft_engine.is_draft_complete()
        
        # Make all 192 picks
        for i in range(192):
            current_team_index = draft_engine.draft_order[i]
            draft_engine.make_pick(current_team_index, sample_players[i % len(sample_players)])
        
        assert draft_engine.is_draft_complete()
        assert draft_engine.current_pick == 193

    def test_get_current_pick_info(self, draft_engine):
        """Test getting current pick information."""
        pick_info = draft_engine.get_current_pick_info()
        
        assert pick_info['pick_number'] == 1
        assert pick_info['round'] == 1
        assert pick_info['team_index'] == 0
        assert pick_info['team'] == draft_engine.teams[0]

    def test_picks_by_round(self, draft_engine, sample_players):
        """Test getting picks organized by round."""
        # Make picks across multiple rounds
        for i in range(30):  # 2.5 rounds
            current_team_index = draft_engine.draft_order[i]
            draft_engine.make_pick(current_team_index, sample_players[i % len(sample_players)])
        
        picks_by_round = draft_engine.get_picks_by_round()
        
        assert len(picks_by_round[1]) == 12
        assert len(picks_by_round[2]) == 12
        assert len(picks_by_round[3]) == 6
        
        # Verify pick numbers
        assert all(pick.pick_number in range(1, 13) for pick in picks_by_round[1])
        assert all(pick.pick_number in range(13, 25) for pick in picks_by_round[2])
        assert all(pick.pick_number in range(25, 31) for pick in picks_by_round[3])

    def test_user_team_picks(self, draft_engine, sample_players):
        """Test tracking user team picks."""
        # Make some picks including user team (index 0)
        for i in range(24):  # 2 rounds
            current_team_index = draft_engine.draft_order[i]
            draft_engine.make_pick(current_team_index, sample_players[i % len(sample_players)])
        
        user_picks = [pick for pick in draft_engine.draft_results if pick.team_index == 0]
        assert len(user_picks) == 2  # User team gets 2 picks in first 2 rounds
        assert user_picks[0].pick_number == 1  # First pick
        assert user_picks[1].pick_number == 24  # Last pick of round 2

    def test_invalid_pick_number_sequence(self, draft_engine, sample_players):
        """Test that picks must be made in order."""
        # Can't skip picks - engine enforces sequential picks
        draft_engine.make_pick(0, sample_players[0])
        assert draft_engine.current_pick == 2
        
        # Next pick must be for pick 2
        current_team = draft_engine.draft_order[1]
        draft_engine.make_pick(current_team, sample_players[1])
        assert draft_engine.current_pick == 3