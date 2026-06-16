# modules/top_navigation.py - Replace the entire file

import streamlit as st
# modules/top_navigation.py - FIXED VERSION

import streamlit as st

# modules/top_navigation.py - Updated with Basic Bid Optimizer

import streamlit as st

def render_top_navigation():
    """Render top navigation bar for authenticated users with role-based access"""
    
    # Get current page and user role
    current_page = st.session_state.get('page', 'dashboard')
    user_role = st.session_state.get('user_role', 'viewer')
    
    # Define role-based permissions
    is_system_admin = user_role == 'system_admin'
    is_regular_admin = user_role == 'admin'
    is_company_admin = user_role in ['company_admin']
    is_manager = user_role in ['manager']
    is_analyst = user_role in ['analyst']
    is_viewer = user_role == 'viewer'
    
    # Check subscription for premium features
    sub = st.session_state.get('subscription', {})
    plan = sub.get('plan', 'free')
    is_premium = plan in ['professional', 'enterprise'] or is_system_admin or is_regular_admin
    
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
    .user-info {
        color: white;
        font-size: 0.8rem;
        text-align: right;
        padding: 0.3rem 0;
    }
    .premium-badge {
        background: #ffd700;
        color: #1e3c72;
        border-radius: 12px;
        padding: 2px 8px;
        font-size: 0.7rem;
        margin-left: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ========== DEFINE NAVIGATION BASED ON ROLE (MUTUALLY EXCLUSIVE) ==========
    from modules.rbac import _rbac, is_premium_user
    if _rbac.has_permission('can_optimize_bid'):
        # Show premium features
        st.sidebar.markdown("### 🚀 Premium Features")
        if st.sidebar.button("🎯 Advanced Optimizer"):
            st.session_state.page = "new_analysis"
            st.rerun()
        if st.sidebar.button("🔮 Competitive Simulator"):
            st.session_state.page = "competitive_bid_simulator"
            st.rerun()
    else:
        st.sidebar.info("💡 Upgrade to premium for advanced features")
    role = _rbac.get_current_user_role()
    is_premium = is_premium_user(role)

    if is_system_admin:
        # System Admin - Full platform control
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📊 Analytics", "admin_analytics"),
            ("📝 Rate Mgmt", "rate_management"),
            ("📥 Import", "import_wizard"),
            ("👥 Users", "user_management"),
            ("📋 Tenders", "tender_management"),
            #("📈 Basic Optimizer", "basic_bid_optimizer"),      # ✅ NEW - Free for all
            ("📈 Basic Optimizer", "boq_bid_optimizer"),      # ✅ NEW - Free for all
            ("🎯 Advanced Optimizer", "new_analysis"),     # Premium
            
            ("🔮 Competitive Simulator", "competitive_bid_simulator"),  # Premium
            ("🏢 Knowledge Repo", "company_knowledge"),
            ("🤖 Extensions", "extension_admin"),
            ("💳 Subscriptions", "subscription"),
            ("⚙️ Admin Dashboard", "admin_dashboard"),
            ("📖 Tutorial", "tutorial")
        ]
    elif is_regular_admin:
        # Regular Admin - Similar to system admin but limited
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📝 Rate Mgmt", "rate_management"),
            ("📥 Import", "import_wizard"),
            ("👥 Users", "user_management"),
            ("📋 Tenders", "tender_management"),
            #("📈 Basic Optimizer", "basic_bid_optimizer"),      # ✅ NEW - Free for all
            ("📈 Basic Optimizer", "boq_bid_optimizer"),      # ✅ NEW - Free for all
            ("🎯 Advanced Optimizer", "new_analysis"),     # Premium            
            ("🔮 Competitive Simulator", "competitive_bid_simulator"),  # Premium
            ("🏢 Knowledge Repo", "company_knowledge"),
            ("🤖 Extension", "extension_usage"),
            ("💳 Subscriptions", "subscription"),
            ("⚙️ Admin", "admin_dashboard"),
            ("📖 Tutorial", "tutorial")
        ]
    
    elif is_company_admin:
        # Company Admin - Own company only
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("🏠 Analytics", "company_analytics"),
            ("📋 Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("📊 BOQ", "boq_generator"),
            #("📈 Basic Optimizer", "basic_bid_optimizer"),      # ✅ NEW - Free for all
            ("📈 Basic Optimizer", "boq_bid_optimizer"),      # ✅ NEW - Free for all
            ("🎯 Advanced Optimizer", "new_analysis"),     # Premium            
            ("🔮 Competitive Simulator", "competitive_bid_simulator"),  # Premium
            ("🏢 Knowledge Repo", "company_knowledge"),
            ("📥 Download Extension", "extension_download"),
            ("🤖 Extension", "extension_usage"),
            ("📈 Reports", "analysis_history"),
            ("👥 Team", "user_management"),
            ("💳 Plan", "subscription"),
            ("📖 Tutorial", "tutorial")
        ]
    
    elif is_manager:
        # Manager - Operational access
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("📊 BOQ", "boq_generator"),
            #("📈 Basic Optimizer", "basic_bid_optimizer"),      # ✅ NEW - Free for all
            ("📈 Basic Optimizer", "boq_bid_optimizer"),      # ✅ NEW - Free for all
            ("🎯 Advanced Optimizer", "new_analysis"),     # Premium                        
            ("🔮 Competitive Simulator", "competitive_bid_simulator") if is_premium else None,
            ("🏢 Knowledge Repo", "company_knowledge") if is_premium else None,
            ("📥 Download Extension", "extension_download"),
            ("🤖 Extension", "extension_usage") if is_premium else None,
            ("📈 Reports", "analysis_history"),
            ("💳 Plan", "subscription"),
            ("📖 Tutorial", "tutorial")
        ]
        nav_items = [item for item in nav_items if item is not None]
    
    elif is_analyst:
        # Analyst - Analysis only
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("📊 BOQ", "boq_generator"),
            #("📈 Basic Optimizer", "basic_bid_optimizer"),      # ✅ NEW - Free for all
            ("📈 Basic Optimizer", "boq_bid_optimizer"),      # ✅ NEW - Free for all
            ("🎯 Advanced Optimizer", "new_analysis"),     # Premium            
            ("🔮 Competitive Simulator", "competitive_bid_simulator") if is_premium else None,
            ("🏢 Knowledge Repo", "company_knowledge") if is_premium else None,
            ("🤖 Extension", "extension_usage") if is_premium else None,
            ("📥 Download Extension", "extension_download"),
            ("📈 Reports", "analysis_history"),
            ("💳 Plan", "subscription"),
            ("📖 Tutorial", "tutorial")
        ]
        nav_items = [item for item in nav_items if item is not None]
    
    elif is_viewer:
        # Viewer - Read-only
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 View Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            #("📈 Basic Optimizer", "basic_bid_optimizer"),      # ✅ NEW - Free for all
            ("📈 Basic Optimizer", "boq_bid_optimizer"),      # ✅ NEW - Free for all                        
            ("📥 Download Extension", "extension_download"),
            ("🏢 Knowledge Repo", "company_knowledge"),
            ("📈 Reports", "analysis_history"),
            ("📖 Tutorial", "tutorial")
        ]
    
    else:
        # Default fallback
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📊 BOQ", "boq_generator"),
            #("📈 Basic Optimizer", "basic_bid_optimizer"),      # ✅ NEW
            ("📈 Basic Optimizer", "boq_bid_optimizer"),      # ✅ NEW - Free for all
            #("🎯 Advanced Optimizer", "new_analysis"),     # Premium            
            #("🎯 Advanced Optimizer", "boq_bid_optimizer")
            ("📥 Download Extension", "extension_download"),
            ("📈 Reports", "analysis_history"),
            ("📖 Tutorial", "tutorial")
        ]
    
    # User info
    full_name = st.session_state.get('full_name', 'User')
    
    # Get extension usage for badge
    extension_used = st.session_state.get('extension_fills_used', 0)
    extension_limit = st.session_state.get('extension_fills_limit', 5)
    extension_remaining = extension_limit - extension_used if extension_limit != -1 else "∞"
    
    # Create the navigation bar
    st.markdown('<div class="top-nav-container">', unsafe_allow_html=True)
    
    # Calculate number of columns needed
    num_cols = len(nav_items) + 2
    cols = st.columns(num_cols)
    
    # Navigation buttons
    for i, (label, page) in enumerate(nav_items):
        with cols[i]:
            is_active = current_page == page
            
            # Special styling for different pages
            if page == "basic_bid_optimizer":
                # Basic Optimizer - Show free badge
                button_label = f"{label}"
            elif page == "boq_bid_optimizer":
                # Advanced Optimizer - Show premium badge
                button_label = f"{label}"
            elif page == "competitive_bid_simulator":
                # Competitive Simulator - Show premium badge
                button_label = f"{label}"
            elif page == "company_knowledge":
                button_label = f"{label}"
            elif page == "extension_admin" or page == "extension_usage":
                # Show remaining fills badge
                if extension_remaining == "∞":
                    button_label = f"{label} (∞)"
                elif extension_remaining > 0:
                    button_label = f"{label} ({extension_remaining})"
                else:
                    button_label = f"{label} (❗)"
            else:
                button_label = label
                
            if st.button(button_label, key=f"top_nav_{page}", use_container_width=True, 
                        type="primary" if is_active else "secondary"):
                st.session_state.page = page
                st.rerun()
    
    # # User info with role badge
    # with cols[-2]:
    #     role_badge = {
    #         'system_admin': '👑 SysAdmin',
    #         'admin': '👑 Admin',
    #         'company_admin': '🏢 Company Admin',
    #         'manager': '📊 Manager',
    #         'analyst': '📈 Analyst',
    #         'data_entry': '📝 Data Entry',
    #         'viewer': '👁️ Viewer'
    #     }.get(user_role, '👤 User')
        
    #     # Add premium badge for eligible users
    #     premium_badge = " ✨" if is_premium and not (is_system_admin or is_regular_admin) else ""
        
    #     st.markdown(f"""
    #     <div style='text-align: right; padding: 0.3rem;'>
    #         <span style='color: white; font-size: 0.8rem;'>
    #             👋 {full_name[:20]} | {role_badge}{premium_badge}
    #         </span>
    #     </div>
    #     """, unsafe_allow_html=True)
    
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

