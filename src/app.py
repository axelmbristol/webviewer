# -*- coding: utf-8 -*-
import glob
import json
import operator
import sys
from datetime import datetime, timedelta
from multiprocessing import Process, Queue
from time import mktime
from time import strptime

import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly
import plotly.graph_objs as go
import tables
from scipy import signal
from dateutil.relativedelta import *
from ipython_genutils.py3compat import xrange
import flask


def get_date_range(layout_data):
    # print(layout_data)
    x_min_epoch = 0.0
    x_max_epoch = 19352963810.0
    try:
        xaxis_autorange = bool(layout_data["xaxis.autorange"])
    except KeyError:
        xaxis_autorange = False
    try:
        auto_range = layout_data["autosize"]
    except KeyError:
        auto_range = False
    try:
        x_min = str(layout_data["xaxis.range[0]"])
        if len(x_min.split(":")) == 2:
            x_min = x_min + ":00"
        if "." not in x_min:
            x_min = x_min + ".00"
        x_min_epoch = int(mktime(strptime(x_min, '%Y-%m-%d %H:%M:%S.%f')))
    except KeyError:
        x_min = None
    try:
        x_max = str(layout_data["xaxis.range[1]"])
        if len(x_max.split(":")) == 2:
            x_max = x_max + ":00"
        if "." not in x_max:
            x_max = x_max + ".00"
        x_max_epoch = int(mktime(strptime(x_max, '%Y-%m-%d %H:%M:%S.%f')))
    except KeyError:
        x_max = None
    return {'x_min_epoch': x_min_epoch, 'x_max_epoch': x_max_epoch,
            'x_min': x_min, 'x_max': x_max,
            'xaxis_autorange': xaxis_autorange, 'auto_range': auto_range}


def get_elapsed_time_string(time_initial, time_next):
    dt1 = datetime.fromtimestamp(time_initial)
    dt2 = datetime.fromtimestamp(time_next)
    rd = relativedelta(dt2, dt1)
    return '%d years %d months %d days %d hours %d minutes %d seconds' % (
        rd.years, rd.months, rd.days, rd.hours, rd.minutes, rd.seconds)


def get_elapsed_time_array(time_initial, time_next):
    dt1 = datetime.fromtimestamp(time_initial)
    dt2 = datetime.fromtimestamp(time_next)
    rd = relativedelta(dt2, dt1)
    return [rd.years, rd.months, rd.days, rd.hours, rd.minutes, rd.seconds]


def get_elapsed_time_seconds(time_initial, time_next):
    dt1 = datetime.fromtimestamp(time_initial)
    dt2 = datetime.fromtimestamp(time_next)
    rd = relativedelta(dt2, dt1)
    result = (dt2 - dt1).total_seconds()
    # print("elpased time input, %d, %d", time_initial, time_next)
    # print(result)
    # print([rd.years, rd.months, rd.days, rd.hours, rd.minutes, rd.seconds])
    return result


def find_appropriate_resolution(duration):
    if 0 < duration <= 3 * 3600.0:
        value = 5
    if 3 * 3600.0 < duration <= 4 * 3600.0:
        value = 4
    if 4 * 3600.0 < duration <= 259200.0:
        value = 4
    if 259200.0 < duration <= 604800.0:
        value = 3
    if 604800.0 < duration <= 5 * 604800.0:
        value = 2
    if 5 * 604800.0 < duration <= 10 * 604800.0:
        value = 1
    if duration > 10 * 604800.0:
        value = 1
    return value


