# _pages/login_page.py - Simplified with Google button below form

import streamlit as st
from modules.auth import authenticate_user, login_user, restore_session_from_url
from utils.helpers import navigate_to
from modules.google_auth import render_google_login_button, handle_google_callback

from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()


def show():
    """Login page with Google Sign-In"""
    
    print("=" * 60)
    print("📄 LOGIN PAGE LOADED")
    print("=" * 60)
    print(f"🔍 logged_in: {st.session_state.get('logged_in', False)}")
    print(f"🔍 page: {st.session_state.get('page', 'None')}")
    print(f"🔍 user_role: {st.session_state.get('user_role', 'None')}")
    
    # ✅ If already logged in, redirect immediately
    if st.session_state.get('logged_in', False):
        user_role = st.session_state.get('user_role', 'viewer')
        print(f"✅ Already logged in as: {user_role}")
        
        if user_role in ['admin', 'system_admin']:
            print("🔀 Redirecting to: admin_dashboard")
            navigate_to("admin_dashboard")
        elif user_role == 'company_admin':
            print("🔀 Redirecting to: company_dashboard")
            navigate_to("company_dashboard")
        else:
            print("🔀 Redirecting to: dashboard")
            navigate_to("dashboard")
        return
    
    # Try to restore session from URL
    print("🔄 Attempting to restore session from URL...")
    if restore_session_from_url():
        user_role = st.session_state.get('user_role', 'viewer')
        print(f"✅ Session restored! Role: {user_role}")
        
        if user_role in ['admin', 'system_admin']:
            print("🔀 Redirecting to: admin_dashboard")
            navigate_to("admin_dashboard")
        elif user_role == 'company_admin':
            print("🔀 Redirecting to: company_dashboard")
            navigate_to("company_dashboard")
        else:
            print("🔀 Redirecting to: dashboard")
            navigate_to("dashboard")
        return
    else:
        print("❌ Session restore failed")
    
    # Handle Google OAuth callback
    print("🔄 Handling Google OAuth callback...")
    handle_google_callback()
    
    
    # Check if showing Google registration
    if st.session_state.get('show_google_registration'):
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return
    
    st.title("🔐 Login to TenderAI")
    
    # Login form
    with st.form("login_form"):
        username = st.text_input("Username or Email", placeholder="Enter your username or email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        remember_me = st.checkbox("Remember me (stay logged in for 30 days)")
        
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                user = authenticate_user(username, password)
                
                if user:
                    if login_user(user, password, remember_me):
                        st.success(f"Welcome back, {user.get('full_name', user.get('username'))}! 🎉")
                        # ✅ Redirect after successful login
                        user_role = user.get('role', 'viewer')
                        if user_role in ['admin', 'system_admin']:
                            navigate_to("admin_dashboard")
                        elif user_role == 'company_admin':
                            navigate_to("company_dashboard")
                        else:
                            navigate_to("dashboard")
                        return
                    else:
                        st.error("Login failed")
                else:
                    st.error("Invalid username/email or password")
    
    # Divider
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #888;'>OR</p>", unsafe_allow_html=True)
    
    # Google Sign-In section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center;">
            <p style="color: #666; font-size: 0.9rem;">Sign in with your Google account</p>
        </div>
        """, unsafe_allow_html=True)
        
        render_google_login_button()
        
        st.markdown("""
        <div style="text-align: center; margin-top: 0.5rem;">
            <p style="color: #999; font-size: 0.7rem;">
                By continuing, you agree to our Terms of Service and Privacy Policy
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Register and Forgot Password
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 Register", use_container_width=True):
            navigate_to("register")
            st.rerun()
    with col2:
        if st.button("🔒 Forgot Password?", use_container_width=True):
            navigate_to("forgot_password")
            st.rerun()
    with col3:
        pass
    
    # Demo credentials
    with st.expander("ℹ️ Demo Credentials"):
        st.code("""
        Admin Account:
        Username: admin
        Password: admin123
        
        Demo User:
        Username: demo
        Password: demo123
        """)