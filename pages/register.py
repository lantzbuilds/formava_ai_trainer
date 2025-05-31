import gradio as gr

from config.database import Database

db = Database()


def register_view():
    with gr.Column():
        gr.Markdown("## Register")

        with gr.Row():
            email = gr.Textbox(label="Email", placeholder="Enter your email")
            password = gr.Textbox(
                label="Password", placeholder="Enter your password", type="password"
            )
            confirm_password = gr.Textbox(
                label="Confirm Password",
                placeholder="Confirm your password",
                type="password",
            )

        with gr.Row():
            name = gr.Textbox(label="Name", placeholder="Enter your name")

        with gr.Row():
            register_button = gr.Button("Register", variant="primary")
            error_message = gr.Markdown(visible=False)

        def handle_register(email, password, confirm_password, name):
            try:
                if password != confirm_password:
                    return None, gr.update(value="Passwords do not match", visible=True)

                # TODO: Implement actual registration logic
                # For now, just return a mock user
                user = {"email": email, "name": name}
                return user, gr.update(visible=False)
            except Exception as e:
                return None, gr.update(value=f"Error: {str(e)}", visible=True)

        register_button.click(
            fn=handle_register,
            inputs=[email, password, confirm_password, name],
            outputs=[gr.State(), error_message],
        )

        return register_button, error_message
