"""
Simple Google OAuth - No email verification required
"""

import streamlit as st
import requests
import secrets
from datetime import datetime

# For demo purposes - in production, use proper OAuth
def render_simple_google_button():
    """Render a simple Google-style login button (demo mode)"""
    
    st.markdown("""
    <style>
    .google-demo-btn {
        background-color: #ffffff;
        color: #757575;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 10px 16px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        transition: all 0.2s;
        width: 100%;
    }
    .google-demo-btn:hover {
        background-color: #f5f5f5;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    if st.button("🟢 Sign in with Google (Demo)", use_container_width=True):
        # For demo: create a test account
        st.session_state.google_demo_email = "demo@gmail.com"
        st.session_state.google_demo_name = "Demo User"
        st.session_state.show_google_demo_registration = True
        st.rerun()

def render_google_demo_registration(db):
    """Handle Google demo registration"""
    
    st.info("🔐 Demo Google Sign-In - No email verification required")
    
    email = st.text_input("Email", value=st.session_state.get('google_demo_email', ''))
    name = st.text_input("Full Name", value=st.session_state.get('google_demo_name', ''))
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Continue with Demo Account", type="primary"):
            # Check if user exists
            existing = db.get_user_by_email(email)
            
            if existing:
                st.session_state.authenticated = True
                st.session_state.user_id = existing['id']
                st.session_state.user_name = existing['full_name']
                st.session_state.user_email = email
                st.session_state.user_role = existing['role']
                st.session_state.company_id = existing['company_id']
                st.session_state.auth_method = 'google_demo'
                st.success(f"Welcome back, {name}!")
                st.rerun()
            else:
                # Create new company and user
                company_id = db.create_company({"company_name": f"{name}'s Company", "email": email})
                if company_id:
                    user_data = {
                        'username': email.split('@')[0],
                        'email': email,
                        'full_name': name,
                        'password': secrets.token_urlsafe(16),
                        'role': 'user',
                        'is_approved': True  # Auto-approve for demo
                    }
                    success, result = db.create_user(company_id, user_data, 'user')
                    if success:
                        st.success("Demo account created! You are now logged in.")
                        st.rerun()
    
    with col2:
        if st.button("Cancel"):
            st.session_state.show_google_demo_registration = False
            st.rerun()