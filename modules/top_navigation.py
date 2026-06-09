# modules/top_navigation.py

import streamlit as st

def render_top_navigation():
    """Render top navigation bar for authenticated users"""
    
    # Get current page and user role
    current_page = st.session_state.get('page', 'dashboard')
    user_role = st.session_state.get('user_role', 'viewer')
    is_admin = user_role in ['admin', 'system_admin']
    
    # CSS for top navigation
    st.markdown("""
    <style>
    .top-nav-container {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 0.5rem 1rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }
    .top-nav-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
        justify-content: center;
    }
    .top-nav-btn {
        background: rgba(255,255,255,0.1);
        border: none;
        padding: 0.4rem 1rem;
        border-radius: 6px;
        color: white;
        cursor: pointer;
        font-size: 0.85rem;
        transition: all 0.2s;
        margin: 0 2px;
    }
    .top-nav-btn:hover {
        background: rgba(255,255,255,0.25);
    }
    .top-nav-btn-active {
        background: #22c55e;
        color: white;
    }
    .user-info {
        color: white;
        font-size: 0.8rem;
        text-align: right;
        padding: 0.3rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Define navigation items based on role
    if is_admin:
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📝 Rate Mgmt", "rate_management"),
            ("📥 Import", "import_wizard"),
            ("👥 Users", "user_management"),
            ("📋 Tenders", "tender_management"),
            ("💳 Subscriptions", "subscription"),
            ("⚙️ Admin", "admin_dashboard")
        ]
    else:
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"), 
            ("📊 BOQ", "boq_generator"),
            ("🎯 Optimizer", "boq_bid_optimizer"),
            ("📈 Reports", "analysis_history"),
            ("👥 Team", "user_management"),
            ("💳 Plan", "subscription")
        ]
    
    # User info and logout
    full_name = st.session_state.get('full_name', 'User')
    
    # Create the navigation bar
    st.markdown('<div class="top-nav-container">', unsafe_allow_html=True)
    
    # Create buttons in a row
    cols = st.columns(len(nav_items) + 2)  # +2 for user info and logout
    
    for i, (label, page) in enumerate(nav_items):
        with cols[i]:
            is_active = current_page == page
            if st.button(label, key=f"top_nav_{page}", use_container_width=True, 
                        type="primary" if is_active else "secondary"):
                st.session_state.page = page
                st.rerun()
    
    # User info
    with cols[-2]:
        st.markdown(f"<div style='text-align: right; color: white; padding: 0.3rem;'>👋 {full_name[:15]}</div>", 
                   unsafe_allow_html=True)
    
    # Logout button
    with cols[-1]:
        if st.button("🚪 Logout", key="top_logout", use_container_width=True, type="secondary"):
            # Clear session state
            for key in list(st.session_state.keys()):
                if key not in ['debug_mode', 'page']:
                    del st.session_state[key]
            st.session_state.logged_in = False
            st.session_state.page = "home"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")