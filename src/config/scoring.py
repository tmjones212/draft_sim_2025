"""Fantasy football scoring configuration"""

# Point values for statistics
SCORING_CONFIG = {
    # Passing
    'pass_completion': 0.5,
    'pass_yard': 0.05,
    
    # Rushing
    'rush_yard': 0.2,
    
    # Receiving
    'reception': 2.0,
    'rec_yard': 0.2,
    
    # Touchdowns (all types)
    'touchdown': 6.0,
    
    # Bonuses
    'bonus_pass_300_yards': 6.0,
    'bonus_rush_100_yards': 3.0,
    'bonus_rec_100_yards': 3.0,
    
    # Defensive scoring (IDP) - User specified values
    'tackle_solo': 1.75,
    'tackle_assist': 1.0,
    'sack': 4.0,
    'int': 6.0,
    'ff': 4.0,  # Forced fumble
    'fr': 3.0,  # Fumble recovery
    'def_td': 6.0,  # Defensive TD
    'safety': 2.0,
    'pass_defended': 1.5
}