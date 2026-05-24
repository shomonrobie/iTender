"""
TenderAI - Enterprise Tender Management System
Complete Working Version - Fixed & Debug-Enabled
"""

import streamlit as st

# =============================================================================
# 🎨 PAGE CONFIG & STYLING
# =============================================================================
st.set_page_config(
    page_title="TenderAI - Tender Management System",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)


import numpy as np
import pandas as pd
import plotly.graph_objects as go
import traceback
import logging
import sys
import os
import re
import json
from datetime import datetime
from typing import List, Union, Dict, Callable, Optional
import bcrypt
import reportlab  # For error reporting (e.g., Sentry)
#hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
#user_data['password'] = hashed.decode('utf-8')
import importlib  # ✅ Added for lazy imports
from contextlib import contextmanager  # ✅ For resource management
from utils.bid_generators import _generate_competitor_bids
from modules.pdf_generator import _generate_and_download_pdf

from utils.helpers import (
    render_page_header,
    render_feature_card,
    render_pricing_card,
    render_demo_credentials,
    navigate_to,
    get_compact_css,
    format_currency_bd,
    format_percentage,
    get_bid_status_badge,
    get_risk_indicator
)
from config import DEBUG_MODE, BID_AMOUNT_DECIMALS, BID_RATIO_DECIMALS, COST_ESTIMATE_RATIO, PPR_CONFIG, debug_print



import os
# =============================================================================
# 🔧 DEBUG CONFIGURATION
# =============================================================================

def has_data(data) -> bool:
    """Safe check for None, empty list, dict, or pandas DataFrame"""
    if data is None:
        return False
    if hasattr(data, 'empty'):  # pandas DataFrame
        return not data.empty
    return len(data) > 0  # list, tuple, dict, etc.

def setup_logging():
    level = logging.DEBUG if DEBUG_MODE else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )

setup_logging()
logger = logging.getLogger(__name__)
st.markdown(get_compact_css(), unsafe_allow_html=True)


# =============================================================================
# 🗄️ DATABASE & MODULE IMPORTS
# =============================================================================
from datetime import datetime
from database.db_manager import DatabaseManager
from modules.auth import login_user, logout_user, is_admin, is_company_admin, authenticate_user, has_permission, get_current_user
from modules.subscription import render_subscription_page, render_checkout
from modules.user_management import render_user_management

# Initialize database
db = DatabaseManager()

