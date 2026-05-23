import streamlit as st

def show():
    st.markdown("""
    <div class="main-header">
        <h1>ℹ️ About Us</h1>
        <p>Empowering construction companies with AI-driven insights</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Our Mission
        To revolutionize the construction industry in Bangladesh by providing 
        cutting-edge AI technology that helps companies win more tenders, 
        optimize resources, and drive growth.
        
        ### Our Vision
        To be the leading AI-powered tender management platform in South Asia, 
        empowering construction companies to make data-driven decisions.
        
        ### Our Story
        Founded in 2024, TenderAI emerged from the need to address the challenges 
        faced by construction companies in Bangladesh when bidding for government 
        and private tenders.
        """)
    
    with col2:
        st.markdown("""
        ### Our Values
        - **Innovation**: Constantly pushing boundaries of AI in construction
        - **Integrity**: Transparent pricing and honest recommendations
        - **Impact**: Measurable results for our customers
        - **Inclusivity**: Solutions for companies of all sizes
        
        ### Our Team
        - **Md. Rahman** - CEO & AI Expert
        - **Sadia Khan** - CTO & ML Engineer
        - **Rafiq Islam** - Construction Expert
        """)
    
    st.markdown("---")
    st.markdown("### 📊 Our Impact")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Companies Served", "500+")
    with col2:
        st.metric("Tenders Analyzed", "10,000+")
    with col3:
        st.metric("Success Rate Increase", "47%")
    with col4:
        st.metric("Customer Satisfaction", "98%")