def thread_activity(q_1, selected_serial_number, value, intermediate_value, relayout_data):
    input_ag = []
    _d = []

    if isinstance(selected_serial_number, list):
        input_ag.extend(selected_serial_number)
    else:
        input_ag.append(selected_serial_number)
    if not selected_serial_number:
        print("selected_serial_number empty")
    else:
        # print("1 the selected serial number are: %s" % ', '.join(str(e) for e in input_ag))
        # print("1 value is %d" % value)
        for i in input_ag:
            data = None
            range_d = get_date_range(json.loads(relayout_data))
            x_max_epoch = range_d['x_max_epoch']
            x_min_epoch = range_d['x_min_epoch']
            x_max = range_d['x_max']
            if range_d['x_max'] is not None:
                value = find_appropriate_resolution(get_elapsed_time_seconds(x_min_epoch, x_max_epoch))

            raw = json.loads(intermediate_value)

            file_path = raw["file_path"]
            print("opening file in thread test")
            h5 = tables.open_file(file_path, "r")

            if value == 0:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['first_sensor_value'])
                        for x in h5.root.resolution_m.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 1:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['first_sensor_value'])
                        for x in h5.root.resolution_w.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 2:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['first_sensor_value'])
                        for x in h5.root.resolution_d.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 3:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['first_sensor_value'])
                        for x in h5.root.resolution_h.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 4:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['first_sensor_value'])
                        for x in h5.root.resolution_h_h.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 5:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['first_sensor_value'])
                        for x in h5.root.resolution_f.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            # h5.close()
            activity = [(x[1]) for x in data]
            time = [(x[0]) for x in data]
            print("activity level-->resolution=%d" % value)

            print(activity)
            # print(time)

            if len(activity) > 0:
                traces = []
                signal_size = len(activity)
                max_activity_value = max(x for x in activity if x is not None)
                min_activity_value = min(x for x in activity if x is not None)
                s_d = time[0]
                e_d = time[len(time) - 1]
                d1 = (datetime.strptime(s_d, '%Y-%m-%dT%H:%M') - datetime(1970, 1, 1)).total_seconds()
                d2 = (datetime.strptime(e_d, '%Y-%m-%dT%H:%M') - datetime(1970, 1, 1)).total_seconds()
                start_date = datetime.fromtimestamp(d1).strftime('%d/%m/%Y %H:%M:%S')
                end_date = datetime.fromtimestamp(d2).strftime('%d/%m/%Y %H:%M:%S')
                time_range = get_elapsed_time_string(d1, d2)

                if value == 2:
                    time = [t.split('T')[0] for t in time]

                traces.append(go.Bar(
                    x=time,
                    y=activity,
                    name=str(i),
                    opacity=0.8
                ))
                _d.append({"activity": activity,
                           "time": time,
                           "range_d": range_d,
                           "start_date": start_date,
                           "end_date": end_date,
                           "signal_size": signal_size,
                           "min_activity_value": min_activity_value,
                           "max_activity_value": max_activity_value,
                           "time_range": time_range,
                           "traces": traces,
                           "x_max": x_max,
                           "relayout_data": relayout_data,
                           'resolution': value})
                q_1.put(_d)
    if q_1.empty():
        q_1.put([])


def compare_dates(d1, d2):
    d1_ = datetime.strptime(d1, '%d/%m/%Y').strftime('%Y-%m-%d')
    d2_ = d2.split('T')[0]
    print(d1_, d2_, d1_ == d2_)
    return d1_ == d2_


def chunks(l, n):
    n = max(1, n)
    return (l[i:i + n] for i in xrange(0, len(l), n))


def is_in_period(start, famacha_day, n):
    datetime_start = datetime.strptime(start, '%Y-%m-%d')
    datetime_famacha = datetime.strptime(famacha_day, '%d/%m/%Y')
    margin = timedelta(days=n)
    return datetime_start - margin <= datetime_famacha <= datetime_start + margin


