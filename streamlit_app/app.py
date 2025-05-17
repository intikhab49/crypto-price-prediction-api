import streamlit as st
import requests
import json

# FastAPI backend URL
API_BASE_URL = "http://127.0.0.1:8000/auth"  # Change if running on a server

# Streamlit app setup
st.set_page_config(page_title="Crypto & Stock Predictor", page_icon="📈", layout="wide")

# Session state for authentication and page navigation
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Login"

### 🚀 LOGIN & REGISTER ###
def login():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        response = requests.post(f"{API_BASE_URL}/login", json={"username": username, "password": password})
        if response.status_code == 200:
            st.session_state.access_token = response.json().get("access_token")
            st.session_state.current_page = "Crypto Predictor"
            st.success("Login successful!")
            st.rerun()  # Rerun the app to update the page
        else:
            st.error("Invalid credentials!")

def register():
    st.title("📝 Register")
    username = st.text_input("New Username")
    password = st.text_input("New Password", type="password")

    if st.button("Register"):
        response = requests.post(f"{API_BASE_URL}/register", json={"username": username, "password": password})
        if response.status_code == 200:
            st.success("Registration successful! Please login.")
        else:
            st.error("Registration failed!")

# Navigation
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio("Go to", ["Login", "Register", "Crypto Predictor"])

# Update the current page based on the sidebar selection
if page != st.session_state.current_page:
    st.session_state.current_page = page
    st.rerun()

# Display the appropriate page based on the current page state
if st.session_state.current_page == "Login":
    login()
elif st.session_state.current_page == "Register":
    register()
elif st.session_state.current_page == "Crypto Predictor":
    if not st.session_state.access_token:
        st.warning("Please log in first!")
        st.stop()

    ### 🚀 CRYPTO PREDICTOR ###
    st.title("📊 Crypto & Stock Predictor")

    symbol = st.selectbox("Select Crypto/Stock Symbol", ["BTC-USD", "BNB-USD", "ETH-USD"])
    
    if st.button("Predict Price"):
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        response = requests.post("http://127.0.0.1:8000/pred/predict", json={"symbol": symbol}, headers=headers)

        if response.status_code == 200:
            data = response.json()
            prob = data.get("predicted_probability", 0)
            recommendation = data.get("recommendation", "Unknown")

            st.metric(label="Predicted Probability", value=f"{prob}%")
            
        else:
            st.error("Prediction failed!")