import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.risk_engine import calculate_priority

st.set_page_config(page_title="AquaMind V0.1", page_icon="💧", layout="wide")

DATA_PATH = "data/pipes_v01.csv"
NODES_PATH = "data/nodes_v01.csv"

LEVEL_COLORS = {
    "Alta": "#d62728",
    "Media": "#f2c14e",
    "Baja": "#2ca02c",
}


@st.cache_data
def load_data():
    pipes = pd.read_csv(DATA_PATH)
    nodes = pd.read_csv(NODES_PATH)
    return pipes, nodes


def build_network_figure(df, nodes, selected_id=None):
    fig = go.Figure()

    for level in ["Baja", "Media", "Alta"]:
        subset = df[df["priority_level"] == level]
        xs, ys = [], []

        for _, row in subset.iterrows():
            xs.extend([row["x1"], row["x2"], None])
            ys.extend([row["y1"], row["y2"], None])

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color=LEVEL_COLORS[level], width=6),
                name=f"Prioridad {level.lower()}",
                hoverinfo="skip",
            )
        )

    mid_x = ((df["x1"] + df["x2"]) / 2).tolist()
    mid_y = ((df["y1"] + df["y2"]) / 2).tolist()

    hover_text = [
        (
            f"<b>{r.tramo_id}</b><br>"
            f"Prioridad: {r.priority_level} ({r.priority_score:.1f}/100)<br>"
            f"Presión: {r.pressure_psi if pd.notna(r.pressure_psi) else 'N/D'} psi<br>"
            f"Caudal: {r.flow_lps if pd.notna(r.flow_lps) else 'N/D'} L/s<br>"
            f"Diámetro: {r.diameter_in}\"<br>"
            f"Longitud: {r.length_m} m<br>"
            f"Calidad de datos: {r.data_completeness:.0f}%"
        )
        for r in df.itertuples()
    ]

    fig.add_trace(
        go.Scatter(
            x=mid_x,
            y=mid_y,
            mode="markers",
            marker=dict(
                size=9,
                color=[LEVEL_COLORS[x] for x in df["priority_level"]],
                line=dict(width=1, color="white"),
            ),
            text=hover_text,
            hovertemplate="%{text}<extra></extra>",
            name="Tramos",
            showlegend=False,
        )
    )

    visible_nodes = set(df["node_u"]).union(set(df["node_v"]))
    nodes_plot = nodes[nodes["node_id"].isin(visible_nodes)]

    fig.add_trace(
        go.Scatter(
            x=nodes_plot["x"],
            y=nodes_plot["y"],
            mode="markers",
            marker=dict(size=8, color="#1f2937"),
            text=nodes_plot["node_id"],
            hovertemplate="<b>Nodo %{text}</b><extra></extra>",
            name="Nodos",
        )
    )

    if selected_id is not None:
        selected = df[df["tramo_id"] == selected_id]

        if not selected.empty:
            r = selected.iloc[0]

            fig.add_trace(
                go.Scatter(
                    x=[r["x1"], r["x2"]],
                    y=[r["y1"], r["y2"]],
                    mode="lines",
                    line=dict(color="#111827", width=12),
                    hoverinfo="skip",
                    name="Seleccionado",
                )
            )

    fig.update_layout(
        height=560,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(visible=False, scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
        ),
    )

    return fig


st.title("💧 AquaMind V0.1")
st.caption(
    "Prueba de concepto para priorizar inspecciones en redes hidráulicas con "
    "datos sintéticos. No es un sistema validado de detección de fugas."
)

try:
    raw_df, nodes_df = load_data()
except FileNotFoundError:
    st.error(
        "No encontré los archivos de datos. Ejecuta primero: "
        "`python src/generate_data.py`"
    )
    st.stop()

st.sidebar.header("Metodología V0.1")
st.sidebar.caption(
    "Los pesos son provisionales y editables. Se normalizan automáticamente."
)

w_leaks = st.sidebar.slider("Historial de fugas", 0, 50, 30)
w_age = st.sidebar.slider("Antigüedad", 0, 50, 20)
w_pressure = st.sidebar.slider("Presión", 0, 50, 20)
w_velocity = st.sidebar.slider("Velocidad", 0, 50, 15)
w_material = st.sidebar.slider("Material", 0, 50, 15)

weights = {
    "historical_leaks": w_leaks,
    "age_years": w_age,
    "pressure_psi": w_pressure,
    "velocity_ms": w_velocity,
    "material": w_material,
}

