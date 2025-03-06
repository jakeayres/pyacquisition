import streamlit as st


st.title('Installation')


st.write('`PyAcquisition` is installable via `pip`.')

st.code('pip install pyacquisition')

st.write('Once installed, you are ready to go!')


st.header('Dependency Management')

st.write('''`PyAcquisition` relies upon a number of well-maintained and widely used
	packages. These include (non exhaustive) `pyvisa`, `asyncio`, `numpy`, `pandas` that are very likely to be installed in
	your local environment. Conflicting version requirements of these dependencies are somewhat inevitable (here and in general).''')

st.write('''It is **strongly** suggested that dependecy management is considered early. Neglecting proper dependency 
	management can lead to version conflicts, broken software, and unpredictable behavior across environments. 
	Without controlled dependencies, updates to libraries may introduce incompatibilities, making debugging 
	difficult and deployments unreliable. All of this is best avoided.''')

st.markdown('At the very least, we suggest that you should:')    
st.markdown('- **Use a Virtual Environment**: Always create a separate virtual environment for each project to isolate dependencies and avoid conflicts with system-wide packages. Install `PyAcquisition` in this virtual environment.')
st.markdown('- **Pin Dependency Versions**: Specify exact versions of dependencies in a requirements.txt or pyproject.toml to ensure that the same versions are installed across all environments.')


st.subheader('`uv` - An extremely fast Python package and project manager')

st.write('''I have no association with `uv` or its developer Astral. I am, however, going to give you a short sales pitch as I have
	found `uv` to be a remarkably simply package management solution that replaces `pip`, `pip-tools`, `poetry`, `pyenv` and `virtualenv`.''')

st.markdown('Visit the [uv github repository](https://github.com/astral-sh/uv) for more information on `uv`.')