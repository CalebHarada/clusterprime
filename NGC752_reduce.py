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

"""
** NOTE! ** There are several preliminary steps to complete before you 
can run this code. See the example linked on the GitHub above. The main points
are summarized here:
    - Put the member catalog in its own subdirectory and make sure it has
    the right column names
    - Download the bad pixel mask for MegaPrime (from the CFHT archive)
    - Set up all the directories the code expects
    - Download the data from the CFHT archive and organize it in subdirectories
    in the way the code expects (I wrote a python script to do this)
"""



# *************
# *** SETUP ***
# *************

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
with warnings.catch_warnings():
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



# **********************
# *** SOURCE FINDING ***
# **********************
# Find all the sources in each chip of each fits files using DAOStarFinder from
# photutils

# Start by creating a list of all the directories with data we need to process
# e.g., ['/home/rdungee/cluster/data/M67reduce/obs000/0000000p']
# where inside that directory (which was created automatically by the previous
# step) is the sky background subtracted images
chipdirs = []
for i in obsis:
    chipdirs.extend(sorted((config.reduce / f'obs{i:03}').glob('*p')))
# Run source finding for each ccd in ccdis, for each directory from the step
# above
# Suppress warnings about deprecated FITS header key
with warnings.catch_warnings():
    for chipdir, outdir in zip(chipdirs, chipdirs):
        print(f"Find sources for {chipdir.parent.stem}, {chipdir.stem}")
        for ccdi in ccdis:
            print(f"CCD: {ccdi:02}")
            clp.reduce.findsources(chipdir, outdir, ccdi, overwrite=overwrite)
# This produces the untrimmed catalogs, which contain every "source" real or not
# these catalogs are stored with the sky subtracted image data, in the the
# reduced data directory subdirs: obsNNN/MMMMMMMp where MMMMMMMp was the filename
# of the fits file before sky subtraction (this subdir contains a file per ccd
# that has been reduced so far)
# The output is simply the table that DAOStarFinder returns, see the photutils
# docs on this for details on what it contains



# ************************
# *** CATALOG TRIMMING ***
# ************************
# We now trim the catalogs by cross matching against Gaia EDR3.
# ***NOTE*** if you want to change the catalog, you must change the function
# readcatalog contained in aperture.py (clusterprime/reduce/photometry/aperture.py)
# In there the catalog is hardcoded in the first line of the function as
# cat = Table.read(f"catalogs/{cluster}_gaiaedr3_plus_ps1.csv")
# a catalog file that you must construct yourself, it needs to have RA/Dec in
# epoch J2000.0 for comparison with megaprime data, it currently assumes the
# column names are "ra2k" and "de2k" for them respectively

# First build the input and output directory lists to cycle through
catdirs = []
for i in obsis:
    catdirs.extend(sorted((config.reduce / f'obs{i:03}').glob('*p')))
outdirs = []
for cd in catdirs:
    outdirs.append(config.analysis / cd.parent.name / cd.name)
trimsource = zip(catdirs, outdirs)

# Run the trimming, which crossmatches the list from the previous step against
# the Gaia EDR3 catalog, anything without a match to Gaia is discarded, real or
# not it will not have astrometry data
for catdir, outdir in trimsource:
    print(f"Crossmatching sources for {catdir.parent.stem}, {catdir.stem}")
    for ccdi in ccdis:
        print(f"CCD: {ccdi:02}")
        clp.reduce.trimsources(config, catdir, outdir, ccdi,
                               overwrite=overwrite)
# This step creates trimmed catalogs for each ccd in each obs subdir
# Columns include:
#  - xcentroid: x pixel centroid of source
#  - ycentroid: y pixel centroid of source
#  - racentroid: same but now in RA (deg)
#  - deccentroid: same but now in Dec (deg)
#  - gaia_id: the gaia identifier for the source, taken from crossmatching step
#  - nndist: the distance in arcsec to the nearest neighboring source
# The file is a astropy.table .ecsv format so it also has commented header lines,
# which contain metadata:
#  - Skymax: the peak sky value for the chip
#  - Gain: the detector gain
#  - Maxlin: the maxlinearity of the detector, for saturation cutoff
#  - Seeing: the seeing FWHM in pixels of that observation



