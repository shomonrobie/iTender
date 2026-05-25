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

def login_user(user, password):
    """Login user and set session state (user is a sqlite3.Row from authenticate_user)"""
    if user is None:
        return False
    
    # user is a sqlite3.Row; we can access by index
    # Expected indices from the SELECT in authenticate_user:
    # 0: id, 1: username, 2: email, 3: full_name, 4: role, 5: is_active,
    # 6: company_id, 7: password, 8: last_login, 9: is_approved, 10: account_type
    # BUT the query in authenticate_user has been updated; ensure indices match!
    # Based on the second authenticate_user (the one you kept), the SELECT is:
    # SELECT u.id, u.username, u.email, u.full_name, u.role, u.is_active,
    #        u.company_id, u.password, u.last_login, u.is_approved, u.account_type
    # So indices: 0=id,1=username,2=email,3=full_name,4=role,5=is_active,6=company_id,
    #            7=password,8=last_login,9=is_approved,10=account_type

    try:
        st.session_state.logged_in = True
        st.session_state.user_id = user[0]
        st.session_state.username = user[1]
        st.session_state.user_email = user[2]
        st.session_state.full_name = user[3]
        st.session_state.user_role = user[4]
        st.session_state.company_id = user[6]   # company_id is at index 6
        st.session_state.account_type = user[10] if len(user) > 10 else "company"  # account_type
        
        # Fetch company name if company_id exists
        if st.session_state.company_id:
            company = db.get_company_by_id(st.session_state.company_id)
            st.session_state.company_name = company.get("company_name", "N/A") if company else "N/A"
        else:
            st.session_state.company_name = "Individual"
        
        # Set subscription plan (you may want to fetch from subscription table)
        # For now, default to professional for admin, else free
        if st.session_state.user_role == 'admin':
            st.session_state.subscription_plan = 'professional'
        else:
            st.session_state.subscription_plan = 'free'
        st.session_state.subscription_status = 'active'
        
        return True
    except Exception as e:
        print(f"Login error: {e}")
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