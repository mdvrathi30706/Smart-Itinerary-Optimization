import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from optimization.solver import solve_mtsp

# Streamlit page setup
st.set_page_config(page_title="Smart Itinerary Optimizer", layout="wide")

# -------------------------------
# Load Data
# -------------------------------
@st.cache_data
def load_data():
    attractions = pd.read_csv("data/delhi_attractions.csv")
    distances = pd.read_csv("data/delhi_distance_matrix.csv", index_col=0)
    return attractions, distances

attractions, distances = load_data()

# -------------------------------
# Sidebar Inputs
# -------------------------------
st.sidebar.title("⚙️ Trip Preferences")
days = st.sidebar.slider("Number of Travel Days", 1, 5, 3)
budget_day = st.sidebar.number_input("Budget per Day (₹)", 100, 10000, 1500, step=100)
time_day = st.sidebar.slider("Available Time per Day (hours)", 4.0, 12.0, 8.0, step=0.5)

st.sidebar.subheader("🎯 Theme Preferences (weights 0–1)")
food = st.sidebar.slider("Food", 0.0, 1.0, 0.3)
adventure = st.sidebar.slider("Adventure", 0.0, 1.0, 0.1)
culture = st.sidebar.slider("Culture", 0.0, 1.0, 0.3)
history = st.sidebar.slider("History", 0.0, 1.0, 0.3)

weights = {"food": food, "adventure": adventure, "culture": culture, "history": history}

run_button = st.sidebar.button("🧭 Generate Optimized Itinerary")

# -------------------------------
# Initialize session state
# -------------------------------
if "itinerary" not in st.session_state:
    st.session_state["itinerary"] = None
    st.session_state["metrics"] = None

# -------------------------------
# App Header and Base Map
# -------------------------------
st.title("🧳 Smart Travel Itinerary Optimizer — Delhi")
st.write("Optimize multi-day routes subject to time and budget limits. (Hard budget enforced)")

st.subheader("📍 Explore Attractions (Delhi)")
base_map = folium.Map(location=[28.6139, 77.2090], zoom_start=12)
cat_colors = {"food": "orange", "culture": "blue", "history": "green", "adventure": "purple"}

for _, row in attractions.iterrows():
    color = cat_colors.get(row["category"], "gray")
    popup = (
        f"<b>{row['name']}</b><br>"
        f"Category: {row['category']}<br>"
        f"Avg time: {row['avg_time_hr']} hr<br>"
        f"Entry fee: ₹{row['entry_fee']}<br>"
        f"Fun: {row['fun_score']}"
    )
    folium.Marker(
        [row["latitude"], row["longitude"]],
        popup=popup,
        tooltip=row["name"],
        icon=folium.Icon(color=color),
    ).add_to(base_map)

st_folium(base_map, width=900, height=450)

# -------------------------------
# Run Optimization on Button Click
# -------------------------------
if run_button:
    with st.spinner("🔍 Running M-TSP optimizer... (this may take up to a minute)"):
        # NOTE: call matches current solver signature (no alpha/beta arguments)
        itinerary, total_cost, total_fun, total_distance = solve_mtsp(
            attractions,
            distances,
            days=days,
            budget_day=budget_day,
            time_day=time_day,
            weights=weights,
            avg_speed_kmph=20.0,
            time_limit_seconds=60
        )

    # Save results in session_state
    st.session_state["itinerary"] = itinerary
    st.session_state["metrics"] = (total_cost, total_fun, total_distance)
    st.success("✅ Optimization finished! Scroll down to view your itinerary.")

# -------------------------------
# Display Results if Available
# -------------------------------
if st.session_state["itinerary"] is not None:
    itinerary = st.session_state["itinerary"]
    total_cost, total_fun, total_distance = st.session_state["metrics"]

    # Show metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total Cost", f"₹{int(total_cost)}")
    c2.metric("🎯 Total Fun Score", round(total_fun, 2))
    c3.metric("🛣️ Total Distance", f"{round(total_distance, 1)} km")

    # Show day-wise itineraries
    st.header("📅 Day-wise Itinerary")
    for d, route in enumerate(itinerary, start=1):
        st.subheader(f"Day {d}")
        if route:
            st.write(" → ".join(route))
        else:
            st.write("_No attractions assigned for this day._")

    # Map visualization of routes
    st.header("🗺️ Optimized Route Map")
    m = folium.Map(location=[28.6139, 77.2090], zoom_start=12)
    colors = ["red", "blue", "green", "purple", "orange", "cadetblue", "darkred"]

    lat_lng_points = []
    for day_idx, route in enumerate(itinerary):
        color = colors[day_idx % len(colors)]
        if not route:
            continue

        for i in range(len(route)):
            a = attractions[attractions["name"] == route[i]].iloc[0]
            lat_lng_points.append((a["latitude"], a["longitude"]))
            folium.Marker(
                [a["latitude"], a["longitude"]],
                popup=f"Day {day_idx+1}: {a['name']}",
                icon=folium.Icon(color=color),
            ).add_to(m)

            if i < len(route) - 1:
                b = attractions[attractions["name"] == route[i+1]].iloc[0]
                folium.PolyLine(
                    [[a["latitude"], a["longitude"]], [b["latitude"], b["longitude"]]],
                    color=color, weight=4, opacity=0.8,
                ).add_to(m)

    # Auto-fit map bounds to all visited attractions
    if lat_lng_points:
        m.fit_bounds(lat_lng_points)

    st_folium(m, width=900, height=600)

else:
    st.info("👈 Configure preferences in the sidebar and click 'Generate Optimized Itinerary'.")
