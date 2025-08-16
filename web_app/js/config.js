// Configuration constants
const CONFIG = {
    NUM_TEAMS: 10,
    NUM_ROUNDS: 16,
    SNAKE_DRAFT: true,
    THIRD_ROUND_REVERSAL: true,
    DEFAULT_TIMER_SECONDS: 90,
    
    // Position limits
    MAX_QB: 4,
    MAX_RB: 9,
    MAX_WR: 9,
    MAX_TE: 3,
    MAX_LB: 4,
    MAX_DB: 4,
    
    // VAR replacement levels (for Value Above Replacement)
    VAR_LEVELS: {
        QB: 10,
        RB: 30,
        WR: 30,
        TE: 10,
        LB: 30,
        DB: 30
    },
    
    // Team names (matching Python version)
    TEAM_NAMES: ['KARWAN', 'JOEY', 'PETER', 'ERIC', 'JERWAN', 'STAN', 'PAT', 'ME', 'JOHNSON', 'LUAN'],
    
    // Scoring settings (for game history calculations)
    SCORING: {
        completions: 0.5,
        passYards: 0.05,
        passTD: 6,
        rushYards: 0.2,
        rushTD: 6,
        receptions: 2.0,
        recYards: 0.2,
        recTD: 6,
        
        // Bonuses
        pass300Bonus: 6,
        rush100Bonus: 3,
        rec100Bonus: 3
    },
    
    // Dome teams
    DOME_TEAMS: ['ATL', 'DET', 'MIN', 'NO', 'LV', 'ARI', 'DAL', 'HOU', 'IND'],
    
    // Manager name mappings for notes
    MANAGER_MAPPINGS: {
        'KARWAN': 'HE HATE ME',
        'JOEY': 'Joey',
        'PETER': 'P-Nasty',
        'ERIC': 'Erich',
        'JERWAN': 'champ',
        'STAN': 'Stan',
        'PAT': 'PatrickS',
        'ME': 'Trent',
        'JOHNSON': 'johnson',
        'LUAN': 'luan'
    }
};

// Position colors
const POSITION_COLORS = {
    QB: '#ff69b4',
    RB: '#40e0d0',
    WR: '#4169e1',
    TE: '#ff8c00',
    LB: '#9370db',
    DB: '#32cd32'
};

// Tier colors
const TIER_COLORS = {
    1: '#FFD700',
    2: '#C0C0C0', 
    3: '#CD7F32',
    4: '#4169E1',
    5: '#32CD32',
    6: '#FF6347',
    7: '#9370DB',
    8: '#20B2AA'
};

// SOS (Strength of Schedule) colors
const SOS_COLORS = {
    easy: '#4CAF50',    // Green: 1-10
    medium: '#FFC107',  // Yellow: 11-20
    hard: '#F44336'     // Red: 21-32
};