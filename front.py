from dash import Dash, html, dash_table, dcc, callback, Output, Input, State
from dash_extensions import WebSocket
from dash.exceptions import PreventUpdate
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc


import json
import requests
import traceback


class SparkLine:

	def __init__(self, uid, label):

		self.uid = uid
		self.label = label
		self.x = []
		self.y = []
	
		self.figure = go.Figure(
			data=go.Scatter(x=self.x, y=self.y, mode='lines', fill='tozeroy'),
			layout={
				'xaxis': {
					'visible': False,
					'showticklabels': False,
				},
				'yaxis': {
					'visible': False,
					'showticklabels': False,
				},
				'margin': dict(l=0, r=0, t=0, b=0)
			}
		)


	def add_point(self, x, y):
		self.x.append(x)
		self.y.append(y)

		self.figure.update_traces(
			x=self.x,
			y=self.y,
		)


	def html(self):
		return dbc.Container([
			dcc.Graph(
				id=f'{self.uid}-graph',
				figure=self.figure,
				style={
					'position': 'absolute',
					'top': 0,
					'left': 0,
					'width': '300px',
					'height': '50px',
				}
			),
			dbc.Badge(
				f'{self.label.upper()}',
				id=f'{self.uid}-label-badge',
				color="primary", 
				className="me-1",
				style={
					'position': 'absolute',
					'top': '5px',
					'left': '5px',
				}
			),
			dbc.Badge(
				f'---',
				id=f'{self.uid}-value-badge',
				color="dark", 
				className="me-1",
				style={
					'position': 'absolute',
					'top': '5px',
					'right': '5px',
				}
			)
		], 
			style={
				'position': 'relative',
				'width': '300px',
			}
		)


class Graph:


	def __init__(self, uid, keys):

		self.uid = uid
		self.keys = keys
		self.dataframe = pd.DataFrame({k: [] for k in self.keys})
		self.figure = go.Figure(
			data=go.Scatter(x=[0], y=[0], mode='markers'),
		)

		self.x_key = keys[0]
		self.y_key = keys[1]


	def html(self):
		return dbc.Container([
			dbc.Row([
				html.Div(f'Graph {self.uid}', className='lead'),
			]),
			dbc.Row([
				html.Span('X AXIS', className='small'),
				dbc.RadioItems(
					id=f'{self.uid}-x-radio',
					class_name="btn-group",
            		input_class_name="btn-check",
            		label_class_name="btn btn-outline-primary",
            		label_checked_class_name="active",
            		options=[{'label': k,'value': k} for k in self.keys], 
					value=self.keys[0],
				),
				],
				className="radio-group"
			),
			dbc.Row([
				html.Span('Y AXIS', className='small'),
				dbc.RadioItems(
					id=f'{self.uid}-y-radio',
					class_name="btn-group",
            		input_class_name="btn-check",
            		label_class_name="btn btn-outline-primary",
            		label_checked_class_name="active",
            		options=[{'label': k,'value': k} for k in self.keys],
					value=self.keys[1],
				),
				],
				className="radio-group"
			),
			dbc.Row([
				dcc.Graph(
					figure=self.figure,
					id=f'{self.uid}-graph',
				)
			]),
		])

	def add_websocket_callback(self, app, websocket_uid):
		@app.callback(
			Output(component_id=f'{self.uid}-graph', component_property='figure'),
			Input(component_id=f'{websocket_uid}', component_property='message'),
			[
				State(component_id=f'{self.uid}-x-radio', component_property='value'),
				State(component_id=f'{self.uid}-y-radio', component_property='value'),
			],
		)
		def update_my_graph(message, x_selected, y_selected):
			try:
				data = json.loads(message['data'])
				data = {k: [v] for k, v in data.items()}
				_df = pd.DataFrame(data)
				print(_df)
				self.dataframe = pd.concat([self.dataframe, _df])

				self.x_key = x_selected
				self.figure.update_layout(
					xaxis_title=f'{self.x_key.upper()}'
				)
				self.y_key = y_selected
				self.figure.update_layout(
					yaxis_title=f'{self.y_key.upper()}'
				)

				self.figure.update_traces(
					x=self.dataframe[self.x_key],
					y=self.dataframe[self.y_key],
				)
				
				return self.figure

			except Exception as e:
				print(e)
				#traceback.print_exc()
				return self.figure


class Front:


	def __init__(self):

		self.measurement_keys = self.get_measurement_keys()
		self.instrument_keys = self.get_instrument_keys()

		self.dataframe = pd.DataFrame({k: [] for k in self.measurement_keys})

		self.x_key = self.measurement_keys[0]
		self.y_key = self.measurement_keys[1]

		self.sparklines = {k: SparkLine(k, k) for k in self.measurement_keys}

		#self.GRAPH = Graph('myid', self.measurement_keys)

		self.app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

		self.make_layout()
		self.add_callbacks()

		#self.GRAPH.add_websocket_callback(self.app, 'ws')


	def get_measurement_keys(self):
		return requests.get('http://localhost:8000/rack/measurements').json()


	def get_instrument_keys(self):
		return requests.get('http://localhost:8000/rack/instruments').json()



	def make_layout(self):

		self.app.layout = dbc.Container([
			dbc.Row([
				html.Div('Dash frontend test', id='title-div', className='text-primary text-center fs-3'),
				WebSocket(id='ws', url='ws://localhost:8765'),
				dbc.Textarea(id='main-input', size='sm')
			]),
			#self.GRAPH.html(),
			*[html.Div(
				[spark.html()],
				style={'height': '55px'}
			) for key, spark in self.sparklines.items()],

		],
		)


	def add_callbacks(self):
		@self.app.callback(
			Output(component_id='main-input', component_property='value'),
			Output(component_id='main-input', component_property='valid'),
			Output(component_id='main-input', component_property='invalid'),
			Input(component_id=f'ws', component_property='message')
		)
		def handle_socket_message(message):
			if message != None:
				data = json.loads(message['data'])
				data = {k: [v] for k, v in data.items()}
				_df = pd.DataFrame(data)
				self.dataframe = pd.concat([self.dataframe, _df])
				return [message['data'], True, False]
			else:
				return ['PROBLEM', False, True]


		@self.app.callback(
			*[Output(component_id=f'{k}-value-badge', component_property='children') for k, v in self.sparklines.items()],
			Input(component_id='main-input', component_property='value'),
		)
		def update_badges(data):
			try:
				message = json.loads(data)
				return [f'{v:.2f}' for k, v in message.items()]
			except:
				raise PreventUpdate


		@self.app.callback(
			*[Output(component_id=f'{k}-graph', component_property='figure') for k, v in self.sparklines.items()],
			Input(component_id='main-input', component_property='value'),
		)
		def update_sparks(data):
			try:
				message = json.loads(data)

				for key, value in message.items():
					sparkline = self.sparklines[key]
					sparkline.add_point(message['time'], value)


				return [spark.figure for key, spark in self.sparklines.items()]
			except:
				raise PreventUpdate



if __name__ == '__main__':
	Front().app.run(debug=True)