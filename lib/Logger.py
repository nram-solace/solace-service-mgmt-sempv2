# Logger
# Logger implementation
# Valid levels:
#   log.trace
#   log.enter
#   log.debug
#   log.info
#   log.warn
#   log.error
#   log.crit
#
# Ramesh Natarajan, Solace PSG
# May 20, 2021

import sys, os
import string, re

import requests
import json
#from importlib_resources import read_text
import logging, inspect
import urllib

import pprint
pp = pprint.PrettyPrinter(indent=4)

class Logger:
    'Loggig implementation'

    #--------------------------------------------------------------
    # Constructor
    #--------------------------------------------------------------
    def __init__(self, label, verbose=0):
        #self.logger = logging.getLogger(me)
        #self.logger.enter ("%s::%s : %s %s %s", __name__, inspect.stack()[0][3], host, user, url)
        self.label = label
        self.logfile = 'log/{}.log'.format(label)
        self.verbose = verbose
        

    # Setuplogger
    # logger levels:
    # Standard: 50:CRIT  40:ERROR  30:WARN  20:INFO 10:DEBUG 0:NOTSET
    # Custom:   32:NOTE  22:STATUS 9:ENTER  8:TRACE
    def SetupLogger(self):
        # add additional levels
        logging.TRACE = 8 
        logging.addLevelName(logging.TRACE, 'TRACE') 
        logging.ENTER = 9  
        logging.addLevelName(logging.ENTER, 'ENTER') 

        self.log = logging.getLogger(self.label)
        self.log.trace = lambda msg, *args: self.log._log(logging.TRACE, msg, args)
        self.log.enter = lambda msg, *args: self.log._log(logging.ENTER, msg, args)
        self.log.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s : %(name)s [%(levelname)s] %(message)s')
        stream_formatter = logging.Formatter('[%(levelname)s] %(message)s')

        # file handler
        print("Working ... Check logfile" + self.logfile)
        fh = logging.FileHandler(self.logfile)
        fh.setLevel(logging.INFO)
        # stream handler -- log at higher level
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)

        if self.verbose > 2 :
            print ("Setting file log level to TRACE and streams to INFO")
            fh.setLevel(logging.TRACE)
            self.log.setLevel(logging.TRACE)
            ch.setLevel(logging.INFO)
        elif self.verbose > 0 :
            print ("Setting file log level to DEBUG and streams to INFO")
            fh.setLevel(logging.DEBUG)
            self.log.setLevel(logging.DEBUG)
            ch.setLevel(logging.INFO)

        fh.setFormatter(formatter)
        self.log.addHandler(fh)
        ch.setFormatter(stream_formatter)
        self.log.addHandler(ch)
        return self.log