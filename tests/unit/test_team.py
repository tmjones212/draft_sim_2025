import pytest
from src.models.team import Team
from src.models.player import Player

class TestTeam:
    def test_initialization(self):
        """Test team initialization with default roster."""
        team = Team("Test Team")
        assert team.name == "Test Team"
        assert len(team.roster) == 16
        assert team.roster["QB"] == []
        assert team.roster["FLEX"] == []
        assert team.count_players() == 0

    def test_add_player_to_position(self):
        """Test adding player to specific position slot."""
        team = Team("Test Team")
        qb = Player("Patrick Mahomes", "QB", 1, 1.0, "KC", 6, 1)
        
        assert team.add_player(qb)
        assert len(team.roster["QB"]) == 1
        assert team.roster["QB"][0] == qb
        assert team.count_players() == 1

    def test_add_multiple_players_same_position(self):
        """Test filling position slots."""
        team = Team("Test Team")
        rb1 = Player("CMC", "RB", 2, 2.0, "SF", 9, 1)
        rb2 = Player("Ekeler", "RB", 6, 6.0, "LAC", 5, 2)
        
        assert team.add_player(rb1)
        assert team.add_player(rb2)
        assert len(team.roster["RB"]) == 2
        assert team.count_players() == 2

    def test_flex_position_assignment(self):
        """Test FLEX position accepts RB/WR/TE."""
        team = Team("Test Team")
        
        # Fill RB slots first
        for i in range(2):
            team.add_player(Player(f"RB{i}", "RB", i+1, i+1.0, "TM", 5, i+1))
        
        # Third RB should go to FLEX
        rb3 = Player("RB3", "RB", 10, 10.0, "TM", 5, 3)
        assert team.add_player(rb3)
        assert len(team.roster["FLEX"]) == 1
        assert team.roster["FLEX"][0] == rb3

    def test_bench_assignment(self):
        """Test players go to bench when starting slots are full."""
        team = Team("Test Team")
        
        # Fill all starting positions
        # 1 QB
        team.add_player(Player("QB1", "QB", 1, 1.0, "TM", 5, 1))
        
        # 2 RBs
        for i in range(2):
            team.add_player(Player(f"RB{i}", "RB", i+2, i+2.0, "TM", 5, i+1))
        
        # 2 WRs
        for i in range(2):
            team.add_player(Player(f"WR{i}", "WR", i+4, i+4.0, "TM", 5, i+1))
        
        # 1 TE
        team.add_player(Player("TE1", "TE", 6, 6.0, "TM", 5, 1))
        
        # 1 FLEX (RB)
        team.add_player(Player("RB3", "RB", 7, 7.0, "TM", 5, 3))
        
        # 1 DST
        team.add_player(Player("DST1", "DST", 8, 8.0, "TM", 5, 1))
        
        # 1 K
        team.add_player(Player("K1", "K", 9, 9.0, "TM", 5, 1))
        
        # Next player should go to bench
        bench_player = Player("BenchRB", "RB", 10, 10.0, "TM", 5, 4)
        assert team.add_player(bench_player)
        assert len(team.roster["BENCH"]) == 1
        assert team.roster["BENCH"][0] == bench_player

    def test_can_draft_player(self):
        """Test checking if a player can be drafted."""
        team = Team("Test Team")
        qb = Player("QB1", "QB", 1, 1.0, "TM", 5, 1)
        
        # Can draft first QB
        assert team.can_draft_player(qb)
        team.add_player(qb)
        
        # Can draft second QB (backup/bench)
        qb2 = Player("QB2", "QB", 2, 2.0, "TM", 5, 2)
        assert team.can_draft_player(qb2)

    def test_roster_full(self):
        """Test when roster is completely full."""
        team = Team("Test Team")
        
        # Add 16 players (full roster)
        for i in range(16):
            pos = ["QB", "RB", "WR", "TE"][i % 4]
            player = Player(f"Player{i}", pos, i+1, i+1.0, "TM", 5, (i//4)+1)
            team.add_player(player)
        
        assert team.count_players() == 16
        
        # Can't add 17th player
        extra_player = Player("Extra", "RB", 17, 17.0, "TM", 5, 5)
        assert not team.add_player(extra_player)
        assert team.count_players() == 16

    def test_get_players_list(self):
        """Test getting all players as a list."""
        team = Team("Test Team")
        players = []
        
        for i in range(5):
            pos = ["QB", "RB", "WR", "TE", "K"][i]
            player = Player(f"Player{i}", pos, i+1, i+1.0, "TM", 5, 1)
            players.append(player)
            team.add_player(player)
        
        team_players = team.get_players()
        assert len(team_players) == 5
        assert set(team_players) == set(players)

    def test_position_priority_order(self):
        """Test that positions are filled in the correct priority order."""
        team = Team("Test Team")
        
        # Add 3 WRs - should fill WR1, WR2, then FLEX
        wr1 = Player("WR1", "WR", 1, 1.0, "TM", 5, 1)
        wr2 = Player("WR2", "WR", 2, 2.0, "TM", 5, 2)
        wr3 = Player("WR3", "WR", 3, 3.0, "TM", 5, 3)
        
        team.add_player(wr1)
        team.add_player(wr2)
        team.add_player(wr3)
        
        assert len(team.roster["WR"]) == 2
        assert len(team.roster["FLEX"]) == 1
        assert team.roster["FLEX"][0] == wr3

    def test_special_teams_positions(self):
        """Test DST and K positions."""
        team = Team("Test Team")
        
        dst = Player("Bears DST", "DST", 100, 100.0, "CHI", 0, 1)
        k = Player("Justin Tucker", "K", 150, 150.0, "BAL", 13, 1)
        
        assert team.add_player(dst)
        assert team.add_player(k)
        
        assert len(team.roster["DST"]) == 1
        assert len(team.roster["K"]) == 1
        assert team.roster["DST"][0] == dst
        assert team.roster["K"][0] == k