from scipy.optimize import curve_fit
import pandas as pd


def LINEAR(x, a, b):
	return a + b*x


def QUADRATIC(x, a, b, c):
	return a + b*x + c*x*x


def _fit(
	func: callable, 
	dataframe: pd.DataFrame, 
	x_column: str, 
	y_column: str,
	where: bool = None,
	**kwargs,
	):
	"""
	Fit datafr

	Wraps scipy.optimize.curve_fit with some sanitization
	to prevent common errors.

	:param      func:      The function
	:type       func:      callable
	:param      dataframe:        { parameter_description }
	:type       dataframe:        { type_description }
	:param      x_column:  The x column
	:type       x_column:  str
	:param      y_column:  The y column
	:type       y_column:  str
	:param      where:     The where
	:type       where:     bool
	:param      kwargs:    The keywords arguments
	:type       kwargs:    dictionary

	:returns:   { description_of_the_return_value }
	:rtype:     { return_type_description }
	"""
	fit_dataframe = dataframe.copy()
	if where is not None:
		fit_dataframe = fit_dataframe.where(where)
	fit_dataframe = fit_dataframe.dropna(subset=[x_column, y_column])
	popt, pcov = curve_fit(func, fit_dataframe[x_column], fit_dataframe[y_column], **kwargs)
	return popt, pcov



def fit(
	func: callable, 
	dataframe: pd.DataFrame, 
	x_column: str, 
	y_column: str,
	z_column: str = None,
	where: bool = None,
	**kwargs,
	):
	"""
	Fit func to data in dataframe and return the optimized coefficients
	and covarience matrix. If z_column is provided, data is grouped by 
	this column and fits are performed on each group. The returned object
	is then a dictionary with keys given by the group value and values
	are a tuple holding the optimized coeffiicents and covariance matrix.

	:param      func:      The function
	:type       func:      callable
	:param      dataframe:        { parameter_description }
	:type       dataframe:        { type_description }
	:param      x_column:  The x column
	:type       x_column:  str
	:param      y_column:  The y column
	:type       y_column:  str
	:param      z_column:  The z column
	:type       z_column:  str
	:param      where:     The where
	:type       where:     bool
	:param      kwargs:    The keywords arguments
	:type       kwargs:    dictionary

	:returns:   { description_of_the_return_value }
	:rtype:     { return_type_description }
	"""
	if z_column is None:
		popt, pcov = _fit(
			func=func,
			dataframe=dataframe,
			x_column=x_column,
			y_column=y_column,
			where=where,
			**kwargs
		)
		return popt, pcov
	else:
		fit_dataframe = dataframe.copy()
		if where is not None:
			fit_dataframe = fit_dataframe.where(where)
		result = {}
		for name, group in fit_dataframe.groupby(z_column):
			popt, pcov = _fit(
				func=func,
				dataframe=group,
				x_column=x_column,
				y_column=y_column,
				where=where,
				**kwargs
			)
			result[name] = (popt, pcov)
		return result


def fit_and_evaluate_at(
	func: callable,
	dataframe: pd.DataFrame,
	x_column: str,
	y_column: str,
	at: float,
	z_column: str = None,
	new_column: str = 'eval',
	where = None,
	merge: bool = False,
	**kwargs
	):
	"""
	Fit func to data in the dataframe and evaluate the function
	at a particular value.

	:param      func:        The function
	:type       func:        callable
	:param      dataframe:          { parameter_description }
	:type       dataframe:          { type_description }
	:param      x_column:    The x column
	:type       x_column:    str
	:param      y_column:    The y column
	:type       y_column:    str
	:param      at:          { parameter_description }
	:type       at:          float
	:param      z_column:    The z column
	:type       z_column:    str
	:param      new_column:  The new column
	:type       new_column:  str
	:param      where:       The where
	:type       where:       { type_description }
	:param      merge:       Merge onto original dataframe (only if z_column is provided)
	:type       merge:       bool
	:param      kwargs:      The keywords arguments
	:type       kwargs:      dictionary

	:returns:   { description_of_the_return_value }
	:rtype:     { return_type_description }
	"""
	
	result = fit(
		func=func, 
		dataframe=dataframe, 
		x_column=x_column, 
		y_column=y_column,
		z_column=z_column,
		where=where, 
		**kwargs
	)


	if z_column is None:
		return func(at, *result[0])

	else:
		if merge:
			new_dataframe = pd.DataFrame({
				z_column: [k for k, v in result.items()],
				new_column: [func(at, *popt) for k, (popt, pcov) in result.items()]
			})
			return dataframe.merge(new_dataframe, on=z_column, how='left')

		else:
			new_dataframe = pd.DataFrame({
				z_column: [k for k, v in result.items()],
				x_column: [at for k, v in result.items()],
				new_column: [func(at, *popt) for k, (popt, pcov) in result.items()]
			})

			return new_dataframe
				


