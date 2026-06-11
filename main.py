"""
TenderAI - Enterprise Tender Management System
Complete Working Version - Fixed & Debug-Enabled
"""
# ====================== FIX WATCHDOG LOG SPAM ======================
import logging

logging.getLogger("watchdog").setLevel(logging.ERROR)
logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.ERROR)
logging.getLogger("streamlit").setLevel(logging.ERROR)

# Filter out noisy inotify messages
class NoSpamFilter(logging.Filter):
    def filter(self, record):
        msg = str(record.msg).lower()
        return "inotify_buffer" not in msg and ".git" not in msg

logging.getLogger("watchdog.observers.inotify_buffer").addFilter(NoSpamFilter())
# ====================== END FIX ======================

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
import pdfplumber
#hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
#user_data['password'] = hashed.decode('utf-8')
import importlib  # ✅ Added for lazy imports
from contextlib import contextmanager  # ✅ For resource management
from utils.bid_generators import _generate_competitor_bids
#from modules.pdf_generator import _generate_and_download_pdf
from modules.ppr_viz import render_ppr_compliance_viz
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
    get_risk_indicator,
    validate_password_strength,
    safe_title
)
from config import DEBUG_MODE, BID_AMOUNT_DECIMALS, BID_RATIO_DECIMALS, COST_ESTIMATE_RATIO, PPR_CONFIG, debug_print
#from modules.pdf_generator import generate_babui_detailed_report
from modules.advanced_bid_optimizer import get_three_tier_comparison

# Continue with normal app flow
# debug_print(f"🚀 App render | Page: {st.session_state.page} | Auth: {st.session_state.logged_in}")
from modules.forgot_password import render_forgot_password
from modules.reset_password import render_reset_password
from _pages.admin_dashboard import show as admin_dashboard_page
from _pages.landing_page2 import show_landing_page
from _pages.about import show_about_page
import random
from modules.report_generator import generate_unified_report, generate_html_content_only

from modules.auth import restore_session_from_url
from version import get_version, get_full_version, get_copyright, get_app_name, get_app_desc
#from modules.tutorials import render_sidebar_tutorial
from modules.subscriber_dashboard import render_subscriber_dashboard

from modules.subscriber_dashboard import render_subscriber_dashboard
from modules.rate_crud_forms import render_rate_crud_forms
from modules.unified_import_wizard import render_unified_import_wizard
from modules.user_management import render_user_management, render_role_management
from modules.user_approval import render_user_approval_page
from modules.competitor_tracking import render_competitor_tracking_page
from modules.competitor_master import render_competitor_master_page
from modules.historical_data import render_historical_data_page
from modules.analysis_history import show_analysis_history
from modules.post_evaluation import render_post_evaluation_page, render_intelligent_suggestions
from modules.tender_management import render_tender_management
from modules.egp_boq_workspace import render_boq_workspace
from modules.tutorials import render_tutorial
from modules.boq_generator_ui import render_boq_generator
from modules.boq_admin_report import render_boq_admin_report
from modules.boq_bid_bridge import render_boq_bid_integration
from _pages.company_subscription import show_company_subscription
from _pages.company_dashboard import show as show_company_dashboard
from _pages.dashboard import show as dashboard_page
from modules.navigation import render_top_navigation, render_page_header
from modules.ui_components import (
    render_app_header, 
    render_dark_mode_toggle, 
    apply_theme, 
    init_theme,
    render_footer
)
from modules.tender_analysis import render_tender_analysis
from modules.bid_scenario_generator import render_bid_scenario_generator_ui
from modules.subscription_manager import SubscriptionManager
from modules.rbac import init_rbac





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
init_rbac()


if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

print("=" * 60)
print(f"MAIN.PY STARTING - logged_in={st.session_state.logged_in}")
print(f"URL params at start: {dict(st.query_params)}")

# Try to restore session from URL
if not st.session_state.logged_in:
    print("Attempting to restore from URL...")
    try:
        from modules.auth import restore_session_from_url
        restored = restore_session_from_url()
        print(f"Restore result: {restored}")
        if restored:
            print("Session restored! User is now logged in.")
            # Don't rerun here to avoid loop
    except Exception as e:
        print(f"Restore exception: {e}")
        import traceback
        traceback.print_exc()
else:
    print("Already logged in, skipping restore")

print("=" * 60)

