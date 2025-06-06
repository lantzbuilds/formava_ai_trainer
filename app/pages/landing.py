import gradio as gr


def landing_page_view(state):
    with gr.Column():
        # Logo (replace with your logo path or use an emoji for now)
        logo = gr.Image(
            "static/images/formava_icon_v0_1.png", elem_id="logo", show_label=False
        )  # or gr.Markdown("🏋️‍♂️")

        # App Title
        title = gr.Markdown("# Formava AI Trainer")

        # Introduction
        intro = gr.Markdown(
            """
            Welcome to **Formava AI Trainer**!  
            This app provides AI-guided personal training advice, designed to work seamlessly with the Hevy Workout app.  
            **But you can also use it as a standalone AI personal trainer—no Hevy account required!**
            """
        )

        # Demo Account Button
        demo_btn = gr.Button("Use Demo Account", variant="primary")

        # Handler for demo login
        def use_demo_account():
            # You can fetch the demo user from DB or hardcode credentials
            demo_user = {
                "id": "demo_user_id",
                "username": "DemoUser",
                # ...other fields as needed
            }
            # Set the user state and navigate to dashboard
            state["user_state"] = demo_user
            # You may need to trigger dashboard view here, depending on your navigation logic
            return gr.update(), gr.update(), state  # adjust as needed

        demo_btn.click(
            fn=use_demo_account,
            inputs=[],
            outputs=[],  # or outputs=[...dashboard components, state] if you want to trigger navigation
        )

        return logo, title, intro, demo_btn
