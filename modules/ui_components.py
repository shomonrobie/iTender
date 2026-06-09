# modules/ui_components.py

import streamlit as st
from datetime import datetime
import hashlib
def init_theme():
    """Initialize theme settings in session state"""
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False

def toggle_dark_mode():
    """Toggle dark mode setting"""
    st.session_state.dark_mode = not st.session_state.dark_mode
    st.rerun()

def get_theme_css():
    """Return CSS based on dark/light mode"""
    if st.session_state.get('dark_mode', False):
        return """
        <style>
        /* Dark Theme */
        :root {
            --bg-primary: #0f0f12;
            --bg-secondary: #1a1a24;
            --bg-card: #1e1e2a;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --border-color: #2a2a35;
            --accent-primary: #667eea;
            --accent-secondary: #764ba2;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        
        /* Main app background */
        .stApp {
            background: linear-gradient(135deg, #0f0f12 0%, #1a1a24 100%);
        }
        
        /* Card styling */
        .metric-card, .feature-card, .pricing-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem;
            transition: transform 0.2s;
        }
        
        .metric-card:hover, .feature-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        
        /* Text colors */
        .stMarkdown, .stText, p, div, span {
            color: var(--text-primary);
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-primary);
        }
        
        /* Dataframes */
        .stDataFrame, .dataframe {
            background: var(--bg-card);
            color: var(--text-primary);
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f0f12 0%, #1a1a24 100%);
            border-right: 1px solid var(--border-color);
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            transition: all 0.2s;
        }
        
        .stButton > button:hover {
            transform: translateY(-1px);
            opacity: 0.9;
        }
        
        /* Input fields */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > select {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-radius: 8px;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 1rem;
            background: transparent;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: var(--bg-secondary);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            color: var(--text-secondary);
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            background: var(--bg-secondary);
            border-radius: 8px;
            color: var(--text-primary);
        }
        
        /* Info/Warning/Success boxes */
        .stAlert {
            background: var(--bg-secondary);
            border-left: 4px solid var(--accent-primary);
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--accent-primary);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-secondary);
        }
        </style>
        """
    else:
        return """
        <style>
        /* Light Theme */
        :root {
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
            --accent-primary: #667eea;
            --accent-secondary: #764ba2;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        
        .stApp {
            background: var(--bg-primary);
        }
        
        .metric-card, .feature-card, .pricing-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem;
            transition: transform 0.2s;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        .metric-card:hover, .feature-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .stDataFrame, .dataframe {
            background: var(--bg-card);
        }
        
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
            border-right: 1px solid var(--border-color);
        }
        
        .stButton > button {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            border: none;
            border-radius: 8px;
        }
        
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > select {
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: #f1f5f9;
            border-radius: 8px;
        }
        
        .streamlit-expanderHeader {
            background: #f8fafc;
            border-radius: 8px;
        }
        </style>
        """

def render_app_header(show_dark_mode_toggle=True):
    """Render professional app header with logo and dark mode toggle"""
    
    init_theme()
    
    # Get user info
    full_name = st.session_state.get('full_name') or 'User'
    company_name = st.session_state.get('company_name') or ''
    display_name = full_name[:20] if len(full_name) > 20 else full_name
    display_company = f"| {company_name[:20]}" if company_name and len(company_name) > 0 else ''
    
    # Determine button text
    button_text = "☀️ Light" if st.session_state.dark_mode else "🌙 Dark"
    
    # Create header with inline button using Streamlit columns
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 0.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 2rem;">🏗️</div>
                <div>
                    <div style="margin: 0; font-size: 1.5rem; font-weight: bold; color: white;">TenderAI</div>
                    <div style="margin: 0; font-size: 0.7rem; color: rgba(255,255,255,0.8);">Enterprise Tender Management & Bid Optimization Platform</div>
                </div>
            </div>
            <div style="background: rgba(255,255,255,0.2); border-radius: 30px; padding: 6px 15px;">
                <span style="color: white; font-size: 0.85rem;">👋 {display_name} {display_company}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Dark mode toggle button below the header
    if show_dark_mode_toggle:
        col1, col2, col3 = st.columns([4, 1, 4])
        with col2:
            if st.button(button_text, key="theme_toggle_header", use_container_width=True):
                toggle_dark_mode()
    
    st.markdown("---")

                    
def render_dark_mode_toggle():
    """Render dark mode toggle button with session-unique key"""
    
    init_theme()
    
    # Create a unique key based on session ID to avoid duplicates
    session_id = st.session_state.get('session_id', 'default')
    unique_suffix = hashlib.md5(f"{session_id}_dark_toggle".encode()).hexdigest()[:8]
    
    # Create columns for the toggle
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        if st.session_state.dark_mode:
            if st.button("☀️ Light Mode", use_container_width=True, key=f"light_mode_{unique_suffix}"):
                toggle_dark_mode()
        else:
            if st.button("🌙 Dark Mode", use_container_width=True, key=f"dark_mode_{unique_suffix}"):
                toggle_dark_mode()



def apply_theme():
    """Apply current theme CSS to the app"""
    css = get_theme_css()
    st.markdown(css, unsafe_allow_html=True)
def render_footer():
    """Render app footer with gradient styling"""
    from version import __version__, __version_date__
    
    # Footer with gradient background
    st.markdown("""
    <style>
    .gradient-footer {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 12px;
        padding: 1rem 2rem;
        margin-top: 2rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }
    .footer-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .footer-item {
        color: rgba(255,255,255,0.9);
        font-size: 0.8rem;
        text-align: center;
    }
    .footer-item a {
        color: #a8c8ff;
        text-decoration: none;
    }
    .footer-item a:hover {
        text-decoration: underline;
    }
    @media (max-width: 768px) {
        .footer-content {
            flex-direction: column;
            text-align: center;
        }
        .gradient-footer {
            padding: 0.8rem 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create gradient footer
    st.markdown(f"""
    <div class="gradient-footer">
        <div class="footer-content">
            <div class="footer-item">
                📌 Version {__version__} | {__version_date__}
            </div>
            <div class="footer-item">
                🏗️ TenderAI - AI-Powered Tender Management
            </div>
            <div class="footer-item">
                💡 Need help? <a href="mailto:support@tenderai.com">Contact Support</a>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)