st.markdown(get_compact_css(), unsafe_allow_html=True)
def check_and_run_migrations(db):
    """Check database schema and run migrations if needed"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # =========================================================================
        # MIGRATION 1: Add district column to companies (existing)
        # =========================================================================
        cursor.execute("PRAGMA table_info(companies)")
        company_columns = [col[1] for col in cursor.fetchall()]
        
        if 'district' not in company_columns:
            debug_print("🔧 Running schema migration: city → district")
            cursor.executescript("""
            ALTER TABLE companies ADD COLUMN district TEXT;
            UPDATE companies SET district = city WHERE city IS NOT NULL;
            """)
            conn.commit()
            debug_print("✅ Migration 1 complete: district column added")
        
        # =========================================================================
        # MIGRATION 2: Add individual user support columns to users table
        # =========================================================================
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        # Define new columns for users table
        user_new_columns = {
            'auth_provider': "TEXT DEFAULT 'email'",
            'email_verified': "BOOLEAN DEFAULT 0",
            'email_verified_at': "TIMESTAMP",
            'verification_token': "TEXT",
            'reset_token': "TEXT",
            'reset_token_expires': "TIMESTAMP",
            'specialization': "TEXT",
            'years_experience': "INTEGER"
        }
        
        migration_2_needed = False
        for col_name in user_new_columns.keys():
            if col_name not in user_columns:
                migration_2_needed = True
                break
        
        if migration_2_needed:
            debug_print("🔧 Running schema migration: adding individual user support columns")
            
            for col_name, col_type in user_new_columns.items():
                if col_name not in user_columns:
                    try:
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                        debug_print(f"  ✅ Added column: {col_name}")
                    except Exception as e:
                        debug_print(f"  ⚠️ Could not add {col_name}: {e}")
            
            conn.commit()
            debug_print("✅ Migration 2 complete: individual user columns added")
        
        # =========================================================================
        # MIGRATION 3: Add is_individual column to companies table
        # =========================================================================
        cursor.execute("PRAGMA table_info(companies)")
        company_columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_individual' not in company_columns:
            debug_print("🔧 Running schema migration: adding is_individual column")
            cursor.execute("ALTER TABLE companies ADD COLUMN is_individual BOOLEAN DEFAULT 0")
            conn.commit()
            debug_print("✅ Migration 3 complete: is_individual column added")
        
        # =========================================================================
        # MIGRATION 4: Create indexes for better performance
        # =========================================================================
        debug_print("🔧 Creating indexes for better performance...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)",
            "CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token)",
            "CREATE INDEX IF NOT EXISTS idx_users_auth_provider ON users(auth_provider)",
            "CREATE INDEX IF NOT EXISTS idx_companies_is_individual ON companies(is_individual)"
        ]
        
        for index in indexes:
            try:
                cursor.execute(index)
                debug_print(f"  ✅ Index created: {index.split('ON')[1].strip() if 'ON' in index else index}")
            except Exception as e:
                debug_print(f"  ⚠️ Could not create index: {e}")
        
        conn.commit()
        debug_print("✅ All migrations completed successfully!")
        
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
        /* =========================================================================
        REMOVE WHITE GAPS - CRITICAL FIX
        ========================================================================= */
        /* Remove padding from main container */
        .main .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            margin-top: 0rem !important;
        }
        
        /* Remove spacing from the top of the app */
        section[data-testid="stAppViewContainer"] > .main {
            padding-top: 0rem !important;
        }
        
        /* Hide default Streamlit header */
        header[data-testid="stHeader"] {
            display: none;
        }
        
        /* Remove margin from the first element */
        .stApp > div:first-child {
            margin-top: -1rem !important;
        }
        
        /* Remove default Streamlit padding */
        .stApp {
            padding-top: 0 !important;
        }
        
        /* Remove gap from block container */
        .block-container {
            padding-top: 0 !important;
        }
        
        /* Remove spacing between elements */
        .element-container {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        
        /* For logged-in users, keep sidebar spacing */
        .logged-in .main .block-container {
            padding-top: 2rem !important;
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
        'user_email': None,
        'full_name': None,
        'company_name': None,
        'subscription_plan': 'free',
        'subscription_status': 'active',
        
        # Navigation - DON'T override if already set
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
    
    # Only set default page if not already set by callback
    if 'page' not in st.session_state:
        st.session_state.page = PageRoutes.HOME
    
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
    INDIVIDUAL_REGISTER = 'individual_register'
    INDIVIDUAL_LOGIN = 'individual_login'
    
    # ─── Authenticated Core Pages ────────────────────────────────────────────
    DASHBOARD = 'dashboard'
    NEW_ANALYSIS = 'new_analysis'  # ✅ Fixed - was missing or incorrect
    RATE_VIEWER = 'rate_viewer'
    HISTORY = 'history'
    PROFILE = 'profile'
    SUBSCRIPTION = 'subscription'
    FORGOT_PASSWORD = 'forgot_password'
    RESET_PASSWORD = 'reset_password'
    
    # ─── Management Pages (Company Admin+) ───────────────────────────────────
    USER_MANAGEMENT = 'user_management'
    TENDER_MANAGEMENT = 'tender_management'
    POST_EVALUATION = 'post_evaluation'
    INTELLIGENT_SUGGESTIONS = 'intelligent_suggestions'
    COMPANY_DASHBOARD = 'company_dashboard'
    EGP_BOQ_WORKSPACE = 'egp_boq_workspace'
    TUTORIAL = 'tutorial'

    # ─── Premium Intelligence Pages ──────────────────────────────────────────
    HISTORICAL_DATA = 'historical_data'
    ANALYSIS_HISTORY = 'analysis_history'
    COMPETITOR_TRACKING = 'competitor_tracking'
    COMPETITOR_MASTER = 'competitor_master'
    BOQ_GENERATOR = "boq_generator"
    BOQ_ADMIN_REPORT = "boq_admin_report"
    BOQ_BID_OPTIMIZER = "boq_bid_optimizer"    
    SCENARIO_GENERATOR = "scenario_generator"
    # ─── Admin System Pages ──────────────────────────────────────────────────
    ADMIN_DASHBOARD = 'admin_dashboard'
    USER_APPROVAL = 'user_approval'
    ROLE_MANAGEMENT = 'role_management'
    RATE_MANAGEMENT = 'rate_management'
    IMPORT_WIZARD = 'import_wizard'
    SUBSCRIBER_DASHBOARD = 'subscriber_dashboard'
    
    # ─── Utility Routes ──────────────────────────────────────────────────────
    CHECKOUT = 'checkout'
    
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
    
def _render_unauthenticated_pages() -> None:
    """Render pages for users who are not logged in"""
    
    # Define unauthenticated page handlers
    UNAUTH_PAGE_HANDLERS = {
        'home': home_page,
        'login': login_page,
        'register': register_page,
        'pricing': pricing_page,
        'about': about_page,
        'contact': contact_page,
        'forgot_password': render_forgot_password,
        'reset_password': lambda: render_reset_password(st.query_params.get("token", "")),
    }
    
    # Get current page from session state
    current_page = st.session_state.get('page', 'login')
    
    # Get the handler function
    handler = UNAUTH_PAGE_HANDLERS.get(current_page, login_page)
    
    # Call the handler
    try:
        handler()
    except Exception as e:
        debug_print(f"❌ Unauthenticated page render error: {e}")
        st.error("⚠️ Unable to load this page. Please try again.")



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
    """Updated Login Page with URL-Based Remember Me & Better Integration"""
    debug_print("🔐 Rendering login page")
    
    # Initialize session state variables
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    if 'forgot_password_email' not in st.session_state:
        st.session_state.forgot_password_email = ''
    if 'remember_me' not in st.session_state:
        st.session_state.remember_me = False

    # Import required modules
    from modules.google_auth import render_google_login_button, handle_google_callback
    from modules.individual_registration import authenticate_individual_user
    from modules.auth import login_user, restore_session_from_url
    
    # ✅ Try to restore session from URL (no cookie complexity)
    if not st.session_state.get('logged_in', False):
        try:
            if restore_session_from_url():
                debug_print("Session restored from URL, redirecting to dashboard")
                navigate_to("dashboard")
                st.rerun()
                return
        except Exception as e:
            debug_print(f"Session restore error: {e}")
    
    # Handle Google OAuth callback
    handle_google_callback()
    
    # Check if showing Google registration
    if st.session_state.get('show_google_registration'):
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return
    
    render_page_header("🔐 Login", "Access your TenderAI account")
    
    # Display session persistence tip
    if not st.session_state.get('logged_in', False):
        st.info("💡 **Tip:** Check 'Remember me' to stay logged in across browser sessions for 30 days.")
    
    # Create tabs for different login types
    tab1, tab2 = st.tabs(["🏢 Company Login", "👤 Individual Login"])
    
    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("company_login_form", clear_on_submit=True):
                username = st.text_input("Username or Email", key="comp_login_username")
                password = st.text_input("Password", type="password", key="comp_login_password")
                remember_me = st.checkbox("Remember me (stay logged in for 30 days)", key="comp_remember_me")
                
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
                
                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password")
                    else:
                        debug_print(f"[LOGIN] Username: {username}, Remember me: {remember_me}")
                        user, status, message = authenticate_user(username, password)
                        debug_print(f"[LOGIN] Auth result: status={status}, user={user is not None}")
                        
                        if status == "pending_approval":
                            st.warning("⚠️ Your account is pending approval by an administrator.")
                        elif user and status == "approved":
                            debug_print(f"[LOGIN] Calling login_user with remember_me={remember_me}")
                            # ✅ Pass cookies=None since we're using URL params
                            if login_user(user, password, remember_me):
                                full_name = user[3] if len(user) > 3 else username
                                debug_print("[LOGIN] Login successful!")
                                st.success(f"Welcome back, {full_name}! 👋")
                                
                                if remember_me:
                                    st.info("✅ Session saved to URL! You'll stay logged in even after browser refresh.")
                                
                                navigate_to("dashboard")
                                st.rerun()
                            else:
                                st.error("❌ Login failed. Please try again.")
                        else:
                            st.error(message or "❌ Invalid credentials. Please try again.")
            
            st.markdown("---")
            if st.button("➕ Register New Company Account", use_container_width=True):
                navigate_to("register")

    with tab2:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Individual Email Login
            
            with st.form("individual_login_form", clear_on_submit=True):
                email = st.text_input("Email Address", key="ind_login_email")
                password = st.text_input("Password", type="password", key="ind_login_password")
                remember_me_ind = st.checkbox("Remember me (stay logged in for 30 days)", key="ind_remember_me")
                
                submitted_ind = st.form_submit_button("Login", use_container_width=True, type="primary")
                
                if submitted_ind:
                    if not email or not password:
                        st.error("Please enter both email and password")
                    else:
                        user = authenticate_individual_user(email, password)
                        if user:
                            from modules.email_verification import send_verification_email
                            if send_verification_email(email, user.get('full_name', 'User'), 'login'):
                                # Store remember_me preference for 2FA completion
                                st.session_state.pending_2fa = {
                                    'user': user, 
                                    'email': email,
                                    'remember_me': remember_me_ind
                                }
                                st.session_state.show_2fa = True
                                st.success("Verification code sent to your email!")
                                st.rerun()
                            else:
                                st.error("Failed to send verification code")
                        else:
                            st.error("❌ Invalid email or password.")

            st.markdown("---")
            st.markdown("<p style='text-align: center; color: #666;'>OR</p>", unsafe_allow_html=True)
            
            # Google Sign-In
            
            st.caption("For consultants, freelancers, and individual users")
            render_google_login_button()
            
            st.markdown("---")
            
            # Registration & Forgot Password Links
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📝 Register as Individual", use_container_width=True):
                    navigate_to(PageRoutes.INDIVIDUAL_REGISTER)
            with col_b:
                if st.button("🔒 Forgot Password?", use_container_width=True, type="secondary"):
                    st.session_state.show_forgot_password = True
                    st.rerun()

    # ====================== 2FA Verification ======================
    if st.session_state.get('show_2fa'):
        st.markdown("---")
        st.markdown("### 🔐 Two-Factor Authentication")
        st.info(f"A verification code has been sent to **{st.session_state.pending_2fa['email']}**")
        
        with st.form("2fa_verification_form"):
            otp = st.text_input("Enter 6-digit verification code", max_chars=6, type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Verify", type="primary", use_container_width=True):
                    from modules.email_verification import verify_otp
                    success, message = verify_otp(st.session_state.pending_2fa['email'], otp)
                    
                    if success:
                        user = st.session_state.pending_2fa['user']
                        remember_me = st.session_state.pending_2fa.get('remember_me', False)
                        
                        # Convert user dict to the expected format for login_user
                        user_tuple = (
                            user.get('id'),
                            user.get('username'),
                            user.get('email'),
                            user.get('full_name'),
                            'individual',
                            1,
                            user.get('company_id'),
                            '',
                            None,
                            1,
                            'individual'
                        )
                        
                        # ✅ Login with remember me option (no cookies parameter)
                        if login_user(user_tuple, None, remember_me):
                            st.session_state.show_2fa = False
                            st.session_state.pending_2fa = None
                            
                            if remember_me:
                                st.info("✅ Session saved to URL! You'll stay logged in even after browser refresh.")
                            
                            navigate_to("dashboard", success_msg=f"Welcome back, {user.get('full_name', 'User')}! 👋")
                            st.rerun()
                        else:
                            st.error("Login failed. Please try again.")
                    else:
                        st.error(message)
            
            with col2:
                if st.form_submit_button("Resend Code", use_container_width=True):
                    from modules.email_verification import send_verification_email
                    if send_verification_email(
                        st.session_state.pending_2fa['email'], 
                        st.session_state.pending_2fa['user'].get('full_name', 'User'), 
                        'login'
                    ):
                        st.success("New verification code sent!")
                    else:
                        st.error("Failed to resend code")
    
    # ====================== Forgot Password Modal ======================
    if st.session_state.get('show_forgot_password'):
        st.markdown("---")
        st.markdown("### 🔒 Reset Your Password")
        
        with st.form("forgot_password_form", clear_on_submit=True):
            email_input = st.text_input(
                "Enter your registered email", 
                value=st.session_state.get('forgot_password_email', '')
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                send_clicked = st.form_submit_button("Send Reset Link", 
                                                   use_container_width=True, 
                                                   type="primary")
            
            with col2:
                cancel_clicked = st.form_submit_button("Cancel", 
                                                     use_container_width=True, 
                                                     type="secondary")
            
            if send_clicked:
                if not email_input or "@" not in email_input:
                    st.error("Please enter a valid email address")
                else:
                    user = db.get_user_by_email(email_input)
                    if user:
                        import secrets
                        reset_token = secrets.token_urlsafe(32)
                        
                        if db.store_password_reset_token(email_input, reset_token):
                            reset_link = f"https://itender-bd.streamlit.app/reset-password?token={reset_token}"
                            from modules.email_verification import send_password_reset_email
                            
                            if send_password_reset_email(email_input, reset_link):
                                st.success(f"✅ Password reset link sent to **{email_input}**")
                                st.session_state.show_forgot_password = False
                                st.rerun()
                            else:
                                st.error("Failed to send reset email. Please try again.")
                        else:
                            st.error("System error. Please try again later.")
                    else:
                        st.error("No account found with this email.")
            
            if cancel_clicked:
                st.session_state.show_forgot_password = False
                st.rerun()

def register_page() -> None:
    """Refactored Registration Page – Company & Individual flows with clear UX"""
    debug_print("📝 Rendering registration page")

    # Page header
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1>📝 Create New Account</h1>
            <p style="color: #555;">Choose the account type that fits you best</p>
        </div>
    """, unsafe_allow_html=True)

    # Two tabs: Company (requires approval) vs Individual (auto-approved)
    tab1, tab2 = st.tabs(["🏢 **Company Registration**", "👤 **Individual Registration**"])

    # ========================= COMPANY REGISTRATION =========================
    with tab1:
        st.markdown("### 🏢 Register as a Company")
        st.caption("For construction companies, contractors, and organisations (requires admin approval)")

        with st.form("company_register_form", clear_on_submit=True):
            # --- Company Information ---
            st.markdown("#### 📌 Company Information")
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("Company Name *", placeholder="e.g., ABC Construction Ltd.")
                company_email = st.text_input("Company Email *", placeholder="info@company.com")
            with col2:
                company_phone = st.text_input("Company Phone *", placeholder="+880 1XXX XXXXXX")
                division = st.selectbox(
                    "Division / Region *",
                    ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
                )

            st.markdown("#### 👤 Admin Account Details")
            col3, col4 = st.columns(2)
            with col3:
                full_name = st.text_input("Full Name (Admin) *", placeholder="John Doe")
                username = st.text_input("Username *", placeholder="johndoe")
            with col4:
                email = st.text_input("Admin Email *", placeholder="john@company.com")
                # No separate phone for admin – reuse company phone

            col5, col6 = st.columns(2)
            with col5:
                password = st.text_input("Password *", type="password", placeholder="••••••••")
            with col6:
                confirm_password = st.text_input("Confirm Password *", type="password", placeholder="••••••••")

            # Password strength meter
            if password:
                score, message, color = validate_password_strength(password)
                st.progress(score / 100, text=f"Strength: {score}%")
                st.markdown(f"<span style='color:{color};'>{message}</span>", unsafe_allow_html=True)

            terms = st.checkbox("I agree to the **Terms of Service** and **Privacy Policy** *", key="comp_reg_terms")

            submitted = st.form_submit_button("🚀 Submit Company Registration", type="primary", use_container_width=True)

            if submitted:
                # Validation
                errors = []
                if not all([company_name, company_email, full_name, email, username, password, division]):
                    errors.append("All fields marked * are required.")
                if password != confirm_password:
                    errors.append("Passwords do not match.")
                if len(password) < 8:
                    errors.append("Password must be at least 8 characters.")
                if score < 60:
                    errors.append("Password is too weak. Please choose a stronger password.")
                if not terms:
                    errors.append("You must accept the Terms of Service.")

                if errors:
                    for err in errors:
                        st.error(f"❌ {err}")
                else:
                    try:
                        # Create company first
                        company_data = {
                            'company_name': company_name.strip(),
                            'email': company_email.strip(),
                            'phone': company_phone.strip(),
                            'division': division
                        }
                        success, result = db.create_company(company_data)
                        if success:
                            company_id = result
                            # Then create admin user
                            user_data = {
                                'username': username.strip(),
                                'password': password,
                                'email': email.strip(),
                                'full_name': full_name.strip(),
                                'phone': company_phone.strip(),
                                'role': 'company_admin',
                                'account_type': 'company',
                                'is_approved': False
                            }
                            user_success, user_result = db.create_user(company_id, user_data, None)
                            if user_success:
                                st.success("✅ Company registration submitted successfully!")
                                st.info("📧 Your account is under review. You will receive an email once approved (usually within 24‑48 hours).")
                                st.balloons()
                                navigate_to("login")
                            else:
                                st.error(f"❌ User creation failed: {user_result}")
                        else:
                            st.error(f"❌ Company creation failed: {result}")
                    except Exception as e:
                        logger.error("Company registration error", exc_info=True)
                        st.error("❌ An unexpected error occurred. Please try again later.")

    # ========================= INDIVIDUAL REGISTRATION =========================
    with tab2:
        st.markdown("### 👤 Register as an Individual")
        st.caption("For freelancers, consultants, and sole proprietors (auto‑approved)")

        # Import and render the existing individual registration module
        from modules.individual_registration import render_individual_registration
        render_individual_registration()

    # ========================= SIDEBAR – Helpful info =========================
    with st.sidebar:
        st.markdown("### 📋 Registration Guidelines")
        st.markdown("""
        **🏢 Company Accounts**
        - Requires admin approval
        - Suitable for teams and organisations
        - Full platform access after approval

        **👤 Individual Accounts**
        - Faster activation (auto‑approved)
        - Ideal for freelancers & consultants
        - Email verification required
        """)
        st.info("💡 Already have an account?")
        if st.button("→ Login Instead", use_container_width=True):
            navigate_to("login")

    debug_print("✅ Registration page render complete")
