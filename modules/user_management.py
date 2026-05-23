import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager

db = DatabaseManager()

def render_user_management():
    """Render user management interface for admin/company_admin"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👥 User Management</h1>
        <p>Manage team members, roles, and permissions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get current company users
    company_id = st.session_state.get('company_id')
    users = db.get_all_users(company_id=company_id)
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", len(users))
    with col2:
        active_users = len([u for u in users if u[6] == 1])
        st.metric("Active Users", active_users)
    with col3:
        admins = len([u for u in users if u[5] in ['admin', 'company_admin']])
        st.metric("Admins", admins)
    with col4:
        analysts = len([u for u in users if u[5] == 'analyst'])
        st.metric("Analysts", analysts)
    
    # Add new user form
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name*")
                email = st.text_input("Email*")
                username = st.text_input("Username*")
                role = st.selectbox("Role*", ["company_admin", "manager", "analyst", "viewer"])
            with col2:
                phone = st.text_input("Phone")
                password = st.text_input("Temporary Password*", type="password")
                confirm_password = st.text_input("Confirm Password*", type="password")
            
            if st.form_submit_button("Add User"):
                if password != confirm_password:
                    st.error("Passwords do not match")
                elif all([full_name, email, username, password]):
                    user_data = {
                        'username': username,
                        'password': password,
                        'email': email,
                        'full_name': full_name,
                        'phone': phone,
                        'role': role
                    }
                    success, result = db.create_user(company_id, user_data, st.session_state.user_id)
                    if success:
                        st.success(f"User {full_name} added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error: {result}")
                else:
                    st.error("Please fill all required fields")
    
    # User list
    st.markdown("### 📋 Team Members")
    
    if users:
        for user in users:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 1.5])
                
                with col1:
                    st.markdown(f"**{user[3]}**")
                    st.caption(f"{user[2]} | {user[1]}")
                
                with col2:
                    st.markdown(f"**Role:** {user[5].replace('_', ' ').title()}")
                    st.caption(f"ID: {user[0]}")
                
                with col3:
                    status = "🟢 Active" if user[6] == 1 else "🔴 Inactive"
                    st.markdown(f"**Status:** {status}")
                    if user[8]:
                        st.caption(f"Last login: {user[8].split()[0]}")
                
                with col4:
                    # Role change dropdown
                    if st.session_state.user_role in ['admin', 'company_admin'] and user[5] != 'admin':
                        new_role = st.selectbox(
                            "Change Role",
                            options=["company_admin", "manager", "analyst", "viewer"],
                            index=["company_admin", "manager", "analyst", "viewer"].index(user[5]) if user[5] in ["company_admin", "manager", "analyst", "viewer"] else 2,
                            key=f"role_{user[0]}",
                            label_visibility="collapsed"
                        )
                        if new_role != user[5]:
                            if db.update_user_role(user[0], new_role, st.session_state.user_id):
                                st.success(f"Role updated to {new_role}")
                                st.rerun()
                
                with col5:
                    # Action buttons
                    if user[0] != st.session_state.user_id:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if user[6] == 1:
                                if st.button("🔴", key=f"deactivate_{user[0]}", help="Deactivate"):
                                    db.update_user_status(user[0], 0)
                                    st.rerun()
                            else:
                                if st.button("🟢", key=f"activate_{user[0]}", help="Activate"):
                                    db.update_user_status(user[0], 1)
                                    st.rerun()
                        with col_b:
                            if user[5] != 'admin':
                                if st.button("🗑️", key=f"delete_{user[0]}", help="Delete"):
                                    db.delete_user(user[0])
                                    st.rerun()
                
                st.markdown("---")
    else:
        st.info("No users found")

def render_role_permissions():
    """Display role permissions matrix"""
    st.markdown("### 📋 Role Permissions Matrix")
    
    permissions_data = {
        'Role': ['Admin', 'Company Admin', 'Manager', 'Analyst', 'Viewer'],
        'Manage Users': ['✅', '✅', '❌', '❌', '❌'],
        'Change Plans': ['✅', '✅', '❌', '❌', '❌'],
        'View All Analyses': ['✅', '✅', '✅', '❌', '❌'],
        'Create Analyses': ['✅', '✅', '✅', '✅', '❌'],
        'View Reports': ['✅', '✅', '✅', '✅', '✅'],
        'Export Data': ['✅', '✅', '✅', '❌', '❌'],
        'Manage Team': ['✅', '✅', '❌', '❌', '❌']
    }
    
    st.dataframe(pd.DataFrame(permissions_data), use_container_width=True, hide_index=True)