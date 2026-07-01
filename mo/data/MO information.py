import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from IPython.display import display
from gerrychain import Graph
import zipfile

# with zipfile.ZipFile("coi-preservation-project-main.zip", "r") as z:
#     z.extractall("coi_project")


# vtds = gpd.read_file("coi_project/coi-preservation-project-main/data/mo_2020_vtd/mo_2020.shp")


zip_path = r"C:\Users\EmuCl\Downloads\coi-preservation-project-main.zip"

with zipfile.ZipFile(zip_path, "r") as z:
    z.extractall(r"C:\Users\EmuCl\Downloads\coi_project")

vtds = gpd.read_file(r"C:\Users\EmuCl\Downloads\coi_project\coi-preservation-project-main\data\mo_2020_vtd\mo_2020.shp")
cois = gpd.read_file(r"C:\Users\EmuCl\Downloads\coi_project\coi-preservation-project-main\data\mo_2021_coi\MO_20210924_phase_C_summary.shp")

if cois.crs != vtds.crs:
    vtds = vtds.to_crs(cois.crs)

## need total pop column, add up presidential votes to get
pres_cols = ['G20PRERTRU', 'G20PREDBID', 'G20PRELJOR', 'G20PREGHAW', 'G20PRECBLA']
vtds['TOTPOP'] = vtds[pres_cols].sum(axis=1)

## now need coi fractions per vtd
# total vtd area
vtds['vtd_area'] = vtds.geometry.area

# what fraction of community resides here? coi area / total area
overlaps = gpd.overlay(vtds, cois, how='intersection')
overlaps['coi_fraction'] = overlaps.geometry.area / overlaps['vtd_area']

#display(overlaps[['NAME', 'cluster', 'coi_fraction', 'TOTPOP']].head(10))

# drop tiny overlaps
clean_overlaps = overlaps[overlaps['coi_fraction'] > 0.01].copy()

# figure out num people from overlaps pct
clean_overlaps['coi_pop'] = clean_overlaps['TOTPOP'] * clean_overlaps['coi_fraction']

coi_dict = {}
for index, row in clean_overlaps.iterrows():
    precinct_name = row['NAME']
    cluster_id = row['cluster']
    population_chunk = row['coi_pop']
    
    if precinct_name not in coi_dict:
        coi_dict[precinct_name] = {}
        
    coi_dict[precinct_name][cluster_id] = population_chunk

vtds['COI_POPS'] = [coi_dict.get(name, {}) for name in vtds['NAME']]

vtds.geometry = vtds.geometry.buffer(0)
g = Graph.from_geodataframe(vtds)

# print(vtds.columns)
# (vtds.head(1))
# display(vtds[['NAME', 'TOTPOP', 'COI_POPS']].head(100))

# coi_expanded = vtds['COI_POPS'].apply(pd.Series)
# export_df = pd.concat([vtds[['NAME', 'TOTPOP']], coi_expanded], axis=1)
# export_df.to_excel(r"C:\Users\EmuCl\Downloads\coi_output_wide.xlsx", index=False)

rows = []
for _, row in vtds.iterrows():
    for cluster_id, pop in row['COI_POPS'].items():
        rows.append({'NAME': row['NAME'], 'TOTPOP': row['TOTPOP'], 'cluster': cluster_id, 'coi_pop': pop})

# long_df = pd.DataFrame(rows)
# long_df.to_excel(r"C:\Users\EmuCl\Downloads\coi_output_long.xlsx", index=False)


# ===========================================================================
precincts = ["West Finley", "South Fork", "Polk", "Fairview"]



def plot_layered_bar(ax, x, precinct, sub, bar_width=0.6, show_legend=False):
    totpop = sub["TOTPOP"].iloc[0]
    sub = sub.sort_values("coi_pop", ascending=False)
    colors = cm.viridis_r(pd.Series(range(len(sub))) / max(len(sub) - 1, 1))

    layers = [("Total Population", totpop, "#cccccc")] + list(
        zip(sub["cluster"], sub["coi_pop"], colors)
    )
    for z, (label, value, color) in enumerate(layers):
        ax.bar(x, value, width=bar_width, color=color, zorder=z,
               label=label if show_legend else None)

    ax.text(x, -totpop * 0.03, precinct, ha="center", va="top", fontsize=9)

df = pd.DataFrame(rows)
#precincts = sorted(df["NAME"].unique())[:5]

fig, ax = plt.subplots(figsize=(2.5 * len(precincts) + 2, 6))

for x, precinct in enumerate(precincts):
    sub = df[df["NAME"] == precinct]
    if sub.empty:
        print(f"Warning: no rows found for '{precinct}'")
        continue
    plot_layered_bar(ax, x, precinct, sub, show_legend=(x == 0))

ax.set_xticks([])
ax.set_ylabel("Population")
ax.set_title("Total Population vs. COI Cluster Layers")
plt.tight_layout()
plt.savefig("layered_coi_chart_first10.png", dpi=150, bbox_inches="tight")
print("Saved chart")
plt.show()