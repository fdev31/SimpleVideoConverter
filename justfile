#!/bin/env just

run:
    ./venv/bin/video-converter

venv:
    rm -fr venv
    python -m venv venv

test:
    ./venv/bin/python -m unittest tests/*.py
