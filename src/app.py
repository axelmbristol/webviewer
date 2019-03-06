# -*- coding: utf-8 -*-
import glob
import json
import operator
import sys
from datetime import datetime, timedelta
from itertools import groupby
from multiprocessing import Process, Queue
from time import mktime
from time import strptime

import dash
import dash_core_components as dcc
import dash_html_components as html
import flask
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
import pymysql
import requests
import tables
from dash.dependencies import Input, Output
from dateutil.relativedelta import *
from ipython_genutils.py3compat import xrange
from scipy import signal

global sql_db


def get_date_range(layout_data):
    # print(layout_data)
    x_min_epoch = 0.0
    x_max_epoch = 19352963810.0
    try:
        xaxis_autorange = bool(layout_data["xaxis.autorange"])
    except (KeyError, TypeError):
        xaxis_autorange = False
    try:
        auto_range = layout_data["autosize"]
    except (KeyError, TypeError):
        auto_range = False
    try:
        x_min = str(layout_data["xaxis.range[0]"])
        if len(x_min.split(":")) == 2:
            x_min = x_min + ":00"
        if "." not in x_min:
            x_min = x_min + ".00"
        x_min_epoch = int(mktime(strptime(x_min, '%Y-%m-%d %H:%M:%S.%f')))
    except (KeyError, TypeError):
        x_min = None
    try:
        x_max = str(layout_data["xaxis.range[1]"])
        if len(x_max.split(":")) == 2:
            x_max = x_max + ":00"
        if "." not in x_max:
            x_max = x_max + ".00"
        x_max_epoch = int(mktime(strptime(x_max, '%Y-%m-%d %H:%M:%S.%f')))
    except (KeyError, TypeError):
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
    result = (dt2 - dt1).total_seconds()
    return result


def find_appropriate_resolution(duration):
    value = None
    if 0 < duration <= 3 * 3600.0:
        value = 5
    if 3 * 3600.0 < duration <= 4 * 3600.0:
        value = 5
    if 4 * 3600.0 < duration <= 259200.0:
        value = 3
    if 259200.0 < duration <= 604800.0:
        value = 3
    if 604800.0 < duration <= 5 * 604800.0:
        value = 2
    if 5 * 604800.0 < duration <= 10 * 604800.0:
        value = 1
    if duration > 10 * 604800.0:
        value = 1
    return value


def compare_dates(d1, d2):
    d1_ = datetime.strptime(d1, '%d/%m/%Y').strftime('%Y-%m-%d')
    d2_ = d2.split('T')[0]
    return d1_ == d2_


def chunks(l, n):
    n = max(1, n)
    return (l[i:i + n] for i in xrange(0, len(l), n))


def is_in_period(start, famacha_day, n):
    datetime_start = datetime.strptime(start, '%Y-%m-%d')
    datetime_famacha = datetime.strptime(famacha_day, '%d/%m/%Y')
    margin = timedelta(days=n)
    return datetime_start - margin <= datetime_famacha <= datetime_start + margin


def build_weather_trace(time, data_f):
    try:
        print("weather data available for [%s]" % ','.join(data_f['weather'].keys()))
        weather_s = [None] * len(time)
        date_weather = data_f['weather'].keys()
        for i, t in enumerate(time):
            day = t.split('T')[0]
            if day in date_weather:
                list = data_f['weather'][day]
                mean = 0
                for item in list:
                    mean += int(item['humidity'])
                weather_s[i] = mean / len(list)

        print(weather_s)
        return go.Scatter(
            x=time,
            y=weather_s,
            name='humidity',
            opacity=0.01,
            yaxis='y2',
            fill='tozeroy',
            mode='none'
        )
    except KeyError as e:
        print(e)


def build_famacha_trace(traces, data_f, resolution):
    try:
        time = traces[0]['x']
        famacha_s = [None] * len(time)
        serial = traces[0]['name']
        date_ = data_f['famacha'][serial].keys()
        date_famacha = [datetime.strptime(d, '%d/%m/%Y').strftime('%Y-%m-%d') for d in date_]
        print("resolution=%d", resolution)
        for i, t in enumerate(time):
            day = t.split('T')[0]
            if resolution == 'resolution_w':
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
            name='famacha score',
            # connectgaps=True,
            opacity=0.2,
            yaxis='y2'
        )
    except (KeyError, TypeError) as e:
        print(e)


def interpolate(input_activity):
    try:
        i = np.array(input_activity, dtype=np.float)
        s = pd.Series(i)
        s = s.interpolate(method='cubic')
        return s.tolist()
    except ValueError as e:
        return input_activity


