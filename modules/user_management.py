import streamlit as st
import pandas as pd
from database.unified_db_manager import UnifiedDatabaseManager
from utils.helpers import validate_password_strength
import re

db = UnifiedDatabaseManager()

import streamlit as st
import pandas as pd
from database.unified_db_manager import UnifiedDatabaseManager
from utils.helpers import validate_password_strength
import re

db = UnifiedDatabaseManager()
def render_user_management():
    """Full user management with CRUD, search, pagination, inline editing"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👥 User Management</h1>
        <p>Manage team members, roles, and permissions</p>
    </div>
    """, unsafe_allow_html=True)
    
    company_id = st.session_state.get('company_id')
    if not company_id:
        st.error("Company ID not found. Please log in again.")
        return
    
    # ========== SESSION STATE FOR PAGINATION & FILTERS ==========
    if 'user_page' not in st.session_state:
        st.session_state.user_page = 1
    if 'user_search' not in st.session_state:
        st.session_state.user_search = ""
    if 'user_role_filter' not in st.session_state:
        st.session_state.user_role_filter = ""
    if 'user_status_filter' not in st.session_state:
        st.session_state.user_status_filter = None
    
    # ========== FILTERS & SEARCH ==========
    st.markdown("### 🔍 Filter Users")
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search_term = st.text_input("Search by name, username, or email", 
                                    value=st.session_state.user_search,
                                    key="user_search_input")
    with col2:
        role_filter = st.selectbox("Role", ["All", "company_admin", "manager", "analyst", "viewer"],
                                   index=0, key="role_filter_select")
    with col3:
        status_filter = st.selectbox("Status", ["All", "Active", "Inactive"],
                                     index=0, key="status_filter_select")
    with col4:
        if st.button("🔄 Reset Filters", use_container_width=True):
            st.session_state.user_search = ""
            st.session_state.user_role_filter = ""
            st.session_state.user_status_filter = None
            st.session_state.user_page = 1
            st.rerun()
    
    # Update session state based on current inputs
    st.session_state.user_search = search_term
    st.session_state.user_role_filter = "" if role_filter == "All" else role_filter
    st.session_state.user_status_filter = None if status_filter == "All" else (1 if status_filter == "Active" else 0)
    
    # ========== PAGINATION SETUP ==========
    users_per_page = 10
    offset = (st.session_state.user_page - 1) * users_per_page
    
    users, total = db.get_all_users_filtered(
        company_id=company_id,
        search=st.session_state.user_search,
        role=st.session_state.user_role_filter,
        status=st.session_state.user_status_filter,
        limit=users_per_page,
        offset=offset
    )
    
    # Stats cards (using dictionary keys, not indices)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Users", total)
    with col2:
        active_count = len([u for u in users if u.get('is_active') == 1])
        st.metric("Active Users", active_count)
    with col3:
        admin_count = len([u for u in users if u.get('role') in ['admin', 'company_admin']])
        st.metric("Admins", admin_count)
    with col4:
        analyst_count = len([u for u in users if u.get('role') == 'analyst'])
        st.metric("Analysts", analyst_count)
    
    # ========== ADD USER FORM (Collapsible) ==========
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email *")
                username = st.text_input("Username *")
                mobile_number = st.text_input("Mobile Number *", help="Bangladeshi mobile: 01XXXXXXXXX")
                role = st.selectbox("Role *", ["company_admin", "manager", "analyst", "viewer"])
            with col2:
                phone = st.text_input("Phone")
                generate_password = st.checkbox("Auto-generate password")
                if not generate_password:
                    password = st.text_input("Temporary Password *", type="password")
                    confirm_password = st.text_input("Confirm Password *", type="password")
            
            score = 0
            if not generate_password and password:
                score, msg, color = validate_password_strength(password)
                st.progress(score / 100)
                st.markdown(f"<small style='color:{color}'>{msg}</small>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Add User", type="primary")
            if submitted:
                if not all([full_name, email, username]):
                    st.error("Please fill all required fields (*)")
                elif not generate_password and password != confirm_password:
                    st.error("Passwords do not match")
                elif not generate_password and score < 60:
                    st.error("Password is too weak")
                else:
                    final_password = db.generate_random_password() if generate_password else password
                    
                    user_data = {
                        'username': username.strip(),
                        'password': final_password,
                        'email': email.strip(),
                        'full_name': full_name.strip(),
                        'phone': phone.strip(),
                        'mobile_number': mobile_number.strip(),
                        'role': role
                    }
                    success, result = db.create_user(company_id, user_data, st.session_state.user_id)
                    if success:
                        if generate_password:
                            st.success(f"User {full_name} added successfully! Password: `{final_password}`")
                        else:
                            st.success(f"User {full_name} added successfully!")
                        st.session_state.user_page = 1
                        st.rerun()
                    else:
                        st.error(f"Error: {result}")
    
    # ========== USER LIST WITH EXPANDERS ==========
    st.markdown("### 📋 Team Members")
    
    if not users:
        st.info("No users found matching the criteria.")
        return
    
    for user in users:
        user_id = user.get('id')
        username = user.get('username', 'N/A')
        email = user.get('email', 'N/A')
        full_name = user.get('full_name', 'N/A')
        phone = user.get('phone', '') or ""
        role = user.get('role', 'viewer')
        is_active = user.get('is_active', 1)
        created_at = user.get('created_at', 'N/A')
        last_login = user.get('last_login', None)
        
        with st.expander(f"{full_name} ({username}) - {role.replace('_', ' ').title()}", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Editable fields
                new_full_name = st.text_input("Full Name", value=full_name, key=f"name_{user_id}")
                new_email = st.text_input("Email", value=email, key=f"email_{user_id}")
                new_phone = st.text_input("Phone", value=phone, key=f"phone_{user_id}")
                new_role = st.selectbox(
                    "Role",
                    options=["company_admin", "manager", "analyst", "viewer"],
                    index=["company_admin", "manager", "analyst", "viewer"].index(role) if role in ["company_admin", "manager", "analyst", "viewer"] else 2,
                    key=f"role_{user_id}"
                )
                new_status = st.checkbox("Active", value=bool(is_active), key=f"status_{user_id}")
                
                if st.button("💾 Save Changes", key=f"save_{user_id}"):
                    updates = {}
                    if new_full_name != full_name:
                        updates['full_name'] = new_full_name
                    if new_email != email:
                        if re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                            updates['email'] = new_email
                        else:
                            st.error("Invalid email format")
                    if new_phone != phone:
                        updates['phone'] = new_phone
                    if new_role != role:
                        updates['role'] = new_role
                    if new_status != bool(is_active):
                        updates['is_active'] = 1 if new_status else 0
                    
                    if updates:
                        success = db.update_user(user_id, updates)
                        if success:
                            st.success("User updated successfully")
                            st.rerun()
                        else:
                            st.error("Failed to update user")
                    else:
                        st.info("No changes made")
            
            with col2:
                st.markdown("#### Actions")
                
                if st.button("🔑 Reset Password", key=f"reset_pw_{user_id}"):
                    success, new_pw = db.reset_user_password(user_id)
                    if success:
                        st.success(f"New password: `{new_pw}`")
                
                if user_id != st.session_state.user_id:
                    if st.button("🗑️ Delete User", key=f"delete_{user_id}", type="secondary"):
                        success = db.delete_user(user_id)
                        if success:
                            st.success(f"User {full_name} deleted")
                            st.rerun()
                        else:
                            st.error("Delete failed")
                else:
                    st.caption("(You cannot delete your own account)")
                
                st.markdown("---")
                st.markdown(f"**Created:** {str(created_at)[:16] if created_at else 'N/A'}")
                st.markdown(f"**Last Login:** {str(last_login)[:16] if last_login else 'Never'}")
    
    # ========== PAGINATION CONTROLS ==========
    total_pages = (total + users_per_page - 1) // users_per_page
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀ Previous", disabled=(st.session_state.user_page <= 1)):
                st.session_state.user_page -= 1
                st.rerun()
        with col2:
            st.write(f"Page {st.session_state.user_page} of {total_pages}")
        with col3:
            if st.button("Next ▶", disabled=(st.session_state.user_page >= total_pages)):
                st.session_state.user_page += 1
                st.rerun()

def render_role_management():
    """UI for managing role-based permissions (admin/company_admin only)"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Role & Permission Management</h1>
        <p>Define what each role can do in the system</p>
    </div>
    """, unsafe_allow_html=True)

    # Check permission
    user_role = st.session_state.get('user_role')
    if user_role not in ['admin', 'system_admin', 'company_admin']:
        st.error("❌ You don't have permission to manage roles.")
        return

    # Get all roles and their current permissions
    roles = db.get_all_roles()
    if not roles:
        st.warning("No role data found. Please contact support.")
        return

    st.info("💡 Changes here affect what users with each role can see and do. Permissions are saved immediately.")
    
    # Tabs for different permission categories
    tab1, tab2 = st.tabs(["📊 General Permissions", "🏗️ Rate Management Permissions"])
    
    with tab1:
        render_general_permissions(roles)
    
    with tab2:
        render_rate_permissions(roles)


