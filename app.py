import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from config.database import Database
from models.user import FitnessGoal, Injury, Sex, UserProfile
from services.hevy_api import HevyAPI
from services.openai_service import OpenAIService
from utils.crypto import decrypt_api_key, encrypt_api_key
from utils.units import (
    cm_to_inches,
    format_height_cm,
    format_weight_kg,
    inches_to_cm,
    kg_to_lbs,
    lbs_to_kg,
)

# Load environment variables
load_dotenv()

# Initialize database connection
db = Database()

# Set page configuration
st.set_page_config(
    page_title="AI Personal Trainer",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Session state for user authentication
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None


# Sidebar navigation
def sidebar():
    st.sidebar.title("AI Personal Trainer")

    if st.session_state.user_id:
        st.sidebar.write(f"Welcome, {st.session_state.username}!")
        if st.sidebar.button("Logout"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.experimental_rerun()

        st.sidebar.markdown("---")
        st.sidebar.subheader("Navigation")
        page = st.sidebar.radio(
            "Go to",
            [
                "Dashboard",
                "Workout History",
                "Profile",
                "AI Recommendations",
                "Sync Hevy",
            ],
        )
        return page
    else:
        page = st.sidebar.radio("Go to", ["Login", "Register"])
        return page


# Login page
def login_page():
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
                    st.session_state.user_id = user.id
                    st.session_state.username = username
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Invalid username or password")


# Registration page
def register_page():
    st.title("Register")

    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        col1, col2 = st.columns(2)
        with col1:
            # Height in feet and inches
            height_feet = st.number_input(
                "Height (feet)", min_value=3, max_value=8, value=5
            )
            height_inches = st.number_input(
                "Height (inches)", min_value=0, max_value=11, value=10
            )
            # Convert to cm for storage
            height_cm = inches_to_cm(height_feet * 12 + height_inches)

            # Weight in pounds
            weight_lbs = st.number_input(
                "Weight (lbs)", min_value=50, max_value=500, value=150
            )
            # Convert to kg for storage
            weight_kg = lbs_to_kg(weight_lbs)

            sex = st.selectbox("Sex", [s.value for s in Sex])

        with col2:
            age = st.number_input("Age", min_value=13, max_value=120, value=30)
            experience = st.selectbox(
                "Experience Level", ["beginner", "intermediate", "advanced"]
            )
            goals = st.multiselect("Fitness Goals", [g.value for g in FitnessGoal])

        # Hevy API Integration
        st.subheader("Hevy API Integration (Optional)")
        hevy_api_key = st.text_input(
            "Hevy API Key",
            type="password",
            help="You can add this later in your profile",
        )
        if hevy_api_key:
            # Encrypt the API key before storing
            encrypted_key = encrypt_api_key(hevy_api_key)
        else:
            encrypted_key = None

        # Injuries
        st.subheader("Injuries (Optional)")
        injuries = []
        injury_count = st.number_input(
            "Number of injuries to add", min_value=0, max_value=5, value=0
        )

        for i in range(injury_count):
            with st.expander(f"Injury {i+1}"):
                description = st.text_input(f"Description", key=f"injury_desc_{i}")
                body_part = st.text_input(f"Body Part", key=f"injury_part_{i}")
                severity = st.selectbox(
                    f"Severity",
                    ["mild", "moderate", "severe"],
                    key=f"injury_severity_{i}",
                )
                date_injured = st.date_input(
                    f"Date Injured", value=datetime.now().date(), key=f"injury_date_{i}"
                )
                is_active = st.checkbox(
                    f"Currently Active", value=True, key=f"injury_active_{i}"
                )
                notes = st.text_area(f"Notes", key=f"injury_notes_{i}")

                if description and body_part:  # Only add if required fields are filled
                    injuries.append(
                        {
                            "description": description,
                            "body_part": body_part,
                            "severity": severity,
                            "date_injured": datetime.combine(
                                date_injured, datetime.min.time()
                            ).isoformat(),
                            "is_active": is_active,
                            "notes": notes,
                        }
                    )

        submit = st.form_submit_button("Register")

        if submit:
            if password != confirm_password:
                st.error("Passwords do not match")
            else:
                try:
                    # Create new user with hashed password
                    new_user = UserProfile.create_user(
                        username=username,
                        email=email,
                        password=password,
                        height_cm=height_cm,
                        weight_kg=weight_kg,
                        sex=Sex(sex),
                        age=age,
                        fitness_goals=[FitnessGoal(g) for g in goals],
                        experience_level=experience,
                        hevy_api_key=encrypted_key,
                        injuries=injuries,
                    )

                    # Save to database
                    doc_id, doc_rev = db.save_document(new_user.dict())
                    st.success(f"Registration successful! Welcome, {username}!")
                    st.session_state.user_id = doc_id
                    st.session_state.username = username
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Registration failed: {str(e)}")


# Dashboard page
def dashboard_page():
    st.title("Dashboard")

    # Get user's recent workouts
    user_id = st.session_state.user_id
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    workouts = db.get_user_workout_history(user_id, start_date, end_date)

    if workouts:
        # Create a DataFrame for visualization
        workout_data = []
        for workout in workouts:
            workout_data.append(
                {
                    "date": workout["start_time"],
                    "title": workout["title"],
                    "exercises": workout["exercise_count"],
                    "duration": workout.get("duration", 0),
                }
            )

        df = pd.DataFrame(workout_data)

        # Display workout frequency
        st.subheader("Workout Frequency")
        fig = px.bar(df, x="date", y="exercises", title="Workouts in the Last 30 Days")
        st.plotly_chart(fig, use_container_width=True)

        # Display recent workouts
        st.subheader("Recent Workouts")
        for workout in workouts[:5]:  # Show last 5 workouts
            with st.expander(f"{workout['title']} - {workout['start_time']}"):
                st.write(
                    f"**Description:** {workout.get('description', 'No description')}"
                )
                st.write(f"**Exercises:** {workout['exercise_count']}")
                if "duration" in workout:
                    st.write(f"**Duration:** {workout['duration']:.1f} minutes")
    else:
        st.info("No workouts found. Start tracking your workouts to see your progress!")


# Workout History page
def workout_history_page():
    st.title("Workout History")

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.utcnow() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.utcnow())

    # Convert to datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Get workouts
    user_id = st.session_state.user_id
    workouts = db.get_user_workout_history(user_id, start_datetime, end_datetime)

    if workouts:
        # Create a DataFrame
        workout_data = []
        for workout in workouts:
            workout_data.append(
                {
                    "date": workout["start_time"],
                    "title": workout["title"],
                    "exercises": workout["exercise_count"],
                    "duration": workout.get("duration", 0),
                }
            )

        df = pd.DataFrame(workout_data)

        # Display as a table
        st.dataframe(df)

        # Download option
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="workout_history.csv",
            mime="text/csv",
        )
    else:
        st.info("No workouts found for the selected date range.")


