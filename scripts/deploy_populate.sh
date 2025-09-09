#!/bin/bash
# Pre-deploy script to populate exercises
set -e

# Set Python path and run the populate script
export PYTHONPATH=/formava_ai_trainer
cd /formava_ai_trainer
python app/scripts/populate_exercises.py
