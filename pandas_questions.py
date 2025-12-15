"""
Plotting referendum results in pandas.

In short, we want to make a beautiful map to report results of a referendum.
We load the data as pandas.DataFrame, merge the info, aggregate them by
regions, and finally plot them on a map using geopandas.
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt


def load_data():
    """Load data from the CSV files referendum/regions/departments."""
    referendum = pd.read_csv("data/referendum.csv", sep=";")
    regions = pd.read_csv("data/regions.csv")
    departments = pd.read_csv("data/departments.csv")

    return referendum, regions, departments


def merge_regions_and_departments(regions, departments):
    """Merge regions and departments in one DataFrame.

    Final columns:
    ['code_reg', 'name_reg', 'code_dep', 'name_dep']
    """
    regions = regions.copy()
    departments = departments.copy()

    regions["code"] = regions["code"].astype(str)
    departments["region_code"] = departments["region_code"].astype(str)

    regions_df = regions.rename(
        columns={"code": "code_reg", "name": "name_reg"}
    )[["code_reg", "name_reg"]]

    departments_df = departments.rename(
        columns={"code": "code_dep", "name": "name_dep"}
    )[["region_code", "code_dep", "name_dep"]]

    merged = departments_df.merge(
        regions_df,
        left_on="region_code",
        right_on="code_reg",
        how="left",
    )

    return merged[["code_reg", "name_reg", "code_dep", "name_dep"]]


def merge_referendum_and_areas(referendum, regions_and_departments):
    """Merge referendum data with region/department information.

    Drop DOM-TOM-COM departments and French living abroad
    (codes containing 'Z').
    """
    ref = referendum.copy()
    regs_deps = regions_and_departments.copy()

    regs_deps["code_dep_str"] = (
        regs_deps["code_dep"].astype(str).str.lstrip("0")
    )
    ref["code_dep_str"] = ref["Department code"].astype(str)

    merged = ref.merge(
        regs_deps,
        left_on="code_dep_str",
        right_on="code_dep_str",
        how="left",
        validate="m:1",
    )

    columns = [
        "Department code",
        "Department name",
        "Town code",
        "Town name",
        "Registered",
        "Abstentions",
        "Null",
        "Choice A",
        "Choice B",
        "code_dep",
        "code_reg",
        "name_reg",
        "name_dep",
    ]

    merged = merged[columns].dropna()

    mask_z = merged["code_dep"].astype(str).str.contains("Z")
    merged = merged.loc[~mask_z]

    return merged


def compute_referendum_result_by_regions(referendum_and_areas):
    """Return absolute counts aggregated by region.

    Index: code_reg
    Columns:
    ['name_reg', 'Registered', 'Abstentions', 'Null', 'Choice A', 'Choice B']
    """
    df = referendum_and_areas.copy()

    aggregated = df.groupby("code_reg").agg(
        name_reg=("name_reg", "first"),
        Registered=("Registered", "sum"),
        Abstentions=("Abstentions", "sum"),
        Null=("Null", "sum"),
        Choice_A=("Choice A", "sum"),
        Choice_B=("Choice B", "sum"),
    )

    aggregated.rename(
        columns={"Choice_A": "Choice A", "Choice_B": "Choice B"},
        inplace=True,
    )

    exclude = {"01", "02", "03", "04", "06", "COM"}
    aggregated = aggregated.loc[~aggregated.index.isin(exclude)]

    aggregated.index.name = "code_reg"

    return aggregated


def plot_referendum_map(referendum_result_by_regions):
    """Plot a map showing Choice A ratio by region.

    Returns a GeoDataFrame with a 'ratio' column.
    """
    gdf_regions = gpd.read_file("data/regions.geojson")

    if "code" in gdf_regions.columns:
        gdf_regions["code"] = gdf_regions["code"].astype(str)
        left_key = "code"
    elif "code_reg" in gdf_regions.columns:
        gdf_regions["code_reg"] = gdf_regions["code_reg"].astype(str)
        left_key = "code_reg"
    else:
        left_key = None

    results = referendum_result_by_regions.reset_index()
    results["code_reg"] = results["code_reg"].astype(str)

    if left_key:
        gdf = gdf_regions.merge(
            results,
            left_on=left_key,
            right_on="code_reg",
            how="left",
        )
    else:
        gdf = gdf_regions.merge(
            results,
            left_on="name",
            right_on="name_reg",
            how="left",
        )

    gdf["ratio"] = gdf["Choice A"] / (
        gdf["Choice A"] + gdf["Choice B"]
    )

    gdf.plot()

    return gdf


if __name__ == "__main__":
    referendum, df_regions, df_departments = load_data()

    regions_departments = merge_regions_and_departments(
        df_regions,
        df_departments,
    )

    referendum_areas = merge_referendum_and_areas(
        referendum,
        regions_departments,
    )

    referendum_results = compute_referendum_result_by_regions(
        referendum_areas,
    )

    print(referendum_results)

    plot_referendum_map(referendum_results)
    plt.show()
