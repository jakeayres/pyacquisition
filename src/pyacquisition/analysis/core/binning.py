import pandas as pd
import numpy as np


def _make_bins(
	minimum: float,
	maximum: float,
	width: float,
	centers: bool,
	):

	if centers:
		left = minimum - width/2
		right = maximum + width/2
	else:
		left = minimum
		right = maximum
	return np.arange(left, right+width, width)


def bin_data(
	data: pd.DataFrame,
	column: str,
	minimum: float,
	maximum: float,
	width: float,
	centers: bool = True,
	new_column: str = None,
	):
	"""
	Bin data into bins of equal width between minimum and maximum. If centers is
	true, inputs minimum and maximum define midpoints of end bins, else they
	define end limits. If new column is provided, bins are saved to
	'new_column', otherwise the data in 'column' is overwritten.
	
	:param      data:        The data
	:type       data:        pandas DataFrame
	:param      column:      The column to bin
	:type       column:      str
	:param      minimum:     Minimum valuue
	:type       minimum:     float
	:param      maximum:     Maximum value
	:type       maximum:     float
	:param      width:       Bin width
	:type       width:       float
	:param      centers:     Maximum and minimum define bin centers
	:type       centers:     bool
	:param      new_column:  Name of new column (if not none)
	:type       new_column:  str
	
	:returns:   Binned dataframe
	:rtype:     pd.DataFrame
	"""

	bins = _make_bins(minimum, maximum, width, centers)
	new_column = column if new_column is None else new_column

	data[new_column] = pd.cut(data[column], bins=bins, precision=5, include_lowest=False)
	data = data.groupby(new_column).mean().reset_index()
	data[new_column] = data[new_column].apply(lambda x: (x.left + x.right) / 2)
	data[new_column] = data[new_column].astype(float)

	return data