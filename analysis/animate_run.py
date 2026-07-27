import os
import json
import gzip
import shutil
import pathlib
import subprocess
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from tqdm import tqdm

# CONFIG
STATE = "co"
GALLERY_PATH = "analysis/gallery/tcp/representable/cog/county_55_coi_0/colorado_cog_representable_simple_37_5_test_weights_250000_v1"

COI_MAP_PATH = "co/data/coi_maps/Colorado_communities_labeled.geojson"
GRAPH_JSON_PATH = "co/data/co_cog_representable.json"
VTD_MAP_PATH = "co/data/census_vtds/co.shp"

STEP_FREQ = 500
FPS = 15
OUTPUT_FILE = "representable_250k.mp4"


def get_base_and_diffs(gallery_path):
    p = pathlib.Path(gallery_path)
    if p.is_file() and p.suffix == ".gz":
        with gzip.open(p, "rt", encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
            base = json.loads(lines[0])
            diffs = [json.loads(line) for line in lines[1:]]
            return base, diffs
    else:
        base_path = p / "base_assignment.json"
        with open(base_path, "r", encoding="utf-8") as f:
            base = json.load(f)

        diffs_path = p / "diffs.jsonl.gz"
        if not diffs_path.exists():
            diffs_path = p / "diffs.jsonl"

        diffs = []
        if diffs_path.exists():
            opener = gzip.open if diffs_path.suffix == ".gz" else open
            mode = "rt" if diffs_path.suffix == ".gz" else "r"
            with opener(diffs_path, mode, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        diffs.append(json.loads(line))
        return base, diffs


def main():
    print("Loading geographic data...")
    vtds = gpd.read_file(VTD_MAP_PATH)
    cois = gpd.read_file(COI_MAP_PATH)
    if cois.crs != vtds.crs:
        cois = cois.to_crs(vtds.crs)

    ### universal coi id lookup to match init_data.py
    def get_coi_id(row):
        for col in ["entry_ID", "cluster", "GEOID", "OBJECTID"]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() and str(val) not in ("None", "nan"):
                return str(val).strip()
        return str(row.name)

    cois["coi_id"] = cois.apply(get_coi_id, axis=1)
    coi_id_col = "coi_id"

    print("Loading graph data...")
    with open(GRAPH_JSON_PATH, "r") as f:
        graph_data = json.load(f)

    nodes = graph_data["nodes"]

    print("Calculating COI total populations...")
    coi_totals = {}
    for node in nodes:
        if "COI_POPS" in node and node["COI_POPS"]:
            for coi_id, data in node["COI_POPS"].items():
                pop = data.get("pop", 0) if isinstance(data, dict) else data
                coi_totals[coi_id] = coi_totals.get(coi_id, 0) + pop

    print("Loading map assignments...")
    base_assignment, diffs = get_base_and_diffs(GALLERY_PATH)

    temp_dir = pathlib.Path("temp_frames")
    temp_dir.mkdir(exist_ok=True)

    for f in temp_dir.glob("*.png"):
        f.unlink()

    current_assignment = base_assignment.copy()

    node_coi_pops = []
    node_counties = []
    for i in range(len(nodes)):
        node_coi_pops.append(nodes[i].get("COI_POPS", {}))
        node_counties.append(nodes[i].get("COUNTYFP20", "Unknown"))

    num_steps = len(diffs) + 1

    target_steps = list(range(0, num_steps, STEP_FREQ))
    if target_steps[-1] != num_steps - 1:
        target_steps.append(num_steps - 1)

    target_step_set = set(target_steps)

    print(f"Generating {len(target_steps)} frames...")

    frame_idx = 0
    for step in tqdm(range(num_steps)):
        if step > 0:
            for key, val in diffs[step - 1].items():
                if isinstance(val, list):
                    # inverted diff: key is district, val is list of node ids
                    try:
                        dist_val = int(key)
                    except ValueError:
                        dist_val = key
                    for node in val:
                        current_assignment[str(node)] = dist_val
                else:
                    # standard diff: key is node id, val is district
                    current_assignment[key] = val

        if step in target_step_set:
            coi_dist_pops = {coi_id: {} for coi_id in coi_totals}
            for str_node, dist in current_assignment.items():
                node_idx = int(str_node)
                if node_coi_pops[node_idx]:
                    for coi_id, data in node_coi_pops[node_idx].items():
                        pop = data["pop"] if isinstance(data, dict) else data
                        coi_dist_pops[coi_id][dist] = (
                            coi_dist_pops[coi_id].get(dist, 0) + pop
                        )

            coi_sss = {}
            for coi_id, total_pop in coi_totals.items():
                if total_pop > 0:
                    sss = sum(
                        (dist_pop / total_pop) ** 2
                        for dist_pop in coi_dist_pops[coi_id].values()
                    )
                else:
                    sss = 0
                coi_sss[coi_id] = sss

            total_tcp_pop = sum(coi_totals.values())
            tcp = (
                sum(score * coi_totals[coi_id] for coi_id, score in coi_sss.items())
                / total_tcp_pop
                if total_tcp_pop
                else 0
            )

            county_districts = {}
            for str_node, dist in current_assignment.items():
                node_idx = int(str_node)
                county = node_counties[node_idx]
                if county not in county_districts:
                    county_districts[county] = set()
                county_districts[county].add(dist)
            splits = sum(1 for dists in county_districts.values() if len(dists) > 1)

            fig, ax = plt.subplots(figsize=(10, 10))
            ax.set_axis_off()
            ax.set_title(
                f"Step: {step:,}  |  TCP: {tcp:.4f}  |  County Splits: {splits}\nCommunity Preservation",
                fontsize=18,
            )

            cois["sss"] = cois[coi_id_col].map(coi_sss).fillna(0)

            cois.plot(
                ax=ax,
                column="sss",
                cmap="RdYlGn",
                vmin=0,
                vmax=1,
                edgecolor="black",
                linewidth=0.5,
                alpha=0.9,
            )

            vtds["district"] = vtds.index.map(
                lambda x: current_assignment.get(str(x), current_assignment.get(x))
            )
            districts = vtds.dissolve(by="district")
            districts.boundary.plot(ax=ax, edgecolor="black", linewidth=2)

            fig.tight_layout()
            frame_path = temp_dir / f"frame_{frame_idx:05d}.png"
            plt.savefig(frame_path, dpi=150, facecolor="white")
            plt.close(fig)
            frame_idx += 1

    print("Compiling video with FFmpeg...")
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(temp_dir / "frame_%05d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        OUTPUT_FILE,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg Error:\n", result.stderr)
    else:
        print(f"Animation saved to {OUTPUT_FILE} successfully!")

    shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