def build_activity_graph(data, data_f, dragmode):
    layout = None
    figures = []
    for d in data:
        # x_max = d["x_max"]
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
        if fig_famacha is not None:
            traces.append(fig_famacha)
        # if x_max is not None:
        x_axis_data = {'title': 'Time'}
        if range_d['x_min'] is not None:
            x_axis_data['autorange'] = range_d['xaxis_autorange']
            x_axis_data['range'] = [range_d['x_min'], range_d['x_max']]

        print('dragmode', dragmode)
        enable_dragmode = None
        if dragmode is not None and "dragmode" in dragmode:
            enable_dragmode = "pan"

        print("x axis data is", x_axis_data)

        layout = go.Layout(xaxis=x_axis_data,
                           yaxis={'title': 'Activity level/Accelerometer count'},
                           yaxis2=dict(
                               nticks=3,
                               overlaying='y',
                               side='right'
                           ),
                           yaxis3=dict(
                               overlaying='y',
                               side='right'
                           ),
                           dragmode=enable_dragmode,
                           autosize=range_d['auto_range'],
                           legend=dict(y=0.98), margin=go.layout.Margin(l=60, r=50, t=5, b=40))
        figures.append(
            [{'thread_activity': True}, {'signal_size': signal_size}, {'min_activity_value': min_activity_value},
             {'max_activity_value': max_activity_value}, {'start_date': start_date},
             {'end_date': end_date}, {'time_range': time_range},
             {'activity': activity}, {'time': time}, {'relayout_data': relayout_data}, {
                 'data': traces,
                 'layout': layout
             }])
        # else:
        #     layout = go.Layout(xaxis={'autorange': True},
        #                        yaxis={'title': 'Activity level/Accelerometer count',
        #                               'autorange': True},
        #                        autosize=True,
        #                        yaxis2=dict(
        #                            nticks=3,
        #                            overlaying='y',
        #                            side='right'
        #                        ),
        #                        legend=dict(y=0.98), margin=go.layout.Margin(l=60, r=50, t=5, b=40))
        #     figures.append(
        #         [{'thread_activity': True}, {'signal_size': signal_size}, {'min_activity_value': min_activity_value},
        #          {'max_activity_value': max_activity_value}, {'start_date': start_date},
        #          {'end_date': end_date}, {'time_range': time_range},
        #          {'activity': activity}, {'time': time}, {'relayout_data': relayout_data}, {
        #              'data': traces,
        #              'layout': layout
        #          }])

    return figures, layout


def pad(l, size, padding):
    return l + [padding] * abs((len(l) - size))


def get_resolution_string(value):
    result = 'resolution_m'
    if value == 0:
        result = 'resolution_m'
    if value == 1:
        result = 'resolution_w'
    if value == 2:
        result = 'resolution_d'
    if value == 3:
        result = 'resolution_h'
    if value == 4:
        result = 'resolution_min'
    if value == 5:
        result = 'resolution_min'
    return result


def thread_activity_herd(q_4, intermediate_value, cubic_interpolation, relayout_data):
    data = None
    range_d = get_date_range(json.loads(relayout_data))
    x_max_epoch = range_d['x_max_epoch']
    x_min_epoch = range_d['x_min_epoch']
    x_max = range_d['x_max']
    resolution_string = 'resolution_w'
    if range_d['x_max'] is not None:
        value = find_appropriate_resolution(get_elapsed_time_seconds(x_min_epoch, x_max_epoch))
        resolution_string = get_resolution_string(value)

    if intermediate_value is not None:
        raw = json.loads(intermediate_value)

        file_path = raw["file_path"]
        farm_id = raw["farm_id"]

        if sys.argv[3] == 'h5':
            print("opening file in thread test")
            h5 = tables.open_file(file_path, "r")
            data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                     x['first_sensor_value'])
                    for x in h5.root.resolution_m.data if x_min_epoch < x['timestamp'] < x_max_epoch]

        if sys.argv[3] == 'sql':
            rows = execute_sql_query(
                "SELECT timestamp_s, first_sensor_value, serial_number FROM %s_%s WHERE timestamp BETWEEN %s AND %s" %
                (farm_id, resolution_string, x_min_epoch, x_max_epoch))
            data = [(x['timestamp_s'], x['first_sensor_value'], x['serial_number']) for x in rows]

    activity_list = []
    data_list = []

    if data is not None:
        data_list = [list(v) for l, v in groupby(sorted(data, key=lambda x: x[2]), lambda x: x[2])]

    records = []
    time = None
    max = 0
    for item in data_list:
        serial = item[0][2]
        a = [(x[1]) for x in item]
        if len(a) < 5:
            continue
        if len(a) > max:
            max = len(a)
            time = [(x[0]) for x in item]
        records.append((a, serial))

    ids = []
    for i in records:
        a = pad(i[0], max, None)
        # a = i[0]
        # if len(a) != max:
        #     continue
        ids.append(i[1])
        if 'cubic' in cubic_interpolation:
            activity_list.append(interpolate(a))
        else:
            activity_list.append(a)

    print(len(ids), ids)
    print(activity_list)
    print(time)

    if len(activity_list) > 0:
        traces = []
        signal_size = len(activity_list[0])
        max_activity_value = 0
        min_activity_value = 0
        s_d = time[0]
        e_d = time[len(time) - 1]
        d1 = (datetime.strptime(s_d, '%Y-%m-%dT%H:%M') - datetime(1970, 1, 1)).total_seconds()
        d2 = (datetime.strptime(e_d, '%Y-%m-%dT%H:%M') - datetime(1970, 1, 1)).total_seconds()
        start_date = datetime.fromtimestamp(d1).strftime('%d/%m/%Y %H:%M:%S')
        end_date = datetime.fromtimestamp(d2).strftime('%d/%m/%Y %H:%M:%S')
        time_range = get_elapsed_time_string(d1, d2)
        if resolution_string == 'resolution_d':
            time = [t.split('T')[0] for t in time]

        serials = [".." + str(v)[5:] for v in ids]
        print(serials)

        trace = go.Heatmap(z=activity_list,
                           x=time,
                           y=serials,
                           colorscale='Viridis')
        traces.append(trace)
        _d = []
        _d.append({"activity": activity_list[0],
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
                   'resolution': resolution_string})
        q_4.put(_d)

    if q_4.empty():
        q_4.put([])


