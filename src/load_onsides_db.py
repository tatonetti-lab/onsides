"""
load_onsides_db.py

Script to implement and run the SQL template at load_onsides_db.sql given the
connection details and paramters.

@author Nicholas P. Tatonetti, PhD
"""

import os
import sys
import csv
import gzip
import pymysql
import argparse



if __name__ == '__main__':
    main()
