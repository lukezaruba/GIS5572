#!/bin/bash

# Install Python 3.6
sudo apt-get install python3.6

# Install PIP
curl https://bootstrap.pypa.io/pip/3.6/get-pip.py -o get-pip.py
sudo python get-pip.py
rm get-pip.py

# Install Flask and psycopg2
sudo pip install flask
sudo pip install psycopg2