def thread_activity(q_1, selected_serial_number, intermediate_value, relayout_data, cubic_interpolation):
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
            resolution_string = 'resolution_w'
            if range_d['x_max'] is not None:
                value = find_appropriate_resolution(get_elapsed_time_seconds(x_min_epoch, x_max_epoch))
                resolution_string = get_resolution_string(value)
            raw = json.loads(intermediate_value)
            file_path = raw["file_path"]
            farm_id = raw["farm_id"]

            if sys.argv[3] == 'h5':
                print("opening file in thread test")
                h5 = tables.open_file(file_path, "r")

            if sys.argv[3] == 'h5':
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['first_sensor_value'])
                        for x in h5.root.resolution_m.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if sys.argv[3] == 'sql':
                rows = execute_sql_query(
                    "SELECT timestamp, first_sensor_value FROM %s_%s WHERE serial_number=%s AND timestamp BETWEEN %s AND %s" %
                    (farm_id, resolution_string, i, x_min_epoch, x_max_epoch))
                data = [
                    (datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), x['first_sensor_value'])
                    for x in rows]

            activity = [(x[1]) for x in data]
            time = [(x[0]) for x in data]

            print(activity)
            print(time)

            activity, time = scale_dataset_to_screen_size(activity, time, 960)

            if len(activity) and len([x for x in activity if x is not None]) > 0:
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

                if resolution_string == 'resolution_d':
                    time = [t.split('T')[0] for t in time]

                if 'cubic' in cubic_interpolation:
                    activity = interpolate(activity)

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
                           'resolution': resolution_string})
                q_1.put(_d)
    if q_1.empty():
        q_1.put([])


def thread_signal(q_2, selected_serial_number, intermediate_value, relayout_data):
    if intermediate_value is None:
        selected_serial_number = []
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
            resolution_string = 'resolution_w'
            if range_d['x_max'] is not None:
                value = find_appropriate_resolution(get_elapsed_time_seconds(x_min_epoch, x_max_epoch))
                resolution_string = get_resolution_string(value)

            raw = json.loads(intermediate_value)

            file_path = raw["file_path"]
            farm_id = raw["farm_id"]
            if sys.argv[3] == 'h5':
                print("opening file in thread signal")
                h5 = tables.open_file(file_path, "r")

            if sys.argv[3] == 'h5':
                data = [(datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['signal_strength_max'], x['signal_strength_min'])
                        for x in h5.root.resolution_m.data if
                        x['serial_number'] == i and x_min_epoch < x['timestamp'] < x_max_epoch]
            if sys.argv[3] == 'sql':
                if resolution_string == 'resolution_min':
                    rows = execute_sql_query(
                        "SELECT timestamp, signal_strength FROM %s_%s WHERE serial_number=%s AND timestamp BETWEEN %s AND %s" %
                        (farm_id, resolution_string, i, x_min_epoch, x_max_epoch))
                    data = [
                        (datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'), x['signal_strength'])
                        for x in rows]
                else:
                    rows = execute_sql_query(
                        "SELECT timestamp, signal_strength_max, signal_strength_min FROM %s_%s WHERE serial_number=%s AND timestamp BETWEEN %s AND %s" %
                        (farm_id, resolution_string, i, x_min_epoch, x_max_epoch))
                    data = [
                        (datetime.utcfromtimestamp(x['timestamp']).strftime('%Y-%m-%dT%H:%M'),
                         x['signal_strength_max'], x['signal_strength_min'])
                        for x in rows]

            time = [(x[0]) for x in data]
            fig_weather = build_weather_trace(time, raw)
            traces.append(fig_weather)

            if resolution_string is not 'resolution_min':
                signal_strength_min = [(x[2]) for x in data]
                signal_strength_max = [(x[1]) for x in data]
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
                                yaxis2=dict(
                                    anchor='x',
                                    overlaying='y',
                                    side='right',
                                    title='Humidity'
                                ),
                                autosize=range_d['auto_range'],
                                showlegend=False,
                                # legend=dict(y=1, x=0),
                                margin=go.layout.Margin(l=60, r=50, t=5, b=40)
                                ),
            'resolution': "resolution_d"
        })
    else:
        q_2.put({
            'data': traces,
            'layout': go.Layout(xaxis={'title': 'Time', 'autorange': True}, yaxis={'title': 'RSSI(received signal '
                                                                                            'strength in)',
                                                                                   'autorange': True},
                                yaxis2=dict(
                                    anchor='x',
                                    overlaying='y',
                                    side='right',
                                    title='Humidity'
                                ),
                                autosize=True,
                                showlegend=False,
                                # legend=dict(y=1, x=0),
                                margin=go.layout.Margin(l=60, r=50, t=5, b=40)
                                ),
            'resolution': "resolution_d"
        })