def register_page_bak() -> None:
    """Registration Page - Separate flows for Company vs Individual"""
    debug_print("📝 Rendering registration page")
    
    render_page_header("📝 Create New Account", "Choose the account type that best fits you")
    
    # Tabs for clear separation
    tab1, tab2 = st.tabs(["🏢 Company Registration", "👤 Individual Registration"])
    
    # ====================== COMPANY REGISTRATION ======================
    with tab1:
        st.markdown("### 🏢 Register as a Company")
        st.caption("For construction companies, contractors, and organizations (requires admin approval)")
        
        with st.form("company_register_form", clear_on_submit=True):
            st.markdown("#### Company Information")
            company_name = st.text_input("Company Name *", key="comp_reg_name")
            company_email = st.text_input("Company Email *", key="comp_reg_email")
            company_phone = st.text_input("Company Phone *", key="comp_reg_phone")
            division = st.selectbox("Division / Region *", 
                ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"],
                key="comp_reg_division"
            )
            
            st.markdown("#### Admin Account Details")
            full_name = st.text_input("Full Name (Admin) *", key="comp_reg_fullname")
            email = st.text_input("Admin Email *", key="comp_reg_admin_email")
            username = st.text_input("Username *", key="comp_reg_username")
            
            password = st.text_input("Password *", type="password", key="comp_reg_password")
            confirm_password = st.text_input("Confirm Password *", type="password", key="comp_reg_confpass")
            
            # Password Strength
            if password:
                score, message, color = validate_password_strength(password)
                st.progress(score / 100)
                st.markdown(f"<p style='color:{color}; font-size:0.9em;'>{message}</p>", unsafe_allow_html=True)
            
            terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *", key="comp_reg_terms")
            
            submitted = st.form_submit_button("Submit Company Registration", 
                                            use_container_width=True, 
                                            type="primary")
            
            if submitted:
                if not all([company_name, company_email, full_name, email, username, password, division]):
                    st.error("❌ Please fill all required fields.")
                elif password != confirm_password:
                    st.error("❌ Passwords do not match.")
                elif len(password) < 8:
                    st.error("❌ Password must be at least 8 characters.")
                elif score < 60:
                    st.error("❌ Password is too weak.")
                elif not terms:
                    st.error("❌ You must accept the terms.")
                else:
                    try:
                        company_data = {
                            'company_name': company_name.strip(),
                            'email': company_email.strip(),
                            'phone': company_phone.strip(),
                            'division': division
                        }
                        
                        success, result = db.create_company(company_data)
                        
                        if success:
                            company_id = result
                            user_data = {
                                'username': username.strip(),
                                'password': password,
                                'email': email.strip(),
                                'full_name': full_name.strip(),
                                'phone': company_phone.strip(),
                                'role': 'company_admin',
                                'account_type': 'company',
                                'is_approved': False
                            }
                            
                            user_success, user_result = db.create_user(company_id, user_data, None)
                            
                            if user_success:
                                st.success("✅ Company registration submitted successfully!")
                                st.info("Your account is under review. You will receive an email once approved (usually within 24-48 hours).")
                                navigate_to("login")
                            else:
                                st.error(f"❌ User creation failed: {user_result}")
                        else:
                            st.error(f"❌ Company creation failed: {result}")
                    except Exception as e:
                        logger.error("Company registration error", exc_info=True)
                        st.error("❌ An error occurred. Please try again.")
    
        # ====================== INDIVIDUAL REGISTRATION ======================
    with tab2:
        # Use the imported individual registration module
        from modules.individual_registration import render_individual_registration
        render_individual_registration()

    
    # Sidebar / Info Box
    with st.sidebar:
        st.markdown("### 📋 Registration Guidelines")
        st.markdown("""
        **Company Accounts:**
        - Require admin approval
        - Suitable for teams
        - Full platform access after approval
        
        **Individual Accounts:**
        - Faster activation
        - Ideal for freelancers & consultants
        - Auto-approved
        """)
        
        st.info("💡 Already have an account?")
        if st.button("→ Login Instead", use_container_width=True):
            navigate_to("login")
    
    debug_print("✅ Registration page render complete")


