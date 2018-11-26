# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly.graph_objs as go
import pymongo
from pymongo import MongoClient
import tables
from datetime import datetime

con = False
h5file = None
if con:
    h5file = tables.open_file("C:\\Users\\fo18103\PycharmProjects\mongo2pytables\src\data_compressed_blosc.h5", "r")
else:
    h5file = tables.open_file("C:\SouthAfrica\\70091100056.h5", "r")

data_f = h5file.root.resolution_f.data
data_d = h5file.root.resolution_d.data
data_h = h5file.root.resolution_h.data
data_h_h = h5file.root.resolution_h_h.data
data_m = h5file.root.resolution_m.data
data_w = h5file.root.resolution_w.data

serial_numbers = list(set([(x['serial_number']) for x in h5file.root.resolution_h.data.iterrows()]))

# serial = 40121100718
# s_activity_f = [(x['first_sensor_value']) for x in data_f.iterrows() if x['serial_number'] == serial]
# s_date_f = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data_f.iterrows() if
#             x['serial_number'] == serial]
#
# s_activity_d = [(x['first_sensor_value']) for x in data_d.iterrows() if x['serial_number'] == serial]
# s_date_d = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data_d.iterrows() if
#             x['serial_number'] == serial]
#
# s_activity_h = [(x['first_sensor_value']) for x in data_h.iterrows() if x['serial_number'] == serial]
# s_date_h = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data_h.iterrows() if
#             x['serial_number'] == serial]
#
# s_activity_h_h = [(x['first_sensor_value']) for x in data_h_h.iterrows() if x['serial_number'] == serial]
# s_date_h_h = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data_h_h.iterrows() if
#               x['serial_number'] == serial]
#
# s_activity_m = [(x['first_sensor_value']) for x in data_m.iterrows() if x['serial_number'] == serial]
# s_date_m = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data_m.iterrows() if
#             x['serial_number'] == serial]
#
# s_activity_w = [(x['first_sensor_value']) for x in data_w.iterrows() if x['serial_number'] == serial]
# s_date_w = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data_w.iterrows() if
#             x['serial_number'] == serial]
#
# try:
#     s_signal_strength_min = [(x['signal_strength_min']) for x in data_f.iterrows() if
#                              x['signal_strength_min'] == serial]
#     s_signal_strength_max = [(x['signal_strength_max']) for x in data_f.iterrows() if
#                              x['signal_strength_max'] == serial]
# except KeyError as e:
#     print(e)
#
# print(data_f)
#
# h5file.close()

# print('init mongoDB...')
# client = MongoClient()
# client = MongoClient('localhost', 27017)
# db = client['70101100005']
#
# colNames = db.list_collection_names()
#
# date = []
# activity = []
#
# s_date = []
# s_activity = []
#
# cpt = 0
# colNames.sort()
# for name in colNames:
#     print(str(cpt)+"/"+str(len(colNames))+" "+name + "...")
#     collection = db[name]
#     animals = collection.find_one()["animals"]
#     data = {}
#     for animal in animals:
#         if animal["serial_number"] == 40061200919:
#             tag_data = animal["tag_data"]
#             serial = tag_data[0]["serial_number"]
#             for entry in tag_data:
#                 a = entry["first_sensor_value"]
#                 if a > 1000:
#                     continue
#                 if a < 0:
#                     continue
#
#                 activity.append(a)
#                 formated = datetime.datetime.strptime(entry["date"] + " " + entry["time"], '%d/%m/%y %I:%M:%S %p')\
#                     .strftime('%Y-%m-%dT%H:%M')
#                 date.append(formated)
#                 #print(formated)
#                 data.update({formated: a})
#
#     for key in sorted(data):
#         s_activity.append(data[key])
#         s_date.append(key)
#         #print("%s: %s" % (key, data[key]))
#
#     cpt = cpt + 1
#     if cpt >= 2:
#         break


serial_numbers_array = []
for s in serial_numbers:
    serial_numbers_array.append({'label': str(s), 'value': s})

