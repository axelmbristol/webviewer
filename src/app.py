# -*- coding: utf-8 -*-
import json
import sys
from datetime import datetime
from os import listdir
from os.path import isfile, join

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import tables
import glob

if __name__ == '__main__':
    print(dcc.__version__)
    print(sys.argv)
    con = False
    # h5file = None
    files_in_data_directory = glob.glob("%s\*.h5" % sys.argv[1])
    # filepath = "C:\SouthAfrica\\70091100056.h5"
    # if con:
    #     h5file = tables.open_file("C:\\Users\\fo18103\PycharmProjects\mongo2pytables\src\data_compressed_blosc.h5", "r")
    # else:
    #     h5file = tables.open_file(filepath, "r")
    #
    # data_f = h5file.root.resolution_f.data
    # data_d = h5file.root.resolution_d.data
    # data_h = h5file.root.resolution_h.data
    # data_h_h = h5file.root.resolution_h_h.data
    # data_m = h5file.root.resolution_m.data
    # data_w = h5file.root.resolution_w.data

    farm_array = []
    for s in files_in_data_directory:
        split = s.split("\\")
        farm_name = split[len(split) - 1]
        farm_array.append({'label': str(farm_name), 'value': farm_name})

    print('init dash...')
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    app.layout = html.Div([
        html.Div(id='output'),
        # Hidden div inside the app that stores the intermediate value
        html.Div(id='intermediate-value', style={'display': 'none'}),
        html.Img(id='logo', style={'width': '15vh'},
                 src='http://dof4zo1o53v4w.cloudfront.net/s3fs-public/styles/logo/public/logos/university-of-bristol-logo.png?itok=V80d7RFe'),
        html.Br(),
        html.Big(
            children="PhD Thesis: Deep learning of activity monitoring data for disease detection to support livestock farming in resource-poor communities in Africa."),
        html.Br(),
        html.Br(),
        html.B(id='farm-title'),
        html.Label('Farm selection:'),
        dcc.Dropdown(
            id='farm-dropdown',
            options=farm_array,
            placeholder="Select farm...",
            style={'width': '55vh', 'margin-bottom': '1vh'}
            # value=40121100718
        ),
        html.Label('Animal selection:'),
        dcc.Dropdown(
            id='serial-number-dropdown',
            options=[],
            multi=True,
            placeholder="Select animal...",
            style={'width': '55vh', 'margin-bottom': '2vh'}
            # value=40121100718
        ),
        html.Label('Data resolution:'),
        html.Div([
            dcc.Slider(
                id='resolution-slider',
                min=0,
                max=5,
                marks={
                    0: 'Month',
                    1: 'Week',
                    2: 'Day',
                    3: 'Hour',
                    4: '30Min',
                    5: 'Full'
                },
                value=3)], style={'width': '20vh', 'margin-bottom': '2vh', 'margin-left': '1vh'}
        ),
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
            style={'height': '35vh'},
            id='activity-graph'
        ),
        dcc.Graph(
            figure=go.Figure(
                data=[
                    go.Scatter(
                        x=[],
                        y=[],
                        name='',
                    )
                ],
                layout=go.Layout(
                    margin=go.layout.Margin(l=40, r=50, t=0, b=0)
                )
            ),
            style={'height': '35vh'},
            id='signal-strength-graph'
        )
    ])


    @app.callback(dash.dependencies.Output('intermediate-value', 'children'),
                  [dash.dependencies.Input('farm-dropdown', 'value')])
    def clean_data(file_path):
        if file_path is not None:
            print("saving data in hidden div...")
            path = sys.argv[1] + "\\" + file_path
            print(path)
            print("getting serial numbers...")
            h5 = tables.open_file(path, "r")
            serial_numbers = list(set([(x['serial_number']) for x in h5.root.resolution_h.data.iterrows()]))
            print(serial_numbers)
            print("getting data in file...")

            data_m = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), x['first_sensor_value'],
                       x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
                      for x in h5.root.resolution_m.data]

            data_w = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), x['first_sensor_value'],
                       x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
                      for x in h5.root.resolution_w.data]

            data_d = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), x['first_sensor_value'],
                       x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
                      for x in h5.root.resolution_d.data]

            data_h = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), x['first_sensor_value'],
                       x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
                      for x in h5.root.resolution_h.data]

            data_h_h = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), x['first_sensor_value'],
                         x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
                        for x in h5.root.resolution_h_h.data]

            data = {'serial_numbers': serial_numbers, 'data_m': data_m, 'data_w': data_w, 'data_d': data_d,
                    'data_h': data_h, 'data_h_h': data_h_h}

            return json.dumps(data)

    @app.callback(
        dash.dependencies.Output('serial-number-dropdown', 'options'),
        [dash.dependencies.Input('intermediate-value', 'children')])
    def update_serial_number_dropdown(intermediate_value):
        if intermediate_value:
            data = json.loads(intermediate_value)["serial_numbers"]
            print("loaded serial numbers")
            print(data)
            s_array = []
            for s in data:
                s_array.append({'label': str(s), 'value': s})
            return s_array
        else:
            return [{}]


    @app.callback(
        dash.dependencies.Output('farm-title', 'children'),
        [dash.dependencies.Input('farm-dropdown', 'value')])
    def update_title(file_path):
        if file_path is not None:
            return "Data file: %s" % sys.argv[1] + "\\" + file_path

    @app.callback(
        dash.dependencies.Output('signal-strength-graph', 'figure'),
        [dash.dependencies.Input('serial-number-dropdown', 'value'),
         dash.dependencies.Input('resolution-slider', 'value'),
         dash.dependencies.Input('farm-dropdown', 'value')])
    def update_figure(selected_serial_number, value, farm):
        if farm is not None:
            path = sys.argv[1] + "\\" + farm
            print('2 You have selected "{}"'.format(path))
        input = []
        if isinstance(selected_serial_number, list):
            input.extend(selected_serial_number)
        else:
            input.append(selected_serial_number)
        traces = []
        if not selected_serial_number:
            print("2 selected_serial_number empty")
        else:
            print("2 the selected serial number are: %s" % ', '.join(str(e) for e in input))
            print("2 file opened value=%d" % value)
            for i in input:
                data = None
                if value == 0:
                    data = tables.open_file(path, "r").root.resolution_m.data
                if value == 1:
                    data = tables.open_file(path, "r").root.resolution_w.data
                if value == 2:
                    data = tables.open_file(path, "r").root.resolution_d.data
                if value == 3:
                    data = tables.open_file(path, "r").root.resolution_h.data
                if value == 4:
                    data = tables.open_file(path, "r").root.resolution_h_h.data
                if value == 5:
                    data = tables.open_file(path, "r").root.resolution_f.data
                try:
                    print(data)
                    signal_strength_min = [(x['signal_strength_min']) for x in data if x['serial_number'] == i]
                    signal_strength_max = [(x['signal_strength_max']) for x in data if x['serial_number'] == i]
                    time = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data if
                            x['serial_number'] == i]
                except KeyError as e:
                    print(e)
                    signal_strength_min = []
                    signal_strength_max = []
                    time = []

                if signal_strength_min is not None:
                    traces.append(go.Scatter(
                        x=time,
                        y=signal_strength_min,
                        name="signal_strength_min"
                    ))
                if signal_strength_max is not None:
                    traces.append(go.Scatter(
                        x=time,
                        y=signal_strength_max,
                        name="signal_strength_max"
                    ))
            print(len(traces))
        return {
            'data': traces,
            'layout': go.Layout(xaxis={'title': 'time'}, yaxis={'title': 'RSSI(received signal strength in)'},
                                legend=dict(y=0.98), margin=go.layout.Margin(l=40, r=50, t=5, b=30))
        }


    @app.callback(
        dash.dependencies.Output('activity-graph', 'figure'),
        [dash.dependencies.Input('serial-number-dropdown', 'value'),
         dash.dependencies.Input('resolution-slider', 'value'),
         dash.dependencies.Input('farm-dropdown', 'value')])
    def update_figure(selected_serial_number, value, farm):
        if farm is not None:
            path = sys.argv[1] + "\\" + farm
            print('You have selected "{}"'.format(path))
        input = []
        if isinstance(selected_serial_number, list):
            input.extend(selected_serial_number)
        else:
            input.append(selected_serial_number)
        traces = []
        if not selected_serial_number:
            print("selected_serial_number empty")
        else:
            print("1 the selected serial number are: %s" % ', '.join(str(e) for e in input))
            print("1 value is %d" % value)
            print("1 file opened path=%s" % path)
            for i in input:
                data = None
                if value == 0:
                    data = tables.open_file(path, "r").root.resolution_m.data
                if value == 1:
                    data = tables.open_file(path, "r").root.resolution_w.data
                if value == 2:
                    data = tables.open_file(path, "r").root.resolution_d.data
                if value == 3:
                    data = tables.open_file(path, "r").root.resolution_h.data
                if value == 4:
                    data = tables.open_file(path, "r").root.resolution_h_h.data
                if value == 5:
                    data = tables.open_file(path, "r").root.resolution_f.data
                print(data)
                activity = [(x['first_sensor_value']) for x in data if x['serial_number'] == i]
                time = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data if
                        x['serial_number'] == i]
                traces.append(go.Bar(
                    x=time,
                    y=activity,
                    name=str(i),
                    opacity=0.6
                ))
            print(activity)
            print(time)
        return {
            'data': traces,
            'layout': go.Layout(xaxis={'title': 'time'}, yaxis={'title': 'activity level/accelerometer count'},
                                showlegend=True, legend=dict(y=0.98), margin=go.layout.Margin(l=40, r=50, t=5, b=30))
        }


    app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/brPBPO.css"})

    app.run_server(debug=True, use_reloader=False)
