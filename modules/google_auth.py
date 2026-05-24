"""
Google OAuth Authentication Module
Individual User Sign-Up Only (Not for Companies)
"""

import streamlit as st
import requests
import secrets
from datetime import datetime

GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "YOUR_GOOGLE_CLIENT_SECRET"
GOOGLE_REDIRECT_URI = "http://localhost:8501"

import os
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", GOOGLE_CLIENT_SECRET)

def get_google_auth_url():
    import urllib.parse
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

# Get redirect URI based on environment
def get_redirect_uri():
    """Get the correct redirect URI for the current environment"""
    if os.getenv('STREAMLIT_SERVER_PORT') == '8501' and 'localhost' in os.getenv('STREAMLIT_BROWSER_SERVER_ADDRESS', ''):
        return "http://localhost:8501/oauth2callback"
    else:
        return "https://itender-bd.streamlit.app/oauth2callback"

GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID"))
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", os.getenv("GOOGLE_CLIENT_SECRET"))
GOOGLE_REDIRECT_URI = get_redirect_uri()


def exchange_code_for_token(code):
    import urllib.parse
    data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'code': code,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    response = requests.post('https://oauth2.googleapis.com/token', data=data)
    if response.status_code == 200:
        return response.json()
    return None

def get_user_info(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def generate_username(email):
    username = email.split('@')[0]
    username = ''.join(c for c in username if c.isalnum() or c == '_')
    return username + secrets.token_hex(2)[:4]

def handle_google_callback(db=None):
    """Handle Google OAuth callback from URL parameters"""
    
    # Get code from URL parameters
    params = st.query_params
    
    if 'code' not in params:
        return  # Not a callback
    
    code = params['code']
    
    with st.spinner("Authenticating with Google..."):
        token_data = exchange_code_for_token(code)
        
        if token_data and 'access_token' in token_data:
            user_info = get_user_info(token_data['access_token'])
            
            if user_info:
                email = user_info.get('email')
                name = user_info.get('name', email.split('@')[0])
                
                from database.db_manager import DatabaseManager
                db = DatabaseManager()
                
                existing_user = db.get_user_by_email(email)
                
                if existing_user:
                    # Set session state
                    st.session_state.logged_in = True
                    st.session_state.user_id = existing_user['id']
                    st.session_state.username = existing_user['username']
                    st.session_state.user_email = email
                    st.session_state.full_name = existing_user['full_name'] or name
                    st.session_state.user_role = existing_user['role']
                    st.session_state.account_type = existing_user.get('account_type', 'individual')
                    st.session_state.company_id = existing_user['company_id']
                    
                    st.success(f"Welcome back, {name}!")
                    st.session_state.page = "dashboard"
                    
                else:
                    # Store for registration
                    st.session_state.pending_google_signup = {
                        'email': email,
                        'name': name,
                        'google_id': user_info.get('id')
                    }
                    st.session_state.show_google_registration = True
                    st.session_state.page = "individual_register"
                
                # Clear query params
                st.query_params.clear()
                
def render_google_login_button():
    """Render Google Sign-In button for individual users"""
    
    st.markdown("""
    <style>
    .google-btn {
        background-color: #ffffff;
        color: #757575;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px 16px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        width: 100%;
        transition: background-color 0.2s;
    }
    .google-btn:hover {
        background-color: #f5f5f5;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    auth_url = get_google_auth_url()
    
    st.markdown(f"""
    <a href="{auth_url}" target="_self" style="text-decoration: none;">
        <div class="google-btn">
            <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google (Individual Account)
        </div>
    </a>
    """, unsafe_allow_html=True)
    
    st.caption("🔹 For individual consultants and freelancers only. Companies should use the registration form.")

def render_google_registration_form(db=None):
    """Render registration completion form for Google users"""
    
    if db is None:
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
    
    st.markdown("### Complete Your Registration")
    st.info("Welcome! Please complete your account setup.")
    
    user_info = st.session_state.get('pending_google_signup', {})
    
    if not user_info:
        st.error("Session expired. Please try again.")
        st.session_state.show_google_registration = False
        return
    
    with st.form("google_registration_form"):
        st.text_input("Email", value=user_info.get('email', ''), disabled=True)
        full_name = st.text_input("Full Name", value=user_info.get('name', ''), key="google_full_name")
        username = st.text_input("Username", value=user_info.get('email', '').split('@')[0], key="google_username")
        phone = st.text_input("Phone (Optional)", key="google_phone")
        specialization = st.selectbox(
            "Specialization",
            ["Construction Consultant", "Bid Analyst", "Quantity Surveyor", 
             "Project Manager", "Civil Engineer", "Architect", "Other"],
            key="google_specialization"
        )
        years_experience = st.slider("Years of Experience", 0, 40, 5, key="google_years")
        
        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy *", key="google_terms")
        
        submitted = st.form_submit_button("Complete Registration", type="primary")
        
        if submitted:
            if not all([full_name, username, specialization]):
                st.error("Please fill all required fields")
            elif not terms:
                st.error("Please accept the terms to continue")
            else:
                # Create individual company
                company_data = {
                    'company_name': f"{full_name} - Individual Consultant",
                    'email': user_info['email'],
                    'phone': phone,
                    'division': specialization,
                    'is_individual': True
                }
                
                success, result = db.create_company(company_data)
                
                if success:
                    company_id = result
                    
                    # Generate random password for Google user
                    import secrets
                    temp_password = secrets.token_urlsafe(12)
                    import bcrypt
                    hashed_password = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    # Create user
                    user_data = {
                        'username': username,
                        'password': hashed_password,
                        'email': user_info['email'],
                        'full_name': full_name,
                        'phone': phone,
                        'role': 'individual',
                        'account_type': 'individual',
                        'specialization': specialization,
                        'years_experience': years_experience,
                        'is_approved': True,
                        'auth_provider': 'google',
                        'google_id': user_info.get('google_id')
                    }
                    
                    user_success, user_result = db.create_user(company_id, user_data, 'individual')
                    
                    if user_success:
                        st.balloons()
                        st.success("Registration successful! You can now login with Google.")
                        st.info(f"Your account has been created. Please login using Google.")
                        
                        st.session_state.show_google_registration = False
                        st.session_state.pending_google_signup = None
                        
                        if st.button("Go to Login", use_container_width=True):
                            st.session_state.page = "individual_login"
                            st.rerun()
                    else:
                        st.error(f"Failed to create user: {user_result}")
                else:
                    st.error(f"Failed to create account: {success}")


def handle_google_callback():
    """Handle Google OAuth callback from URL parameters"""
    
    # Get code from URL parameters
    params = st.query_params
    
    if 'code' not in params:
        return  # Not a callback
    
    code = params['code']
    
    with st.spinner("Authenticating with Google..."):
        token_data = exchange_code_for_token(code)
        
        if token_data and 'access_token' in token_data:
            user_info = get_user_info(token_data['access_token'])
            
            if user_info:
                email = user_info.get('email')
                name = user_info.get('name', email.split('@')[0])
                
                from database.db_manager import DatabaseManager
                db = DatabaseManager()
                
                # Check if user exists
                existing_user = db.get_user_by_email(email)
                
                if existing_user:
                    # Login existing user
                    st.session_state.logged_in = True
                    st.session_state.user_id = existing_user['id']
                    st.session_state.username = existing_user['username']
                    st.session_state.user_email = email
                    st.session_state.full_name = existing_user['full_name'] or name
                    st.session_state.user_role = existing_user['role']
                    st.session_state.account_type = existing_user.get('account_type', 'individual')
                    st.session_state.company_id = existing_user['company_id']
                    
                    st.success(f"Welcome back, {name}!")
                    
                    # Clear query params and redirect
                    st.query_params.clear()
                    st.session_state.page = "dashboard"
                    st.rerun()  # This is fine inside a function called from main()
                else:
                    # Store pending signup info
                    st.session_state.pending_google_signup = {
                        'email': email,
                        'name': name,
                        'google_id': user_info.get('id')
                    }
                    st.session_state.show_google_registration = True
                    st.query_params.clear()
                    st.rerun()  # This is fine inside a function called from main()


def render_google_2fa():
    """Render 2FA verification for Google login"""
    
    st.markdown("### Verify Your Identity")
    st.info(f"A verification code has been sent to your email")
    
    with st.form("google_2fa_form"):
        otp = st.text_input("Enter 6-digit code", max_chars=6, type="password")
        
        if st.form_submit_button("Verify", type="primary"):
            from modules.email_verification import verify_otp
            
            user = st.session_state.google_2fa_user
            success, message = verify_otp(user['email'], otp)
            
            if success:
                # Set session state
                st.session_state.logged_in = True
                st.session_state.user_id = user['id']
                st.session_state.user_email = user['email']
                st.session_state.full_name = user['full_name']
                st.session_state.user_role = 'individual'
                st.session_state.account_type = 'individual'
                
                st.session_state.show_google_2fa = False
                st.session_state.google_2fa_user = None
                
                st.success("Login successful!")
                st.rerun()
            else:
                st.error(message)
