

import streamlit as st
from modules.auth import login_user

from config import DEBUG_MODE, debug_print
from utils.helpers import (
    render_page_header,
    render_feature_card,
    render_pricing_card,
    render_demo_credentials,
    navigate_to,
    get_compact_css,
    format_currency_bd,
    format_percentage,
    get_bid_status_badge,
    get_risk_indicator,
    validate_password_strength,
    safe_title
)
from modules.auth import login_user, logout_user, is_admin, is_company_admin, authenticate_user, has_permission, get_current_user

def show():
    """Updated Login Page with URL-Based Remember Me & Better Integration"""
    debug_print("🔐 Rendering login page")
    
    # Initialize session state variables
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    if 'forgot_password_email' not in st.session_state:
        st.session_state.forgot_password_email = ''
    if 'remember_me' not in st.session_state:
        st.session_state.remember_me = False

    # Import required modules
    from modules.google_auth import render_google_login_button, handle_google_callback
    from modules.individual_registration import authenticate_individual_user
    from modules.auth import login_user, restore_session_from_url
    
    # ✅ Try to restore session from URL (no cookie complexity)
    if not st.session_state.get('logged_in', False):
        try:
            if restore_session_from_url():
                debug_print("Session restored from URL, redirecting to dashboard")
                navigate_to("dashboard")
                st.rerun()
                return
        except Exception as e:
            debug_print(f"Session restore error: {e}")
    
    # Handle Google OAuth callback
    handle_google_callback()
    
    # Check if showing Google registration
    if st.session_state.get('show_google_registration'):
        from modules.google_auth import render_google_registration_form
        render_google_registration_form(db)
        return
    
    render_page_header("🔐 Login", "Access your TenderAI account")
    
    # Display session persistence tip
    if not st.session_state.get('logged_in', False):
        st.info("💡 **Tip:** Check 'Remember me' to stay logged in across browser sessions for 30 days.")
    
    # Create tabs for different login types
    tab1, tab2 = st.tabs(["🏢 Company Login", "👤 Individual Login"])
    
    with tab1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("company_login_form", clear_on_submit=True):
                username = st.text_input("Username or Email", key="comp_login_username")
                password = st.text_input("Password", type="password", key="comp_login_password")
                remember_me = st.checkbox("Remember me (stay logged in for 30 days)", key="comp_remember_me")
                
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
                
                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password")
                    else:
                        debug_print(f"[LOGIN] Username: {username}, Remember me: {remember_me}")
                        user, status, message = authenticate_user(username, password)
                        debug_print(f"[LOGIN] Auth result: status={status}, user={user is not None}")
                        
                        if status == "pending_approval":
                            st.warning("⚠️ Your account is pending approval by an administrator.")
                        elif user and status == "approved":
                            debug_print(f"[LOGIN] Calling login_user with remember_me={remember_me}")
                            # ✅ Pass cookies=None since we're using URL params
                            if login_user(user, password, remember_me):
                                full_name = user[3] if len(user) > 3 else username
                                debug_print("[LOGIN] Login successful!")
                                st.success(f"Welcome back, {full_name}! 👋")
                                
                                if remember_me:
                                    st.info("✅ Session saved to URL! You'll stay logged in even after browser refresh.")
                                
                                navigate_to("dashboard")
                                st.rerun()
                            else:
                                st.error("❌ Login failed. Please try again.")
                        else:
                            st.error(message or "❌ Invalid credentials. Please try again.")
            
            st.markdown("---")
            if st.button("➕ Register New Company Account", use_container_width=True):
                navigate_to("register")

    with tab2:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Individual Email Login
            
            with st.form("individual_login_form", clear_on_submit=True):
                email = st.text_input("Email Address", key="ind_login_email")
                password = st.text_input("Password", type="password", key="ind_login_password")
                remember_me_ind = st.checkbox("Remember me (stay logged in for 30 days)", key="ind_remember_me")
                
                submitted_ind = st.form_submit_button("Login", use_container_width=True, type="primary")
                
                if submitted_ind:
                    if not email or not password:
                        st.error("Please enter both email and password")
                    else:
                        user = authenticate_individual_user(email, password)
                        if user:
                            from modules.email_verification import send_verification_email
                            if send_verification_email(email, user.get('full_name', 'User'), 'login'):
                                # Store remember_me preference for 2FA completion
                                st.session_state.pending_2fa = {
                                    'user': user, 
                                    'email': email,
                                    'remember_me': remember_me_ind
                                }
                                st.session_state.show_2fa = True
                                st.success("Verification code sent to your email!")
                                st.rerun()
                            else:
                                st.error("Failed to send verification code")
                        else:
                            st.error("❌ Invalid email or password.")

            st.markdown("---")
            st.markdown("<p style='text-align: center; color: #666;'>OR</p>", unsafe_allow_html=True)
            
            # Google Sign-In
            
            st.caption("For consultants, freelancers, and individual users")
            render_google_login_button()
            
            st.markdown("---")
            
            # Registration & Forgot Password Links
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📝 Register as Individual", use_container_width=True):
                    navigate_to(PageRoutes.INDIVIDUAL_REGISTER)
            with col_b:
                if st.button("🔒 Forgot Password?", use_container_width=True, type="secondary"):
                    st.session_state.show_forgot_password = True
                    st.rerun()

    # ====================== 2FA Verification ======================
    if st.session_state.get('show_2fa'):
        st.markdown("---")
        st.markdown("### 🔐 Two-Factor Authentication")
        st.info(f"A verification code has been sent to **{st.session_state.pending_2fa['email']}**")
        
        with st.form("2fa_verification_form"):
            otp = st.text_input("Enter 6-digit verification code", max_chars=6, type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Verify", type="primary", use_container_width=True):
                    from modules.email_verification import verify_otp
                    success, message = verify_otp(st.session_state.pending_2fa['email'], otp)
                    
                    if success:
                        user = st.session_state.pending_2fa['user']
                        remember_me = st.session_state.pending_2fa.get('remember_me', False)
                        
                        # Convert user dict to the expected format for login_user
                        user_tuple = (
                            user.get('id'),
                            user.get('username'),
                            user.get('email'),
                            user.get('full_name'),
                            'individual',
                            1,
                            user.get('company_id'),
                            '',
                            None,
                            1,
                            'individual'
                        )
                        
                        # ✅ Login with remember me option (no cookies parameter)
                        if login_user(user_tuple, None, remember_me):
                            st.session_state.show_2fa = False
                            st.session_state.pending_2fa = None
                            
                            if remember_me:
                                st.info("✅ Session saved to URL! You'll stay logged in even after browser refresh.")
                            
                            navigate_to("dashboard", success_msg=f"Welcome back, {user.get('full_name', 'User')}! 👋")
                            st.rerun()
                        else:
                            st.error("Login failed. Please try again.")
                    else:
                        st.error(message)
            
            with col2:
                if st.form_submit_button("Resend Code", use_container_width=True):
                    from modules.email_verification import send_verification_email
                    if send_verification_email(
                        st.session_state.pending_2fa['email'], 
                        st.session_state.pending_2fa['user'].get('full_name', 'User'), 
                        'login'
                    ):
                        st.success("New verification code sent!")
                    else:
                        st.error("Failed to resend code")
    
    # ====================== Forgot Password Modal ======================
    if st.session_state.get('show_forgot_password'):
        st.markdown("---")
        st.markdown("### 🔒 Reset Your Password")
        
        with st.form("forgot_password_form", clear_on_submit=True):
            email_input = st.text_input(
                "Enter your registered email", 
                value=st.session_state.get('forgot_password_email', '')
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                send_clicked = st.form_submit_button("Send Reset Link", 
                                                   use_container_width=True, 
                                                   type="primary")
            
            with col2:
                cancel_clicked = st.form_submit_button("Cancel", 
                                                     use_container_width=True, 
                                                     type="secondary")
            
            if send_clicked:
                if not email_input or "@" not in email_input:
                    st.error("Please enter a valid email address")
                else:
                    user = db.get_user_by_email(email_input)
                    if user:
                        import secrets
                        reset_token = secrets.token_urlsafe(32)
                        
                        if db.store_password_reset_token(email_input, reset_token):
                            reset_link = f"https://itender-bd.streamlit.app/reset-password?token={reset_token}"
                            from modules.email_verification import send_password_reset_email
                            
                            if send_password_reset_email(email_input, reset_link):
                                st.success(f"✅ Password reset link sent to **{email_input}**")
                                st.session_state.show_forgot_password = False
                                st.rerun()
                            else:
                                st.error("Failed to send reset email. Please try again.")
                        else:
                            st.error("System error. Please try again later.")
                    else:
                        st.error("No account found with this email.")
            
            if cancel_clicked:
                st.session_state.show_forgot_password = False
                st.rerun()