def render_general_permissions(roles):
    """Render general system permissions"""
    
    for role_info in roles:
        role_name = role_info['role']
        perms = role_info['permissions']
        
        # Skip editing 'admin' if you want to lock it
        if role_name == 'admin' and st.session_state.get('user_role') != 'system_admin':
            st.warning(f"Role '{role_name}' permissions are locked for your account level.")
            continue
        
        with st.expander(f"📌 Role: **{role_name.replace('_', ' ').title()}**", expanded=False):
            # Prepare permission keys
            perm_keys = [
                'manage_users', 'manage_tenders', 'run_analysis',
                'view_reports', 'export_data', 'change_plans',
                'manage_team', 'delete_any'
            ]
            
            # Use columns to display checkboxes in a grid
            col_count = 4
            cols = st.columns(col_count)
            updated_perms = {}
            
            for i, key in enumerate(perm_keys):
                col = cols[i % col_count]
                current = perms.get(key, False)
                label = key.replace('_', ' ').title()
                with col:
                    new_val = st.checkbox(label, value=current, key=f"{role_name}_{key}")
                    updated_perms[key] = new_val
            
            # Save button for this role
            if st.button(f"💾 Save General Permissions for {role_name}", key=f"save_general_{role_name}"):
                # Merge with existing rate permissions
                current_perms = db.get_role_permissions(role_name)
                current_perms.update(updated_perms)
                success = db.update_role_permissions(role_name, current_perms)
                if success:
                    st.success(f"Permissions for {role_name} updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update permissions.")


