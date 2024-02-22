#!/bin/bash

git pull
python -m venv the-DM
source the-DM/bin/activate
pip install -r requirements.txt