def thread_spectrogram(q_3, activity, time, window_size, radio, relayout):
    j = json.loads(relayout)
    range_d = get_date_range(j)
    print("thread_spectrogram")
    # print(activity, time, window_size, radio, relayout)
    x_max = range_d['x_max']
    traces = []
    # print("activity in spec", activity)
    if len(activity) > 1 and None not in activity:
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
                xaxis={'range': [range_d['x_min'], range_d['x_max']],
                       'autorange': range_d['xaxis_autorange']},
                yaxis={'title': 'Frequency'},
                autosize=range_d['auto_range'],
                showlegend=True, legend=dict(y=0.98),
                margin=go.layout.Margin(l=60, r=50, t=5, b=40))
        }])
    else:
        layout_activity = go.Layout(
            xaxis={'autorange': True},
            yaxis={'title': 'Frequency', 'autorange': True},
            autosize=True,
            showlegend=True, legend=dict(y=0.98),
            margin=go.layout.Margin(l=60, r=50, t=5, b=40))

        q_3.put([{'thread_activity': True}, {'activity': activity}, {'time': time}, {
            'data': traces,
            'layout': layout_activity
        }])


def connect_to_sql_database(db_server_name="localhost", db_user="axel", db_password="Mojjo@2015",
                            db_name="south_africa_test5",
                            char_set="utf8mb4", cusror_type=pymysql.cursors.DictCursor):
    # print("connecting to db %s..." % db_name)
    global sql_db
    sql_db = pymysql.connect(host=db_server_name, user=db_user, password=db_password,
                             db=db_name, charset=char_set, cursorclass=cusror_type)
    return sql_db


def execute_sql_query(query, records=None, log_enabled=False):
    try:
        sql_db = connect_to_sql_database()
        cursor = sql_db.cursor()
        if records is not None:
            print("SQL Query: %s" % query, records)
            cursor.executemany(query, records)
        else:
            if log_enabled:
                print("SQL Query: %s" % query)
            cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            if log_enabled:
                print("SQL Answer: %s" % row)
        return rows
    except Exception as e:
        print("Exeception occured:{}".format(e))


def get_figure_width(fig_id="activity-graph", url="http://127.0.0.1:8050/"):
    r = requests.get(url)
    # html_string = r.content
    # print(html_string)
    # parsed_html = BeautifulSoup(html_string, 'html.parser')
    # data = parsed_html.find(id=fig_id)
    return -1


def scale_dataset_to_screen_size(activity_list, timestamp_list, width):
    print("screen width is %d. There are %d points in activity list." % (width, len(activity_list)))
    n_samples = len(activity_list)
    n_timestamps_per_pixel = n_samples / width
    binned_activity_list = [None for _ in range(width)]
    binned_timestamp_list = [None for _ in range(width)]
    try:
        for i in xrange(0, len(activity_list)):
            binned_idx = round(i / n_timestamps_per_pixel)
            binned_timestamp_list[binned_idx] = timestamp_list[i]
            if activity_list[i] is None:
                continue
            # need to initialize value for later increment
            if binned_activity_list[binned_idx] is None:
                binned_activity_list[binned_idx] = 0
            binned_activity_list[binned_idx] += activity_list[i]
    except IndexError as e:
        print(len(binned_activity_list), binned_idx, e, binned_activity_list)
    print("length after scale to screen of width %d is %d." % (width, len(binned_activity_list)))
    print(binned_activity_list)
    print(binned_timestamp_list)

    if None in binned_timestamp_list:
        return activity_list, timestamp_list

    return binned_activity_list, binned_timestamp_list