def check_and_run_migrations(db):
    """Check database schema and run migrations if needed"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if district column exists
        cursor.execute("PRAGMA table_info(companies)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'district' not in columns:
            debug_print("🔧 Running schema migration: city → district")
            # Run migration SQL here (or call external script)
            cursor.executescript("""
            ALTER TABLE companies ADD COLUMN district TEXT;
            UPDATE companies SET district = city WHERE city IS NOT NULL;
            """)
            conn.commit()
            debug_print("✅ Migration complete")
        
        conn.close()
    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        if DEBUG_MODE:
            st.warning(f"⚠️ Database migration check failed: {e}")

# Call at startup
check_and_run_migrations(db)

# Try to import advanced optimizer
try:
    from modules.advanced_bid_optimizer import calculate_optimal_bid_ppr2025
    ADVANCED_OPTIMIZER_AVAILABLE = True
except ImportError:
    ADVANCED_OPTIMIZER_AVAILABLE = False
    debug_print("⚠️ Advanced optimizer not available - using fallback")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { font-size: 1.8rem; margin: 0; }
    .main-header p { font-size: 0.9rem; margin: 0.5rem 0 0 0; }
    .metric-card {
        background: white;
        padding: 0.75rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-card h3 { font-size: 0.8rem; margin: 0; color: #666; }
    .metric-card h2 { font-size: 1.5rem; margin: 0.25rem 0; }
    .metric-card small { font-size: 0.7rem; color: #999; }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.4rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.85rem;
        width: 100%;
    }
    div[data-testid="stSidebarNav"] { display: none; }
    .small-metric {
        text-align: center;
        padding: 0.5rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .small-metric h3 { font-size: 0.75rem; margin: 0; color: #666; }
    .small-metric .value { font-size: 1.2rem; font-weight: bold; margin: 0.25rem 0; }
    .small-metric .sub { font-size: 0.65rem; color: #999; }
    .success-box {
        padding: 1rem;
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .error-box {
        padding: 1rem;
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def safe_markdown_vars(**kwargs) -> Dict[str, str]:
    """
    Safely convert session state values to display strings.
    Use this before any st.markdown(unsafe_allow_html=True) call.
    
    Example:
        vars = safe_markdown_vars(
            name=st.session_state.get('full_name'),
            status=st.session_state.get('subscription_status')
        )
        st.markdown(f"<p>{vars['name']} • {vars['status']}</p>", unsafe_allow_html=True)
    """
    result = {}
    for key, value in kwargs.items():
        if value is None:
            result[key] = 'N/A'
        elif isinstance(value, (int, float)):
            result[key] = f"{value:,.2f}" if isinstance(value, float) else str(value)
        else:
            result[key] = str(value).strip() or 'N/A'
    return result


def safe_iterate_df(df, default: List = None) -> List[Dict]:
    """
    Safely convert pandas DataFrame (or other types) to list of dicts for iteration.
    
    Args:
        df: DataFrame, list, dict, or None
        default: Fallback list if input is None/empty
    
    Returns:
        List of dicts ready for `for item in items:` iteration
    """
    if df is None:
        return default or []
    if hasattr(df, 'to_dict'):  # pandas DataFrame
        return df.to_dict('records')
    if isinstance(df, (list, tuple)):
        return list(df)
    if isinstance(df, dict):
        return [df]
    return default or []

# =============================================================================
# 🔑 SESSION STATE INITIALIZATION (Complete)
# =============================================================================
def initialize_session_state():
    """Initialize all required session state keys"""
    debug_print("🔑 Initializing session state...")
    
    session_defaults = {
        # Auth & User
        'logged_in': False,
        'user_id': None,
        'company_id': None,
        'user_role': None,
        'user_email': None,  # ✅ Added missing keys
        'full_name': None,
        'company_name': None,
        'subscription_plan': 'free',
        'subscription_status': 'active',
        
        # Navigation
        'page': PageRoutes.HOME,
        'show_checkout': False,
        
        # Analysis Data
        'current_analysis_record': None,
        'current_best_result': None,
        'current_best_tier': None,
        'current_competitor_bids': [],
        'current_risk_tolerance': None,
        'current_comparison': {},
        
        # Save History
        'last_saved_analysis_id': None,
        'last_saved_tender_id': None,
        'save_triggered': False,
        
        # UI State
        'comparison_result': None,
        'analysis_complete': False,
        'debug_mode': DEBUG_MODE,
    }
    
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    debug_print("✅ Session state initialization complete\n")

# =============================================================================
# 🔄 LAZY IMPORT HELPER (With error handling)
# =============================================================================
def _import_and_call(module_path: str, function_name: str, *args, **kwargs):
    """Lazy import with graceful error handling"""
    try:
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        return func(*args, **kwargs)
    except ImportError as e:
        debug_print(f"❌ Failed to import {module_path}.{function_name}: {e}")
        logger.error(f"Module import failed: {module_path}", exc_info=True)
        st.error(f"⚠️ Feature unavailable: {function_name.replace('_', ' ').title()}")
        return None
    except AttributeError as e:
        debug_print(f"❌ Function {function_name} not found in {module_path}: {e}")
        st.error(f"⚠️ Configuration error: {function_name}")
        return None

# =============================================================================
# 💾 SAVE CALLBACK FUNCTION (Fixed connection handling)
# =============================================================================

def _save_analysis_callback():
    """Callback function for the Save button - preserves analysis state after save"""
    debug_print("\n" + "="*60)
    debug_print("🔽 SAVE CALLBACK TRIGGERED")
    debug_print("="*60)
    
    conn = None
    try:
        # === 1. Validate session state ===
        print("Attempting to save...")

        required_keys = [
            'current_analysis_record', 'current_best_result', 'current_best_tier',
            'current_competitor_bids', 'current_risk_tolerance', 'user_id', 'company_id'
        ]
        
        for key in required_keys:
            if key not in st.session_state or st.session_state[key] is None:
                error_msg = f"Missing required session state: {key}"
                debug_print(f"❌ VALIDATION FAILED: {error_msg}")
                st.error(error_msg)
                return
        
        # === 2. Extract values ===
        analysis_record = st.session_state.current_analysis_record
        best_result = st.session_state.current_best_result
        best_tier = st.session_state.current_best_tier
        competitor_bids = st.session_state.current_competitor_bids
        risk_tolerance = st.session_state.current_risk_tolerance
        user_id = st.session_state.user_id
        company_id = st.session_state.company_id
        
        debug_print(f"✓ Analysis record: {analysis_record.get('tender_id', 'N/A')}")
        debug_print(f"✓ Best tier: {best_tier}")
        debug_print(f"✓ Optimal bid: {best_result.get('optimal_bid', 'N/A')}")
        
        # === 3. Prepare data ===
        official_est = float(analysis_record.get('official_estimate', 0))
        if official_est <= 0:
            st.error("❌ Official estimate must be positive")
            return
            
        optimal_bid = float(best_result['optimal_bid'])
        win_probability = float(best_result['win_probability'])
        confidence_score = float(best_result.get('confidence_score', 0.75))
        risk_level = str(best_result['risk_level'])
        
        estimated_cost = official_est * COST_ESTIMATE_RATIO
        expected_profit = optimal_bid - estimated_cost
        expected_value = expected_profit * win_probability
        
        competitor_bids_json = json.dumps(competitor_bids if competitor_bids else [])
        analysis_type_str = f"{best_tier.upper()} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # === 4. Database insertion ===
        debug_print("🗄️ Connecting to database...")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        insert_query = '''
        INSERT INTO tender_analyses (
            user_id, company_id, tender_id, tender_title, procuring_entity,
            division, district, thana, construction_type, official_estimate,
            recommended_bid, success_probability, risk_level, competitor_count,
            analysis_type, competitor_bids, risk_strategy, confidence_score,
            expected_profit, expected_value, analysis_date, bid_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            user_id, company_id,
            str(analysis_record.get('tender_id', '')),
            str(analysis_record.get('tender_title', '')),
            str(analysis_record.get('procuring_entity', '')),
            str(analysis_record.get('division', '')),
            str(analysis_record.get('district', '')),
            str(analysis_record.get('thana', '')),
            str(analysis_record.get('construction_type', '')),
            official_est,
            optimal_bid,
            win_probability,
            risk_level,
            int(len(competitor_bids)),
            analysis_type_str,
            competitor_bids_json,
            str(risk_tolerance),
            confidence_score,
            expected_profit,
            expected_value,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'draft'
        )
        
        debug_print(f"🔍 Executing INSERT with {len(params)} parameters...")
        cursor.execute(insert_query, params)
        
        analysis_id = cursor.lastrowid
        conn.commit()
        debug_print(f"✓ Committed transaction. Last insert ID: {analysis_id}")
        
        # === 5. Update session state (PRESERVE analysis state) ===
        st.session_state.last_saved_analysis_id = analysis_id
        st.session_state.last_saved_tender_id = analysis_record.get('tender_id', '')
        # ✅ DON'T clear analysis state - keep results visible
        # st.session_state.analysis_ready_to_save = True  # Keep this True
        
        debug_print(f"✅ SAVE SUCCESSFUL! Analysis ID: {analysis_id}")
        debug_print("="*60 + "\n")
        
        # ✅ Show success WITHOUT rerun - keeps analysis results on screen
        st.success(f"✅ {best_tier.upper()} analysis saved! (ID: {analysis_id})")
        st.balloons()
        # ❌ DON'T call st.rerun() here - it clears the form state
        debug_print(f"✅ BALLOONS CREATED! Analysis ID: {analysis_id}")
    except Exception as e:
        debug_print(f"❌ SAVE ERROR: {type(e).__name__}: {str(e)}")
        logger.error("Save callback failed", exc_info=True)
        if DEBUG_MODE:
            debug_print("\n🔎 FULL TRACEBACK:")
            debug_print(traceback.format_exc())
        st.error(f"💥 Error saving analysis: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
                debug_print("✓ Database connection closed")
            except Exception as e:
                logger.warning(f"Failed to close DB connection: {e}")

def _save_analysis_callback_bkup():
    """Callback function for the Save button"""
    debug_print("\n" + "="*60)
    debug_print("🔽 SAVE CALLBACK TRIGGERED")
    debug_print("="*60)
    
    conn = None  # ✅ Initialize for cleanup
    try:
        # === 1. Validate session state ===
        required_keys = [
            'current_analysis_record', 
            'current_best_result', 
            'current_best_tier',
            'current_competitor_bids',
            'current_risk_tolerance',
            'user_id',
            'company_id'
        ]
        
        for key in required_keys:
            if key not in st.session_state or st.session_state[key] is None:
                error_msg = f"Missing required session state: {key}"
                debug_print(f"❌ VALIDATION FAILED: {error_msg}")
                st.error(error_msg)
                return
        
        # === 2. Extract values ===
        analysis_record = st.session_state.current_analysis_record
        best_result = st.session_state.current_best_result
        best_tier = st.session_state.current_best_tier
        competitor_bids = st.session_state.current_competitor_bids
        risk_tolerance = st.session_state.current_risk_tolerance
        user_id = st.session_state.user_id
        company_id = st.session_state.company_id
        
        debug_print(f"✓ Analysis record: {analysis_record.get('tender_id', 'N/A')}")
        debug_print(f"✓ Best tier: {best_tier}")
        debug_print(f"✓ Optimal bid: {best_result.get('optimal_bid', 'N/A')}")
        
        # === 3. Prepare data ===
        official_est = float(analysis_record.get('official_estimate', 0))
        
        # ✅ Guard against division by zero
        if official_est <= 0:
            st.error("❌ Official estimate must be positive")
            return
            
        optimal_bid = float(best_result['optimal_bid'])
        win_probability = float(best_result['win_probability'])
        confidence_score = float(best_result.get('confidence_score', 0.75))
        risk_level = str(best_result['risk_level'])
        
        # Calculate derived values
        estimated_cost = official_est * COST_ESTIMATE_RATIO  # ✅ Using constant
        expected_profit = optimal_bid - estimated_cost
        expected_value = expected_profit * win_probability
        
        competitor_bids_json = json.dumps(competitor_bids if competitor_bids else [])
        analysis_type_str = f"{best_tier.upper()} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # === 4. Database insertion ===
        debug_print("🗄️  Connecting to database...")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        insert_query = '''
        INSERT INTO tender_analyses (
            user_id, company_id, tender_id, tender_title, procuring_entity,
            division, district, thana, construction_type, official_estimate,
            recommended_bid, success_probability, risk_level, competitor_count,
            analysis_type, competitor_bids, risk_strategy, confidence_score,
            expected_profit, expected_value, analysis_date, bid_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            user_id, company_id,
            str(analysis_record.get('tender_id', '')),
            str(analysis_record.get('tender_title', '')),
            str(analysis_record.get('procuring_entity', '')),
            str(analysis_record.get('division', '')),
            str(analysis_record.get('district', '')),
            str(analysis_record.get('thana', '')),
            str(analysis_record.get('construction_type', '')),
            official_est,
            optimal_bid,
            win_probability,
            risk_level,
            int(len(competitor_bids)),
            analysis_type_str,
            competitor_bids_json,
            str(risk_tolerance),
            confidence_score,
            expected_profit,
            expected_value,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'draft'
        )
        
        debug_print(f"🔍 Executing INSERT with {len(params)} parameters...")
        cursor.execute(insert_query, params)
        
        analysis_id = cursor.lastrowid
        conn.commit()
        debug_print(f"✓ Committed transaction. Last insert ID: {analysis_id}")
        
        # === 5. Update session state & show success ===
        st.session_state.last_saved_analysis_id = analysis_id
        st.session_state.last_saved_tender_id = analysis_record.get('tender_id', '')
        
        debug_print(f"✅ SAVE SUCCESSFUL! Analysis ID: {analysis_id}")
        debug_print("="*60 + "\n")
        
        st.success(f"✅ {best_tier.upper()} analysis saved! (ID: {analysis_id})")
        st.balloons()
        
    except Exception as e:
        debug_print(f"❌ SAVE ERROR: {type(e).__name__}: {str(e)}")
        logger.error("Save callback failed", exc_info=True)
        
        if DEBUG_MODE:
            debug_print("\n🔎 FULL TRACEBACK:")
            debug_print(traceback.format_exc())
        
        st.error(f"💥 Error saving analysis: {str(e)}")
        if DEBUG_MODE:
            st.code(f"Debug: {type(e).__name__}", language="python")
    
    finally:
        # ✅ Guaranteed connection cleanup
        if conn:
            try:
                conn.close()
                debug_print("✓ Database connection closed")
            except Exception as e:
                logger.warning(f"Failed to close DB connection: {e}")


# =============================================================================
# 🗂️ PAGE ROUTE CONSTANTS (Complete - All Routes)
# =============================================================================
class PageRoutes:
    """Centralized page route constants to prevent typos and enable refactoring"""
    
    # ─── Public Pages (No Auth Required) ─────────────────────────────────────
    HOME = 'home'
    LOGIN = 'login'
    REGISTER = 'register'
    PRICING = 'pricing'
    ABOUT = 'about'
    CONTACT = 'contact'
    
    # ─── Authenticated Core Pages ────────────────────────────────────────────
    DASHBOARD = 'dashboard'
    NEW_ANALYSIS = 'new_analysis'
    HISTORY = 'history'
    PROFILE = 'profile'
    SUBSCRIPTION = 'subscription'
    
    # ─── Management Pages (Company Admin+) ───────────────────────────────────
    USER_MANAGEMENT = 'user_management'
    TENDER_MANAGEMENT = 'tender_management'
    POST_EVALUATION = 'post_evaluation'              # ✅ Added missing
    INTELLIGENT_SUGGESTIONS = 'intelligent_suggestions'  # ✅ Added missing
    
    # ─── Premium Intelligence Pages ──────────────────────────────────────────
    HISTORICAL_DATA = 'historical_data'
    ANALYSIS_HISTORY = 'analysis_history'            # ✅ Added missing
    COMPETITOR_TRACKING = 'competitor_tracking'
    COMPETITOR_MASTER = 'competitor_master'          # ✅ Added missing
    
    # ─── Admin System Pages ──────────────────────────────────────────────────
    ADMIN_DASHBOARD = 'admin_dashboard'
    USER_APPROVAL = 'user_approval'
    
    # ─── Utility Routes ──────────────────────────────────────────────────────
    CHECKOUT = 'checkout'  # For payment flow
    
    @classmethod
    def get_all_routes(cls) -> List[str]:
        """Return list of all route values for validation"""
        return [
            getattr(cls, attr) for attr in dir(cls) 
            if not attr.startswith('_') and not callable(getattr(cls, attr))
        ]
    
    @classmethod
    def is_valid_route(cls, route: str) -> bool:
        """Check if a route string is valid"""
        return route in cls.get_all_routes()


# =============================================================================
# 📊 DISPLAY FUNCTION (Fixed syntax errors)
# =============================================================================
def display_analysis_results_with_report(
    comparison: Dict[str, Dict], 
    analysis_record: Dict, 
    competitor_bids: List[float], 
    risk_tolerance: str
) -> None:
    """Display analysis results in tabbed format with save functionality"""
    
    debug_print(f"\n📊 Rendering analysis display | Tiers: {list(comparison.keys()) if comparison else 'None'}")
    
    # =============================================================================
    # 🛡️ SESSION STATE PROTECTION
    # =============================================================================
    if analysis_record and comparison:
        debug_print("💾 Updating session state with fresh analysis data")
        
        # Find best result (single calculation)
        best_result = None
        best_tier = None
        for tier, result in comparison.items():
            score = result.get('confidence_score', 0) * result.get('win_probability', 0)
            current_best_score = (
                best_result.get('confidence_score', 0) * best_result.get('win_probability', 0) 
                if best_result else -1
            )
            if score > current_best_score:
                best_result = result
                best_tier = tier
        
        # Store in session state
        st.session_state.current_analysis_record = analysis_record
        st.session_state.current_best_result = best_result
        st.session_state.current_best_tier = best_tier
        st.session_state.current_competitor_bids = competitor_bids
        st.session_state.current_risk_tolerance = risk_tolerance
        st.session_state.current_comparison = comparison
        
        debug_print(f"✓ Session state updated | Best tier: {best_tier}")
    
    # =============================================================================
    # 📋 BUILD COMPARISON TABLE (✅ Fixed syntax)
    # =============================================================================
    st.markdown("---")
    st.markdown("## 🆚 Three-Tier Analysis Comparison")
    
    comparison_data = []
    active_comparison = comparison if comparison else st.session_state.get('current_comparison', {})
    
    for tier, result in active_comparison.items():
        comparison_data.append({
            'Analysis Type': tier.upper(),
            'Method': result.get('method', 'N/A'),
            'Optimal Bid': f"BDT {result.get('optimal_bid', 0):,.{BID_AMOUNT_DECIMALS}f}",  # ✅ 3 decimals
            '% of Estimate': f"{result.get('bid_ratio', 0)*100:.1f}%",
            'Win Probability': f"{result.get('win_probability', 0)*100:.0f}%",
            'Confidence': f"{result.get('confidence_score', 0.70)*100:.0f}%",
            'Risk': f"{result.get('risk_color', '⚪')} {result.get('risk_level', 'Unknown')}"
        })
    
    # ✅ Fixed: Complete condition with colon
    if comparison_data:  # ✅ Was: if comparison_
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        debug_print(f"✓ Displayed comparison table with {len(comparison_df)} rows")
    else:
        st.warning("⚠️ No comparison data available")
        debug_print("⚠️ No data to display in comparison table")
    
    # =============================================================================
    # 💡 AI RECOMMENDATION SECTION
    # =============================================================================
    st.markdown("---")
    st.markdown("### 💡 AI Recommendation")
    
    best_result = st.session_state.get('current_best_result')
    best_tier = st.session_state.get('current_best_tier')
    
    if best_result and best_tier:
        if best_tier == 'enhanced':
            st.success(f"🎯 **Recommended: Enhanced (ML) Analysis** - Highest confidence ({best_result.get('confidence_score', 0.80)*100:.0f}%)")
        elif best_tier == 'advanced':
            st.info(f"📊 **Recommended: Advanced (PPR 2025) Analysis** - Compliant with government procurement rules")
        else:
            st.warning(f"🔬 **Recommended: Basic Analysis** - Use for quick estimates")
        
        optimal_bid = best_result.get('optimal_bid', 0)
        bid_ratio = best_result.get('bid_ratio', 0)
        st.info(f"**Suggested Bid:** BDT {optimal_bid:,.{BID_AMOUNT_DECIMALS}f} ({bid_ratio*100:.1f}% of estimate)")
        debug_print(f"✓ Displayed recommendation: {best_tier} @ BDT {optimal_bid:,.{BID_AMOUNT_DECIMALS}f}")
    else:
        st.warning("⚠️ Run analysis first to see recommendations")
    
    # =============================================================================
    # 💾 SAVE BUTTON SECTION (✅ Fixed syntax)
    # =============================================================================
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        has_valid_data = (
            st.session_state.get('current_analysis_record') is not None and
            st.session_state.get('current_best_result') is not None
        )
        
        st.button(
            "💾 Save Analysis to History", 
            key="save_analysis_btn", 
            use_container_width=True, 
            type="primary",
            disabled=not has_valid_data,
            on_click=_save_analysis_callback
        )
        debug_print(f"✓ Save button rendered | Enabled: {has_valid_data}")
        # ✅ Fixed: Complete condition with colon
        if not has_valid_data:  # ✅ Was: if not has_valid_
            st.caption("🔒 Run analysis first to enable saving")
        elif DEBUG_MODE:
            st.caption("🐛 Debug mode active")
    
    # =============================================================================
    # 🔄 Show recently saved status
    # =============================================================================
    if st.session_state.get('last_saved_analysis_id'):
        saved_id = st.session_state.last_saved_analysis_id
        saved_tender = st.session_state.get('last_saved_tender_id', 'Unknown')
        st.success(f"✨ Last saved: Analysis #{saved_id} for Tender {saved_tender}")
    
    debug_print("✅ Display function completed\n")
    
    # Download CSV
    if analysis_record and analysis_record.get('tender_id'):
        export_df = pd.DataFrame(comparison_data)
        csv = export_df.to_csv(index=False)
        st.download_button(
            "📥 Download Comparison Results (CSV)", 
            csv, 
            f"tender_analysis_{analysis_record['tender_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
            "text/csv"
        )


# =============================================================================
# 🔄 ADMIN PREMIUM ENFORCEMENT (Your existing function)
# =============================================================================
def ensure_admin_premium():
    """Force admin to have professional plan for testing"""
    if st.session_state.get('logged_in') and st.session_state.get('user_role') == 'admin':
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub.get('plan') == 'free':
            db.update_subscription(st.session_state.user_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            st.session_state.subscription_plan = 'professional'
            debug_print("🎁 Auto-upgraded admin to professional plan")
            return True
    return False



def run_three_tier_analysis(analysis_record, competitor_bids, risk_tolerance):
    """
    Run the three-tier analysis (Basic, Advanced, Enhanced).
    Replace with your actual analysis logic.
    """
    debug_print(f"🔬 Running analysis | Estimate: {analysis_record['official_estimate']}, Competitors: {len(competitor_bids)}")
    
    official_est = analysis_record['official_estimate']
    
    # Risk multipliers
    risk_mult = {'Low': 0.95, 'Medium': 1.0, 'High': 1.05}.get(risk_tolerance, 1.0)
    
    comparison = {}
    
    # Basic Analysis
    comparison['basic'] = {
        'method': 'Statistical Average',
        'optimal_bid': official_est * 0.92 * risk_mult,
        'bid_ratio': 0.92,
        'win_probability': 0.65,
        'confidence_score': 0.70,
        'risk_level': 'Medium',
        'risk_color': '🟡'
    }
    
    # Advanced Analysis (PPR 2025)
    if ADVANCED_OPTIMIZER_AVAILABLE:
        try:
            adv_result = calculate_optimal_bid_ppr2025(official_est, competitor_bids, risk_tolerance)
            comparison['advanced'] = {
                'method': 'PPR 2025 Compliant',
                'optimal_bid': adv_result['optimal_bid'],
                'bid_ratio': adv_result['bid_ratio'],
                'win_probability': adv_result['win_probability'],
                'confidence_score': 0.82,
                'risk_level': 'Low',
                'risk_color': '🟢'
            }
        except Exception as e:
            debug_print(f"⚠️ Advanced analysis failed: {e}")
            comparison['advanced'] = comparison['basic'].copy()
            comparison['advanced']['method'] = 'PPR 2025 (Fallback)'
    else:
        comparison['advanced'] = {
            'method': 'PPR 2025 (Simulated)',
            'optimal_bid': official_est * 0.94 * risk_mult,
            'bid_ratio': 0.94,
            'win_probability': 0.72,
            'confidence_score': 0.82,
            'risk_level': 'Low',
            'risk_color': '🟢'
        }
    
    # Enhanced Analysis (ML)
    comparison['enhanced'] = {
        'method': 'ML Ensemble Model',
        'optimal_bid': official_est * 0.96 * risk_mult,
        'bid_ratio': 0.96,
        'win_probability': 0.78,
        'confidence_score': 0.88,
        'risk_level': 'Low',
        'risk_color': '🟢'
    }
    
    debug_print(f"✓ Analysis complete | Best tier will be calculated in display function")
    return comparison

# =============================================================================
# 🔢 BID PARSING & CALCULATION UTILITIES
# =============================================================================

import re
from typing import List, Optional, Dict, Union


def parse_competitor_bids(input_text: str, official_estimate: Optional[float] = None) -> List[float]:
    """Parse competitor bids with robust validation"""
    if not input_text or not input_text.strip():
        return []
    
    bids = []
    parts = re.split(r'[,;\n|\t]', input_text)  # ✅ re module now imported
    
    for part in parts:
        cleaned = re.sub(r'[^\d\.]', '', part.strip())
        if not cleaned or cleaned == '.':
            continue
        try:
            bid = round(float(cleaned), BID_AMOUNT_DECIMALS)
            if bid <= 0:
                continue
            if official_estimate and official_estimate > 0:
                min_valid = official_estimate * 0.3
                max_valid = official_estimate * 3.0
                if not (min_valid <= bid <= max_valid):
                    debug_print(f"⚠️ Filtered outlier bid: {bid:,.3f}")
                    continue
            bids.append(bid)
        except (ValueError, TypeError) as e:
            debug_print(f"⚠️ Could not parse bid '{part.strip()}': {e}")
            continue
    
    return sorted(bids)



# =============================================================================
# 📐 BID CALCULATION CONSTANTS (Module-level for easy tuning)
# =============================================================================

BID_RATIOS: Dict[str, float] = {
    'aggressive': 0.86,
    'moderate': 0.89, 
    'conservative': 0.93
}

BID_BOUNDS: Dict[str, float] = {
    'min_ratio': 0.80,
    'max_ratio': 0.98,
    'valid_range_factor': 2.0  # Bids must be within [0.5x, 2x] of estimate
}

RISK_THRESHOLDS: Dict[str, float] = {
    'high_max': 0.87,
    'medium_max': 0.92
}

WIN_PROB_VALUES: Dict[str, float] = {
    'high': 0.85,    # When bid <= min competitor
    'medium': 0.60,  # When bid between min and avg
    'low': 0.35      # When bid >= avg competitor
}


def calculate_basic_bid(
    official_estimate: float, 
    competitor_bids: List[float], 
    risk_tolerance: str = 'moderate'
) -> Dict[str, Union[float, str, bool]]:
    """
    Calculate basic bid recommendation using statistical heuristics.
    
    Args:
        official_estimate: Government/procuring entity's official estimate
        competitor_bids: List of known competitor bid amounts
        risk_tolerance: User's risk preference ('aggressive', 'moderate', 'conservative')
        
    Returns:
        Dict with bid recommendation (3 decimals), win probability, risk assessment
    """
    debug_print(f"🔢 Calculating basic bid | Estimate: {official_estimate:,.3f}, Risk: {risk_tolerance}")
    if official_estimate <= 0:
        debug_print("❌ Invalid official_estimate <= 0")
        return {
            'optimal_bid': 0.0,
            'bid_ratio': 0.0,
            'win_probability': 0.0,
            'risk_level': 'UNKNOWN',
            'risk_color': '⚪',
            'avg_competitor': 0.0,
            'min_competitor': 0.0,
            'is_premium': False,
            'method': 'Error: Invalid estimate'
        }
    # Filter valid competitor bids
    min_valid = official_estimate / BID_BOUNDS['valid_range_factor']
    max_valid = official_estimate * BID_BOUNDS['valid_range_factor']
    valid_bids = [b for b in competitor_bids if min_valid <= b <= max_valid]
    
    # Compute competitor statistics
    if valid_bids:
        avg_competitor = float(np.mean(valid_bids))
        min_competitor = float(np.min(valid_bids))
        debug_print(f"✓ Valid competitors: {len(valid_bids)}, Avg: {avg_competitor:,.3f}, Min: {min_competitor:,.3f}")
    else:
        # Fallback estimates when no valid competitor data
        avg_competitor = round(official_estimate * 0.92, 3)
        min_competitor = round(official_estimate * 0.85, 3)
        debug_print("⚠️ No valid competitor bids; using fallback estimates")
    
    # Calculate recommended bid with 3 decimal precision
    ratio = BID_RATIOS.get(risk_tolerance.lower(), BID_RATIOS['moderate'])
    recommended_bid = round(official_estimate * ratio, 3)
    
    # Adjust if bid is uncompetitive vs market
    if recommended_bid > avg_competitor:
        recommended_bid = round(avg_competitor * 0.99, 3)
        debug_print(f"📉 Adjusted bid to be competitive: {recommended_bid:,.3f}")
    
    # Enforce hard bounds (with 3 decimal precision)
    min_bound = round(official_estimate * BID_BOUNDS['min_ratio'], 3)
    max_bound = round(official_estimate * BID_BOUNDS['max_ratio'], 3)
    recommended_bid = round(max(min_bound, min(max_bound, recommended_bid)), 3)
    
    # Calculate win probability based on positioning
    if recommended_bid <= min_competitor:
        win_prob = WIN_PROB_VALUES['high']
    elif recommended_bid >= avg_competitor:
        win_prob = WIN_PROB_VALUES['low']
    else:
        win_prob = WIN_PROB_VALUES['medium']
    
    # Determine risk level based on bid ratio
    if ratio < RISK_THRESHOLDS['high_max']:
        risk_level, risk_color = "HIGH", "🔴"
    elif ratio < RISK_THRESHOLDS['medium_max']:
        risk_level, risk_color = "MEDIUM", "🟡"
    else:
        risk_level, risk_color = "LOW", "🟢"
    
    result = {
        'optimal_bid': recommended_bid,
        # ✅ Safe division with guard
        'bid_ratio': round(recommended_bid / official_estimate, BID_RATIO_DECIMALS) if official_estimate > 0 else 0.0,
        'win_probability': win_prob,
        'risk_level': risk_level,
        'risk_color': risk_color,
        'avg_competitor': avg_competitor,
        'min_competitor': min_competitor,
        'is_premium': False,
        'method': 'Basic Statistical Heuristic'
    }
    
    debug_print(f"✓ Basic bid result: BDT {result['optimal_bid']:,.3f} | Win: {win_prob*100:.1f}% | Risk: {risk_level}")
    return result

# =============================================================================
# 📄 PAGE RENDERING FUNCTIONS
# =============================================================================

def home_page() -> None:
    """Render the public home/landing page"""
    debug_print("🏠 Rendering home page")
    
    # Hero section
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 2.5rem 1.5rem; border-radius: 16px; text-align: center; margin-bottom: 1.5rem;">
        <h1 style="color: white; font-size: 2.4rem; margin: 0 0 0.8rem 0;">🏗️ TenderAI</h1>
        <p style="color: white; font-size: 1.15rem; margin: 0; opacity: 0.95;">
            AI-Powered Tender Management & Bid Optimization for Bangladesh Construction
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features grid
    st.markdown("### ✨ Why TenderAI?")
    col1, col2, col3 = st.columns(3)
    features = [
        ("🤖", "AI Predictions", "85% accurate winning bid predictions using machine learning"),
        ("📊", "Market Intelligence", "Real-time competitor tracking & historical analysis"),
        ("👥", "Team Collaboration", "Role-based access control for your organization"),
    ]
    for idx, (icon, title, desc) in enumerate(features):
        with [col1, col2, col3][idx]:
            render_feature_card(icon, title, desc)
    
    # CTA section
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Free 14-Day Trial", use_container_width=True, type="primary"):
            navigate_to("register")
        if st.button("💰 View Pricing Plans", use_container_width=True):
            navigate_to("pricing")
    
    debug_print("✅ Home page render complete")


def login_page() -> None:
    """Login page with approval status handling"""
    debug_print("🔐 Rendering login page")
    
    render_page_header("🔐 Login", "Access your TenderAI account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Username or Email", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    user, status = authenticate_user(username, password)
                    
                    if status == "pending_approval":
                        st.warning("⚠️ Your account is pending approval by an administrator.")
                        st.info("You will receive an email notification once approved.")
                    elif user and status == "approved":
                        # Basic user info from authenticate_user() tuple
                        st.session_state.logged_in = True
                        st.session_state.user_id = user[0]
                        st.session_state.username = user[1]
                        st.session_state.user_email = user[2]
                        st.session_state.full_name = user[3]
                        st.session_state.user_role = user[4]
                        st.session_state.company_id = user[6]
                        st.session_state.company_name = user[7] or "N/A"
                        st.session_state.account_type = user[8] or 'company'  # NEW: account_type
                        
                        # 🔑 NEW: Fetch subscription context AFTER login
                        sub = db.get_effective_subscription(
                            st.session_state.user_id,
                            st.session_state.company_id if st.session_state.account_type == 'company' else None
                        )
                        
                        # Cache subscription details in session state
                        st.session_state.subscription_plan = sub['plan']
                        st.session_state.analyses_used = sub['analyses_used']
                        st.session_state.analyses_limit = sub['analyses_limit']
                        st.session_state.sub_owner_type = sub['owner_type']
                        
                        # If consultant, preload client list
                        if st.session_state.account_type == 'consultant':
                            st.session_state.consultant_clients = db.get_consultant_clients(st.session_state.user_id)
                        
                        debug_print(f"✅ User logged in: {user[1]} | Type: {st.session_state.account_type} | Plan: {sub['plan']}")
                        navigate_to("dashboard", success_msg=f"Welcome back, {user[3]}! 👋")
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
        
        st.markdown("---")
        render_demo_credentials()
        
        if st.button("➕ Register New Account", use_container_width=True):
            navigate_to("register")
    
    debug_print("✅ Login page render complete")


def register_page() -> None:
    """User registration page with company + admin account creation"""
    debug_print("📝 Rendering registration page")
    
    render_page_header("📝 Create Account", "Start your 14-day free trial • Approval required")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("register_form", clear_on_submit=True):
            st.markdown("### 🏢 Company Information")
            company_name = st.text_input("Company Name *", key="reg_company")
            company_email = st.text_input("Company Email *", key="reg_comp_email")
            company_phone = st.text_input("Company Phone", key="reg_comp_phone")
            division = st.selectbox("Division", 
                ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"],
                key="reg_division"
            )
            
            st.markdown("### 👤 Admin Account")
            full_name = st.text_input("Full Name *", key="reg_fullname")
            email = st.text_input("Email Address *", key="reg_email")
            username = st.text_input("Username *", key="reg_username")
            password = st.text_input("Password *", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password *", type="password", key="reg_confpass")
            
            terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *", key="reg_terms")
            
            submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            account_type = st.radio(
                "Account Type",
                options=["company", "consultant"],
                captions=["I represent a construction company", "I'm an independent consultant serving multiple clients"],
                index=0,
                key="reg_account_type"
            )

            if submitted:
                # Validation
                if not all([company_name, company_email, full_name, email, username, password]):
                    st.error("❌ Please fill all required fields marked with *")
                elif password != confirm_password:
                    st.error("❌ Passwords do not match")
                elif len(password) < 8:
                    st.error("❌ Password must be at least 8 characters")
                elif not terms:
                    st.error("❌ Please accept the terms to continue")
                else:
                    try:
                        # ✅ SECURITY NOTE: In production, hash passwords before storage
                        # Example: import bcrypt; hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                        # Create company first
                        company_data = {
                            'company_name': company_name,
                            'email': company_email,
                            'phone': company_phone,
                            'division': division
                        }
                        
                        success, result = db.create_company(company_data)
                        
                        if success:
                            company_id = result
                            
                            # Create admin user
                            user_data = {
                                'username': username,
                                'password': password,
                                'email': email,
                                'full_name': full_name,
                                'phone': '',
                                'role': 'company_admin' if account_type == 'company' else 'consultant',
                                'account_type': account_type,  # ← NEW FIELD
                                'is_approved': False
                            }
                            
                            user_success, user_result = db.create_user(company_id, user_data, None)
                            
                            if user_success:
                                st.success("✅ Account created successfully! Please wait for admin approval.")
                                st.info("You will receive an email notification once your account is approved.")
                                navigate_to("login")
                            else:
                                st.error(f"❌ Error creating user: {user_result}")
                                # Rollback company creation if user creation fails
                                db.delete_company(company_id)  # Assuming this method exists
                        else:
                            st.error(f"❌ Error creating company: {result}")
                            
                    except Exception as e:
                        debug_print(f"❌ Registration error: {e}")
                        logger.error("Registration failed", exc_info=True)
                        st.error(f"❌ An unexpected error occurred. Please try again.")
    
    with col2:
        st.markdown("### 📋 Registration Process")
        st.markdown("""
        1. **Fill out the registration form** with company & admin details
        2. **Submit for approval** – our team reviews each application
        3. **Wait for admin approval** – typically within 24-48 hours
        4. **Login to your account** – start your free trial immediately
        
        ### 🔐 Why Approval Required?
        - Ensures only legitimate construction companies access the platform
        - Prevents spam and abuse of AI prediction resources
        - Enables personalized onboarding and support
        """)
        
        st.markdown("### 🎁 Free Trial Includes")
        st.markdown("""
        ✅ **Professional plan features** (৳14,999/mo value)  
        ✅ **Unlimited tender analyses** during trial period  
        ✅ **AI-powered bid predictions** with 85% accuracy  
        ✅ **Team collaboration** – invite up to 5 members  
        ✅ **Priority email support**  
        ✅ **No credit card required** – cancel anytime  
        """)
        
        st.info("💡 Already have an account?")
        if st.button("→ Login Instead", use_container_width=True):
            navigate_to("login")
    
    debug_print("✅ Registration page render complete")


def pricing_page() -> None:
    """Pricing plans page with interactive selection"""
    debug_print("💰 Rendering pricing page")
    
    render_page_header("💰 Pricing Plans", "Choose the plan that fits your business")
    
    # Plan definitions (module-level constant would be better, but keeping local for now)
    plans = {
        'free': {
            'name': 'Free', 
            'price': 0, 
            'features': [
                '5 analyses/month',
                'Basic statistical reports',
                'Email support',
                'Single user account'
            ]
        },
        'basic': {
            'name': 'Basic', 
            'price': 4999, 
            'features': [
                '30 analyses/month',
                'AI-powered predictions',
                'Competitor analysis',
                'Priority email support',
                'Up to 3 team members'
            ]
        },
        'professional': {
            'name': 'Professional', 
            'price': 14999, 
            'features': [
                'Unlimited analyses',
                'ML ensemble predictions',
                'Real-time market intelligence',
                'Team collaboration tools',
                'Advanced reporting & export',
                'Priority support + training'
            ]
        },
        'enterprise': {
            'name': 'Enterprise', 
            'price': 49999, 
            'features': [
                'Everything in Professional',
                'Custom AI model training',
                'Dedicated account manager',
                'API access & webhooks',
                'SLA guarantee (99.9% uptime)',
                'On-premise deployment option'
            ]
        }
    }
    
    # Display pricing cards
    col1, col2, col3, col4 = st.columns(4)
    columns = [col1, col2, col3, col4]
    
    for idx, (plan_key, plan_data) in enumerate(plans.items()):
        with columns[idx]:
            is_recommended = (plan_key == 'professional')
            render_pricing_card(plan_key, plan_data, is_recommended)
    
    # Trial reminder
    st.markdown("---")
    st.info("🎁 **All plans include a 14-day free trial** – No credit card required to start. Cancel anytime.")
    
    debug_print("✅ Pricing page render complete")


def about_page() -> None:
    """About us page"""
    debug_print("ℹ️ Rendering about page")
    
    render_page_header("ℹ️ About Us", "Revolutionizing Bangladesh construction with AI")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🎯 Our Mission")
        st.markdown("""
        To empower construction companies in Bangladesh with AI-driven insights, 
        enabling smarter bidding decisions, reduced risk, and increased win rates 
        in public procurement tenders.
        """)
        
        st.markdown("### 👁️ Our Vision")
        st.markdown("""
        To become the leading AI-powered tender management platform in South Asia, 
        transforming how infrastructure projects are planned, bid, and delivered.
        """)
        
        st.markdown("### 🛠️ Technology Stack")
        st.markdown("""
        - **AI/ML**: Scikit-learn, XGBoost, custom ensemble models
        - **Backend**: Python, FastAPI, PostgreSQL
        - **Frontend**: Streamlit, Plotly, custom CSS
        - **Infrastructure**: Docker, AWS/GCP ready
        """)
    
    with col2:
        st.markdown("### 📊 Impact Metrics")
        metrics = [
            ("🏆", "Avg. Win Rate Increase", "+23%"),
            ("💰", "Avg. Savings per Tender", "৳2.4L"),
            ("⏱️", "Time Saved per Analysis", "4.2 hours"),
            ("🏢", "Companies Served", "150+"),
        ]
        for icon, label, value in metrics:
            st.markdown(f"""
            <div class="small-metric">
                <h3>{icon} {label}</h3>
                <div class="value">{value}</div>
            </div>
            """, unsafe_allow_html=True)
    
    debug_print("✅ About page render complete")


def contact_page() -> None:
    """Contact us page with form"""
    debug_print("📞 Rendering contact page")
    
    render_page_header("📞 Contact Us", "We're here to help")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("contact_form", clear_on_submit=True):
            name = st.text_input("Your Name *", key="contact_name")
            email = st.text_input("Your Email *", key="contact_email")
            subject = st.selectbox("Subject", 
                ["General Inquiry", "Technical Support", "Sales Question", "Partnership", "Other"],
                key="contact_subject"
            )
            message = st.text_area("Message *", height=150, key="contact_message")
            
            submitted = st.form_submit_button("Send Message", use_container_width=True, type="primary")
            
            if submitted:
                if not all([name, email, message]):
                    st.error("❌ Please fill all required fields")
                else:
                    try:
                        db.save_contact_message(name, email, subject, message)
                        st.success("✅ Thank you! We'll get back to you within 24 hours.")
                        # Clear form by rerunning
                        st.rerun()
                    except Exception as e:
                        debug_print(f"❌ Contact form error: {e}")
                        st.error("❌ Failed to send message. Please try again or email support@tenderai.com")
    
    with col2:
        st.markdown("### 📬 Other Ways to Reach Us")
        st.markdown("""
        **Email**  
        📧 support@tenderai.com  
        📧 sales@tenderai.com  
        
        **Phone**  
        📱 +880 1XXX-XXXXXX (Sat-Thu, 9AM-6PM)  
        
        **Office**  
        📍 Dhaka, Bangladesh  
        """)
        
        st.markdown("### ⏱️ Response Times")
        st.markdown("""
        - **Technical Support**: < 4 hours (business days)  
        - **Sales Inquiries**: < 24 hours  
        - **General Questions**: < 48 hours  
        """)
    
    debug_print("✅ Contact page render complete")


def dashboard_page() -> None:
    """Main dashboard for authenticated users"""
    debug_print("📊 Rendering dashboard page")
    
    # Ensure admin has premium access (for testing)
    ensure_admin_premium()
    # ✅ Pre-compute safe display values BEFORE markdown
    full_name = st.session_state.get('full_name', 'User')
    company_name = st.session_state.get('company_name', 'N/A')
    plan = str(st.session_state.get('subscription_plan', 'free')).upper()
    sub_status = st.session_state.get('subscription_status')
    status_display = str(sub_status).title() if sub_status is not None else 'Unknown'
    
    # Header with user info
    st.markdown(f"""
    <div class="main-header">
        <h1 style="margin: 0;">Welcome, {full_name}! 👋</h1>
        <p style="margin: 0.3rem 0 0 0; opacity: 0.9;">
            {company_name} • {plan} Plan • {status_display}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Fetch stats (consider caching for performance)
    stats = db.get_company_stats(st.session_state.company_id)
    sub = db.get_user_subscription(st.session_state.user_id)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📈 Total Analyses", stats.get('total_analyses', 0))
    with col2:
        win_rate = stats.get('win_rate', 0) * 100
        st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
    with col3:
        st.metric("👥 Team Members", stats.get('total_users', 1))
    with col4:
        limit = sub.get('analyses_limit', 5)
        used = sub.get('analyses_used', 0)
        remaining = "∞" if limit == -1 else max(0, limit - used)
        st.metric("📊 Analyses Left", remaining)
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔍 Start New Analysis", use_container_width=True, type="primary"):
            navigate_to("new_analysis")
    with col2:
        if st.button("📜 View History", use_container_width=True):
            navigate_to("history")
    with col3:
        if st.button("👤 My Profile", use_container_width=True):
            navigate_to("profile")
    
    # Role-specific actions
    if st.session_state.user_role in ['admin', 'company_admin']:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👥 Manage Team", use_container_width=True):
                navigate_to("user_management")
        with col2:
            if st.button("💳 Subscription", use_container_width=True):
                navigate_to("subscription")
    
    # =============================================================================
    # 🕐 RECENT ANALYSES SECTION (Tabular Format)
    # =============================================================================
    st.markdown("### 🕐 Recent Analyses")

    try:
        # Use the existing working method
        recent_df = db.get_user_analyses(
            user_id=st.session_state.user_id,
            company_id=st.session_state.company_id,
            role=st.session_state.user_role,
            limit=5  # Get only 5 most recent
        )
        
        if recent_df is not None and not recent_df.empty:
            # Convert to list of dicts for safe iteration
            recent_records = recent_df.to_dict('records')
            
            # Create table headers
            col1, col2, col3, col4, col5, col6 = st.columns([2.5, 2, 1.2, 1, 1.2, 0.8])
            
            with col1:
                st.markdown("**<span style='font-size:0.75rem;'>Tender Title</span>**", unsafe_allow_html=True)
            with col2:
                st.markdown("**<span style='font-size:0.75rem;'>Bid Amount</span>**", unsafe_allow_html=True)
            with col3:
                st.markdown("**<span style='font-size:0.75rem;'>Win Chance</span>**", unsafe_allow_html=True)
            with col4:
                st.markdown("**<span style='font-size:0.75rem;'>Status</span>**", unsafe_allow_html=True)
            with col5:
                st.markdown("**<span style='font-size:0.75rem;'>Created</span>**", unsafe_allow_html=True)
            with col6:
                st.markdown("**<span style='font-size:0.75rem;'></span>**", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Display rows
            for idx, analysis in enumerate(recent_records):
                cols = st.columns([2.5, 2, 1.2, 1, 1.2, 0.8])
                
                with cols[0]:
                    title = str(analysis.get('tender_title', 'Untitled'))[:50]
                    st.markdown(f"<span style='font-size:0.75rem;' title='{analysis.get('tender_title', '')}'>{title}</span>", unsafe_allow_html=True)
                
                with cols[1]:
                    bid = analysis.get('recommended_bid', 0) or 0
                    st.markdown(f"<span style='font-size:0.75rem;'>BDT {bid:,.3f}</span>", unsafe_allow_html=True)
                
                with cols[2]:
                    win_prob = analysis.get('success_probability', 0) or 0
                    win_pct = win_prob * 100 if win_prob <= 1 else win_prob
                    st.markdown(f"<span style='font-size:0.75rem;'>{win_pct:.1f}%</span>", unsafe_allow_html=True)
                    
                    # Mini progress bar
                    st.progress(min(win_pct / 100, 1.0), text="")
                
                with cols[3]:
                    status = analysis.get('bid_status', 'draft') or 'draft'
                    status_emoji = {"won": "🏆", "lost": "❌", "submitted": "📤", "draft": "⚪"}.get(status.lower(), "⚪")
                    st.markdown(f"<span style='font-size:0.75rem;'>{status_emoji} {status.title()}</span>", unsafe_allow_html=True)
                
                with cols[4]:
                    created_date = str(analysis.get('analysis_date', ''))[:16] if analysis.get('analysis_date') else "N/A"
                    created_by = analysis.get('created_by', 'System')
                    if not created_by or created_by == 'System':
                        created_by = st.session_state.get('full_name', 'User')[:15]
                    st.markdown(f"<span style='font-size:0.7rem;'>{created_date}<br><span style='color:#666;'>by {created_by}</span></span>", unsafe_allow_html=True)
                
                with cols[5]:
                    analysis_id = analysis.get('id')
                    button_key = f"dashboard_view_{analysis_id}_{idx}"
                    if st.button("📄", key=button_key, help="View details", use_container_width=True):
                        st.session_state.selected_analysis_id = analysis_id
                        st.session_state.page = "history"
                        st.rerun()
                
                st.markdown("---")
            
            # View all link
            if st.button("📊 View All Analyses →", use_container_width=True):
                st.session_state.page = "history"
                st.rerun()
                
        else:
            st.info("📭 No analyses yet. Run your first analysis in Three-Tier Bid Optimization!")
            
    except Exception as e:
        st.warning(f"Could not load recent analyses: {str(e)}")
        # Fallback to simple display
        st.info("📭 Start your first analysis to see recent activity here!")

    
    debug_print("✅ Dashboard page render complete")

def safe_date_slice(date_value, length: int = 10) -> str:
    """Safely slice date values (handles Timestamp, str, None)"""
    if date_value is None:
        return 'N/A'
    date_str = str(date_value)
    return date_str[:length] if len(date_str) >= length else date_str
def history_page() -> None:
    """History page - delegates to analysis_history module"""
    debug_print("📜 Rendering history page from analysis_history module")
    
    # Import and call the module's function
    from modules.analysis_history import show_analysis_history
    show_analysis_history()

def _export_analysis_csv(analysis: Dict) -> None:
    """Export single analysis to CSV (helper for history page)"""
    try:
        import csv
        import io
        
        # Define fields to export
        fields = [
            'tender_id', 'tender_title', 'procuring_entity', 'official_estimate',
            'recommended_bid', 'success_probability', 'risk_level', 'analysis_type',
            'analysis_date', 'bid_status'
        ]
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerow({k: analysis.get(k, '') for k in fields})
        
        # Trigger download
        csv_data = output.getvalue()
        output.close()
        
        tender_id = str(analysis.get('tender_id', 'export')).replace('/', '_')
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"analysis_{tender_id}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"❌ Export failed: {str(e)}")
        if DEBUG_MODE:
            st.code(traceback.format_exc(), language="python")

def profile_page() -> None:
    """User profile view and edit"""
    debug_print("👤 Rendering profile page")
    
    render_page_header("👤 My Profile", "View and update your account information")
    
    # Fetch fresh user data
    user = db.get_user_by_id(st.session_state.user_id)
    
    if not user:
        st.error("❌ Could not load user profile. Please try logging in again.")
        if st.button("→ Return to Dashboard"):
            navigate_to("dashboard")
        return
    
    # Display user info (read-only for now; add edit form if needed)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 Account Details")
        st.info(f"**Full Name:** {user[5] if len(user) > 5 else 'N/A'}")
        st.info(f"**Username:** {user[1] if len(user) > 1 else 'N/A'}")
        st.info(f"**Email:** {user[4] if len(user) > 4 else 'N/A'}")
        st.info(f"**Phone:** {user[7] if len(user) > 7 and user[7] else 'Not provided'}")
    
    with col2:
        st.markdown("### 🏢 Company & Role")
        st.info(f"**Company:** {user[14] if len(user) > 14 else 'N/A'}")
        role_value = user[6] if (user and len(user) > 6 and user[6] is not None) else 'N/A'
        st.info(f"**Role:** {str(role_value).title()}")
        st.info(f"**Account Status:** {'✅ Active' if user[8] else '⏳ Pending'}" if len(user) > 8 else "**Status:** N/A")
        
        # Subscription info
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub:
            st.markdown("---")
            st.markdown("### 💳 Subscription")
            st.info(f"**Plan:** {sub.get('plan', 'free').upper()}")
            sub_status = sub.get('status') if sub else None
            status_display = str(sub_status).title() if sub_status is not None else 'Unknown'
            st.info(f"**Status:** {status_display}")
            if sub.get('analyses_limit', 5) == -1:
                st.info("**Analyses:** Unlimited")
            else:
                used = sub.get('analyses_used', 0)
                limit = sub.get('analyses_limit', 5)
                st.info(f"**Analyses:** {used}/{limit} used this month")
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ Edit Profile", use_container_width=True):
            st.info("Profile editing coming soon! Contact support@tenderai.com for updates.")
    with col2:
        if st.button("🔐 Change Password", use_container_width=True):
            st.info("Password change feature coming soon!")
    with col3:
        if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
            # Clear session state
            for key in list(st.session_state.keys()):
                if key not in ['debug_mode']:  # Preserve debug setting
                    del st.session_state[key]
            initialize_session_state()  # Re-init with defaults
            navigate_to("home", success_msg="You have been signed out. 👋")
    
    debug_print("✅ Profile page render complete")


def admin_dashboard_page() -> None:
    """Simple admin dashboard for system oversight"""
    debug_print("👑 Rendering admin dashboard")
    
    render_page_header("👑 Admin Dashboard", "System Administration & Oversight")
    
    # Only allow admin role
    if st.session_state.user_role != 'admin':
        st.error("🔒 Access denied. Admin privileges required.")
        if st.button("→ Return to Dashboard"):
            navigate_to("dashboard")
        return
    
    # Fetch system-wide stats
    all_users = db.get_all_users() or []
    all_subs = db.get_all_subscriptions() or []
    all_companies = db.get_all_companies() or []
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Users", len(all_users))
    with col2:
        active_users = len([u for u in all_users if u[6] == 1]) if all_users and len(all_users[0]) > 6 else 0
        st.metric("✅ Active Users", active_users)
    with col3:
        st.metric("🏢 Companies", len(all_companies))
    with col4:
        st.metric("💳 Subscriptions", len(all_subs))
    
    # Pending approvals section
    pending_users = [u for u in all_users if len(u) > 8 and not u[8]] if all_users else []
    if pending_users:
        st.markdown("### ⏳ Pending Approvals")
        for user in pending_users[:10]:  # Show first 10
            with st.expander(f"{user[3]} ({user[1]}) • {user[2]}"):
                st.write(f"**Company:** {user[7] if len(user) > 7 else 'N/A'}")
                st.write(f"**Registered:** {user[9] if len(user) > 9 else 'N/A'}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✅ Approve", key=f"approve_{user[0]}"):
                        db.approve_user(user[0])  # Assuming this method exists
                        st.success(f"Approved {user[1]}")
                        st.rerun()
                with col2:
                    if st.button(f"❌ Reject", key=f"reject_{user[0]}", type="secondary"):
                        db.reject_user(user[0])  # Assuming this method exists
                        st.warning(f"Rejected {user[1]}")
                        st.rerun()
    
    # Recent activity / all users table
    st.markdown("### 📋 All Users (Recent 20)")
    if all_users:
        user_data = []
        for u in all_users[:20]:
            user_data.append({
                'ID': u[0],
                'Username': u[1],
                'Email': u[2],
                'Name': u[3],
                'Role': u[5] if len(u) > 5 else 'N/A',
                'Active': '✅' if (len(u) > 6 and u[6]) else '❌',
                'Approved': '✅' if (len(u) > 8 and u[8]) else '⏳'
            })
        st.dataframe(pd.DataFrame(user_data), use_container_width=True, hide_index=True)
    else:
        st.info("No users found in system.")
    
    debug_print("✅ Admin dashboard render complete")


def render_comparison(
    basic_result: Dict, 
    advanced_result: Dict, 
    official_estimate: float, 
    competitor_bids: List[float], 
    risk_tolerance: str
) -> None:
    """
    Render side-by-side comparison between basic and advanced analysis.
    
    Note: This is the 2-tier version. For 3-tier, use display_analysis_results_with_report()
    """
    debug_print("🆚 Rendering comparison: Basic vs Advanced")
    
    st.markdown("### 🆚 Analysis Comparison: Basic vs Advanced")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Basic Analysis")
        st.markdown(f"- **Optimal Bid:** BDT {basic_result['optimal_bid']:,.3f}")
        st.markdown(f"- **% of Estimate:** {basic_result['bid_ratio']*100:.2f}%")
        st.markdown(f"- **Win Probability:** {basic_result['win_probability']*100:.0f}%")
        st.markdown(f"- **Risk Level:** {basic_result['risk_color']} {basic_result['risk_level']}")
        st.caption(f"Method: {basic_result.get('method', 'Statistical')}")
    
    with col2:
        st.markdown("#### 🧠 Advanced ML Analysis")
        st.markdown(f"- **Optimal Bid:** BDT {advanced_result['optimal_bid']:,.3f}")
        st.markdown(f"- **% of Estimate:** {advanced_result['bid_ratio']*100:.2f}%")
        st.markdown(f"- **Win Probability:** {advanced_result['win_probability']*100:.0f}%")
        st.markdown(f"- **Risk Level:** {advanced_result['risk_color']} {advanced_result['risk_level']}")
        st.caption(f"Method: {advanced_result.get('method', 'ML Ensemble')}")
    
    # Difference analysis
    diff = advanced_result['optimal_bid'] - basic_result['optimal_bid']
    diff_percent = (diff / official_estimate) * 100 if official_estimate else 0
    
    st.markdown("---")
    st.markdown("#### 💡 Analysis Insight")
    
    if abs(diff) < official_estimate * 0.005:  # 0.5% threshold
        st.info("📊 Both analyses suggest very similar bid amounts (within 0.5%). The market appears stable and predictable.")
    elif diff > 0:
        st.warning(f"""
        📈 Advanced analysis suggests **increasing bid by BDT {diff:,.3f}** ({diff_percent:+.2f}% of estimate) 
        for optimal outcome. This accounts for:
        - Historical competitor patterns
        - Market condition adjustments
        - Risk-optimized positioning
        """)
    else:
        st.success(f"""
        📉 Advanced analysis suggests **decreasing bid by BDT {abs(diff):,.3f}** ({diff_percent:+.2f}% of estimate) 
        to improve win probability while maintaining profitability. This leverages:
        - Identified competitor weaknesses
        - Optimal risk-reward positioning
        - ML-predicted market response
        """)
    
    # Win probability comparison
    win_diff = advanced_result['win_probability'] - basic_result['win_probability']
    if win_diff > 0.10:
        st.success(f"🎯 Advanced ML analysis shows **+{win_diff*100:.0f}% higher win probability** due to identified competitor patterns and market dynamics.")
    elif win_diff < -0.10:
        st.warning(f"⚠️ Advanced analysis shows **-{abs(win_diff)*100:.0f}% win probability** – this may indicate aggressive competitor clustering or market saturation. Review carefully.")
    
    st.markdown("---")
    st.markdown("#### ✅ Recommendation")
    
    # For admin, default to advanced; for others, respect subscription
    if st.session_state.user_role == 'admin' or st.session_state.subscription_plan in ['professional', 'enterprise']:
        recommended = advanced_result
        rec_label = "Advanced ML Analysis"
        rec_icon = "🧠"
    else:
        recommended = basic_result
        rec_label = "Basic Analysis"
        rec_icon = "📊"
    
    st.info(f"""
    {rec_icon} **Recommended Bid:** BDT {recommended['optimal_bid']:,.3f}  
    Based on {rec_label} • Win probability: {recommended['win_probability']*100:.0f}% • Risk: {recommended['risk_color']} {recommended['risk_level']}
    """)
    
    # Save button hint
    if st.session_state.get('current_analysis_record'):
        st.caption("💡 Click '💾 Save Analysis' below to store this recommendation in your history.")
    
    debug_print("✅ Comparison render complete")



# =============================================================================
# 🎨 UI HELPER COMPONENTS (Extracted for reusability)
# =============================================================================

def render_tender_info_card(tender_data: Dict) -> None:  # ← Correct: tender_data (parameter name)
    """Render a compact tender information summary card"""
    # Now use tender_data consistently inside:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea;">
        <strong>📋 {tender_data.get('tender_title', 'Untitled')[:60]}{'...' if len(tender_data.get('tender_title',''))>60 else ''}</strong><br>
        <small>
            ID: {tender_data.get('tender_id', 'N/A')} • 
            Entity: {tender_data.get('procuring_entity', 'N/A')[:40]}<br>
            Estimate: BDT {tender_data.get('official_estimate', 0):,.3f} • 
            Deadline: {tender_data.get('submission_deadline', 'N/A')}
        </small>
    </div>
    """, unsafe_allow_html=True)

def safe_title(value, default: str = 'N/A') -> str:
    """
    Safely convert any value to title case.
    Handles None, non-strings, and empty values gracefully.
    
    Args:
        value: Any value (str, None, int, etc.)
        default: Fallback string if value is None/empty
    
    Returns:
        Title-cased string or default
    """
    if value is None:
        return default
    try:
        return str(value).strip().title() if str(value).strip() else default
    except Exception:
        return default


def render_competitor_bid_row(idx: int, competitor_Dict, competitor_options: Dict, key_prefix: str) -> tuple:
    """
    Render a single competitor bid input row.
    Returns updated competitor entry dict.
    """
    col_a, col_b, col_c, col_d = st.columns([2.5, 2, 1.5, 0.5])
    
    with col_a:
        if competitor_options:
            name = st.selectbox(
                "Competitor",
                options=[""] + list(competitor_options.keys()),
                index=list(competitor_options.keys()).index(competitor_entry['name']) if competitor_entry['name'] in competitor_options else 0,
                key=f"{key_prefix}_name_{idx}",
                label_visibility="collapsed"
            )
        else:
            name = st.text_input("Competitor", value=competitor_entry['name'], key=f"{key_prefix}_name_{idx}", label_visibility="collapsed")
    
    with col_b:
        bid = st.number_input(
            "Bid (BDT)",
            min_value=0.0,
            value=float(competitor_entry['bid']),
            step=100000.0,  # 1 lakh steps for easier input
            format="%.3f",  # 3 decimal precision
            key=f"{key_prefix}_bid_{idx}",
            label_visibility="collapsed"
        )
    
    with col_c:
        was_winner = st.checkbox(
            "Winner?",
            value=competitor_entry.get('was_winner', False),
            key=f"{key_prefix}_winner_{idx}"
        )
    
    with col_d:
        remove = st.button("🗑️", key=f"{key_prefix}_remove_{idx}", help="Remove this competitor")
    
    return {
        'name': name,
        'bid': round(bid, 3),  # Ensure 3 decimal precision
        'was_winner': was_winner,
        'remove': remove
    }


def render_ppr_metrics_card(label: str, value: str, caption: str, warning: bool = False) -> None:
    """Render a PPR compliance metric with optional warning styling"""
    border_color = "#dc3545" if warning else "#28a745"
    bg_color = "#fff5f5" if warning else "#f0fff4"
    
    st.markdown(f"""
    <div style="background: {bg_color}; padding: 0.75rem; border-radius: 8px; 
                border-left: 3px solid {border_color}; text-align: center;">
        <div style="font-size: 0.8rem; color: #666;">{label}</div>
        <div style="font-size: 1.3rem; font-weight: bold; color: #1e3c72; margin: 0.25rem 0;">{value}</div>
        <div style="font-size: 0.7rem; color: #888;">{caption}</div>
    </div>
    """, unsafe_allow_html=True)


def calculate_ppr_compliance(official_estimate: float, competitor_bids: List[float], recommended_bid: float) -> Dict:
    """
    Calculate PPR 2025 compliance metrics.
    
    Returns dict with all calculated values for display.
    """
    # PPR 2025 constants
    NPPI_FACTOR = 0.920
    WEIGHTS = {'competitor_avg': 0.5, 'official_est': 0.2, 'nppi': 0.3}
    
    # Calculate NPPI price
    nppi_price = round(official_estimate * NPPI_FACTOR, 3)
    
    # Competitor statistics
    if competitor_bids:
        avg_competitor = float(np.mean(competitor_bids))
        competitor_sample = competitor_bids[:5]  # Use first 5 for std dev
    else:
        # Fallback estimates
        avg_competitor = round(official_estimate * 0.91, 3)
        competitor_sample = [
            round(official_estimate * p, 3) 
            for p in [0.88, 0.90, 0.92, 0.94, 0.95]
        ]
    
    # Weighted average (X̄)
    weighted_avg = round(
        WEIGHTS['competitor_avg'] * avg_competitor +
        WEIGHTS['official_est'] * official_estimate +
        WEIGHTS['nppi'] * nppi_price,
        3
    )
    
    # Weighted standard deviation (Sd)
    if len(competitor_sample) > 0:
        squared_deviations = [(weighted_avg - price) ** 2 for price in competitor_sample]
        variance = sum(squared_deviations) / len(competitor_sample)
        weighted_std = round(np.sqrt(variance), 3)
    else:
        weighted_std = 0.0
    
    # SLT Threshold
    slt_threshold = round(weighted_avg - weighted_std, 3)
    
    # Evaluation
    is_below_slt = recommended_bid < slt_threshold
    compliance_status = "NON-COMPLIANT ⚠️" if is_below_slt else "COMPLIANT ✅"
    
    return {
        'nppi_factor': NPPI_FACTOR,
        'nppi_price': nppi_price,
        'avg_competitor': avg_competitor,
        'weighted_avg': weighted_avg,
        'weighted_std': weighted_std,
        'slt_threshold': slt_threshold,
        'recommended_bid': recommended_bid,
        'is_below_slt': is_below_slt,
        'compliance_status': compliance_status,
        'competitor_sample': competitor_sample,
        'squared_deviations': squared_deviations if 'squared_deviations' in locals() else []
    }


# =============================================================================
# 📊 REFACTORED: Tender Analysis Page (UI Optimized)
# =============================================================================
@st.cache_data(ttl=300)  # Cache for 5 minutes
def _get_company_tenders_cached(company_id: int) -> pd.DataFrame:
    """Cached helper to fetch company tenders as DataFrame"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            t.id, t.company_id, t.tender_id, t.tender_title, t.procuring_entity,
            t.division, t.district, t.thana, t.country, t.procurement_type,
            t.official_estimate, t.submission_deadline, t.tender_security,
            t.document_fee, t.evaluation_type,
            -- ✅ Locking columns:
            t.is_locked, t.is_copy, t.original_tender_id, t.is_active,
            t.created_at, t.updated_at
        FROM company_tenders t
        WHERE t.company_id = ? 
        ORDER BY t.created_at DESC
        ''', (company_id,))
        
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Failed to fetch cached tenders: {e}")
        return pd.DataFrame()


def _process_competitor_bids_input(
    bid_source: str, 
    official_estimate: float, 
    tender_id: str,
    competitor_options: Dict[str, int],
    session_key: str = 'analysis_competitor_bids'
) -> List[float]:
    """
    Handle competitor bid input logic (auto-generate or manual entry).
    Returns list of bid amounts (floats, 3 decimal precision).
    """
    competitor_bids = []
    
    if bid_source == "Enter manually":
        # Manual entry mode
        if session_key not in st.session_state:
            st.session_state[session_key] = []
        
        # Render competitor input rows
        num_competitors = st.number_input(
            "Number of competitors", 
            min_value=0, 
            max_value=20, 
            value=max(3, len(st.session_state[session_key])),
            key=f"{session_key}_count"
        )
        
        # Process existing entries
        updated_entries = []
        for idx, entry in enumerate(st.session_state[session_key]):
            updated = render_competitor_bid_row(idx, entry, competitor_options, session_key)
            if not updated['remove'] and updated['name'] and updated['bid'] > 0:
                updated_entries.append({
                    'name': updated['name'],
                    'bid': updated['bid'],
                    'was_winner': updated['was_winner']
                })
        
        st.session_state[session_key] = updated_entries
        
        # Add new competitor section
        with st.expander("➕ Add New Competitor", expanded=False):
            col_a, col_b, col_c, col_d = st.columns([2, 2, 1.5, 0.5])
            with col_a:
                new_name = st.selectbox(
                    "Select from master list", 
                    options=[""] + list(competitor_options.keys()),
                    key=f"{session_key}_new_name"
                )
            with col_b:
                new_bid = st.number_input(
                    "Bid Amount (BDT)",
                    min_value=0.0,
                    value=round(official_estimate * 0.90, 3) if official_estimate > 0 else 0.0,
                    step=100000.0,
                    format="%.3f",
                    key=f"{session_key}_new_bid"
                )
            with col_c:
                new_winner = st.checkbox("Winner?", key=f"{session_key}_new_winner")
            with col_d:
                add_clicked = st.button("Add", key=f"{session_key}_add_btn")
            
            if add_clicked and new_name and new_bid > 0:
                existing_names = [e['name'] for e in st.session_state[session_key]]
                if new_name not in existing_names:
                    st.session_state[session_key].append({
                        'name': new_name,
                        'bid': round(new_bid, 3),
                        'was_winner': new_winner
                    })
                    st.toast(f"✅ Added {new_name}", icon="🎯")
                    st.rerun()
                else:
                    st.warning(f"⚠️ {new_name} already in list")
        
        # Extract bid amounts
        competitor_bids = [round(e['bid'], 3) for e in st.session_state[session_key]]
        
        # Show summary if bids exist
        if competitor_bids:
            with st.expander("📊 Competitor Summary", expanded=True):
                summary_df = pd.DataFrame([
                    {
                        'Competitor': e['name'],
                        'Bid (BDT)': f"{e['bid']:,.3f}",
                        '% of Estimate': f"{e['bid']/official_estimate*100:.2f}%" if official_estimate > 0 else "N/A",
                        'Winner': '🏆' if e.get('was_winner') else ''
                    }
                    for e in st.session_state[session_key]
                ])
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns([4, 1])
                with col2:
                    if st.button("🗑️ Clear All", key=f"{session_key}_clear", use_container_width=True):
                        st.session_state[session_key] = []
                        st.rerun()
    
    else:
        # Auto-generate mode
        num_competitors = st.slider(
            "Number of competitors to simulate", 
            min_value=3, 
            max_value=15, 
            value=7,
            key=f"{session_key}_auto_count"
        )
        
        # Clear manual entries when switching to auto
        if session_key in st.session_state:
            st.session_state[session_key] = []
        
        # Generate realistic bids with seeded randomness
        seed_val = hash(f"{tender_id}_{official_estimate}_{num_competitors}") % (2**32)
        np.random.seed(seed_val)
        
        base_ratios = np.random.uniform(0.85, 0.98, num_competitors)
        noise = np.random.uniform(-0.03, 0.03, num_competitors)
        final_ratios = np.clip(base_ratios + noise, 0.80, 1.00)
        
        competitor_bids = [round(official_estimate * r, 3) for r in final_ratios]
        
        # Show preview
        with st.expander("🤖 Auto-Generated Bids Preview", expanded=True):
            preview_df = pd.DataFrame({
                'Simulated Bidder': [f"Bidder {i+1}" for i in range(num_competitors)],
                'Bid Amount (BDT)': [f"{b:,.3f}" for b in competitor_bids],
                '% of Estimate': [f"{b/official_estimate*100:.2f}%" for b in competitor_bids]
            })
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            st.caption("💡 Bids are simulated based on historical patterns. Switch to 'Enter manually' for real competitor data.")
    
    return competitor_bids

def tender_analysis_page() -> None:
    """
    Three-Tier Tender Analysis Page - Refactored for better UX
    Features: 
    - Searchable table selector at top (like Edit Tender)
    - Clean collapsible form sections
    - Robust session state sync for auto-populate
    - Compact locking workflow + visual PPR compliance
    """
    debug_print("🎯 Rendering tender analysis page")
    
    # Clear stale flags
    if 'tender_form_submitted' in st.session_state:
        del st.session_state.tender_form_submitted

    # Header
    render_page_header(
        "🎯 Three-Tier Bid Optimization", 
        "Compare Basic, Advanced (PPR 2025), and Enhanced (ML) analysis",
        icon="🏗️"
    )
    
    # Ensure admin has premium access
    ensure_admin_premium()
    
    # 🔑 HYBRID SUBSCRIPTION CHECK
    sub = db.get_effective_subscription(
        st.session_state.user_id, 
        st.session_state.company_id if st.session_state.get('account_type') == 'company' else None
    )
    st.session_state.subscription_plan = sub.get('plan', 'free')
    st.session_state.analyses_used = sub.get('analyses_used', 0)
    st.session_state.analyses_limit = sub.get('analyses_limit', 5)
    st.session_state.sub_owner_type = sub.get('owner_type', 'free')
    
    # Check usage limits
    if st.session_state.analyses_limit > 0 and st.session_state.analyses_used >= st.session_state.analyses_limit:
        st.warning(f"🔒 {st.session_state.sub_owner_type.title()} analysis limit reached.")
        if st.button("💳 Upgrade Plan", type="primary"):
            st.session_state.page = "subscription"
            st.rerun()
        return
    
    is_premium = st.session_state.subscription_plan in ['professional', 'enterprise'] or st.session_state.user_role == 'admin'
    
    # =============================================================================
    # 🔹 1. SESSION STATE INITIALIZATION (Page-specific)
    # =============================================================================
    page_defaults = {
        'selected_tender_for_analysis': None,
        'analysis_competitor_bids': [],
        'analysis_ready_to_save': False,
        'last_analysis_comparison': None,
        'last_analysis_record': None,
        'ppr_calculation_cache': None,
        'tender_lock_status': 'unlocked',
        # ✅ Widget keys (must match st.text_input key= values)
        'input_tender_id': '', 'input_tender_title': '', 'input_procuring_entity': '',
        'input_division': 'Dhaka', 'input_district': '', 'input_thana': '',
        'input_official_estimate': 0.0, 'input_tender_security': 0.0, 
        'input_document_fee': 0.0, 'input_procurement_type': 'works',
        '_pdf_buffer': None,          # For PDF download
        '_pdf_filename': None,        # For PDF filename
        'analysis_ready_to_save': False,
        }
    for k, v in page_defaults.items():
        st.session_state.setdefault(k, v)
    
    # =============================================================================
    # 🔹 2. SEARCHABLE TENDER SELECTOR (Top of Page - Like Edit Tender)
    # =============================================================================
    st.markdown("### 🔍 Select Tender for Analysis")
    
    # Search filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search_id = st.text_input("Tender ID", key="analysis_search_id", placeholder="e.g., 1265809")
    with col2:
        search_title = st.text_input("Title/Entity", key="analysis_search_title", placeholder="Search...")
    with col3:
        filter_type = st.selectbox("Type", ["All", "works", "goods", "services"], key="analysis_filter_type")
    
    # Fetch & filter tenders
    all_tenders = _get_company_tenders_cached(st.session_state.company_id)
    filtered = all_tenders.copy()
    
    if search_id:
        filtered = filtered[filtered['tender_id'].str.contains(search_id, case=False, na=False)]
    if search_title:
        filtered = filtered[
            filtered['tender_title'].str.contains(search_title, case=False, na=False) | 
            filtered['procuring_entity'].str.contains(search_title, case=False, na=False)
        ]
    if filter_type != "All":
        filtered = filtered[filtered['procurement_type'] == filter_type]
    
    # Display selection table
    if not filtered.empty:
        display_df = filtered[['id', 'tender_id', 'tender_title', 'procuring_entity', 
                              'procurement_type', 'official_estimate', 'submission_deadline', 
                              'is_locked', 'is_copy']].copy()
        
        display_df['estimate_fmt'] = display_df['official_estimate'].apply(lambda x: f"BDT {x:,.0f}" if pd.notna(x) else "N/A")
        display_df['deadline_fmt'] = pd.to_datetime(display_df['submission_deadline'], errors='coerce').dt.strftime('%d %b %Y')
        display_df['status'] = display_df.apply(lambda r: "🔒 LOCKED" if r['is_locked'] else ("📋 COPY" if r['is_copy'] else "🔓 Open"), axis=1)
        
        st.dataframe(
            display_df[['tender_id', 'tender_title', 'procuring_entity', 'procurement_type', 'estimate_fmt', 'deadline_fmt', 'status']],
            use_container_width=True,
            height=250,
            column_config={
                "tender_id": "ID",
                "tender_title": st.column_config.TextColumn("Title", width="large"),
                "procuring_entity": "Entity",
                "procurement_type": "Type",
                "estimate_fmt": "Estimate",
                "deadline_fmt": "Deadline",
                "status": "Status"
            }
        )
        
        # Selection dropdown + Load button
        tender_options = {f"{row['tender_id']} • {str(row['tender_title'])[:50]}...": row.to_dict() for _, row in filtered.iterrows()}
        selected_label = st.selectbox("Select tender to analyze:", options=["-- Create New Analysis --"] + list(tender_options.keys()), key="analysis_selector")
        
        if selected_label != "-- Create New Analysis --" and selected_label in tender_options:
            selected_data = tender_options[selected_label]
            
            if st.button("📥 Load Tender for Analysis", type="primary", key="load_analysis_tender"):
                # ✅ Sync to widget keys (input_*), NOT form_* keys
                st.session_state.selected_tender_for_analysis = selected_data
                
                # Basic details
                st.session_state.input_tender_id = str(selected_data.get('tender_id', ''))
                st.session_state.input_tender_title = str(selected_data.get('tender_title', ''))
                st.session_state.input_procuring_entity = str(selected_data.get('procuring_entity', ''))
                
                # Location
                st.session_state.input_division = str(selected_data.get('division', 'Dhaka'))
                st.session_state.input_district = str(selected_data.get('district', ''))
                st.session_state.input_thana = str(selected_data.get('thana', ''))
                
                # Financials
                st.session_state.input_official_estimate = float(selected_data.get('official_estimate', 0) or 0)
                st.session_state.input_tender_security = float(selected_data.get('tender_security', 0) or 0)
                st.session_state.input_document_fee = float(selected_data.get('document_fee', 0) or 0)
                st.session_state.input_procurement_type = str(selected_data.get('procurement_type', 'works'))
                
                # Lock status
                is_locked = bool(selected_data.get('is_locked', False))
                st.session_state.tender_lock_status = 'locked' if is_locked else 'unlocked'
                
                # Show toast AND rerun
                st.toast(f"✅ Loaded: {selected_data['tender_title'][:40]}", icon="📋")
                st.rerun()
    else:
        st.info("📭 No tenders found. Create a tender first or adjust your search.")
    
    # Show loaded tender summary (compact)
    if st.session_state.selected_tender_for_analysis:
        t = st.session_state.selected_tender_for_analysis
        status_badge = "🔒" if t.get('is_locked') else ("📋" if t.get('is_copy') else "🔓")
        st.markdown(f"""
        <div style="background:#f8fafc;padding:0.75rem 1rem;border-radius:8px;border-left:4px solid #3b82f6;margin:0.5rem 0">
            <strong>{status_badge} {str(t.get('tender_title',''))[:70]}{'...' if len(str(t.get('tender_title',''))) > 70 else ''}</strong><br>
            <small>ID: {t.get('tender_id')} • Est: BDT {t.get('official_estimate',0):,.0f} • Deadline: {str(t.get('submission_deadline',''))[:10]}</small>
        </div>
        """, unsafe_allow_html=True)
    
    # =============================================================================
    # 🔹 3. COMPACT ANALYSIS FORM (Collapsible Sections)
    # =============================================================================
    st.markdown("### 📝 Analysis Inputs")
    
    # Determine form disabled state
    is_new = st.session_state.selected_tender_for_analysis is None
    is_locked = st.session_state.tender_lock_status == 'locked' and not is_new
    form_disabled = is_locked and st.session_state.user_role != 'admin'
    
    if form_disabled:
        st.warning("🔒 Tender is locked. Only admin can edit. Request a backup copy if needed.")
    
    with st.form("analysis_form", clear_on_submit=False):
        # Section 1: Basic Details (Collapsible)
        with st.expander("📋 Basic Tender Details", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Tender ID *", key="input_tender_id", disabled=form_disabled)
                st.text_area("Tender Title *", height=40, key="input_tender_title", disabled=form_disabled)
                st.text_input("Procuring Entity *", key="input_procuring_entity", disabled=form_disabled)
            with c2:
                from modules.bangladesh_locations import DIVISIONS, get_districts, get_upazilas
                div = st.selectbox("Division", DIVISIONS, key="input_division", disabled=form_disabled)
                dists = get_districts(div)
                dist = st.selectbox("District", dists, key="input_district", disabled=form_disabled)
                upzs = get_upazilas(dist)
                if upzs:
                    st.selectbox("Thana/Upazila", upzs, key="input_thana", disabled=form_disabled)
                else:
                    st.text_input("Thana/Upazila", key="input_thana_text", disabled=form_disabled)
        
        # Section 2: Financials (Collapsible)
        with st.expander("💰 Financial Details", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.number_input("Official Estimate (BDT) *", min_value=0.0, step=100000.0, format="%.3f", key="input_official_estimate", disabled=form_disabled)
                st.number_input("Tender Security (BDT)", min_value=0.0, step=10000.0, format="%.3f", key="input_tender_security", disabled=form_disabled)
            with c2:
                st.selectbox("Procurement Type", ["works", "goods", "services"], key="input_procurement_type", disabled=form_disabled)
                st.number_input("Document Fee (BDT)", min_value=0.0, step=500.0, format="%.3f", key="input_document_fee", disabled=form_disabled)
        
        with st.expander("👥 Competitor Intelligence", expanded=True):
            bid_source = st.radio(
                "Provide competitor bids:",
                ["🤖 Auto-generate realistic bids", "✍️ Enter manually from known competitors"],
                horizontal=True,
                key="analysis_bid_source",
                disabled=form_disabled
            )

            if "manual" in bid_source.lower():
                competitors = db.get_competitor_master_list(st.session_state.company_id)
                competitor_options = {c[1]: c[0] for c in competitors} if competitors else {}
                
                if competitor_options:
                    st.markdown("#### Add Competitor Bids")
                    
                    if 'competitor_rows' not in st.session_state:
                        st.session_state.competitor_rows = [{'id': 0, 'name': '', 'bid': 0.0}]
                    
                    for i, row in enumerate(st.session_state.competitor_rows):
                        c1, c2, c3 = st.columns([3, 2, 0.5])
                        with c1:
                            name = st.selectbox(
                                "Competitor",
                                options=[""] + list(competitor_options.keys()),
                                index=list(competitor_options.keys()).index(row['name']) if row['name'] in competitor_options else 0,
                                key=f"comp_name_{i}",
                                disabled=form_disabled
                            )
                        with c2:
                            bid = st.number_input(
                                "Bid (BDT)",
                                min_value=0.0,
                                value=float(row['bid']),
                                step=100000.0,
                                format="%.3f",
                                key=f"comp_bid_{i}",
                                disabled=form_disabled
                            )
                        with c3:
                            if st.button("🗑️", key=f"comp_del_{i}", disabled=form_disabled):
                                st.session_state.competitor_rows.pop(i)
                                st.rerun()
                        
                        st.session_state.competitor_rows[i]['name'] = name
                        st.session_state.competitor_rows[i]['bid'] = bid
                    
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        if st.button("➕ Add Competitor", key="add_comp_row", disabled=form_disabled):
                            new_id = max([r['id'] for r in st.session_state.competitor_rows], default=-1) + 1
                            st.session_state.competitor_rows.append({'id': new_id, 'name': '', 'bid': 0.0})
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Clear All", key="clear_comp_rows", disabled=form_disabled):
                            st.session_state.competitor_rows = []
                            st.rerun()
                    
                    # Build and save competitor_bids
                    competitor_bids = [
                        {'name': row['name'], 'bid': float(row['bid'])}
                        for row in st.session_state.competitor_rows
                        if row['name'] and row['bid'] > 0
                    ]
                    st.session_state.analysis_competitor_bids = competitor_bids  # ✅ Persist for post-form
                    
                    if not competitor_bids:
                        st.caption("💡 Add at least one competitor with a bid value")
                else:
                    st.info("📭 No competitors in master list. Add competitors first in Competitor Management.")
            else:
                # ✅ Auto-generate: USE configured settings
                estimate_val = st.session_state.get('input_official_estimate', 0.0) or 0
                competitor_count = st.session_state.get('auto_competitor_count', 3)
                risk_pref = st.session_state.get('auto_risk_pref', 'moderate')
                
                if estimate_val > 0:
                    # Generate bids using configured count + risk preference
                    competitor_bids = _generate_competitor_bids(
                        estimate_val, 
                        num_competitors=competitor_count,
                        risk_preference=risk_pref  # Pass risk pref to generation function
                    )
                    st.session_state.analysis_competitor_bids = competitor_bids
                    st.caption(f"🤖 Generated {competitor_count} {risk_pref} competitor bids")
                else:
                    st.caption("💡 Enter Official Estimate first to auto-generate bids")
                    competitor_bids = []
                    st.session_state.analysis_competitor_bids = []
        
        # Section 4: Risk Strategy
        with st.expander("🎯 Risk Strategy", expanded=True):
            risk_tolerance = st.select_slider(
                "Risk tolerance",
                options=['aggressive', 'moderate', 'conservative'],
                value='moderate',
                key="analysis_risk_tolerance",
                disabled=form_disabled,
                help="Aggressive: Lower bids | Conservative: Safer wins"
            )
        # =============================================================================
        # ⚙️ AUTO-BID CALCULATION SETTINGS (New Section)
        # =============================================================================
        with st.expander("⚙️ Auto-Bid Calculation Settings", expanded=False):
            st.markdown("Configure how competitor bids are generated for analysis")
            
            col1, col2 = st.columns(2)
            with col1:
                # ✅ Configurable competitor count (persisted in session state)
                st.session_state.auto_competitor_count = st.slider(
                    "Number of Competitors for Auto-Generation",
                    min_value=2, max_value=10, value=st.session_state.get('auto_competitor_count', 3),
                    help="More competitors = more realistic bid distribution. Affects auto-generated bids only."
                )
            with col2:
                # Risk preference for auto-generation
                st.session_state.auto_risk_pref = st.selectbox(
                    "Auto-Generation Risk Preference",
                    options=['aggressive', 'moderate', 'conservative'],
                    index=['aggressive', 'moderate', 'conservative'].index(st.session_state.get('auto_risk_pref', 'moderate')),
                    help="Aggressive: Lower bids | Conservative: Higher, safer bids"
                )
            
            st.caption("💡 These settings only affect 🤖 Auto-generate mode. Manual entries are always respected.")
        
        # Submit button
        form_complete = all([
            st.session_state.get('input_tender_id', ''),
            st.session_state.get('input_tender_title', ''),
            st.session_state.get('input_procuring_entity', ''),
            (st.session_state.get('input_official_estimate', 0) or 0) > 0
        ])
        submit_disabled = not form_complete or not st.session_state.get('analysis_competitor_bids', []) or form_disabled

        form_submitted = st.form_submit_button("🚀 Run Three-Tier Analysis", type="primary", use_container_width=True, disabled=submit_disabled)

        if not form_complete and not form_disabled:
            st.caption("⚠️ Fill required fields: Tender ID, Title, Entity, Estimate")
        elif not st.session_state.get('analysis_competitor_bids', []) and not form_disabled:
            st.caption("⚠️ Add at least one competitor bid")
    
    # =============================================================================
    # 🔹 RUN ANALYSIS ON FORM SUBMIT
    # =============================================================================
        # =============================================================================
    # 🔹 RUN ANALYSIS ON FORM SUBMIT
    # =============================================================================
    if form_submitted and not form_disabled:
        try:
            # ✅ 1. Read & Validate Inputs
            inputs = {
                'tender_id': st.session_state.get('input_tender_id', '').strip(),
                'tender_title': st.session_state.get('input_tender_title', '').strip(),
                'procuring_entity': st.session_state.get('input_procuring_entity', '').strip(),
                'official_estimate': float(st.session_state.get('input_official_estimate', 0) or 0),
                'procurement_type': st.session_state.get('input_procurement_type', 'works'),
                'division': st.session_state.get('input_division', 'Dhaka'),
                'district': st.session_state.get('input_district', ''),
                'thana': st.session_state.get('input_thana', st.session_state.get('input_thana_text', '')),
                'risk_tolerance': st.session_state.get('analysis_risk_tolerance', 'moderate'),
                'competitor_bids': st.session_state.get('analysis_competitor_bids', [])
            }
            
            required_missing = [k for k in ['tender_id', 'tender_title', 'procuring_entity'] if not inputs[k]]
            if inputs['official_estimate'] <= 0:
                required_missing.append('official_estimate')
            
            if required_missing:
                st.error(f"❌ Please fill required fields: {', '.join(required_missing)}")
            elif not inputs['competitor_bids']:
                st.error("❌ Please provide at least one competitor bid")
            else:
                # ✅ 2. Run Analysis
                with st.spinner("🔍 Running Three-Tier Analysis..."):
                    from modules.advanced_bid_optimizer import get_three_tier_comparison
                    comparison = get_three_tier_comparison(
                        official_estimate=inputs['official_estimate'],
                        competitor_bids=inputs['competitor_bids'],
                        procurement_type=inputs['procurement_type'],
                        risk_tolerance=inputs['risk_tolerance'],
                        company_id=st.session_state.company_id
                    )
                    
                    best_tier = max(comparison.keys(), key=lambda t: comparison[t].get('confidence_score', 0) * comparison[t]['win_probability'])
                    
                    # ✅ 3. Store in Session State (PERSISTS across reruns)
                    st.session_state.current_analysis_record = {
                        'tender_id': inputs['tender_id'], 'tender_title': inputs['tender_title'],
                        'procuring_entity': inputs['procuring_entity'], 'division': inputs['division'],
                        'district': inputs['district'], 'thana': inputs['thana'],
                        'construction_type': inputs['procurement_type'],
                        'official_estimate': round(inputs['official_estimate'], 3),
                        'competitor_bids': inputs['competitor_bids'], 'risk_tolerance': inputs['risk_tolerance'],
                        'procurement_type': inputs['procurement_type']
                    }
                    st.session_state.current_comparison = comparison
                    st.session_state.current_best_result = comparison[best_tier]
                    st.session_state.current_best_tier = best_tier
                    st.session_state.current_competitor_bids = inputs['competitor_bids']
                    st.session_state.current_risk_tolerance = inputs['risk_tolerance']
                    st.session_state.analysis_ready_to_save = True
                    
                    db.increment_analysis_usage(st.session_state.user_id)
                    st.session_state.analyses_used += 1
                    
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            st.error(f"❌ Analysis error: {str(e)}")

    # =============================================================================
    # 🔹 DISPLAY RESULTS (PERSISTS AFTER SAVE/INSPECT CLICKS)
    # =============================================================================
    if st.session_state.get('current_analysis_record') is not None:
        comparison = st.session_state.current_comparison
        analysis_record = st.session_state.current_analysis_record
        inputs = {'official_estimate': analysis_record['official_estimate'], 'tender_id': analysis_record['tender_id']}
        
        # ✅ Display PPR & Results (Your existing display code goes here)
        if is_premium:
            display_analysis_results_with_report(
                comparison=comparison, analysis_record=analysis_record,
                competitor_bids=st.session_state.current_competitor_bids,
                risk_tolerance=st.session_state.current_risk_tolerance
            )
        else:
            st.info("🔓 Free Plan: Showing Basic vs Advanced. Upgrade for ML analysis!")
            render_comparison(
                basic_result=comparison['basic'], advanced_result=comparison['advanced'],
                official_estimate=analysis_record['official_estimate'],
                competitor_bids=st.session_state.current_competitor_bids,
                risk_tolerance=st.session_state.current_risk_tolerance
            )
        
        # ✅ PPR Visualization
        st.markdown("---\n### 📈 PPR 2025 Compliance")
        try:
            from modules.ppr_viz import render_ppr_compliance_viz
            render_ppr_compliance_viz(comparison, analysis_record)
        except ImportError:
            adv = comparison.get('advanced', comparison.get('basic', {}))
            rec_bid = adv.get('optimal_bid', 0)
            slt = adv.get('slt_threshold', 0)
            nppi = adv.get('nppi_factor', 0.92)
            is_compliant = rec_bid >= slt
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("NPPI Factor", f"{nppi:.3f}")
            mc2.metric("NPPI Price", f"BDT {analysis_record['official_estimate']*nppi:,.0f}")
            mc3.metric("Weighted Avg", f"BDT {adv.get('weighted_average', 0):,.0f}")
            mc4.metric("SLT Threshold", f"BDT {slt:,.0f}", delta="⚠️ Below" if not is_compliant else "✅ Above", delta_color="inverse" if not is_compliant else "normal")
            if is_compliant: st.success(f"✅ **PPR Compliant**: Bid BDT {rec_bid:,.0f} meets requirements")
            else: st.error(f"🚨 **SLT Risk**: Bid BDT {rec_bid:,.0f} is below threshold BDT {slt:,.0f}")
        
        # =============================================================================
        # 📄 PDF EXPORT (Fixed Data Mapping)
        # =============================================================================
        if st.button("📑 Generate PDF Report", use_container_width=True, type="secondary", key="gen_pdf_btn"):
            # ✅ 1. Build complete report_data dict
            report_data = {
                **st.session_state.get('current_analysis_record', {}),
                **st.session_state.get('current_best_result', {})
            }
            
            # ✅ 2. Explicitly map & cast critical fields
            est = float(st.session_state.get('input_official_estimate', report_data.get('official_estimate', 1)) or 1)
            report_data.update({
                'official_estimate': est,
                'recommended_bid': float(report_data.get('optimal_bid', 0)),
                'slt_threshold': float(report_data.get('slt_threshold', est * 0.80)),
                'nppi_factor': float(report_data.get('nppi_factor', 0.92)),
                'success_probability': float(report_data.get('win_probability', 0.6)),
                'competitor_count': len(st.session_state.get('current_competitor_bids', [])),
                'bid_source': st.session_state.get('analysis_bid_source', 'Auto-Generated'),
                'comparison': st.session_state.get('current_comparison', {}),
                'competitor_bids': st.session_state.get('current_competitor_bids', [])
            })
            
            # ✅ 3. Call generator
            with st.spinner("🔄 Generating Babui TenderAI Report..."):
                try:
                    from modules.pdf_generator import generate_babui_detailed_report
                    user_info = {
                        'full_name': st.session_state.get('full_name', 'N/A'),
                        'company_name': st.session_state.get('company_name', 'N/A')
                    }
                    pdf_buffer = generate_babui_detailed_report(report_data, user_info)
                    
                    # ✅ 4. Store & show download
                    safe_tid = str(report_data.get('tender_id', 'report')).replace('/', '_').replace(' ', '_')
                    st.session_state._pdf_buffer = pdf_buffer
                    st.session_state._pdf_filename = f"Babui_TenderAI_{safe_tid}_{datetime.now().strftime('%Y%m%d')}.pdf"
                    st.success("✅ Report generated! Scroll down to download.")
                except Exception as e:
                    st.error(f"❌ PDF Error: {str(e)}")
        
        # ✅ CSV Export
        export_rows = []
        for tier, result in comparison.items():
            export_rows.append({
                'Tier': tier.upper(), 'Method': result.get('method', ''),
                'Optimal_Bid_BDT': result['optimal_bid'],
                'Win_Probability_%': round(result['win_probability'] * 100, 1),
                'Confidence_%': round(result.get('confidence_score', 0.7) * 100, 1),
                'PPR_Compliant': 'Yes' if result['optimal_bid'] >= (comparison.get('advanced', comparison['basic']).get('slt_threshold', 0)) else 'No'
            })
        csv = pd.DataFrame(export_rows).to_csv(index=False)
        st.download_button("📥 Export Results (CSV)", data=csv, 
                          file_name=f"analysis_{inputs['tender_id']}_{datetime.now().strftime('%Y%m%d')}.csv",
                          mime="text/csv", use_container_width=True)
        
        # ✅ PDF Download Button (Shows if buffer exists)
        if st.session_state.get('_pdf_buffer') and st.session_state.get('_pdf_filename'):
            st.markdown("---")
            st.info("📄 **PDF Report Ready**")
            col1, col2 = st.columns([3, 1])
            with col1: st.caption(f"File: `{st.session_state._pdf_filename}`")
            with col2:
                if st.button("🗑️ Clear", key="clear_pdf_buf", use_container_width=True):
                    st.session_state.pop('_pdf_buffer', None)
                    st.session_state.pop('_pdf_filename', None)
                    st.rerun()
            st.download_button("💾 Download Enhanced PDF Report", data=st.session_state._pdf_buffer,
                              file_name=st.session_state._pdf_filename, mime="application/pdf",
                              use_container_width=True, key="download_enhanced_pdf")
    
    if DEBUG_MODE and st.button("🔬 Inspect report_data"):
        st.write("### report_data Preview")
        report_data = {}
        if st.session_state.get('current_analysis_record'):
            report_data.update(st.session_state.current_analysis_record)
        if st.session_state.get('current_best_result'):
            report_data.update(st.session_state.current_best_result)
        report_data.update({
            'official_estimate': float(st.session_state.get('input_official_estimate', 1) or 1),
            'recommended_bid': float(report_data.get('optimal_bid', 0) or 0),
            'slt_threshold': float(report_data.get('slt_threshold', report_data.get('official_estimate', 1) * 0.80) or 0),
        })
        st.json({k: v for k, v in report_data.items() if k in ['tender_id', 'official_estimate', 'recommended_bid', 'slt_threshold', 'nppi_factor']})
    if DEBUG_MODE and st.button("🔬 Test PDF Generator Directly"):
        test_data = {
            'tender_id': 'TEST-001',
            'tender_title': 'Test Tender',
            'procuring_entity': 'Test Entity',
            'official_estimate': 1000000.0,
            'recommended_bid': 920000.0,
            'slt_threshold': 850000.0,
            'nppi_factor': 0.92,
            'success_probability': 0.65,
            'risk_level': 'MEDIUM'
        }
        user_info = {'full_name': 'Test User', 'company_name': 'Test Co'}
        
        try:
            from modules.pdf_generator import generate_enhanced_analysis_report
            buf = generate_enhanced_analysis_report(test_data, user_info, include_charts=False)
            if buf and buf.getbuffer().nbytes > 0:
                st.success(f"✅ Direct test succeeded! Buffer size: {buf.getbuffer().nbytes} bytes")
                st.download_button("💾 Download Test PDF", data=buf, file_name="test.pdf", mime="application/pdf")
            else:
                st.error("❌ Direct test returned empty buffer")
        except Exception as e:
            st.error(f"❌ Direct test failed: {e}")
            st.code(traceback.format_exc(), language="python")
    debug_print("✅ Tender analysis page complete")
    
# =============================================================================
# 🎨 SIDEBAR COMPONENT (Refactored + UI Optimized)
# =============================================================================

def render_nav_button(label: str, page_key: str, icon: str = "", 
                     disabled: bool = False, badge: Optional[str] = None,
                     button_type: str = "secondary") -> bool:
    """Render navigation button with optional text badge"""
    # Build label with badge as plain text (Streamlit-safe)
    full_label = f"{icon} {label}"
    if badge:
        full_label += f" [{badge}]"  # Simple text badge
    
    clicked = st.button(
        full_label,
        key=f"nav_{page_key}",
        use_container_width=True,
        type=button_type,
        disabled=disabled
        # ❌ Removed help parameter that was showing as visible text
    )
    
    if clicked:
        st.session_state.page = page_key
        st.rerun()
    
    return clicked


def render_sidebar() -> None:
    """Optimized sidebar with role-based navigation and responsive design"""
    debug_print("🧭 Rendering sidebar")
    
    with st.sidebar:
        if st.session_state.page != 'tender_management' and 'extracted_data' in st.session_state:
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
        # App branding
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #eee;">
            <h2 style="margin: 0; color: #1e3c72;">🏗️ TenderAI</h2>
            <small style="color: #666;">Bid Optimization Platform</small>
        </div>
        """, unsafe_allow_html=True)
        
        # =====================================================================
        # 👤 USER INFO SECTION
        # =====================================================================
        if st.session_state.get('logged_in'):
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                        padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
                <strong>👋 {st.session_state.get('full_name', 'User')}</strong><br>
                <small>
                    🏢 {st.session_state.get('company_name', 'N/A')}<br>
                    ⭐ {safe_title(st.session_state.get('user_role'), 'User')}
                </small>
            </div>
            """, unsafe_allow_html=True)
            
            # Subscription badge
            sub = db.get_user_subscription(st.session_state.user_id) if st.session_state.get('user_id') else {}
            plan = sub.get('plan', 'free')
            is_premium = plan in ['professional', 'enterprise'] or st.session_state.get('user_role') == 'admin'
            
            badge_color = "#22c55e" if is_premium else "#6b7280"
            badge_text = "✨ PREMIUM" if is_premium else "🔓 FREE TRIAL"
            
            st.markdown(f"""
            <div style="text-align: center; background: {badge_color}20; 
                        padding: 0.4rem; border-radius: 6px; margin: 0.5rem 0; 
                        border: 1px solid {badge_color};">
                <strong style="color: {badge_color};">{badge_text}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # =====================================================================
        # 🧭 NAVIGATION MENUS (Role-based)
        # =====================================================================
        
        # Public navigation (not logged in)
        if not st.session_state.get('logged_in'):
            st.markdown("### 🌐 Public")
            public_menu = [
                ("🏠", "Home", "home"),
                ("💰", "Pricing", "pricing"),
                ("ℹ️", "About", "about"),
                ("📞", "Contact", "contact"),
                ("🔐", "Login", "login"),
            ]
            for icon, label, page in public_menu:
                render_nav_button(label, page, icon=icon)
            
            if st.button("➕ Register", use_container_width=True, type="primary"):
                st.session_state.page = "register"
                st.rerun()
        
        # Authenticated user navigation
        else:
            # Main menu (all users)
            st.markdown("### 📊 Main")
            main_menu = [
                ("📈", "Dashboard", "dashboard"),
                ("🎯", "New Analysis", "new_analysis"),
                ("📜", "History", "history"),
                ("👤", "Profile", "profile"),
            ]
            for icon, label, page in main_menu:
                render_nav_button(label, page, icon=icon)
            
            # Subscription management
            if st.button("💳 Subscription", key="nav_subscription", use_container_width=True):
                st.session_state.page = "subscription"
                st.rerun()
            
            # Management menu (company admins+)
            if st.session_state.get('user_role') in ['admin', 'company_admin']:
                st.markdown("---")
                st.markdown("### 👥 Management")
                
                mgmt_menu = [
                    ("👥", "Team Management", "user_management"),
                    ("📋", "Tender Management", "tender_management"),
                ]
                for icon, label, page in mgmt_menu:
                    render_nav_button(label, page, icon=icon)
                
                # Post-evaluation tools (premium feature)
                if is_premium:
                    st.markdown("#### 📊 Evaluation")
                    eval_menu = [
                        ("📋", "Post-Evaluation", "post_evaluation"),
                        ("🧠", "AI Suggestions", "intelligent_suggestions"),
                    ]
                    for icon, label, page in eval_menu:
                        render_nav_button(label, page, icon=icon, button_type="secondary")
            
            # Premium features
            if is_premium:
                st.markdown("---")
                st.markdown("### 📚 Intelligence")
                
                intel_menu = [
                    ("📊", "Historical Data", "historical_data"),
                    ("👥", "Competitor Tracking", "competitor_tracking"),
                    ("🗂️", "Competitor Master", "competitor_master"),
                ]
                for icon, label, page in intel_menu:
                    render_nav_button(label, page, icon=icon, button_type="secondary")
            
            # Admin-only section
            if st.session_state.get('user_role') == 'admin':
                st.markdown("---")
                st.markdown("### 👑 System Admin")
                
                # Check pending approvals for badge
                pending_count = 0
                try:
                    if hasattr(db, 'get_pending_users'):
                        pending_count = len(db.get_pending_users(st.session_state.company_id))
                except:
                    pass
                
                admin_menu = [
                    ("📊", "Admin Dashboard", "admin_dashboard"),
                    ("👥", "User Approvals", "user_approval", 
                     str(pending_count) if pending_count > 0 else None),
                ]
                for item in admin_menu:
                    icon, label, page = item[0], item[1], item[2]
                    badge = item[3] if len(item) > 3 else None
                    render_nav_button(label, page, icon=icon, badge=badge, button_type="secondary")
            
            # =================================================================
            # 🚪 LOGOUT SECTION
            # =================================================================
            st.markdown("---")
            
            # Usage stats for premium users
            if is_premium and sub:
                limit = sub.get('analyses_limit', -1)
                used = sub.get('analyses_used', 0)
                if limit > 0:
                    remaining = max(0, limit - used)
                    pct_used = min(100, (used / limit) * 100)
                    st.markdown(f"""
                    <div style="font-size: 0.8rem; color: #666; text-align: center;">
                        <strong>Analyses:</strong> {used}/{limit} used<br>
                        <div style="background: #e5e7eb; border-radius: 4px; height: 4px; margin: 4px 0;">
                            <div style="background: #667eea; width: {pct_used}%; height: 100%; border-radius: 4px;"></div>
                        </div>
                        <small>{remaining} remaining this month</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Logout button
            if st.button("🚪 Sign Out", key="nav_logout", use_container_width=True, type="secondary"):
                logout_user()
                # Clear sensitive session data
                for key in list(st.session_state.keys()):
                    if key not in ['debug_mode', 'page']:
                        del st.session_state[key]
                initialize_session_state()
                st.toast("👋 You have been signed out", icon="✅")
                st.rerun()
        
        # Debug mode indicator
        if DEBUG_MODE:
            st.markdown("---")
            st.caption("🐛 Debug Mode Active")


# =============================================================================
# 🎬 MAIN APP ROUTER (Refactored + Optimized)
# =============================================================================

def _render_public_pages() -> None:
    """Render pages for non-authenticated users"""
    page_handlers = {
        'home': home_page,
        'login': login_page,
        'register': register_page,
        'pricing': pricing_page,
        'about': about_page,
        'contact': contact_page,
    }
    
    handler = page_handlers.get(st.session_state.page, home_page)
    handler()


def _render_authenticated_pages() -> None:
    """Render pages for authenticated users with lazy module imports"""
    
    PAGE_HANDLERS: Dict[str, Callable] = {
        # Core pages (already imported at module level)
        PageRoutes.DASHBOARD: dashboard_page,
        PageRoutes.NEW_ANALYSIS: tender_analysis_page,
        PageRoutes.HISTORY: history_page,
        PageRoutes.PROFILE: profile_page,
        PageRoutes.ADMIN_DASHBOARD: admin_dashboard_page,
        
        # Module-based pages (lazy import)
        #PageRoutes.SUBSCRIPTION: lambda: render_subscription_page(db, st.session_state.user_id),
        PageRoutes.SUBSCRIPTION: lambda: render_subscription_page(),
        #PageRoutes.USER_MANAGEMENT: lambda: render_user_management(db, st.session_state.user_id, st.session_state.company_id),
        PageRoutes.USER_MANAGEMENT: lambda: render_user_management(),
        # Advanced modules (import only when accessed)
        PageRoutes.TENDER_MANAGEMENT: lambda: _import_and_call('modules.tender_management', 'render_tender_management'),
        PageRoutes.POST_EVALUATION: lambda: _import_and_call('modules.post_evaluation', 'render_post_evaluation_page'),  # ✅ Now works
        PageRoutes.INTELLIGENT_SUGGESTIONS: lambda: _import_and_call('modules.post_evaluation', 'render_intelligent_suggestions'),  # ✅ Now works
        PageRoutes.HISTORICAL_DATA: lambda: _import_and_call('modules.historical_data', 'render_historical_data_page'),
        PageRoutes.ANALYSIS_HISTORY: lambda: _import_and_call('modules.analysis_history', 'show_analysis_history'),  # ✅ Now works
        PageRoutes.COMPETITOR_TRACKING: lambda: _import_and_call('modules.competitor_tracking', 'render_competitor_tracking_page'),
        PageRoutes.COMPETITOR_MASTER: lambda: _import_and_call('modules.competitor_master', 'render_competitor_master_page'),  # ✅ Now works
        PageRoutes.USER_APPROVAL: lambda: _import_and_call('modules.user_approval', 'render_user_approval_page'),
    }
    
    # Get handler with fallback to dashboard for unknown routes
    handler = PAGE_HANDLERS.get(st.session_state.page, PAGE_HANDLERS[PageRoutes.DASHBOARD])
    
    try:
        handler()
    except ImportError as e:
        debug_print(f"❌ Module import error for '{st.session_state.page}': {e}")
        logger.error(f"Import failed: {st.session_state.page}", exc_info=True)
        st.error(f"⚠️ Feature unavailable: {st.session_state.page.replace('_', ' ').title()}")
        st.info("This feature may require a higher subscription plan or system configuration.")
    except Exception as e:
        debug_print(f"❌ Render error for '{st.session_state.page}': {e}")
        logger.error(f"Page render failed: {st.session_state.page}", exc_info=True)
        st.error("⚠️ Unable to load this page. Please try again or contact support.")
        if DEBUG_MODE:
            with st.expander("🐛 Debug Traceback"):
                st.code(traceback.format_exc(), language="python")


def _import_and_call(module_path: str, function_name: str, *args, **kwargs):
    """
    Lazy import helper for module-based page handlers.
    Prevents importing all modules at startup.
    """
    import importlib
    module = importlib.import_module(module_path)
    func = getattr(module, function_name)
    return func(*args, **kwargs)


def main() -> None:
    """
    Main application entry point with optimized routing.
    Uses PageRoutes constants, lazy imports, and safe error handling.
    """
    debug_print(f"🚀 App render | Page: {st.session_state.page} | Auth: {st.session_state.logged_in}")
    
    # Hide Streamlit's default chrome elements
    st.markdown("""
    <style>
        div[data-testid="stSidebarNav"] { display: none; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .stApp { max-width: 100%; }
    </style>
    """, unsafe_allow_html=True)
    
    # Ensure session state is initialized (safety net)
    if 'page' not in st.session_state:
        st.session_state.page = PageRoutes.HOME
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Render sidebar (always visible)
    render_sidebar()
    
    # Handle checkout flow (modal-like experience)
    if st.session_state.get('show_checkout'):
        render_checkout()
        return
    
    # Route to appropriate page handler
    if not st.session_state.logged_in:
        _render_public_pages()
    else:
        _render_authenticated_pages()
    
    # Optional: Global debug panel (development only)
    if DEBUG_MODE and st.session_state.get('user_role') == 'admin':
        _render_global_debug_panel()


def _render_global_debug_panel() -> None:
    """Render global debug information for admin users (development only)"""
    with st.expander("🐛 Global Debug Panel", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Session State Keys")
            for key in sorted(st.session_state.keys()):
                val = st.session_state[key]
                display = str(val)[:150] + "..." if len(str(val)) > 150 else str(val)
                st.code(f"{key}: {display}", language="python")
        
        with col2:
            st.markdown("#### Quick Actions")
            if st.button("🗑️ Clear Non-Essential State", use_container_width=True):
                protected = ['logged_in', 'user_id', 'company_id', 'user_role', 'subscription_plan', 'debug_mode', 'page']
                for key in list(st.session_state.keys()):
                    if key not in protected:
                        del st.session_state[key]
                st.success("Session state cleared!")
                st.rerun()
            
            if st.button("🔄 Force Rerun", use_container_width=True):
                st.rerun()
            
            st.markdown("#### System Info")
            st.code(f"""
Python: {sys.version.split()[0]}
Streamlit: {st.__version__}
Debug Mode: {DEBUG_MODE}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """, language="python")


# =============================================================================
# 🎬 APP LAUNCH (Final safety)
# =============================================================================
if __name__ == "__main__":
    # ✅ Ensure imports are available
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    
    debug_print("🎬 Starting TenderAI application...")
    
    # ✅ Initialize once at startup
    initialize_session_state()
    
    try:
        main()
    except Exception as e:
        logger.critical("Application crashed", exc_info=True)
        st.error("💥 Application error. Please refresh or contact support.")
        if DEBUG_MODE:
            required_routes = [
                'home', 'login', 'register', 'pricing', 'about', 'contact',
                'dashboard', 'new_analysis', 'history', 'profile', 'subscription',
                'user_management', 'tender_management', 'post_evaluation', 'intelligent_suggestions',
                'historical_data', 'analysis_history', 'competitor_tracking', 'competitor_master',
                'admin_dashboard', 'user_approval'
            ]
            
            missing = [r for r in required_routes if r not in PageRoutes.get_all_routes()]
            if missing:
                debug_print(f"❌ Missing PageRoutes attributes: {missing}")
            else:
                debug_print("✅ All PageRoutes attributes present")
    
    debug_print("✅ App render cycle complete\n")