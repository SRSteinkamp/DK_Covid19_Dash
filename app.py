import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pandas as pd
from dash.dependencies import Input, Output, State
import requests
import io
import re

app = dash.Dash()
server = app.server

# https://api.statbank.dk/console#tableinfo


def get_tableinformation():
    r = requests.post('https://api.statbank.dk/v1/tableinfo',
                  json={"table": "SMIT4", "format": "JSON", "lang": "en"})
    table_info = r.json()
    return table_info

def get_region_info(table_info):
    dropdown_regions = [{'value': ii['id'], 'label': ii['text']}
                        for ii in table_info['variables'][1]['values']]
    return dropdown_regions

def get_data_info(table_info):
    data_info = [{'value': ii['id'], 'label': ii['text']}
                   for ii in table_info['variables'][0]['values']]
    return data_info

def get_available_dates(table_info):
    available_dates = [ii['id'] for ii in table_info['variables'][2]['values']]

    return available_dates


# Get information about the database a priori.
table_info = get_tableinformation()
# Find regions and create a dropdown menu from it.
dropdown_regions = get_region_info(table_info)
# Find the data types (i.e. cases per 100.000 or raw)
data_info = get_data_info(table_info)
# Create a direct mapping between database code and value
data_info_dict = {ii['value']: ii['label'] for ii in  data_info}
# Find the available dates, which is needed to correctly send requests.
available_dates = get_available_dates(table_info)


def transform_date(date):
    part = date.split('-')
    new_date = '{}M{}D{}'.format(part[0], part[1], part[2])
    return new_date


def sub_date(date):
    return re.sub('[M,D]', '-', date)


def get_dates(start="2020-03-21", end="2021-03-09",
              available_dates=available_dates):
    drange = pd.date_range(start=start, end=end)
    drange = [transform_date(str(ii)[:10]) for ii in drange]
    drange = [d for d in drange if d in available_dates]

    return drange


def make_request(start_date='2021-03-06', end_date='2021-03-09', regions=['000'],
                 population_scaling = ["50", "55"],
                 available_dates=available_dates):

    request = dict(lang = 'en',
        table = 'SMIT4',
        format = "CSV",
        valuePresentation = "Value",
        variables = [
            dict(
                code = "AKTP",
                values = population_scaling
            ),
            dict(
                code = "KOMK",
                values = regions
            ),
            dict(
                code = "Tid",
                values = get_dates(start_date, end_date,
                                   available_dates=available_dates)
         )
     ])

    return request


def get_df(start_date, end_date, regions=['000'],
           available_dates=available_dates):

    new_request = make_request(start_date, end_date, regions,
                               available_dates=available_dates)
    r = requests.post('https://api.statbank.dk/v1/data', json=new_request)
    df = pd.read_csv(io.StringIO(r.text), sep=';')
    df['TID'] = pd.to_datetime(df['TID'], format='%YM%mD%d')
    return df


def plotly_graph(x, y, name):
    graph = go.Scatter(x=x, y=y, name=name,
                       mode='lines+markers')
    return graph


