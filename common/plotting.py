import pandas as pd
import numpy as np
import json

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import plotly.graph_objects as go

from common import scoring


### maps
def plot_partition(partition, vtds, cois, title):
    # map districts to df
    vtds["district"] = vtds.index.map(partition.assignment)

    fig, ax = plt.subplots(figsize=(12, 10))

    vtds.plot(
        ax=ax, column="district", cmap="Pastel1", edgecolor="black", linewidth=0.15
    )
    # cois.plot(ax=ax, column="cluster", facecolor='none', edgecolor="red", linewidth=0.15)

    if title:
        ax.set_title(title, fontsize=16)
    ax.axis("off")
    plt.show()


def plot_partition_party(partition, vtds, cois, title):
    # map districts to df
    vtds["district"] = vtds.index.map(partition.assignment)

    district_colors = {}
    most_dem_val = 0
    most_dem_district = None
    for district_id, node_ids in partition.parts.items():
        dem_pop = 0
        tot_pop = 0
        for node_id in node_ids:
            dem_pop += partition.graph.nodes[node_id]["PRE20D"]
            tot_pop += partition.graph.nodes[node_id]["TOTVOTES20"]

        if tot_pop > 0 and (dem_pop / tot_pop) > 0.5:
            district_colors[district_id] = "lightblue"
            if dem_pop / tot_pop > most_dem_val:
                most_dem_val = dem_pop / tot_pop
                district_colors[most_dem_district] = "lightblue"
                district_colors[district_id] = "dodgerblue"
                most_dem_district = district_id
        else:
            district_colors[district_id] = "lightcoral"

    vtds["party_color"] = vtds["district"].map(district_colors)

    fig, ax = plt.subplots(figsize=(12, 10))

    partition.plot(ax=ax, edgecolor="black", linewidth=2)
    vtds.plot(ax=ax, color=vtds["party_color"], edgecolor="black", linewidth=0.15)
    print(most_dem_val)

    if title:
        ax.set_title(title, fontsize=16)
    ax.axis("off")
    plt.show()


