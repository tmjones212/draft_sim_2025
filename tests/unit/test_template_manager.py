import unittest
import os
import shutil
import tempfile
from src.core.template_manager import TemplateManager, DraftTemplate
from src.models import Player, Team
from src.core import DraftEngine, DraftPick


class TestTemplateManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for templates
        self.temp_dir = tempfile.mkdtemp()
        self.template_manager = TemplateManager(self.temp_dir)
        
        # Create test players
        self.players = []
        for i in range(10):
            player = Player(
                name=f"Player {i}",
                position="RB" if i % 2 == 0 else "WR",
                team=f"TEAM{i}",
                bye_week=i + 1,
                points_2024=100 + i,
                points_2025_proj=110 + i,
                var=0.1 + i * 0.01,
                rank=i + 1,
                adp=i + 1.5
            )
            player.player_id = f"player_{i}"
            self.players.append(player)
        
        # Create test teams
        self.teams = []
        roster_spots = {'qb': 1, 'rb': 2, 'wr': 2, 'te': 1, 'flex': 1, 'bn': 2}
        for i in range(4):
            team = Team(i + 1, f"Team {i + 1}", roster_spots)
            self.teams.append(team)
        
        # Create draft engine
        self.draft_engine = DraftEngine(
            num_teams=4,
            roster_spots={'qb': 1, 'rb': 2, 'wr': 2, 'te': 1, 'flex': 1, 'bn': 2},
            draft_type='snake'
        )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_template(self):
        """Test saving and loading a template"""
        # Make some draft picks
        self.draft_engine.make_pick(self.teams[0], self.players[0])
        self.draft_engine.make_pick(self.teams[1], self.players[1])
        
        # Add players to team rosters
        self.teams[0].add_player(self.players[0])
        self.teams[1].add_player(self.players[1])
        
        # Save template
        success = self.template_manager.save_template(
            name="Test Template",
            draft_engine=self.draft_engine,
            teams=self.teams,
            available_players=self.players[2:],
            all_players=self.players,
            user_team_id=1,
            manual_mode=True,
            custom_rankings={"player_0": 1, "player_1": 2},
            player_tiers={"player_2": 1, "player_3": 2},
            watch_list=["player_4", "player_5"]
        )
        
        self.assertTrue(success)
        
        # Load template
        templates = self.template_manager.list_templates()
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["name"], "Test Template")
        
        template = self.template_manager.load_template(templates[0]["filename"])
        self.assertIsNotNone(template)
        self.assertEqual(template.name, "Test Template")
        
        # Verify draft configuration
        self.assertEqual(template.draft_config["num_teams"], 4)
        self.assertEqual(template.draft_config["draft_type"], "snake")
        
        # Verify draft results
        self.assertEqual(len(template.draft_results), 2)
        self.assertEqual(template.draft_results[0]["player_id"], "player_0")
        self.assertEqual(template.draft_results[1]["player_id"], "player_1")
        
        # Verify team states
        self.assertIn("1", template.team_states)
        self.assertIn("2", template.team_states)
        self.assertEqual(template.team_states["1"]["name"], "Team 1")
        self.assertIn("player_0", template.team_states["1"]["roster"]["rb"])
        
        # Verify player pool
        self.assertEqual(len(template.player_pool["all_players"]), 10)
        self.assertEqual(len(template.player_pool["available_player_ids"]), 8)
        
        # Verify user settings
        self.assertEqual(template.user_settings["user_team_id"], 1)
        self.assertTrue(template.user_settings["manual_mode"])
        self.assertEqual(template.user_settings["custom_rankings"]["player_0"], 1)
        self.assertEqual(template.user_settings["player_tiers"]["player_2"], 1)
        self.assertIn("player_4", template.user_settings["watch_list"])
    
    def test_list_templates(self):
        """Test listing multiple templates"""
        # Save multiple templates
        for i in range(3):
            self.template_manager.save_template(
                name=f"Template {i}",
                draft_engine=self.draft_engine,
                teams=self.teams,
                available_players=self.players,
                all_players=self.players,
                user_team_id=1,
                manual_mode=False
            )
        
        # List templates
        templates = self.template_manager.list_templates()
        self.assertEqual(len(templates), 3)
        
        # Verify templates are sorted by creation date (newest first)
        template_names = [t["name"] for t in templates]
        self.assertEqual(template_names, ["Template 2", "Template 1", "Template 0"])
    
    def test_delete_template(self):
        """Test deleting a template"""
        # Save a template
        self.template_manager.save_template(
            name="Delete Me",
            draft_engine=self.draft_engine,
            teams=self.teams,
            available_players=self.players,
            all_players=self.players,
            user_team_id=1,
            manual_mode=False
        )
        
        # Verify it exists
        templates = self.template_manager.list_templates()
        self.assertEqual(len(templates), 1)
        
        # Delete it
        success = self.template_manager.delete_template(templates[0]["filename"])
        self.assertTrue(success)
        
        # Verify it's gone
        templates = self.template_manager.list_templates()
        self.assertEqual(len(templates), 0)
    
    def test_save_template_with_complex_state(self):
        """Test saving a template with complex draft state"""
        # Simulate a more complex draft with multiple rounds
        picks = [
            (0, 0), (1, 1), (2, 2), (3, 3),  # Round 1
            (3, 4), (2, 5), (1, 6), (0, 7),  # Round 2 (snake)
        ]
        
        for team_idx, player_idx in picks:
            team = self.teams[team_idx]
            player = self.players[player_idx]
            self.draft_engine.make_pick(team, player)
            team.add_player(player)
        
        # Save template
        available = [p for p in self.players if p not in self.players[:8]]
        success = self.template_manager.save_template(
            name="Complex Draft",
            draft_engine=self.draft_engine,
            teams=self.teams,
            available_players=available,
            all_players=self.players,
            user_team_id=2,
            manual_mode=False
        )
        
        self.assertTrue(success)
        
        # Load and verify
        templates = self.template_manager.list_templates()
        template = self.template_manager.load_template(templates[0]["filename"])
        
        # Verify correct number of picks
        self.assertEqual(len(template.draft_results), 8)
        
        # Verify snake draft order
        self.assertEqual(template.draft_results[4]["team_id"], 4)  # Team 4 gets pick 5
        self.assertEqual(template.draft_results[7]["team_id"], 1)  # Team 1 gets pick 8
        
        # Verify current pick info
        current_pick = template.draft_config["current_pick"]
        self.assertEqual(current_pick["pick_number"], 9)
        self.assertEqual(current_pick["round"], 3)
    
    def test_invalid_template_handling(self):
        """Test handling of invalid template files"""
        # Try to load non-existent template
        template = self.template_manager.load_template("nonexistent.json")
        self.assertIsNone(template)
        
        # Create invalid JSON file
        invalid_file = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_file, 'w') as f:
            f.write("not valid json")
        
        # Try to load invalid template
        template = self.template_manager.load_template("invalid.json")
        self.assertIsNone(template)
        
        # Try to delete non-existent template
        success = self.template_manager.delete_template("nonexistent.json")
        self.assertFalse(success)


