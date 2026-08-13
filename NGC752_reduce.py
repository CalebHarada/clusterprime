#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2026-08-12 14:13
Author: calebharada

ngc752_reduce.py

    Description: script to reduce the NGC 752 MegaPrime data, based on the 
        example provided here: 
        https://github.com/rdungee/clusterprime/blob/main/M67reduce.py
"""

##############################################
import os, sys
import warnings

import numpy as np

from astropy.io import fits
from astropy.table import Column, Table

import clusterprime as clp
##############################################


# *************
# *** SETUP ***
# *************

"""
** NOTE! ** There are several preliminary steps to complete before you 
can run this code. See the example linked on the GitHub above. The main points
are summarized here:
    - Put the member catalog in its own subdirectory and make sure it has
    the right column names
    - Download the bad pixel mask for MegaPrime ()
    - Set up all the directories the code expects
    - Download the data from the CFHT archive and organize it in subdirectories
    in the way the code expects (I wrote a python script to do this)
"""

# Setting overwrite to False to prevent overwriting any data that might
# already exist
overwrite = False

# Setting debug to False since this was only used during the development
debug = False

# Aperture size of 2 is what we settled on, this sets the aperture
# _radius_ at 2 times the seeing FWHM of the image
apsize = 2.00

# Create the config file, we use the default for the various directories
# Suppress warning about the cluster name
cwd = os.getcwd()
with warnings.catch_warnings(record=True) as w:
    config = clp.Config(cwd, 'NGC752', 'added_overlap_flag', apsize)


# We had XXX visits to NGC752 in total, meaning there were observations 000
# through XXX (obs000 to obsXXX), to "parallelize" reducing the data we
# can focus it on a subset of the observations set by this range. This
# line is doing that by user input (e.g. calling
#  'python NGC752reduce.py 0 20' will run it for obs000 to obs019)
obsis = range(int(sys.argv[1]), int(sys.argv[2]))
# Version that runs it without user input, commented out for now
# obsis = range(0, 20)

# Can also technically split on CCDs since there are 40 chips in the megaprime
# detector. These numbers are the .fits file extensions for each one, they do
# not put image data in the 0th extension, hence the use of [1,41)
ccdis = range(1, 41)



# ***********************
# *** SKY SUBTRACTION ***
# ***********************
# This step runs the sky subtraction on all obsis and ccdis specified above
# Start by constructing a list input directories
# e.g., ['/home/rdungee/cluster/data/M67/obs000',
#        '/home/rdungee/cluster/data/M67/obs001']
# which will pull data from those directories, run the sky subtraction, and then
# save the results to the matching reduce directories:
# /home/rdungee/cluster/data/M67reduce/obs000
#  and /home/rdungee/cluster/data/M67reduce/obs001
newobsdirs = []
for i in obsis:
    newobsdirs.append(config.data / f'obs{i:03}')

# Gather the actual file names for each directory, use a dictionary so that each
# directory is mapped directly to the list of files it contains, making it easy
# to confirm it found the right files
# e.g.,: {'obs000': ['/full/path/0000000.fits.fz', '/full/path/0000001.fits.fz']}
skysub = {}
for obs in newobsdirs:
    pointings = sorted(obs.glob('*.fits.fz'))
    skysub[obs.stem] = pointings

# Add whats been done to the logger for quick read through later
logger = clp.Logger()

# Run the skysubtraction
for fitsgroup in skysub:
    print("Running skysubtract for group: ", fitsgroup)
    clp.reduce.skysubtract(config, skysub[fitsgroup], fitsgroup, logger, 
                           overwrite=overwrite)