def build_weather_trace(traces, data_f, resolution):
    try:
        print("weather data available for [%s]" % ','.join(data_f['weather'].keys()))
        time = traces[0]['x']
        # m = pow(10, int(len(str(max(traces[0]['y'])).split('.')[0])/1.3))
        weather_s = [None] * len(time)
        date_weather = data_f['weather'].keys()
        # date_famacha = [datetime.strptime(d, '%Y-%m-%d').strftime('%Y-%m-%d') for d in date_]

        # # get interval of time
        # chunked = chunks(time, 2)
        # for i, item in enumerate(chunked):
        # #check if time in period
        #     for day in date_famacha:
        #         if is_in_period(day, item[0], item[1]):
        #             key = datetime.strptime(day, '%Y-%m-%d').strftime('%d/%m/%Y')
        #             famacha_s[i] = data_f['famacha'][serial][key]
        print("resolution=%d", resolution)
        for i, t in enumerate(time):
            day = t.split('T')[0]
            try:
                h = t.split('T')[1].split(':')[0]
            except IndexError as e:
                h = "12:00"
                print(e)
            if day in date_weather:
                list = data_f['weather'][day]
                for item in list:
                    if h == item['time'].split(':')[0]:
                        weather_s[i] = item['humidity']

        print(weather_s)
        return go.Scatter(
            x=time,
            y=weather_s,
            name='humidity',
            # connectgaps=True,
            opacity=0.1,
            yaxis='y3',
            fill='tozeroy',
            mode='none'
            # marker=dict(
            #     color='rgb(153,0,255)'
            # ),
        )
    except KeyError as e:
        print(e)


def build_famacha_trace(traces, data_f, resolution):
    try:
        print("famatcha data available for [%s]" % ','.join(data_f['famacha'].keys()))
        time = traces[0]['x']
        # m = pow(10, int(len(str(max(traces[0]['y'])).split('.')[0])/1.3))
        famacha_s = [None] * len(time)
        serial = traces[0]['name']
        date_ = data_f['famacha'][serial].keys()
        date_famacha = [datetime.strptime(d, '%d/%m/%Y').strftime('%Y-%m-%d') for d in date_]

        # # get interval of time
        # chunked = chunks(time, 2)
        # for i, item in enumerate(chunked):
        # #check if time in period
        #     for day in date_famacha:
        #         if is_in_period(day, item[0], item[1]):
        #             key = datetime.strptime(day, '%Y-%m-%d').strftime('%d/%m/%Y')
        #             famacha_s[i] = data_f['famacha'][serial][key]
        print("resolution=%d", resolution)
        for i, t in enumerate(time):
            day = t.split('T')[0]
            if resolution == 1:
                for day_in_famacha in date_famacha:
                    key = datetime.strptime(day_in_famacha, '%Y-%m-%d').strftime('%d/%m/%Y')
                    if is_in_period(day, key, 5):
                        famacha_s[i] = data_f['famacha'][serial][key]
            else:
                if day in date_famacha:
                    key = datetime.strptime(day, '%Y-%m-%d').strftime('%d/%m/%Y')
                    famacha_s[i] = data_f['famacha'][serial][key]

        print(famacha_s)
        return go.Bar(
            x=time,
            y=famacha_s,
            # mode='lines+markers',
            name='famacha score',
            # connectgaps=True,
            opacity=0.2,
            yaxis='y2'
            # marker=dict(
            #     color='rgb(153,0,255)'
            # ),
        )
    except KeyError as e:
        print(e)


