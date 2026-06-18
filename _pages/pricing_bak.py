import streamlit as st

PLANS = {
    'free': {'name': 'Free', 'price': 0, 'features': ['5 analyses/month', 'Basic reports', 'Email support']},
    'basic': {'name': 'Basic', 'price': 4999, 'features': ['30 analyses/month', 'AI predictions', 'Export reports', 'Email support']},
    'professional': {'name': 'Professional', 'price': 14999, 'features': ['Unlimited analyses', 'ML predictions', 'Team collaboration', 'Priority support']},
    'enterprise': {'name': 'Enterprise', 'price': 49999, 'features': ['Custom AI', 'Dedicated support', 'SLA guarantee', 'On-premise option']}
}

def show():
    st.markdown("""
    <div class="main-header">
        <h1>💰 Pricing Plans</h1>
        <p>Choose the plan that fits your business</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    for idx, (key, plan) in enumerate(PLANS.items()):
        with [col1, col2, col3, col4][idx]:
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 10px; 
                        border: 2px solid {'#667eea' if key == 'professional' else '#e0e0e0'};
                        text-align: center; margin: 0.5rem;">
                <h3>{plan['name']}</h3>
                <div style="font-size: 2rem; font-weight: bold; margin: 1rem 0;">
                    ৳{plan['price']:,}<small style="font-size: 0.8rem;">/month</small>
                </div>
                <hr>
            """, unsafe_allow_html=True)
            
            for feature in plan['features']:
                st.markdown(f"✅ {feature}")
            
            st.markdown("---")
            
            if st.button(f"Get {plan['name']}", key=f"select_{key}", use_container_width=True):
                st.session_state.selected_plan = key
                st.session_state.show_checkout = True
                st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)