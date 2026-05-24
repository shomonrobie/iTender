import streamlit as st
import sys
import os
import json
import base64

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from modules.google_auth import handle_google_callback

# Set page config for the callback page (must be first)
st.set_page_config(
    page_title="Google Sign-In",
    page_icon="🔐",
    layout="centered"
)

# Handle the OAuth callback (this will return user data)
user_data = handle_google_callback()

if user_data:
    # Encode user data to pass via URL
    user_data_json = json.dumps(user_data)
    user_data_b64 = base64.urlsafe_b64encode(user_data_json.encode()).decode()
    
    st.success("Login successful! Redirecting to dashboard...")
    
    # Redirect with user data in URL
    st.markdown(f"""
    <meta http-equiv="refresh" content="1; url=/?user={user_data_b64}" />
    <script>
        setTimeout(function() {{
            window.location.href = '/?user={user_data_b64}';
        }}, 1000);
    </script>
    """, unsafe_allow_html=True)
else:
    st.error("Login failed. Please try again.")
    st.markdown("""
    <meta http-equiv="refresh" content="3; url=/" />
    <a href="/">Click here to return to home</a>
    """, unsafe_allow_html=True)