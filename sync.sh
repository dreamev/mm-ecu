#!/usr/bin/env bash
#

fswatch -o code.py | while read num; do
    cp code.py /Volumes/CIRCUITPY
done