def build_activity_graph(data, data_f):
    figures = []
    for d in data:
        x_max = d["x_max"]
        signal_size = d["signal_size"]
        min_activity_value = d["min_activity_value"]
        max_activity_value = d["max_activity_value"]
        start_date = d["start_date"]
        end_date = d["end_date"]
        time_range = d["time_range"]
        activity = d["activity"]
        time = d["time"]
        relayout_data = d["relayout_data"]
        traces = d["traces"]
        range_d = d["range_d"]
        resolution = d["resolution"]

        fig_famacha = build_famacha_trace(traces, data_f, resolution)
        fig_weather = build_weather_trace(traces, data_f, resolution)

        traces.append(fig_famacha)
        if resolution == 1:
            traces.append(fig_weather)
        # traces.append(fig_weather)
        print(traces)

        if x_max is not None:
            figures.append(
                [{'thread_activity': True}, {'signal_size': signal_size}, {'min_activity_value': min_activity_value},
                 {'max_activity_value': max_activity_value}, {'start_date': start_date},
                 {'end_date': end_date}, {'time_range': time_range},
                 {'activity': activity}, {'time': time}, {'relayout_data': relayout_data}, {
                     'data': traces,
                     'layout': go.Layout(xaxis={'title': 'Time', 'autorange': range_d['xaxis_autorange'],
                                                'range': [range_d['x_min'], range_d['x_max']]},
                                         yaxis={'title': 'Activity level/Accelerometer count'},
                                         yaxis2=dict(
                                             nticks=3,
                                             # title='FAMACHA',
                                             # titlefont=dict(
                                             #     color='rgb(148, 103, 189)'
                                             # ),
                                             # tickfont=dict(
                                             #     color='rgb(148, 103, 189)'
                                             # ),
                                             overlaying='y',
                                             side='right'
                                         ),
                                         yaxis3=dict(
                                             # title='HUMIDITY',
                                             # titlefont=dict(
                                             #     color='rgb(148, 103, 189)'
                                             # ),
                                             # tickfont=dict(
                                             #     color='rgb(148, 103, 189)'
                                             # ),
                                             overlaying='y',
                                             side='right'
                                         ),
                                         autosize=range_d['auto_range'],
                                         legend=dict(y=0.98), margin=go.layout.Margin(l=60, r=50, t=5, b=40))
                 }])
        else:
            figures.append(
                [{'thread_activity': True}, {'signal_size': signal_size}, {'min_activity_value': min_activity_value},
                 {'max_activity_value': max_activity_value}, {'start_date': start_date},
                 {'end_date': end_date}, {'time_range': time_range},
                 {'activity': activity}, {'time': time}, {'relayout_data': relayout_data}, {
                     'data': traces,
                     'layout': go.Layout(xaxis={'title': 'Time', 'autorange': True},
                                         yaxis={'title': 'Activity level/Accelerometer count',
                                                'autorange': True},
                                         autosize=True,
                                         yaxis2=dict(
                                             nticks=3,
                                             # title='FAMACHA',
                                             # titlefont=dict(
                                             #     color='rgb(148, 103, 189)'
                                             # ),
                                             # tickfont=dict(
                                             #     color='rgb(148, 103, 189)'
                                             # ),
                                             anchor='x',
                                             overlaying='y',
                                             side='right'
                                         ),
                                         yaxis3=dict(
                                             # title='HUMIDITY',
                                             # titlefont=dict(
                                             #     color='rgb(148, 103, 189)'
                                             # ),
                                             # tickfont=dict(
                                             #     color='rgb(148, 103, 189)'
                                             # ),
                                             anchor='x',
                                             overlaying='y',
                                             side='right'
                                         )
                                         # ,
                                         # shapes=[dict(
                                         #     type='rect',
                                         #     # x-reference is assigned to the x-values
                                         #     xref='x',
                                         #     # y-reference is assigned to the plot paper [0,1]
                                         #     yref='paper',
                                         #     x0='2015-01-22T00:37',
                                         #     y0=0,
                                         #     x1='2016-04-05T23:34',
                                         #     y1=1,
                                         #     fillcolor='#d3d3d3',
                                         #     opacity=0.2,
                                         #     line={'width': 0, }
                                         # )]
                                         ,
                                         legend=dict(y=0.98), margin=go.layout.Margin(l=60, r=50, t=5, b=40))
                 }])
    return figures