def plot_detailed(
    vtds_gdf,
    cois_gdf,
    community_scores_df,
    district_col,
    cluster_col="cluster",
    dem_vote_col="PRE20D",
    tot_vote_col="TOTVOTES20",
    title="Community Map",
):
    """
    generates an interactive plotly map with toggle buttons to switch
    between coi preservation (sss scores) and district partisanship.
    """
    ### init
    vtds_4326 = vtds_gdf.to_crs(epsg=4326)
    cois_4326 = cois_gdf.to_crs(epsg=4326)

    cois_4326.geometry = cois_4326.geometry.simplify(
        tolerance=0.001, preserve_topology=True
    )

    # get district lines
    vtds_4326.geometry = vtds_4326.geometry.make_valid()

    # dissolve and sum up the votes
    districts_4326 = vtds_4326.dissolve(
        by=district_col, aggfunc={dem_vote_col: "sum", tot_vote_col: "sum"}
    ).reset_index()

    # dem share and seats
    districts_4326["dem_share"] = (
        districts_4326[dem_vote_col] / districts_4326[tot_vote_col]
    )
    dem_seats = (districts_4326["dem_share"] > 0.5).sum()
    total_seats = len(districts_4326)

    cois_enriched = cois_4326.merge(
        community_scores_df[["community_id", "sss_score", "total_pop"]],
        left_on=cluster_col,
        right_on="community_id",
        how="left",
    )
    cois_enriched["sss_score"] = cois_enriched["sss_score"].fillna(0)
    cois_enriched["total_pop"] = cois_enriched["total_pop"].fillna(0)

    # calculate overall tcp score
    total_coi_pop = cois_enriched["total_pop"].sum()
    if total_coi_pop > 0:
        tcp_score = (
            cois_enriched["sss_score"] * cois_enriched["total_pop"]
        ).sum() / total_coi_pop
    else:
        tcp_score = 0.0

    # keep only cols needed for plotting
    coi_plot_cols = [cluster_col, "sss_score", "total_pop", "geometry"]
    if "community_id" in cois_enriched.columns and "community_id" != cluster_col:
        coi_plot_cols.append("community_id")
    cois_for_json = cois_enriched[
        [c for c in coi_plot_cols if c in cois_enriched.columns]
    ].copy()

    district_plot_cols = [district_col, dem_vote_col, tot_vote_col, "dem_share", "geometry"]
    districts_for_json = districts_4326[
        [c for c in district_plot_cols if c in districts_4326.columns]
    ].copy()

    # convert to json for plotting
    cois_geojson = json.loads(cois_for_json.to_json())
    districts_geojson = json.loads(districts_for_json.to_json())

    fig = go.Figure()

    ### trace 0: coi shapes
    fig.add_trace(
        go.Choroplethmap(
            geojson=cois_geojson,
            locations=cois_enriched.index,
            z=cois_enriched["sss_score"],
            text=cois_enriched[cluster_col],
            customdata=cois_enriched[["total_pop", "sss_score"]],
            colorscale="RdYlGn",
            zmin=0.0,
            zmax=1.0,
            showscale=True,
            colorbar_title="SSS Score",
            marker=dict(opacity=0.8, line=dict(width=0.4, color="black")),
            hovertemplate=(
                "<b>cluster id:</b> %{text}<br>"
                "<b>total population:</b> %{customdata[0]:,.0f}<br>"
                "<b>sss score:</b> %{customdata[1]:.4f}<extra></extra>"
            ),
            selected=dict(marker=dict(opacity=1.0)),
            unselected=dict(marker=dict(opacity=0.15)),
            visible=True,
        )
    )

    ### trace 1: black district borders for coi view
    fig.add_trace(
        go.Choroplethmap(
            geojson=districts_geojson,
            locations=districts_4326.index,
            z=[1] * len(districts_4326),
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            showscale=False,
            marker=dict(line=dict(width=3.0, color="black")),
            hoverinfo="skip",
            visible=True,
        )
    )

    ### trace 2: district partisan heat map
    fig.add_trace(
        go.Choroplethmap(
            geojson=districts_geojson,
            locations=districts_4326.index,
            z=districts_4326["dem_share"],
            text=districts_4326[district_col],
            customdata=districts_4326["dem_share"],
            colorscale="RdBu",
            zmin=0.2,
            zmax=0.8,
            zmid=0.5,
            showscale=True,
            colorbar_title="Dem Share",
            marker=dict(opacity=0.8, line=dict(width=2.5, color="black")),
            hovertemplate=(
                "<b>district:</b> %{text}<br>"
                "<b>democratic share:</b> %{customdata:.1%}<extra></extra>"
            ),
            visible=False,
        )
    )

    ### trace 3: coi shapes for partisan map
    fig.add_trace(
        go.Choroplethmap(
            geojson=cois_geojson,
            locations=cois_enriched.index,
            z=[1]
            * len(cois_enriched),  # dummy z array since we want a uniform flat color
            text=cois_enriched[cluster_col],
            customdata=cois_enriched[["total_pop", "sss_score"]],
            # translucent white fill
            colorscale=[[0, "rgba(255,255,255,0.15)"], [1, "rgba(255,255,255,0.15)"]],
            showscale=False,
            # faint black outlines
            marker=dict(opacity=1.0, line=dict(width=0.5, color="rgba(0,0,0,0.5)")),
            hoverinfo="skip",
            selected=dict(marker=dict(opacity=1.0)),
            unselected=dict(marker=dict(opacity=0.5)),
            visible=False,
        )
    )

    # center cam
    minx, miny, maxx, maxy = vtds_4326.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    full_title = f"{title}<br><sub>partisan outcome: {dem_seats}/{total_seats} dem seats won | tcp score: {tcp_score:.4f}</sub>"

    # build the toggle menu
    updatemenus = [
        dict(
            type="buttons",
            direction="right",
            active=0,
            x=0.5,
            y=1.05,
            xanchor="center",
            yanchor="bottom",
            buttons=list(
                [
                    dict(
                        label="COI Preservation Map",
                        method="update",
                        # trace index as args
                        args=[{"visible": [True, True, False, False]}],
                    ),
                    dict(
                        label="District Partisan Map",
                        method="update",
                        # hides trace 0 and 1, shows trace 2
                        args=[{"visible": [False, False, True, True]}],
                    ),
                ]
            ),
        )
    ]

    fig.update_layout(
        title=full_title,
        updatemenus=updatemenus,
        map_style="open-street-map",
        map_zoom=6,
        map_center={"lat": center_lat, "lon": center_lon},
        margin={"r": 0, "t": 90, "l": 0, "b": 0},
        height=800,
        clickmode="event+select",
    )

    import os
    if os.environ.get("PAPERMILL_RUN") != "True":
        fig.show()
    return cois_enriched


