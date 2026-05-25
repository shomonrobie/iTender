# modules/ppr_calculations.py
import numpy as np

def calculate_ppr_metrics(official_estimate: float, competitor_bids: list, nppi_factor: float = None) -> dict:
    """
    Calculate PPR 2025 compliance metrics.
    Reuses the same logic as render_ppr_compliance_viz
    """
    comp_bid_values = [cb.get('bid', 0) for cb in competitor_bids] if competitor_bids else []
    
    if nppi_factor is None:
        nppi_factor = 0.92  # Default 28-day average
    
    nppi_price = official_estimate * nppi_factor
    
    # Calculate weighted average (X̄) - using your formula from the viz
    if comp_bid_values:
        avg_competitor = sum(comp_bid_values) / len(comp_bid_values)
        weighted_average = (0.5 * avg_competitor) + (0.2 * official_estimate) + (0.3 * nppi_price)
        
        # Calculate standard deviation
        if len(comp_bid_values) > 1:
            weighted_std_dev = np.std(comp_bid_values)
        else:
            weighted_std_dev = official_estimate * 0.05  # Default 5% of estimate
    else:
        # No competitor bids - use conservative estimate
        weighted_average = official_estimate * 0.85
        weighted_std_dev = official_estimate * 0.10
    
    # SLT Threshold = X̄ - Sd (or 80% of estimate as fallback)
    slt_threshold = max(weighted_average - weighted_std_dev, official_estimate * 0.75)
    
    # Also calculate the 80% rule for comparison
    slt_eighty_percent = official_estimate * 0.80
    
    return {
        'nppi_factor': nppi_factor,
        'nppi_price': nppi_price,
        'avg_competitor': avg_competitor if comp_bid_values else 0,
        'weighted_average': weighted_average,
        'weighted_std_dev': weighted_std_dev,
        'slt_threshold': slt_threshold,
        'slt_eighty_percent': slt_eighty_percent,
        'competitor_count': len(comp_bid_values),
        'competitor_bids': comp_bid_values
    }