# ******************
# *** PHOTOMETRY ***
# ******************
# Now compute the aperture photometry, using photutils this is pretty
# straight forward to do, most of the work now is keeping track of everything

# Start with directory lists again, looking for the trimmed catalogs and their
# matching reduced images for computing photometry
catdirs = []
for i in obsis:
   catdirs.extend(sorted((config.analysis / f'obs{i:03}').glob('*p')))
phot = zip(catdirs, catdirs)
# Run the photometry
for catdir, outdir in phot:
   print(f"Photometrizing {catdir.parent.stem}, {catdir.stem}")
   for ccdi in ccdis:
       print(f"CCD: {ccdi:02}")
       clp.reduce.photometrize(config, catdir, outdir, ccdi, 
                       overwrite=overwrite)
# This step creates photometry catalogs in the same directory as the catalogs
# Columns include:
#  - xcentroid: x pixel centroid of source
#  - ycentroid: y pixel centroid of source
#  - gaia_id: the gaia identifier for the source, taken from crossmatching step
#  - nndist: the distance in arcsec to the nearest neighboring source
#  - flux: the flux in the aperture
#  - flux_unc: the uncertainty of the flux from error propagation (Poisson, read noise, sky)
#  - MaskedPix?: if true, bad pixels were in the aperture
#  - SatPix?: if true, saturated pixels were in aperture
#  - mag_inst: instrumental magnitude of flux
#  - mag_unc: uncertainty on mag
# The file is a astropy.table .ecsv format so it also has commented header lines,
# which contain metadata:
#  - Skymax: the peak sky value for the chip
#  - Gain: the detector gain
#  - Maxlin: the maxlinearity of the detector, for saturation cutoff
#  - Seeing: the seeing FWHM in pixels of that observation
#  - AIRMASS: the airmass of the observation
#  - EXPTIME: the exposure time of the obs
#  - MJD-OBS: exposure start time in MJD format
#  - DATE-OBS: the date of the observation in UTC
#  - UTC-OBS: the exposure start time in UTC



# *******************
# *** EPOCH MEANS ***
# *******************
# Now we compute the mean magnitude for each source in a given epoch (i.e., the
# mean of up to 5 magnitudes, creating a point in the light curve)

# Directory set up as usual
obsnums = [config.analysis / f'obs{i:03}' for i in obsis]
epochmeans = zip(obsnums, obsnums)
# Run the epoch mean generating
for obsdir, outdir in epochmeans:
   print(f"Computing Epoch Means for {obsdir.stem}")
   for ccdi in ccdis:
       print(f"CCD: {ccdi:02}")
       clp.reduce.meanofpointings(config, obsdir, outdir, ccdi,
                                  overwrite=overwrite)
# This step generates a table per ccd that sit in the epoch reduced data
# directory (e.g. /home/rdungee/cluster/data/M67reduce/analysisname/obs000) for legacy
# reasons it includes the aperture size (2.00 in this example script) in
# the filename
# Columns include:
#  - gaia_id: the gaia identifier for the source, taken from crossmatching step
#  - magavg: mean mag_inst value
#  - magsdv: the standard deviation of the N measurements
#  - magunc: the estimated uncertainty using error propagation
#  - nndist: the distance in arcsec to the nearest neighboring source
#  - Ninmean: the number of mag_inst values used in computing the above (i.e.,
#             how many didn't have bad pixels/weren't partially on chip/no saturation)
# The file is a astropy.table .ecsv format so it also has commented header lines,
# which contain metadata:
#  - MJD-OBS: exposure start time in MJD format
#  - DATE-OBS: the date of the observation in UTC
#  - UTC-OBS: the exposure start time in UTC
#  - Seeing: the seeing FWHM in pixels of that observation
