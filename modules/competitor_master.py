"""
Competitor Master Management
Maintain a master list of all competitors for reuse across tenders
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

def render_competitor_master_page():
    """Render competitor master management page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📋 Competitor Master Database</h1>
        <p>Manage your competitor list for reuse across tenders</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check premium access
    subscription = db.get_user_subscription(st.session_state.user_id)
    is_premium = subscription.get('plan') in ['professional', 'enterprise'] or st.session_state.user_role == 'admin'
    
    if not is_premium:
        st.warning("⚠️ Competitor tracking is available for Professional and Enterprise plans only.")
        return
    
    tabs = st.tabs(["📋 Competitor List", "➕ Add New Competitor", "📊 Competitor Analytics"])
    
    with tabs[0]:
        render_competitor_list()
    
    with tabs[1]:
        render_add_competitor_form()
    
    with tabs[2]:
        render_competitor_analytics()

def render_competitor_list():
    """Display and manage competitor list"""
    
    st.markdown("### Competitor Directory")
    
    # Search and filter
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("🔍 Search Competitor", placeholder="Enter competitor name...")
    with col2:
        show_inactive = st.checkbox("Show Inactive Competitors")
    
    competitors = db.get_competitor_master_list(st.session_state.company_id, active_only=not show_inactive)
    
    if not competitors:
        st.info("No competitors found. Add your first competitor using the form above.")
        return
    
    # Convert to DataFrame for display
    comp_df = pd.DataFrame(competitors, 
                          columns=['ID', 'Name', 'Business Type', 'Total Bids', 'Total Wins',
                                   'Avg Bid Ratio', 'Strategy', 'Last Seen', 'Active'])
    
    # Filter by search
    if search:
        comp_df = comp_df[comp_df['Name'].str.contains(search, case=False)]
    
    # Calculate win rate
    comp_df['Win Rate'] = comp_df.apply(lambda x: f"{x['Total Wins']/x['Total Bids']*100:.0f}%" if x['Total Bids'] > 0 else "0%", axis=1)
    comp_df['Avg Bid Ratio'] = comp_df['Avg Bid Ratio'].apply(lambda x: f"{x*100:.1f}%" if x else "N/A")
    
    # Display
    st.dataframe(comp_df[['Name', 'Business Type', 'Total Bids', 'Win Rate', 'Avg Bid Ratio', 'Strategy', 'Last Seen']], 
                use_container_width=True, hide_index=True)
    
    # Competitor details expander
    st.markdown("---")
    st.markdown("### 🔍 Competitor Details")
    
    selected_comp = st.selectbox("Select Competitor to View/Edit", comp_df['Name'].tolist())
    
    if selected_comp:
        comp_data = comp_df[comp_df['Name'] == selected_comp].iloc[0]
        comp_id = comp_data['ID']
        
        # Get full details
        full_details = db.get_competitor_by_id(comp_id)
        
        if full_details:
            with st.expander(f"Details for {selected_comp}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Business Type:** {full_details[3] if len(full_details) > 3 else 'N/A'}")
                    st.markdown(f"**Contact Person:** {full_details[4] if len(full_details) > 4 else 'N/A'}")
                    st.markdown(f"**Phone:** {full_details[5] if len(full_details) > 5 else 'N/A'}")
                    st.markdown(f"**Email:** {full_details[6] if len(full_details) > 6 else 'N/A'}")
                
                with col2:
                    st.markdown(f"**Total Bids:** {full_details[11] if len(full_details) > 11 else 0}")
                    st.markdown(f"**Total Wins:** {full_details[12] if len(full_details) > 12 else 0}")
                    st.markdown(f"**Win Rate:** {(full_details[12]/full_details[11]*100 if full_details[11] > 0 else 0):.0f}%")
                    st.markdown(f"**Preferred Strategy:** {full_details[14] if len(full_details) > 14 else 'Unknown'}")
                
                st.markdown(f"**Notes:** {full_details[9] if len(full_details) > 9 else 'No notes'}")
                
                # Edit option
                if st.button("✏️ Edit Competitor", key=f"edit_{comp_id}"):
                    st.session_state.edit_competitor = full_details
                    st.rerun()

