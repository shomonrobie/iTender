

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
def show():
    """Refactored Registration Page – Company & Individual flows with clear UX"""
    debug_print("📝 Rendering registration page")

    # Page header
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1>📝 Create New Account</h1>
            <p style="color: #555;">Choose the account type that fits you best</p>
        </div>
    """, unsafe_allow_html=True)

    # Two tabs: Company (requires approval) vs Individual (auto-approved)
    tab1, tab2 = st.tabs(["🏢 **Company Registration**", "👤 **Individual Registration**"])

    # ========================= COMPANY REGISTRATION =========================
    with tab1:
        st.markdown("### 🏢 Register as a Company")
        st.caption("For construction companies, contractors, and organisations (requires admin approval)")

        with st.form("company_register_form", clear_on_submit=True):
            # --- Company Information ---
            st.markdown("#### 📌 Company Information")
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("Company Name *", placeholder="e.g., ABC Construction Ltd.")
                company_email = st.text_input("Company Email *", placeholder="info@company.com")
            with col2:
                company_phone = st.text_input("Company Phone *", placeholder="+880 1XXX XXXXXX")
                division = st.selectbox(
                    "Division / Region *",
                    ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
                )

            st.markdown("#### 👤 Admin Account Details")
            col3, col4 = st.columns(2)
            with col3:
                full_name = st.text_input("Full Name (Admin) *", placeholder="John Doe")
                username = st.text_input("Username *", placeholder="johndoe")
            with col4:
                email = st.text_input("Admin Email *", placeholder="john@company.com")
                # No separate phone for admin – reuse company phone

            col5, col6 = st.columns(2)
            with col5:
                password = st.text_input("Password *", type="password", placeholder="••••••••")
            with col6:
                confirm_password = st.text_input("Confirm Password *", type="password", placeholder="••••••••")

            # Password strength meter
            if password:
                score, message, color = validate_password_strength(password)
                st.progress(score / 100, text=f"Strength: {score}%")
                st.markdown(f"<span style='color:{color};'>{message}</span>", unsafe_allow_html=True)

            terms = st.checkbox("I agree to the **Terms of Service** and **Privacy Policy** *", key="comp_reg_terms")

            submitted = st.form_submit_button("🚀 Submit Company Registration", type="primary", use_container_width=True)

            if submitted:
                # Validation
                errors = []
                if not all([company_name, company_email, full_name, email, username, password, division]):
                    errors.append("All fields marked * are required.")
                if password != confirm_password:
                    errors.append("Passwords do not match.")
                if len(password) < 8:
                    errors.append("Password must be at least 8 characters.")
                if score < 60:
                    errors.append("Password is too weak. Please choose a stronger password.")
                if not terms:
                    errors.append("You must accept the Terms of Service.")

                if errors:
                    for err in errors:
                        st.error(f"❌ {err}")
                else:
                    try:
                        # Create company first
                        company_data = {
                            'company_name': company_name.strip(),
                            'email': company_email.strip(),
                            'phone': company_phone.strip(),
                            'division': division
                        }
                        success, result = db.create_company(company_data)
                        if success:
                            company_id = result
                            # Then create admin user
                            user_data = {
                                'username': username.strip(),
                                'password': password,
                                'email': email.strip(),
                                'full_name': full_name.strip(),
                                'phone': company_phone.strip(),
                                'role': 'company_admin',
                                'account_type': 'company',
                                'is_approved': False
                            }
                            user_success, user_result = db.create_user(company_id, user_data, None)
                            if user_success:
                                st.success("✅ Company registration submitted successfully!")
                                st.info("📧 Your account is under review. You will receive an email once approved (usually within 24‑48 hours).")
                                st.balloons()
                                navigate_to("login")
                            else:
                                st.error(f"❌ User creation failed: {user_result}")
                        else:
                            st.error(f"❌ Company creation failed: {result}")
                    except Exception as e:
                        logger.error("Company registration error", exc_info=True)
                        st.error("❌ An unexpected error occurred. Please try again later.")

    # ========================= INDIVIDUAL REGISTRATION =========================
    with tab2:
        st.markdown("### 👤 Register as an Individual")
        st.caption("For freelancers, consultants, and sole proprietors (auto‑approved)")

        # Import and render the existing individual registration module
        from modules.individual_registration import render_individual_registration
        render_individual_registration()

    # ========================= SIDEBAR – Helpful info =========================
    with st.sidebar:
        st.markdown("### 📋 Registration Guidelines")
        st.markdown("""
        **🏢 Company Accounts**
        - Requires admin approval
        - Suitable for teams and organisations
        - Full platform access after approval

        **👤 Individual Accounts**
        - Faster activation (auto‑approved)
        - Ideal for freelancers & consultants
        - Email verification required
        """)
        st.info("💡 Already have an account?")
        if st.button("→ Login Instead", use_container_width=True):
            navigate_to("login")

    debug_print("✅ Registration page render complete")