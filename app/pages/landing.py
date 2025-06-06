import gradio as gr


def landing_page_view(state):
    with gr.Column():
        with gr.Row():
            # App Title
            title = gr.Markdown("# Formava AI Trainer", elem_id="app-title")
            # Logo
            logo = gr.Image(
                "app/static/images/formava_logo_med_v0_1.png",
                elem_id="logo",
                show_label=False,
            )

        # Introduction
        intro = gr.Markdown(
            """
            Welcome to **Formava AI Trainer**!  
            This app provides AI-guided personal training advice, designed to work seamlessly with the Hevy Workout app.  
            **But you can also use it as a standalone AI personal trainer—no Hevy account required!**
            
            While we're beta testing, you can use the demo account to automatically log in. It's already connected to the Hevy Workout app, so you can use it to start training right away.
            """
        )

        # Demo Account Button
        demo_btn = gr.Button("Use Demo Account", variant="primary")

        # Handler for demo login
        def use_demo_account():
            # You can fetch the demo user from DB or hardcode credentials
            demo_user = {
                "id": "075ce2423576c5d4a0d8f883aa4ebf7e",
                "username": "demo_user",
                "email": "demo_user@formava.ai",
            }

            return demo_user

        # demo_btn.click(
        #     fn=use_demo_account,
        #     inputs=[],
        #     outputs=[
        #         state["user_state"],
        #     ],
        # )

        return title, intro, logo, demo_btn, use_demo_account
