"""
Login page for the AI Personal Trainer application.
"""

import streamlit as st

from config.database import Database
from models.user import UserProfile

# Initialize database connection
db = Database()


def login_page():
    """Display the login page."""
    st.title("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            # Get user from database
            user_doc = db.get_user_by_username(username)
            if user_doc:
                # Create UserProfile instance from document
                user = UserProfile(**user_doc)
                # Verify password
                if user.verify_password(password):
                    # Store the document ID, not the user ID
                    st.session_state.user_id = user_doc["_id"]
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Invalid username or password")
