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
    
    # Check if user is admin
    if st.session_state.user_role not in ['admin', 'company_admin']:
        st.error("You don't have permission to access this page.")
        return
    
    # Get pending users
    pending_users = db.get_pending_users(st.session_state.company_id)
    
    if not pending_users:
        st.info("No pending user registrations.")
        return
    
    st.markdown(f"### Pending Approvals ({len(pending_users)})")
    
    for user in pending_users:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                st.markdown(f"**{user[3]}**")
                st.caption(f"@{user[1]} | {user[2]}")
            
            with col2:
                st.markdown(f"**Role:** {user[5]}")
                st.markdown(f"**Registered:** {user[6]}")
            
            with col3:
                if st.button("✅ Approve", key=f"approve_{user[0]}", use_container_width=True):
                    db.approve_user(user[0], st.session_state.user_id)
                    st.success(f"User {user[3]} has been approved!")
                    st.rerun()
            
            with col4:
                if st.button("❌ Reject", key=f"reject_{user[0]}", use_container_width=True):
                    db.reject_user(user[0], st.session_state.user_id)
                    st.warning(f"User {user[3]} has been rejected.")
                    st.rerun()
            
            st.markdown("---")


def show_pending_approval_badge():
    """Show badge in sidebar for admin if there are pending approvals"""
    if st.session_state.user_role in ['admin', 'company_admin']:
        pending_count = len(db.get_pending_users(st.session_state.company_id))
        if pending_count > 0:
            st.sidebar.markdown(f"🔔 **Pending Approvals: {pending_count}**")
            if st.sidebar.button("👥 View Pending Approvals", use_container_width=True):
                st.session_state.page = "user_approval"
                st.rerun()
