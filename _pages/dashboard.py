# _pages/dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()


def show():
    """User dashboard page"""
    
    st.markdown(f"""
    <div class="main-header">
        <h1>Welcome, {st.session_state.full_name}! 👋</h1>
        <p>{st.session_state.company_name} | {st.session_state.subscription_plan.upper()} Plan</p>
    </div>
    """, unsafe_allow_html=True)
    
    user_role = st.session_state.get('user_role', 'viewer')
    is_admin = user_role in ['admin', 'system_admin']
    is_company_admin = user_role in ['admin', 'system_admin', 'company_admin']
    is_analyst = user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst']
    can_edit = user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst']

    # Get user statistics
    stats = db.get_company_stats(st.session_state.company_id)
    
    # Get analyses with safe defaults
    try:
        analyses_df = db.get_user_analyses(
            st.session_state.user_id, 
            st.session_state.company_id, 
            st.session_state.user_role,
            limit=10
        )
    except Exception as e:
        print(f"Error getting analyses: {e}")
        analyses_df = pd.DataFrame()
    
    # Key metrics with safe defaults
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_analyses = stats.get('total_analyses', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 Total Analyses</h3>
            <h2>{total_analyses}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        win_rate = stats.get('win_rate', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h3>🏆 Win Rate</h3>
            <h2>{win_rate:.0f}%</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        total_users = stats.get('total_users', 1)
        st.markdown(f"""
        <div class="metric-card">
            <h3>👥 Team Members</h3>
            <h2>{total_users}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Get subscription info safely
        try:
            sub = db.get_user_subscription(st.session_state.user_id)
            analyses_limit = sub.get('analyses_limit', 5)
            analyses_used = sub.get('analyses_used', 0)
            
            if analyses_limit == -1:
                remaining = "Unlimited"
            else:
                remaining = max(0, analyses_limit - analyses_used)
        except Exception as e:
            print(f"Error getting subscription: {e}")
            remaining = "N/A"
        
        st.markdown(f"""
        <div class="metric-card">
            <h3>📈 Analyses Left</h3>
            <h2>{remaining}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Extension Status Section
    st.markdown("### 🤖 Extension Status")
    
    # Get extension usage safely
    try:
        usage = db.get_extension_fill_usage(st.session_state.company_id)
        is_unlimited = usage.get('is_unlimited', False)
        remaining_fills = usage.get('remaining', 0)
    except Exception as e:
        print(f"Error getting extension usage: {e}")
        is_unlimited = False
        remaining_fills = 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if is_unlimited:
            st.info("🎯 **Extension Auto-Fill**: Unlimited")
        else:
            if remaining_fills > 0:
                st.success(f"🎯 **Extension Auto-Fill**: {remaining_fills} fills remaining this month")
            else:
                st.warning(f"🎯 **Extension Auto-Fill**: 0 fills remaining - Please upgrade")
    
    with col2:
        #st.caption("📥 **Install Extension**")
        if st.button("Get Chrome Extension", use_container_width=True):
            st.info("Contact admin for extension download link")
    
    with col3:
        if not is_unlimited and remaining_fills == 0:
            if st.button("💳 Upgrade for More", use_container_width=True):
                st.session_state.page = "subscription"
                st.rerun()

    # Quick actions
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📋 Tenders", use_container_width=True):
            st.session_state.page = "tender_management"
            st.rerun()
    with col2:
        if st.button("📊 New Analysis", use_container_width=True):
            st.session_state.page = "boq_bid_optimizer"
            st.rerun()
            
    
    with col3:
        if st.button("📜 View History", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    
    with col4:
        if is_company_admin:
            if st.button("👥 Team Management", use_container_width=True):
                st.session_state.page = "user_management"
                st.rerun()
        else:
            st.button("🔒 Team Management", disabled=True, use_container_width=True,
                    help="Only company admins can manage team")
    
    with col5:
        if st.button("💳 Upgrade Plan", use_container_width=True):
            st.session_state.page = "subscription"
            st.rerun()
    
    # Recent analyses
    if analyses_df is not None and len(analyses_df) > 0:
        st.markdown("### 📋 Recent Analyses")
        display_cols = ['tender_id', 'tender_title', 'procuring_entity', 'recommended_bid', 'bid_status']
        available_cols = [col for col in display_cols if col in analyses_df.columns]
        if available_cols:
            st.dataframe(analyses_df[available_cols].head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No analyses yet. Create your first analysis!")
    
    # Subscription alert if trial ending (safely)
    try:
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub.get('status') == 'trial' and sub.get('end_date'):
            end_date = datetime.strptime(sub['end_date'], '%Y-%m-%d')
            days_left = (end_date - datetime.now()).days
            if 0 < days_left <= 7:
                st.warning(f"⚠️ Your trial ends in {days_left} days. Upgrade to continue using premium features!")
            elif days_left <= 0:
                st.error("⚠️ Your trial has ended. Please upgrade to continue using premium features!")
    except Exception as e:
        print(f"Error checking subscription trial: {e}")