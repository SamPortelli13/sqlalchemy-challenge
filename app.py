import numpy as np
import pandas as pd

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from datetime import datetime, timedelta

from flask import Flask, jsonify, request

def validate_date(check_date):
    checked_date=""
    try:
        checked_date=datetime.strptime(check_date, '%Y-%m-%d').date()
        return [True, checked_date]
    except ValueError:
        return [False, checked_date]
#################################################
# Database Setup
#################################################
engine = create_engine("sqlite:///Resources/hawaii.sqlite")
connection = engine.connect()

# reflect an existing database into a new model
Base = automap_base()
# reflect the tables
Base.prepare(engine, reflect=True)
session = Session(engine)

# Save references to the tables
Measurement = Base.classes.measurement
Station = Base.classes.station

# Calculate the date 1 year ago from the last data point in the database

for row in session.query(Measurement.date, Measurement.id, Measurement.prcp, Measurement.station, Measurement.tobs).order_by(Measurement.id.desc()).limit(1).all():
    base_date = datetime.strptime(row[0],'%Y-%m-%d')

# Retrieve 12 months of precipitation data and store into tables
all_prcp = []
compare_date = base_date - timedelta(days=365)
for row in session.query(Measurement.date,Measurement.prcp, Measurement.station, Measurement.tobs).filter(Measurement.date > compare_date):
    prcp_dict={}
    prcp_dict["date"]=datetime.strptime(row[0],'%Y-%m-%d').date()
    prcp_dict["prcp"]=row[1]
    all_prcp.append(prcp_dict)

# Retrieve the a list of stations
all_stations = []
for row in session.query(Station.station).group_by(Station.station).all():
    all_stations.append(row[0])

# What is the most active stations? (i.e. what station has the most rows)?a
station_id_table=[]
for row in session.query(Measurement.station,func.count(Measurement.prcp)).group_by(Measurement.station).order_by(func.count(Measurement.prcp).desc()).all():
    station_id_table.append(row[0])
most_active_station =station_id_table[0]

all_tobs = []
for row in session.query(Measurement.date,Measurement.prcp, Measurement.station, Measurement.tobs).filter(Measurement.date > compare_date).\
        filter(Measurement.station==most_active_station).order_by(Measurement.date):
    all_tobs_dict={}
    all_tobs_dict["date"]=datetime.strptime(row[0],'%Y-%m-%d').date()
    all_tobs_dict["tobs"]=row[3]
    all_tobs.append(all_tobs_dict)


#################################################
# Flask Setup
#################################################
app = Flask(__name__)

@app.route("/")
def welcome():
    """List all available api routes."""
    return (
        f"Available Routes:<br/>"
        f"/api/v1.0/precipitation<br/>"
        f"/api/v1.0/stations<br/>"
        f"/api/v1.0/tobs<br/>"
        f"/api/v1.0/start_date/end_date"
    )

@app.route("/api/v1.0/precipitation")
def precipitation():
#  Convert the query results to a dictionary using `date` as the key and `prcp` as the value.
#  Return the JSON representation of your dictionary.
    return jsonify(f"Precipitation Dictionary:",all_prcp)

@app.route("/api/v1.0/stations")
def stations():
#  Return a JSON list of stations from the dataset.
    return jsonify(f"List of Stations:",all_stations)

@app.route("/api/v1.0/tobs")
def ptobs():
#  Query the dates and temperature observations of the most active station for the last year of data.
#  Return a JSON list of temperature observations (TOBS) for the previous year.
    return jsonify(f"Most Active Station Temperature Observations for: ",most_active_station,all_tobs)

@app.route('/api/v1.0/<start>')
@app.route('/api/v1.0/<start>/<end>')
def date_range(start=None,end=None):
# When given the start only, calculate `TMIN`, `TAVG`, and `TMAX` for all dates greater than and equal to the start date.
# When given the start and the end date, calculate the `TMIN`, `TAVG`, and `TMAX` for dates between the start and end date inclusive.

    start_date=""
    end_date=""
    is_start_date_valid = validate_date(start)[0]
    if is_start_date_valid:
        start_date = validate_date(start)[1]
    if end is not None:
        is_end_date_valid = validate_date(end)[0]
        if is_end_date_valid:
            end_date = validate_date(end)[1]

# Return a JSON list of the minimum temperature, the average temperature, and the max temperature for a given start or start-end range.
    session=Session(engine)
    Measurement = Base.classes.measurement
    if start_date =="":
        return jsonify(f"The start date is invalid: {start} - enter a valid format: yyyy-mm-dd")
    if end is not None and end_date =="":
        return jsonify(f"The end date is invalid: {end} - enter a valid format: yyyy-mm-dd")
    temp_min=0
    temp_avg=0
    temp_max=0
    if end is None:   #if end date is not supplied, just calculate using the start date
        for row in session.query(func.min(Measurement.tobs), func.avg(Measurement.tobs), func.max(Measurement.tobs)).\
                            filter(Measurement.date >= start_date).all():
            if row[0] is None:
                session.close()
                return jsonify(f"No data for Dates >= start_date: {start_date}")
            else:
                temp_min=row[0]
                temp_avg=row[1]
                temp_max=row[2]
                session.close()
                return jsonify(f"For Dates >= start_date: {start_date}", f"Min temp: {temp_min}, Avg temp: {'{:,.4f}'.format(temp_avg)}, Max temp: {temp_max}")
    else:           # if end date is supplied, use the date range
        for row in session.query(func.min(Measurement.tobs), func.avg(Measurement.tobs), func.max(Measurement.tobs)).\
                                filter(Measurement.date >= start_date).filter(Measurement.date <= end_date).all():
            if row[0] is None:
                return jsonify(f"No data for Dates >= start_date: {start_date} to {end_date}")
                session.close()
            else:
                temp_min=row[0]
                temp_avg=row[1]
                temp_max=row[2]
                session.close()
                return jsonify(f"For Dates: {start_date} to {end_date}", f"Min temp: {temp_min}, Avg temp: {'{:,.4f}'.format(temp_avg)}, Max temp: {temp_max}")


if __name__ == '__main__':
    app.run(debug=True)