df = calculate_priority(raw_df, weights)

sectors = ["Todos"] + sorted(df["sector"].dropna().unique().tolist())
sector = st.sidebar.selectbox("Sector", sectors)

view = df.copy() if sector == "Todos" else df[df["sector"] == sector].copy()

if view.empty:
    st.warning("No hay tramos para el sector seleccionado.")
    st.stop()

selected_id = st.selectbox(
    "Selecciona un tramo para inspeccionarlo",
    view.sort_values("priority_score", ascending=False)["tramo_id"].tolist(),
)

selected = view[view["tramo_id"] == selected_id].iloc[0]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Tramos analizados", len(view))
m2.metric("Prioridad promedio", f"{view['priority_score'].mean():.1f}/100")
m3.metric("Prioridad alta", int((view["priority_level"] == "Alta").sum()))
m4.metric(
    "Calidad media de datos",
    f"{view['data_completeness'].mean():.0f}%",
)

left, right = st.columns([1.7, 1])

with left:
    st.subheader("Red hidráulica sintética")
    st.plotly_chart(
        build_network_figure(view, nodes_df, selected_id),
        use_container_width=True,
    )
    st.caption(
        "Los colores representan prioridad relativa dentro de la red analizada: "
        "verde = baja, amarillo = media, rojo = alta."
    )

with right:
    st.subheader(f"Tramo {selected['tramo_id']}")
    st.metric(
        "Índice de prioridad",
        f"{selected['priority_score']:.1f}/100",
        selected["priority_level"],
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Presión",
        f"{selected['pressure_psi']:.1f} psi"
        if pd.notna(selected["pressure_psi"])
        else "N/D",
    )
    c2.metric(
        "Caudal",
        f"{selected['flow_lps']:.2f} L/s"
        if pd.notna(selected["flow_lps"])
        else "N/D",
    )
    c1.metric("Diámetro", f'{selected["diameter_in"]:.0f}"')
    c2.metric("Longitud", f"{selected['length_m']:.1f} m")
    c1.metric(
        "Velocidad",
        f"{selected['velocity_ms']:.2f} m/s"
        if pd.notna(selected["velocity_ms"])
        else "N/D",
    )
    c2.metric(
        "Calidad de datos",
        f"{selected['data_completeness']:.0f}%",
    )

    st.write(f"**Sector:** {selected['sector']}")
    st.write(
        f"**Material:** "
        f"{selected['material'] if pd.notna(selected['material']) else 'N/D'}"
    )

    if pd.notna(selected["age_years"]):
        st.write(f"**Antigüedad:** {int(selected['age_years'])} años")
    else:
        st.write("**Antigüedad:** N/D")

    st.write(
        f"**Factores que más aportan al índice:** "
        f"{selected['main_factors']}"
    )
    st.write(
        f"**Confianza de datos:** {selected['data_confidence']}"
    )

    if selected["missing_fields"]:
        st.warning(f"Datos faltantes: {selected['missing_fields']}")
    else:
        st.success(
            "Este tramo tiene completas las variables consideradas en la V0.1."
        )

st.subheader("Tramos prioritarios")

table = view.sort_values(
    "priority_score",
    ascending=False,
)[
    [
        "tramo_id",
        "sector",
        "priority_score",
        "priority_level",
        "pressure_psi",
        "flow_lps",
        "velocity_ms",
        "diameter_in",
        "length_m",
        "data_completeness",
        "main_factors",
    ]
].head(15)

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
)

csv = view.to_csv(index=False).encode("utf-8")

st.download_button(
    "Descargar resultados CSV",
    data=csv,
    file_name="aquamind_v01_resultados.csv",
    mime="text/csv",
)

with st.expander("Metodología y limitaciones de esta V0.1"):
    st.markdown(
        """
        - **No es machine learning ni un detector de fugas validado.**
        - El índice es un **baseline heurístico y explicable** para probar el flujo de decisión.
        - Los pesos son provisionales y pueden modificarse en la barra lateral.
        - Los datos son sintéticos e incluyen valores faltantes de forma intencional.
        - La **confianza de datos** mide completitud de información, no probabilidad estadística de que exista una fuga.
        - Diámetro y caudal se utilizan para calcular velocidad. Longitud y sector se muestran como contexto.
        - El siguiente paso es validar variables y metodología con especialistas y posteriormente con una red real o experimental.
        """
    )
