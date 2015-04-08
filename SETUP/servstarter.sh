#!/usr/bin/env bash

p=$HOME/predictor

screen -dmS modeler python3 $p/modeler/modeler.py
screen -dmS mapper python3 $p/mapper/modeler.py