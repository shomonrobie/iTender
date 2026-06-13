# _pages/extension_admin.py - COMPLETE FIXED VERSION

import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from database.enhanced_db_manager import enhanced_db

# Use the main database connection
db = DatabaseManager()

def show():
    """Extension Admin Dashboard - Manage extension usage and settings"""
    
    if st.session_state.user_role not in ['admin', 'system_admin']:
        st.error("🔒 Access denied. Admin privileges required.")
        return
    
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Extension Administration</h1>
        <p>Manage Chrome extension settings, view usage analytics, and configure limits</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Usage Analytics",
        "⚙️ Plan Configuration",
        "📋 Company Limits",
        "📈 Activity Log"
    ])
    
    with tab1:
        render_usage_analytics()
    
    with tab2:
        render_plan_configuration()
    
    with tab3:
        render_company_limits()
    
    with tab4:
        render_activity_log()


def render_usage_analytics():
    """Render extension usage analytics"""
    st.markdown("### Extension Usage Analytics")
    
    # Use the main database connection
    conn = db.get_connection()
    
    # Check if extension_auto_fill_log table exists
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='extension_auto_fill_log'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        st.info("No extension usage data yet. The extension will start tracking once installed and used.")
        conn.close()
        return
    
    # Overall stats
    try:
        df = pd.read_sql_query("""
            SELECT 
                COUNT(*) as total_fills,
                COUNT(DISTINCT company_id) as active_companies,
                COUNT(DISTINCT user_id) as active_users,
                AVG(confidence_score) as avg_confidence
            FROM extension_auto_fill_log
            WHERE filled_at >= date('now', '-30 days')
        """, conn)
        
        if not df.empty and df['total_fills'].iloc[0] > 0:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Auto-Fills", df['total_fills'].iloc[0])
            with col2:
                st.metric("Active Companies", df['active_companies'].iloc[0])
            with col3:
                st.metric("Active Users", df['active_users'].iloc[0])
            with col4:
                avg_conf = df['avg_confidence'].iloc[0]
                st.metric("Avg Confidence", f"{avg_conf * 100:.1f}%" if avg_conf else "N/A")
    except Exception as e:
        st.warning(f"Could not load stats: {e}")
    
    # Daily trend
    try:
        daily_trend = pd.read_sql_query("""
            SELECT 
                date(filled_at) as date,
                COUNT(*) as fills
            FROM extension_auto_fill_log
            WHERE filled_at >= date('now', '-30 days')
            GROUP BY date(filled_at)
            ORDER BY date
        """, conn)
        
        if not daily_trend.empty:
            st.markdown("#### Daily Usage Trend")
            st.line_chart(daily_trend.set_index('date'))
    except Exception as e:
        pass
    
    conn.close()


def render_plan_configuration():
    """Configure extension limits per plan"""
    st.markdown("### Plan Configuration")
    
    st.info("Configure how many auto-fills each subscription plan gets per month")
    
    # Get current limits from subscription_plans table
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check if subscription_plans table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subscription_plans'")
    if cursor.fetchone():
        cursor.execute("SELECT plan_name, extension_auto_fills FROM subscription_plans")
        plans_data = cursor.fetchall()
        plan_limits = {plan: limit for plan, limit in plans_data}
    else:
        # Default limits
        plan_limits = {
            'free': 5,
            'basic': 30,
            'professional': 100,
            'enterprise': -1
        }
    
    conn.close()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Current Limits")
        for plan, limit in plan_limits.items():
            limit_display = "Unlimited" if limit == -1 else str(limit)
            st.metric(plan.capitalize(), limit_display)
    
    with col2:
        st.markdown("#### Update Limits")
        
        new_free = st.number_input("Free Plan Limit", min_value=0, max_value=50, value=plan_limits.get('free', 5))
        new_basic = st.number_input("Basic Plan Limit", min_value=0, max_value=200, value=plan_limits.get('basic', 30))
        new_professional = st.number_input("Professional Plan Limit", min_value=0, max_value=500, value=plan_limits.get('professional', 100))
        unlimited_enterprise = st.checkbox("Enterprise Unlimited", value=plan_limits.get('enterprise', -1) == -1)
        new_enterprise = -1 if unlimited_enterprise else st.number_input("Enterprise Limit", min_value=0, max_value=1000, value=100)
        
        if st.button("💾 Save Plan Limits", type="primary"):
            # Update in database
            conn = db.get_connection()
            cursor = conn.cursor()
            
            try:
                # Update subscription_plans table
                cursor.execute("UPDATE subscription_plans SET extension_auto_fills = ? WHERE plan_name = 'free'", (new_free,))
                cursor.execute("UPDATE subscription_plans SET extension_auto_fills = ? WHERE plan_name = 'basic'", (new_basic,))
                cursor.execute("UPDATE subscription_plans SET extension_auto_fills = ? WHERE plan_name = 'professional'", (new_professional,))
                cursor.execute("UPDATE subscription_plans SET extension_auto_fills = ? WHERE plan_name = 'enterprise'", (new_enterprise,))
                conn.commit()
                st.success("Plan limits updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update: {e}")
            finally:
                conn.close()


