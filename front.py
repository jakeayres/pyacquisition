from dash import Dash, html, dash_table, dcc, callback, Output, Input, State
from dash_extensions import WebSocket
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

import json
import requests
import traceback


class Front:


	def __init__(self):

		self.measurement_keys = self.get_measurement_keys()
		self.instrument_keys = self.get_instrument_keys()

		self.dataframe = pd.DataFrame({k: [] for k in self.measurement_keys})

		self.graph = go.Figure(
			data=go.Scatter(x=[0], y=[0], mode='markers'),
		)
		self.x_key = self.measurement_keys[0]
		self.y_key = self.measurement_keys[1]

		self.app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

		self.make_layout()
		self.add_callbacks()


	def get_measurement_keys(self):
		return requests.get('http://localhost:8000/rack/measurements').json()


	def get_instrument_keys(self):
		return requests.get('http://localhost:8000/rack/instruments').json()


	def make_layout(self):

		self.app.layout = dbc.Container([
			dbc.Row([
				html.Div('Dash frontend test', className='text-primary text-center fs-3')
			]),
			dbc.Row([
				dcc.RadioItems(
					[k for k in self.measurement_keys], self.measurement_keys[0],
					id='x-radio',
				),
				dcc.RadioItems(
					[k for k in self.measurement_keys], self.measurement_keys[0],
					id='y-radio',
				)
			]),
			dbc.Row([
				dbc.Row([
					WebSocket(id='ws', url='ws://localhost:8765')
				]),
				dbc.Row([
					dcc.Graph(
						figure=go.Figure(),
						id='graph',
					)
				]),
			])
		], fluid=True)

	def add_callbacks(self):

		@self.app.callback(
			Output(component_id='graph', component_property='figure'),
			Input(component_id='ws', component_property='message'),
			[
				State(component_id='x-radio', component_property='value'),
				State(component_id='y-radio', component_property='value'),
			],
		)
		def update_my_graph(message, x_selected, y_selected):
			try:
				data = json.loads(message['data'])
				data = {k: [v] for k, v in data.items()}
				_df = pd.DataFrame(data)
				self.dataframe = pd.concat([self.dataframe, _df])

				self.x_key = x_selected
				self.graph.update_layout(
					xaxis_title=f'{self.x_key.upper()}'
				)
				self.y_key = y_selected
				self.graph.update_layout(
					yaxis_title=f'{self.y_key.upper()}'
				)

				self.graph.update_traces(
					x=self.dataframe[self.x_key],
					y=self.dataframe[self.y_key],
				)
				
				return self.graph

			except Exception as e:
				print(e)
				#traceback.print_exc()
				return self.graph


if __name__ == '__main__':
	Front().app.run(debug=True)