# modules/user_approval.py

import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager

db = DatabaseManager()

def render_user_approval_page():
    """Admin page to approve pending user registrations"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👥 User Approval Management</h1>
        <p>Approve or reject pending user registrations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if user has admin privileges
    user_role = st.session_state.get('user_role', '')
    if user_role not in ['admin', 'system_admin', 'company_admin']:
        st.error("You don't have permission to access this page.")
        return
    
    # Get pending users (system-wide for system_admin, company-specific for company_admin)
    if user_role in ['admin', 'system_admin']:
        # System admin sees all pending users across all companies
        pending_users = db.get_all_pending_users()
        st.markdown(f"### System-wide Pending Approvals ({len(pending_users)})")
    else:
        # Company admin sees only their company's pending users
        pending_users = db.get_pending_users(st.session_state.company_id)
        st.markdown(f"### Company Pending Approvals ({len(pending_users)})")
    
    if not pending_users:
        st.info("No pending user registrations.")
        return
    
    for user in pending_users:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                st.markdown(f"**{user.get('full_name', user[3] if len(user) > 3 else 'N/A')}**")
                st.caption(f"@{user.get('username', user[1] if len(user) > 1 else 'N/A')} | {user.get('email', user[2] if len(user) > 2 else 'N/A')}")
            
            with col2:
                st.markdown(f"**Role:** {user.get('role', user[5] if len(user) > 5 else 'N/A')}")
                st.markdown(f"**Registered:** {user.get('created_at', user[6] if len(user) > 6 else 'N/A')}")
            
            with col3:
                if st.button("✅ Approve", key=f"approve_{user['id'] if isinstance(user, dict) else user[0]}", use_container_width=True):
                    user_id = user['id'] if isinstance(user, dict) else user[0]
                    db.approve_user(user_id, st.session_state.user_id)
                    st.success(f"User {user.get('full_name', user[3])} has been approved!")
                    st.rerun()
            
            with col4:
                if st.button("❌ Reject", key=f"reject_{user['id'] if isinstance(user, dict) else user[0]}", use_container_width=True):
                    user_id = user['id'] if isinstance(user, dict) else user[0]
                    db.reject_user(user_id, st.session_state.user_id)
                    st.warning(f"User {user.get('full_name', user[3])} has been rejected.")
                    st.rerun()
            
            st.markdown("---")



def show_pending_approval_badge():
    """Show badge in sidebar for admin if there are pending approvals"""
    user_role = st.session_state.get('user_role', '')
    if user_role in ['admin', 'system_admin', 'company_admin']:
        if user_role in ['admin', 'system_admin']:
            pending_count = len(db.get_all_pending_users())
        else:
            pending_count = len(db.get_pending_users(st.session_state.company_id))
        
        if pending_count > 0:
            st.sidebar.markdown(f"🔔 **Pending Approvals: {pending_count}**")
            if st.sidebar.button("👥 View Pending Approvals", use_container_width=True):
                st.session_state.page = "user_approval"
                st.rerun()

