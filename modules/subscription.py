import streamlit as st
import pandas as pd
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

PLANS = {
    'free': {
        'name': 'Free',
        'price_monthly': 0,
        'price_yearly': 0,
        'analyses_limit': 5,
        'users_limit': 1,
        'features': ['5 analyses/month', 'Basic Bid Optimizer','Rate Viewer', 'Basic reports', 'Email support', '7-day history']
    },
    'basic': {
        'name': 'Basic',
        'price_monthly': 4999,
        'price_yearly': 49990,
        'analyses_limit': 30,
        'users_limit': 3,
        'features': ['30 analyses/month', 'Basic Bid Optimizer', 'Advanced Bid Optimizer', 'AI predictions', 'Export reports', '30-day history', 'Email support']
    },
    'professional': {
        'name': 'Professional',
        'price_monthly': 14999,
        'price_yearly': 149990,
        'analyses_limit': -1,
        'users_limit': 10,
        'features': ['Unlimited analyses', 'Competitive Bid Simulator', 'ML predictions', 'Competitor tracking', 'Team collaboration', 'Priority support', 'API access']
    },
    'enterprise': {
        'name': 'Enterprise',
        'price_monthly': 49999,
        'price_yearly': 499990,
        'analyses_limit': -1,
        'users_limit': -1,
        'features': ['Everything in Professional', 'Custom AI model', 'Dedicated support', 'SLA guarantee', 'On-premise option']
    }
}

def render_subscription_page():
    """Render subscription management page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>💳 Subscription Management</h1>
        <p>Manage your plan, billing, and premium features</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get current subscription
    current_sub = db.get_user_subscription(st.session_state.user_id)
    current_plan = current_sub.get('plan', 'free')
    
    # Current plan details
    st.markdown("### 📋 Current Subscription")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Plan", PLANS[current_plan]['name'])
    with col2:
        st.metric("Status", current_sub.get('status', 'active').upper())
    with col3:
        limit = current_sub.get('analyses_limit', 5)
        used = current_sub.get('analyses_used', 0)
        if limit == -1:
            st.metric("Analyses", "Unlimited")
        else:
            remaining = max(0, limit - used)
            st.metric("Analyses Remaining", remaining)
    with col4:
        end_date = current_sub.get('end_date')
        if end_date:
            try:
                if isinstance(end_date, str):
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                else:
                    end_date_obj = end_date
                days_left = (end_date_obj - datetime.now()).days
                st.metric("Days Remaining", max(0, days_left))
            except:
                st.metric("Days Remaining", "N/A")
        else:
            st.metric("Days Remaining", "Active")
    
    # Current features
    st.markdown("### ✨ Current Plan Features")
    for feature in PLANS[current_plan]['features']:
        st.markdown(f"✅ {feature}")
    
    # Upgrade options
    st.markdown("---")
    st.markdown("### 🚀 Upgrade Options")
    
    # Billing cycle toggle
    billing_cycle = st.radio("Billing Cycle", ["Monthly", "Yearly (Save 20%)"], horizontal=True)
    
    # Display plans
    col1, col2, col3 = st.columns(3)
    
    upgrade_plans = ['basic', 'professional', 'enterprise']
    for idx, plan_key in enumerate(upgrade_plans):
        plan = PLANS[plan_key]
        price = plan['price_monthly'] if billing_cycle == "Monthly" else plan['price_yearly']
        
        with [col1, col2, col3][idx]:
            is_current = plan_key == current_plan
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 10px; 
                        border: 2px solid {'#667eea' if plan_key == 'professional' else '#e0e0e0'};
                        text-align: center; margin: 0.5rem;">
                <h3>{plan['name']}</h3>
                <div style="font-size: 2rem; font-weight: bold; margin: 1rem 0;">
                    ৳{price:,}<small style="font-size: 0.8rem;">/{'year' if billing_cycle == 'Yearly' else 'month'}</small>
                </div>
                <hr>
            """, unsafe_allow_html=True)
            
            for feature in plan['features'][:4]:
                st.markdown(f"✅ {feature}")
            
            st.markdown(f"👥 Up to {plan['users_limit'] if plan['users_limit'] != -1 else 'Unlimited'} users")
            
            if not is_current:
                if st.button(f"Upgrade to {plan['name']}", key=f"upgrade_{plan_key}", use_container_width=True):
                    st.session_state.selected_plan = plan_key
                    st.session_state.billing_cycle = billing_cycle.lower()
                    st.session_state.show_checkout = True
                    st.rerun()
            else:
                st.markdown("✅ **Current Plan**")
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Admin: View all subscriptions
    if st.session_state.user_role == 'admin':
        st.markdown("---")
        st.markdown("### 👑 Admin: All Subscriptions")
        
        all_subs = db.get_all_subscriptions()
        if all_subs:
            sub_df = pd.DataFrame(all_subs)
            if len(sub_df.columns) >= 5:
                sub_df = sub_df.iloc[:, :5]
            st.dataframe(sub_df, use_container_width=True, hide_index=True)
    
    # Billing history
    st.markdown("---")
    st.markdown("### 📜 Billing History")
    
    history_data = [
        {'Date': '2024-03-01', 'Amount': '৳14,999', 'Plan': 'Professional', 'Status': 'Paid'},
        {'Date': '2024-02-01', 'Amount': '৳14,999', 'Plan': 'Professional', 'Status': 'Paid'},
    ]
    st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)

