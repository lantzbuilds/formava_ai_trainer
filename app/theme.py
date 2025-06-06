"""
Theme configuration for the AI Personal Trainer application.
"""

import gradio as gr


def setup_theme():
    """Setup the application theme and custom CSS."""
    custom_css = """
    /* Base styles */
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 1rem;
    }
    
    /* Navigation styles */
    .nav-bar {
        background-color: #f0f0f0;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    
    .nav-button {
        flex: 1;
        min-width: 120px;
        margin: 0.25rem;
        white-space: nowrap;
        text-align: center;
    }
    
    /* Page container styles */
    .page-container {
        padding: 1rem;
        border-radius: 8px;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        width: 100%;
        box-sizing: border-box;
    }
    
    /* Form styles */
    .form-group {
        margin-bottom: 1rem;
        width: 100%;
    }
    
    .form-input {
        width: 100%;
        box-sizing: border-box;
    }
    
    /* Responsive grid */
    .grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1rem;
        width: 100%;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .container {
            padding: 0.5rem;
        }
        
        .nav-bar {
            padding: 0.5rem;
        }
        
        .nav-button {
            min-width: 100px;
            font-size: 0.9rem;
            padding: 0.5rem;
        }
        
        .page-container {
            padding: 0.75rem;
        }
        
        .grid-container {
            grid-template-columns: 1fr;
        }
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .nav-bar {
            background-color: #2d2d2d;
        }
        
        .page-container {
            background-color: #1e1e1e;
            color: #ffffff;
        }
    }
    """

    return gr.Blocks(theme=gr.themes.Soft(), css=custom_css)
