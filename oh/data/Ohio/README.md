# Ohio

## `png/`

A heatmap of each cluster, showing county boundaries (gray lines). Shows the largest connected component (by block count) of the blocks involved in the cluster. Insets are available for clusters that cover less than some percentage of the state's land area.

## `png_summary/`

This map of the state shows the number of each cluster placed at the weighted center of the full cluster.

## `shapefile_coi/`

This shapefile contains 986 polygons, one for each "area of interest" scraped from the portal up to the end of August. (We scraped 9/1 around midnight.) The key is a 4-digit [portal ID](https://portal.ohio-mapping.org/) with a suffix (-1, -2, ...) to denote each polygon in a submission. 

## `shapefile_summary/`

This shapefile includes 22 polygons—one for each of the 22 C clusters. The key is the cluster ID, such as C14. (No other attributes; no subclusters are available for Ohio.)


## `submission_db.csv`

A database of COI portal submissions (with approximate block group/block representations) used to generate geoclusters.
