# -*- coding: utf-8 -*-
#
# Interpolation Methods with ArcPy
# Luke Zaruba
# GIS 5572: ArcGIS II - Lab 3
# 2023-04-06
#

import pandas as pd
import requests
import arcpy
import arcgis
import os

# For Type Annotations
from os import PathLike
from pandas import DataFrame, Series


class WeatherLoader:
    """
    A class used to extract and transform daily MN weather data automatically.

    Methods
    -------
    extract()
        Runs the extraction process for the data and returns as either JSON or DataFrame.
    _extractColumn(field)
        Static, private method. Used for converting JSON to DataFrame.
    transform()
        Performs QAQC Process on DataFrame.
    aggregate()
        Aggregates and calculates average values for stations.
    load()
        Loads to geodatabase.

    Example
    -------
    > weather_etl = WeatherLoader(r"out_gdb_path", 3, 2022)
    > raw_df = weather_etl.extract()
    > transformed_df = weather_etl.transform()
    > aggregated_df = weather_etl.aggregate()
    > weather_etl.load()
    """

    def __init__(self, geodatabase: PathLike, month=1, year=2023):
        """_summary_

        Args:
            geodatabase (PathLike): _description_
            month (int, optional): _description_. Defaults to 1.
            year (int, optional): _description_. Defaults to 2023.
        """
        self.geodatabase = geodatabase
        self.month = month
        self.year = year

        self.fc = f"aggMthWX_{self.month}{self.year}"

        # Set Base URL
        self.url = r"https://mesonet.agron.iastate.edu/api/1/daily.geojson?network=MN_RWIS&month=_M_&year=_Y_".replace(
            "_M_", str(self.month)
        ).replace(
            "_Y_", str(self.year)
        )

    def extract(self) -> DataFrame:
        """_summary_

        Returns:
            DataFrame: _description_
        """
        # Get Response & Convert to DF
        response = requests.get(self.url)
        json = response.json()["features"]
        df_raw = pd.DataFrame.from_records(json)

        # Series Conversion from Dicts to Actual Vals
        desiredSeries = ["station", "date", "max_tmpf", "min_tmpf", "precip", "name"]

        for s in desiredSeries:
            self._extractToCol(df_raw, s)

        # Extract Geometries
        df_raw["x"] = df_raw["geometry"].apply(lambda x: dict(x)["coordinates"][0])
        df_raw["y"] = df_raw["geometry"].apply(lambda x: dict(x)["coordinates"][1])

        # Copy Useful Columns to new DF
        self.df = df_raw[
            ["station", "date", "max_tmpf", "min_tmpf", "precip", "name", "x", "y"]
        ].copy()

        # Return DF
        return self.df

    @staticmethod
    def _extractToCol(df: DataFrame, field: Series) -> Series:
        """Function to extract fields from dicts that are columns in DF.

        Args:
            df (DataFrame): _description_
            field (Series): _description_

        Returns:
            Series: _description_
        """
        df[field] = df["properties"].apply(lambda x: dict(x)[field])

    def transform(self) -> DataFrame:
        """_summary_

        Returns:
            DataFrame: _description_
        """
        # Fill NA Precip Values
        self.df["precip"].fillna(0, inplace=True)

        # Drop Rows where 'precip' < 0
        self.df = self.df.loc[self.df["precip"] >= 0]

        # Drop Rows with Null 'Latitude' or 'Longitude'
        self.df = self.df.dropna(subset=["x", "y", "max_tmpf", "min_tmpf"])

        # Convert Data Types
        self.df["station"] = self.df["station"].astype(str)
        self.df["name"] = self.df["name"].astype(str)
        self.df["date"] = self.df["date"].astype("datetime64[ns]")

        # Drop Rows where Lat/Lon are Outside MN BBox
        self.df = self.df.loc[self.df["x"] > -97.5]
        self.df = self.df.loc[self.df["x"] < -89.0]
        self.df = self.df.loc[self.df["y"] > 43.0]
        self.df = self.df.loc[self.df["y"] < 49.5]

        # Return DF
        return self.df

    def aggregate(self) -> DataFrame:
        """_summary_

        Returns:
            DataFrame: _description_
        """
        # Define Aggregate Functions
        agg_functions = {
            "station": "first",
            "name": "first",
            "x": "first",
            "y": "first",
            "max_tmpf": "mean",
            "min_tmpf": "mean",
            "precip": "mean",
        }

        # Perform Aggregation
        self.aggregated_df = self.df.groupby(self.df["station"]).aggregate(
            agg_functions
        )

        # Return DF
        return self.aggregated_df

    def load(self):
        # Convert Weather Observations from DF to SEDF
        self.sedf = arcgis.GeoAccessor.from_xy(self.aggregated_df, "x", "y")

        # Convert Weather Observations from SEDF to FC
        self.sedf.spatial.to_featureclass(
            location=os.path.join(self.geodatabase, self.fc)
        )
