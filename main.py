import os
import dash
# import dash_core_components as dcc
# import dash_html_components as html

from dash import dcc
from dash import html
from dash.dependencies import Input, Output
from symptom_detection.SymptomDetection import detect_symptoms, detections_to_li_html

EXAMPLE_DIR = r'text_examples'
example_files = [os.path.join(EXAMPLE_DIR, f) for f in os.listdir(EXAMPLE_DIR) if f[-4:] == '.txt']

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1('Автоматическое извлечение симптомов',
            style={'text-align': 'center', 'padding': '5px', }),

    html.Div(
        html.Div(
            [
                html.Div(
                    children=[
                        dcc.Dropdown(
                            id="example_list",
                            options=[
                                {'label': os.path.basename(f).split('.')[0],
                                 'value': f} for f in example_files
                            ],
                            value=None
                        )
                    ],
                    style={
                        'width': '50%',
                        'textAlign': 'justify'
                    })
            ],
            style={
                "display": "flex",
                'justify-content': 'center',
            }
        ),
        style={
            'width': '100%',
            'height': 40,
            'padding': '5px'
        }
    ),

    html.Div(
        [
            dcc.Textarea(
                id="input_text",
                placeholder="Введите анамнез кардиологического пациента ...",
                # debounce=True,
                style={
                    'height': '100%',
                    'text-align': 'left',
                    'width': '50%',
                    'vertical-align': 'top'
                }
            )
        ],
        style={
            'width': '100%',
            'height': 200,
            'textAlign': 'center',
            'padding': '5px',
        }
    ),

    html.Div(
        html.Button('Обработать', id='process_button', n_clicks=0),
        style={
            'width': '100%',
            # 'height': 40,
            'textAlign': 'center',
            'padding': '15px'
        },
    ),

    html.Div(
        [
            dcc.RadioItems(
                id='my_radio',
                options=[
                    {'label': 'Отметить обнаруженные симптомы в тексте', 'value': 'res_in_text'},
                    {'label': 'Показать положительные симптомы', 'value': 'pos_sym'},
                    {'label': 'Показать отрицательные симптомы', 'value': 'neg_sym'}
                ],
                labelStyle={"display": "block"},
                value='res_in_text'
            )
        ],
        style={
            'width': '100%',
            # 'height': 40,
            'textAlign': 'center',
            'padding': '5px'
        }
    ),
    html.Div(
        html.Div(
            [
                html.Div(id="processed_data",
                         style={
                             'width': '50%',
                             'textAlign': 'justify'
                         })
            ],
            style={
                "display": "flex",
                'justify-content': 'center',
            }
        ),
        style={
            'width': '100%',
            'height': 400,
            'padding': '5px'
        }
    ),
    # dcc.Store inside the app that stores the intermediate value
    dcc.Store(id='intermediate-value', data=([], '')),
    dcc.Store(id='text-value', data=''),
    dcc.Store(id='click-value', data=0),
]
)


@app.callback(
    Output("input_text", "value"),
    [Input("example_list", 'value')]
)
def insert_example(file_name):
    if file_name is None:
        return ''
    with open(file_name) as f:
        return f.read()


@app.callback(
    [
        Output('intermediate-value', 'data'),
        Output('text-value', 'data'),
        Output('click-value', 'data'),
    ],
    [
        Input('process_button', 'n_clicks'),
        Input("input_text", "value"),
        Input('text-value', 'data'),
        Input('intermediate-value', 'data'),
        Input('click-value', 'data'),
    ]
)
def update_output(*vals):
    n_clicks = vals[0]
    text = vals[1].strip()
    prev_text = vals[2]
    prev_res = vals[3]
    prev_clicks = vals[4]
    # print('len(text)', len(prev_text), len(text))
    # print('n_clicks', prev_clicks, n_clicks)
    if n_clicks > prev_clicks and text != prev_text:
            if len(text.strip()) != 0:
                processed_data = detect_symptoms(text, 'span')
                return processed_data, text, n_clicks
    return prev_res, prev_text, n_clicks


@app.callback(
    Output("processed_data", "children"),
    [
        Input('intermediate-value', 'data'),
        Input("my_radio", "value"),
    ]
)
def process_text(*vals):
    to_do = vals[1]
    detections, text_res = vals[0]
    if len(text_res) != 0:
        if to_do == 'res_in_text':
            return text_res

        if to_do == 'pos_sym':
            return detections_to_li_html(detections)

        if to_do == 'neg_sym':
            return detections_to_li_html(detections, neg_status=True)


if __name__ == "__main__":
    app.run_server(debug=True)
    # app.run_server(host='0.0.0.0', debug=True, use_reloader=False)
    # TODO: 120_173
