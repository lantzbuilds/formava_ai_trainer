import logging

import gradio as gr

from app.config.database import Database
from app.models.user import UserProfile

db = Database()
logger = logging.getLogger(__name__)


def login_view():
    with gr.Column():
        gr.Markdown("## Login")

        username = gr.Textbox(label="Username", placeholder="Enter your username")
        password = gr.Textbox(
            label="Password",
            placeholder="Enter your password",
            type="password",
            show_label=True,
            interactive=True,
            visible=True,
        )

        with gr.Row():
            login_button = gr.Button("Login", variant="primary")

        error_message = gr.Markdown(visible=False, elem_classes="error-message")

        # Add a timer to auto-clear error messages after 5 seconds
        error_timer = gr.Timer(value=15.0, active=False)

        def clear_error_on_timer():
            """Clear error message after timer expires."""
            return gr.update(value="", visible=False), gr.update(active=False)

        def clear_error_on_user_input():
            """Clear error message when user starts typing."""
            return gr.update(value="", visible=False), gr.update(active=False)

        # Clear error message when user starts typing
        username.change(
            fn=clear_error_on_user_input, outputs=[error_message, error_timer]
        )
        password.change(
            fn=clear_error_on_user_input, outputs=[error_message, error_timer]
        )

        # Auto-clear error message after 5 seconds
        error_timer.tick(fn=clear_error_on_timer, outputs=[error_message, error_timer])

        return login_button, error_message, username, password, error_timer