def render_top_navigation_bak():
    """Render top navigation bar for authenticated users with role-based access"""
    
    # Get current page and user role
    current_page = st.session_state.get('page', 'dashboard')
    user_role = st.session_state.get('user_role', 'viewer')
    
    # Define role-based permissions
    is_system_admin = user_role == 'system_admin'
    is_regular_admin = user_role == 'admin'
    is_company_admin = user_role in ['company_admin']
    is_manager = user_role in ['manager']
    is_analyst = user_role in ['analyst']
    is_viewer = user_role == 'viewer'
    
    # Check subscription for premium features
    sub = st.session_state.get('subscription', {})
    plan = sub.get('plan', 'free')
    is_premium = plan in ['professional', 'enterprise'] or is_system_admin or is_regular_admin
    
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
    .user-info {
        color: white;
        font-size: 0.8rem;
        text-align: right;
        padding: 0.3rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ========== DEFINE NAVIGATION BASED ON ROLE (MUTUALLY EXCLUSIVE) ==========
    
    if is_system_admin:
        # System Admin - Full platform control
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📝 Rate Mgmt", "rate_management"),
            ("📥 Import", "import_wizard"),
            ("👥 Users", "user_management"),
            ("📋 Tenders", "tender_management"),
            ("🎯 Bid Optimizer", "boq_bid_optimizer"),
            ("🔮 Simulator", "competitive_bid_simulator"),
            ("🏢 Knowledge Repo", "company_knowledge"),
            ("🤖 Extension Admin", "extension_admin"),  # System admin only
            ("💳 Subscriptions", "subscription"),
            ("⚙️ Admin Dashboard", "admin_dashboard")
        ]
    
    elif is_regular_admin:
        # Regular Admin - Similar to system admin but limited
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📝 Rate Mgmt", "rate_management"),
            ("📥 Import", "import_wizard"),
            ("👥 Users", "user_management"),
            ("📋 Tenders", "tender_management"),
            ("🎯 Bid Optimizer", "boq_bid_optimizer"),
            ("🔮 Simulator", "competitive_bid_simulator"),
            ("🏢 Knowledge Repo", "company_knowledge"),
            ("🤖 Extension", "extension_usage"),  # Regular admin sees company usage
            ("💳 Subscriptions", "subscription"),
            ("⚙️ Admin", "admin_dashboard")
        ]
    
    elif is_company_admin:
        # Company Admin - Own company only
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("📊 BOQ", "boq_generator"),
            ("🎯 Optimizer", "boq_bid_optimizer"),
            ("🔮 Simulator", "competitive_bid_simulator"),
            ("🏢 Knowledge Repo", "company_knowledge"),
            ("🤖 Extension", "extension_usage"),
            ("📈 Reports", "analysis_history"),
            ("👥 Team", "user_management"),
            ("💳 Plan", "subscription")
        ]
    
    elif is_manager:
        # Manager - Operational access
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("📊 BOQ", "boq_generator"),
            ("🎯 Optimizer", "boq_bid_optimizer"),
            ("🔮 Simulator", "competitive_bid_simulator") if is_premium else None,
            ("🏢 Knowledge Repo", "company_knowledge") if is_premium else None,
            ("🤖 Extension", "extension_usage") if is_premium else None,
            ("📈 Reports", "analysis_history"),
            ("💳 Plan", "subscription")
        ]
        nav_items = [item for item in nav_items if item is not None]
    
    elif is_analyst:
        # Analyst - Analysis only
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("📊 BOQ", "boq_generator"),
            ("🎯 Optimizer", "boq_bid_optimizer"),
            ("🔮 Simulator", "competitive_bid_simulator") if is_premium else None,
            ("🏢 Knowledge Repo", "company_knowledge") if is_premium else None,
            ("🤖 Extension", "extension_usage") if is_premium else None,
            ("📈 Reports", "analysis_history"),
            ("💳 Plan", "subscription")
        ]
        nav_items = [item for item in nav_items if item is not None]
    
    elif is_viewer:
        # Viewer - Read-only
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📋 View Tenders", "tender_management"),
            ("📊 Rate Viewer", "rate_viewer"),
            ("🏢 Knowledge Repo", "company_knowledge"),
            ("📈 Reports", "analysis_history")
        ]
    
    else:
        # Default fallback
        nav_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📊 BOQ", "boq_generator"),
            ("🎯 Optimizer", "boq_bid_optimizer")
        ]
    
    # User info
    full_name = st.session_state.get('full_name', 'User')
    
    # Get extension usage for badge
    extension_used = st.session_state.get('extension_fills_used', 0)
    extension_limit = st.session_state.get('extension_fills_limit', 5)
    extension_remaining = extension_limit - extension_used if extension_limit != -1 else "∞"
    
    # Create the navigation bar
    st.markdown('<div class="top-nav-container">', unsafe_allow_html=True)
    
    # Calculate number of columns needed
    num_cols = len(nav_items) + 2
    cols = st.columns(num_cols)
    
    # Navigation buttons
    for i, (label, page) in enumerate(nav_items):
        with cols[i]:
            is_active = current_page == page
            
            # Special styling for simulator and knowledge repo
            if page == "competitive_bid_simulator":
                button_label = f"{label}"
            elif page == "company_knowledge":
                button_label = f"{label}"
            elif page == "extension_admin" or page == "extension_usage":
                # Show remaining fills badge
                if extension_remaining == "∞":
                    button_label = f"{label} (∞)"
                elif extension_remaining > 0:
                    button_label = f"{label} ({extension_remaining})"
                else:
                    button_label = f"{label} (❗)"
            else:
                button_label = label
                
            if st.button(button_label, key=f"top_nav_{page}", use_container_width=True, 
                        type="primary" if is_active else "secondary"):
                st.session_state.page = page
                st.rerun()
    
    # User info with role badge
    
    # with cols[-2]:
    #     role_badge = {
    #         'system_admin': '👑 SysAdmin',
    #         'admin': '👑 Admin',
    #         'company_admin': '🏢 Company Admin',
    #         'manager': '📊 Manager',
    #         'analyst': '📈 Analyst',
    #         'data_entry': '📝 Data Entry',
    #         'viewer': '👁️ Viewer'
    #     }.get(user_role, '👤 User')
        
    #     # Add premium badge for eligible users
    #     premium_badge = " ✨" if is_premium and not (is_system_admin or is_regular_admin) else ""
        
    #     st.markdown(f"""
    #     <div style='text-align: right; padding: 0.3rem;'>
    #         <span style='color: white; font-size: 0.8rem;'>
    #             👋 {full_name[:20]} | {role_badge}{premium_badge}
    #         </span>
    #     </div>
    #     """, unsafe_allow_html=True)
    
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