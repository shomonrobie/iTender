"""
Authentication Module for TenderAI
Handles user authentication, login, logout, and permission checks
"""

import streamlit as st
from database.db_manager import DatabaseManager

db = DatabaseManager()

def authenticate_user(username, password):
    """Authenticate user - returns user data and status"""
    return db.authenticate_user(username, password)

def login_user(username, password):
    """Login user and set session state"""
    result = db.authenticate_user(username, password)
    
    # Check if result is a tuple with user data or a special status
    if result is None:
        return False
    
    # Handle different return types
    if isinstance(result, tuple) and result:
        user = result
        # Check if it's a special status
        if len(result) == 2 and result[1] == "pending_approval":
            st.warning("Your account is pending approval. Please wait for admin approval.")
            return False
        
        # Normal user login
        st.session_state.logged_in = True
        st.session_state.user_id = user[0]
        st.session_state.username = user[1]
        st.session_state.user_email = user[2]
        st.session_state.full_name = user[3]
        st.session_state.user_role = user[4]
        st.session_state.company_id = user[5]
        st.session_state.company_name = user[7]
        st.session_state.subscription_plan = user[8] if len(user) > 8 and user[8] else 'free'
        st.session_state.subscription_status = user[9] if len(user) > 9 and user[9] else 'active'
        return True
    
    return False

def logout_user():
    """Logout current user"""
    for key in list(st.session_state.keys()):
        if key not in ['page', 'show_checkout']:
            del st.session_state[key]
    st.session_state.logged_in = False
    st.session_state.page = 'home'
    return True

def is_admin():
    """Check if current user is admin"""
    return st.session_state.get('user_role') == 'admin'

def is_company_admin():
    """Check if current user is company admin"""
    return st.session_state.get('user_role') in ['admin', 'company_admin']

def has_permission(required_role):
    """Check if user has required role permission"""
    role_hierarchy = {
        'admin': 5,
        'company_admin': 4,
        'manager': 3,
        'analyst': 2,
        'viewer': 1
    }
    current_role = st.session_state.get('user_role', 'viewer')
    return role_hierarchy.get(current_role, 0) >= role_hierarchy.get(required_role, 0)

def get_current_user():
    """Get current user details"""
    if st.session_state.get('logged_in'):
        return {
            'id': st.session_state.get('user_id'),
            'username': st.session_state.get('username'),
            'email': st.session_state.get('user_email'),
            'full_name': st.session_state.get('full_name'),
            'role': st.session_state.get('user_role'),
            'company_id': st.session_state.get('company_id'),
            'company_name': st.session_state.get('company_name')
        }
    return None

def is_user_approved(user_id=None):
    """Check if user is approved"""
    if user_id is None:
        user_id = st.session_state.get('user_id')
    if user_id:
        return db.is_user_approved(user_id)
    return False