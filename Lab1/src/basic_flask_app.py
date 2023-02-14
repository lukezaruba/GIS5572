# -*- coding: utf-8 -*-
#
# Creating a Basic API with Flask & psycopg2
#
# GIS 5572: ArcGIS II
# Luke Zaruba
# February 16, 2023
#

import psycopg2
import json
from flask import Flask, request

# Create App Instance
app = Flask(__name__)

# Defining Routes
@app.route('/')
def home():
  response = "GIS 5572 - Luke's Basic API"
  return response

@app.route('/getpolygon')
def getPolygon():
    # Make a Connection to the DB - CHANGE PARAMS TO EXECUTE
    connection = psycopg2.connect(
        host="instance_ip_here",
        database="db_name",
        user="user",
        password="pw"
    )

    # Create Cursor
    cursor = connection.cursor()

    # Set Query
    query = "SELECT JSON_AGG(lab1_polygon) FROM lab1_polygon;"

    # Try to Execute
    try:
        # Execute Query
        out = cursor.execute(query)

        # Close Connection
        connection.close()

        # Convert to GeoJSON
        output = jsonToGeojson(out)

        return output

    # Display Error
    except Exception as e:
        return("Error: " + e)


# Helper Function for Converting JSON to GeoJSON
def jsonToGeojson(raw_json):
    # Convert to JSON
    json_input = json.load(raw_json, "r", encoding="utf-8")

    # Set GeoJSON Structure
    geojson = {
        "type":"FeatureCollection",
        "features":[
                {
                        "type":"Feature",
                        "geometry":{
                        "type":"Polygon",
                        "coordinates":obj["geom"]["coordinates"][0][0],
                },
                        "properties":{"objectid":obj["objectid"]},
                } for obj in json_input
        ]
    }

    # Return GeoJSON
    return geojson