def build_dashboard_layout():
    return html.Div([
        html.Div([html.Pre(id='relayout-data-last-config', style={'display': 'none'})]),
        html.Div(id='output'),
        # Hidden div inside the app that stores the intermediate value
        html.Div(id='intermediate-value', style={'display': 'none'}),
        html.Div(id='figure-data', style={'display': 'none'}),
        html.Div(id='figure-data-herd', style={'display': 'none'}),
        html.Img(id='logo', style={'max-width': '10%', 'min-width': '10%'},
                 src='http://dof4zo1o53v4w.cloudfront.net/s3fs-public/styles/logo/public/logos/university-of-bristol'
                     '-logo.png?itok=V80d7RFe'),
        html.Br(),
        html.Big(
            children="PhD Thesis: Deep learning of activity monitoring data for disease detection to support "
                     "livestock farming in resource-poor communities in Africa."),
        html.Br(),
        html.Br(),
        # html.B(id='farm-title'),
        html.Div([html.Pre(id='relayout-data', style={'display': 'none'})]),

        html.Div([
            html.Div([
                html.Label('Farm selection:', style={'color': 'white', 'font-weight': 'bold'}),
                dcc.Dropdown(
                    id='farm-dropdown',
                    options=farm_array,
                    placeholder="Select farm...",
                    style={'width': '350px', 'margin-bottom': '10px'}
                    # value=40121100718
                ),
                html.Label('Animal selection:', style={'color': 'white', 'font-weight': 'bold'}),
                dcc.Dropdown(
                    id='serial-number-dropdown',
                    options=[],
                    multi=False,
                    placeholder="Select animal...",
                    style={'width': '350px', 'margin-bottom': '20px'}
                    # value=40121100718
                ),

                html.Div([
                    html.Div([
                        html.Label('Transform:', style={'min-width': '100px', 'color': 'white', 'font-weight': 'bold'}),
                        dcc.RadioItems(
                            id='transform-radio',
                            options=[
                                {'label': 'STFT', 'value': 'STFT'},
                                {'label': 'CWT', 'value': 'CWT'}
                            ],
                            labelStyle={'display': 'inline-block', 'color': 'white'},
                            value='CWT')],
                        style={'margin-bottom': '30px', 'margin-left': '0px', 'min-width': '120px', 'display': 'inline-block'}
                    ),
                    html.Div([
                        html.Label('Window size:', style={'min-width': '100px', 'margin-left': '0vh', 'color': 'white',
                                                          'font-weight': 'bold'}),
                        dcc.Input(
                            id='window-size-input',
                            placeholder='Input size of window here...',
                            type='text',
                            value='40',
                            style={'min-width': '50px', 'max-width': '50px', 'height': '20px', 'margin-left': '0vh'}
                        )],
                        style={'margin-bottom': '30px', 'margin-left': '10px', 'min-width': '120px',
                               'display': 'inline-block'}
                    ),

                    html.Div([
                        html.Label('Interpolation:',
                                   style={'min-width': '100px', 'margin-left': '0vh', 'color': 'white',
                                          'font-weight': 'bold'}),
                        dcc.Checklist(
                            id='cubic-interpolation',
                            options=[
                                {'label': 'Cubic', 'value': 'cubic'}
                            ],
                            values=[],
                            style={'margin-top': '-50px', 'height': '20px', 'min-width': '100px', 'margin-left': '0px',
                                   'color': 'white',
                                   'font-weight': 'bold', 'display': 'inline-block'}
                        )
                    ],
                        style={'margin-bottom': '30px', 'margin-left': '0px', 'min-width': '120px',
                               'display': 'inline-block'}
                    ),

                ],
                    style={'max-height': '10px', 'min-height': '10px', 'max-width': '400px', 'min-width': '400px', 'margin-bottom': '0px'}
                )
            ], className='two columns'),

            html.Div([
                # html.Label('logs:'),
                html.Div(id='log-div', style={'max-width': '500px', 'min-width': '500px', 'color': 'white', 'background-color': 'red'}),
            ], style={'margin-left': '35px', 'margin-top': '0vh', 'width': '50vh'}, className='two columns')
        ], id='dashboard',
            style={'position': 'relative', 'width': '100%', 'height': '200px', 'min-height': '200px',
                   'max-height': '200px', 'background-color': 'gray', 'padding-left': '25px',  'padding-bottom': '10px', 'padding-top': '5px', 'margin': '0vh'}),

        html.Div([
            html.Big(
                id="no-farm-label",
                children="No farm selected.")
        ], style={'width': '100%', 'text-align': 'center', 'margin-top': '5vh'})

    ])