def plot_partition_detailed(
    partition, vtds_gdf, cois_gdf, title="Partition Map", cluster_col="cluster"
):
    """
    wrapper that extracts data from a gerrychain partition, scores it,
    maps it to the vtds, and passes it to the interactive plotly map func.
    """
    # extract data and score
    df_part = scoring.extract_data(partition)
    community_scores = scoring.score_communities(df_part)

    # map to temp col
    temp_col = "temp_plot_district"
    vtds_gdf[temp_col] = vtds_gdf.index.map(partition.assignment)

    # wrapped function, pass everything in
    plot_detailed(
        vtds_gdf=vtds_gdf,
        cois_gdf=cois_gdf,
        community_scores_df=community_scores,
        district_col=temp_col,
        cluster_col=cluster_col,
        title=title,
    )
    # delete temp call
    vtds_gdf.drop(columns=[temp_col], inplace=True)


### plots
def plot_tcp_distribution(df, initial_score=None, enacted_data=None, steps_str=""):
    plt.figure(figsize=(8, 5))
    plt.hist(df["weighted_tcp_score"], bins=50, edgecolor="black", alpha=0.7)

    if initial_score is not None:
        plt.axvline(
            initial_score,
            color="grey",
            linestyle="dashed",
            linewidth=2,
            label=f"Initial: {initial_score:.3f}",
        )

    if enacted_data:
        colors = ["blue", "red", "green", "purple"]
        for i, (label, data) in enumerate(enacted_data.items()):
            score = data.get("score")
            if score is not None:
                plt.axvline(
                    score,
                    color=colors[i % len(colors)],
                    linestyle="dashed",
                    linewidth=2,
                    label=f"{label}: {score:.3f}",
                )

    title = f"Distribution of TCP Scores" + (
        f" ({steps_str} Steps)" if steps_str else ""
    )
    plt.title(title)
    plt.xlabel("Total COI Preservation (Weighted TCP)")
    plt.ylabel("Frequency")
    plt.legend()
    plt.show()


def plot_dem_wins_distribution(df, initial_wins=None, enacted_data=None, steps_str=""):
    n_districts = df.filter(like="dist_").shape[1]
    plt.figure(figsize=(8, 5))
    plt.hist(
        df["dem_wins"],
        bins=np.arange(-0.5, n_districts + 1.5, 1),
        alpha=0.7,
    )

    if initial_wins is not None:
        plt.axvline(
            x=initial_wins,
            color="grey",
            linestyle="dashed",
            label=f"Initial Wins ({initial_wins})",
        )

    if enacted_data:
        colors = ["blue", "red", "green", "purple"]
        for i, (label, data) in enumerate(enacted_data.items()):
            wins = data.get("wins")
            if wins is not None:
                plt.axvline(
                    x=wins,
                    color=colors[i % len(colors)],
                    linestyle="dashed",
                    linewidth=2,
                    label=f"{label}: {wins}",
                )

    plt.xticks(range(n_districts + 1))
    title = f"Distribution of Dem Wins" + (
        f" over {steps_str} Steps" if steps_str else ""
    )
    plt.title(title)
    plt.xlabel("Dem Seats")
    plt.ylabel("Frequency")
    plt.legend()
    plt.show()


def plot_tcp_by_seat_count(df, enacted_data=None, desired_tcp=None):
    n_districts = df.filter(like="dist_").shape[1]
    seats_with_data = [
        s for s in range(n_districts + 1) if len(df[df["dem_wins"] == s]) > 0
    ]
    data_to_plot = [
        df[df["dem_wins"] == s]["weighted_tcp_score"] for s in seats_with_data
    ]

    plt.figure(figsize=(10, 6))
    plt.boxplot(data_to_plot, tick_labels=seats_with_data)

    if enacted_data:
        colors = ["blue", "red", "green", "purple"]
        for i, (label, data) in enumerate(enacted_data.items()):
            score = data.get("score")
            wins = data.get("wins")
            if score is not None:
                win_text = f" ({wins} seats)" if wins is not None else ""
                plt.axhline(
                    score,
                    color=colors[i % len(colors)],
                    linestyle="dashed",
                    label=f"{label}{win_text}",
                )

    if desired_tcp is not None:
        plt.axhline(
            desired_tcp, color="lightgrey", linestyle="dashed", label="Mean/Target"
        )

    plt.xlabel("Dem Seats Won")
    plt.ylabel("TCP Score")
    plt.title("Distribution of TCP Scores by Seat Count")
    plt.legend()
    plt.show()


