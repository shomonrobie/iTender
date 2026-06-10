import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from datetime import datetime

db = DatabaseManager()

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
    analyses_df = db.get_user_analyses(
        st.session_state.user_id, 
        st.session_state.company_id, 
        st.session_state.user_role,
        limit=10
    )
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 Total Analyses</h3>
            <h2>{stats['total_analyses']}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:  
        st.markdown(f"""
        <div class="metric-card">
            <h3>🏆 Win Rate</h3>
            <h2>{stats['win_rate']:.0f}%</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>👥 Team Members</h3>
            <h2>{stats['total_users']}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Get subscription info
        sub = db.get_user_subscription(st.session_state.user_id)
        if sub['analyses_limit'] == -1:
            remaining = "Unlimited"
        else:
            remaining = sub['analyses_limit'] - sub['analyses_used']
            remaining = max(0, remaining)
        st.markdown(f"""
        <div class="metric-card">
            <h3>📈 Analyses Left</h3>
            <h2>{remaining}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick actions
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📋 Tenders", use_container_width=True):
            st.session_state.page = "tender_management"
            st.rerun()
    with col2:
        if st.button("📊 New Analysis", use_container_width=True):
            st.session_state.page = "new_analysis"
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
        #if st.button("👥 Manage Team", use_container_width=True):
        #    st.session_state.page = "user_management"
        #    st.rerun()
    
    with col5:
        if st.button("💳 Upgrade Plan", use_container_width=True):
            st.session_state.page = "subscription"
            st.rerun()
    
    # Recent analyses
    if len(analyses_df) > 0:
        st.markdown("### 📋 Recent Analyses")
        display_cols = ['tender_id', 'tender_title', 'procuring_entity', 'recommended_bid', 'bid_status']
        available_cols = [col for col in display_cols if col in analyses_df.columns]
        if available_cols:
            st.dataframe(analyses_df[available_cols].head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No analyses yet. Create your first analysis!")
    
    # Subscription alert if trial ending
    sub = db.get_user_subscription(st.session_state.user_id)
    if sub['status'] == 'trial' and sub['end_date']:
        from datetime import datetime
        end_date = datetime.strptime(sub['end_date'], '%Y-%m-%d')
        days_left = (end_date - datetime.now()).days
        if days_left <= 7:
            st.warning(f"⚠️ Your trial ends in {days_left} days. Upgrade to continue using premium features!")