def get_side_by_side_div(div_l, div_r):
    return html.Div([
        html.Div([div_l], style={'height': '200px', 'width': '800px', 'float': 'left'}),
        html.Div([div_r], style={'height': '200px', 'width': '800px', 'float': 'right'})
    ],
        style={'height': '400px', 'width': '1920px'})


def build_graphs_layout():
    return html.Div([

        get_side_by_side_div(
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
                        margin=go.layout.Margin(l=0, r=0, t=0, b=0)
                    )
                ),
                style={'padding-top': '0vh'},
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
                        margin=go.layout.Margin(l=0, r=0, t=0, b=0)
                    )
                ),
                style={'padding-top': '0vh'},
                id='activity-graph-herd'
            ))
        ,

        get_side_by_side_div(
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
        )

    ])


def build_default_app_layout(app):
    app.layout = html.Div(
        [
            build_dashboard_layout(), build_graphs_layout()
        ], id='main-div', style={'max-width': '1920px', 'min-width': '1920px'})


def check_dragmode(layout_dict_list):
    for layout_dict in layout_dict_list:
        if layout_dict is None:
            continue
        if 'dragmode' in layout_dict:
            return True
    return False


if __name__ == '__main__':
    print("dash ccv %s" % dcc.__version__)
    print(sys.argv)
    q_1 = Queue()
    q_2 = Queue()
    q_3 = Queue()
    q_4 = Queue()
    con = False
    farm_array = []

    if sys.argv[3] == 'h5':
        h5_files_in_data_directory = glob.glob("%s\*.h5" % sys.argv[1])
        json_files_in_data_directory = glob.glob("%s\*.json" % sys.argv[2])
        print(h5_files_in_data_directory)
        print(json_files_in_data_directory)
        for s in h5_files_in_data_directory:
            split = s.split("\\")
            farm_name = split[len(split) - 1]
            farm_array.append({'label': str(farm_name), 'value': farm_name})

    if sys.argv[3] == 'sql':
        db_name = "south_africa_test5"
        db_server_name = "localhost"
        db_user = "axel"
        db_password = "Mojjo@2015"
        char_set = "utf8mb4"
        cusror_type = pymysql.cursors.DictCursor

        sql_db = pymysql.connect(host=db_server_name, user=db_user, password=db_password)
        connect_to_sql_database(db_server_name, db_user, db_password, db_name, char_set, cusror_type)
        tables = execute_sql_query("SHOW TABLES", log_enabled=True)
        farm_names = []
        for table in tables:
            name = table["Tables_in_%s" % db_name].split("_")
            farm_names.append("%s_%s" % (name[0], name[1]))
        farm_names = list(set(farm_names))

        for farm_name in farm_names:
            farm_array.append({'label': str(farm_name), 'value': farm_name})

    print('init dash...')
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    server = flask.Flask(__name__)
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets, server=server)
    build_default_app_layout(app)
    # server = app.server
    app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/brPBPO.css"})


    @app.callback(
        dash.dependencies.Output('relayout-data-last-config', 'children'),
        [Input('relayout-data', 'children')
         ])
    def display_selected_data(v1):
        if v1 is not None:
            d = json.loads(v1)
            if 'dragmode' in d and d['dragmode'] == 'pan':
                print('do not update field!')
                # raise Exception("hack for skipping text field update...")
                raise dash.exceptions.PreventUpdate()
            else:
                return json.dumps(v1, indent=2)

    @app.callback(
        Output('relayout-data', 'children'),
        [Input('activity-graph', 'relayoutData'),
         Input('signal-strength-graph', 'relayoutData'),
         Input('spectrogram-activity-graph', 'relayoutData')
         ],
        [dash.dependencies.State('relayout-data-last-config', 'children')]
    )
    def display_selected_data(v1, v2, v3, v4):
        new_layout_data = json.dumps({'autosize': True}, indent=2)

        print("v1 v2 v3 are:", v1, v2, v3)
        if check_dragmode([v1, v2, v3]):
            print("get previous zoom")
            v4 = v4.rstrip()
            last = json.loads(v4).rstrip()
            last = json.loads(last)
            print("last config:", last)
            last['dragmode'] = "pan"
            new_layout_data = json.dumps(last, indent=2)
            return new_layout_data

        if v1 is not None:
            if "autosize" not in v1 and "xaxis.autorange" not in v1:
                new_layout_data = json.dumps(v1, indent=2)
        if v2 is not None:
            if "autosize" not in v2 and "xaxis.autorange" not in v2:
                new_layout_data = json.dumps(v2, indent=2)
        if v3 is not None:
            if "autosize" not in v3 and "xaxis.autorange" not in v3:
                new_layout_data = json.dumps(v3, indent=2)

        print("new layout data is:", new_layout_data)

        return new_layout_data


    @app.callback(Output('log-div', 'children'),
                  [Input('figure-data', 'children'),
                   Input('serial-number-dropdown', 'options'),
                   Input('farm-dropdown', 'value')])
    def clean_data(data, serial, farm):

        print("printing log...")
        print(farm)
        j = json.dumps(serial)
        individual_with_famacha_data = str(j).count('(famacha data available)')
        print(individual_with_famacha_data)
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

        if not d and farm is not None:
            return html.Div([
                html.Br(),
                html.P("Individual in the farm: %d" % len(serial)),
                html.P("Individual with famacha data available: %s" % individual_with_famacha_data)
            ])


    @app.callback(Output('intermediate-value', 'children'),
                  [Input('farm-dropdown', 'value')])
    def clean_data(farm_id):
        if farm_id is not None:
            print("saving data in hidden div...")
            path = sys.argv[1] + "\\" + farm_id
            if sys.argv[3] == 'h5':
                h5 = tables.open_file(path, "r")
                serial_numbers = list(set([(x['serial_number']) for x in h5.root.resolution_m.data.iterrows()]))
                print(serial_numbers)
                print("getting data in file...")

                # sort by serial numbers containing data size
                map = {}
                for serial_number in serial_numbers:
                    map[serial_number] = len([x['signal_strength_min'] for x in h5.root.resolution_h.data if
                                              x['serial_number'] == serial_number])

            if sys.argv[3] == 'sql':
                serial_numbers_rows = execute_sql_query("SELECT DISTINCT(serial_number) FROM %s_resolution_m" % farm_id)
                serial_numbers = [x['serial_number'] for x in serial_numbers_rows]
                print(serial_numbers)
                print("getting data in file...")
                map = {}
                for serial_number in serial_numbers:
                    rows = execute_sql_query(
                        "SELECT * FROM %s_resolution_w WHERE serial_number=%s" % (farm_id, serial_number),
                        log_enabled=False)
                    map[serial_number] = len(rows)

            sorted_map = sorted(map.items(), key=operator.itemgetter(1))
            sorted_serial_numbers = []
            for item in sorted_map:
                sorted_serial_numbers.append(item[0])

            sorted_serial_numbers.reverse()
            f_id = farm_id.split('.')[0]
            path_json = sys.argv[2] + "\\" + f_id + ".json"
            famacha_data = {}

            try:
                with open(path_json) as f:
                    famacha_data = json.load(f)
            except FileNotFoundError as e:
                print(e)

            path_json_weather = sys.argv[2] + "\\" + f_id.split('_')[0] + "_weather.json"
            weather_data = {}
            try:
                with open(path_json_weather) as f_w:
                    weather_data = json.load(f_w)
            except FileNotFoundError as e:
                print(e)

            data = {'serial_numbers': sorted_serial_numbers, 'file_path': path, 'farm_id': farm_id,
                    'famacha': famacha_data, 'weather': weather_data}
            return json.dumps(data)


    @app.callback(
        Output('serial-number-dropdown', 'options'),
        [Input('intermediate-value', 'children')])
    def update_serial_number_drop_down(intermediate_value):
        if intermediate_value:
            l = json.loads(intermediate_value)
            data = l["serial_numbers"]
            keys = l['famacha'].keys()
            print(keys)
            famacha = list(map(int, keys))
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
        Output('figure-data', 'children'),
        [Input('serial-number-dropdown', 'value'),
         Input('intermediate-value', 'children'),
         Input('cubic-interpolation', 'values'),
         Input('relayout-data', 'children')])
    def update_figure(selected_serial_number, intermediate_value, cubic_interp, relayout_data):
        if intermediate_value is not None:
            global sql_db
            p = Process(target=thread_activity,
                        args=(q_1, selected_serial_number, intermediate_value, relayout_data, cubic_interp,))
            p.start()
            result = q_1.get(timeout=20)
            p.join()
            if len(result) > 0:
                return json.dumps(result, cls=plotly.utils.PlotlyJSONEncoder)


    @app.callback(
        Output('figure-data-herd', 'children'),
        [Input('intermediate-value', 'children'),
         Input('cubic-interpolation', 'values'),
         Input('relayout-data', 'children')])
    def update_figure(intermediate_value, cubic_interp, relayout_data):
        global sql_db
        p = Process(target=thread_activity_herd,
                    args=(q_4, intermediate_value, cubic_interp, relayout_data,))
        p.start()
        result = q_4.get(timeout=20)
        p.join()
        if len(result) > 0:
            return json.dumps(result, cls=plotly.utils.PlotlyJSONEncoder)


    @app.callback(
        Output('activity-graph', 'figure'),
        [Input('intermediate-value', 'children'),
         Input('figure-data', 'children'),
         Input('activity-graph', 'relayoutData')])
    def update_figure(data_f, data, last):
        _d = []
        if data is not None:
            _d = json.loads(data)
        _d_f = []
        if data_f is not None:
            _d_f = json.loads(data_f)
        figures, layout = build_activity_graph(_d, _d_f, last)
        for f in figures:
            result = {
                'data': f[10]['data'],
                'layout': go.Layout(f[10]['layout'])
            }

            return result
        return {}


    @app.callback(
        Output('activity-graph-herd', 'figure'),
        [Input('figure-data-herd', 'children')])
    def update_figure(data):
        result = {
            'data': [],
            'layout': go.Layout(xaxis=dict(ticks=''),
                                yaxis=dict(ticks='', nticks=3))
        }

        if data is not None:
            j = json.loads(data)
            range_d = j[0]["range_d"]
            # ticks = len(j[0]['traces'][0]['y'])
            result = {
                'data': j[0]['traces'],
                'layout': go.Layout(xaxis=dict(ticks=''),
                                    yaxis=dict(ticks=''))
            }
        print('result', result)
        return result


    # @app.callback(
    #     Output('spectrogram-activity-graph', 'style'),
    #     [Input('spectrogram-activity-graph', 'figure')])
    # def hide_graph(spectrogram_activity_graph):
    #     if len(spectrogram_activity_graph['data']) == 0:
    #         return {'display': 'none'}

    @app.callback(
        Output('spectrogram-activity-graph', 'figure'),
        [Input('figure-data', 'children'),
         Input('cubic-interpolation', 'values'),
         Input('window-size-input', 'value'),
         Input('transform-radio', 'value')])
    def update_figure(data, interpolation, window_size, radio):
        # if 'cubic' in interpolation:
        j = []
        if data is not None:
            j = json.loads(data)
        result = {
            'data': [],
            'layout': go.Layout(xaxis={'autorange': True},
                                yaxis={'autorange': True, 'title': 'Frequency'},
                                autosize=True,
                                legend=dict(y=0.98), margin=go.layout.Margin(l=60, r=50, t=5, b=40))
        }
        for f in j:
            activity = f["activity"]
            time = f["time"]
            relayout = f["relayout_data"]
            p = Process(target=thread_spectrogram, args=(q_3, activity, time, window_size, radio, relayout,))
            p.start()
            result = q_3.get(timeout=20)[3]
            p.join()

        return result


    @app.callback(
        Output('signal-strength-graph', 'figure'),
        [Input('serial-number-dropdown', 'value'),
         Input('intermediate-value', 'children'),
         Input('relayout-data', 'children')])
    def update_figure(selected_serial_number, intermediate_value, relayout_data):
        p = Process(target=thread_signal, args=(q_2, selected_serial_number, intermediate_value, relayout_data,))
        p.start()
        result = q_2.get(timeout=20)
        p.join()
        return result


    # @app.callback(
    #     Output('signal-strength-graph', 'style'),
    #     [Input('signal-strength-graph', 'figure')])
    # def hide_graph(signal_strength_graph):
    #     if len(signal_strength_graph['data']) == 0:
    #         return {'display': 'none', 'height': '20vh'}
    #     else:
    #         return {'height': '20vh'}


    # @app.callback(
    #     Output('activity-graph-herd', 'style'),
    #     [Input('activity-graph-herd', 'figure')])
    # def hide_graph(activity_graph_herd):
    #     if len(activity_graph_herd['data']) == 0:
    #         return {'display': 'none', 'height': '80vh'}
    #     else:
    #         return {'height': '80vh'}


    # @app.callback(
    #     Output('activity-graph', 'style'),
    #     [Input('activity-graph', 'figure')])
    # def hide_graph(activity_graph):
    #     if 'data' not in activity_graph or len(activity_graph['data']) == 0:
    #         return {'display': 'none', 'height': '23vh'}
    #     else:
    #         return {'height': '23vh'}


    # @app.callback(
    #     Output('spectrogram-activity-graph', 'style'),
    #     [Input('spectrogram-activity-graph', 'figure')])
    # def hide_graph(activity_graph):
    #     if len(activity_graph['data']) == 0:
    #         return {'display': 'none', 'height': '23vh'}
    #     else:
    #         return {'height': '23vh'}


    @app.callback(
        Output('no-farm-label', 'style'),
        [Input('farm-dropdown', 'value')])
    def hide_graph(value):
        if value is not None:
            return {'display': 'none', 'height': '0%'}


    # @app.callback(
    #     Output('no-farm-label-1', 'style'),
    #     [Input('farm-dropdown', 'value')])
    # def hide_graph(value):
    #     if value is not None:
    #         return {'display': 'none', 'height': '0%'}
    #
    #
    # @app.callback(
    #     Output('no-farm-label-2', 'style'),
    #     [Input('farm-dropdown', 'value')])
    # def hide_graph(value):
    #     if value is not None:
    #         return {'display': 'none', 'height': '0%'}

    app.run_server(debug=True, use_reloader=False)
