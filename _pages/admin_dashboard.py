import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager

db = DatabaseManager()

def show():
    """Admin dashboard page with full system management"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👑 Admin Dashboard</h1>
        <p>System-wide administration and monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get all users for stats
    all_users_raw = db.get_all_users()
    all_subs = db.get_all_subscriptions()
    
    # Convert to dictionary format for consistent access
    all_users = []
    for u in all_users_raw:
        if hasattr(u, 'keys'):  # sqlite3.Row or dict-like
            user_dict = dict(u)
        elif isinstance(u, (tuple, list)):
            # Convert tuple to dict with proper keys
            if len(u) >= 10:
                user_dict = {
                    'id': u[0], 'username': u[1], 'email': u[2], 'full_name': u[3],
                    'phone': u[4], 'role': u[5], 'is_active': u[6],
                    'created_at': u[7], 'last_login': u[8], 'company_name': u[9],
                    'is_approved': u[10] if len(u) > 10 else 1
                }
            else:
                continue
        elif isinstance(u, dict):
            user_dict = u
        else:
            continue
        all_users.append(user_dict)
    
    # Statistics - using dictionary keys
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", len(all_users))
    
    with col2:
        active_users = len([u for u in all_users if u.get('is_active', 0) == 1]) if all_users else 0
        st.metric("Active Users", active_users)
    
    with col3:
        companies = set([u.get('company_name', 'N/A') for u in all_users]) if all_users else set()
        st.metric("Companies", len(companies))
    
    with col4:
        paid_subs = len([s for s in all_subs if len(s) > 2 and s[2] not in ['free', 'trial']]) if all_subs else 0
        st.metric("Paid Subscriptions", paid_subs)
    
    # Tabs for different admin functions
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "👥 All Users", 
        "🏢 Companies", 
        "👑 System Users", 
        "🔐 Role Management"
    ])
    
    with tab1:
        render_admin_overview(all_users, all_subs)
    
    with tab2:
        render_all_users(all_users)
    
    with tab3:
        render_company_management()
    
    with tab4:
        render_system_user_management()
    
    with tab5:
        render_role_management_page()


def render_admin_overview(all_users, all_subs):
    """Render system overview with charts"""
    st.markdown("### System Overview")
    
    # User growth chart (from database)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM users
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """)
    user_growth_data = cursor.fetchall()
    conn.close()
    
    if user_growth_data:
        user_growth = pd.DataFrame(user_growth_data, columns=['Month', 'Users'])
        user_growth = user_growth.iloc[::-1]  # Reverse to show chronological
        st.line_chart(user_growth.set_index('Month'))
    else:
        st.info("No user growth data available")
    
    # Plan distribution
    if all_subs:
        plan_counts = {}
        for sub in all_subs:
            plan = sub[2] if len(sub) > 2 else 'free'
            plan_counts[plan] = plan_counts.get(plan, 0) + 1
        
        plan_df = pd.DataFrame(plan_counts.items(), columns=['Plan', 'Count'])
        st.bar_chart(plan_df.set_index('Plan'))
    
    # Role distribution
    if all_users:
        role_counts = {}
        for user in all_users:
            role = user.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        role_df = pd.DataFrame(role_counts.items(), columns=['Role', 'Count'])
        st.bar_chart(role_df.set_index('Role'))
    
    # Recent activity
    st.markdown("### Recent Activity")
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.action_type, l.target_type, u.username, l.created_at
            FROM activity_logs l
            JOIN users u ON l.actor_user_id = u.id
            ORDER BY l.created_at DESC
            LIMIT 10
        """)
        recent_activity = cursor.fetchall()
        conn.close()
        
        if recent_activity:
            activity_df = pd.DataFrame(recent_activity, columns=['Action', 'Type', 'User', 'Time'])
            st.dataframe(activity_df, use_container_width=True, hide_index=True)
        else:
            st.info("No recent activity")
    except Exception as e:
        st.info("Activity logging not yet enabled")


def render_all_users(all_users):
    """Render all users table"""
    st.markdown("### All Users")
    
    # Search filter
    search = st.text_input("🔍 Search users", placeholder="Name, email, or username...")
    
    if all_users:
        user_list = []
        for u in all_users:
            user_dict = {
                'ID': u.get('id', 'N/A'),
                'Username': u.get('username', 'N/A'),
                'Email': u.get('email', 'N/A'),
                'Full Name': u.get('full_name', 'N/A'),
                'Phone': u.get('phone', ''),
                'Role': u.get('role', 'N/A'),
                'Active': '✅' if u.get('is_active', 0) == 1 else '❌',
                'Company': u.get('company_name', 'N/A'),
                'Created': str(u.get('created_at', ''))[:10] if u.get('created_at') else ''
            }
            
            # Apply search filter
            if search:
                if (search.lower() in user_dict['Username'].lower() or 
                    search.lower() in user_dict['Email'].lower() or 
                    search.lower() in user_dict['Full Name'].lower()):
                    user_list.append(user_dict)
            else:
                user_list.append(user_dict)
        
        if user_list:
            user_df = pd.DataFrame(user_list)
            st.dataframe(user_df, use_container_width=True, hide_index=True)
        else:
            st.info("No users match the search criteria")
    else:
        st.info("No users found")

def render_company_management():
    """Render company management interface for super admin with subscription control"""
    st.markdown("### 🏢 Company Management")
    st.caption("Create, edit, and manage companies on the platform")
    
    # Add New Company (existing code)
    with st.expander("➕ Add New Company", expanded=False):
        with st.form("add_company_form"):
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("Company Name *")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
                division = st.text_input("Division")
            with col2:
                district = st.text_input("District")
                registration_number = st.text_input("Registration Number")
                vat_number = st.text_input("VAT Number")
                address = st.text_area("Address", height=80)
            
            submitted = st.form_submit_button("Create Company", type="primary")
            if submitted:
                if not company_name:
                    st.error("Company name is required")
                else:
                    company_data = {
                        'company_name': company_name,
                        'email': email,
                        'phone': phone,
                        'division': division,
                        'district': district,
                        'address': address,
                        'registration_number': registration_number,
                        'vat_number': vat_number
                    }
                    success, result = db.create_company(company_data)
                    if success:
                        st.success(f"✅ Company '{company_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result}")
    
    # Search and filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search companies", placeholder="Name or email...")
    with col2:
        show_inactive = st.checkbox("Show inactive")
    
    # Get companies
    status_filter = None if show_inactive else 1
    companies, total = db.get_all_companies_filtered(
        search=search,
        status=status_filter,
        limit=50,
        offset=0
    )
    
    st.markdown(f"**Total Companies:** {total}")
    
    # Display companies
    if companies:
        for company in companies:
            # Get subscription info
            subscription = db.get_company_subscription(company['id'])
            
            with st.expander(f"🏢 {company['company_name']} - {company.get('email', 'No email')}"):
                # Create tabs for company details and subscription
                comp_tab1, comp_tab2 = st.tabs(["📋 Company Details", "💳 Subscription"])
                
                with comp_tab1:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Company details form (existing code)
                        new_name = st.text_input("Company Name", value=company['company_name'], key=f"name_{company['id']}")
                        new_email = st.text_input("Email", value=company.get('email', ''), key=f"email_{company['id']}")
                        new_phone = st.text_input("Phone", value=company.get('phone', ''), key=f"phone_{company['id']}")
                        new_division = st.text_input("Division", value=company.get('division', ''), key=f"div_{company['id']}")
                        new_district = st.text_input("District", value=company.get('district', ''), key=f"dist_{company['id']}")
                        new_registration = st.text_input("Registration Number", value=company.get('registration_number', ''), key=f"reg_{company['id']}")
                        new_vat = st.text_input("VAT Number", value=company.get('vat_number', ''), key=f"vat_{company['id']}")
                        new_address = st.text_area("Address", value=company.get('address', ''), key=f"addr_{company['id']}")
                        new_active = st.checkbox("Active", value=company.get('is_active', 1) == 1, key=f"active_{company['id']}")
                        
                        if st.button("💾 Save Company Details", key=f"save_comp_{company['id']}"):
                            updates = {}
                            if new_name != company['company_name']:
                                updates['company_name'] = new_name
                            if new_email != company.get('email'):
                                updates['email'] = new_email
                            if new_phone != company.get('phone'):
                                updates['phone'] = new_phone
                            if new_division != company.get('division'):
                                updates['division'] = new_division
                            if new_district != company.get('district'):
                                updates['district'] = new_district
                            if new_registration != company.get('registration_number'):
                                updates['registration_number'] = new_registration
                            if new_vat != company.get('vat_number'):
                                updates['vat_number'] = new_vat
                            if new_address != company.get('address'):
                                updates['address'] = new_address
                            if new_active != (company.get('is_active', 1) == 1):
                                updates['is_active'] = 1 if new_active else 0
                            
                            if updates:
                                if db.update_company(company['id'], updates):
                                    st.success("Company updated!")
                                    st.rerun()
                                else:
                                    st.error("Update failed")
                    
                    with col2:
                        st.markdown("#### 📊 Statistics")
                        try:
                            stats = db.get_company_stats_by_id(company['id'])
                            st.metric("👥 Users", stats.get('total_users', 0))
                            st.metric("📈 Analyses", stats.get('total_analyses', 0))
                            st.metric("🏆 Win Rate", f"{stats.get('win_rate', 0):.1f}%")
                        except:
                            st.metric("👥 Users", "N/A")
                        
                        st.markdown("---")
                        st.markdown("#### ⚡ Actions")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("👥 Manage Users", key=f"users_{company['id']}"):
                                st.session_state.selected_company_id = company['id']
                                st.session_state.page = "user_management"
                                st.rerun()
                        with col_b:
                            if company.get('is_active', 1) == 1:
                                if st.button("🔒 Deactivate", key=f"deact_{company['id']}"):
                                    db.delete_company(company['id'])
                                    st.success(f"Company {company['company_name']} deactivated")
                                    st.rerun()
                            else:
                                if st.button("🔓 Activate", key=f"act_{company['id']}"):
                                    db.update_company(company['id'], {'is_active': 1})
                                    st.success(f"Company {company['company_name']} activated")
                                    st.rerun()
                        
                        st.caption(f"📅 Created: {company.get('created_at', 'N/A')[:10] if company.get('created_at') else 'N/A'}")
                
                with comp_tab2:
                    st.markdown("#### 💳 Subscription Management")
                    
                    # Display current subscription
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Current Plan", subscription.get('plan', 'free').upper())
                    with col2:
                        st.metric("Status", subscription.get('status', 'active').upper())
                    with col3:
                        limit = subscription.get('analyses_limit', 5)
                        used = subscription.get('analyses_used', 0)
                        if limit == -1:
                            st.metric("Analyses", "Unlimited")
                        else:
                            remaining = max(0, limit - used)
                            st.metric("Analyses Remaining", f"{remaining}/{limit}")
                    
                    st.markdown("---")
                    st.markdown("#### Update Subscription")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_plan = st.selectbox(
                            "Select Plan",
                            options=["free", "basic", "professional", "enterprise"],
                            index=["free", "basic", "professional", "enterprise"].index(subscription.get('plan', 'free')),
                            key=f"plan_select_{company['id']}"
                        )
                    
                    with col2:
                        duration = st.selectbox(
                            "Duration",
                            options=["monthly", "yearly"],
                            key=f"duration_select_{company['id']}"
                        )
                    
                    # Plan benefits
                    plan_benefits = {
                        "free": "• 5 analyses/month\n• Basic reports\n• Email support",
                        "basic": "• 30 analyses/month\n• AI predictions\n• Priority support",
                        "professional": "• Unlimited analyses\n• ML predictions\n• Team collaboration\n• Advanced reporting",
                        "enterprise": "• Everything in Professional\n• Custom AI model\n• Dedicated support\n• API access"
                    }
                    st.info(plan_benefits.get(new_plan, ""))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"💾 Update Subscription", key=f"update_sub_{company['id']}", type="primary"):
                            success = db.update_company_subscription(company['id'], new_plan, duration, 'admin_manual')
                            if success:
                                st.success(f"✅ Subscription updated to {new_plan.upper()}!")
                                st.rerun()
                            else:
                                st.error("Failed to update subscription")
                    
                    with col2:
                        if subscription.get('plan') != 'free':
                            if st.button(f"❌ Cancel Subscription", key=f"cancel_sub_{company['id']}"):
                                success = db.update_company_subscription(company['id'], 'free', 'monthly', 'admin_cancelled')
                                if success:
                                    st.success("Subscription cancelled. Plan set to FREE.")
                                    st.rerun()
                                else:
                                    st.error("Failed to cancel subscription")
                    
                    # Subscription details
                    st.markdown("---")
                    st.markdown("#### Subscription Details")
                    st.caption(f"**Start Date:** {subscription.get('start_date', 'N/A')}")
                    st.caption(f"**End Date:** {subscription.get('end_date', 'N/A')}")
                    if subscription.get('payment_method'):
                        st.caption(f"**Payment Method:** {subscription.get('payment_method')}")
                    if subscription.get('transaction_id'):
                        st.caption(f"**Transaction ID:** {subscription.get('transaction_id')}")
    else:
        st.info("No companies found")

def render_system_user_management():
    """Manage system-level users and company users (for system admin)"""
    st.markdown("### 👥 User Management")
    st.caption("Create users for companies or system-level access")
    
    # ========== ADD NEW USER ==========
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form"):
            st.markdown("#### User Details")
            
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email *")
                username = st.text_input("Username *")
            
            with col2:
                phone = st.text_input("Phone")
                generate_password = st.checkbox("Auto-generate password")
                if not generate_password:
                    password = st.text_input("Password *", type="password")
                    confirm_password = st.text_input("Confirm Password *", type="password")
            
            st.markdown("---")
            st.markdown("#### User Type & Role")
            
            user_type = st.radio(
                "User Type",
                options=["Company User", "System User"],
                help="Company User: Belongs to a specific company | System User: Platform-level access",
                key="user_type_radio_add"
            )
            
            if user_type == "Company User":
                companies, _ = db.get_all_companies_filtered(status=1, limit=200, offset=0)
                company_options = {c['company_name']: c['id'] for c in companies}
                
                if company_options:
                    selected_company = st.selectbox(
                        "Select Company *",
                        options=list(company_options.keys()),
                        key="company_select_add"
                    )
                    company_id = company_options[selected_company]
                    
                    role = st.selectbox(
                        "Role *",
                        options=["company_admin", "manager", "analyst", "viewer"],
                        key="company_role_add"
                    )
                    
                    role_descriptions = {
                        "company_admin": "Full access to company: manage users, tenders, and settings",
                        "manager": "Can manage tenders and create users",
                        "analyst": "Can run analyses and view reports",
                        "viewer": "Read-only access to company data"
                    }
                    st.caption(f"📌 {role_descriptions.get(role, '')}")
                else:
                    st.error("No companies found. Please create a company first.")
                    company_id = None
                    role = "viewer"
            else:
                company_id = None
                role = st.selectbox(
                    "Role *",
                    options=["system_admin", "system_support", "system_auditor"],
                    key="system_role_add"
                )
                
                role_descriptions = {
                    "system_admin": "Full platform access: manage companies, users, roles, and all data",
                    "system_support": "Can view all companies and provide support (no editing)",
                    "system_auditor": "Read-only access across entire platform"
                }
                st.caption(f"📌 {role_descriptions.get(role, '')}")
            
            submitted = st.form_submit_button("Create User", type="primary")                        

            if submitted:
                # Validation
                if not all([full_name, email, username]):
                    st.error("Please fill all required fields")
                elif not generate_password and password != confirm_password:
                    st.error("Passwords do not match")
                elif user_type == "Company User" and not company_id:
                    st.error("Please select a company")
                else:
                    # Generate or use provided password
                    if generate_password:
                        final_password = db.generate_random_password()
                    else:
                        final_password = password
                    
                    user_data = {
                        'username': username.strip(),
                        'password': final_password,
                        'email': email.strip(),
                        'full_name': full_name.strip(),
                        'phone': phone.strip(),
                        'role': role
                    }
                    
                    if user_type == "Company User":
                        success, result = db.create_company_user(company_id, user_data, st.session_state.user_id)
                        user_type_text = f"company user for '{selected_company}'"
                    else:
                        success, result = db.create_system_user(user_data, st.session_state.user_id)
                        user_type_text = "system user"
                    
                    if success:
                        if generate_password:
                            st.success(f"✅ User {full_name} created as {user_type_text}!\n\n**Password:** `{final_password}`")
                        else:
                            st.success(f"✅ User {full_name} created as {user_type_text} successfully!")
                        
                        # Clear form data from session state
                        st.session_state.pop('full_name', None)
                        st.session_state.pop('email', None)
                        st.session_state.pop('username', None)
                        st.session_state.pop('phone', None)
                        st.session_state.pop('password', None)
                        st.session_state.pop('confirm_password', None)
                        
                        # Rerun to clear the form
                        st.rerun()
                    else:
                        st.error(f"Failed: {result}")

    
    # ========== DISPLAY USERS ==========
    st.markdown("### 📋 Users")
    
    tab1, tab2 = st.tabs(["🏢 Company Users", "👑 System Users"])
    
    # ========== COMPANY USERS TAB ==========
    with tab1:
        companies, _ = db.get_all_companies_filtered(status=None, limit=200, offset=0)
        
        if companies:
            for company_idx, company in enumerate(companies):
                try:
                    company_users, company_total = db.get_all_users_filtered(
                        company_id=company['id'],
                        limit=100,
                        offset=0
                    )
                    
                    if company_users:
                        st.markdown(f"#### {company['company_name']} ({company_total} users)")
                        
                        for user_idx, user in enumerate(company_users):
                            if not isinstance(user, dict):
                                continue
                            
                            user_id = user.get('id')
                            if not user_id:
                                continue
                            
                            # Create unique key using company_id, user_id, and timestamp
                            unique_base = f"comp_{company['id']}_user_{user_id}"
                            
                            with st.expander(f"👤 {user.get('full_name', 'Unknown')} ({user.get('username', 'N/A')}) - {user.get('role', 'N/A').title()}"):
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    new_full_name = st.text_input(
                                        "Full Name", 
                                        value=user.get('full_name', ''), 
                                        key=f"{unique_base}_name"
                                    )
                                    new_email = st.text_input(
                                        "Email", 
                                        value=user.get('email', ''), 
                                        key=f"{unique_base}_email"
                                    )
                                    new_phone = st.text_input(
                                        "Phone", 
                                        value=user.get('phone', ''), 
                                        key=f"{unique_base}_phone"
                                    )
                                    
                                    # Role options based on user type
                                    role_options = ["company_admin", "manager", "analyst", "viewer"]
                                    current_role = user.get('role', 'viewer')
                                    
                                    try:
                                        role_index = role_options.index(current_role) if current_role in role_options else 2
                                    except ValueError:
                                        role_index = 2
                                    
                                    new_role = st.selectbox(
                                        "Role",
                                        options=role_options,
                                        index=role_index,
                                        key=f"{unique_base}_role"
                                    )
                                    
                                    new_active = st.checkbox(
                                        "Active", 
                                        value=user.get('is_active', 1) == 1, 
                                        key=f"{unique_base}_active"
                                    )
                                    
                                    if st.button("💾 Save Changes", key=f"{unique_base}_save"):
                                        updates = {}
                                        if new_full_name != user.get('full_name'):
                                            updates['full_name'] = new_full_name
                                        if new_email != user.get('email'):
                                            updates['email'] = new_email
                                        if new_phone != user.get('phone'):
                                            updates['phone'] = new_phone
                                        if new_role != user.get('role'):
                                            updates['role'] = new_role
                                        if new_active != (user.get('is_active', 1) == 1):
                                            updates['is_active'] = 1 if new_active else 0
                                        
                                        if updates:
                                            if db.update_user(user_id, updates):
                                                st.success("User updated!")
                                                st.rerun()
                                
                                with col2:
                                    if st.button("🔑 Reset Password", key=f"{unique_base}_reset"):
                                        success, new_pw = db.reset_user_password(user_id)
                                        if success:
                                            st.success(f"New password: `{new_pw}`")
                                    
                                    if user_id != st.session_state.user_id:
                                        if st.button("🗑️ Delete User", key=f"{unique_base}_delete", type="secondary"):
                                            if db.delete_user(user_id):
                                                st.success("User deleted")
                                                st.rerun()
                                    
                                    st.caption(f"Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
                except Exception as e:
                    st.warning(f"Could not load users for {company.get('company_name', 'Unknown')}: {e}")
        else:
            st.info("No companies found")
    
    # ========== SYSTEM USERS TAB ==========
    with tab2:
        try:
            system_users = db.get_system_users()
        except AttributeError:
            st.warning("get_system_users() method not available")
            return
        
        if system_users:
            for user_idx, user in enumerate(system_users):
                if not isinstance(user, dict):
                    continue
                
                user_id = user.get('id')
                if not user_id:
                    continue
                
                unique_base = f"sys_user_{user_id}"
                
                with st.expander(f"👑 {user.get('full_name', 'Unknown')} ({user.get('username', 'N/A')}) - {user.get('role', 'N/A').replace('_', ' ').title()}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        new_full_name = st.text_input(
                            "Full Name", 
                            value=user.get('full_name', ''), 
                            key=f"{unique_base}_name"
                        )
                        new_email = st.text_input(
                            "Email", 
                            value=user.get('email', ''), 
                            key=f"{unique_base}_email"
                        )
                        new_phone = st.text_input(
                            "Phone", 
                            value=user.get('phone', ''), 
                            key=f"{unique_base}_phone"
                        )
                        
                        role_options = ["system_admin", "system_support", "system_auditor"]
                        current_role = user.get('role', 'system_support')
                        
                        try:
                            role_index = role_options.index(current_role) if current_role in role_options else 1
                        except ValueError:
                            role_index = 1
                        
                        new_role = st.selectbox(
                            "Role",
                            options=role_options,
                            index=role_index,
                            key=f"{unique_base}_role"
                        )
                        new_active = st.checkbox(
                            "Active", 
                            value=user.get('is_active', 1) == 1, 
                            key=f"{unique_base}_active"
                        )
                        
                        if st.button("💾 Save Changes", key=f"{unique_base}_save"):
                            updates = {}
                            if new_full_name != user.get('full_name'):
                                updates['full_name'] = new_full_name
                            if new_email != user.get('email'):
                                updates['email'] = new_email
                            if new_phone != user.get('phone'):
                                updates['phone'] = new_phone
                            if new_role != user.get('role'):
                                updates['role'] = new_role
                            if new_active != (user.get('is_active', 1) == 1):
                                updates['is_active'] = 1 if new_active else 0
                            
                            if updates:
                                if db.update_user(user_id, updates):
                                    st.success("User updated!")
                                    st.rerun()
                    
                    with col2:
                        if st.button("🔑 Reset Password", key=f"{unique_base}_reset"):
                            success, new_pw = db.reset_user_password(user_id)
                            if success:
                                st.success(f"New password: `{new_pw}`")
                        
                        if user_id != st.session_state.user_id:
                            if st.button("🗑️ Delete User", key=f"{unique_base}_delete", type="secondary"):
                                if db.delete_user(user_id):
                                    st.success("User deleted")
                                    st.rerun()
                        
                        st.caption(f"Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
        else:
            st.info("No system users found")

def render_system_user_management_bak():
    """Manage system-level users and company users (for system admin)"""
    st.markdown("### 👥 User Management")
    st.caption("Create users for companies or system-level access")
    
    # ========== ADD NEW USER ==========
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form"):
            # ... (keep the existing form code as is) ...
            pass  # Placeholder - keep your existing form code
    
    # ========== DISPLAY USERS BY TYPE ==========
    st.markdown("### 📋 Users")
    
    # Tabs for different user types
    tab1, tab2 = st.tabs(["🏢 Company Users", "👑 System Users"])
    
    with tab1:
        # Get company users
        companies, _ = db.get_all_companies_filtered(status=1, limit=200, offset=0)
        
        if companies:
            for company in companies:
                try:
                    company_users, company_total = db.get_all_users_filtered(
                        company_id=company['id'],
                        limit=100,
                        offset=0
                    )
                    
                    if company_users:
                        st.markdown(f"#### {company['company_name']} ({company_total} users)")
                        
                        for user in company_users:
                            # Ensure user is a dictionary
                            if not isinstance(user, dict):
                                continue
                            
                            user_id = user.get('id')
                            if not user_id:
                                continue
                            
                            with st.expander(f"👤 {user.get('full_name', 'Unknown')} ({user.get('username', 'N/A')}) - {user.get('role', 'N/A').title()}"):
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    new_full_name = st.text_input("Full Name", value=user.get('full_name', ''), key=f"name_{user_id}")
                                    new_email = st.text_input("Email", value=user.get('email', ''), key=f"email_{user_id}")
                                    new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"phone_{user_id}")
                                    new_role = st.selectbox(
                                        "Role",
                                        options=["company_admin", "manager", "analyst", "viewer"],
                                        index=["company_admin", "manager", "analyst", "viewer"].index(user.get('role', 'viewer')) if user.get('role') in ["company_admin", "manager", "analyst", "viewer"] else 2,
                                        key=f"role_{user_id}"
                                    )
                                    new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"active_{user_id}")
                                    
                                    if st.button("💾 Save Changes", key=f"save_{user_id}"):
                                        updates = {}
                                        if new_full_name != user.get('full_name'):
                                            updates['full_name'] = new_full_name
                                        if new_email != user.get('email'):
                                            updates['email'] = new_email
                                        if new_phone != user.get('phone'):
                                            updates['phone'] = new_phone
                                        if new_role != user.get('role'):
                                            updates['role'] = new_role
                                        if new_active != (user.get('is_active', 1) == 1):
                                            updates['is_active'] = 1 if new_active else 0
                                        
                                        if updates:
                                            if db.update_user(user_id, updates):
                                                st.success("User updated!")
                                                st.rerun()
                                
                                with col2:
                                    if st.button("🔑 Reset Password", key=f"reset_{user_id}"):
                                        success, new_pw = db.reset_user_password(user_id)
                                        if success:
                                            st.success(f"New password: `{new_pw}`")
                                    
                                    if user_id != st.session_state.user_id:
                                        if st.button("🗑️ Delete User", key=f"delete_{user_id}", type="secondary"):
                                            if db.delete_user(user_id):
                                                st.success("User deleted")
                                                st.rerun()
                                    
                                    st.caption(f"Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
                except Exception as e:
                    st.warning(f"Could not load users for {company.get('company_name', 'Unknown')}: {e}")
        else:
            st.info("No companies found. Create a company first.")
    
    with tab2:
        # Get system users
        try:
            system_users = db.get_system_users()
        except AttributeError:
            st.warning("get_system_users() method not available. Please update db_manager.py")
            return
        
        if system_users:
            for user in system_users:
                # Ensure user is a dictionary
                if not isinstance(user, dict):
                    continue
                
                user_id = user.get('id')
                if not user_id:
                    continue
                
                with st.expander(f"👑 {user.get('full_name', 'Unknown')} ({user.get('username', 'N/A')}) - {user.get('role', 'N/A').replace('_', ' ').title()}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        new_full_name = st.text_input("Full Name", value=user.get('full_name', ''), key=f"sys_name_{user_id}")
                        new_email = st.text_input("Email", value=user.get('email', ''), key=f"sys_email_{user_id}")
                        new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"sys_phone_{user_id}")
                        
                        # Determine role options based on current role
                        role_options = ["system_admin", "system_support", "system_auditor"]
                        current_role = user.get('role', 'system_support')
                        
                        try:
                            role_index = role_options.index(current_role) if current_role in role_options else 1
                        except ValueError:
                            role_index = 1
                        
                        new_role = st.selectbox(
                            "Role",
                            options=role_options,
                            index=role_index,
                            key=f"sys_role_{user_id}"
                        )
                        new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"sys_active_{user_id}")
                        
                        if st.button("💾 Save Changes", key=f"sys_save_{user_id}"):
                            updates = {}
                            if new_full_name != user.get('full_name'):
                                updates['full_name'] = new_full_name
                            if new_email != user.get('email'):
                                updates['email'] = new_email
                            if new_phone != user.get('phone'):
                                updates['phone'] = new_phone
                            if new_role != user.get('role'):
                                updates['role'] = new_role
                            if new_active != (user.get('is_active', 1) == 1):
                                updates['is_active'] = 1 if new_active else 0
                            
                            if updates:
                                if db.update_user(user_id, updates):
                                    st.success("User updated!")
                                    st.rerun()
                    
                    with col2:
                        if st.button("🔑 Reset Password", key=f"sys_reset_{user_id}"):
                            success, new_pw = db.reset_user_password(user_id)
                            if success:
                                st.success(f"New password: `{new_pw}`")
                        
                        if user_id != st.session_state.user_id:
                            if st.button("🗑️ Delete User", key=f"sys_del_{user_id}", type="secondary"):
                                if db.delete_user(user_id):
                                    st.success("User deleted")
                                    st.rerun()
                        
                        st.caption(f"Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
        else:
            st.info("No system users found")

def render_role_management_page():
    """Render role permissions management"""
    st.markdown("### 🔐 Role Permissions Management")
    st.caption("Configure what each role can do in the system")
    
    try:
        roles = db.get_all_roles()
    except AttributeError:
        st.warning("get_all_roles() method not available. Please update db_manager.py")
        return
    
    if not roles:
        st.warning("No roles found. Please run database migration.")
        return
    
    # Display role hierarchy
    st.markdown("#### Role Hierarchy")
    role_hierarchy = {
        'system_admin': '👑 Full platform access',
        'system_support': '🛠️ Can view all companies, support access',
        'system_auditor': '📊 Read-only across platform',
        'company_admin': '🏢 Full company management',
        'manager': '📋 Can manage tenders and create users',
        'analyst': '🔬 Can run analyses and view reports',
        'viewer': '👁️ Read-only access'
    }
    
    for role, desc in role_hierarchy.items():
        if any(r['role'] == role for r in roles):
            st.markdown(f"- **{role.replace('_', ' ').title()}**: {desc}")
    
    st.markdown("---")
    st.markdown("#### Edit Role Permissions")
    
    for role_info in roles:
        role_name = role_info['role']
        permissions = role_info['permissions']
        
        with st.expander(f"📌 {role_name.replace('_', ' ').title()}", expanded=False):
            st.markdown(f"**Role:** `{role_name}`")
            st.markdown(f"**Description:** {role_hierarchy.get(role_name, 'No description')}")
            
            # Display key permissions
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**User Management**")
                user_perms = ['manage_users', 'manage_team', 'create_user', 'delete_user']
                for perm in user_perms:
                    if perm in permissions:
                        current = permissions.get(perm, False)
                        new_val = st.checkbox(perm.replace('_', ' ').title(), value=current, key=f"{role_name}_{perm}")
                        permissions[perm] = new_val
            
            with col2:
                st.markdown("**Tender & Analysis**")
                tender_perms = ['manage_tenders', 'run_analysis', 'view_reports', 'export_data']
                for perm in tender_perms:
                    if perm in permissions:
                        current = permissions.get(perm, False)
                        new_val = st.checkbox(perm.replace('_', ' ').title(), value=current, key=f"{role_name}_{perm}")
                        permissions[perm] = new_val
            
            if st.button(f"💾 Save Permissions for {role_name}", key=f"save_role_{role_name}"):
                success = db.update_role_permissions(role_name, permissions)
                if success:
                    st.success(f"Permissions for {role_name} updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update permissions")