app.layout = html.Div([
    html.H1('Yet another Covid Dashboard (Denmark)'),
    html.Div([
        dcc.Markdown(
            '''
            IMPORTANT: The underlying databases are not updated anymore.

            A little Dashboard to compare and investigate COVID cases around Denmark and its
            communes.

            Data is retrieved from [statbank.dk](https://statbank.dk) via the POST api, however, data is
            only updated on Thursdays, so some recent data will be missing.

            To update the underlying data (i.e. different regions and date ranges) please click the
            `Update` button.

            Use the radio buttons below to change the appearance of the plot.

            Finally, the plot also allows for all normal plotly operations like zooming into data
            and selecting different data traces.
            '''
        )
    ]),

    html.Div([
    html.H3('Select a Region:',
            style={'paddingRight': '30px'}),
    dcc.Dropdown(id='pick_region',
                options=dropdown_regions,
                value=['000'],
                multi=True,
                style={'height': '50px'})
    ],
             style={'display': 'inline-block', 'verticalAlign': 'top',
                    'width': '45%',
                    'height': '120px',
                    'paddingRight': '30px'}),

    html.Div([
        html.H3('Select a start and end date:'),
              dcc.DatePickerRange(id='date_picker',
                                  min_date_allowed=sub_date(available_dates[0]),
                                  max_date_allowed=sub_date(available_dates[-1]),
                                  start_date='2021-03-01',
                                  end_date=sub_date(available_dates[-1]),
                                  display_format='YYYY-MM-DD',
                                  style={'height': '50px'})
              ],
             style={'display': 'inline-block',
                    'height': '120px',
                    'verticalAlign': 'top',
                    'width': '20%',
                    'paddingRight': '30px'}),

    html.Div([
        html.Button(id='submit_button',
                    n_clicks=0,
                    children='Update',
                    style={'fontSize': 20,
                           'marginTop' : '60px',
                           'height': '45px',
                           'width': '120px'})
        ],
             style={'display': 'inline-block',
                    'verticalAlign': 'bottom',
                    'horizontalAlign': 'middle',
                    'width': '30%',
                    'height': '120px'}),

        html.Div([]),

        html.Div([
            html.H3('Scale Cases'),
            dcc.RadioItems(id='scale_pop', options=data_info,
                value='50', labelStyle={'display': 'block'}),

            html.H3('Display Mode'),
            dcc.RadioItems(id='growth',
                                options=[{'value': 'total', 'label': 'total'},
                                        {'value': 'new', 'label': 'new cases'}],
                value= 'total', labelStyle={'display': 'block'})],
                style={'display': 'inline-block',
                        'verticalAlign': 'top',
                        'width': '10%',
                        'marginTop': '20px',
                        'marginLeft': '5px',
                        'horizontalAlign': 'left'}),

    html.Div([dcc.Graph(id='ts-graph',
                        figure={'data': [{'x': [1,2],
                                          'y': [3,1]}],
                                'layout': go.Layout(
                                    title='Default Title'
                                )})
              ],
             style={'display': 'inline-block',
                    'width':'87%',
                    'verticalAlign': 'top',
                    'horizontalAlign': 'right'}),


    # Hidden div for dataset
    html.Div(id='dataset', style={'display': 'none'} )
    ])


# Callback to store data, triggered by submit button.
@app.callback(Output('dataset', 'children'),
              [Input('submit_button', 'n_clicks')],
              [State('pick_region', 'value'),
               State('date_picker', 'start_date'),
               State('date_picker', 'end_date')])
def query_data(click, region, start, end):

    df = get_df(start, end, region)

    return df.to_json(date_format='iso', orient='split', date_unit='s')


# Callback to change graph appearance
@app.callback(Output('ts-graph', 'figure'),
              [Input('scale_pop', 'value'),
               Input('growth', 'value'),
               Input('dataset', 'children')],
              [State('pick_region', 'value')])
def update_graph(option1, option2, data, region):
    opt1 = data_info_dict[option1]

    df = pd.read_json(data,  orient='split')

    tmp_df = df.query('AKTP == @opt1')

    traces = []
    for reg in df['KOMK'].unique():

        tmp_df2 = tmp_df.query('KOMK == @reg')

        if option2 == 'total':
            traces.append(plotly_graph(tmp_df2['TID'],
                                       tmp_df2['INDHOLD'],
                                       reg))

        if option2 == 'new':
            traces.append(plotly_graph(tmp_df2['TID'].iloc[1:],
                                       tmp_df2['INDHOLD'].diff().iloc[1:],
                                       reg))

    title = ' - '.join([str(ii) for ii in df['KOMK'].unique()])
    fig = {
        'data': traces,
        'layout': {'title': 'Cases for:\n' + title,
                   'xaxis': {'title': 'Date'},
                   'yaxis': {'title': opt1}}
    }

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)