print('init dash...')
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children="test"),
    dcc.Dropdown(
        id='serial-number-dropdown',
        options=serial_numbers_array,
        multi=True,
        value=40121100718
    ),
    # html.Div(children="activity level over time."),
    # dcc.Graph(
    #     figure=go.Figure(
    #         data=[
    #             go.Bar(
    #                 x=s_date_m,
    #                 y=s_activity_m,
    #                 name=serial,
    #             )
    #         ],
    #         layout=go.Layout(
    #             margin=go.layout.Margin(l=40, r=50, t=5, b=30)
    #         )
    #     ),
    #     style={'height': '15vh'},
    #     id='my-graph-m'
    # ),
    # html.Div(children="resolution w."),
    # dcc.Graph(
    #     figure=go.Figure(
    #         data=[
    #             go.Bar(
    #                 x=s_date_w,
    #                 y=s_activity_w,
    #                 name=serial,
    #             )
    #         ],
    #         layout=go.Layout(
    #             margin=go.layout.Margin(l=40, r=50, t=5, b=30)
    #         )
    #     ),
    #     style={'height': '15vh'},
    #     id='my-graph-w'
    # ),
    html.Div(children="resolution d."),
    dcc.Graph(
        figure=go.Figure(
            data=[
                go.Bar(
                    x=[],
                    y=[],
                    name='',
                )
            ],
            layout=go.Layout(
                margin=go.layout.Margin(l=40, r=50, t=5, b=30)
            )
        ),
        style={'height': '80vh'},
        id='activity-graph-d'
    )
    # html.Div(children="resolution h."),
    # dcc.Graph(
    #     figure=go.Figure(
    #         data=[
    #             go.Bar(
    #                 x=s_date_h,
    #                 y=s_activity_h,
    #                 name=serial,
    #             )
    #         ],
    #         layout=go.Layout(
    #             margin=go.layout.Margin(l=40, r=50, t=5, b=30)
    #         )
    #     ),
    #     style={'height': '15vh'},
    #     id='my-graph-h'
    # ),
    # html.Div(children="resolution 30 mins."),
    # dcc.Graph(
    #     figure=go.Figure(
    #         data=[
    #             go.Bar(
    #                 x=s_date_h_h,
    #                 y=s_activity_h_h,
    #                 name=serial,
    #             )
    #         ],
    #         layout=go.Layout(
    #             margin=go.layout.Margin(l=40, r=50, t=5, b=30)
    #         )
    #     ),
    #     style={'height': '15vh'},
    #     id='my-graph-h-h'
    # ),
    # html.Div(children="resolution full."),
    # dcc.Graph(
    #     figure=go.Figure(
    #         data=[
    #             go.Bar(
    #                 x=s_date_f,
    #                 y=s_activity_f,
    #                 name=serial,
    #             )
    #         ],
    #         layout=go.Layout(
    #             margin=go.layout.Margin(l=40, r=50, t=5, b=30)
    #         )
    #     ),
    #     style={'height': '15vh'},
    #     id='my-graph'
    # )
])


@app.callback(
    dash.dependencies.Output('activity-graph-d', 'figure'),
    [dash.dependencies.Input('serial-number-dropdown', 'value')])
def update_figure(selected_serial_number):
    input = []
    if isinstance(selected_serial_number, list):
        input.extend(selected_serial_number)
    else:
        input.append(selected_serial_number)
    traces = []
    if not selected_serial_number:
        print("empty")
    else:
        print("the selected serial number are: %s" % ', '.join(str(e) for e in input))
        for i in input:
            activity = [(x['first_sensor_value']) for x in data_f.iterrows() if x['serial_number'] == i]
            time = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data_f.iterrows() if
                    x['serial_number'] == i]
            traces.append(go.Bar(
                x=time,
                y=activity,
                name=str(i),
                opacity=0.6
            ))
    return {
        'data': traces,
        'layout': go.Layout(margin=go.layout.Margin(l=40, r=50, t=5, b=30))
    }


if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)
