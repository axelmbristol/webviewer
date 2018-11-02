# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly.graph_objs as go
import pymongo
from pymongo import MongoClient
import datetime

print('init mongoDB...')
client = MongoClient()
client = MongoClient('localhost', 27017)
db = client['70101100029']

colNames = db.list_collection_names()

date = []
activity = []
cpt = 0
colNames.sort()
for name in colNames:
    print(str(cpt)+"/"+str(len(colNames))+" "+name + "...")
    collection = db[name]

    animals = collection.find_one()["animals"]

    for n in animals:
        if n["serial_number"] == 40061201116:
            animal = n
            tag_data = animal["tag_data"]
            serial = tag_data[0]["serial_number"]
            for entry in tag_data:
                a = entry["first_sensor_value"]
                if a > 1000:
                    a = 1000
                if a < 0:
                    a = 0

                activity.append(a)
                formated = datetime.datetime.strptime(entry["date"] + " " + entry["time"], '%d/%m/%y %I:%M:%S %p').strftime(
                    '%Y-%m-%dT%H:%M')
                date.append(formated)

                #print(str(a) + " " + str(formated))

    cpt = cpt + 1
    if cpt > 7:
        break

print('init dash...')
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children=serial),

    html.Div(children='''
        activity level over time.
    '''),

    dcc.Graph(
        figure=go.Figure(
            data=[
                go.Scatter(
                    x=date,
                    y=activity,
                    name=serial,
                )
            ],
            layout=go.Layout(
                margin=go.layout.Margin(l=40, r=0, t=40, b=160)
            )
        ),
        style={'height': '80vh'},
        id='my-graph'
    )
])

if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)
