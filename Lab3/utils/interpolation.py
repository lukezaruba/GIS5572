# -*- coding: utf-8 -*-
#
# Interpolation Methods with ArcPy
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


class Pipeline:
    """
    A class used to run a pipeline of interpolation and accuracy assessments automatically.

    Methods
    -------
    run_exploratory_interpolation()
        Runs the exploratory interpolation tool and generates results for best-performing model.
    display(display_method)
        Displays accuracy assessment from the run_exploratory_interpolation() tool.
    create_point_accuracy_layer()
        Calculates difference from actual to interpolated values at known points.
    convert_results_to_hex(contours, res)
        Converts the geostats interpolation layer to H3 hexagons.
    export_to_sde(sde_path, dataset)
        Exports dataset to PostgreSQL database that is connected to via SDE connection.

    Example
    -------
    > interpolation_pipeline = Pipeline(r"point_fc_path", r"out_dir_path", "value_of_interest")
    > interpolation_pipeline.run_exploratory_interpolation()
    > interpolation_pipeline.display("PRINT")
    > interpolation_pipeline.create_point_accuracy_layer(r"output_gdb_path")
    > interpolation_pipeline.convert_results_to_hex(r"output_gdb_path", 7)
    > interpolation_pipeline.export_to_sde(r"sde_path", "TESSELLATION")
    """

    def __init__(
        self,
        point_feature_class: PathLike,
        output_directory: PathLike,
        output_geodatabase: PathLike,
        value_of_interest: str,
    ) -> None:
        """Instantiates the Pipeline class.

        Args:
            point_feature_class (PathLike): Path to an input point feature class that will be interpolated.
            output_directory (PathLike): Directory that will store the outputs.
            output_geodatabase (PathLike): Path to the geodatabase where the output will be stored.
            value_of_interest (str): Value in the input point feature class that will be interpolated.
        """
        self.point_feature_class = point_feature_class
        self.output_directory = output_directory
        self.output_geodatabase = output_geodatabase
        self.value_of_interest = value_of_interest

        # Define Other Paths
        self.feature_name = os.path.split(self.point_feature_class)[1]
        self.stats_table = f"{self.feature_name}_stats"
        self.geostats_layer = f"{self.feature_name}_bestInterpolator"
        self.interpolation_methods = "ORDINARY_KRIGING;UNIVERSAL_KRIGING;IDW"

        # Set Workspace
        arcpy.env.workspace = self.output_geodatabase

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
            "ACCURACY PERCENT #",
            "ACCURACY 1",
            None,
        )

        # Message
        print(arcpy.GetMessages())

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
        # Convert from GDB Table to CSV
        arcpy.conversion.ExportTable(
            self.stats_table,
            os.path.join(self.output_directory, f"{self.stats_table}.csv"),
        )

        # Read Table into DF
        df = pd.read_csv(os.path.join(self.output_directory, f"{self.stats_table}.csv"))

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

    def create_point_accuracy_layer(self) -> None:
        """Calculates difference from actual to interpolated values at known points."""
        # Extract Values of Geostats Layer to Points
        self.point_accuracy_path = os.path.join(
            self.output_geodatabase, f"{self.feature_name}_point_diff"
        )

        arcpy.ga.GALayerToPoints(
            self.geostats_layer,
            self.point_feature_class,
            None,
            self.point_accuracy_path,
        )

        # Message
        print(f"Point accuracy successfully generated at: {self.point_accuracy_path}")

    def convert_results_to_hex(self, contours=False, res=6) -> None:
        """Converts the geostats interpolation layer to H3 hexagons.

        Args:
            contours(bool, optional): Determines if filled contours are needed or not.
            res (int, optional): Resolution of the H3 cells that will be used. Defaults to 6.
        """
        # If needed, Convert to Polygons First
        if contours:
            self.contour_path = os.path.join(
                self.output_geodatabase, f"{self.feature_name}_filledContours"
            )

            arcpy.ga.GALayerToContour(
                self.geostats_layer,
                "FILLED_CONTOUR",
                self.contour_path,
                "PRESENTATION",
                "GEOMETRIC_INTERVAL",
                20,
                [],
                None,
            )

        # Generate Tessellated Representation of Geostats Layer
        self._empty_tessellation_path = os.path.join(
            self.output_geodatabase, f"{self.feature_name}_h3_{res}_empty"
        )

        arcpy.management.GenerateTessellation(
            self._empty_tessellation_path,
            self.point_feature_class,
            "H3_HEXAGON",
            H3_Resolution=res,
        )

        # Summarize Point Predictions with Tessellation
        self.tessellation_path = os.path.join(
            self.output_geodatabase, f"{self.feature_name}_h3_{res}"
        )

        # Summarize based on Contours or Not
        if contours:
            arcpy.gapro.SummarizeWithin(
                self.contour_path,
                self.tessellation_path,
                "POLYGON",
                summary_polygons=self._empty_tessellation_path,
                sum_shape="NO_SUMMARY",
                standard_summary_fields="Value_Max MEAN Count",
            )

        else:
            arcpy.gapro.SummarizeWithin(
                self.point_accuracy_path,
                self.tessellation_path,
                "POLYGON",
                summary_polygons=self._empty_tessellation_path,
                sum_shape="NO_SUMMARY",
                standard_summary_fields="Predicted MEAN Rate",
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
            output_fc = os.path.join(sde_path, f"{self.feature_name}_h3")

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
