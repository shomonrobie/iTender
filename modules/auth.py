"""
Authentication Module for TenderAI
Handles user authentication, login, logout, and permission checks
"""

import streamlit as st
from database.db_manager import DatabaseManager
import time
import hashlib
import json
import traceback

db = DatabaseManager()


def save_session_to_url(remember_me=False):
    """Save session to URL parameters for persistence"""
    if not remember_me:
        return
    
    if st.session_state.get('logged_in', False):
        # Save to URL parameters (these persist across refreshes)
        st.query_params['user_id'] = str(st.session_state.user_id)
        st.query_params['username'] = st.session_state.username
        st.query_params['expiry'] = str(int(time.time()) + 30 * 24 * 3600)
        print(f"✅ Session saved to URL for user: {st.session_state.username}")

def restore_session_from_url():
    """Restore session from URL parameters"""
    print("=" * 50)
    print("RESTORE_SESSION_FROM_URL CALLED")
    
    # Already logged in
    if st.session_state.get('logged_in', False):
        print("User already logged in, skipping restore")
        return True
    
    # Check URL parameters
    params = st.query_params
    print(f"URL params: {dict(params)}")
    
    if 'user_id' in params and 'username' in params and 'expiry' in params:
        try:
            # Check expiry
            current_time = int(time.time())
            expiry_time = int(params['expiry'])
            
            if expiry_time <= current_time:
                print("Session expired")
                st.query_params.clear()
                return False
            
            user_id = int(params['user_id'])
            username = params['username']
            print(f"Looking up user: id={user_id}")
            
            # Get user from database
            user = db.get_user_by_id(user_id)
            
            if not user:
                print("User not found")
                st.query_params.clear()
                return False
            
            # Based on your users table schema:
            # Index 0: id
            # Index 1: company_id  
            # Index 2: username  ← THIS IS THE USERNAME
            # Index 3: password
            # Index 4: email
            # Index 5: full_name
            # Index 6: phone
            # Index 7: role
            # Index 8: is_active
            # Index 9: created_at
            # Index 10: last_login
            # Index 11: created_by
            # Index 12: company_name (from JOIN)
            # Index 13: company_id (duplicate from JOIN)
            
            # Verify username matches
            if user[2] != username:  # username is at index 2
                print(f"Username mismatch: DB='{user[2]}', URL='{username}'")
                st.query_params.clear()
                return False
            
            print(f"✅ User verified: {user[2]}")
            
            # Restore session
            st.session_state.logged_in = True
            st.session_state.user_id = user[0]      # id
            st.session_state.username = user[2]     # username
            st.session_state.user_email = user[4]   # email
            st.session_state.full_name = user[5]    # full_name
            st.session_state.user_role = user[7]    # role
            st.session_state.company_id = user[1]   # company_id (from users table)
            st.session_state.account_type = 'company'  # default
            st.session_state.remember_me = True
            
            print(f"✅ Restored - username: {st.session_state.username}")
            print(f"✅ Restored - role: {st.session_state.user_role}")
            print(f"✅ Restored - email: {st.session_state.user_email}")
            
            # Get company name (from JOIN result at index 12)
            if len(user) > 12 and user[12]:
                st.session_state.company_name = user[12]
                print(f"✅ Company name: {st.session_state.company_name}")
            elif st.session_state.company_id:
                company = db.get_company_by_id(st.session_state.company_id)
                st.session_state.company_name = company.get("company_name", "N/A") if company else "N/A"
            else:
                st.session_state.company_name = "Individual"
            
            # Set subscription plan
            if st.session_state.user_role == 'admin':
                st.session_state.subscription_plan = 'professional'
            else:
                st.session_state.subscription_plan = 'free'
            st.session_state.subscription_status = 'active'
            
            print(f"✅✅✅ Session restored for user: {st.session_state.username}")
            
            # Clear URL params after restore
            st.query_params.clear()
            print("URL params cleared")
            
            return True
            
        except Exception as e:
            print(f"Restore error: {e}")
            import traceback
            traceback.print_exc()
            st.query_params.clear()
    
    return False



def clear_session_url():
    """Clear session from URL"""
    st.query_params.clear()

# Keep your existing login_user function but add URL save
def login_user(user, password, remember_me=False):
    """Login user and set session state"""
    if user is None:
        return False
    
    try:
        st.session_state.logged_in = True
        st.session_state.user_id = user[0]
        st.session_state.username = user[1]
        st.session_state.user_email = user[2]
        st.session_state.full_name = user[3]
        st.session_state.user_role = user[4]
        st.session_state.company_id = user[6]
        st.session_state.account_type = user[10] if len(user) > 10 else "company"
        
        # Fetch company name
        if st.session_state.company_id:
            company = db.get_company_by_id(st.session_state.company_id)
            st.session_state.company_name = company.get("company_name", "N/A") if company else "N/A"
        else:
            st.session_state.company_name = "Individual"
        
        # Set subscription plan
        if st.session_state.user_role == 'admin':
            st.session_state.subscription_plan = 'professional'
        else:
            st.session_state.subscription_plan = 'free'
        st.session_state.subscription_status = 'active'
        
        # Save to URL if remember_me is checked
        if remember_me:
            save_session_to_url(remember_me)
        
        return True
    except Exception as e:
        print(f"Login error: {e}")
        return False

def logout_user():
    """Logout current user and clear URL params"""
    clear_session_url()
    
    for key in list(st.session_state.keys()):
        if key not in ['page', 'show_checkout']:
            del st.session_state[key]
    st.session_state.logged_in = False
    st.session_state.page = 'home'
    return True



def authenticate_user(username, password):
    """Authenticate user - returns user data and status"""
    return db.authenticate_user(username, password)


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

def get_refresh_warning():
    """Display warning about browser refresh behavior"""
    if st.session_state.get('logged_in', False):
        st.sidebar.info(
            "🔄 **Tip:** Browser refresh won't log you out if 'Remember Me' was checked.\n\n"
            "Use the Logout button below to end your session."
        )