import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager

db = DatabaseManager()

def show():
    """Admin dashboard page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👑 Admin Dashboard</h1>
        <p>System-wide administration and monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get all users
    all_users = db.get_all_users()
    all_subs = db.get_all_subscriptions()
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", len(all_users))
    
    with col2:
        active_users = len([u for u in all_users if u[6] == 1])
        st.metric("Active Users", active_users)
    
    with col3:
        companies = set([u[9] for u in all_users]) if all_users else set()
        st.metric("Companies", len(companies))
    
    with col4:
        paid_subs = len([s for s in all_subs if s[2] not in ['free', 'trial']]) if all_subs else 0
        st.metric("Paid Subscriptions", paid_subs)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "👥 All Users", "💳 Subscriptions", "📊 System Stats"])
    
    with tab1:
        st.markdown("### System Overview")
        
        # User growth chart (mock data)
        user_growth = pd.DataFrame({
            'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'Users': [50, 75, 110, 150, 200, 250]
        })
        st.line_chart(user_growth.set_index('Month'))
        
        # Plan distribution
        if all_subs:
            plan_counts = {}
            for sub in all_subs:
                plan = sub[2] if len(sub) > 2 else 'free'
                plan_counts[plan] = plan_counts.get(plan, 0) + 1
            
            plan_df = pd.DataFrame(plan_counts.items(), columns=['Plan', 'Count'])
            st.bar_chart(plan_df.set_index('Plan'))
    
    with tab2:
        st.markdown("### All Users")
        
        if all_users:
            user_df = pd.DataFrame(all_users, 
                                  columns=['ID', 'Username', 'Email', 'Full Name', 'Phone', 'Role', 'Active', 'Created', 'Last Login', 'Company'])
            st.dataframe(user_df[['Username', 'Full Name', 'Email', 'Role', 'Active', 'Company']], 
                        use_container_width=True, hide_index=True)
        else:
            st.info("No users found")
    
    with tab3:
        st.markdown("### All Subscriptions")
        
        if all_subs:
            sub_df = pd.DataFrame(all_subs,
                                 columns=['ID', 'User ID', 'Plan', 'Status', 'Start', 'End', 
                                         'Analyses Used', 'Limit', 'Payment Method', 'Transaction', 'Updated', 
                                         'Username', 'Email', 'Full Name', 'Company'])
            st.dataframe(sub_df[['Company', 'Username', 'Full Name', 'Plan', 'Status', 'Analyses Used', 'Limit']], 
                        use_container_width=True, hide_index=True)
        else:
            st.info("No subscriptions found")
    
    with tab4:
        st.markdown("### System Statistics")
        
        # Get all analyses count
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tender_analyses")
        total_analyses = cursor.fetchone()[0]
        conn.close()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Analyses Performed", total_analyses)
        with col2:
            st.metric("Average Analyses per User", round(total_analyses / max(len(all_users), 1), 1))