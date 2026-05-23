"""
Analysis History Module - Enhanced with Row Buttons & Detailed Reports
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import traceback
import sqlite3
from utils.helpers import format_currency_bd, format_percentage, get_compact_css, get_bid_status_badge, get_risk_indicator
from utils.helpers import (
    get_compact_css,
    format_currency_bd,
    format_percentage,
    get_bid_status_badge,
    get_risk_indicator,
    render_page_header
)

# Page config for better display
st.set_page_config(layout="wide")

   
def show_analysis_history():
    """Tender analysis history page with row buttons and detailed reports"""
    
    st.markdown(get_compact_css(), unsafe_allow_html=True)

    # Page Header
    # Use the centralized page header
    render_page_header(
        " Tender History", 
        "View detailed analysis reports",
        icon="📜"
    )


    
    # Get current user's company ID
    company_id = st.session_state.get('company_id')
    
    if not company_id:
        st.error("⚠️ Company information not found. Please log in again.")
        return
    
    # Direct database connection
    db_path = r"D:\itender\data\tender_system.db"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all analyses for this company
        query = """
        SELECT 
            ta.id,
            ta.tender_id,
            ta.tender_title,
            ta.procuring_entity,
            ta.analysis_type,
            ta.recommended_bid,
            ta.confidence_score,
            ta.success_probability,
            ta.risk_level,
            ta.bid_status,
            ta.analysis_date,
            ta.is_final_submitted,
            ta.official_estimate,
            ta.competitor_count,
            ta.risk_strategy,
            ta.slt_threshold,
            ta.nppi_factor,
            ta.weighted_average,
            ta.division,
            ta.district,
            ta.thana,
            ta.construction_type,
            ta.competitor_bids,
            ta.expected_profit,
            ta.expected_value,
            ta.final_submitted_bid
        FROM tender_analyses ta
        WHERE ta.company_id = ?
        ORDER BY ta.analysis_date DESC
        """
        
        cursor.execute(query, (company_id,))
        rows = cursor.fetchall()
        
        if not rows:
            st.info("📭 No analyses saved yet. Run your first analysis in **Three-Tier Bid Optimization**!")
            conn.close()
            return
        
        # Convert to list of dicts
        analyses = []
        for row in rows:
            analyses.append(dict(row))
        
        # =========================================================================
        # FILTERS SECTION
        # =========================================================================
        with st.expander("🔍 Filters", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                search_term = st.text_input("Search", placeholder="ID or title", key="search_input")
            
            with col2:
                statuses = list(set([a.get('bid_status', 'draft') for a in analyses]))
                status_filter = st.selectbox("Status", ["All"] + statuses, key="status_filter")
            
            with col3:
                analysis_types = list(set([a.get('analysis_type', 'BASIC') for a in analyses]))
                type_filter = st.selectbox("Analysis Type", ["All"] + analysis_types, key="type_filter")
            
            with col4:
                risk_levels = list(set([a.get('risk_level', 'Medium') for a in analyses if a.get('risk_level')]))
                risk_filter = st.selectbox("Risk Level", ["All"] + risk_levels, key="risk_filter")
        
        # Apply filters
        filtered_analyses = analyses.copy()
        
        if search_term:
            search_lower = search_term.lower()
            filtered_analyses = [
                a for a in filtered_analyses 
                if search_lower in str(a.get('tender_id', '')).lower() 
                or search_lower in str(a.get('tender_title', '')).lower()
            ]
        
        if status_filter != "All":
            filtered_analyses = [a for a in filtered_analyses if a.get('bid_status') == status_filter]
        
        if type_filter != "All":
            filtered_analyses = [a for a in filtered_analyses if a.get('analysis_type') == type_filter]
        
        if risk_filter != "All":
            filtered_analyses = [a for a in filtered_analyses if a.get('risk_level') == risk_filter]
        
        st.markdown(f"<p class='small-text'>📊 Showing <b>{len(filtered_analyses)}</b> of <b>{len(analyses)}</b> analyses</p>", unsafe_allow_html=True)
        
        # =============================================================================
        # PAGINATION SETUP
        # =============================================================================
        # Initialize pagination state
        if 'history_page_num' not in st.session_state:
            st.session_state.history_page_num = 1

        # Pagination settings
        items_per_page = 10
        total_items = len(filtered_analyses)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

        # Ensure current page is valid
        if st.session_state.history_page_num > total_pages:
            st.session_state.history_page_num = total_pages

        # Calculate slice indices
        start_idx = (st.session_state.history_page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)

        # Get current page items
        current_page_items = filtered_analyses[start_idx:end_idx]

        # Display pagination controls
        if total_pages > 1:
            col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
            
            with col1:
                if st.button("◀◀ First", use_container_width=True, disabled=(st.session_state.history_page_num == 1)):
                    st.session_state.history_page_num = 1
                    st.rerun()
            
            with col2:
                if st.button("◀ Previous", use_container_width=True, disabled=(st.session_state.history_page_num == 1)):
                    st.session_state.history_page_num -= 1
                    st.rerun()
            
            with col3:
                st.markdown(f"<div style='text-align: center; font-size:0.8rem;'>Page {st.session_state.history_page_num} of {total_pages}</div>", unsafe_allow_html=True)
            
            with col4:
                if st.button("Next ▶", use_container_width=True, disabled=(st.session_state.history_page_num == total_pages)):
                    st.session_state.history_page_num += 1
                    st.rerun()
            
            with col5:
                if st.button("Last ▶▶", use_container_width=True, disabled=(st.session_state.history_page_num == total_pages)):
                    st.session_state.history_page_num = total_pages
                    st.rerun()
            
            st.markdown("---")

        # Display info text
        st.markdown(f"<span style='font-size:0.7rem; color:#666;'>Showing {start_idx + 1}-{end_idx} of {total_items} analyses</span>", unsafe_allow_html=True)
        st.markdown("---")

        # =========================================================================
        # MAIN TABLE WITH BUTTONS
        # =========================================================================
        st.markdown("---")
        
        if not filtered_analyses:
            st.warning("No analyses match your filters")
            conn.close()
            return
        
        # Initialize session state for selected analysis
        if 'selected_analysis_id' not in st.session_state:
            st.session_state.selected_analysis_id = None
        
        header_cols = st.columns([2, 3.5, 2, 1, 1, 1, 0.8])
        headers = ["Tender ID", "Title", "Bid Amount", "Win %", "Risk", "Status", ""]
    
        for col, header in zip(header_cols, headers):
            with col:
                st.markdown(f"**<span style='font-size:0.75rem;'>{header}</span>**", unsafe_allow_html=True)
    
        st.markdown("---")
        # Display table with buttons
        for idx, analysis in enumerate(current_page_items):
            # Use columns with minimal width
            with st.container():
                cols = st.columns([2, 3.5, 2, 1, 1, 1, 0.8])
                
                with cols[0]:
                    st.markdown(f"<span style='font-size:0.75rem; font-weight:bold;'>{analysis.get('tender_id', 'N/A')[:20]}</span>", unsafe_allow_html=True)
                
                with cols[1]:
                    title = str(analysis.get('tender_title', 'Untitled'))[:40]
                    st.markdown(f"<span style='font-size:0.75rem;'>{title}</span>", unsafe_allow_html=True)
                
                with cols[2]:
                    bid = analysis.get('recommended_bid', 0)
                    st.markdown(f"<span style='font-size:0.75rem;'>{format_currency_bd(bid, 3)}</span>", unsafe_allow_html=True)
                
                with cols[3]:
                    win_prob = analysis.get('success_probability', 0)
                    if win_prob:
                        win_pct = win_prob * 100 if win_prob <= 1 else win_prob
                        st.markdown(f"<span style='font-size:0.75rem;'>{win_pct:.0f}%</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='font-size:0.75rem;'>N/A</span>", unsafe_allow_html=True)
                
                with cols[4]:
                    risk = analysis.get('risk_level', 'Unknown')
                    risk_display = get_risk_indicator(risk)
                    st.markdown(f"<span style='font-size:0.75rem;'>{risk_display}</span>", unsafe_allow_html=True)
                
                with cols[5]:
                    status = analysis.get('bid_status', 'draft')
                    badge = get_bid_status_badge(status)
                    st.markdown(f"<span style='font-size:0.75rem;'>{badge} {status.title()}</span>", unsafe_allow_html=True)
                
                with cols[6]:
                    button_key = f"view_{analysis.get('id')}_{idx}"
                    if st.button("📄", key=button_key, help="View details", use_container_width=True):
                        if st.session_state.selected_analysis_id == analysis.get('id'):
                            st.session_state.selected_analysis_id = None
                        else:
                            st.session_state.selected_analysis_id = analysis.get('id')
                        st.rerun()
                
                # Minimal separator
                st.markdown("---")


        
        # =========================================================================
        # DETAILED REPORT SECTION
        # =========================================================================
        if st.session_state.selected_analysis_id:
            # Find the selected analysis
            selected = next((a for a in filtered_analyses if a.get('id') == st.session_state.selected_analysis_id), None)
            
            if selected:
                st.markdown("### 📋 Detailed Analysis Report")
                st.markdown(f"**Tender ID:** {selected.get('tender_id', 'N/A')}")
                st.markdown(f"**Title:** {selected.get('tender_title', 'N/A')}")
                
                # Create tabs for different sections
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📊 Bid Analysis", "📈 PPR Metrics", "🏢 Competitors", 
                    "💰 Financials", "📍 Location & Meta"
                ])
                
                with tab1:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Official Estimate", f"BDT {selected.get('official_estimate', 0):,.2f}")
                        st.metric("Recommended Bid", f"BDT {selected.get('recommended_bid', 0):,.2f}")
                        
                        # Calculate bid ratio
                        est = selected.get('official_estimate', 1)
                        rec = selected.get('recommended_bid', 0)
                        ratio = (rec / est * 100) if est > 0 else 0
                        st.metric("Bid Ratio", f"{ratio:.1f}% of estimate")
                    
                    with col2:
                        st.metric("Win Probability", f"{selected.get('success_probability', 0)*100:.0f}%" if selected.get('success_probability') else "N/A")
                        st.metric("Confidence Score", f"{selected.get('confidence_score', 0)*100:.0f}%" if selected.get('confidence_score') else "N/A")
                        st.metric("Analysis Type", selected.get('analysis_type', 'N/A'))
                    
                    with col3:
                        st.metric("Risk Level", selected.get('risk_level', 'N/A'))
                        st.metric("Risk Strategy", selected.get('risk_strategy', 'N/A'))
                        st.metric("Bid Status", selected.get('bid_status', 'draft').title())
                        
                        if selected.get('final_submitted_bid'):
                            st.metric("Final Submitted Bid", f"BDT {selected['final_submitted_bid']:,.2f}")
                
                with tab2:
                    col1, col2 = st.columns(2)
                    
                    st.markdown("#### PPR 2025 Compliance Metrics")
    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # SLT Threshold
                        slt = selected.get('slt_threshold')
                        if slt and slt > 0:
                            st.metric("SLT Threshold", format_currency_bd(slt, 3))
                            st.caption("Clause 49.2 - Significantly Low-priced Tender")
                            
                            # Check compliance
                            rec_bid = selected.get('recommended_bid', 0)
                            if rec_bid >= slt:
                                st.success("✅ Bid above SLT threshold")
                            else:
                                st.warning("⚠️ Bid below SLT threshold - may be rejected")
                        else:
                            st.info("📊 SLT calculation requires Advanced/Enhanced analysis")
                            st.caption("Run Advanced or Enhanced analysis with competitor data")
                        
                        # Weighted Average
                        w_avg = selected.get('weighted_average')
                        if w_avg and w_avg > 0:
                            st.metric("Weighted Average (X̄)", format_currency_bd(w_avg, 3))
                            st.caption("PPR 2025 formula: 0.5×AvgComp + 0.2×Est + 0.3×NPPI")
                    
                    with col2:
                        # NPPI Factor
                        nppi = selected.get('nppi_factor')
                        if nppi and nppi > 0:
                            st.metric("NPPI Factor", f"{nppi:.3f}")
                            st.caption("Clause 49.4-49.5 - Normalized PPI")
                            
                            # Interpretation
                            if nppi < 0.95:
                                st.info("📉 Below market average - favorable")
                            elif nppi > 1.05:
                                st.warning("📈 Above market average - conservative")
                            else:
                                st.success("✅ At market average")
                        else:
                            st.info("📊 NPPI requires historical tender data")
                            st.caption("Add historical tender results to enable NPPI")
                        
                        # Competition intensity
                        comp_count = selected.get('competitor_count', 0)
                        if comp_count > 0:
                            st.metric("Competitors", comp_count)
                            if comp_count <= 3:
                                st.info("🟢 Low competition")
                            elif comp_count <= 6:
                                st.warning("🟡 Medium competition")
                            else:
                                st.error("🔴 High competition")
                
                with tab3:
                    st.markdown("#### Competitor Analysis")
                    st.metric("Number of Competitors", selected.get('competitor_count', 0))
                    
                    # Parse and display competitor bids
                    comp_bids = selected.get('competitor_bids')
                    if comp_bids:
                        try:
                            if isinstance(comp_bids, str):
                                competitors = json.loads(comp_bids)
                            else:
                                competitors = comp_bids
                            
                            if isinstance(competitors, list) and competitors:
                                st.markdown("##### Competitor Bids")
                                comp_df = pd.DataFrame(competitors)
                                
                                # Add bid ranking
                                if 'bid' in comp_df.columns:
                                    comp_df['Rank'] = comp_df['bid'].rank().astype(int)
                                    comp_df = comp_df.sort_values('bid')
                                
                                st.dataframe(comp_df, hide_index=True, use_container_width=True)
                                
                                # Show our position
                                our_bid = selected.get('recommended_bid', 0)
                                if our_bid > 0:
                                    all_bids = [c.get('bid', 0) for c in competitors] + [our_bid]
                                    all_bids_sorted = sorted(all_bids)
                                    our_rank = all_bids_sorted.index(our_bid) + 1
                                    st.info(f"📊 Your bid would rank #{our_rank} out of {len(all_bids)} bidders")
                            else:
                                st.info("No competitor bid details available")
                        except Exception as e:
                            st.warning(f"Could not parse competitor data: {e}")
                    else:
                        st.info("No competitor data available for this analysis")
                
                with tab4:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Profitability Analysis")
                        est_cost = selected.get('official_estimate', 0) * 0.85  # Assume 85% cost
                        profit = selected.get('recommended_bid', 0) - est_cost
                        margin = (profit / selected.get('recommended_bid', 1)) * 100 if selected.get('recommended_bid') else 0
                        
                        st.metric("Estimated Cost", f"BDT {est_cost:,.2f}")
                        st.metric("Estimated Profit", f"BDT {profit:,.2f}", delta=f"{margin:.1f}% margin")
                        
                        exp_profit = selected.get('expected_profit')
                        if exp_profit:
                            st.metric("Expected Profit", f"BDT {exp_profit:,.2f}")
                        
                        exp_value = selected.get('expected_value')
                        if exp_value:
                            st.metric("Expected Value", f"BDT {exp_value:,.2f}")
                    
                    with col2:
                        st.markdown("#### Risk-Reward Assessment")
                        
                        # Create a simple risk meter
                        risk_level = selected.get('risk_level', 'Medium')
                        risk_scores = {'Low': 25, 'Medium': 50, 'High': 75}
                        risk_score = risk_scores.get(risk_level, 50)
                        
                        st.progress(risk_score / 100, text=f"Risk Score: {risk_score}%")
                        
                        # Recommendations based on risk
                        if risk_level == 'Low':
                            st.success("✅ Low risk - Safe bid with good chance of winning")
                        elif risk_level == 'Medium':
                            st.warning("⚖️ Moderate risk - Balanced approach recommended")
                        else:
                            st.error("⚠️ High risk - Consider revising bid or strategy")
                
                with tab5:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Location Information")
                        st.metric("Division", selected.get('division', 'N/A'))
                        st.metric("District", selected.get('district', 'N/A'))
                        st.metric("Thana/Upazila", selected.get('thana', 'N/A'))
                        st.metric("Construction Type", selected.get('construction_type', 'N/A'))
                    
                    with col2:
                        st.markdown("#### Analysis Metadata")
                        st.metric("Procuring Entity", selected.get('procuring_entity', 'N/A')[:50])
                        st.metric("Analysis Date", str(selected.get('analysis_date', 'N/A'))[:19])
                        st.metric("Final Submitted", "Yes" if selected.get('is_final_submitted') else "No")
                
                # Export options
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    report_text = f"""
                        TENDER ANALYSIS REPORT
                        ======================
                        Tender ID: {selected.get('tender_id', 'N/A')}
                        Title: {selected.get('tender_title', 'N/A')}
                        Procuring Entity: {selected.get('procuring_entity', 'N/A')}

                        BID METRICS (e-GP 3-decimal standard)
                        -----------
                        Official Estimate: {format_currency_bd(selected.get('official_estimate'), 3)}
                        Recommended Bid: {format_currency_bd(selected.get('recommended_bid'), 3)}
                        Bid Ratio: {(selected.get('recommended_bid', 0) / max(selected.get('official_estimate', 1), 1) * 100):.1f}%
                        Win Probability: {format_percentage(selected.get('success_probability'))}
                        Confidence Score: {format_percentage(selected.get('confidence_score'))}
                        Risk Level: {selected.get('risk_level', 'N/A')}

                        PPR 2025 COMPLIANCE
                        -------------------
                        SLT Threshold: {format_currency_bd(selected.get('slt_threshold'), 3) if selected.get('slt_threshold') else 'Not Available'}
                        NPPI Factor: {f"{selected.get('nppi_factor'):.3f}" if selected.get('nppi_factor') else 'Not Available'}
                        Weighted Average: {format_currency_bd(selected.get('weighted_average'), 3) if selected.get('weighted_average') else 'Not Available'}

                        Generated by TenderAI on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        """

                    st.download_button(
                        "📄 Export as TXT",
                        report_text,
                        f"report_{selected.get('tender_id', 'export')}.txt",
                        width='stretch'

                    )
                
                with col2:
                    # Export as JSON
                    export_data = {k: v for k, v in selected.items() if v is not None and k != 'competitor_bids'}
                    export_json = json.dumps(export_data, default=str, indent=2)
                    st.download_button(
                        "💾 Export as JSON",
                        export_json,
                        f"analysis_{selected.get('tender_id', 'export')}.json",
                        "application/json",
                        width='stretch'                    )
                
                with col3:
                    if st.button("❌ Close Report", width='stretch'):
                        st.session_state.selected_analysis_id = None
                        st.rerun()
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading analysis history: {str(e)}")
        print(f"ERROR: {e}")
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()