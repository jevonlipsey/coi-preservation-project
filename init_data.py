import os
import geopandas as gpd
import pandas as pd
import networkx as nx
from gerrychain import Graph
from pathlib import Path

### config
TARGET_STATES = ["co"]  # "mo", "co", or both
DIST_LEVELS = ["cog", "ss", "sh"]  # district levels for co

# coi map paths (relative to script location)
CO_COI_MAP_DIR = Path("co/data/coi-maps")
MO_COI_MAP_PATH = Path("mo/data/mo_2021_coi/MO_20210924_phase_C_summary.shp")

# directories for generated graph jsons
CO_COI_GRAPH_DIR = Path("co/data/coi-graphs")
MO_COI_GRAPH_DIR = Path("mo/data")

# coi maps to process for co
CO_COI_MAPS = {
    "people_based": "people_based.geojson",
    "superclean": "superclean.geojson",
}
MO_COI_MAP_NAME = "aggregated"


def init_mo(coi_map_path, coi_map_name="aggregated"):
    print(f"initializing mo (coi_map: {coi_map_name})...")
    vtds = gpd.read_file(Path("mo/data/mo-aggregated/mo.shp"))
    cois = gpd.read_file(Path(coi_map_path))

    subclusters = cois[cois["cluster"].str.contains("-")]
    parents_to_drop = subclusters["cluster"].apply(lambda x: x.split("-")[0]).unique()
    cois = cois[~cois["cluster"].isin(parents_to_drop)]

    if cois.crs != vtds.crs:
        cois = cois.to_crs(vtds.crs)

    vtds["TOTVOTES20"] = vtds["PRE20D"] + vtds["PRE20R"] + vtds["PRE20O"]
    vtds["vtd_area"] = vtds.geometry.area

    overlaps = gpd.overlay(vtds, cois, how="intersection")
    overlaps["coi_fraction"] = overlaps.geometry.area / overlaps["vtd_area"]
    clean_overlaps = overlaps[overlaps["coi_fraction"] > 0.01].copy()
    clean_overlaps["coi_pop"] = (
        clean_overlaps["TOTPOP"] * clean_overlaps["coi_fraction"]
    )

    coi_dict = {}
    for index, row in clean_overlaps.iterrows():
        vtd_name = row["NAME20"]
        cluster_id = row.get("cluster")
        if pd.isna(cluster_id) or not str(cluster_id).strip() or str(cluster_id) in ("None", "nan"):
            cluster_id = row.get("GEOID", row.get("OBJECTID", str(index)))
        cluster_id = str(cluster_id)
        population_chunk = row["coi_pop"]

        if vtd_name not in coi_dict:
            coi_dict[vtd_name] = {}

        coi_dict[vtd_name][cluster_id] = {
            "pop": population_chunk,
            "category": "coi",
        }

    vtds["COI_POPS"] = [coi_dict.get(name, {}) for name in vtds["NAME20"]]

    congressional_2025 = gpd.read_file(
        Path("mo/data/mo_2025_congressional/HB1_Cong_Dist_2025.shp")
    )
    congressional_2022 = gpd.read_file(
        Path("mo/data/mo_2022_congressional/tl_2022_29_cd118.shp")
    )

    congressional_2025 = congressional_2025.to_crs(vtds.crs)
    congressional_2022 = congressional_2022.to_crs(vtds.crs)

    vtd_points = vtds.copy()
    vtd_points.geometry = vtd_points.representative_point()

    joined_vtds_2025 = gpd.sjoin(
        vtd_points, congressional_2025, how="left", predicate="intersects"
    )
    joined_vtds_2022 = gpd.sjoin(
        vtd_points, congressional_2022, how="left", predicate="intersects"
    )

    vtds["district_2025"] = joined_vtds_2025["District"]
    vtds["district_2022"] = joined_vtds_2022["CD118FP"].astype(int, errors="ignore")

    vtds.geometry = vtds.geometry.buffer(0)
    g = Graph.from_geodataframe(vtds)

    out_path = Path(f"mo/data/mo_cog_{coi_map_name}.json")
    g.to_json(out_path.as_posix())
    print(f"mo initialized and graph saved to {out_path}")


