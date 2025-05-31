import gradio as gr

from config.database import Database

db = Database()


def login_view():
    with gr.Column():
        gr.Markdown("## Login")

        with gr.Row():
            email = gr.Textbox(label="Email", placeholder="Enter your email")
            password = gr.Textbox(
                label="Password", placeholder="Enter your password", type="password"
            )

        with gr.Row():
            login_button = gr.Button("Login", variant="primary")
            error_message = gr.Markdown(visible=False)

        def handle_login(email, password):
            try:
                # TODO: Implement actual login logic
                # For now, just return a mock user
                user = {"email": email, "name": "Test User"}
                return user, gr.update(visible=False)
            except Exception as e:
                return None, gr.update(value=f"Error: {str(e)}", visible=True)

        login_button.click(
            fn=handle_login,
            inputs=[email, password],
            outputs=[gr.State(), error_message],
        )

        return login_button, error_message
