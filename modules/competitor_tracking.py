"""
Competitor Profile Tracking System
Tracks competitor behavior patterns over time for better predictions
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database.db_manager import DatabaseManager

db = DatabaseManager()

class CompetitorTracker:
    """Track and analyze competitor bidding patterns"""
    
    def __init__(self, company_id):
        self.company_id = company_id
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create competitor tracking tables if not exist"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Competitor profiles table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitor_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            competitor_name TEXT,
            competitor_type TEXT,
            first_seen DATE,
            last_seen DATE,
            total_appearances INTEGER DEFAULT 0,
            wins_count INTEGER DEFAULT 0,
            avg_bid_ratio REAL,
            bid_std_dev REAL,
            strategy TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id),
            UNIQUE(company_id, competitor_name)
        )
        ''')
        
        # Competitor bid history
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitor_bid_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            competitor_name TEXT,
            tender_id TEXT,
            bid_amount REAL,
            official_estimate REAL,
            bid_ratio REAL,
            was_winner BOOLEAN DEFAULT 0,
            bid_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def update_competitor_profile(self, competitor_name, bid_amount, official_estimate, was_winner=False, tender_id=None):
        """Update or create competitor profile with new bid data"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        bid_ratio = bid_amount / official_estimate
        
        # Check if competitor exists
        cursor.execute('''
        SELECT id, total_appearances, wins_count, avg_bid_ratio, bid_std_dev
        FROM competitor_profiles 
        WHERE company_id = ? AND competitor_name = ?
        ''', (self.company_id, competitor_name))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing profile
            comp_id, total, wins, avg_ratio, std_dev = existing
            new_total = total + 1
            new_wins = wins + (1 if was_winner else 0)
            
            # Update rolling average
            new_avg_ratio = (avg_ratio * total + bid_ratio) / new_total
            
            # Update standard deviation
            bids = self._get_competitor_bids(competitor_name)
            bids.append(bid_ratio)
            new_std_dev = np.std(bids) if len(bids) > 1 else 0
            
            # Determine strategy based on bid ratios
            if new_avg_ratio < 0.88:
                strategy = "Aggressive"
            elif new_avg_ratio < 0.92:
                strategy = "Moderate"
            else:
                strategy = "Conservative"
            
            cursor.execute('''
            UPDATE competitor_profiles 
            SET total_appearances = ?, wins_count = ?, avg_bid_ratio = ?, 
                bid_std_dev = ?, strategy = ?, last_seen = ?, updated_at = ?
            WHERE id = ?
            ''', (new_total, new_wins, new_avg_ratio, new_std_dev, strategy, 
                  datetime.now().date(), datetime.now(), comp_id))
        else:
            # Create new profile
            strategy = "Aggressive" if bid_ratio < 0.88 else "Moderate" if bid_ratio < 0.92 else "Conservative"
            cursor.execute('''
            INSERT INTO competitor_profiles 
            (company_id, competitor_name, first_seen, last_seen, total_appearances, 
             wins_count, avg_bid_ratio, bid_std_dev, strategy)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
            ''', (self.company_id, competitor_name, datetime.now().date(), 
                  datetime.now().date(), 1 if was_winner else 0, bid_ratio, 0, strategy))
        
        # Save bid history
        if tender_id:
            cursor.execute('''
            INSERT INTO competitor_bid_history 
            (company_id, competitor_name, tender_id, bid_amount, official_estimate, 
             bid_ratio, was_winner, bid_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.company_id, competitor_name, tender_id, bid_amount, 
                  official_estimate, bid_ratio, was_winner, datetime.now().date()))
        
        conn.commit()
        conn.close()
    
    def _get_competitor_bids(self, competitor_name):
        """Get all bid ratios for a competitor"""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT bid_ratio FROM competitor_bid_history 
        WHERE company_id = ? AND competitor_name = ?
        ORDER BY bid_date DESC
        ''', (self.company_id, competitor_name))
        bids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return bids
    
    def get_competitor_insights(self):
        """Get aggregated competitor insights"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT competitor_name, strategy, total_appearances, avg_bid_ratio, 
               wins_count, last_seen
        FROM competitor_profiles 
        WHERE company_id = ?
        ORDER BY total_appearances DESC
        ''', (self.company_id,))
        
        competitors = cursor.fetchall()
        conn.close()
        
        if not competitors:
            return None
        
        insights = {
            'total_competitors': len(competitors),
            'aggressive_count': len([c for c in competitors if c[1] == 'Aggressive']),
            'moderate_count': len([c for c in competitors if c[1] == 'Moderate']),
            'conservative_count': len([c for c in competitors if c[1] == 'Conservative']),
            'competitors': competitors,
            'avg_market_ratio': np.mean([c[3] for c in competitors]) if competitors else 0.90
        }
        
        return insights
    
    def predict_competitor_bid(self, competitor_name, official_estimate):
        """Predict what a specific competitor will bid"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT avg_bid_ratio, bid_std_dev, strategy
        FROM competitor_profiles 
        WHERE company_id = ? AND competitor_name = ?
        ''', (self.company_id, competitor_name))
        
        profile = cursor.fetchone()
        conn.close()
        
        if profile:
            avg_ratio, std_dev, strategy = profile
            # Add some randomness based on their historical variance
            random_factor = np.random.normal(0, std_dev * 0.5) if std_dev > 0 else 0
            predicted_ratio = avg_ratio + random_factor
            predicted_ratio = max(0.80, min(0.98, predicted_ratio))
            return official_estimate * predicted_ratio, strategy
        else:
            # Default prediction for unknown competitor
            return official_estimate * 0.90, "Unknown"

def get_competitor_strategy_insights(self):
    """Get detailed competitor strategy insights"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT competitor_name, strategy, avg_bid_ratio, total_appearances, wins_count,
           (wins_count * 1.0 / total_appearances) as win_rate
    FROM competitor_profiles 
    WHERE company_id = ? AND total_appearances >= 2
    ORDER BY total_appearances DESC
    ''', (self.company_id,))
    
    competitors = cursor.fetchall()
    conn.close()
    
    if not competitors:
        return None
    
    insights = {
        'total_tracked': len(competitors),
        'aggressive': [c for c in competitors if c[1] == 'Aggressive'],
        'moderate': [c for c in competitors if c[1] == 'Moderate'],
        'conservative': [c for c in competitors if c[1] == 'Conservative'],
        'high_win_rate': [c for c in competitors if c[5] > 0.5],
        'most_frequent': competitors[:5] if competitors else []
    }
    
    # Calculate market aggression index
    total_bids = sum(c[3] for c in competitors)
    aggressive_bids = sum(c[3] for c in competitors if c[1] == 'Aggressive')
    insights['market_aggression_index'] = aggressive_bids / total_bids if total_bids > 0 else 0.5
    
    return insights

