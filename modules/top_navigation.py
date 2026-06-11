# modules/top_navigation.py

import streamlit as st

def render_top_navigation():
    """Render top navigation bar for authenticated users with role-based access"""
    
    # Get current page and user role
    current_page = st.session_state.get('page', 'dashboard')
    user_role = st.session_state.get('user_role', 'viewer')
    
    # Define role-based permissions
    is_admin = user_role in ['admin', 'system_admin']
    is_company_admin = user_role in ['admin', 'system_admin', 'company_admin']
    is_analyst = user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst']
    is_viewer = user_role == 'viewer'
    
    # Check subscription for premium features
    sub = st.session_state.get('subscription', {})
    plan = sub.get('plan', 'free')
    is_premium = plan in ['professional', 'enterprise'] or is_admin
    
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
        # Admin navigation - full access
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📝 Rate Mgmt", "rate_management"),
            ("📥 Import", "import_wizard"),
            ("👥 Users", "user_management"),
            ("📋 Tenders", "tender_management"),
            ("🎯 Bid Optimizer", "boq_bid_optimizer"),
            ("🔮 Scenario Gen", "scenario_generator"),  # ✅ Added
            ("💳 Subscriptions", "subscription"),
            ("⚙️ Admin", "admin_dashboard")
        ]
    elif is_company_admin:
        # Company Admin navigation
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("📊 BOQ", "boq_generator"),
            ("🎯 Optimizer", "boq_bid_optimizer"),
            ("🔮 Scenario Gen", "scenario_generator"),  # ✅ Added
            ("📈 Reports", "analysis_history"),
            ("👥 Team", "user_management"),
            ("💳 Plan", "subscription")
        ]
    elif is_analyst:
        # Analyst/Manager navigation - no team management
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("📊 BOQ", "boq_generator"),
            ("🎯 Optimizer", "boq_bid_optimizer"),
            ("🔮 Scenario Gen", "scenario_generator") if is_premium else None,  # ✅ Premium only
            ("📈 Reports", "analysis_history"),
            ("💳 Plan", "subscription")
        ]
        # Remove None items
        nav_items = [item for item in nav_items if item is not None]
    elif is_viewer:
        # Viewer navigation - read-only access
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 View Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("📈 Reports", "analysis_history")
        ]
    else:
        # Default for other roles
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📊 BOQ", "boq_generator"),
            ("🎯 Optimizer", "boq_bid_optimizer"),
            ("🔮 Scenario Gen", "scenario_generator") if is_premium else None,
        ]
        nav_items = [item for item in nav_items if item is not None]
    
    # User info
    full_name = st.session_state.get('full_name', 'User')
    company_name = st.session_state.get('company_name', '')
    
    # Create the navigation bar
    st.markdown('<div class="top-nav-container">', unsafe_allow_html=True)
    
    # Calculate number of columns needed (nav items + user info + logout)
    num_cols = len(nav_items) + 2
    cols = st.columns(num_cols)
    
    # Navigation buttons
    for i, (label, page) in enumerate(nav_items):
        with cols[i]:
            is_active = current_page == page
            # Special styling for Scenario Generator
            if page == "scenario_generator":
                button_label = f"✨ {label}"
            else:
                button_label = label
                
            if st.button(button_label, key=f"top_nav_{page}", use_container_width=True, 
                        type="primary" if is_active else "secondary"):
                st.session_state.page = page
                st.rerun()
    
    # User info with role badge
    with cols[-2]:
        role_badge = {
            'admin': '👑 Admin',
            'system_admin': '👑 SysAdmin',
            'company_admin': '🏢 Company Admin',
            'manager': '📊 Manager',
            'analyst': '📈 Analyst',
            'data_entry': '📝 Data Entry',
            'viewer': '👁️ Viewer'
        }.get(user_role, '👤 User')
        
        # Add premium badge for eligible users
        premium_badge = " ✨" if is_premium and not is_admin else ""
        
        st.markdown(f"""
        <div style='text-align: right; padding: 0.3rem;'>
            <span style='color: white; font-size: 0.8rem;'>
                👋 {full_name[:15]} | {role_badge}{premium_badge}
            </span>
        </div>
        """, unsafe_allow_html=True)
    
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