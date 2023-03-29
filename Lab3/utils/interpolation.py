# -*- coding: utf-8 -*-
#
# Interpolation Methods with ArcPy
#
# Luke Zaruba
# GIS 5572: ArcGIS II - Lab 3
# 2023-04-06
#
import arcpy
import os
import pandas as pd

# For Type Annotations
from typing import Union
from pandas import DataFrame
from os import PathLike


class Interpolator:
    """
    A class used to run a pipeline of interpolation and accuracy assessments automatically.

    Methods
    -------
    run_exploratory_interpolation()
        Runs the exploratory interpolation tool and generates results for best-performing model.
    display()
        Displays accuracy assessment from the run_exploratory_interpolation() tool.
    create_point_accuracy_layer()
        Calculates difference from actual to interpolated values at known points.
    convert_results_to_hex()
        Converts the geostats interpolation layer to H3 hexagons.
    export_to_sde()
        Exports dataset to PostgreSQL database that is connected to via SDE connection.
    """

    def __init__(
        self,
        point_feature_class: PathLike,
        output_directory: PathLike,
        value_of_interest: str,
    ) -> None:
        """Instantiates the Interpolator class.

        Args:
            point_feature_class (PathLike): Path to an input point feature class that will be interpolated.
            output_directory (PathLike): Directory that will store the outputs.
            value_of_interest (str): Value in the input point feature class that will be interpolated.
        """
        self.point_feature_class = point_feature_class
        self.output_directory = output_directory
        self.value_of_interest = value_of_interest

        # Define Other Paths
        self.feature_name = self.point_feature_class.split(r"/")[-1]
        self.stats_table = os.path.join(
            self.output_directory, f"{self.feature_name}_stats.csv"
        )
        self.geostats_layer = os.path.join(
            self.output_directory, f"{self.feature_name}_bestInterpolator"
        )
        self.interpolation_methods = ["ORDINARY_KRIGING", "EBK", "IDW"]

    def run_exploratory_interpolation(self) -> None:
        """Runs the exploratory interpolation tool and generates results for best-performing model."""
        # Run exploratory Interpolation
        arcpy.ga.ExploratoryInterpolation(
            self.point_feature_class,
            self.value_of_interest,
            self.stats_table,
            self.geostats_layer,
            self.interpolation_methods,
            "SINGLE",
            "ACCURACY",
        )

        # Message
        print(
            f"""
            Exploratory interpolation successfully ran.
            Best result saved at: {self.geostats_layer}
            Results table saved at: {self.stats_table}
            """
        )

    def display(self, display_method: str) -> Union[str, DataFrame]:
        """Displays accuracy assessment from the run_exploratory_interpolation() tool.

        Args:
            display_method (str): Method that will be used to display the data.

        Raises:
            ValueError: Raised if display_method is not valid option.
            TypeError: Raised if display_method is not of type str.

        Returns:
            Union[str, DataFrame]: Either string or DataFrame is returned.
        """
        # Read Table into DF
        df = pd.read_csv(self.stats_table)

        # Display based on Method
        if display_method == "PRINT":
            return print(df)

        elif display_method == "DATAFRAME":
            return df

        # Raise Errors for Invalid Method Param
        else:
            if type(display_method) == str:
                raise ValueError(
                    "Param 'display_method' must be in ['PRINT', 'DATAFRAME']"
                )
            else:
                raise TypeError(
                    "Param 'display_method' must be of type string and value of ['PRINT', 'DATAFRAME']"
                )

    def create_point_accuracy_layer(self, geodatabase: PathLike) -> None:
        """Calculates difference from actual to interpolated values at known points.

        Args:
            geodatabase (PathLike): Path to the geodatabase where the output will be stored.
        """
        # Extract Values of Geostats Layer to Points
        self.point_accuracy_path = os.path.join(
            geodatabase, f"{self.feature_name}_point_diff"
        )

        arcpy.ga.GALayerToPoints(
            self.geostats_layer, self.point_feature_class, self.point_accuracy_path
        )

        # Message
        print(f"Point accuracy successfully generated at: {self.point_accuracy_path}")

    def convert_results_to_hex(self, geodatabase: PathLike, res=6) -> None:
        """Converts the geostats interpolation layer to H3 hexagons.

        Args:
            geodatabase (PathLike): Path to the geodatabase where the output will be stored.
            res (int, optional): Resolution of the H3 cells that will be used. Defaults to 6.
        """
        # Generate Tessellated Representation of Geostats Layer
        self._empty_tessellation_path = os.path.join(
            geodatabase, f"{self.feature_name}_h3_{res}_empty"
        )

        arcpy.management.GenerateTessellation(
            self._empty_tessellation_path,
            self.point_feature_class,
            "H3_HEXAGON",
            H3_Resolution=res,
        )

        # Join Geostats Layer to Tessellation
        self.tessellation_path = os.path.join(
            geodatabase, f"{self.feature_name}_h3_{res}"
        )

        arcpy.ga.ArealInterpolationLayerToPolygons(
            self.geostats_layer, self._empty_tessellation_path, self.tessellation_path
        )

        # Message
        print(
            f"Data successfully aggregated to H3 hexagons at: {self.tessellation_path}"
        )

    def export_to_sde(self, sde_path: PathLike, dataset: str) -> None:
        """Exports dataset to PostgreSQL database that is connected to via SDE connection.

        Args:
            sde_path (PathLike): Path to the SDE connection file.
            dataset (str): Deterimines which dataset will be exported to the database.

        Raises:
            ValueError: Raised if dataset is not valid option.
            TypeError: Raised if dataset is not of type str.
        """
        # Determine Dataset to Export
        if dataset == "TESSELLATION":
            input_fc = self.tessellation_path
            output_fc = os.path.join(sde_path, f"{self.feature_name}_h3_{res}")

        elif dataset == "POINT_ACCURACY":
            input_fc = self.point_accuracy_path
            output_fc = os.path.join(sde_path, f"{self.feature_name}_point_diff")

        else:
            if type(dataset) == str:
                raise ValueError(
                    "Param 'dataset' must be in ['TESSELLATION', 'POINT_ACCURACY']"
                )
            else:
                raise TypeError(
                    "Param 'dataset' must be of type string and value of ['TESSELLATION', 'POINT_ACCURACY']"
                )
        # Export
        arcpy.conversion.ExportFeatures(input_fc, output_fc)
