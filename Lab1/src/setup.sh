#!/bin/bash

# Install Python 3.9
sudo apt-get install python3.9

# Install PIP
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python3.9 get-pip.py
rm get-pip.py

# Install Flask and psycopg2
sudo pip install flask
sudo pip install psycopg2
