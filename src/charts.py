import plotly.express as px
import pandas as pd
import streamlit as st


def render_overview_charts(df, incidents):
    left, right = st.columns(2)

    with left:
        by_component = (
            df.groupby("component")
            .agg(logs=("event_id", "count"), anomalies=("is_anomaly", "sum"))
            .reset_index()
            .sort_values("logs", ascending=False)
            .head(15)
        )
        fig = px.bar(
            by_component, x="component", y=["logs", "anomalies"],
            barmode="group", title="Logs vs anomalies by component"
        )
        fig.update_layout(height=420, xaxis_tickangle=-45)
        st.plotly_chart(fig, width="stretch")

    with right:
        hourly = (
            df.set_index("normalized_timestamp")
            .resample("1h")
            .agg(logs=("event_id", "count"), anomalies=("is_anomaly", "sum"))
            .reset_index()
        )
        fig = px.line(
            hourly, x="normalized_timestamp", y=["logs", "anomalies"],
            title="Log and anomaly activity over time"
        )
        fig.update_layout(height=420)
        st.plotly_chart(fig, width="stretch")


def render_anomaly_chart(df, score_column="anomaly_score", title="Anomaly score over time"):
    sample = df.sample(min(5000, len(df)), random_state=42)
    fig = px.scatter(
        sample,
        x="normalized_timestamp",
        y=score_column,
        color="severity",
        hover_data=["component", "parsed_message_type", "message"],
        title=title,
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, width="stretch")


def render_model_anomaly_chart(df, score_column, title, flag_column):
    """Render a model-specific anomaly score chart."""
    sample = df.sample(min(5000, len(df)), random_state=42)
    fig = px.scatter(
        sample,
        x="normalized_timestamp",
        y=score_column,
        color=flag_column,
        hover_data=["component", "parsed_message_type", "message"],
        title=title,
    )
    fig.update_layout(height=380)
    st.plotly_chart(fig, width="stretch")


def render_model_comparison_chart(metrics: pd.DataFrame):
    if metrics.empty:
        return
    plot_df = metrics[metrics["Model"] != "Ensemble (2/3)"].copy()
    fig = px.bar(
        plot_df,
        x="Model",
        y="Anomaly rate (%)",
        text="Anomaly rate (%)",
        title="Anomaly rate by model",
    )
    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig.update_layout(height=380, yaxis_title="Anomaly rate (%)")
    st.plotly_chart(fig, width="stretch")


def render_consensus_chart(df):
    counts = (
        df["anomaly_votes"]
        .value_counts()
        .reindex([0, 1, 2, 3], fill_value=0)
        .rename_axis("votes")
        .reset_index(name="records")
    )
    counts["votes"] = counts["votes"].map({0: "0 / 3", 1: "1 / 3", 2: "2 / 3", 3: "3 / 3"})
    fig = px.bar(
        counts,
        x="votes",
        y="records",
        text="records",
        title="Multi-model anomaly consensus",
    )
    fig.update_layout(height=380, xaxis_title="Models flagging the record")
    st.plotly_chart(fig, width="stretch")


def render_incident_timeline(incidents):
    if incidents.empty:
        return
    plot_df = incidents.copy()
    fig = px.timeline(
        plot_df,
        x_start="start_time",
        x_end="end_time",
        y="incident_id",
        color="severity",
        hover_data=["primary_component", "event_count", "anomaly_count"],
        title="Incident timeline",
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch")
