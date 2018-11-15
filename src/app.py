# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly.graph_objs as go
import pymongo
from pymongo import MongoClient
import datetime
import tables


con = True
h5file = None
if con:
    h5file = tables.open_file("C:\\Users\\fo18103\PycharmProjects\mongo2pytables\src\data_compressed_blosc.h5", "r")
else:
    h5file = tables.open_file("C:\\Users\\fo18103\PycharmProjects\mongo2pytables\src\data.h5", "r")

print(0)
data = h5file.root.array

print(data)

h5file.close()


exit(0)

print('init mongoDB...')
client = MongoClient()
client = MongoClient('localhost', 27017)
db = client['70101100005']

colNames = db.list_collection_names()

date = []
activity = []

s_date = []
s_activity = []

cpt = 0
colNames.sort()
for name in colNames:
    print(str(cpt)+"/"+str(len(colNames))+" "+name + "...")
    collection = db[name]
    animals = collection.find_one()["animals"]
    data = {}
    for animal in animals:
        if animal["serial_number"] == 40061200919:
            tag_data = animal["tag_data"]
            serial = tag_data[0]["serial_number"]
            for entry in tag_data:
                a = entry["first_sensor_value"]
                if a > 1000:
                    continue
                if a < 0:
                    continue

                activity.append(a)
                formated = datetime.datetime.strptime(entry["date"] + " " + entry["time"],
                                                      '%d/%m/%y %I:%M:%S %p').strftime(
                    '%Y-%m-%dT%H:%M')
                date.append(formated)
                #print(formated)
                data.update({formated: a})

    for key in sorted(data):
        s_activity.append(data[key])
        s_date.append(key)
        #print("%s: %s" % (key, data[key]))

    cpt = cpt + 1
    if cpt >= 2:
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
                    x=s_date,
                    y=s_activity,
                    mode='lines',
                    name=serial,
                )
            ],
            layout=go.Layout(
                margin=go.layout.Margin(l=40, r=50, t=40, b=160)
            )
        ),
        style={'height': '80vh'},
        id='my-graph'
    )
])

if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)
