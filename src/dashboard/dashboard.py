"""
Predict players for fanta.
Author: Matteo Courthoud
Date: 22/10/2022
"""

import datetime
import numpy as np
import pandas as pd
from dash import Dash, Input, Output, dcc, html, dash_table
import plotly.express as px
import plotly.graph_objects as go


NUM_PLAYERS = 8
NUM_VISIBLE_PLAYERS = 3
SEASON = 2023
PLAYERS_FILE = '../data/players.csv'
GAMES_FILE = '../data/%i/games.csv'
INJURIES_FILE = '../data/injuries.csv'
CURRENT_STATS_FILE = '../data/current_stats.csv'
PREDICTED_GAIN_FILE = '../data/predicted_gain.csv'


def add_date_position(df: pd.DataFrame) -> pd.DataFrame:
    # Add dates
    df_dates = pd.read_csv(GAMES_FILE % SEASON)[['date', 'game_id']].drop_duplicates()
    df_dates['date'] = pd.to_datetime(df_dates['date'])
    df = pd.merge(df, df_dates, on='game_id', how='right')

    # Add positions
    df = pd.merge(df, pd.read_csv(PLAYERS_FILE), on='name', how='left')
    return df


def import_data() -> pd.DataFrame:
    df = pd.read_csv(CURRENT_STATS_FILE)
    df = add_date_position(df)
    df['date'] = pd.to_datetime(df['date'])
    df['time_delta'] = (datetime.datetime.today() - df.date).dt.days
    df['last_price'] = df.groupby('name')['fanta_value'].transform('last')
    df_gain = pd.read_csv(PREDICTED_GAIN_FILE)[['name', 'predicted_gain', 'status']]
    df = pd.merge(df, df_gain, on='name', how='left')
    df['status'] = df['status'].fillna('')
    return df


# Init
df = import_data()
df_plot = df.copy()
df_plot['name'] = df_plot['name'] + ' - ' + df_plot['last_price'].apply(lambda x: '{0:.1f}'.format(x))
roles = ["All", "C", "F", "G"]
metrics = {'Predicted Gain': 'predicted_gain', 
           'Median Gain': 'median_gain',
           'Average Score': 'mean_score',
           'fanta Value': 'fanta_value'}

