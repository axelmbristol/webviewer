# -*- coding: utf-8 -*-
import io
import sys
import json
import dash
import glob
import ijson
import pandas
import pprint
import numpy as np
import tables
from datetime import datetime
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from scipy import signal
import matplotlib.pyplot as plt
import plotly.tools as tls
import plotly.plotly as py
import operator

if __name__ == '__main__':
    print(dcc.__version__)
    print(sys.argv)
    con = False
    files_in_data_directory = glob.glob("%s\*.h5" % sys.argv[1])
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
                 src='http://dof4zo1o53v4w.cloudfront.net/s3fs-public/styles/logo/public/logos/university-of-bristol'
                     '-logo.png?itok=V80d7RFe'),
        html.Br(),
        html.Big(
            children="PhD Thesis: Deep learning of activity monitoring data for disease detection to support "
                     "livestock farming in resource-poor communities in Africa."),
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
                value=3)], style={'width': '25vh', 'margin-bottom': '2vh', 'margin-left': '1vh'}
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
            style={'height': '20vh'},
            id='activity-graph'
        ),
        dcc.Graph(
            figure=go.Figure(
                data=[
                    go.Heatmap(
                        x=[],
                        y=[],
                        name='',
                    )
                ],
                layout=go.Layout(
                    margin=go.layout.Margin(l=40, r=50, t=5, b=30)
                )
            ),
            style={'height': '20vh'},
            id='spectrogram-activity-graph'
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
            style={'height': '20vh'},
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

            data_m = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), abs(x['first_sensor_value']),
                       x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
                      for x in h5.root.resolution_m.data]

            data_w = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), abs(x['first_sensor_value']),
                       x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
                      for x in h5.root.resolution_w.data]

            data_d = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), abs(x['first_sensor_value']),
                       x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
                      for x in h5.root.resolution_d.data]

            data_h = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), abs(x['first_sensor_value']),
                       x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
                      for x in h5.root.resolution_h.data]

            # data_h_h = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), abs(x['first_sensor_value']),
            #              x['serial_number'], x['signal_strength_max'], x['signal_strength_min'])
            #             for x in h5.root.resolution_h_h.data]
            #
            # data_f = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), abs(x['first_sensor_value']),
            #            x['serial_number'])
            #           for x in h5.root.resolution_f.data]

            # data_m = []
            # data_w = []
            # data_d = []
            # data_h = []
            data_h_h = []
            data_f = []

            #sort by serial numbers containing data size
            map = {}
            for serial_number in serial_numbers:
                map[serial_number] = len([x['signal_strength_min'] for x in h5.root.resolution_h.data if x['serial_number'] == serial_number])

            sorted_map = sorted(map.items(), key=operator.itemgetter(1))

            sorted_serial_numbers = []
            for item in sorted_map:
                sorted_serial_numbers.append(item[0])

            sorted_serial_numbers.reverse()

            data = {'serial_numbers': sorted_serial_numbers, 'data_m': data_m, 'data_w': data_w, 'data_d': data_d,
                    'data_h': data_h, 'data_h_h': data_h_h, 'data_f': data_f}
            return json.dumps(data)

    @app.callback(
        dash.dependencies.Output('serial-number-dropdown', 'options'),
        [dash.dependencies.Input('intermediate-value', 'children')])
    def update_serial_number_drop_down(intermediate_value):
        if intermediate_value:
            data = json.loads(intermediate_value)["serial_numbers"]
            # objects = ijson.items(io.StringIO(intermediate_value), 'serial_numbers')
            # columns = list(objects)
            print("loaded serial numbers")
            print(data)
            s_array = []
            for serial in data:
                s_array.append({'label': str(serial), 'value': serial})
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
         dash.dependencies.Input('intermediate-value', 'children')])
    def update_figure(selected_serial_number, value, intermediate_value):
        input_ss = []
        if isinstance(selected_serial_number, list):
            input_ss.extend(selected_serial_number)
        else:
            input_ss.append(selected_serial_number)
        traces = []
        if not selected_serial_number:
            print("2 selected_serial_number empty")
        else:
            print("2 the selected serial number are: %s" % ', '.join(str(e) for e in input_ss))
            print("2 file opened value=%d" % value)
            for i in input_ss:
                data = None
                raw = json.loads(intermediate_value)
                print("loaded serial numbers")
                if value == 0:
                    data = raw["data_m"]
                if value == 1:
                    data = raw["data_w"]
                if value == 2:
                    data = raw["data_d"]
                if value == 3:
                    data = raw["data_h"]
                if value == 4:
                    data = raw["data_h_h"]
                if value == 5:
                    data = raw["data_f"]

                if value is not 5:
                    signal_strength_min = [(x[4]) for x in data if x[2] == i]
                    signal_strength_max = [(x[3]) for x in data if x[2] == i]
                    time = [(x[0]) for x in data if x[2] == i]
                    print(signal_strength_min)
                    print(signal_strength_max)
                    print(time)

                    if signal_strength_min is not None:
                        traces.append(go.Scatter(
                            x=time,
                            y=signal_strength_min,
                            name=("signal strength min %d" % i) if (len(input_ss) > 1) else "signal strength min"

                        ))
                    if signal_strength_max is not None:
                        traces.append(go.Scatter(
                            x=time,
                            y=signal_strength_max,
                            name=("signal strength max %d" % i) if (len(input_ss) > 1) else "signal strength min"
                        ))
        return {
            'data': traces,
            'layout': go.Layout(xaxis={'title': 'Time'}, yaxis={'title': 'RSSI(received signal strength in)'},
                                legend=dict(y=0.98), margin=go.layout.Margin(l=60, r=50, t=5, b=40))
        }


    @app.callback(
        dash.dependencies.Output('activity-graph', 'figure'),
        [dash.dependencies.Input('serial-number-dropdown', 'value'),
         dash.dependencies.Input('resolution-slider', 'value'),
         dash.dependencies.Input('intermediate-value', 'children')])
    def update_figure(selected_serial_number, value, intermediate_value):
        input_ag = []
        if isinstance(selected_serial_number, list):
            input_ag.extend(selected_serial_number)
        else:
            input_ag.append(selected_serial_number)
        traces = []
        if not selected_serial_number:
            print("selected_serial_number empty")
        else:
            print("1 the selected serial number are: %s" % ', '.join(str(e) for e in input_ag))
            print("1 value is %d" % value)
            for i in input_ag:
                data = None
                raw = json.loads(intermediate_value)
                print("loaded serial numbers")
                if value == 0:
                    data = raw["data_m"]
                if value == 1:
                    data = raw["data_w"]
                if value == 2:
                    data = raw["data_d"]
                if value == 3:
                    data = raw["data_h"]
                if value == 4:
                    data = raw["data_h_h"]
                if value == 5:
                    data = raw["data_f"]

                activity = [(x[1]) for x in data if x[2] == i]
                time = [(x[0]) for x in data if x[2] == i]
                print("activity level-->")
                print(activity)
                print(time)
                traces.append(go.Bar(
                    x=time,
                    y=activity,
                    name=str(i),
                    opacity=0.6
                ))
        return {
            'data': traces,
            'layout': go.Layout(xaxis={'title': 'Time'}, yaxis={'title': 'Activity level/Accelerometer count'},
                                showlegend=True, legend=dict(y=0.98), margin=go.layout.Margin(l=60, r=50, t=5, b=40))
        }

    @app.callback(
        dash.dependencies.Output('spectrogram-activity-graph', 'figure'),
        [dash.dependencies.Input('serial-number-dropdown', 'value'),
         dash.dependencies.Input('resolution-slider', 'value'),
         dash.dependencies.Input('intermediate-value', 'children')])
    def update_figure(selected_serial_number, value, intermediate_value):
        input_ag = []
        if isinstance(selected_serial_number, list):
            input_ag.extend(selected_serial_number)
        else:
            input_ag.append(selected_serial_number)
        traces = []
        if not selected_serial_number:
            print("selected_serial_number empty")
        else:
            print("1 the selected serial number are: %s" % ', '.join(str(e) for e in input_ag))
            print("1 value is %d" % value)
            for i in input_ag:
                data = None
                raw = json.loads(intermediate_value)
                print("loaded serial numbers")
                if value == 0:
                    data = raw["data_m"]
                if value == 1:
                    data = raw["data_w"]
                if value == 2:
                    data = raw["data_d"]
                if value == 3:
                    data = raw["data_h"]
                if value == 4:
                    data = raw["data_h_h"]
                if value == 5:
                    data = raw["data_f"]

                activity = [(x[1]) for x in data if x[2] == i]
                time = [(x[0]) for x in data if x[2] == i]
                print(activity)
                print(time)

                N = int(len(activity)/40)  # Number of point in the fft
                w = signal.blackman(int(N/1.9))
                f, t, Sxx = signal.spectrogram(np.asarray(activity), window=w, nfft=N)

                # f, t, Sxx = signal.spectrogram(np.asarray(activity), 0.1)
                # plt.pcolormesh(t, f, Sxx)
                # plt.ylabel('Frequency [Hz]')
                # plt.xlabel('Time [sec]')
                # mpl_fig = plt.pcolormesh(t, f, Sxx)
                # plotly_fig = tls.mpl_to_plotly(mpl_fig)
                traces.append(go.Heatmap(
                                    x=t,
                                    y=f,
                                    z=Sxx,
                                    colorscale='Viridis',
                                    ))
        return {
            'data': traces,
            'layout': go.Layout(xaxis={'title': 'Time [sec]'}, yaxis={'title': 'Frequency [Hz]'},
                                showlegend=True, legend=dict(y=0.98), margin=go.layout.Margin(l=60, r=50, t=5, b=40))
        }


    app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/brPBPO.css"})
    app.run_server(debug=True, use_reloader=False)
