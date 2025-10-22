import os
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv('API_BASE', 'http://localhost:8000')
API_PREFIX = os.getenv('API_PREFIX', '/api/v1')

st.set_page_config(page_title="Loan Navigator UI", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {'token': None, 'role': None}

# --- Login UI ---
st.title('Loan Navigator - Login')

with st.form('login'):
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    submitted = st.form_submit_button('Login')

if submitted:
    # Try admin login first (admin creds stored in .env with ADMIN_USERNAME/ADMIN_PASSWORD)
    admin_username = os.getenv('ADMIN_USERNAME')
    admin_password = os.getenv('ADMIN_PASSWORD')
    admin_jwt_key = os.getenv('ADMIN_JWT_KEY')

    if username and password and admin_username and password == admin_password and username == admin_username:
        # create admin token locally (signed with ADMIN_JWT_KEY)
        import jwt, datetime
        payload = {
            'sub': username,
            'iat': int(datetime.datetime.utcnow().timestamp()),
            'exp': int((datetime.datetime.utcnow() + datetime.timedelta(days=7)).timestamp())
        }
        token = jwt.encode(payload, admin_jwt_key, algorithm='HS256')
        st.session_state.auth = {'token': token, 'role': 'admin', 'user': username}
        st.success('Logged in as admin')
        st.experimental_rerun()

    # Else try user login via backend endpoint
    try:
        resp = requests.post(f"{API_BASE}{API_PREFIX}/auth/login", json={'username': username, 'password': password}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.auth = {'token': data['token'], 'role': 'user', 'user': data.get('user')}
            st.success('Logged in')
            st.experimental_rerun()
        else:
            st.error('Login failed: ' + resp.text)
    except Exception as e:
        st.error('Error contacting API: ' + str(e))

# If logged in, show dashboard
if st.session_state.auth.get('token'):
    role = st.session_state.auth.get('role')
    token = st.session_state.auth.get('token')

    st.sidebar.markdown(f"**Logged in as:** {st.session_state.auth.get('user')} ({role})")
    if st.sidebar.button('Logout'):
        st.session_state.auth = {'token': None, 'role': None}
        st.experimental_rerun()

    if role == 'admin':
        st.header('Admin Dashboard')
        # Fetch users list from backend
        try:
            headers = {'Authorization': f'Bearer {token}'}
            resp = requests.get(f"{API_BASE}{API_PREFIX}/admin/users", headers=headers, timeout=10)
            if resp.status_code == 200:
                users = resp.json()
                sel = st.selectbox('Select a user to act on', options=[u['customer_id'] for u in users])
                if sel:
                    st.subheader(f'Loans & actions for customer {sel}')
                    # Let admin ask questions about selected user loans
                    question = st.text_area('Ask a question about the selected customer's loans')
                    if st.button('Ask AI') and question:
                        payload = {'message': question, 'customer_id': int(sel)}
                        r = requests.post(f"{API_BASE}{API_PREFIX}/chat/", json=payload, headers=headers, timeout=30)
                        if r.status_code == 200:
                            st.markdown('**AI Answer**')
                            st.write(r.json().get('answer'))
                        else:
                            st.error(f'Error: {r.status_code} - {r.text}')
            else:
                st.error('Failed to fetch users: ' + resp.text)
        except Exception as e:
            st.error('Error contacting API: ' + str(e))

    else:
        st.header('Customer Dashboard')
        # Load customer loans
        try:
            headers = {'Authorization': f'Bearer {token}'}
            # Ask backend for customer loans
            r = requests.get(f"{API_BASE}{API_PREFIX}/customer/loans", headers=headers, timeout=10)
            if r.status_code == 200:
                loans = r.json()
                st.write('Your loans:')
                selected = []
                for loan in loans:
                    checked = st.checkbox(f"Loan {loan.get('loan_id')} - Status: {loan.get('status')}", value=False)
                    if checked:
                        selected.append(loan)

                question = st.text_area('Ask a question about your loans (leave blank to use all loans)')
                if st.button('Ask AI'):
                    payload = {'message': question or 'Please analyze my loans.', 'customer_id': loans[0].get('customer_id') if loans else None}
                    r2 = requests.post(f"{API_BASE}{API_PREFIX}/chat/", json=payload, headers=headers, timeout=30)
                    if r2.status_code == 200:
                        st.markdown('**AI Answer**')
                        st.write(r2.json().get('answer'))
                    else:
                        st.error(f'Error: {r2.status_code} - {r2.text}')
            else:
                st.error('Failed to fetch loans: ' + r.text)
        except Exception as e:
            st.error('Error contacting API: ' + str(e))