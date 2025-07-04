import pytest
import sys
from pathlib import Path

# Add the src directory to the Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.models.player import Player
from src.models.team import Team
from src.core.draft_logic import DraftEngine
from config import Config

@pytest.fixture
def sample_players():
    """Create a list of sample players for testing."""
    players = [
        Player(name="Patrick Mahomes", position="QB", rank=1, adp=1.5, team="KC", bye_week=6, position_rank=1),
        Player(name="Josh Allen", position="QB", rank=5, adp=5.2, team="BUF", bye_week=13, position_rank=2),
        Player(name="Christian McCaffrey", position="RB", rank=2, adp=1.1, team="SF", bye_week=9, position_rank=1),
        Player(name="Tyreek Hill", position="WR", rank=3, adp=3.5, team="MIA", bye_week=6, position_rank=1),
        Player(name="Travis Kelce", position="TE", rank=4, adp=4.2, team="KC", bye_week=6, position_rank=1),
        Player(name="Austin Ekeler", position="RB", rank=6, adp=6.8, team="LAC", bye_week=5, position_rank=2),
        Player(name="Stefon Diggs", position="WR", rank=7, adp=7.3, team="BUF", bye_week=13, position_rank=2),
        Player(name="Mark Andrews", position="TE", rank=8, adp=8.9, team="BAL", bye_week=13, position_rank=2),
        Player(name="Saquon Barkley", position="RB", rank=9, adp=9.1, team="PHI", bye_week=10, position_rank=3),
        Player(name="CeeDee Lamb", position="WR", rank=10, adp=10.5, team="DAL", bye_week=7, position_rank=3),
    ]
    # Add more players to have enough for a full draft
    for i in range(11, 201):
        pos = ["QB", "RB", "WR", "TE"][i % 4]
        pos_rank = (i // 4) + 1
        players.append(
            Player(
                name=f"Player {i}",
                position=pos,
                rank=i,
                adp=float(i) + 0.1,
                team="TM",
                bye_week=(i % 14) + 1,
                position_rank=pos_rank
            )
        )
    return players

@pytest.fixture
def teams():
    """Create a list of teams for testing."""
    team_names = ["Team 1", "Team 2", "Team 3", "Team 4", "Team 5", "Team 6", 
                  "Team 7", "Team 8", "Team 9", "Team 10", "Team 11", "Team 12"]
    return [Team(name) for name in team_names]

@pytest.fixture
def draft_engine(teams):
    """Create a draft engine with test teams."""
    return DraftEngine(teams, user_team_index=0)

@pytest.fixture
def config():
    """Return the test configuration."""
    return Config