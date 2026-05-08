#!/bin/bash
cd "$(dirname "$0")"
venv/Scripts/pytest test_area_analysis.py -v