class TestDraftTemplate(unittest.TestCase):
    def test_draft_template_creation(self):
        """Test creating a DraftTemplate"""
        template = DraftTemplate("My Template")
        self.assertEqual(template.name, "My Template")
        self.assertIsNotNone(template.created_at)
        self.assertEqual(template.draft_config, {})
        self.assertEqual(template.draft_results, [])
        self.assertEqual(template.team_states, {})
        self.assertEqual(template.player_pool, {})
        self.assertEqual(template.user_settings, {})
    
    def test_draft_template_serialization(self):
        """Test converting DraftTemplate to/from dict"""
        template = DraftTemplate("Test")
        template.draft_config = {"num_teams": 10}
        template.draft_results = [{"pick_number": 1}]
        template.team_states = {"1": {"name": "Team 1"}}
        template.player_pool = {"available_player_ids": ["p1", "p2"]}
        template.user_settings = {"user_team_id": 1}
        
        # Convert to dict
        data = template.to_dict()
        self.assertEqual(data["name"], "Test")
        self.assertEqual(data["draft_config"]["num_teams"], 10)
        self.assertEqual(len(data["draft_results"]), 1)
        
        # Convert back from dict
        template2 = DraftTemplate.from_dict(data)
        self.assertEqual(template2.name, "Test")
        self.assertEqual(template2.draft_config["num_teams"], 10)
        self.assertEqual(len(template2.draft_results), 1)
        self.assertEqual(template2.team_states["1"]["name"], "Team 1")


if __name__ == '__main__':
    unittest.main()