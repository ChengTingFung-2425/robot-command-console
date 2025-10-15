# Removed Python Packages

This document lists the Python packages that were removed from `requirements.txt` as they were not being used by the application.

## Summary
- **Before**: 151 packages
- **After**: 63 packages
- **Removed**: 88 packages (58% reduction)

## Categories of Removed Packages

### Jupyter Ecosystem (20 packages)
These packages are for Jupyter notebooks and JupyterLab, which are not used in this Flask web application:
- ipykernel==6.19.2
- ipython==8.10.0
- ipython-genutils==0.2.0
- jupyter-events==0.5.0
- jupyter-server-mathjax==0.2.6
- jupyter_client==7.4.8
- jupyter_core==5.1.0
- jupyter_server==2.0.1
- jupyter_server_terminals==0.4.2
- jupyterlab==4.4.8
- jupyterlab-git==0.51.1
- jupyterlab-pygments==0.2.2
- jupyterlab_server==2.16.5
- nbclassic==0.4.8
- nbclient==0.7.2
- nbconvert==7.2.6
- nbdime==3.1.1
- nbformat==5.7.0
- notebook==6.5.2
- notebook_shim==0.2.2

### Data Science Libraries (13 packages)
These are machine learning and data visualization libraries not used in the application:
- matplotlib==3.6.2
- matplotlib-inline==0.1.6
- numpy==1.23.5
- nvidia-cublas-cu11==11.10.3.66
- nvidia-cuda-nvrtc-cu11==11.7.99
- nvidia-cuda-runtime-cu11==11.7.99
- nvidia-cudnn-cu11==8.5.0.96
- pandas==1.5.2
- plotly==5.11.0
- scikit-learn==1.5.0
- scipy==1.9.3
- seaborn==0.12.1
- torch==2.8.0

### Dependencies of Jupyter/Data Science (55 packages)
These are support libraries only needed by the above packages:
- Pygments==2.13.0
- Send2Trash==1.8.0
- anyio==3.6.2
- argon2-cffi==21.3.0
- argon2-cffi-bindings==21.2.0
- asttokens==2.2.1
- backcall==0.2.0
- beautifulsoup4==4.11.1
- bleach==5.0.1
- comm==0.1.2
- contourpy==1.0.6
- cycler==0.11.0
- debugpy==1.6.4
- defusedxml==0.7.1
- entrypoints==0.4
- executing==1.2.0
- fastjsonschema==2.16.2
- fonttools==4.43.0
- fqdn==1.5.1
- isoduration==20.11.0
- jedi==0.18.2
- joblib==1.2.0
- json5==0.9.10
- jsonpointer==2.3
- jsonschema==4.17.3
- kiwisolver==1.4.4
- mistune==2.0.4
- nest-asyncio==1.5.6
- pandocfilters==1.5.0
- parso==0.8.3
- pexpect==4.8.0
- pickleshare==0.7.5
- prometheus-client==0.15.0
- prompt-toolkit==3.0.36
- psutil==5.9.4
- ptyprocess==0.7.0
- pure-eval==0.2.2
- pyrsistent==0.19.2
- python-json-logger==2.0.4
- pyzmq==24.0.1
- rfc3339-validator==0.1.4
- rfc3986-validator==0.1.1
- sniffio==1.3.0
- stack-data==0.6.2
- tenacity==8.1.0
- terminado==0.17.1
- threadpoolctl==3.1.0
- tinycss2==1.2.1
- tornado==6.5
- traitlets==5.7.1
- uri-template==1.2.0
- wcwidth==0.2.5
- webcolors==1.12
- webencodings==0.5.1
- websocket-client==1.4.2

## What Remains

The following package categories remain as they are actively used by the Flask web application:

### Core Flask & Extensions
- Flask==2.2.5
- Flask-Babel==2.0.0
- Flask-Bootstrap==3.3.7.1
- Flask-Login==0.6.2
- Flask-Mail==0.9.1
- Flask-Migrate==4.0.0
- Flask-Moment==1.0.5
- Flask-SQLAlchemy==3.0.2
- Flask-WTF==1.0.1

### Database
- SQLAlchemy==1.4.45
- alembic==1.8.1
- psycopg2==2.9.5

### Internationalization
- Babel==2.11.0

### Security & Authentication
- Werkzeug==3.0.6
- PyJWT==2.6.0
- email-validator==1.3.0

### Template & Form Handling
- Jinja2==3.1.6
- WTForms==3.0.1
- dominate==2.7.0
- visitor==0.1.3

### Development Tools
- djlint==1.19.7 (HTML/Jinja template linter)
- GitPython==3.1.41

### Other Utilities
Various supporting libraries for the above packages

## Verification

No Python code in the repository imports or uses any of the removed packages. The application is a Flask web application that does not require Jupyter notebooks or data science libraries.
