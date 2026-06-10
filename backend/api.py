from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Yeni, kısıt-sağlayan optimizasyon paketimiz
from algorithm.data import load_problem
from algorithm.milp import solve_milp
from algorithm.ga import GeneticOptimizer
from algorithm.validator import validate
from algorithm.solution import compute_cost

app = FastAPI(title="ENS001 Gemi Rotalama Optimizasyon API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL = os.path.join(BASE_DIR, "context", "Data_Emre2.xlsx")


@app.get("/")
def read_root():
    return {"message": "ENS001 Optimizasyon Motoru v2 aktif. /api/optimize kullanın."}


@app.get("/api/optimize")
def run_optimization():
    """Kesin MILP ile feasible+optimal planı, GA ile yakınsama geçmişini döner."""
    prob = load_problem(EXCEL)

    # Kanıtlı optimum (garantili feasible) çözüm
    milp_sol = solve_milp(prob, time_limit=120)
    report = validate(prob, milp_sol)          # bağımsız doğrulama
    cb = compute_cost(prob, milp_sol)

    # Animasyonlu yakınsama grafiği için GA geçmişi
    ga = GeneticOptimizer(prob, seed=42)
    _, history = ga.run()

    # Frontend'in haritada çizebilmesi için rota verisi
    routes_data = []
    events = prob.demand_events
    load_by_route = {}
    for i, rid in milp_sol.event_assignment.items():
        load_by_route[rid] = load_by_route.get(rid, 0.0) + events[i].qty

    for r in milp_sol.routes_flat():
        ship = prob.ships_by_id[r.ship_id]
        stops = [r.start_port, *r.customers, r.end_port]
        routes_data.append({
            "route_id": r.route_id,
            "ship_id": r.ship_id,
            "capacity": ship.capacity,
            "total_load": round(load_by_route.get(r.route_id, 0.0), 1),
            "stops": stops,
            "cost": round(r.cost, 2),
            "duration": r.duration,
            "region": r.region,
        })

    return {
        "status": "success",
        "feasible": report.feasible,
        "violations": report.violations,
        "final_cost": round(cb.total, 2),
        "cost_breakdown": {
            "route_cost": round(cb.route_cost, 2),
            "operating_cost": round(cb.operating_cost, 2),
            "idle_penalty": round(cb.idle_penalty, 2),
            "rental_income": round(cb.rental_income, 2),
        },
        "history": [round(h, 2) for h in history],
        "routes": routes_data,
    }
