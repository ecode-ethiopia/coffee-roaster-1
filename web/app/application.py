import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.exceptions import PreventUpdate

from flask import Flask, send_file
from datetime import datetime
from io import BytesIO

import view
import control


app = dash.Dash(__name__)
app.config['suppress_callback_exceptions'] = True
app.title = 'Coffee Roast Controller'


app.layout = html.Div(children=[
    html.Div(
        children=[
            html.H5(
                'Coffee Roaster',
                className='my-0 mr-md-auto text-light font-weight-bold',
            ),
            html.Nav(
                children=[
                    # Button/status go here
                ], className='my-2 my-md-0 mr-md-3',
            )
        ], className='d-flex flex-column flex-md-row align-items-center p-3 px-md-4 mb-3 bg-dark border-bottom shadow-sm gradient-nav',
    ),

    # URL bar (not visible)
    dcc.Location(id='url', refresh=False),

    # Page content
    html.Div(id='page-content', className='px-md4')

])


@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    return view.layout


# Callback to update axes
@app.callback([dash.dependencies.Output('main-chart', 'figure'),
               dash.dependencies.Output('chart-data-interval-component', 'interval')],
              [dash.dependencies.Input('interval-component', 'n_intervals')])
def update_chart_figure(n):
    # Lock updates for 5s while refreshing chart
    control.set_value('lock', True, 5)
    return view.initialise_chart(), 2 * view.UPDATE_INTERVAL * 1000


# Callback to set heater level
@app.callback(dash.dependencies.Output('heat-badge', 'children'),
              [dash.dependencies.Input('heat-slider', 'value')])
def set_heat(value):
    return view.set_heat(value)


# Callback to set start PID control
@app.callback(dash.dependencies.Output('ror-badge', 'children'),
              [dash.dependencies.Input('ror-slider', 'value')])
def start_pid(value):
    return view.start_pid(value)


# Callback to update ror-badge colour and update PID settings
@app.callback(dash.dependencies.Output('ror-badge', 'className'),
              [dash.dependencies.Input('ror-slider', 'value'),
               dash.dependencies.Input('data-interval-component', 'n_intervals')])
def update_ror_badge(value, n):
    view.update_pid(value)
    return view.badge_auto(False)


# Callback to data (table, stopwatch)
@app.callback([dash.dependencies.Output('latest-table', 'children'),
               dash.dependencies.Output('heat-badge', 'className'),
               dash.dependencies.Output('stopwatch-button', 'children')],
              [dash.dependencies.Input('data-interval-component', 'n_intervals')])
def update_data(n):
    return view.table(), view.badge_auto(True), view.stopwatch()


# Callback to data (table, stopwatch)
@app.callback(dash.dependencies.Output('main-chart', 'extendData'),
              [dash.dependencies.Input('chart-data-interval-component', 'n_intervals')],
              [dash.dependencies.State('main-chart', 'figure')])
def update_chart_data(n, fig):
    if not fig:
        PreventUpdate()
    if control.get_value('lock'):
        # Abort update if chart refresh has locked it
        PreventUpdate()
    return view.update_chart(fig)


# Stopwatch click (reset)
@app.callback(dash.dependencies.Output('hidden-div', 'children'),
              [dash.dependencies.Input('stopwatch-button', 'n_clicks')])
def reset_stopwatch(n):
    if n:
        view.reset_stopwatch()
    return ''


# Data download handler
@app.server.route('/download')
def download():
    df = view.data_summary(['log.temperature', 'log.heat', 'log.auto_mode'])
    csv = BytesIO()
    csv.write(df.to_csv().encode('utf-8'))
    csv.seek(0)
    return send_file(
        csv,
        mimetype='text/csv',
        as_attachment=True,
        attachment_filename='profile_{0:%Y%m%d}.csv'.format(datetime.now())
    )


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', threaded=True, debug=False, port=80)