def thread_signal(q_2, selected_serial_number, value, intermediate_value, relayout_data):
    input_ss = []
    x_max = None
    if isinstance(selected_serial_number, list):
        input_ss.extend(selected_serial_number)
    else:
        input_ss.append(selected_serial_number)
    traces = []
    if not selected_serial_number:
        print("2 selected_serial_number empty")
    else:
        for i in input_ss:
            data = None
            range_d = get_date_range(json.loads(relayout_data))
            x_max_epoch = range_d['x_max_epoch']
            x_min_epoch = range_d['x_min_epoch']
            if range_d['x_max'] is not None:
                value = find_appropriate_resolution(get_elapsed_time_seconds(x_min_epoch, x_max_epoch))

            raw = json.loads(intermediate_value)
            file_path = raw["file_path"]
            print("opening file in thread signal")
            h5 = tables.open_file(file_path, "r")
            if value == 0:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['signal_strength_max'], x['signal_strength_min'])
                        for x in h5.root.resolution_m.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 1:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['signal_strength_max'], x['signal_strength_min'])
                        for x in h5.root.resolution_w.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 2:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['signal_strength_max'], x['signal_strength_min'])
                        for x in h5.root.resolution_d.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 3:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['signal_strength_max'], x['signal_strength_min'])
                        for x in h5.root.resolution_h.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 4:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['signal_strength_max'], x['signal_strength_min'])
                        for x in h5.root.resolution_h_h.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if value == 5:
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['signal_strength'])
                        for x in h5.root.resolution_f.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            # h5.close()

            time = [(x[0]) for x in data]

            if value is not 5:
                signal_strength_min = [(x[2]) for x in data]
                signal_strength_max = [(x[1]) for x in data]
                print("thread_signal resolution=%d" % value)
                if signal_strength_min is not None:
                    traces.append(go.Scatter(
                        x=time,
                        y=signal_strength_min,
                        mode='lines+markers',
                        name=("signal strength min %d" % i) if (len(input_ss) > 1) else "signal strength min"

                    ))
                if signal_strength_max is not None:
                    traces.append(go.Scatter(
                        x=time,
                        y=signal_strength_max,
                        mode='lines+markers',
                        name=("signal strength max %d" % i) if (len(input_ss) > 1) else "signal strength min"
                    ))
            else:
                signal_strength_ = [(x[1]) for x in data]
                if signal_strength_ is not None:
                    traces.append(go.Scatter(
                        x=time,
                        y=signal_strength_,
                        mode='lines+markers',
                        name=("signal strength%d" % i) if (len(input_ss) > 1) else "signal strength"

                    ))

    if x_max is not None:
        q_2.put({
            'data': traces,
            'layout': go.Layout(xaxis={'title': 'Time', 'autorange': range_d['xaxis_autorange'],
                                       'range': [range_d['x_min'], range_d['x_max']]},
                                yaxis={'title': 'RSSI(received signal strength in)'},
                                autosize=range_d['auto_range'],
                                showlegend=False,
                                # legend=dict(y=1, x=0),
                                margin=go.layout.Margin(l=60, r=50, t=5, b=40)
                                ),
            'resolution': value
        })
    else:
        q_2.put({
            'data': traces,
            'layout': go.Layout(xaxis={'title': 'Time', 'autorange': True}, yaxis={'title': 'RSSI(received signal '
                                                                                            'strength in)',
                                                                                   'autorange': True},
                                autosize=True,
                                showlegend=False,
                                # legend=dict(y=1, x=0),
                                margin=go.layout.Margin(l=60, r=50, t=5, b=40)
                                ),
            'resolution': value
        })


def thread_spectrogram(q_3, activity, time, window_size, radio, relayout):
    j = json.loads(relayout)
    range_d = get_date_range(j)
    print("thread_spectrogram")
    # print(activity, time, window_size, radio, relayout)
    x_max = range_d['x_max']
    traces = []
    # print("activity in spec", activity)
    if len(activity) > 1:
        if activity is not None and window_size is not None:
            if int(window_size) > len(activity):
                window_size = int(len(activity))

        w = signal.blackman(int(window_size))
        f, t, Sxx = signal.spectrogram(np.asarray(activity), window=w)

        widths = np.arange(1, 31)
        cwtmatr = signal.cwt(np.asarray(activity), signal.ricker, widths)
        if radio == "STFT":
            transform = Sxx
        if radio == "CWT":
            transform = cwtmatr
        traces.append(go.Heatmap(
            x=time,
            y=f,
            z=transform,
            colorscale='Viridis',
        ))

    if x_max is not None:
        q_3.put([{'thread_activity': True}, {'activity': activity}, {'time': time}, {
            'data': traces,
            'layout': go.Layout(
                xaxis={'title': 'Time', 'range': [range_d['x_min'], range_d['x_max']],
                       'autorange': range_d['xaxis_autorange']},
                yaxis={'title': 'Frequency'},
                autosize=range_d['auto_range'],
                showlegend=True, legend=dict(y=0.98),
                margin=go.layout.Margin(l=60, r=50, t=5, b=40))
        }])
    else:
        q_3.put([{'thread_activity': True}, {'activity': activity}, {'time': time}, {
            'data': traces,
            'layout': go.Layout(
                xaxis={'title': 'Time', 'autorange': True},
                yaxis={'title': 'Frequency', 'autorange': True},
                autosize=True,
                showlegend=True, legend=dict(y=0.98),
                margin=go.layout.Margin(l=60, r=50, t=5, b=40))
        }])


