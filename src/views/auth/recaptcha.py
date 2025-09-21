# src/views/auth/recaptcha.py
import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class Recaptcha:
    def __init__(self):
        self.site_key = os.getenv("RECAPTCHA_SITE_KEY", st.secrets.get("recaptcha", {}).get("site_key", ""))
        self.secret_key = os.getenv("RECAPTCHA_SECRET_KEY", st.secrets.get("recaptcha", {}).get("secret_key", ""))
    
    def render(self, key="recaptcha"):
        """Render reCAPTCHA v2 widget"""
        st.markdown(f"""
        <div class="g-recaptcha" data-sitekey="{self.site_key}"></div>
        <script src="https://www.google.com/recaptcha/api.js" async defer></script>
        """, unsafe_allow_html=True)
        
        # Add a hidden input to capture the response
        recaptcha_response = st.text_input("", key=key, type="password", label_visibility="collapsed")
        
        return recaptcha_response
    
    def verify(self, recaptcha_response):
        """Verify reCAPTCHA response"""
        if not recaptcha_response:
            return False
            
        data = {
            'secret': self.secret_key,
            'response': recaptcha_response
        }
        
        try:
            response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data, timeout=10)
            result = response.json()
            return result.get('success', False)
        except Exception as e:
            st.error(f"reCAPTCHA verification failed: {e}")
            return False