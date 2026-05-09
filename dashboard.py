import dash
from ui.layout import get_layout
from ui.callbacks import register_callbacks

# Initialize Dash App
app = dash.Dash(
    __name__,
    title="F1 2022 Pit Wall",
    update_title=None,
    suppress_callback_exceptions=True,
    # Use the custom CSS in assets/style.css automatically
    assets_folder='assets' 
)

# Set the modular layout
app.layout = get_layout()

# Register centralized callbacks
register_callbacks(app)

if __name__ == "__main__":
    print("F1 2022 Pit Wall Dashboard starting...")
    app.run(debug=True, port=8050)
