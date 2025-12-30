# Smart Travel Itinerary Optimizer

> **An Operations Management project** that generates optimized multi-day travel itineraries based on user preferences, time, and budget — powered by optimization algorithms and visualized with interactive maps.

---

## Overview

The **Smart Travel Itinerary Optimizer** creates customized travel plans for a single city.  
Given user inputs such as total days, daily time, and budget, the system uses a **multi-day Traveling Salesman Problem (M-TSP)** formulation to generate an itinerary that **maximizes total enjoyment** while respecting real-world constraints.

The tool is built using:
-  **OR-Tools** (CBC Solver) for optimization  
-  **Folium** for interactive map visualization  
-  **Streamlit** for the user interface  

---

## Key Features

- **Mathematical Optimization (M-TSP)**
  - Formulated as a Mixed Integer Linear Program (MILP)
  - Uses fun scores, entry fees, and distances between attractions
  - Balances enjoyment with travel distance via a tunable weight `α`

-  **User Constraints**
  - Daily time and budget limits
  - Each attraction can be visited at most once
  - Flow constraints ensure realistic connectivity between attractions

-  **Balanced Objective**
  - Maximize: Σ fun[i]·y[i,d] – α·Σ dist[i,j]·x[i,j,d]
  - where `α` controls the trade-off between fun and spatial compactness.

-  **Interactive Map Output**
- Each day’s route is color-coded
- Attractions shown with category-based markers
- Route paths drawn dynamically using Folium

-  **Realistic Cost Modeling**
- Entry fees per attraction  
- Travel cost (₹/km) computed from route distances

---

##  Methodology

1. **Input Stage** (via Streamlit)
 - City dataset selection (currently Delhi)
 - Travel days, budget/day, available hours/day
 - Thematic weights (Food, Adventure, Culture, History)
 - Optional parameters: travel cost per km, distance weight α

2. **Optimization Engine**
 - Formulates and solves a Multi-Day Traveling Salesman Problem
 - Decision variables:
   - `y[i,d]` → whether attraction *i* is visited on day *d*
   - `x[i,j,d]` → whether the route goes from *i* to *j* on day *d*
 - Constraints:
   - Time ≤ available hours per day
   - Budget ≤ daily budget
   - Each attraction visited at most once
   - Flow consistency & MTZ subtour elimination

3. **Output Stage**
 - Day-wise itinerary
 - Total fun score, total distance, and total cost
 - Interactive map of optimized routes

---

##  Dataset

The optimizer currently supports **Delhi** as a sample dataset.

- `data/delhi_attractions.csv`  
Contains: name, latitude, longitude, avg_time_hr, entry_fee, fun_score, category

- `data/delhi_distance_matrix.csv`  
Square matrix of distances (in km) between each attraction.

> You can easily extend to other cities by adding new CSVs in the same format.

---

##  Project Structure

Smart-Itinerary-Optimization/
│
├── app.py # Streamlit UI
├── optimization/
│ └── solver.py # OR-Tools M-TSP solver
├── data/
│ ├── delhi_attractions.csv # Places dataset
│ └── delhi_distance_matrix.csv # Distance matrix
├── requirements.txt # Dependencies
└── README.md # Project documentation

---

##  Mathematical Model Summary

**Decision Variables:**
| Symbol | Description |
|---------|--------------|
| `x[i,j,d]` | 1 if we travel from attraction *i* to *j* on day *d* |
| `y[i,d]` | 1 if attraction *i* is visited on day *d* |
| `u[i,d]` | Position index of attraction *i* in day *d* (MTZ variable) |

**Objective:**
\[
\max \sum_{d,i} fun_i y_{id} - \alpha \sum_{d,i,j} dist_{ij} x_{ijd}
\]

**Constraints:**
1. `in_sum + out_sum ≥ y[i,d]`  — connectivity if visited  
2. `in_sum + out_sum ≤ 2·y[i,d]` — at most one in and one out  
3. `Σ_d y[i,d] ≤ 1`  — each attraction visited at most once  
4. Time limit per day  
5. Budget limit per day  
6. MTZ subtour elimination  

---

##  Installation & Setup

### Clone the Repository
```bash
git clone https://github.com/mdvrathi30706/Smart-Itinerary-Optimization.git
cd Smart-Itinerary-Optimization
pip install -r requirements.txt
streamlit run app.py
```
then open the app in your browser

---

##  Future Enhancements

- Add hotel/depot node for daily round trips
- Extend to multiple cities / state-level optimization
- Integrate live Google Maps API for real distance matrix
- Deploy Streamlit app online for user access
- Use Gurobi/CPLEX for faster optimality proofs
- Add local 2-opt heuristic for route refinement


