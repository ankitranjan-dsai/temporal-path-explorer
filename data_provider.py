# Credit: B (load_temporal_file, clean_temporal_data); A (load_temporal_upload, sample CSV, verbose, integration).
# Integrated from: teammate_deliverables/B/b_new_pipeline.ipynb → data_provider.py
# Role: Load temporal edge tables from CSV/JSON; clean to SRC/TGT/Unix (+ edge_id, datetime) for UI and data_adj.

import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# Repo-root sample graph: demo_data.csv (same file can be uploaded from disk to test).
DEMO_DATA_CSV = Path(__file__).resolve().parent / "demo_data.csv"
DEMO_DATA_FILENAME = "demo_data.csv"


# --- Teammate B: temporal table load & clean (canonical: SRC, TGT, Unix, edge_id, datetime) ---


def load_temporal_file(file_path: str) -> pd.DataFrame:
    """
    Load temporal network data from CSV or JSON.
    Required logical columns: SRC, TGT, Unix
    """
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)

    elif file_path.endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            df = pd.DataFrame(data)

        elif isinstance(data, dict):
            if "edges" in data:
                df = pd.DataFrame(data["edges"])
            else:
                df = pd.DataFrame(data)
        else:
            raise ValueError("Unsupported JSON structure.")

    else:
        raise ValueError("Unsupported file format. Use CSV or JSON.")

    col_map = {}
    for col in df.columns:
        c = str(col).strip().lower()
        if c in ["src", "source", "from"]:
            col_map[col] = "SRC"
        elif c in ["tgt", "target", "to"]:
            col_map[col] = "TGT"
        elif c in ["unix", "time", "timestamp", "t"]:
            col_map[col] = "Unix"

    df = df.rename(columns=col_map)

    required = {"SRC", "TGT", "Unix"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"Missing required columns. Found columns: {df.columns.tolist()}. "
            f"Required columns: SRC, TGT, Unix"
        )

    return df[["SRC", "TGT", "Unix"]]


def load_temporal_upload(uploaded_file: Any) -> pd.DataFrame:
    """
    Same contract as load_temporal_file for st.file_uploader() buffers.
    """
    name = (getattr(uploaded_file, "name", None) or "").lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith(".json"):
        data = json.load(uploaded_file)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            if "edges" in data:
                df = pd.DataFrame(data["edges"])
            else:
                df = pd.DataFrame(data)
        else:
            raise ValueError("Unsupported JSON structure.")
    else:
        raise ValueError("Unsupported file format. Use CSV or JSON.")

    col_map = {}
    for col in df.columns:
        c = str(col).strip().lower()
        if c in ["src", "source", "from"]:
            col_map[col] = "SRC"
        elif c in ["tgt", "target", "to"]:
            col_map[col] = "TGT"
        elif c in ["unix", "time", "timestamp", "t"]:
            col_map[col] = "Unix"

    df = df.rename(columns=col_map)
    required = {"SRC", "TGT", "Unix"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"Missing required columns. Found columns: {df.columns.tolist()}. "
            f"Required columns: SRC, TGT, Unix"
        )
    return df[["SRC", "TGT", "Unix"]]


def clean_temporal_data(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Sort, dedupe, add edge_id and datetime. Original B prints optional via verbose."""
    t0 = time.time()
    df = df.copy()

    df["SRC"] = df["SRC"].astype(str).str.strip()
    df["TGT"] = df["TGT"].astype(str).str.strip()
    df["Unix"] = pd.to_numeric(df["Unix"], errors="coerce")

    before_invalid = len(df)
    df = df.dropna(subset=["SRC", "TGT", "Unix"])
    invalid_removed = before_invalid - len(df)

    df["Unix"] = df["Unix"].astype(int)

    before_dup = len(df)
    df = df.drop_duplicates(subset=["SRC", "TGT", "Unix"])
    duplicates_removed = before_dup - len(df)

    df = df.sort_values(by=["Unix", "SRC", "TGT"]).reset_index(drop=True)

    df.insert(0, "edge_id", [f"e{str(i).zfill(7)}" for i in range(1, len(df) + 1)])

    df["datetime"] = pd.to_datetime(df["Unix"], unit="s")

    if verbose:
        print("Cleaning completed.")
        print("Rows after cleaning:", len(df))
        print("Invalid rows removed:", invalid_removed)
        print("Duplicates removed:", duplicates_removed)
        print("Time taken (seconds):", round(time.time() - t0, 3))

    return df


# --- Built-in sample graph: ~20 nodes, moderate edge count ---


def _load_example_data() -> pd.DataFrame:
    """~20 nodes, ring + random chords, Unix 0..15 (small integers as timestamps)."""
    rng = random.Random(42)
    nodes = [f"v{i}" for i in range(1, 21)]
    rows: List[Dict[str, Any]] = []
    t = 0
    for i in range(20):
        u, v = nodes[i], nodes[(i + 1) % 20]
        rows.append({"source": u, "target": v, "time": int(t)})
        t += 1
    for _ in range(28):
        u, v = rng.sample(nodes, 2)
        rows.append({"source": u, "target": v, "time": int(rng.randint(0, 15))})
    return pd.DataFrame.from_records(rows)


def load_example_canonical_cleaned() -> pd.DataFrame:
    """Sample temporal graph (~20 nodes): prefer ``demo_data.csv`` beside this package; else embedded rows."""
    if DEMO_DATA_CSV.is_file():
        raw = load_temporal_file(str(DEMO_DATA_CSV))
        return clean_temporal_data(raw, verbose=False)
    raw = _load_example_data().rename(columns={"source": "SRC", "target": "TGT", "time": "Unix"})
    return clean_temporal_data(raw, verbose=False)


def demo_source_label() -> str:
    """Short label for UI when user loads built-in sample data."""
    return DEMO_DATA_FILENAME if DEMO_DATA_CSV.is_file() else "Built-in sample (embedded)"
