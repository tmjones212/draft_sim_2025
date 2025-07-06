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
    'bonus_rec_100_yards': 3.0
}