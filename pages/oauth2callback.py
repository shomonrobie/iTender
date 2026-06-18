# pages/oauth2callback.py
"""
OAuth2 Callback Handler for Google Sign-In
"""

import streamlit as st

# ✅ Check if code is in the URL
query_params = st.query_params

if 'code' in query_params:
    # ✅ Get the current URL with code
    import urllib.parse
    
    # Build the redirect URL with the code intact
    # Redirect to the main page (login) with all query params
    redirect_url = "/?page=login"
    
    # Add all query params to the redirect URL
    params = dict(query_params)
    if params:
        redirect_url += "&" + urllib.parse.urlencode(params)
    
    # ✅ Show loading message and redirect using JavaScript
    st.markdown(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="1;url={redirect_url}">
        <style>
            body {{
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                margin: 0;
            }}
            .container {{
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            }}
            .loader {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="loader"></div>
            <h2>🔄 Authenticating...</h2>
            <p>Please wait while we complete your sign-in.</p>
            <p style="font-size: 12px; color: #888;">Redirecting...</p>
        </div>
        
        <script>
            // Redirect to the main page with all query params intact
            // This ensures the 'code' parameter is preserved
            setTimeout(function() {{
                window.location.href = "{redirect_url}";
            }}, 500);
        </script>
    </body>
    </html>
    """, unsafe_allow_html=True)
    
else:
    # No code in URL - redirect to login
    st.markdown("""
    <meta http-equiv="refresh" content="1;url=/?page=login">
    <div style="text-align: center; padding: 50px;">
        <h2>🔐 No Authentication Code</h2>
        <p>Redirecting to login...</p>
    </div>
    """, unsafe_allow_html=True)