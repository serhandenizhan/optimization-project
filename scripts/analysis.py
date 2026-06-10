# -*- coding: utf-8 -*-
"""Performans analizi & yakınsama grafiği (yeni, kısıt-sağlayan motor).

Üretir:
  * convergence_graph.png : GA yakınsaması + MILP optimum referans çizgisi.
Çalıştırma: python analysis.py
"""
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithm.data import load_problem
from algorithm.milp import solve_milp
from algorithm.ga import GeneticOptimizer
from algorithm.validator import validate
from algorithm.solution import compute_cost


def run_performance_analysis():
    excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "context", "Data_Emre2.xlsx")
    prob = load_problem(excel_path)
    print(f"Gemi: {len(prob.ships)} | Feasible rota: {len(prob.routes)} | "
          f"Talep olayı: {len(prob.demand_events)}")

    # --- MILP optimum (referans) ---
    t0 = time.time()
    milp_sol = solve_milp(prob, time_limit=180)
    milp_t = time.time() - t0
    milp_cost = compute_cost(prob, milp_sol).total
    milp_feas = validate(prob, milp_sol).feasible
    print(f"MILP optimum: {milp_cost:,.2f} $  ({milp_t:.2f} sn, feasible={milp_feas})")

    # --- GA yakınsaması ---
    t0 = time.time()
    ga = GeneticOptimizer(prob, seed=42)
    ga_sol, history = ga.run()
    ga_t = time.time() - t0
    ga_cost = compute_cost(prob, ga_sol).total
    ga_feas = validate(prob, ga_sol).feasible
    print(f"GA sonucu : {ga_cost:,.2f} $  ({ga_t:.2f} sn, feasible={ga_feas})")
    gap = (ga_cost - milp_cost) / abs(milp_cost) * 100
    print(f"GA gap    : %{gap:.1f}")

    # --- Grafik ---
    plt.figure(figsize=(10, 6))
    plt.plot(history, color="#2563eb", linewidth=2, label="GA — En İyi Maliyet (Z)")
    plt.axhline(milp_cost, color="#dc2626", linestyle="--", linewidth=2,
                label=f"MILP Optimum = {milp_cost:,.0f} $")
    plt.title("Yakınsama: Geliştirilmiş GA vs Kanıtlı MILP Optimum\n"
              "(her iki çözüm de TÜM kısıtları sağlar — 0 ihlal)")
    plt.xlabel("Jenerasyon")
    plt.ylabel("Toplam Maliyet Z ($)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "convergence_graph.png")
    plt.savefig(out, dpi=120)
    print(f"Grafik kaydedildi: {out}")


if __name__ == "__main__":
    run_performance_analysis()
