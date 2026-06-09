# _pages/company_subscription.py

import streamlit as st
from modules.subscription_manager import SubscriptionManager
from database.db_manager import DatabaseManager

def show_company_subscription():
    """Show company subscription management page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>💳 Company Subscription</h1>
        <p>Manage your plan, billing, and team access</p>
    </div>
    """, unsafe_allow_html=True)
    
    db = DatabaseManager()
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role', 'viewer')
    
    if not company_id:
        st.error("No company found. Please contact support.")
        return
    
    sub_manager = SubscriptionManager(db)
    current_sub = sub_manager.get_company_subscription(company_id)
    
    # Debug: Print what's in current_sub
    if st.session_state.get('debug_mode', False):
        st.write("Debug - Subscription data:", current_sub)
    
    # Display current subscription
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Plan", current_sub.get('plan_name', 'Free').upper())
    with col2:
        st.metric("Status", current_sub.get('status', 'active').upper())
    with col3:
        remaining_boq = current_sub.get('max_boq_generations', 5) - current_sub.get('boq_used', 0)
        if current_sub.get('max_boq_generations', 5) == -1:
            remaining_boq = "∞"
        st.metric("BOQ Remaining", remaining_boq)
    with col4:
        remaining_analyses = current_sub.get('max_tender_analyses', 5) - current_sub.get('analyses_used', 0)
        if current_sub.get('max_tender_analyses', 5) == -1:
            remaining_analyses = "∞"
        st.metric("Analyses Remaining", remaining_analyses)
    
    # Display plan features
    st.markdown("### 📋 Plan Features")
    
    features = [
        ("📊 BOQ Generations", f"{current_sub.get('max_boq_generations', 5) if current_sub.get('max_boq_generations', 5) != -1 else 'Unlimited'}/month"),
        ("🎯 Bid Optimizations", f"{current_sub.get('max_bid_optimizations', 5) if current_sub.get('max_bid_optimizations', 5) != -1 else 'Unlimited'}/month"),
        ("📈 Tender Analyses", f"{current_sub.get('max_tender_analyses', 5) if current_sub.get('max_tender_analyses', 5) != -1 else 'Unlimited'}/month"),
        ("👥 Team Members", f"{current_sub.get('max_users', 1) if current_sub.get('max_users', 1) != -1 else 'Unlimited'} users"),
        ("📤 Export Data", "✅" if current_sub.get('can_export_data', False) else "❌"),
        ("✏️ Edit Rates", "✅" if current_sub.get('can_edit_rates', False) else "❌"),
        ("🗑️ Delete Rates", "✅" if current_sub.get('can_delete_rates', False) else "❌"),
        ("👥 Manage Team", "✅" if current_sub.get('can_manage_team', False) else "❌"),
    ]
    
    col1, col2 = st.columns(2)
    for i, (feature, value) in enumerate(features):
        with col1 if i % 2 == 0 else col2:
            st.markdown(f"**{feature}:** {value}")
    
    # Usage progress
    st.markdown("---")
    st.markdown("### 📊 Current Usage")
    
    # BOQ Usage
    max_boq = current_sub.get('max_boq_generations', 5)
    boq_used = current_sub.get('boq_used', 0)
    if max_boq != -1:
        boq_percent = (boq_used / max_boq) * 100 if max_boq > 0 else 0
        st.progress(min(boq_percent / 100, 1.0))
        st.caption(f"BOQ Usage: {boq_used} / {max_boq} ({boq_percent:.0f}%)")
    else:
        st.progress(0)
        st.caption("BOQ Usage: Unlimited")
    
    # Analysis Usage
    max_analyses = current_sub.get('max_tender_analyses', 5)
    analyses_used = current_sub.get('analyses_used', 0)
    if max_analyses != -1:
        analysis_percent = (analyses_used / max_analyses) * 100 if max_analyses > 0 else 0
        st.progress(min(analysis_percent / 100, 1.0))
        st.caption(f"Analyses Usage: {analyses_used} / {max_analyses} ({analysis_percent:.0f}%)")
    else:
        st.progress(0)
        st.caption("Analyses Usage: Unlimited")
    
    # Team usage
    max_users = current_sub.get('max_users', 1)
    if max_users != -1:
        try:
            current_users = sub_manager._get_company_user_count(company_id)
            user_percent = (current_users / max_users) * 100 if max_users > 0 else 0
            st.progress(min(user_percent / 100, 1.0))
            st.caption(f"Team Members: {current_users} / {max_users} ({user_percent:.0f}%)")
        except:
            st.caption(f"Team Members: Up to {max_users} users")
    else:
        st.progress(0)
        st.caption("Team Members: Unlimited")
    
    # Upgrade options (only for non-enterprise and admins)
    can_manage = user_role in ['admin', 'system_admin', 'company_admin']
    
    if can_manage and current_sub.get('plan') != 'enterprise':
        st.markdown("---")
        st.markdown("### 🚀 Upgrade Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Upgrade to Professional", use_container_width=True):
                st.session_state.page = "subscription"
                st.rerun()
        
        with col2:
            if st.button("Contact Sales for Enterprise", use_container_width=True):
                st.info("📧 sales@tenderai.com | 📞 +880 1234 567890")
    
    # Show warning if limits are near
    if max_boq != -1 and boq_used >= max_boq * 0.8:
        st.warning(f"⚠️ You have used {boq_used}/{max_boq} BOQ generations. Consider upgrading for more capacity.")
    
    if max_analyses != -1 and analyses_used >= max_analyses * 0.8:
        st.warning(f"⚠️ You have used {analyses_used}/{max_analyses} analyses. Consider upgrading for more capacity.")