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

        def clear_error():
            """Clear error message when user starts typing."""
            return gr.update(value="", visible=False)

        # Clear error message when user starts typing
        username.change(fn=clear_error, outputs=[error_message])
        password.change(fn=clear_error, outputs=[error_message])

        return login_button, error_message, username, password