def render_add_competitor_form():
    """Form to add new competitor to master list"""
    
    st.markdown("### Add New Competitor")
    st.caption("Add competitors once, then select from dropdown when recording historical tenders")
    
    with st.form("add_competitor_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            competitor_name = st.text_input("Competitor Name*")
            business_type = st.selectbox("Business Type", ["Construction Company", "Trading Company", "Joint Venture", "Individual", "Other"])
            contact_person = st.text_input("Contact Person")
            phone = st.text_input("Phone Number")
        
        with col2:
            email = st.text_input("Email Address")
            address = st.text_area("Address", height=68)
            preferred_strategy = st.selectbox("Observed Strategy", ["Aggressive", "Moderate", "Conservative", "Variable", "Unknown"])
            notes = st.text_area("Additional Notes", height=68)
        
        submitted = st.form_submit_button("💾 Add Competitor to Master List", use_container_width=True)
        
        if submitted:
            if not competitor_name:
                st.error("Competitor name is required")
            else:
                competitor_data = {
                    'competitor_name': competitor_name,
                    'business_type': business_type,
                    'contact_person': contact_person,
                    'phone': phone,
                    'email': email,
                    'address': address,
                    'notes': notes,
                    'preferred_strategy': preferred_strategy,
                    'bid_ratio': 0.90,  # Default placeholder
                    'was_winner': False
                }
                
                comp_id = db.add_competitor_to_master(st.session_state.company_id, competitor_data)

                st.success(f"✅ Competitor '{competitor_name}' added to master list!")
                st.balloons()

def render_competitor_analytics():
    """Display competitor analytics and insights"""
    
    st.markdown("### Competitor Analytics")
    
    competitors = db.get_competitor_master_list(st.session_state.company_id)
    
    if not competitors:
        st.info("No competitor data available. Add competitors and record historical tenders.")
        return
    
    comp_df = pd.DataFrame(competitors, 
                          columns=['ID', 'Name', 'Business Type', 'Total Bids', 'Total Wins',
                                   'Avg Bid Ratio', 'Strategy', 'Last Seen', 'Active'])
    
    # Calculate metrics
    comp_df['Win Rate'] = comp_df.apply(lambda x: x['Total Wins'] / x['Total Bids'] if x['Total Bids'] > 0 else 0, axis=1)
    
    # Top competitors by frequency
    st.markdown("#### Most Frequent Competitors")
    top_frequent = comp_df.nlargest(10, 'Total Bids')[['Name', 'Total Bids', 'Win Rate', 'Avg Bid Ratio']]
    top_frequent['Win Rate'] = top_frequent['Win Rate'].apply(lambda x: f"{x*100:.0f}%")
    top_frequent['Avg Bid Ratio'] = top_frequent['Avg Bid Ratio'].apply(lambda x: f"{x*100:.1f}%")
    st.dataframe(top_frequent, use_container_width=True, hide_index=True)
    
    # Most successful competitors
    st.markdown("#### Most Successful Competitors (Highest Win Rate)")
    top_winners = comp_df[comp_df['Total Bids'] >= 2].nlargest(10, 'Win Rate')[['Name', 'Total Bids', 'Win Rate', 'Avg Bid Ratio']]
    if len(top_winners) > 0:
        top_winners['Win Rate'] = top_winners['Win Rate'].apply(lambda x: f"{x*100:.0f}%")
        top_winners['Avg Bid Ratio'] = top_winners['Avg Bid Ratio'].apply(lambda x: f"{x*100:.1f}%")
        st.dataframe(top_winners, use_container_width=True, hide_index=True)
    else:
        st.info("Insufficient data for win rate analysis")
    
    # Strategy distribution
    st.markdown("#### Strategy Distribution")
    strategy_counts = comp_df['Strategy'].value_counts()
    if len(strategy_counts) > 0:
        fig = px.pie(values=strategy_counts.values, names=strategy_counts.index, title="Competitor Strategy Breakdown")
        st.plotly_chart(fig, use_container_width=True)
    
    # Market aggression index
    avg_aggression = comp_df['Avg Bid Ratio'].mean()
    st.markdown(f"#### Market Insights")
    if avg_aggression < 0.89:
        st.warning(f"📊 **Aggressive Market** - Average bid ratio: {avg_aggression*100:.1f}% (Highly competitive)")
    elif avg_aggression < 0.93:
        st.info(f"📊 **Moderate Market** - Average bid ratio: {avg_aggression*100:.1f}% (Balanced competition)")
    else:
        st.success(f"📊 **Conservative Market** - Average bid ratio: {avg_aggression*100:.1f}% (Room for better margins)")