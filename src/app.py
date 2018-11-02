# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly.graph_objs as go

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

N = 500
_y = np.array([0,1,2,3])
_x = np.array([np.datetime64('2005-02-25T03:30'),
               np.datetime64('2005-02-25T03:31'),
               np.datetime64('2005-02-25T03:32'),
               np.datetime64('2005-02-25T03:33')])

app.layout = html.Div(children=[
    html.H1(children='farmId'),

    html.Div(children='''
        description.
    '''),

    dcc.Graph(
        figure=go.Figure(
            data=[
                go.Scatter(
                    x=_x,
                    y=_y,
                    name='animal1',
                )
            ]
        ),
        style={'height': 300},
        id='my-graph'
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)
