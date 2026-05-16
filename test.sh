#!/bin/bash
cd "$(dirname "$0")"
venv/Scripts/pytest tests/ -v