def render_rate_permissions(roles):
    """Render rate management permissions"""
    
    st.markdown("#### 🏗️ Rate Management Permissions")
    st.caption("Control access to Zones, Chapters, Parents, Children, and Versions")
    
    for role_info in roles:
        role_name = role_info['role']
        perms = role_info['permissions']
        
        if role_name == 'admin' and st.session_state.get('user_role') != 'system_admin':
            continue
        
        with st.expander(f"📌 Role: **{role_name.replace('_', ' ').title()}**", expanded=False):
            # Rate management permission keys
            rate_perm_keys = [
                'view_rates', 'edit_rates', 'delete_rates',
                'manage_zones', 'manage_chapters', 'manage_parents',
                'manage_children', 'manage_versions'
            ]
            
            # Display in two columns
            col1, col2 = st.columns(2)
            updated_perms = {}
            
            # Column 1
            with col1:
                for key in rate_perm_keys[:4]:
                    current = perms.get(key, False)
                    label = key.replace('_', ' ').title()
                    new_val = st.checkbox(label, value=current, key=f"{role_name}_rate_{key}")
                    updated_perms[key] = new_val
            
            # Column 2
            with col2:
                for key in rate_perm_keys[4:]:
                    current = perms.get(key, False)
                    label = key.replace('_', ' ').title()
                    new_val = st.checkbox(label, value=current, key=f"{role_name}_rate_{key}")
                    updated_perms[key] = new_val
            
            # Save button
            if st.button(f"💾 Save Rate Permissions for {role_name}", key=f"save_rate_{role_name}"):
                current_perms = db.get_role_permissions(role_name)
                current_perms.update(updated_perms)
                success = db.update_role_permissions(role_name, current_perms)
                if success:
                    st.success(f"Rate permissions for {role_name} updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update permissions.")


def render_permission_matrix(roles):
    """Display permission matrix for quick reference"""
    with st.expander("📊 Permission Matrix (Read‑only)", expanded=False):
        matrix_data = []
        for role_info in roles:
            row = {'Role': role_info['role'].replace('_', ' ').title()}
            perms = role_info['permissions']
            
            # General permissions
            for key in ['manage_users', 'manage_tenders', 'run_analysis', 'view_reports', 'export_data']:
                row[key.replace('_', ' ').title()] = '✅' if perms.get(key, False) else '❌'
            
            # Rate permissions
            for key in ['view_rates', 'edit_rates', 'manage_parents', 'manage_children']:
                row[key.replace('_', ' ').title()] = '✅' if perms.get(key, False) else '❌'
            
            matrix_data.append(row)
        
        st.dataframe(matrix_data, use_container_width=True, hide_index=True)