def render_company_limits():
    """Manage per-company extension limits"""
    st.markdown("### Company-Specific Limits")
    
    # Use the main database connection
    conn = db.get_connection()
    
    # Check if companies table exists
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
    if not cursor.fetchone():
        st.error("Companies table not found. Please check database connection.")
        conn.close()
        return
    
    search = st.text_input("Search Company", placeholder="Enter company name...")
    
    try:
        query = """
            SELECT id, company_name
            FROM companies
            WHERE is_active = 1
        """
        params = []
        
        if search:
            query += " AND company_name LIKE ?"
            params.append(f"%{search}%")
        
        query += " ORDER BY company_name LIMIT 50"
        
        companies = pd.read_sql_query(query, conn, params=params if search else None)
        
        if not companies.empty:
            st.markdown("#### Companies")
            
            for _, company in companies.iterrows():
                with st.expander(f"🏢 {company['company_name']}"):
                    # Get current usage
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) FROM extension_auto_fill_log 
                        WHERE company_id = ? AND filled_at >= date('now', 'start of month')
                    """, (company['id'],))
                    used_this_month = cursor.fetchone()[0] or 0
                    
                    st.write(f"**Used this month:** {used_this_month}")
                    
                    custom_limit = st.number_input(
                        "Custom monthly limit (-1 for unlimited)", 
                        min_value=-1, 
                        max_value=1000,
                        value=5,
                        key=f"limit_{company['id']}"
                    )
                    
                    if st.button(f"Apply Limit", key=f"apply_{company['id']}"):
                        st.success(f"Limit set to {custom_limit if custom_limit != -1 else 'Unlimited'} for {company['company_name']}")
        else:
            st.info("No companies found")
            
    except Exception as e:
        st.error(f"Error loading companies: {e}")
        import traceback
        st.code(traceback.format_exc())
    finally:
        conn.close()


def render_activity_log():
    """Render detailed activity log"""
    st.markdown("### Extension Activity Log")
    
    # Use the main database connection
    conn = db.get_connection()
    
    # Check if extension_auto_fill_log table exists
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='extension_auto_fill_log'")
    if not cursor.fetchone():
        st.info("No extension activity logged yet.")
        conn.close()
        return
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        date_filter = st.date_input("Date Range Start", value=pd.Timestamp.now().replace(day=1))
    
    with col2:
        company_filter = st.text_input("Company Name (optional)")
    
    try:
        if company_filter:
            # Get company ID first
            cursor.execute("SELECT id FROM companies WHERE company_name LIKE ?", (f"%{company_filter}%",))
            company_ids = [row[0] for row in cursor.fetchall()]
            
            if company_ids:
                placeholders = ','.join(['?'] * len(company_ids))
                query = f"""
                    SELECT 
                        e.filled_at,
                        e.company_id,
                        e.user_id,
                        e.field_label,
                        e.confidence_score,
                        e.page_url
                    FROM extension_auto_fill_log e
                    WHERE e.filled_at >= ? AND e.company_id IN ({placeholders})
                    ORDER BY e.filled_at DESC LIMIT 200
                """
                params = [date_filter.strftime('%Y-%m-%d')] + company_ids
            else:
                query = """
                    SELECT 
                        e.filled_at,
                        e.company_id,
                        e.user_id,
                        e.field_label,
                        e.confidence_score,
                        e.page_url
                    FROM extension_auto_fill_log e
                    WHERE e.filled_at >= ?
                    ORDER BY e.filled_at DESC LIMIT 200
                """
                params = [date_filter.strftime('%Y-%m-%d')]
        else:
            query = """
                SELECT 
                    e.filled_at,
                    e.company_id,
                    e.user_id,
                    e.field_label,
                    e.confidence_score,
                    e.page_url
                FROM extension_auto_fill_log e
                WHERE e.filled_at >= ?
                ORDER BY e.filled_at DESC LIMIT 200
            """
            params = [date_filter.strftime('%Y-%m-%d')]
        
        logs = pd.read_sql_query(query, conn, params=params)
        
        if not logs.empty:
            logs['filled_at'] = pd.to_datetime(logs['filled_at']).dt.strftime('%Y-%m-%d %H:%M')
            logs['confidence_score'] = logs['confidence_score'].apply(lambda x: f"{x*100:.0f}%" if x else "N/A")
            
            # Get company names
            company_ids = logs['company_id'].unique()
            if len(company_ids) > 0:
                placeholders = ','.join(['?'] * len(company_ids))
                companies_df = pd.read_sql_query(f"SELECT id, company_name FROM companies WHERE id IN ({placeholders})", 
                                                  conn, params=list(company_ids))
                company_names = dict(zip(companies_df['id'], companies_df['company_name']))
                logs['company_name'] = logs['company_id'].map(company_names)
            
            st.dataframe(logs[['filled_at', 'company_name', 'user_id', 'field_label', 'confidence_score']], 
                        use_container_width=True, hide_index=True)
            
            # Download option
            csv = logs.to_csv(index=False)
            st.download_button(
                "📥 Download Logs (CSV)",
                csv,
                f"extension_logs_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
        else:
            st.info("No activity logs found for the selected period")
            
    except Exception as e:
        st.error(f"Error loading activity log: {e}")
    finally:
        conn.close()