"""
ADVANCED BID OPTIMIZATION ALGORITHM
Multi-Layered AI with Machine Learning, Market Dynamics, and Risk Analysis
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from scipy.optimize import minimize_scalar
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class AdvancedBidOptimizer:
    """
    Advanced bid optimization with 6-layer analysis:
    1. Statistical Analysis
    2. Machine Learning
    3. Market Dynamics
    4. Competitor Behavior
    5. Historical Pattern
    6. Risk Assessment
    """
    
    def __init__(self):
        self.ml_model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def calculate_optimal_bid(self, 
                             official_estimate: float,
                             competitor_bids: list,
                             market_conditions: dict = None,
                             company_profile: dict = None,
                             historical_data: list = None,
                             risk_tolerance: str = 'moderate') -> dict:
        """Calculate optimal bid using all available data"""
        
        if market_conditions is None:
            market_conditions = self._get_default_market_conditions()
        if company_profile is None:
            company_profile = self._get_default_company_profile()
            
        # Layer 1: Statistical Analysis
        statistical = self._statistical_analysis(official_estimate, competitor_bids)
        
        # Layer 2: Machine Learning
        ml_result = self._ml_prediction(official_estimate, competitor_bids, market_conditions, historical_data)
        
        # Layer 3: Market Dynamics
        market = self._market_dynamics_analysis(official_estimate, market_conditions)
        
        # Layer 4: Competitor Behavior
        competitor = self._competitor_behavior_analysis(competitor_bids, historical_data)
        
        # Layer 5: Historical Patterns
        historical = self._historical_pattern_analysis(official_estimate, historical_data)
        
        # Layer 6: Risk Assessment
        risk = self._risk_assessment(official_estimate, statistical, competitor, risk_tolerance)
        
        # Combine all layers
        final_result = self._combine_results(
            statistical, ml_result, market, competitor, historical, risk,
            company_profile, risk_tolerance, official_estimate
        )
        
        return final_result
    
    def _get_default_market_conditions(self):
        current_month = datetime.now().month
        seasonality = {
            1: 1.02, 2: 1.01, 3: 0.99, 4: 0.98, 5: 0.97, 6: 0.95,
            7: 0.94, 8: 0.94, 9: 0.96, 10: 0.98, 11: 1.00, 12: 1.02
        }.get(current_month, 1.0)
        
        return {
            'market_index': 1.0,
            'seasonality': seasonality,
            'competition_level': 'medium',
            'competition_intensity': 0.5,
            'inflation_rate': 0.07,
            'material_cost_index': 1.05,
            'labor_cost_index': 1.08
        }
    
    def _get_default_company_profile(self):
        return {
            'strength': 'medium',
            'success_rate': 0.35,
            'project_experience': 'medium'
        }
    
    def _statistical_analysis(self, official_estimate, competitor_bids):
        if not competitor_bids or len(competitor_bids) < 2:
            mean_bid = official_estimate * 0.92
            std_dev = official_estimate * 0.05
            median_bid = mean_bid
        else:
            mean_bid = np.mean(competitor_bids)
            std_dev = np.std(competitor_bids)
            median_bid = np.median(competitor_bids)
        
        # Calculate optimal statistical bid
        if std_dev > 0:
            def expected_value(bid_ratio):
                bid = official_estimate * bid_ratio
                win_prob = 1 - stats.norm.cdf(bid, mean_bid, std_dev) if bid > mean_bid else 0.5
                profit = bid - (official_estimate * 0.85)
                return -win_prob * profit
            
            result = minimize_scalar(expected_value, bounds=(0.80, 0.98), method='bounded')
            statistical_optimal = official_estimate * result.x if result.success else mean_bid * 0.98
        else:
            statistical_optimal = mean_bid * 0.98
        
        # Detect outliers
        outliers = []
        adjusted_mean = mean_bid
        if len(competitor_bids) >= 4:
            z_scores = np.abs(stats.zscore(competitor_bids))
            outliers = [competitor_bids[i] for i in range(len(competitor_bids)) if z_scores[i] > 2]
            normal_bids = [competitor_bids[i] for i in range(len(competitor_bids)) if z_scores[i] <= 2]
            if normal_bids:
                adjusted_mean = np.mean(normal_bids)
        
        return {
            'mean_bid': mean_bid,
            'median_bid': median_bid,
            'std_dev': std_dev,
            'statistical_optimal': statistical_optimal,
            'adjusted_mean': adjusted_mean,
            'outliers': outliers
        }
    
    def _ml_prediction(self, official_estimate, competitor_bids, market_conditions, historical_data):
        if historical_data and len(historical_data) >= 10 and not self.is_trained:
            self._train_ml_model(historical_data)
        
        num_competitors = len(competitor_bids) if competitor_bids else 5
        avg_competitor_ratio = np.mean(competitor_bids) / official_estimate if competitor_bids else 0.92
        
        if self.is_trained and self.ml_model:
            features = np.array([[
                official_estimate, num_competitors,
                market_conditions.get('market_index', 1.0),
                market_conditions.get('seasonality', 1.0),
                avg_competitor_ratio
            ]])
            features_scaled = self.scaler.transform(features)
            ml_ratio = self.ml_model.predict(features_scaled)[0]
            ml_prediction = official_estimate * ml_ratio
            confidence = 0.75
        else:
            ml_ratio = 0.89
            ml_prediction = official_estimate * ml_ratio
            confidence = 0.60
        
        return {
            'ml_prediction': ml_prediction,
            'ml_ratio': ml_ratio,
            'confidence': confidence
        }
    
    def _train_ml_model(self, historical_data):
        try:
            X = []
            y = []
            for record in historical_data:
                if 'official_estimate' in record and 'winning_bid' in record:
                    features = [
                        record['official_estimate'],
                        record.get('num_competitors', 5),
                        record.get('market_index', 1.0),
                        record.get('seasonality', 1.0),
                        record.get('avg_competitor_ratio', 0.92)
                    ]
                    X.append(features)
                    y.append(record['winning_bid'] / record['official_estimate'])
            
            if len(X) >= 10:
                X_scaled = self.scaler.fit_transform(X)
                self.ml_model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
                self.ml_model.fit(X_scaled, y)
                self.is_trained = True
        except Exception as e:
            print(f"ML training error: {str(e)}")
    
    def _market_dynamics_analysis(self, official_estimate, market_conditions):
        seasonality = market_conditions.get('seasonality', 1.0)
        economic_factor = (1 + market_conditions.get('inflation_rate', 0.07)) * 1.05 * 1.08
        competition_levels = {'low': 1.02, 'medium': 1.00, 'high': 0.98, 'very_high': 0.95}
        competition_factor = competition_levels.get(market_conditions.get('competition_level', 'medium'), 1.0)
        
        market_multiplier = seasonality * economic_factor * competition_factor
        market_multiplier = np.clip(market_multiplier, 0.85, 1.15)
        
        return {
            'market_multiplier': market_multiplier,
            'adjusted_estimate': official_estimate * market_multiplier,
            'market_adjusted_bid': official_estimate * market_multiplier * 0.90
        }
    
    def _competitor_behavior_analysis(self, competitor_bids, historical_data):
        if not competitor_bids or len(competitor_bids) < 3:
            return {'aggressive_count': 0, 'conservative_count': 0, 'avg_aggressiveness': 0.5}
        
        # Simple clustering
        avg_bid = np.mean(competitor_bids)
        aggressive = [b for b in competitor_bids if b < avg_bid * 0.95]
        conservative = [b for b in competitor_bids if b > avg_bid * 1.05]
        
        return {
            'aggressive_count': len(aggressive),
            'conservative_count': len(conservative),
            'avg_aggressiveness': len(aggressive) / len(competitor_bids) if competitor_bids else 0.5,
            'sweet_spot': min(competitor_bids) * 0.99 if competitor_bids else None
        }
    
    def _historical_pattern_analysis(self, official_estimate, historical_data):
        if not historical_data or len(historical_data) < 5:
            return {'pattern_confidence': 0.3, 'historical_optimal_ratio': 0.89}
        
        similarities = []
        for record in historical_data:
            if 'official_estimate' in record and 'winning_bid' in record:
                value_sim = 1 - abs(np.log(official_estimate) - np.log(record['official_estimate'])) / 10
                value_sim = max(0, min(1, value_sim))
                similarities.append({
                    'similarity': value_sim,
                    'winning_ratio': record['winning_bid'] / record['official_estimate']
                })
        
        similar_tenders = sorted(similarities, key=lambda x: x['similarity'], reverse=True)[:5]
        if similar_tenders:
            total_weight = sum(s['similarity'] for s in similar_tenders)
            weighted_ratio = sum(s['winning_ratio'] * s['similarity'] for s in similar_tenders) / total_weight
        else:
            weighted_ratio = 0.89
        
        return {'historical_optimal_ratio': weighted_ratio}
    
    def _risk_assessment(self, official_estimate, statistical, competitor, risk_tolerance):
        mean_bid = statistical['mean_bid']
        std_dev = statistical['std_dev']
        
        var_95 = mean_bid - 1.645 * std_dev if std_dev > 0 else mean_bid * 0.85
        
        tolerance_multipliers = {
            'aggressive': 0.97, 'moderate': 1.00, 'conservative': 1.03
        }
        risk_multiplier = tolerance_multipliers.get(risk_tolerance, 1.0)
        
        competition_risk = min(80, competitor.get('aggressive_count', 0) * 20)
        total_risk = competition_risk * 0.5 + 30
        
        if total_risk < 30:
            risk_level = "LOW"
            risk_color = "🟢"
        elif total_risk < 60:
            risk_level = "MEDIUM"
            risk_color = "🟡"
        else:
            risk_level = "HIGH"
            risk_color = "🔴"
        
        return {
            'var_95': var_95,
            'risk_multiplier': risk_multiplier,
            'risk_score': total_risk,
            'risk_level': risk_level,
            'risk_color': risk_color
        }
    
    def _combine_results(self, statistical, ml, market, competitor, historical, risk,
                        company_profile, risk_tolerance, official_estimate):
        
        # Individual recommendations
        recommendations = {
            'statistical': statistical['statistical_optimal'],
            'ml': ml['ml_prediction'],
            'market': market['market_adjusted_bid'],
            'competitor': competitor.get('sweet_spot', statistical['mean_bid'] * 0.98),
            'historical': official_estimate * historical.get('historical_optimal_ratio', 0.89)
        }
        
        # Weighted average
        weights = {'statistical': 0.30, 'ml': 0.25, 'market': 0.15, 'competitor': 0.20, 'historical': 0.10}
        weighted_bid = sum(recommendations[k] * weights[k] for k in weights)
        
        # Apply risk adjustment
        final_bid = weighted_bid * risk['risk_multiplier']
        final_bid = np.clip(final_bid, official_estimate * 0.82, official_estimate * 0.96)
        
        # Calculate win probability
        mean_bid = statistical['mean_bid']
        std_dev = statistical['std_dev']
        if std_dev > 0:
            win_prob = 1 - stats.norm.cdf(final_bid, mean_bid, std_dev)
            win_prob = max(0.1, min(0.9, win_prob))
        else:
            win_prob = 0.55
        
        # Generate scenarios
        scenarios = {
            'aggressive': {'bid': final_bid * 0.97, 'win_probability': win_prob * 1.15, 'description': 'Higher win chance'},
            'moderate': {'bid': final_bid, 'win_probability': win_prob, 'description': 'Balanced approach'},
            'conservative': {'bid': final_bid * 1.03, 'win_probability': win_prob * 0.85, 'description': 'Higher profit'}
        }
        
        return {
            'optimal_bid': final_bid,
            'bid_ratio': final_bid / official_estimate,
            'win_probability': win_prob,
            'risk_level': risk['risk_level'],
            'risk_color': risk['risk_color'],
            'risk_score': risk['risk_score'],
            'recommended_min': final_bid * 0.97,
            'recommended_max': final_bid * 1.03,
            'scenarios': scenarios,
            'recommendations': recommendations,
            'has_ml': self.is_trained
        }