"""
Application Streamlit — Prédiction LoL en temps réel.
Lance une partie de LoL, puis : streamlit run app/main.py
"""

import sys
import time
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.live.live_client import get_current_features
from src.models.predict import get_advice, predict_win_probability

POLL_INTERVAL = 7  # secondes entre chaque update

st.set_page_config(
    page_title="LoL Win Predictor",
    page_icon="⚔️",
    layout="wide",
)

st.title("⚔️ LoL Win Predictor")
st.caption("Prédiction en temps réel de la victoire — équipe bleue (ORDER)")

# Historique des prédictions pour le graphe de tendance
if "history" not in st.session_state:
    st.session_state.history = []
if "last_features" not in st.session_state:
    st.session_state.last_features = None


def make_gauge(proba: float) -> go.Figure:
    color = "green" if proba > 0.6 else ("red" if proba < 0.4 else "orange")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(proba * 100, 1),
        number={"suffix": "%", "font": {"size": 48}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 40], "color": "#ffcccc"},
                {"range": [40, 60], "color": "#fff3cc"},
                {"range": [60, 100], "color": "#ccffcc"},
            ],
            "threshold": {
                "line": {"color": "black", "width": 3},
                "thickness": 0.75,
                "value": 50,
            },
        },
        title={"text": "Probabilité victoire BLUE", "font": {"size": 18}},
    ))
    fig.update_layout(height=300, margin=dict(t=40, b=0, l=20, r=20))
    return fig


def make_trend(history: list[tuple]) -> go.Figure:
    if len(history) < 2:
        return None
    times, probas = zip(*history)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(times), y=[p * 100 for p in probas],
        mode="lines+markers", line=dict(color="steelblue", width=2),
        name="Win %",
    ))
    fig.add_hline(y=50, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="Évolution de la probabilité",
        xaxis_title="Temps de jeu (min)",
        yaxis_title="Win % (équipe bleue)",
        yaxis=dict(range=[0, 100]),
        height=250,
        margin=dict(t=40, b=40, l=40, r=20),
    )
    return fig


# Layout principal
col_gauge, col_stats = st.columns([1, 1])
gauge_placeholder = col_gauge.empty()
stats_placeholder = col_stats.empty()
trend_placeholder = st.empty()
advice_placeholder = st.empty()
status_placeholder = st.empty()

while True:
    features = get_current_features()

    if features is None:
        status_placeholder.warning(
            "🔌 Aucune partie détectée. Lance League of Legends et rejoins une partie."
        )
        gauge_placeholder.plotly_chart(make_gauge(0.5), use_container_width=True)
        time.sleep(POLL_INTERVAL)
        st.rerun()

    status_placeholder.success(f"🎮 Partie en cours — {features['game_time_minutes']:.1f} min")

    proba = predict_win_probability(features)
    st.session_state.history.append((features["game_time_minutes"], proba))
    st.session_state.last_features = features

    # Gauge
    with gauge_placeholder:
        st.plotly_chart(make_gauge(proba), use_container_width=True)

    # Stats tableau
    with stats_placeholder:
        st.subheader("État actuel")
        cols = st.columns(2)
        metrics = [
            ("Kills", features.get("kills_diff", 0)),
            ("CS", features.get("cs_diff", 0)),
            ("Gold", features.get("gold_diff", 0)),
            ("Niveaux", features.get("level_diff", 0)),
            ("Tours", features.get("towers_diff", 0)),
            ("Dragons", features.get("dragons_diff", 0)),
            ("Barons", features.get("barons_diff", 0)),
            ("Hérauts", features.get("heralds_diff", 0)),
        ]
        for i, (label, val) in enumerate(metrics):
            delta_color = "normal" if val != 0 else "off"
            cols[i % 2].metric(
                label=f"{label} (bleu - rouge)",
                value=f"{val:+d}",
                delta_color=delta_color,
            )

    # Tendance
    trend_fig = make_trend(st.session_state.history)
    if trend_fig:
        with trend_placeholder:
            st.plotly_chart(trend_fig, use_container_width=True)

    # Conseils
    advice = get_advice(features, proba)
    with advice_placeholder:
        st.subheader("Conseils stratégiques")
        for tip in advice:
            st.info(tip)

    time.sleep(POLL_INTERVAL)
    st.rerun()