def init_co(coi_map_path, dist_level="cog", coi_map_name="graph"):
    print(f"initializing co ({dist_level}, coi_map: {coi_map_name})...")
    vtds = gpd.read_file(Path("co/data/census_vtds/co.shp"))
    coi_map_path = Path(coi_map_path)
    if not coi_map_path.exists():
        coi_map_path = CO_COI_MAP_DIR / coi_map_path.name
    cois = gpd.read_file(coi_map_path)

    if cois.crs != vtds.crs:
        cois = cois.to_crs(vtds.crs)

    vtds["TOTVOTES20"] = vtds["PRE20D"] + vtds["PRE20R"] + vtds["PRE20O"]
    vtds["vtd_area"] = vtds.geometry.area

    overlaps = gpd.overlay(vtds, cois, how="intersection")
    overlaps["coi_fraction"] = overlaps.geometry.area / overlaps["vtd_area"]
    clean_overlaps = overlaps[overlaps["coi_fraction"] > 0.01].copy()
    clean_overlaps["coi_pop"] = (
        clean_overlaps["TOTPOP"] * clean_overlaps["coi_fraction"]
    )

    coi_dict = {}
    for index, row in clean_overlaps.iterrows():
        vtd_name = row["NAME20"]
        cluster_id = row.get("entry_ID")
        if pd.isna(cluster_id) or not str(cluster_id).strip() or str(cluster_id) in ("None", "nan"):
            cluster_id = row.get("GEOID", row.get("OBJECTID", str(index)))
        cluster_id = str(cluster_id)
        population_chunk = row["coi_pop"]

        if vtd_name not in coi_dict:
            coi_dict[vtd_name] = {}

        coi_dict[vtd_name][cluster_id] = {
            "pop": population_chunk,
            "category": "coi",
        }

    vtds["COI_POPS"] = [coi_dict.get(name, {}) for name in vtds["NAME20"]]

    if dist_level == "cog":
        dist_2021 = gpd.read_file(
            Path(
                "co/data/2021_Approved_Congressional_Plan_with_Final_Adjustments/2021_Approved_Congressional_Plan_with_Final_Adjustments/2021_Approved_Congressional_Plan_w_Final_Adjustments.shp"
            )
        )
    elif dist_level == "ss":
        dist_2021 = gpd.read_file(
            Path(
                "co/data/2021_Approved_Senate_Plan_w_Final_Adjustments/2021_Approved_Senate_Plan_w_Final_Adjustments/2021_Approved_Senate_Plan_w_Final_Adjustments.shp"
            )
        )
    elif dist_level == "sh":
        dist_2021 = gpd.read_file(
            Path(
                "co/data/2021_Approved_House_Plan_w_Final_Adjustments/2021_Approved_House_Plan_w_Final_Adjustments/2021_Approved_House_Plan_w_Final_Adjustments.shp"
            )
        )

    dist_2021 = dist_2021.to_crs(vtds.crs)
    vtd_points = vtds.copy()
    vtd_points.geometry = vtd_points.representative_point()
    joined_vtds_2021 = gpd.sjoin(
        vtd_points, dist_2021, how="left", predicate="intersects"
    )
    vtds["district_2021"] = joined_vtds_2021["District"]

    vtds.geometry = vtds.geometry.buffer(0)
    g = Graph.from_geodataframe(vtds)

    CO_COI_GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CO_COI_GRAPH_DIR / f"co_{dist_level}_{coi_map_name}.json"
    g.to_json(out_path.as_posix())
    print(f"co initialized and graph saved to {out_path}")


if __name__ == "__main__":
    if "mo" in TARGET_STATES:
        init_mo(coi_map_path=MO_COI_MAP_PATH, coi_map_name=MO_COI_MAP_NAME)
    if "co" in TARGET_STATES:
        for level in DIST_LEVELS:
            for map_name, filename in CO_COI_MAPS.items():
                init_co(
                    coi_map_path=CO_COI_MAP_DIR / filename,
                    dist_level=level,
                    coi_map_name=map_name,
                )