def pricing_page() -> None:
    """Pricing plans page with interactive selection"""
    debug_print("💰 Rendering pricing page")
    
    # Import and call the subscription module
    from modules.subscription import render_subscription_page
    render_subscription_page()
    
    debug_print("✅ Pricing page render complete")





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
    
def dashboard_page_bak() -> None:
    """Main dashboard for authenticated users"""
    
    # No need for separate header - top navigation handles it
    # Just render dashboard content
        # Add card CSS
    st.markdown("""
    <style>
    .metric-card {
        background: var(--bg-card);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        border: 1px solid var(--border-color);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    
    # Get stats
    stats = db.get_company_stats(st.session_state.company_id) if st.session_state.company_id else {'total_analyses': 0, 'win_rate': 0, 'total_users': 1}
    
    with col1:
        st.metric("📈 Total Analyses", stats.get('total_analyses', 0))
    with col2:
        win_rate = stats.get('win_rate', 0)
        st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
    with col3:
        st.metric("👥 Team Members", stats.get('total_users', 1))
    with col4:
        sub = db.get_user_subscription(st.session_state.user_id)
        limit = sub.get('analyses_limit', 5)
        used = sub.get('analyses_used', 0)
        remaining = "∞" if limit == -1 else max(0, limit - used)
        st.metric("📊 Analyses Left", remaining)
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📋 Tenders", use_container_width=True):
            st.session_state.page = "tender_management"
            st.rerun()
    
    with col2:
        if st.button("📊 BOQ Generator", use_container_width=True):
            st.session_state.page = "boq_generator"
            st.rerun()
    
    with col3:
        print("🔍 RENDERING DASHBOARD PAGE - START NEW ANALYSIS BUTTON")
        if st.button("🔍 Start New Analysis", key="dashboard_start_new_analysis_btn", use_container_width=True, type="primary"):
            navigate_to("new_analysis")

    with col4:
        if st.button("🎯 Bid Optimizer", use_container_width=True):
            st.session_state.page = "boq_bid_optimizer"
            st.rerun()
    
    with col5:
        if st.session_state.user_role in ['admin', 'system_admin', 'company_admin']:
            if st.button("👥 Team Management", use_container_width=True):
                st.session_state.page = "user_management"
                st.rerun()
    
    # Recent analyses table
    st.markdown("### 🕐 Recent Analyses")
    
    try:
        recent_df = db.get_user_analyses(
            user_id=st.session_state.user_id,
            company_id=st.session_state.company_id,
            role=st.session_state.user_role,
            limit=5
        )
        
        if recent_df is not None and not recent_df.empty:
            # Display recent analyses
            for _, analysis in recent_df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1.5, 1])
                with col1:
                    st.markdown(analysis.get('tender_title', 'Untitled')[:50])
                with col2:
                    st.markdown(f"BDT {analysis.get('recommended_bid', 0):,.0f}")
                with col3:
                    win_prob = analysis.get('success_probability', 0) or 0
                    win_pct = win_prob * 100 if win_prob <= 1 else win_prob
                    st.markdown(f"{win_pct:.1f}%")
                with col4:
                    status = analysis.get('bid_status', 'draft')
                    emoji = {"won": "🏆", "lost": "❌", "submitted": "📤", "draft": "⚪"}.get(status, "⚪")
                    st.markdown(f"{emoji} {status.title()}")
                with col5:
                    if st.button("View", key=f"view_{analysis.get('id')}"):
                        st.session_state.selected_analysis_id = analysis.get('id')
                        st.session_state.page = "history"
                        st.rerun()
                st.markdown("---")
        else:
            st.info("📭 No analyses yet. Start your first analysis!")
    except Exception as e:
        st.info("📭 Start your first analysis to see recent activity here!")


def history_page() -> None:
    """History page - delegates to analysis_history module"""
    debug_print("📜 Rendering history page from analysis_history module")
    
    # Import and call the module's function
    from modules.analysis_history import show_analysis_history
    show_analysis_history()


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


def _nav_button(label: str, page_key: str, badge: str = None):
    """Helper function to render navigation buttons without duplicate icons"""
    
    # Map page keys to actual route strings
    page_routes = {
        # Core Workflow
        "tender_management": "tender_management",
        "boq_generator": "boq_generator",
        "boq_bid_optimizer": "boq_bid_optimizer",
        
        # Analysis
        "dashboard": "dashboard",
        "new_analysis": "new_analysis",
        "history": "history",
        "historical_data": "historical_data",
        "competitor_tracking": "competitor_tracking",
        "competitor_master": "competitor_master",
        "post_evaluation": "post_evaluation",
        "intelligent_suggestions": "intelligent_suggestions",
        "scenario_generator": "scenario_generator",
        # Company Management
        "company_dashboard": "company_dashboard",
        "egp_boq_workspace": "egp_boq_workspace",
        "user_management": "user_management",
        
        # Rate Management
        "rate_management": "rate_management",
        "rate_viewer": "rate_viewer",
        
        # Administration
        "admin_dashboard": "admin_dashboard",
        "boq_admin_report": "boq_admin_report",
        "user_approval": "user_approval",
        "role_management": "role_management",
        "company_management": "company_management",
        
        # System Tools
        "version_management": "version_management",
        "rollback_management": "rollback_management",
        "subscription": "subscription",
        "profile": "profile",
        
        # Help
        "tutorial": "tutorial"
    }
    
    route = page_routes.get(page_key, page_key)
    is_active = st.session_state.get('page') == route
    
    # Create display text with badge if provided
    display_text = label
    if badge:
        display_text = f"{label} <span style='background:#ef4444; color:white; padding:0px 6px; border-radius:10px; font-size:0.7rem; margin-left:5px;'>{badge}</span>"
    
    if is_active:
        # Active button styling
        st.markdown(f"""
        <div style="background: #667eea; border-radius: 8px; margin: 2px 0;">
            <div style="padding: 8px 12px; color: white; font-weight: bold;">
                {display_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Inactive button
        if st.button(display_text, key=f"nav_{route}", use_container_width=True):
            st.session_state.page = route
            st.rerun()

def render_sidebar() -> None:
    """Optimized sidebar with role-based navigation - ONLY for logged-in users"""
    if not st.session_state.get('logged_in'):
        return
    
    debug_print("🧭 Rendering sidebar")
    
    with st.sidebar:
        # Clear extracted data if leaving tender management page
        if st.session_state.page != 'tender_management' and 'extracted_data' in st.session_state:
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
        
        from version import get_app_name, get_app_desc

        # ========== BRANDING ==========
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #eee;">
            <h2 style="margin: 0; color: #1e3c72;">🏗️ {get_app_name()}</h2>
            <small style="color: #666;">{get_app_desc()}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # ========== USER INFO & BADGE ==========
        if st.session_state.get('logged_in'):
            full_name = st.session_state.get('full_name', 'User')
            company_name = st.session_state.get('company_name', 'N/A')
            user_role = st.session_state.get('user_role', 'User')
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); 
                        padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
                <strong>👋 {full_name}</strong><br>
                <small>🏢 {company_name}<br>
                ⭐ {safe_title(user_role, 'User')}</small>
            </div>
            """, unsafe_allow_html=True)
            
            sub = db.get_user_subscription(st.session_state.user_id) if st.session_state.get('user_id') else {}
            plan = sub.get('plan', 'free')
            is_premium = plan in ['professional', 'enterprise'] or st.session_state.get('user_role') in ['admin', 'system_admin']
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
        
        # ========== LOGOUT BUTTON (TOP) ==========
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 👤 Account")
        with col2:
            if st.button("🚪", key="nav_logout_icon", help="Sign Out", use_container_width=True):
                logout_user()
                for key in list(st.session_state.keys()):
                    if key not in ['debug_mode', 'page']:
                        del st.session_state[key]
                initialize_session_state()
                st.toast("👋 You have been signed out", icon="✅")
                st.rerun()
        
        st.markdown("---")
        
        # ========== SECTION 1: CORE WORKFLOW ==========
        user_role = st.session_state.get('user_role', 'user')
        
        st.markdown("### 🚀 Core Workflow")
        
        _nav_button("📋 Tender Management", "tender_management")
        
        if user_role != 'viewer':
            _nav_button("📄 BOQ Generator", "boq_generator")
        
        if user_role != 'viewer':
            _nav_button("🎯 BOQ to Bid Optimizer", "boq_bid_optimizer")
        
        st.markdown("---")
        
        # ========== SECTION 2: ANALYSIS & INTELLIGENCE ==========
        st.markdown("### 📊 Analysis & Intelligence")
        
        _nav_button("📈 Dashboard", "dashboard")
        _nav_button("🎯 New Analysis", "new_analysis")
        _nav_button("📜 History", "history")
        
        # Premium features (requires is_premium defined)
        is_system_admin = st.session_state.get('user_role') == 'system_admin'

        if is_premium or is_system_admin:
            _nav_button("📊 Historical Data", "historical_data")
            _nav_button("👥 Competitor Tracking", "competitor_tracking")
            _nav_button("🗂️ Competitor Master", "competitor_master")
            _nav_button("📋 Post-Evaluation", "post_evaluation")
            _nav_button("🧠 AI Suggestions", "intelligent_suggestions")
            _nav_button("🧠 Scenario Generator", "scenario_generator")  # Fixed!
        
        st.markdown("---")
        
        # ========== SECTION 3: COMPANY MANAGEMENT ==========
        if user_role in ['company_admin', 'admin', 'system_admin']:
            st.markdown("### 🏢 Company Management")
            _nav_button("🏢 Company Dashboard", "company_dashboard")
            _nav_button("🏗️ e-GP BOQ Workspace", "egp_boq_workspace")
            _nav_button("👥 Team Management", "user_management")
            st.markdown("---")
        
        # ========== SECTION 4: RATE MANAGEMENT ==========
        if user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst', 'data_entry']:
            st.markdown("### 🏗️ Rate Management")
            _nav_button("📝 Rate Management", "rate_management")
            _nav_button("📊 Rate Viewer", "rate_viewer")
            st.markdown("---")
        
        # ========== SECTION 5: ADMINISTRATION ==========
        if user_role in ['admin', 'system_admin']:
            st.markdown("### 👑 Administration")
            _nav_button("📊 Admin Dashboard", "admin_dashboard")
            _nav_button("📊 BOQ Report", "boq_admin_report")
            
            pending_count = 0
            try:
                if hasattr(db, 'get_pending_users'):
                    pending_count = len(db.get_pending_users(None))
            except:
                pass
            
            _nav_button("👥 User Approvals", "user_approval", badge=pending_count if pending_count > 0 else None)
            _nav_button("🔐 Role Permissions", "role_management")
            _nav_button("🏢 All Companies", "company_management")
            st.markdown("---")
        
        # ========== SECTION 6: SYSTEM TOOLS ==========
        st.markdown("### ⚙️ System Tools")
        
        if user_role in ['admin', 'system_admin']:
            _nav_button("📦 Version Management", "version_management")
            _nav_button("🔄 Rollback Management", "rollback_management")
        
        _nav_button("💳 Subscription", "subscription")
        _nav_button("👤 Profile", "profile")
        
        st.markdown("---")
        
        # ========== SECTION 7: HELP & SUPPORT ==========
        st.markdown("### 📚 Help & Support")
        _nav_button("📖 Tutorial", "tutorial")
        st.markdown("---")
        
        # ========== USAGE STATS ==========
        if is_premium and sub:
            limit = sub.get('analyses_limit', -1)
            used = sub.get('analyses_used', 0)
            if limit > 0:
                remaining = max(0, limit - used)
                pct_used = min(100, (used / limit) * 100)
                st.markdown(f"""
                <div style="font-size: 0.8rem; color: #666; text-align: center;">
                    <strong>📊 Monthly Usage</strong><br>
                    {used}/{limit} analyses used<br>
                    <div style="background: #e5e7eb; border-radius: 4px; height: 4px; margin: 4px 0;">
                        <div style="background: #667eea; width: {pct_used}%; height: 100%; border-radius: 4px;"></div>
                    </div>
                    <small>{remaining} remaining this month</small>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("---")
        
        # ========== FULL LOGOUT BUTTON (BOTTOM) ==========
        if st.button("🚪 Sign Out", key="nav_logout", use_container_width=True, type="secondary"):
            logout_user()
            for key in list(st.session_state.keys()):
                if key not in ['debug_mode', 'page']:
                    del st.session_state[key]
            initialize_session_state()
            st.toast("👋 You have been signed out", icon="✅")
            st.rerun()
        
        # ========== VERSION INFO ==========
        from version import __version__, __version_date__
        st.markdown("---")
        st.caption(f"📌 Version {__version__} | {__version_date__}")
        st.caption("💡 Need help? [Contact Support](mailto:support@tenderai.com)")
        
        if DEBUG_MODE:
            st.markdown("---")
            st.caption("🐛 Debug Mode Active")

# =============================================================================
# 🎬 MAIN APP ROUTER (Refactored + Optimized)
# =============================================================================

def _render_public_pages() -> None:
    """Render pages for non-authenticated users"""
    from modules.individual_registration import render_individual_registration, render_individual_login
    
    page_handlers = {
        'home': lambda: show_landing_page(),  # Use the new landing page
        'login': login_page,
        'register': register_page,
        'pricing': pricing_page,
        'about': lambda: show_about_page(),  # Use the new about page
        'contact': contact_page,
        'individual_register': render_individual_registration,
        'individual_login': render_individual_login,
    }
    
    handler = page_handlers.get(st.session_state.page, home_page)
    handler()


def _render_authenticated_pages() -> None:
    """Render pages for authenticated users with top navigation"""
    
    from modules.top_navigation import render_top_navigation
    
    # Render top navigation bar (appears on all authenticated pages)
    render_top_navigation()
    
    # Page handlers (your existing code)
    PAGE_HANDLERS: Dict[str, Callable] = {
        # Core pages
        PageRoutes.DASHBOARD: dashboard_page,
        PageRoutes.NEW_ANALYSIS: render_tender_analysis,
        PageRoutes.HISTORY: history_page,
        PageRoutes.PROFILE: profile_page,
        PageRoutes.ADMIN_DASHBOARD: admin_dashboard_page,
        PageRoutes.SUBSCRIPTION: lambda: render_subscription_page(),
        PageRoutes.USER_MANAGEMENT: lambda: render_user_management(),
         # ========== ADD THESE MISSING HANDLERS ==========
        PageRoutes.RATE_MANAGEMENT: lambda: render_rate_crud_forms(db),
        PageRoutes.IMPORT_WIZARD: lambda: render_unified_import_wizard(db),
        
        PageRoutes.RATE_VIEWER: lambda: _import_and_call('modules.rate_viewer', 'render_rate_viewer', db),

        # Advanced modules (lazy import)
        PageRoutes.TENDER_MANAGEMENT: lambda: _import_and_call('modules.tender_management', 'render_tender_management'),
        PageRoutes.POST_EVALUATION: lambda: _import_and_call('modules.post_evaluation', 'render_post_evaluation_page'),
        PageRoutes.INTELLIGENT_SUGGESTIONS: lambda: _import_and_call('modules.post_evaluation', 'render_intelligent_suggestions'),
        PageRoutes.HISTORICAL_DATA: lambda: _import_and_call('modules.historical_data', 'render_historical_data_page'),
        PageRoutes.ANALYSIS_HISTORY: lambda: _import_and_call('modules.analysis_history', 'show_analysis_history'),
        PageRoutes.COMPETITOR_TRACKING: lambda: _import_and_call('modules.competitor_tracking', 'render_competitor_tracking_page'),
        PageRoutes.COMPETITOR_MASTER: lambda: _import_and_call('modules.competitor_master', 'render_competitor_master_page'),
        PageRoutes.USER_APPROVAL: lambda: _import_and_call('modules.user_approval', 'render_user_approval_page'),
        PageRoutes.ROLE_MANAGEMENT: lambda: _import_and_call('modules.user_management', 'render_role_management'),
        PageRoutes.COMPANY_DASHBOARD: lambda: _import_and_call('_pages.company_dashboard', 'show'),        
        PageRoutes.EGP_BOQ_WORKSPACE: lambda: _import_and_call('modules.egp_boq_workspace', 'render_boq_workspace'),
        PageRoutes.TUTORIAL: lambda: _import_and_call('modules.tutorials', 'render_tutorial'),
        PageRoutes.BOQ_GENERATOR: lambda: _import_and_call('modules.boq_generator_ui', 'render_boq_generator'),
        PageRoutes.BOQ_ADMIN_REPORT: lambda: _import_and_call('modules.boq_admin_report', 'render_boq_admin_report'),
        PageRoutes.BOQ_BID_OPTIMIZER: lambda: _import_and_call('modules.boq_bid_bridge', 'render_boq_bid_integration'),
        PageRoutes.SCENARIO_GENERATOR: lambda: render_bid_scenario_generator_ui(db, SubscriptionManager(db))


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

# =============================================================================
# 🎨 HEADER COMPONENT (For Public Pages)
# =============================================================================

def render_header_nav() -> None:
    """Render header navigation menu for non-authenticated users"""
    
    # Custom CSS for header navigation
    st.markdown("""
    <style>
        /* Remove gap below header */
        .header-nav-container {
            margin-bottom: -1rem !important;
        }
        
        .header-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 2rem;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            border-radius: 0 0 10px 10px;
            margin-bottom: 0rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header-logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header-logo h2 {
            color: white;
            margin: 0;
            font-size: 1.5rem;
        }
        .header-logo p {
            color: rgba(255,255,255,0.8);
            margin: 0;
            font-size: 0.8rem;
        }
        .header-menu {
            display: flex;
            gap: 1rem;
        }
        /* Style Streamlit buttons to look like navigation links */
        .header-menu .stButton > button {
            background: transparent !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            border-radius: 5px !important;
            font-weight: normal !important;
            font-size: 1rem !important;
            width: auto !important;
            margin: 0 !important;
            box-shadow: none !important;
        }
        .header-menu .stButton > button:hover {
            background: rgba(255,255,255,0.2) !important;
            transform: none !important;
        }
        .header-menu .active .stButton > button {
            background: rgba(255,255,255,0.3) !important;
            font-weight: bold !important;
        }
        .btn-login .stButton > button {
            background: transparent !important;
            border: 1px solid white !important;
        }
        .btn-register .stButton > button {
            background: #22c55e !important;
        }
        .btn-register .stButton > button:hover {
            background: #16a34a !important;
        }
        @media (max-width: 768px) {
            .header-nav {
                flex-direction: column;
                gap: 1rem;
                padding: 1rem;
            }
            .header-menu {
                flex-wrap: wrap;
                justify-content: center;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Create header using Streamlit columns (this works reliably)
    with st.container():
        # Use columns for layout
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("""
            <div class="header-logo">
                <h2>🏗️ TenderAI</h2>
                <p>Bid Optimization Platform</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Get current page
            current_page = st.session_state.get('page', 'home')
            
            # Create a row of buttons
            menu_cols = st.columns(6)
            
            pages = [
                ("🏠 Home", "home"),
                ("💰 Pricing", "pricing"),
                ("ℹ️ About", "about"),
                ("📞 Contact", "contact"),
                ("🔐 Login", "login"),
                ("➕ Register", "register"),
            ]
            
            for idx, (label, page_key) in enumerate(pages):
                with menu_cols[idx]:
                    # Determine button type
                    if page_key in ['login', 'register']:
                        btn_class = "btn-login" if page_key == 'login' else "btn-register"
                    else:
                        btn_class = ""
                    
                    # Check if this is the active page
                    is_active = current_page == page_key
                    button_type = "primary" if is_active else "secondary"
                    
                    # Create the button
                    if st.button(label, key=f"nav_{page_key}", use_container_width=True, type=button_type):
                        st.session_state.page = page_key
                        st.rerun()

def main() -> None:
    """
    Main application entry point with optimized routing.
    """
    import base64
    import json
    
    # Initialize theme
    init_theme()
    
    # Apply theme CSS
    apply_theme()

    # =========================================================================
    # RESTORE SESSION FROM URL PARAMETER (Google OAuth)
    # =========================================================================
    query_params = st.query_params
    
    # Check for user data in URL (from Google callback)
    if 'user' in query_params:
        try:
            user_data_b64 = query_params['user']
            user_data_json = base64.urlsafe_b64decode(user_data_b64).decode()
            user_data = json.loads(user_data_json)
            
            # Restore session state
            for key, value in user_data.items():
                st.session_state[key] = value
            
            # Clear the parameter to avoid re-processing
            st.query_params.clear()
            # Force rerun to show dashboard
            st.rerun()
            return
        except Exception as e:
            debug_print(f"Error restoring session: {e}")
    
    # =========================================================================
    # HANDLE GOOGLE OAUTH CALLBACK
    # =========================================================================
    from modules.google_auth import handle_google_callback
    
    # Check if this is an OAuth callback
    if 'code' in query_params:
        # Handle the callback - this will process the code and redirect
        handle_google_callback()
        # After handling, clear params and rerun to avoid reprocessing
        st.query_params.clear()
        st.rerun()
        return

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
    
    # =========================================================================
    # CONDITIONAL HEADER & SIDEBAR RENDERING
    # =========================================================================
    
    # ONLY render app header for logged-in users
    if st.session_state.logged_in:
        # Pass the dark mode toggle to be rendered inside the header
        render_app_header(show_dark_mode_toggle=True)
    
    if st.session_state.logged_in:
        # For logged-in users, show sidebar (without dark mode toggle)
        with st.sidebar:
            render_sidebar()
    else:
        # For non-authenticated users, show header navigation
        render_header_nav()
    
    # Handle checkout flow (modal-like experience)
    if st.session_state.get('show_checkout'):
        render_checkout()
        return
    
    # Route to appropriate page handler
    if not st.session_state.logged_in:
        _render_public_pages()
    else:
        _render_authenticated_pages()
    
    # =========================================================================
    # RENDER FOOTER (Only for logged-in users)
    # =========================================================================
    if st.session_state.logged_in:
        from modules.ui_components import render_footer
        render_footer()
    
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

def _handle_subscription_redirect():
    """Redirect to appropriate subscription page based on user type"""
    account_type = st.session_state.get('account_type', 'company')
    if account_type == 'individual':
        from subscription import render_subscription_page
        render_subscription_page()
    else:
        show_company_subscription()


def _handle_company_dashboard():
    """Handle company dashboard - redirect to subscriber dashboard for non-admins"""
    user_role = st.session_state.get('user_role', 'viewer')
    
    if user_role in ['admin', 'system_admin']:
        # Admins see company dashboard with management features
        show_company_dashboard()
    else:
        # Subscribers see their project dashboard
        render_subscriber_dashboard(db)


def _handle_admin_dashboard():
    """Handle admin dashboard with proper navigation"""
    from _pages.admin_dashboard import show as show_admin_dashboard
    show_admin_dashboard()


def _handle_premium_feature(feature_func):
    """Check subscription before showing premium features"""
    company_id = st.session_state.get('company_id')
    
    if not company_id:
        st.error("Company information not found")
        return
    
    # Check if user has access to premium features
    from modules.subscription_manager import SubscriptionManager
    sub_manager = SubscriptionManager(db)
    sub = sub_manager.get_company_subscription(company_id)
    
    # Professional and Enterprise plans have access
    if sub.get('plan') in ['professional', 'enterprise']:
        feature_func()
    else:
        st.warning("🔒 This is a premium feature")
        st.info(f"Your current plan: **{sub.get('plan_name', 'Free')}**")
        st.markdown("**Upgrade to Professional or Enterprise to access:**")
        st.markdown("- Competitor tracking and analysis")
        st.markdown("- Historical data analysis")
        st.markdown("- Post-bid evaluation")
        st.markdown("- Intelligent suggestions")
        
        if st.button("💳 Upgrade Now", use_container_width=True):
            st.session_state.page = "subscription"
            st.rerun()

def _access_denied():
    """Show access denied message"""
    st.error("❌ Access Denied")
    st.info("You don't have permission to access this page.")
    if st.button("← Return to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

def debug_competitor_bids_state(location: str):
    """Debug helper to track competitor bids through session state"""
    debug_print(f"\n📍 COMPETITOR DEBUG [{location}]")
    debug_print(f"  analysis_competitor_bids: {len(st.session_state.get('analysis_competitor_bids', []))}")
    debug_print(f"  current_competitor_bids: {len(st.session_state.get('current_competitor_bids', []))}")
    debug_print(f"  auto_competitor_count: {st.session_state.get('auto_competitor_count', 3)}")
    debug_print(f"  analysis_bid_source: {st.session_state.get('analysis_bid_source', 'N/A')}")
    
    # Show actual data if available
    comp_bids = st.session_state.get('analysis_competitor_bids', [])
    if comp_bids:
        debug_print(f"  Sample: {comp_bids[0] if comp_bids else 'None'}")

def upgrade_admin_once():
    if st.session_state.get('_admin_upgraded', False):
        return
    if st.session_state.get('logged_in') and st.session_state.get('user_role') == 'admin':
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub.get('plan') == 'free':
            db.update_subscription(st.session_state.user_id, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
            st.session_state.subscription_plan = 'professional'
            st.session_state._admin_upgraded = True

# =============================================================================
# 🎬 APP LAUNCH (Final safety)
# =============================================================================
if __name__ == "__main__":
    # ✅ Ensure imports are available
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    
    debug_print("🎬 Starting TenderAI application...")
    #upgrade_admin_once()  # Ensure admin users are upgraded at startup (one-time check)
    #db.update_role_permissions_for_rates()

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
                'historical_data', 'analysis_history', 'competitor_tracking', 'scenario_generator,' 'competitor_master',
                'admin_dashboard', 'user_approval', 'role_management', 'tutorial'
            ]
            
            missing = [r for r in required_routes if r not in PageRoutes.get_all_routes()]
            if missing:
                debug_print(f"❌ Missing PageRoutes attributes: {missing}")
            else:
                debug_print("✅ All PageRoutes attributes present")
    
    debug_print("✅ App render cycle complete\n")