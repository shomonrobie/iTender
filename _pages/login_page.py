# _pages/login_page.py

import streamlit as st
from modules.auth import authenticate_user, login_user, restore_session_from_url
from utils.helpers import navigate_to


def show():
    """Simple login page"""
    
    # Try to restore session
    if not st.session_state.get('logged_in', False):
        if restore_session_from_url():
            navigate_to("dashboard")
            st.rerun()
            return
    
    st.title("🔐 Login to TenderAI")
    
    # Simple login form
    with st.form("login_form"):
        username = st.text_input("Username or Email", placeholder="Enter your username or email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        remember_me = st.checkbox("Remember me (stay logged in for 30 days)")
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
        with col2:
            if st.form_submit_button("Register", use_container_width=True):
                navigate_to("register")
                st.rerun()
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                user = authenticate_user(username, password)
                
                if user:
                    if login_user(user, password, remember_me):
                        st.success(f"Welcome back, {user.get('full_name', user.get('username'))}! 🎉")
                        st.rerun()
                    else:
                        st.error("Login failed")
                else:
                    st.error("Invalid username/email or password")
    
    # Forgot password link
    st.markdown("---")
    st.markdown("### Forgot Password?")
    st.caption("Contact your system administrator to reset your password.")
    
    # Demo credentials (for testing)
    with st.expander("ℹ️ Demo Credentials"):
        st.code("""
        Admin Account:
        Username: admin
        Password: admin123
        
        Demo User:
        Username: demo
        Password: demo123
        """)