# Profile page
def profile_page():
    st.title("Your Profile")

    user_id = st.session_state.user_id
    user_doc = db.get_document(user_id)

    if user_doc:
        # Display current profile
        st.subheader("Personal Information")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Username:** {user_doc.get('username', 'N/A')}")
            st.write(f"**Email:** {user_doc.get('email', 'N/A')}")
            st.write(f"**Height:** {format_height_cm(user_doc.get('height_cm', 0))}")
            st.write(f"**Weight:** {format_weight_kg(user_doc.get('weight_kg', 0))}")

        with col2:
            st.write(f"**Sex:** {user_doc.get('sex', 'N/A')}")
            st.write(f"**Age:** {user_doc.get('age', 'N/A')}")
            st.write(f"**Experience Level:** {user_doc.get('experience_level', 'N/A')}")
            st.write(
                f"**Fitness Goals:** {', '.join(user_doc.get('fitness_goals', []))}"
            )

        # Hevy API Integration
        st.subheader("Hevy API Integration")
        if user_doc.get("hevy_api_key"):
            st.success("Hevy API key is configured")
            if st.button("Update Hevy API Key"):
                new_key = st.text_input("New Hevy API Key", type="password")
                if st.button("Save"):
                    encrypted_key = encrypt_api_key(new_key)
                    db.update_user_hevy_api_key(user_id, encrypted_key)
                    st.success("Hevy API key updated successfully!")
                    st.experimental_rerun()
        else:
            st.warning("Hevy API key is not configured")
            new_key = st.text_input("Hevy API Key", type="password")
            if st.button("Save"):
                encrypted_key = encrypt_api_key(new_key)
                db.update_user_hevy_api_key(user_id, encrypted_key)
                st.success("Hevy API key saved successfully!")
                st.experimental_rerun()

        # Edit profile
        st.subheader("Edit Profile")
        with st.form("edit_profile"):
            # Height in feet and inches
            current_height_cm = user_doc.get("height_cm", 170)
            current_height_inches = cm_to_inches(current_height_cm)
            height_feet = st.number_input(
                "Height (feet)",
                min_value=3,
                max_value=8,
                value=int(current_height_inches // 12),
            )
            height_inches = st.number_input(
                "Height (inches)",
                min_value=0,
                max_value=11,
                value=int(current_height_inches % 12),
            )
            new_height_cm = inches_to_cm(height_feet * 12 + height_inches)

            # Weight in pounds
            current_weight_kg = user_doc.get("weight_kg", 70)
            weight_lbs = st.number_input(
                "Weight (lbs)",
                min_value=50,
                max_value=500,
                value=int(kg_to_lbs(current_weight_kg)),
            )
            new_weight_kg = lbs_to_kg(weight_lbs)

            new_goals = st.multiselect(
                "Fitness Goals",
                [g.value for g in FitnessGoal],
                default=user_doc.get("fitness_goals", []),
            )

            if st.form_submit_button("Update Profile"):
                user_doc["height_cm"] = new_height_cm
                user_doc["weight_kg"] = new_weight_kg
                user_doc["fitness_goals"] = new_goals
                user_doc["updated_at"] = datetime.utcnow().isoformat()

                db.update_document(user_doc)
                st.success("Profile updated successfully!")
                st.experimental_rerun()
    else:
        st.error("User profile not found.")


# AI Recommendations page
def ai_recommendations_page():
    st.title("AI Workout Recommendations")

    user_id = st.session_state.user_id
    user_doc = db.get_document(user_id)

    if user_doc:
        st.subheader("Your Profile")
        st.write(f"**Experience Level:** {user_doc.get('experience_level', 'N/A')}")
        st.write(f"**Fitness Goals:** {', '.join(user_doc.get('fitness_goals', []))}")

        # Get recent workouts
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        workouts = db.get_user_workout_history(user_id, start_date, end_date)

        if workouts:
            st.subheader("Recent Workouts")
            workout_summary = []
            for workout in workouts[:5]:  # Show last 5 workouts
                workout_summary.append(
                    f"- {workout['title']} ({workout['start_time']})"
                )

            st.write("\n".join(workout_summary))

            # Generate recommendation
            if st.button("Generate Workout Recommendation"):
                with st.spinner(
                    "Analyzing your workout history and generating a personalized recommendation..."
                ):
                    try:
                        # Initialize OpenAI service
                        openai_service = OpenAIService()

                        # Generate recommendations
                        recommendations = (
                            openai_service.generate_workout_recommendation(
                                user_profile=user_doc,
                                recent_workouts=workouts,
                                num_workouts=1,
                            )
                        )

                        if recommendations:
                            st.success("Recommendation generated!")

                            # Display recommendation
                            st.subheader("Recommended Workout")
                            workout = recommendations[0]
                            st.write(f"**Title:** {workout['title']}")
                            st.write(f"**Description:** {workout['description']}")

                            st.write("**Exercises:**")
                            for exercise in workout["exercises"]:
                                st.write(
                                    f"- **{exercise['name']}:** {exercise['sets']} sets x {exercise['reps']} reps"
                                )
                                if "notes" in exercise and exercise["notes"]:
                                    st.write(f"  *{exercise['notes']}*")
                        else:
                            st.error(
                                "Failed to generate recommendations. Please try again."
                            )
                    except Exception as e:
                        st.error(f"Error generating recommendations: {e}")
        else:
            st.info(
                "No recent workouts found. Complete a workout to get personalized recommendations."
            )
    else:
        st.error("User profile not found.")


# Sync Hevy page
def sync_hevy_page():
    st.title("Sync with Hevy")

    user_id = st.session_state.user_id
    user_doc = db.get_document(user_id)

    if user_doc:
        if user_doc.get("hevy_api_key"):
            st.info(
                "Your Hevy API key is configured. You can sync your workouts from Hevy."
            )

            if st.button("Sync Workouts from Hevy"):
                with st.spinner("Syncing workouts from Hevy..."):
                    try:
                        # Initialize Hevy API service
                        hevy_api = HevyAPI(user_doc["hevy_api_key"])

                        # Sync workouts
                        synced_count = hevy_api.sync_workouts(db, user_id)

                        st.success(
                            f"Successfully synced {synced_count} workouts from Hevy!"
                        )
                    except Exception as e:
                        st.error(f"Error syncing workouts: {e}")
        else:
            st.warning("You need to configure your Hevy API key to sync workouts.")
            st.write("Go to the Profile page to set up your Hevy API key.")
    else:
        st.error("User profile not found.")


# Main app
def main():
    page = sidebar()

    if page == "Login":
        login_page()
    elif page == "Register":
        register_page()
    elif page == "Dashboard":
        dashboard_page()
    elif page == "Workout History":
        workout_history_page()
    elif page == "Profile":
        profile_page()
    elif page == "AI Recommendations":
        ai_recommendations_page()
    elif page == "Sync Hevy":
        sync_hevy_page()


if __name__ == "__main__":
    main()
