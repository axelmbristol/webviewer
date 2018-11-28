# -*- coding: utf-8 -*-
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
    print(sys.argv)
    con = False
    h5file = None

    files_in_data_directory = glob.glob("%s\*.h5" % sys.argv[1])

    filepath = "C:\SouthAfrica\\70091100056.h5"
    if con:
        h5file = tables.open_file("C:\\Users\\fo18103\PycharmProjects\mongo2pytables\src\data_compressed_blosc.h5", "r")
    else:
        h5file = tables.open_file(filepath, "r")

    data_f = h5file.root.resolution_f.data
    data_d = h5file.root.resolution_d.data
    data_h = h5file.root.resolution_h.data
    data_h_h = h5file.root.resolution_h_h.data
    data_m = h5file.root.resolution_m.data
    data_w = h5file.root.resolution_w.data

    farm_array = []
    for s in files_in_data_directory:
        split = s.split("\\")
        farm_name = split[len(split)-1]
        farm_array.append({'label': str(farm_name), 'value': farm_name})

    print('init dash...')
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    app.layout = html.Div(children=[
        html.Img(style={'width': '15vh'}, src='http://dof4zo1o53v4w.cloudfront.net/s3fs-public/styles/logo/public/logos/university-of-bristol-logo.png?itok=V80d7RFe'),
        html.Br(),
        html.Big(children="PhD Thesis: Deep learning of activity monitoring data for disease detection to support livestock farming in resource-poor communities in Africa."),
        html.Br(),
        html.Br(),
        html.B(id='farm-title', children=filepath),
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
            style={'height': '70vh'},
            id='activity-graph-d'
        )
    ])

    @app.callback(
        dash.dependencies.Output('farm-title', 'children'),
        [dash.dependencies.Input('farm-dropdown', 'value')])
    def update_title(file_path):
        return "%s" % file_path

    @app.callback(
        dash.dependencies.Output('serial-number-dropdown', 'value'),
        [dash.dependencies.Input('farm-dropdown', 'value')])
    def update_drop_down(farm):
        return []

    @app.callback(
        dash.dependencies.Output('serial-number-dropdown', 'options'),
        [dash.dependencies.Input('farm-dropdown', 'value')])
    def update_drop_down(farm):
        if farm is not None:
            path = sys.argv[1]+"\\"+farm
            print(path)
            serial_numbers = list(set([(x['serial_number']) for x in tables.open_file(path, "r").root.resolution_h.data.iterrows()]))
            serial_numbers_array = []
            for s in serial_numbers:
                serial_numbers_array.append({'label': str(s), 'value': s})
            return serial_numbers_array
        else:
            return []

    @app.callback(
        dash.dependencies.Output('activity-graph-d', 'figure'),
        [dash.dependencies.Input('serial-number-dropdown', 'value'),
         dash.dependencies.Input('resolution-slider', 'value'),
         dash.dependencies.Input('farm-dropdown', 'value')])
    def update_figure(selected_serial_number, value, farm):
        if farm is not None:
            print('You have selected "{}"'.format(sys.argv[1]+"\\"+farm))
        input = []
        if isinstance(selected_serial_number, list):
            input.extend(selected_serial_number)
        else:
            input.append(selected_serial_number)
        traces = []
        if not selected_serial_number:
            print("selected_serial_number empty")
        else:
            print("the selected serial number are: %s" % ', '.join(str(e) for e in input))
            for i in input:
                data = None
                if value == 0:
                    data = data_m
                if value == 1:
                    data = data_w
                if value == 2:
                    data = data_d
                if value == 3:
                    data = data_h
                if value == 4:
                    data = data_h_h
                if value == 5:
                    data = data_f

                activity = [(x['first_sensor_value']) for x in data.iterrows() if x['serial_number'] == i]
                try:
                    signal_strength_min = [(x['signal_strength_min']) for x in data.iterrows() if x['serial_number'] == i]
                except KeyError as e:
                    print(e)
                    signal_strength_min = None

                try:
                    signal_strength_max = [(x['signal_strength_max']) for x in data.iterrows() if
                                           x['serial_number'] == i]
                except KeyError as e:
                    print(e)
                    signal_strength_max = None

                time = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M')) for x in data.iterrows()
                        if
                        x['serial_number'] == i]
                traces.append(go.Bar(
                    x=time,
                    y=activity,
                    name="activity level of %s" % str(i),
                    opacity=0.6
                ))
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
            print(activity)
            print(time)
        return {
            'data': traces,
            'layout': go.Layout(legend=dict(y=0.98), margin=go.layout.Margin(l=40, r=50, t=5, b=30))
        }

    app.run_server(debug=True, use_reloader=False)