def predict_competitor_behavior(self, competitor_name, official_estimate):
    """Enhanced competitor behavior prediction"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT avg_bid_ratio, bid_std_dev, strategy, total_appearances, wins_count
    FROM competitor_profiles 
    WHERE company_id = ? AND competitor_name = ?
    ''', (self.company_id, competitor_name))
    
    profile = cursor.fetchone()
    conn.close()
    
    if not profile:
        return {
            'predicted_bid': official_estimate * 0.91,
            'strategy': 'Unknown',
            'confidence': 0.40,
            'min_expected': official_estimate * 0.85,
            'max_expected': official_estimate * 0.96
        }
    
    avg_ratio, std_dev, strategy, appearances, wins = profile
    
    # Calculate confidence based on data points
    confidence = min(0.95, 0.50 + (appearances * 0.03))
    
    # Predict with confidence interval
    predicted_ratio = avg_ratio
    min_ratio = max(0.75, avg_ratio - (std_dev * 1.5))
    max_ratio = min(1.00, avg_ratio + (std_dev * 1.5))
    
    return {
        'predicted_bid': official_estimate * predicted_ratio,
        'strategy': strategy,
        'confidence': confidence,
        'appearances': appearances,
        'win_rate': wins / appearances if appearances > 0 else 0,
        'min_expected': official_estimate * min_ratio,
        'max_expected': official_estimate * max_ratio
    }

def render_competitor_tracking_page():
    """Render competitor tracking dashboard"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👥 Competitor Tracking</h1>
        <p>Track competitor behavior patterns for better bid predictions</p>
    </div>
    """, unsafe_allow_html=True)
    
    tracker = CompetitorTracker(st.session_state.company_id)
    insights = tracker.get_competitor_insights()
    
    if not insights:
        st.info("No competitor data yet. As you save analysis results, competitor profiles will be built automatically.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Competitors Tracked", insights['total_competitors'])
    with col2:
        st.metric("Aggressive Bidders", insights['aggressive_count'])
    with col3:
        st.metric("Moderate Bidders", insights['moderate_count'])
    with col4:
        st.metric("Conservative Bidders", insights['conservative_count'])
    
    st.markdown("### 📊 Competitor Profiles")
    
    competitors_df = pd.DataFrame(insights['competitors'], 
                                  columns=['Name', 'Strategy', 'Appearances', 'Avg Bid Ratio', 'Wins', 'Last Seen'])
    competitors_df['Avg Bid Ratio'] = competitors_df['Avg Bid Ratio'].apply(lambda x: f"{x*100:.1f}%")
    
    st.dataframe(competitors_df, use_container_width=True, hide_index=True)
    
    st.markdown("### 📈 Market Intelligence")
    st.info(f"💰 Average Market Bid Ratio: {insights['avg_market_ratio']*100:.1f}% of estimate")
    
    if insights['aggressive_count'] > insights['conservative_count']:
        st.warning("⚠️ Market is aggressive - consider more competitive pricing")
    elif insights['conservative_count'] > insights['aggressive_count']:
        st.success("✅ Market is conservative - room for better margins")