def plot_partisan_shift(df, score_col="weighted_tcp_score", top_q=0.80, bottom_q=0.20):
    top_cutoff = df[score_col].quantile(top_q)
    bottom_cutoff = df[score_col].quantile(bottom_q)

    high_maps = df[df[score_col] >= top_cutoff]
    low_maps = df[df[score_col] <= bottom_cutoff]

    n_districts = df.filter(like="dist_").shape[1]
    share_cols = [f"dist_{i}_dem_share" for i in range(1, n_districts + 1)]

    data_high = [high_maps[col] for col in share_cols]
    data_low = [low_maps[col] for col in share_cols]

    fig, ax = plt.subplots(figsize=(14, 7))

    pos_low = np.arange(1, n_districts + 1) - 0.15
    pos_high = np.arange(1, n_districts + 1) + 0.15

    ax.boxplot(
        data_low,
        positions=pos_low,
        widths=0.25,
        patch_artist=True,
        boxprops=dict(facecolor="lightcoral", color="black"),
        medianprops=dict(color="black", linewidth=1.5),
    )

    ax.boxplot(
        data_high,
        positions=pos_high,
        widths=0.25,
        patch_artist=True,
        boxprops=dict(facecolor="lightgreen", color="black"),
        medianprops=dict(color="black", linewidth=1.5),
    )

    ax.axhline(
        0.5, color="red", linestyle="dashed", linewidth=2, label="50% Win Threshold"
    )
    ax.set_xticks(range(1, n_districts + 1))
    ax.set_xticklabels([f"Dist {i}" for i in range(1, n_districts + 1)])
    ax.set_title("How Preserving Communities Shifts the Vote Share", fontsize=16)
    ax.set_xlabel("District (Ranked)")
    ax.set_ylabel("Democratic Vote Share")

    legend_elements = [
        Patch(
            facecolor="lightcoral",
            edgecolor="black",
            label=f"Low TCP Maps (Worst {int(bottom_q * 100)}%)",
        ),
        Patch(
            facecolor="lightgreen",
            edgecolor="black",
            label=f"High TCP Maps (Best {int((1 - top_q) * 100)}%)",
        ),
    ]
    ax.legend(handles=legend_elements, loc="upper left")
    plt.show()


def plot_mix(
    csv_a,
    csv_b,
    label_a="csv_a",
    label_b="csv_b",
    share_col_prefix="dist_",
    title="Democratic Vote Share Comparison",
):
    """Plot democratic vote-share distributions from two CSV files or dataframes."""

    def _coerce_frame(data):
        if isinstance(data, pd.DataFrame):
            return data.copy()
        if isinstance(data, str):
            return pd.read_csv(data)
        raise TypeError("Expected a pandas DataFrame or a CSV file path")

    df_a = _coerce_frame(csv_a)
    df_b = _coerce_frame(csv_b)

    share_cols_a = [
        col for col in df_a.columns if col.startswith(share_col_prefix) and col.endswith("_dem_share")
    ]
    share_cols_b = [
        col for col in df_b.columns if col.startswith(share_col_prefix) and col.endswith("_dem_share")
    ]

    if not share_cols_a or not share_cols_b:
        raise ValueError("No district dem-share columns found in the provided data")

    if len(share_cols_a) != len(share_cols_b):
        raise ValueError("The two inputs must contain the same number of district dem-share columns")

    data_a = [df_a[col].dropna() for col in share_cols_a]
    data_b = [df_b[col].dropna() for col in share_cols_b]

    fig, ax = plt.subplots(figsize=(14, 7))

    pos_a = np.arange(1, len(share_cols_a) + 1) - 0.15
    pos_b = np.arange(1, len(share_cols_b) + 1) + 0.15

    ax.boxplot(
        data_a,
        positions=pos_a,
        widths=0.25,
        patch_artist=True,
        boxprops=dict(facecolor="lightcoral", color="black"),
        medianprops=dict(color="black", linewidth=1.5),
    )

    ax.boxplot(
        data_b,
        positions=pos_b,
        widths=0.25,
        patch_artist=True,
        boxprops=dict(facecolor="lightgreen", color="black"),
        medianprops=dict(color="black", linewidth=1.5),
    )

    ax.axhline(0.5, color="red", linestyle="dashed", linewidth=2, label="50% Win Threshold")
    ax.set_xticks(range(1, len(share_cols_a) + 1))
    ax.set_xticklabels([f"Dist {i}" for i in range(1, len(share_cols_a) + 1)])
    ax.set_title(title, fontsize=16)
    ax.set_xlabel("District")
    ax.set_ylabel("Democratic Vote Share")

    legend_elements = [
        Patch(facecolor="lightcoral", edgecolor="black", label=label_a),
        Patch(facecolor="lightgreen", edgecolor="black", label=label_b),
    ]
    ax.legend(handles=legend_elements, loc="upper left")
    plt.show()


### new plots
