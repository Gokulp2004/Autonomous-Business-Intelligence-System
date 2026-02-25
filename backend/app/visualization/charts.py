"""
charts.py — Plotly Chart Builders

Creates interactive charts using Plotly. The charts are returned as JSON
which the React frontend renders using Plotly.js.

Why Plotly?
  - Interactive (zoom, hover, pan)
  - Works in both Python (backend) and JavaScript (frontend)
  - Beautiful default styling
  - Easy to export to images for PDF reports
"""

# TODO: Implement in Step 7


def create_bar_chart(df, x_col, y_col, title="") -> dict:
    """Create a bar chart and return Plotly JSON."""
    # TODO: Implement in Step 7
    pass


def create_line_chart(df, x_col, y_col, title="") -> dict:
    """Create a line chart and return Plotly JSON."""
    # TODO: Implement in Step 7
    pass


def create_scatter_plot(df, x_col, y_col, title="") -> dict:
    """Create a scatter plot and return Plotly JSON."""
    # TODO: Implement in Step 7
    pass


def create_correlation_heatmap(df, title="Correlation Matrix") -> dict:
    """Create a correlation heatmap and return Plotly JSON."""
    # TODO: Implement in Step 7
    pass
