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
    
    # Defensive scoring (for DB and LB)
    'tackle_solo': 1.75,
    'tackle_assist': 1.0,
    'sack': 3.5,
    'interception': 4.0,
    'pass_defended': 1.0,
    'forced_fumble': 3.0,
    'fumble_recovery': 3.0,
    'defensive_touchdown': 6.0,
    'safety': 2.0
}