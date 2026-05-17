import plotly.graph_objects as go
import streamlit as st

PROPERTY_TYPE_LABELS = {"D": "Detached", "S": "Semi-detached", "T": "Terraced", "F": "Flat"}
PROPERTY_TYPE_COLORS = {"D": "#1f77b4", "S": "#ff7f0e", "T": "#2ca02c", "F": "#d62728"}

DURATION_LABELS = {"F": "Freehold", "L": "Leasehold", "U": "Unknown"}
OLD_NEW_LABELS  = {"Y": "New build", "N": "Established"}


def hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def chart_layout(**kwargs):
    return dict(
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=20, b=40),
        hovermode="x unified",
        **kwargs,
    )


def add_baseline_bars(fig, years, vals, name, color, baseline=100, hover_suffix="", show_legend=True):
    """Add grouped bars coloured by whether they are above or below a baseline."""
    above = [v - baseline if v >= baseline else 0 for v in vals]
    below = [v - baseline if v <  baseline else 0 for v in vals]
    hover = f"%{{x}}: %{{base:.1f}}{hover_suffix}<extra>{name}</extra>"
    fig.add_trace(go.Bar(x=years, y=above, name=name, marker_color=color, opacity=0.8,
                         legendgroup=name, showlegend=show_legend, base=baseline, hovertemplate=hover))
    fig.add_trace(go.Bar(x=years, y=below, name=name, marker_color=color, opacity=0.4,
                         legendgroup=name, showlegend=False, base=baseline, hovertemplate=hover))


def show_data_table(rows, label="Data"):
    """Render rows (list of dicts) in a collapsed expander as a markdown table."""
    if not rows:
        return
    with st.expander(f"📋 {label}"):
        headers   = list(rows[0].keys())
        header_row = "| " + " | ".join(headers) + " |"
        sep_row    = "| " + " | ".join("---" for _ in headers) + " |"
        data_rows  = ["| " + " | ".join(str(r.get(h, "")) for h in headers) + " |" for r in rows]
        st.markdown("\n".join([header_row, sep_row] + data_rows))
