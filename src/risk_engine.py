import numpy as np
import pandas as pd

MATERIAL_RISK = {
    "Asbesto-Cemento": 1.00,
    "Hierro Fundido": 0.80,
    "Acero": 0.60,
    "PVC": 0.35,
    "Polietileno": 0.20,
}

FACTOR_LABELS = {
    "historical_leaks": "historial de fugas",
    "age_years": "antigüedad",
    "pressure_psi": "presión",
    "velocity_ms": "velocidad",
    "material": "material",
}

RAW_DATA_FIELDS = [
    "age_years",
    "material",
    "pressure_psi",
    "flow_lps",
    "historical_leaks",
]


def normalize(series):
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty:
        return pd.Series(0.5, index=series.index)

    minimum = s.min(skipna=True)
    maximum = s.max(skipna=True)

    if maximum == minimum:
        return pd.Series(0.5, index=series.index)

    return (s - minimum) / (maximum - minimum)


def calculate_velocity(flow_lps, diameter_in):
    """
    Convierte:
      caudal: L/s -> m3/s
      diámetro: pulgadas -> m
    y calcula v = Q / A.
    """
    q_m3s = pd.to_numeric(flow_lps, errors="coerce") / 1000.0
    d_m = pd.to_numeric(diameter_in, errors="coerce") * 0.0254
    area_m2 = np.pi * (d_m ** 2) / 4.0
    return q_m3s / area_m2


def calculate_priority(df, weights=None):
    out = df.copy()

    if weights is None:
        weights = {
            "historical_leaks": 30,
            "age_years": 20,
            "pressure_psi": 20,
            "velocity_ms": 15,
            "material": 15,
        }

    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("La suma de los pesos debe ser mayor que cero.")

    weights = {key: value / total_weight for key, value in weights.items()}

    out["velocity_ms"] = calculate_velocity(
        out["flow_lps"],
        out["diameter_in"],
    ).round(2)

    # Completitud de datos. NO es probabilidad de fuga.
    out["data_completeness"] = (
        out[RAW_DATA_FIELDS].notna().mean(axis=1) * 100
    ).round(0)

    out["data_confidence"] = pd.cut(
        out["data_completeness"],
        bins=[-1, 59, 79, 101],
        labels=["Baja", "Media", "Alta"],
    ).astype(str)

    field_names = {
        "age_years": "antigüedad",
        "material": "material",
        "pressure_psi": "presión",
        "flow_lps": "caudal",
        "historical_leaks": "historial de fugas",
    }

    out["missing_fields"] = out[RAW_DATA_FIELDS].apply(
        lambda row: ", ".join(
            field_names[col]
            for col in RAW_DATA_FIELDS
            if pd.isna(row[col])
        ),
        axis=1,
    )

    factors = pd.DataFrame(index=out.index)
    factors["historical_leaks"] = normalize(out["historical_leaks"])
    factors["age_years"] = normalize(out["age_years"])
    factors["pressure_psi"] = normalize(out["pressure_psi"])
    factors["velocity_ms"] = normalize(out["velocity_ms"])
    factors["material"] = out["material"].map(MATERIAL_RISK)

    # Los faltantes se rellenan con la mediana para que no se vuelvan
    # artificialmente "seguros" o "peligrosos".
    for col in factors.columns:
        median = factors[col].median(skipna=True)
        if pd.isna(median):
            median = 0.5
        factors[col] = factors[col].fillna(median)

    contributions = pd.DataFrame(index=out.index)
    for col in factors.columns:
        contributions[col] = factors[col] * weights[col]

    out["priority_score"] = (contributions.sum(axis=1) * 100).round(1)

    def top_factors(idx):
        ordered = contributions.loc[idx].sort_values(ascending=False)
        return " + ".join(FACTOR_LABELS[key] for key in ordered.index[:2])

    out["main_factors"] = [top_factors(idx) for idx in out.index]

    # Prioridad RELATIVA: 20% superior = alta, siguiente 30% = media.
    percentile = out["priority_score"].rank(method="average", pct=True)
    out["priority_level"] = np.select(
        [percentile >= 0.80, percentile >= 0.50],
        ["Alta", "Media"],
        default="Baja",
    )

    return out.sort_values(
        "priority_score",
        ascending=False,
    ).reset_index(drop=True)
