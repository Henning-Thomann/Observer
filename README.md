# The Observer

## Getting started

Requirements: Python 3.11+

This guide shows how to run this project in a virtual environment. Alternatively you can install the dependency globally.

First create a virtual environment with ```python3 -m venv```.
Secondly you need to activate it.
```
source venv/bin/activate # on Linux
venv\bin\Activate.ps1    # on Windows
```
Finally we can install the dependencies and run the project.
```
pip install -r requirements.txt
python3 src/main.py
```
An additional ``wh.dat`` file which contains the discord webhook (as fully qualified link) is required.
