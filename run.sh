#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    python -m venv venv
    venv/Scripts/pip install -r requirements.txt
fi

venv/Scripts/streamlit run app.py