if __name__ == '__main__':
    print("dash ccv %s" % dcc.__version__)
    print(sys.argv)
    q_1 = Queue()
    q_2 = Queue()
    q_3 = Queue()
    con = False
    h5_files_in_data_directory = glob.glob("%s\*.h5" % sys.argv[1])
    json_files_in_data_directory = glob.glob("%s\*.json" % sys.argv[2])
    print(h5_files_in_data_directory)
    print(json_files_in_data_directory)
    farm_array = []
    for s in h5_files_in_data_directory:
        split = s.split("\\")
        farm_name = split[len(split) - 1]
        farm_array.append({'label': str(farm_name), 'value': farm_name})

    print('init dash...')
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    server = flask.Flask(__name__)
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets, server=server)

    # server = app.server

    styles = {
        'pre': {
            'border': 'thin lightgrey solid',
            'overflowX': 'scroll'
        }
    }

    app.layout = html.Div([
        html.Div(id='output'),
        # Hidden div inside the app that stores the intermediate value
        html.Div(id='intermediate-value', style={'display': 'none'}),
        html.Div(id='figure-data', style={'display': 'none'}),
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

        html.Div([html.Pre(id='relayout-data', style={'display': 'none'})], className='three columns'),

        html.Div([
            html.Div([
                html.Label('Farm selection:', style={'color': 'white', 'font-weight': 'bold'}),
                dcc.Dropdown(
                    id='farm-dropdown',
                    options=farm_array,
                    placeholder="Select farm...",
                    style={'width': '47vh', 'margin-bottom': '1vh'}
                    # value=40121100718
                ),
                html.Label('Animal selection:', style={'color': 'white', 'font-weight': 'bold'}),
                dcc.Dropdown(
                    id='serial-number-dropdown',
                    options=[],
                    multi=False,
                    placeholder="Select animal...",
                    style={'width': '47vh', 'margin-bottom': '2vh'}
                    # value=40121100718
                ),

                html.Div([
                    html.Div([
                        html.Label('Sample rate (1 sample per unit of time):',
                                   style={'color': 'white', 'font-weight': 'bold'}),
                        dcc.Slider(
                            id='resolution-slider',
                            min=0,
                            max=5,
                            marks={
                                0: 'Month',
                                1: 'Week',
                                2: 'Day',
                                3: 'Hour',
                                4: '30min',
                                5: '3min'
                            },
                            value=1)],
                        className='two columns',
                        style={'width': '23vh', 'margin-bottom': '3vh', 'margin-left': '1vh', 'display': 'none'}
                    ),
                    html.Div([
                        html.Label('Transform:', style={'color': 'white', 'font-weight': 'bold'}),
                        dcc.RadioItems(
                            id='transform-radio',
                            options=[
                                {'label': 'STFT', 'value': 'STFT'},
                                {'label': 'CWT', 'value': 'CWT'}
                            ],
                            labelStyle={'display': 'inline-block', 'color': 'white'},
                            value='CWT')],
                        className='two columns',
                        style={'margin-bottom': '3vh', 'margin-left': '0vh', 'width': '12vh'}
                    ),
                    html.Div([
                        html.Label('Window size:', style={'width': '10vh', 'margin-left': '0vh', 'color': 'white',
                                                          'font-weight': 'bold'}),
                        dcc.Input(
                            id='window-size-input',
                            placeholder='Input size of window here...',
                            type='text',
                            value='40',
                            style={'width': '5vh', 'height': '2vh', 'margin-left': '0vh'}
                        )],
                        className='two columns'

                    )
                ],
                    style={'margin-bottom': '8vh'}
                )
            ], className='two columns'),

            html.Div([
                # html.Label('logs:'),
                html.Div(id='log-div', style={'color': 'white'}),
            ], style={'margin-left': '35vh', 'margin-top': '0vh', 'width': '50vh'}, className='two columns')
        ],
            style={'width': '110vh', 'height': '20.4vh', 'background-color': 'gray', 'padding': '1vh'}),

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
                    margin=go.layout.Margin(l=40, r=50, t=10, b=35)
                )
            ),
            style={'height': '23vh', 'padding-top': '1vh'},
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
                    margin=go.layout.Margin(l=40, r=50, t=5, b=35)

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
                    margin=go.layout.Margin(l=40, r=50, t=5, b=0)
                )
            ),
            style={'height': '20vh'},
            id='signal-strength-graph'
        )
    ])


    @app.callback(
        dash.dependencies.Output('relayout-data', 'children'),
        [dash.dependencies.Input('activity-graph', 'relayoutData'),
         dash.dependencies.Input('signal-strength-graph', 'relayoutData'),
         dash.dependencies.Input('spectrogram-activity-graph', 'relayoutData'),
         dash.dependencies.Input('farm-dropdown', 'value')])
    def display_selected_data(v1, v2, v3, v4):
        if v1 is not None:
            if "autosize" not in v1 and "xaxis.autorange" not in v1:
                return json.dumps(v1, indent=2)
        if v2 is not None:
            if "autosize" not in v2 and "xaxis.autorange" not in v2:
                return json.dumps(v2, indent=2)
        if v3 is not None:
            if "autosize" not in v3 and "xaxis.autorange" not in v3:
                return json.dumps(v3, indent=2)

        return json.dumps({'autosize': True}, indent=2)


    @app.callback(dash.dependencies.Output('log-div', 'children'),
                  [dash.dependencies.Input('figure-data', 'children')])
    def clean_data(data):
        print("printing log...")
        d = []
        if data is not None:
            d = json.loads(data)
        for i in d:
            signal_size = i['signal_size']
            max_activity_value = i['max_activity_value']
            min_activity_value = i['min_activity_value']
            start_date = i['start_date']
            end_date = i['end_date']
            time_range = i['time_range']
            return html.Div([
                html.P("Number of points in signal: %d" % signal_size),
                html.P("Max activity value: %d" % max_activity_value),
                html.P("Min activity value: %d" % min_activity_value),
                html.P("Start date: %s" % start_date),
                html.P("End date: %s" % end_date),
                html.P("Time range: %s" % time_range)
            ])


    @app.callback(dash.dependencies.Output('intermediate-value', 'children'),
                  [dash.dependencies.Input('farm-dropdown', 'value')])
    def clean_data(file_path):
        if file_path is not None:
            print("saving data in hidden div...")
            path = sys.argv[1] + "\\" + file_path
            h5 = tables.open_file(path, "r")

            serial_numbers = list(set([(x['serial_number']) for x in h5.root.resolution_m.data.iterrows()]))
            print(serial_numbers)
            print("getting data in file...")

            # sort by serial numbers containing data size
            map = {}
            for serial_number in serial_numbers:
                map[serial_number] = len([x['signal_strength_min'] for x in h5.root.resolution_h.data if
                                          x['serial_number'] == serial_number])

            sorted_map = sorted(map.items(), key=operator.itemgetter(1))

            sorted_serial_numbers = []
            for item in sorted_map:
                sorted_serial_numbers.append(item[0])

            sorted_serial_numbers.reverse()

            # data = {'serial_numbers': sorted_serial_numbers, 'data_m': data_m, 'data_w': data_w, 'data_d': data_d,
            #         'data_h': data_h, 'data_h_h': data_h_h, 'data_f': data_f}
            # return json.dumps(data)

            # get famacha score data
            f_id = file_path.split('.')[0]
            path_json = sys.argv[2] + "\\" + f_id + ".json"
            with open(path_json) as f:
                famacha_data = json.load(f)

            path_json_weather = sys.argv[2] + "\\" + f_id.split('_')[0] + "_weather.json"
            with open(path_json_weather) as f_w:
                weather_data = json.load(f_w)

            print("famatcha data available for [%s]" % ','.join(famacha_data.keys()))

            data = {'serial_numbers': sorted_serial_numbers, 'file_path': path, 'famacha': famacha_data, 'weather': weather_data}
            return json.dumps(data)


    @app.callback(
        dash.dependencies.Output('serial-number-dropdown', 'options'),
        [dash.dependencies.Input('intermediate-value', 'children')])
    def update_serial_number_drop_down(intermediate_value):
        if intermediate_value:
            l = json.loads(intermediate_value)
            data = l["serial_numbers"]
            famacha = list(map(int, l['famacha'].keys()))
            s_array = []
            for serial in data:
                if serial in famacha:
                    s_array.append({'label': "%s (famacha data available)" % str(serial), 'value': serial})
                else:
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
        dash.dependencies.Output('figure-data', 'children'),
        [dash.dependencies.Input('serial-number-dropdown', 'value'),
         dash.dependencies.Input('resolution-slider', 'value'),
         dash.dependencies.Input('intermediate-value', 'children'),
         dash.dependencies.Input('relayout-data', 'children')])
    def update_figure(selected_serial_number, value, intermediate_value, relayout_data):
        p = Process(target=thread_activity,
                    args=(q_1, selected_serial_number, value, intermediate_value, relayout_data,))
        p.start()
        result = q_1.get()
        p.join()
        if len(result) > 0:
            return json.dumps(result, cls=plotly.utils.PlotlyJSONEncoder)


    @app.callback(
        dash.dependencies.Output('activity-graph', 'figure'),
        [dash.dependencies.Input('intermediate-value', 'children'),
         dash.dependencies.Input('figure-data', 'children')])
    def update_figure(data_f, data):
        _d = []
        if data is not None:
            _d = json.loads(data)
        _d_f = []
        if data_f is not None:
            _d_f = json.loads(data_f)

        figures = build_activity_graph(_d, _d_f)

        result = {}
        for f in figures:
            result = {
                'data': f[10]['data'],
                'layout': go.Layout(f[10]['layout'])
            }

        return result


    @app.callback(
        dash.dependencies.Output('spectrogram-activity-graph', 'figure'),
        [dash.dependencies.Input('figure-data', 'children'),
         dash.dependencies.Input('window-size-input', 'value'),
         dash.dependencies.Input('transform-radio', 'value')])
    def update_figure(data, window_size, radio):
        j = []
        if data is not None:
            j = json.loads(data)
        result = {}
        for f in j:
            activity = f["activity"]
            time = f["time"]
            relayout = f["relayout_data"]
            p = Process(target=thread_spectrogram, args=(q_3, activity, time, window_size, radio, relayout,))
            p.start()
            result = q_3.get()[3]
            p.join()

        return result


    @app.callback(
        dash.dependencies.Output('signal-strength-graph', 'figure'),
        [dash.dependencies.Input('serial-number-dropdown', 'value'),
         dash.dependencies.Input('resolution-slider', 'value'),
         dash.dependencies.Input('intermediate-value', 'children'),
         dash.dependencies.Input('relayout-data', 'children')])
    def update_figure(selected_serial_number, value, intermediate_value, relayout_data):
        p = Process(target=thread_signal, args=(q_2, selected_serial_number, value, intermediate_value, relayout_data,))
        p.start()
        result = q_2.get()
        p.join()
        return result


    app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/brPBPO.css"})
    app.run_server(debug=True, use_reloader=False)
