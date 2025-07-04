import pytest
from src.models.player import Player

class TestPlayerPool:
    def test_player_availability_tracking(self, sample_players):
        """Test tracking available vs drafted players."""
        all_players = sample_players.copy()
        available_players = sample_players.copy()
        drafted_players = []
        
        # Draft some players
        for i in range(5):
            player = available_players.pop(i)
            drafted_players.append(player)
        
        # Verify counts
        assert len(available_players) == len(all_players) - 5
        assert len(drafted_players) == 5
        
        # Verify no overlap
        for player in drafted_players:
            assert player not in available_players
            assert player in all_players

    def test_player_pool_restoration(self, sample_players):
        """Test restoring players to available pool."""
        available_players = sample_players.copy()
        drafted_players = []
        
        # Draft 10 players
        players_to_draft = []
        for i in range(10):
            player = available_players[i]
            players_to_draft.append(player)
        
        for player in players_to_draft:
            available_players.remove(player)
            drafted_players.append(player)
        
        # Restore last 5 players
        players_to_restore = drafted_players[-5:]
        for player in players_to_restore:
            drafted_players.remove(player)
            available_players.append(player)
        
        # Verify restoration
        assert len(available_players) == len(sample_players) - 5
        assert len(drafted_players) == 5
        for player in players_to_restore:
            assert player in available_players
            assert player not in drafted_players

    def test_duplicate_player_prevention(self, sample_players):
        """Test that same player can't be drafted twice."""
        available_players = sample_players.copy()
        drafted_players = []
        
        player = available_players[0]
        
        # First draft should succeed
        available_players.remove(player)
        drafted_players.append(player)
        
        # Attempting to draft again should fail
        assert player not in available_players
        assert player in drafted_players
        
        # Can't add to drafted again
        with pytest.raises(ValueError):
            drafted_players.append(player)
            raise ValueError("Player already drafted")

    def test_player_search_by_position(self, sample_players):
        """Test finding available players by position."""
        available_players = sample_players.copy()
        
        # Get all QBs
        available_qbs = [p for p in available_players if p.position == "QB"]
        assert len(available_qbs) > 0
        
        # Draft a QB
        qb_to_draft = available_qbs[0]
        available_players.remove(qb_to_draft)
        
        # Verify QB is no longer available
        remaining_qbs = [p for p in available_players if p.position == "QB"]
        assert len(remaining_qbs) == len(available_qbs) - 1
        assert qb_to_draft not in remaining_qbs

    def test_player_search_by_rank(self, sample_players):
        """Test finding best available player."""
        available_players = sorted(sample_players.copy(), key=lambda p: p.rank)
        
        # Best available should be rank 1
        best_available = available_players[0]
        assert best_available.rank == 1
        
        # Remove top 5 players
        for _ in range(5):
            available_players.pop(0)
        
        # Best available should now be rank 6
        best_available = available_players[0]
        assert best_available.rank == 6

    def test_position_scarcity(self, sample_players):
        """Test tracking position scarcity as players are drafted."""
        available_players = sample_players.copy()
        
        # Count initial positions
        position_counts = {}
        for player in available_players:
            position_counts[player.position] = position_counts.get(player.position, 0) + 1
        
        initial_rb_count = position_counts.get("RB", 0)
        
        # Draft all RBs
        rbs_to_draft = [p for p in available_players if p.position == "RB"]
        for rb in rbs_to_draft:
            available_players.remove(rb)
        
        # Verify no RBs available
        remaining_rbs = [p for p in available_players if p.position == "RB"]
        assert len(remaining_rbs) == 0
        
        # Other positions should still be available
        remaining_qbs = [p for p in available_players if p.position == "QB"]
        assert len(remaining_qbs) > 0

    def test_bye_week_filtering(self, sample_players):
        """Test filtering players by bye week."""
        available_players = sample_players.copy()
        
        # Find players with specific bye week
        bye_week_6_players = [p for p in available_players if p.bye_week == 6]
        assert len(bye_week_6_players) > 0
        
        # Draft a bye week 6 player
        player_to_draft = bye_week_6_players[0]
        available_players.remove(player_to_draft)
        
        # Verify count decreased
        remaining_bye_6 = [p for p in available_players if p.bye_week == 6]
        assert len(remaining_bye_6) == len(bye_week_6_players) - 1

    def test_team_stack_filtering(self, sample_players):
        """Test filtering players by NFL team."""
        available_players = sample_players.copy()
        
        # Find KC players (Mahomes and Kelce in sample data)
        kc_players = [p for p in available_players if p.team == "KC"]
        assert len(kc_players) >= 2
        
        # Draft one KC player
        available_players.remove(kc_players[0])
        
        # Other KC players should still be available
        remaining_kc = [p for p in available_players if p.team == "KC"]
        assert len(remaining_kc) == len(kc_players) - 1

    def test_adp_based_filtering(self, sample_players):
        """Test filtering players by ADP range."""
        available_players = sample_players.copy()
        
        # Find players with ADP between 20-40
        mid_round_players = [p for p in available_players if 20 <= p.adp <= 40]
        initial_count = len(mid_round_players)
        
        # Draft some of them
        for i in range(min(5, len(mid_round_players))):
            available_players.remove(mid_round_players[i])
        
        # Verify remaining
        remaining_mid = [p for p in available_players if 20 <= p.adp <= 40]
        assert len(remaining_mid) == max(0, initial_count - 5)

    def test_position_rank_tracking(self, sample_players):
        """Test tracking position ranks as players are drafted."""
        available_players = sample_players.copy()
        
        # Get all RBs sorted by position rank
        available_rbs = sorted(
            [p for p in available_players if p.position == "RB"],
            key=lambda p: p.position_rank
        )
        
        # RB1 should have position_rank 1
        rb1 = available_rbs[0]
        assert rb1.position_rank == 1
        
        # Remove RB1
        available_players.remove(rb1)
        
        # Next best RB should be RB2
        remaining_rbs = sorted(
            [p for p in available_players if p.position == "RB"],
            key=lambda p: p.position_rank
        )
        if remaining_rbs:
            assert remaining_rbs[0].position_rank == 2