df_last = df.copy()
df_last['last_date'] = df_last.groupby('name')['date'].transform('max')
df_last = df_last[df_last.date == df_last.last_date]
df_last = df_last[df_last.date >= (pd.Timestamp.now().normalize() - pd.Timedelta(3, 'd'))]
df_last = df_last[['name', 'position', 'fanta_value', 'fanta_score', 'fanta_gain',
                   'mp', 'pts', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf']]
df_last.columns = ['Name', 'Role', 'Value', 'Score', 'Gain',
                   'min', 'pts', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf']
df_last = df_last.sort_values('Gain', ascending=False).reset_index(drop=True).round(1)


external_stylesheets = [
    {
        "href": (
            "https://fonts.googleapis.com/css2?"
            "family=Lato:wght@400;700&display=swap"
        ),
        "rel": "stylesheet",
    },
]
app = Dash(__name__, external_stylesheets=external_stylesheets)

header_div = html.Div(
            children=[
                html.H1(
                    children="🏀 Fantabasket", className="header-title"
                ),
            ],
            className="header",
        )

role_menu_div = html.Div(
                    children=[
                        html.Div(children="Role", className="menu-title"),
                        dcc.Dropdown(
                            id="role-filter",
                            options=[{"label": role, "value": role} for role in roles],
                            value="All",
                            clearable=False,
                            className="dropdown",
                        ),
                    ]
                )

type_menu_div = html.Div(
                    children=[
                        html.Div(children="Variable", className="menu-title"),
                        dcc.Dropdown(
                            id="metric-filter",
                            options=[{"label": label, "value": value} for label, value in metrics.items()],
                            value="predicted_gain",
                            clearable=False,
                            searchable=False,
                            className="dropdown",
                        ),
                    ],
                )

date_menu_div = html.Div(
                    children=[
                        html.Div(
                            children="Value Range", className="menu-title"
                        ),
                        dcc.RangeSlider(min=0, max=30, value=[0, 30],
                                        id='value-range',
                                        className="slider"),
                    ]
                )

menu_div = html.Div(
            children=[
                role_menu_div,
                type_menu_div,
                date_menu_div,
            ],
            className="menu",
        )

price_chart_div = html.Div(
            children=[
                html.Div(
                    children=dcc.Graph(
                        id="price-chart",
                        config={"displayModeBar": False},
                    ),
                    className="card",
                ),
            ],
            className="wrapper",
        )

data_div = html.Div(
            children=[
                html.Div(
                    children=dash_table.DataTable(
                        data=df_last.to_dict("records"),
                        columns=[{"name": i, "id": i} for i in df_last.columns], 
                        cell_selectable=False,
                        sort_action="native",
                        page_current=0,
                        page_size=10,
                        page_action="native",
                        id="data-table",
                        style_as_list_view=True,
                        style_header=dict(backgroundColor="#FF8C00",
                                          color="white",
                                          fontWeight="bold",
                                          border="1px solid #FF8C00",
                                          padding="8px"),
                        style_cell=dict(textAlign="left",
                                        padding="5px"),
                        style_table=dict(borderStyle="hidden",
                                         borderRadius='5px',
                                         overflow="hidden",
                                         color="black"),
                        style_data_conditional=[
                                {
                                    'if': {
                                        'filter_query': '{Gain} > 0',
                                        'column_id': 'Gain'
                                    },
                                    'color': 'green',
                                    'fontWeight': 'bold'
                                },
                                {
                                    'if': {
                                        'filter_query': '{Gain} < 0',
                                        'column_id': 'Gain'
                                    },
                                    'color': 'tomato',
                                    'fontWeight': 'bold'
                                },
                                {
                                    "if": {"column_id": "Name"},
                                    "fontWeight": "bold",
                                },
                                {
                                    "if": {"column_id": "Score"},
                                    "fontWeight": "bold",
                                },
                            ]
                        ),
                    className="card",
                    ),
                ],
            className="wrapper",
            )

app.layout = html.Div(
    children=[
        header_div,
        menu_div,
        price_chart_div,
        data_div,
    ]
)



my_template = dict(
    layout=go.Layout(title_font=dict(family="Rockwell", size=24),
                     xaxis=dict(showgrid=False, titlefont=dict(size=14)),
                     yaxis=dict(zerolinewidth=2, titlefont=dict(size=14)),
                     font=dict(size=12),
                     colorway=px.colors.qualitative.Set1)
)


@app.callback(
    Output("price-chart", "figure"),
    Input("role-filter", "value"),
    Input("metric-filter", "value"),
    Input("value-range", "value"),
)
def make_figure(role, metric, value_range):
    temp = df_plot.copy()
    temp = temp[temp.fanta_value >= value_range[0]]
    temp = temp[temp.fanta_value <= value_range[1]]
    if role != 'All':
        temp = temp[temp.position == role]
    temp = temp.fillna(0)
    temp_players = temp[temp.time_delta < 14
                        ].groupby(
        'name', as_index=False).agg(
        predicted_gain=('predicted_gain', 'last'),
        median_gain=('fanta_gain', 'median'),
        mean_score=('fanta_score', 'mean'),
        fanta_value=('fanta_value', 'last'))
    best_players = temp_players.sort_values(metric, ascending=False)['name'].values[:NUM_PLAYERS]
    temp = temp.loc[temp.name.isin(best_players), :]
    temp = temp.sort_values(['predicted_gain', 'date'])
    fig = go.Figure()
    palette = px.colors.qualitative.Plotly
    for i, name in enumerate(temp.name.unique()):
        temp_name = temp[temp.name == name]
        fig.add_trace(go.Scatter(x=temp_name.date,
                                 y=temp_name.fanta_score,
                                 mode='lines+markers',
                                 legendgroup=name,
                                 name=name,
                                 visible=True if (i < NUM_VISIBLE_PLAYERS) else 'legendonly',
                                 marker=dict(color=palette[i % len(palette)], size=8),
                                 line=dict(width=3),
                                 customdata=np.stack((temp_name.fanta_gain, temp_name.mp, temp_name.start), axis=-1),
                                 hovertemplate='<b>Score</b>: %{y:.1f}' +
                                                '<br><b>Gain </b>: %{customdata[0]:,.1f}' +
                                                '<br><b>Mins </b>: %{customdata[1]:,.0f}' +
                                                '<br><b>Start</b>: %{customdata[2]:,.0f}')
                      )
        fig.add_scatter(x=temp_name.loc[temp_name.start == 0, "date"],
                        y=temp_name.loc[temp_name.start == 0, "fanta_score"],
                        mode='markers',
                        marker=dict(size=4, color="white"),
                        visible=True if (i < NUM_VISIBLE_PLAYERS) else 'legendonly',
                        legendgroup=name,
                        showlegend=False,
                        hoverinfo='skip',
                        )

    fig.update_layout(
        template=my_template,
        xaxis_title="<b>Date</b>",
        yaxis_title="<b>Score</b>",
        legend_title="<b>Player</b>",
        yaxis_range=[-10, 70],
        xaxis_range=[min(temp.date)-pd.Timedelta(2, 'd'), max(temp.date)+pd.Timedelta(2, 'd')],
    )
    return fig


if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port="8080")
