def debug_print(*args, **kwargs):
    print(*args, **kwargs)

def _generate_competitor_bids_basic(official_estimate: float, num_competitors: int = 3) -> list:
    """
    Generate realistic competitor bids based on official estimate.
    Bids are distributed around the estimate with natural variation.
    """
    import random
    competitor_bids = []
    
    # Generate bids: typically 85%-115% of estimate, with clustering
    for i in range(num_competitors):
        # Add some randomness: most bids cluster near estimate, some are aggressive/conservative
        if i == 0:
            # Aggressive bidder: 85-95% of estimate
            ratio = random.uniform(0.85, 0.95)
            name = "Aggressive Competitor Co."
        elif i == 1:
            # Conservative bidder: 100-115% of estimate
            ratio = random.uniform(1.00, 1.15)
            name = "Premium Solutions Ltd."
        else:
            # Moderate bidder: 92-108% of estimate
            ratio = random.uniform(0.92, 1.08)
            name = f"Regional Contractor {i}"
        
        bid_amount = official_estimate * ratio
        competitor_bids.append({
            'name': name,
            'bid': round(bid_amount, 2)
        })
    
    return competitor_bids
def _generate_competitor_bids(official_estimate: float, num_competitors: int = 3, risk_preference: str = 'moderate') -> list:
    """
    Generate realistic competitor bids based on official estimate and risk preference.
    """
    import random
    competitor_bids = []
    
    # Risk-based bid ratio ranges
    risk_ranges = {
        'aggressive': (0.82, 0.94),    # Lower bids, higher risk
        'moderate': (0.88, 1.02),      # Balanced around estimate
        'conservative': (0.94, 1.08)   # Higher bids, safer win
    }
    min_ratio, max_ratio = risk_ranges.get(risk_preference, (0.88, 1.02))
    
    for i in range(num_competitors):
        # Add variation: cluster bids with some outliers
        if i < num_competitors - 1:
            # Most bids cluster in middle of range
            ratio = random.uniform(min_ratio + 0.03, max_ratio - 0.03)
        else:
            # Last bid is an outlier (aggressive or conservative)
            ratio = random.choice([random.uniform(min_ratio, min_ratio + 0.03), 
                                  random.uniform(max_ratio - 0.03, max_ratio)])
        
        bid_amount = official_estimate * ratio
        competitor_bids.append({
            'name': f"Competitor {i+1}",
            'bid': round(bid_amount, 2)
        })
    
    return competitor_bids    

__all__ = ['_generate_competitor_bids', '_generate_competitor_bids_basic', 'debug_print']

