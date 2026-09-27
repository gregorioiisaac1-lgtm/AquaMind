import os

import numpy as np
import pandas as pd


def generate_synthetic_network(seed=42, rows=6, cols=6):
    rng = np.random.default_rng(seed)

    nodes = []
    for r in range(rows):
        for c in range(cols):
            node_id = f"N{r * cols + c + 1:02d}"
            nodes.append(
                {
                    "node_id": node_id,
                    "x": c,
                    "y": rows - 1 - r,
                }
            )

    nodes_df = pd.DataFrame(nodes)

    edges = []
    tramo_number = 1

    def get_node(node_id):
        return nodes_df[nodes_df["node_id"] == node_id].iloc[0]

    def add_edge(node_u, node_v):
        nonlocal tramo_number

        u = get_node(node_u)
        v = get_node(node_v)

        material = rng.choice(
            [
                "Asbesto-Cemento",
                "Hierro Fundido",
                "Acero",
                "PVC",
                "Polietileno",
            ],
            p=[0.15, 0.20, 0.20, 0.30, 0.15],
        )

        age_years = int(rng.integers(8, 76))
        diameter_in = int(
            rng.choice(
                [4, 6, 8, 10, 12, 16],
                p=[0.12, 0.18, 0.25, 0.18, 0.17, 0.10],
            )
        )

        pressure_psi = float(np.clip(rng.normal(55, 14), 20, 100))
        flow_lps = float(np.clip(rng.normal(11, 5), 1, 30))
        historical_leaks = int(rng.poisson(1.0))
        length_m = float(rng.uniform(70, 120))

        avg_y = (float(u["y"]) + float(v["y"])) / 2
        if avg_y >= 3.5:
            sector = "Norte"
        elif avg_y >= 1.5:
            sector = "Centro"
        else:
            sector = "Sur"

        edges.append(
            {
                "tramo_id": f"T-{tramo_number:03d}",
                "node_u": node_u,
                "node_v": node_v,
                "x1": float(u["x"]),
                "y1": float(u["y"]),
                "x2": float(v["x"]),
                "y2": float(v["y"]),
                "length_m": round(length_m, 1),
                "diameter_in": diameter_in,
                "material": material,
                "age_years": age_years,
                "pressure_psi": round(pressure_psi, 1),
                "flow_lps": round(flow_lps, 2),
                "historical_leaks": historical_leaks,
                "sector": sector,
            }
        )

        tramo_number += 1

    # Red tipo malla: 36 nodos y 60 tramos.
    for r in range(rows):
        for c in range(cols):
            current = f"N{r * cols + c + 1:02d}"

            if c < cols - 1:
                right = f"N{r * cols + c + 2:02d}"
                add_edge(current, right)

            if r < rows - 1:
                down = f"N{(r + 1) * cols + c + 1:02d}"
                add_edge(current, down)

    pipes_df = pd.DataFrame(edges)

    # Datos faltantes deliberados para simular redes con información incompleta.
    missing_fraction = {
        "age_years": 0.12,
        "material": 0.08,
        "pressure_psi": 0.18,
        "flow_lps": 0.22,
        "historical_leaks": 0.10,
    }

    for column, fraction in missing_fraction.items():
        count = max(1, int(len(pipes_df) * fraction))
        missing_index = rng.choice(
            pipes_df.index,
            size=count,
            replace=False,
        )
        pipes_df.loc[missing_index, column] = np.nan

    return nodes_df, pipes_df


def main():
    nodes_df, pipes_df = generate_synthetic_network()

    os.makedirs("data", exist_ok=True)

    nodes_path = "data/nodes_v01.csv"
    pipes_path = "data/pipes_v01.csv"

    nodes_df.to_csv(nodes_path, index=False)
    pipes_df.to_csv(pipes_path, index=False)

    print(f"Se generaron {len(nodes_df)} nodos en {nodes_path}")
    print(f"Se generaron {len(pipes_df)} tramos en {pipes_path}")


if __name__ == "__main__":
    main()
