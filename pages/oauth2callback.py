import streamlit as st
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import the callback handler
from modules.google_auth import handle_google_callback

# Set page config for the callback page (must be first)
st.set_page_config(
    page_title="Google Sign-In",
    page_icon="🔐",
    layout="centered"
)

# Handle the OAuth callback
handle_google_callback()

# Display a message while processing
st.info("Processing Google Sign-In... Please wait.")

# Auto-redirect to main after processing
st.markdown("""
<meta http-equiv="refresh" content="2; url=/" />
""", unsafe_allow_html=True)