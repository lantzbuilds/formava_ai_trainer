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
            label="Password",
            placeholder="Enter your password",
            type="password",
            show_label=True,
            interactive=True,
            visible=True,
        )

        with gr.Row():
            login_button = gr.Button("Login", variant="primary")
            error_message = gr.Markdown(visible=False)

        return login_button, error_message, username, password
