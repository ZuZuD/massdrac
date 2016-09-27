#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger()

# set logger level to debug to print everything 
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')

file_handler = RotatingFileHandler('activity.log', 'a', 1000000, 1)

file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

steam_handler = logging.StreamHandler()
steam_handler.setLevel(logging.WARNING)
logger.addHandler(steam_handler)
    