def render_checkout():
    """Render checkout page"""
    st.markdown("""
    <div class="main-header">
        <h1>💳 Checkout</h1>
        <p>Complete your purchase</p>
    </div>
    """, unsafe_allow_html=True)
    
    if 'selected_plan' not in st.session_state:
        st.session_state.selected_plan = 'professional'
    
    plan = PLANS[st.session_state.selected_plan]
    billing = st.session_state.get('billing_cycle', 'monthly')
    
    if billing == 'monthly':
        price = plan['price_monthly']
        duration = 'month'
    else:
        price = plan['price_yearly']
        duration = 'year'
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### {plan['name']} Plan - {duration.upper()}LY")
        
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
            <h4>Order Summary</h4>
            <p><strong>Plan:</strong> {plan['name']} ({duration}ly)</p>
            <p><strong>Subtotal:</strong> ৳{price:,}</p>
            <p><strong>VAT (15%):</strong> ৳{price * 0.15:,.0f}</p>
            <hr>
            <p><strong>Total:</strong> ৳{price * 1.15:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Select Payment Method")
        
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        
        payment_methods = {
            'bkash': '💚 bKash',
            'nagad': '🧡 Nagad',
            'rocket': '💙 Rocket',
            'card': '💳 Credit Card'
        }
        
        selected_payment = None
        for idx, (key, name) in enumerate(payment_methods.items()):
            with [col_p1, col_p2, col_p3, col_p4][idx]:
                if st.button(name, key=f"pay_{key}", use_container_width=True):
                    selected_payment = key
        
        if selected_payment:
            st.markdown(f"### Payment via {payment_methods[selected_payment]}")
            
            if selected_payment == 'bkash':
                phone = st.text_input("bKash Account Number (01XXXXXXXXX)")
                if st.button("Complete Payment", use_container_width=True):
                    if phone:
                        transaction_id = f"BKASH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        db.update_subscription(st.session_state.user_id, st.session_state.selected_plan, 
                                              billing, selected_payment, transaction_id)
                        st.balloons()
                        st.success("Payment successful! Subscription activated.")
                        st.session_state.show_checkout = False
                        st.rerun()
                    else:
                        st.error("Please enter your bKash number")
            
            elif selected_payment == 'card':
                st.markdown("**Card Details**")
                card_number = st.text_input("Card Number", placeholder="4242 4242 4242 4242")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    expiry = st.text_input("Expiry (MM/YY)")
                with col_c2:
                    cvv = st.text_input("CVV", type="password")
                
                if st.button("Pay Now", use_container_width=True):
                    if card_number and expiry and cvv:
                        transaction_id = f"CARD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        db.update_subscription(st.session_state.user_id, st.session_state.selected_plan, 
                                              billing, selected_payment, transaction_id)
                        st.balloons()
                        st.success("Payment successful! Subscription activated.")
                        st.session_state.show_checkout = False
                        st.rerun()
                    else:
                        st.error("Please fill all card details")
    
    with col2:
        st.markdown("### What's Included")
        for feature in plan['features']:
            st.markdown(f"✅ {feature}")
        st.markdown("---")
        st.markdown("### 🔒 Secure Payment")
        st.markdown("- 256-bit SSL encryption\n- PCI compliant\n- Money-back guarantee")