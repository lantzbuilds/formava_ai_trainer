import logging

import gradio as gr

from config.database import Database
from models.user import UserProfile

db = Database()
logger = logging.getLogger(__name__)


def login_view():
    with gr.Column():
        gr.Markdown("## Login")

        username = gr.Textbox(label="Username", placeholder="Enter your username")
        password = gr.Textbox(
            label="Password", placeholder="Enter your password", type="password"
        )

        with gr.Row():
            login_button = gr.Button("Login", variant="primary")
            error_message = gr.Markdown(visible=False)

        def handle_login(username, password):
            try:
                # Get user from database
                user_doc = db.get_user_by_username(username)
                if not user_doc:
                    return None, gr.update(
                        value="Invalid username or password", visible=True
                    )

                # Verify password
                if not UserProfile.verify_password(password, user_doc["password"]):
                    return None, gr.update(
                        value="Invalid username or password", visible=True
                    )

                # Return user object for state management
                user = {
                    "id": user_doc["_id"],
                    "username": user_doc["username"],
                    "email": user_doc["email"],
                }

                return user, gr.update(visible=False)

            except Exception as e:
                logger.error(f"Login failed: {str(e)}", exc_info=True)
                return None, gr.update(value=f"Login failed: {str(e)}", visible=True)

        login_button.click(
            fn=handle_login,
            inputs=[username, password],
            outputs=[gr.State(), error_message],
        )

        return login_button, error_message
