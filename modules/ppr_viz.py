import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_ppr_compliance_viz(comparison: dict, tender_data: dict):
    """Interactive PPR 2025 Compliance Visualization"""
    st.markdown("### 📈 PPR 2025 Compliance Dashboard")
    
    adv = comparison.get('advanced', comparison.get('basic', {}))
    rec_bid = adv.get('optimal_bid', 0)
    slt_threshold = adv.get('slt_threshold', 0)
    nppi = adv.get('nppi_factor', 0)
    est = tender_data.get('official_estimate', 1)
    comp_bids = [cb['bid'] for cb in tender_data.get('competitor_bids', [])] if tender_data.get('competitor_bids') else []
    
    is_compliant = rec_bid >= slt_threshold
    status_color = "#10b981" if is_compliant else "#ef4444"
    status_label = "✅ PPR Compliant" if is_compliant else "⚠️ SLT Risk"
    
    # 1. Compliance Gauge
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=rec_bid,
        title={'text': "Recommended Bid vs SLT Threshold", 'font': {'size': 14}},
        delta={'reference': slt_threshold, 'relative': True, 'position': "top"},
        gauge={
            'axis': {'range': [slt_threshold*0.9, est], 'tickwidth': 1},
            'bar': {'color': status_color},
            'steps': [{'range': [0, slt_threshold], 'color': '#fee2e2'}, {'range': [slt_threshold, est], 'color': '#dcfce7'}],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': slt_threshold}
        }
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    # 2. Bid Distribution
    if comp_bids:
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Box(y=comp_bids, name='Competitor Bids', marker_color='#3b82f6'))
        fig_dist.add_trace(go.Box(y=[rec_bid], name='Our Recommended', marker_color=status_color))
        fig_dist.add_hline(y=slt_threshold, line_dash="dash", line_color="red", annotation_text="SLT Threshold")
        fig_dist.update_layout(title="Bid Distribution vs SLT Threshold", yaxis_title="Bid Amount (BDT)", height=300)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    # 3. Metrics Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("SLT Threshold", f"BDT {slt_threshold:,.3f}")
    col2.metric("Recommended Bid", f"BDT {rec_bid:,.3f}", 
                delta=f"{(rec_bid-slt_threshold)/slt_threshold*100:.1f}% above SLT" if is_compliant else "Below SLT", 
                delta_color="normal" if is_compliant else "inverse")
    col3.metric("NPPI Factor", f"{nppi:.3f}", help="National Public Procurement Price Index")
    col4.markdown(f"""
    <div style="background:{status_color}20; padding:10px; border-radius:8px; border:1px solid {status_color}; text-align:center;">
        <strong style="color:{status_color}; font-size:1.1em;">{status_label}</strong><br>
        <small>PPR 2025 Clause 49</small>
    </div>""", unsafe_allow_html=True)
    
    # 4. Calculation Breakdown
    with st.expander("🔍 View PPR 2025 Calculation Breakdown", expanded=False):
        st.markdown("`X̄ = 0.5(Avg Comp) + 0.2(Estimate) + 0.3(NPPI)` → `SLT = X̄ - Sd`")
        st.dataframe(pd.DataFrame({
            'Component': ['Avg Competitor', 'Official Estimate', 'NPPI Price', 'Weighted Avg (X̄)', 'Std Dev (Sd)', 'SLT Threshold'],
            'Value': [f"BDT {sum(comp_bids)/len(comp_bids):,.3f}" if comp_bids else "N/A", f"BDT {est:,.3f}", 
                      f"BDT {est*nppi:,.3f}", f"BDT {adv.get('weighted_average', 0):,.3f}", 
                      f"{adv.get('weighted_std_dev', 0):.3f}", f"BDT {slt_threshold:,.3f}"]
        }), hide_index=True, use_container_width=True)