import matplotlib.pyplot as plt
import numpy as np 
import pandas as pd
from matplotlib import cm
import itertools

#3D
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mpl_toolkits.mplot3d import art3d

#2D Hist
import matplotlib.patches as patches
from matplotlib.path import Path

# Colors
import matplotlib.colors
from matplotlib.colors import LogNorm
import copy
import colormap as colormap

#Confidence
import scipy as sp
import scipy.stats
from scipy import stats

import os, sys
import glob
from os import listdir
from os.path import isfile, join
import re

# Time
import datetime

#Gifs 
import imageio

# For sorting Class List
import operator

# For Setting up data Structure
import pathlib

from scipy.optimize import curve_fit


class impactClass:
	def __init__(self, chainFile = None, chainDir = None, GRS_num = 1, burnIn = 0.5, outDir = 'data'): 
		"""
			if ChainFile is specified, reads in from pickle data
			if chainDir os specified, writes pickle data
		"""
		if chainDir is not None:
			""" THIS FUNCTION IS UNTESTED """
			"""
			Function to read micrometeoroite MCMC chain files. Assumes directory structure 
			as in the Aug2017 runs directory on tsankawi. Output is a python pickle file 
			containing a dictionary with the relevant chain information. 
			Arguments
			   chainDir = directory corresponding to the MCMC output is found
			   GRS_num = index of the grs for this chain (1 or 2)
			   burnIn = fraction of chain to throw out for burn in
			   outDir = output directory for pickle file (name will be generated automatically)
			   
			Ira Thorpe
			2018-05-12 
			"""
			
			# modules
			import os
			import pickle
			import string
			
			# find directory and get gps time
			base = os.path.basename(chainDir)
			gpsTime = float(base[len(base) - 10 : len(base)])
			
			# load impactChain
			impFile = chainDir +'/impactchain.dat'
			dat = np.loadtxt(impFile)
			N = np.shape(dat)[0]
			trim = int(float(N) * burnIn);
			dat = np.delete(dat, slice(0, trim), axis=0)
			
			# build into a dictionary
			t0 = np.median(dat[:, 3])

			self.segment = gpsTime
			self.gps     = gpsTime + 1638.4 - t0
			self.N       = np.shape(dat)[0]
			self.logL    = dat[:, 0]
			self.snr     = dat[:, 1]
			self.t0      = -(dat[:, 3] - t0)
			self.Ptot    = dat[:, 4]
			self.lat     = 90 - (np.arccos(dat[:,7]) * 180 / np.pi)
			self.lon     = np.mod(dat[:, 8] * 180 / np.pi + 180, 360) - 180
			self.rx      = dat[:, 10]
			self.ry      = dat[:, 11]
			self.rz      = dat[:, 12] 
			self.face    = dat[:, 9]
			self.grs     = GRS_num


			# Dictionary to load to file, only because I don't want to break Ira's build
			data = {
				'segment' : self.segment,
				'gps'     : self.gps,
				'N'       : self.N,
				'logL'    : self.logL,
				'snr'     : self.snr,
				't0'      : self.t0,
				'Ptot'    : self.Ptot, 
				'lat'     : self.lat, 
				'lon'     : self.lon,
				'rx'      : self.rx,
				'ry'      : self.ry,
				'rz'      : self.rz,
				'face'    : self.face,  
			}

			df_veto = self.getVetoList()
			self.isValid = self.isValid(df_veto, checkReal = True)

			# load log likelihood chain
			logLfile = chainDir +'/logLchain.dat'
			dat = np.loadtxt(logLfile)
			trim = int(float(self.N) * burnIn);
			dat = np.delete(dat, slice(0, trim), axis=0)
			
			# compute detection fraction
			dfrac = np.sum(dat[:, 0]) / (np.shape(dat)[0])
			self.dfrac = dfrac
			
			# save data in processed directory
			pickle.dump(data, open(str(os.cwd) + '/' + 
						outDir + '/' + str(int(gpsTime)) + '_grs' + 
						str(int(GRS_num)) + '.pickle','wb'))

		else:
			import pickle
			"Converts Ira's dictionary into a class"


			fid = open(chainFile,'rb')
			data = pickle.load(fid)
			fid.close()
			
			# Loads dictionary into data
			self.data = data
			
			self.segment = data['segment']
			self.gps     = data['gps']
			self.N       = data['N']
			self.logL    = data['logL']
			self.snr     = data['snr']
			self.t0      = data['t0']
			self.Ptot    = data['Ptot'] * 10 ** 6 # Micro Ns
			self.lat     = data['lat']
			self.lon     = data['lon']
			self.rx      = data['rx']
			self.ry      = data['ry']
			self.rz      = data['rz']
			self.face    = data['face']
			self.grs     = GRS_num

			df_veto = self.getVetoList()
			self.isValid = self.isValid(df_veto, checkReal = True)
			self.define_coords()

	# ---------------------------------------#
	#          Getters and Setters           #
	# ---------------------------------------#

	def __str__(self):
		return str(self.__class__) + ": " + str(self.__dict__)

	def filename(self):
		""" Returns segment as a string """
		return str(int(self.segment))

	def getParam(self, param):
		""" Given String returns whole parameter chain""" 
		if (param == 'segment'):
			return self.segment
		elif param == 'gps':
			return self.gps
		elif param == 'N':
			return self.N
		elif param == 'snr':
			return self.snr
		elif param == 't0':
			return self.t0
		elif param == 'Ptot':
			return self.Ptot
		elif param == 'lat':
			return self.lat
		elif param == 'lon':
			return self.lon
		elif param == 'rx':
			return self.rx
		elif param == 'ry':
			return self.ry
		elif param == 'rz':
			return self.rz
		elif param == 'face':
			return self.face
		elif param == 'grs':
			return self.grs
		elif param == 'isValid':
			return self.isValid
		else: 
			print("Invaid Input: given,", param)

	def getMedian(self, param):
		""" 
			Returns median of parameter if len(param) > 1,
			else returns parameter
		"""
		if (param == 'segment'):
			return self.segment
		elif param == 'gps':
			return self.gps
		elif param == 'N':
			return self.N
		elif param == 'snr':
			return np.median(self.snr)
		elif param == 't0':
			return np.median(self.t0)
		elif param == 'Ptot':
			return np.median(self.Ptot)
		elif param == 'lat':
			return np.median(self.lat)
		elif param == 'lon':
			return np.median(self.lon)
		elif param == 'rx':
			return np.median(self.rx)
		elif param == 'ry':
			return np.median(self.ry)
		elif param == 'rz':
			return np.median(self.rz)
		elif param == 'face':
			return stats.mode(self.face)
		elif param == 'grs':
			return self.grs
		elif param == 'isValid':
			return self.isValid
		else: 
			print("Invaid Input: given,", param)

	def getVetoList(self):
		names = ['isImpact', 't', 'UTC', 'run', 'dt',
				'prob',
				'p', 'dp',
				'c', 'dc',
				'phi', 'dphi',
				'x', 'dx',
				'y', 'dy',
				'z', 'dz']
		df_veto = pd.read_csv('Impacts/impact_cat.csv', header = None, names = names)
		df_veto['isImpact'] = df_veto['isImpact'].map(
			{'TRUE': True, 'FALSE': False, 'M':True})

		return df_veto

	
	def isValid(self, df_veto, checkReal = True):
		for i in range(len(df_veto['t'])):
			diff = np.abs(self.gps - df_veto['t'][i])
			if diff < 1:
				# Only Counts if it's a real impact
				return df_veto['isImpact'][i]
		# if it's not in my list return True
		return True

	def summaryString(self,
			keys = ['Ptot','lat','lon','rx','ry','rz'],
			scale = [1.0, 1.0, 1.0, 100.0, 100.0, 100.0]):
		"""
		function to produce a string for use in a ApJ style fancy table
		"""
		p = np.zeros([np.shape(keys)[0],3])

		for idx, kk in enumerate(keys) :
			p[idx, :] = np.percentile(self.getParam(kk) * scale[idx], [50, 2.75, 97.5])

		faceNames = ['+x+x','+x+y','+y+y','+y-x','-x-x','-x-y','-y-y','-y+x','+z+z','-z-z']
		cf, bf = np.histogram(self.face, bins=np.arange(0.5, 11, 1),density = True)

		if np.max(cf) > 0.7 :
			faceText = faceNames[np.argmax(cf)]
		else:
			faceText = '-'

		if self.skyArea < 5000:#(0.1*41253) :
			areaText = str('{0:.0f}'.format(self.skyArea))
			SClatText = str('{0:.0f}'.format(self.lat_c))
			SClonText = str('{0:.0f}'.format(self.lon_c))
			SunlatText = str('{0:.0f}'.format(self.lat_c_sun))
			SunlonText = str('{0:.0f}'.format(self.lon_c_sun))
		else :
			areaText = '-'
			SClatText = '-'
			SClonText = '-'
			SunlatText = '-'
			SunlonText = '-'

		d = datetime.datetime.fromtimestamp(self.gps + 315964783)
		printTab = {
			'date' : d.strftime('%Y-%m-%d'),
			'gps'  : self.gps,
			'Pmed' : p[0, 0],
			'PerrU': p[0, 2] - p[0, 0],
			'PerrL': p[0, 1] - p[0, 0],
			'face' : faceText,
			'area' : areaText,
			'SClat' : SClatText,
			'SClon' : SClonText,
			'Sunlat' : SunlatText,
			'Sunlon' : SunlonText}



		tabStr = str((r'{0[date]:s} & ' +
			r'{0[gps]:.0f} & ' +
			r'${0[Pmed]:4.1f}^{{+{0[PerrU]:.1f}}}_{{{0[PerrL]:.1f}}}$ & ' +
			r'{0[face]:s} & ' +
			r'{0[area]:s} & ' +
			r'{0[SClat]:s} & ' +
			r'{0[SClon]:s} & ' +
			r'{0[Sunlat]:s} & ' +
			r'{0[Sunlon]:s} \\').format(printTab))

		return tabStr


	# ---------------------------------------#
	#      Coordinate Transformations        #
	# ---------------------------------------#

	def getSCquats(self, doText = False):
		"""
		function to get spacecraft quaternions    
		function to read SC quaternion file. Can either read a python binary file (faster, 
		default) or an ASCII text file (slower)
		
		Ira Thorpe
		2018-05-12
		"""
		#import libraries
		import numpy as np, quaternion
		import os
		import pathlib
		
		# get current working directory
		p = pathlib.PurePath(os.getcwd())
		baseDir = str(p.parent)
		
		# load Quaternion data
		if doText:
			quatFile = baseDir +'/rawData/allQuats.txt'
			dat = np.loadtxt(quatFile)
		else :
			quatFile = baseDir + '/data/quats.npy'
			dat = np.load(quatFile)
			
		# separate out gps time (1st column) from quaternions (columns 2-5)
		allGPS = np.array(dat[...,0])
		allQuats = quaternion.as_quat_array(np.array(dat[...,[4,1,2,3]]))
		
		# find nearest gps time
		idxmin = (np.abs(allGPS - self.gps)).argmin()
		impQuat = allQuats[idxmin]

		# return the quaternion
		return impQuat

	def ECI_to_SUN(self):
		"""
		returns rotation quaternion from ECI to SUN coordinates

		"""
		import numpy as np, quaternion
		import os
		import pathlib
		from astropy.time import Time
		from astropy.coordinates import get_body

		# quaternion to rotate from ECI to Sun (place +x in Sunward direction)
		# Get sun location 
		s = get_body('sun', Time(self.gps ,format = 'gps', scale = 'utc'))
		sun_dec_rad = s.dec.value * np.pi / 180
		sun_ra_rad = s.ra.value * np.pi / 180

		# unit vector in sunward direction
		usun = np.array([np.cos(sun_dec_rad) * np.cos(sun_ra_rad),
					np.cos(sun_dec_rad) * np.sin(sun_ra_rad), 
					np.sin(sun_dec_rad)])
		
		# find quaternion to go between x and sunward direction
		ux = np.array([1, 0, 0])
		usun_x_ux = np.cross(usun, ux)
		qr_ECIx_sun = quaternion.as_quat_array([1 + np.dot(ux, usun),
											usun_x_ux[0],
											usun_x_ux[1],
											usun_x_ux[2]])
		qr_ECIx_sun = qr_ECIx_sun / quaternion.np.abs(qr_ECIx_sun)

		return qr_ECIx_sun


	# function to locate impact and estimate area using healpix binning.
	def findSkyAngles(self, CI = 0.68, nside = 32):
		"""
		function to determine impact sky area using HEALPIX binning. Returns 1 sigma sky area in 
		square degrees and central point latitude and longitude. If dictionary passed to the 
		function has sun-frame angles in addition to SC-frame angles, it will operate on both.
		Arguments
			data = dictionary containing chain data
			CI = confidence interval for sky area
			nside = HEALPIX number of sides
		
		Ira Thorpe
		2018-05-24
		"""
		#import libraries
		import healpy as hp
		import numpy as np
		import matplotlib.pyplot as plt

		# Build the HEALPIX map
		npix = hp.nside2npix(nside)
		mp = np.arange(npix)

		# Convert data to HEALPIX
		dat_hp = hp.pixelfunc.ang2pix(nside, self.lon, self.lat, nest=False, lonlat=True)

		# Make the histogram
		bin_edges = np.arange(-0.5, npix + 0.5, 1.0)
		bin_centers = np.arange(0, npix, 1.0)
		cnt_hp, bins = np.histogram(dat_hp, bin_edges)
		
		# Measure centroid and sky area
		cdf = np.cumsum(cnt_hp.astype('float')) / float(self.N)        
		ilb = (np.abs(cdf - ((1.0 - CI) / 2.0))).argmin()
		iub = (np.abs(cdf - (1.0 - ((1.0 - CI) / 2.0)))).argmin()
		imed = (np.abs(cdf - 0.5)).argmin()
		area = 41253.0 * float(iub - ilb) / float(npix)
		lon_c, lat_c = hp.pixelfunc.pix2ang(nside, imed, nest = False, lonlat = True)
		lon_c = np.mod(180 + lon_c, 360) - 180
		
		# put back into data dictionary
		self.lat_c = lat_c
		self.lon_c = lon_c
		self.skyArea = area
		self.healPix = cnt_hp / float(self.N)
		
		# if Sun angles are present, repeat for them
		if hasattr(self, 'lon_sun'):
			# Convert data to HEALPIX
			dat_hp = hp.pixelfunc.ang2pix(nside, self.lon_sun, self.lat_sun, nest = False, lonlat = True)

			# Make the histogram
			cnt_hp, bins = np.histogram(dat_hp, bin_edges)
		
			# Measure sky area
			cdf = np.cumsum(cnt_hp.astype('float')) / float(self.N)        
			ilb = (np.abs(cdf - ((1.0 - CI) / 2.0))).argmin()
			iub = (np.abs(cdf - (1.0 - ((1.0 - CI) / 2.0)))).argmin()
			imed = (np.abs(cdf - 0.5)).argmin()
			area = 41253.0 * float(iub - ilb) / float(npix)
			lon_c, lat_c = hp.pixelfunc.pix2ang(nside, imed, nest = False, lonlat = True)
			lon_c = np.mod(180 + lon_c, 360) - 180
			
			# put into dictionary
			self.lat_c_sun = lat_c
			self.lon_c_sun = lon_c
			self.skyArea_sun = area
			self.healPix_sun = cnt_hp / float(self.N)

		# if Micro angles are present, repeat for them
		if hasattr(self, 'lon_micro'):
			# Convert data to HEALPIX
			dat_hp = hp.pixelfunc.ang2pix(nside, self.lon_micro, self.lat_micro, nest = False, lonlat = True)

			# Make the histogram
			cnt_hp, bins = np.histogram(dat_hp, bin_edges)
		
			# Measure sky area
			cdf = np.cumsum(cnt_hp.astype('float')) / float(self.N)        
			ilb = (np.abs(cdf - ((1.0 - CI) / 2.0))).argmin()
			iub = (np.abs(cdf - (1.0 - ((1.0 - CI) / 2.0)))).argmin()
			imed = (np.abs(cdf - 0.5)).argmin()
			area = 41253.0 * float(iub - ilb) / float(npix)
			lon_c, lat_c = hp.pixelfunc.pix2ang(nside, imed, nest = False, lonlat = True)
			lon_c = np.mod(180 + lon_c, 360) - 180
			
			# put into dictionary
			self.lat_c_micro = lat_c
			self.lon_c_micro = lon_c
			self.skyArea_micro = area
			self.healPix_micro = cnt_hp / float(self.N)

		return self
		
	# function to convert angles from SC frame to Sun-center frame (in degrees)
	def SCtoSun(self):
		"""
		funciton to convert angles from SC frame to sun-centered frame used by micrometeoroid 
		population models. 
		
		Ira Thorpe
		2018-05-24
		"""
		
		# libraries & modules
		import numpy as np, quaternion
		from microTools import getSCquats
		from astropy.time import Time
		from astropy.coordinates import get_body
		
		# make quaternion array from SC latitude and longitude
		lon_sc_rad = self.lon * np.pi / 180
		lat_sc_rad = self.lat * np.pi / 180
		n = np.vstack((np.zeros(np.shape(lat_sc_rad)),
					np.cos(lat_sc_rad) * np.cos(lon_sc_rad),
					np.cos(lat_sc_rad) * np.sin(lon_sc_rad),
					np.sin(lat_sc_rad)))
		q_coord_sc = quaternion.as_quat_array(np.transpose(n))

		# read SC quaternion (rotate from SC to ECI)
		qr_ECI_SC = getSCquats(int(self.gps))
		
		# perform first rotation
		q_coord_ECI = qr_ECI_SC * q_coord_sc * quaternion.np.conjugate(qr_ECI_SC)
		
		# get rotation matrix from ECI to SUN
		qr_ECIx_sun = self.ECI_to_SUN()
		
		# perform second rotation
		q_coord_sun = qr_ECIx_sun * q_coord_ECI * quaternion.np.conjugate(qr_ECIx_sun)
		
		# extract latitude and longitude in Sunward direction
		q_coord_sun_n = quaternion.as_float_array(q_coord_sun)
		lon_sun = 180 / np.pi * np.arctan2(q_coord_sun_n[:, 2], 
										   q_coord_sun_n[:, 1])
		lat_sun = 180 / np.pi * np.arctan2(q_coord_sun_n[:, 3],
								np.sqrt(np.square(q_coord_sun_n[:, 1]) + np.square(q_coord_sun_n[:, 2])))
		
		# add to dictionary
		self.lon_sun = lon_sun
		self.lat_sun = lat_sun
		return self
	
	def SuntoMicro_OLD(self):
		"""
		Rotates from sun centered frame to strange micrometeoroid frame
				
				(sun)  (direction of motion around sun)   (earth)
				 -90                 0                      +90
				  o                  x                       .

		"""
		self.lon_micro = np.copy(self.lon_sun)
		self.lat_micro = np.copy(self.lat_sun)

		for i, lon in enumerate(self.lon_micro):
			if lon - 90 < -180:
				self.lon_micro[i] = 180 + 90 + lon
			else:
				self.lon_micro[i] -= 90
		return self


	def SuntoMicro(self):
		"""
		Rotates from sun centered frame to strange micrometeoroid frame
				
	(direction of motion around sun)                    (anti-earth around sun)
				 -90                sun                      +90
				  o                  x                       .

		"""
		self.lon_micro = -1 * np.copy(self.lon_sun)
		self.lat_micro = np.copy(self.lat_sun)
		"""

		for i, lon in enumerate(self.lon_micro):
			if lon - 90 < -180:
				self.lon_micro[i] = 180 + 90 + lon
			else:
				self.lon_micro[i] -= 90
		"""
		return self

	
	# function to convert angles from SC frame to Sun-center frame (in degrees)
	def SuntoSC(self):
		"""
		function to convert angles from sun-centered frame used by micrometeoroid 
		population models to SC frame. 
		
		Sophie Hourihane
		2018-06-12
		"""
		
		# libraries & modules
		import numpy as np, quaternion
		from microTools import getSCquats
		from astropy.time import Time
		from astropy.coordinates import get_body
		
		# get longitude and latitude in radians
		try:
			lon_sun_rad = self.lon_sun * np.pi / 180
			lat_sun_rad = self.lat_sun * np.pi / 180
		except AttributeError:
			print("self.lon_sun or self.lat_sun does not exist!")
			return

		# turn long lat angles into quaternion
		n = np.vstack((np.zeros(np.shape(lat_sun_rad)),
					np.cos(lat_sun_rad) * np.cos(lon_sun_rad),
					np.cos(lat_sun_rad) * np.sin(lon_sun_rad),
					np.sin(lat_sun_rad)))
		q_coord_sun = quaternion.as_quat_array(np.transpose(n))

		# get rotation quaternion
		qr_ECIx_sun = self.ECI_to_SUN()
		
		# Rotate from SUN to ECI:
		q_coord_ECI = quaternion.np.conjugate(qr_ECIx_sun) * q_coord_sun * qr_ECIx_sun

		# read SC quaternion (get rotation q from ECI to SC)
		qr_ECI_SC = getSCquats(int(self.gps))

		# rotate from ECI to SC
		q_coord_sc = quaternion.np.conjugate(qr_ECI_SC) * q_coord_ECI * qr_ECI_SC

		# extract latitude and longitude in SC direction
		q_coord_sc_n = quaternion.as_float_array(q_coord_sc)
		lon_sc = 180 / np.pi * np.arctan2(q_coord_sc_n[:, 2], 
										   q_coord_sc_n[:, 1])
		lat_sc = 180 / np.pi * np.arctan2(q_coord_sc_n[:, 3],
								np.sqrt(np.square(q_coord_sc_n[:, 1]) + np.square(q_coord_sc_n[:, 2])))

		# add to dictionary
		self.lon = lon_sc
		self.lat = lat_sc
		return self

	# ---------------------------------------#
	#          Graphing Functions            #
	# ---------------------------------------#

	# function to make dual corner plots
	def dualCorner(self, data2,
			keys=['Ptot', 'lat', 'lon', 'rx', 'ry', 'rz'],
			labels = ['$P_{tot}\,[\mu N]$', '$lat\,[deg]$', '$lon\,[deg]$', 
					 '$r_x\,[cm]$', '$r_y\,[cm]$', '$r_z\,[cm]$'],
			scale = [1.0e6, 1.0, 1.0, 100.0, 100.0, 100.0],
			Nbins = 30):

		"""
		function to produce a 'dual corner plot': basically a corner plot for each GRS with the 
		lower corner being GRS1 and the upper corner being GRS2. Useful for comparing chains
		Arguments:
			self = class containing grs1 data 
			data2 = class containing grs2 data
			key = dictionary keys corresponding to the parameters to plot
			labels = LaTeX labels for the keys
			scale = scale factors for the keys
			Nbins = number of bins
			
		Ira Thorpe
		2018-05-30
		"""
		# import
		import numpy as np
		import matplotlib.pyplot as plt
		import matplotlib
		
		# get number of keys
		Nkeys = np.shape(keys)[0]

		# initialize figure
		hf = plt.figure(figsize=(18, 16), dpi= 80, facecolor='w', edgecolor='k')
		kk = 0
		# loop over keys for x (rows)
		for ii in range(0, Nkeys):
			# get x data for both GRS
			x1 = self.getParam(keys[ii]) * scale[ii]
			N1 = np.shape(x1)[0]
			x2 = data2.getParam(keys[ii]) * scale[ii]
			N2 = np.shape(x2)[0]

			# determine x bins
			xtot = np.concatenate([x1, x2])
			xbins = np.linspace(np.min(xtot), np.max(xtot), Nbins)
			xe = xbins - 0.5 * (xbins[1] - xbins[0])
			xe = np.append(xe, xe[Nbins - 1] + xe[1] - xe[0])

			# loop over keys for y (columns)
			for jj in range(0, Nkeys):
				# lower corner
				if jj < ii:
					kk = kk + 1
					# get y data
					y1 = self.getParam(keys[jj]) * scale[jj]
					y2 = data2.getParam(keys[jj]) * scale[jj]

					# determine y bins
					ytot = np.concatenate([y1, y2])
					ybins = np.linspace(np.min(ytot), np.max(ytot), Nbins)
					ye = ybins - 0.5 * (ybins[1] - ybins[0])
					ye = np.append(ye, ye[Nbins - 1] + ye[1] - ye[0])

					# 2D histogram and plot
					# Handleing strange binning error, bins were too small
					try:
						c_x1y1, x2e, y2e = np.histogram2d(x1, y1, [xbins, ybins], normed = True)
					except:
						c_x1y1, x2e, y2e = np.histogram2d(x1, y1, normed = True)
					plt.subplot(Nkeys, Nkeys, kk)
					plt.contourf(c_x1y1, extent = [y2e.min(), y2e.max(), x2e.min(), x2e.max()], cmap=matplotlib.cm.Reds)
					ax = plt.gca()
					ax.grid(color = 'k',linestyle = '--')

				# diagonals
				elif jj == ii:
					# histograms
					c_x1x1, x1e = np.histogram(x1, xe, normed = True)
					c_x2x2, x1e = np.histogram(x2, xe, normed = True)

					# plot
					kk = kk + 1
					plt.subplot(Nkeys, Nkeys, kk)
					plt.step(xbins, c_x1x1, 'r')
					plt.step(xbins, c_x2x2, 'b')
					ax = plt.gca()
					ax.grid(color = 'k', linestyle = '--')
					ax.legend(['GRS%i'%self.grs, 'GRS%i'%data2.grs])
					ax.set_yticklabels([])

				# upper corner
				elif jj > ii:
					kk = kk + 1

					# determine y bins
					y1 = self.getParam(keys[jj]) * scale[jj]
					y2 = data2.getParam(keys[jj]) * scale[jj]
					ytot = np.concatenate([y1, y2])
					ybins = np.linspace(np.min(ytot), np.max(ytot), Nbins)
					ye = ybins - 0.5 * (ybins[1] - ybins[0])
					ye = np.append(ye, ye[Nbins - 1]+ ye[1] - ye[0])

					# Handleing strange binning error, bins were too small
					try:
						c_x2y2, x2e, y2e = np.histogram2d(x2, y2, [xbins, ybins], normed = True)
					except:	
						c_x2y2, x2e, y2e = np.histogram2d(x2, y2, normed = True)
					plt.subplot(Nkeys, Nkeys, kk)
					plt.contourf(c_x2y2, extent = [y2e.min(), y2e.max(), x2e.min(), x2e.max()], cmap = matplotlib.cm.Blues)
					ax = plt.gca()
					ax.grid(color='k',linestyle='--')

				# assign axes labels
				if jj == 0:
					if ii > 0:
						ax.yaxis.label.set_text(labels[ii])
					else:
						ax.set_yticklabels([])
				elif jj == Nkeys - 1:
					if ii < Nkeys - 1:
						ax.yaxis.label.set_text(labels[ii])
						ax.yaxis.set_label_position('right')
						ax.yaxis.tick_right()
					else:
						ax.set_yticklabels([])
				else:
					ax.set_yticklabels([])
				if ii == 0 :
					ax.xaxis.label.set_text(labels[jj])
					ax.xaxis.set_label_position('top')
					ax.xaxis.tick_top()
				elif ii == Nkeys - 1:
					ax.xaxis.label.set_text(labels[jj])
				else:
					ax.set_xticklabels([])
		return hf

	def makeMollweide(self, frame = None):
		"""
			frame: string, defines coordinates
			None    = SC data
			'sun'   = sun centered data 
			'micro' = sun at -90 data
		"""

		from astropy.coordinates import SkyCoord
		from astropy.io import fits
		from astropy import units as u
		import ligo.skymap.plot

		fig = plt.figure(figsize=(8, 4), dpi=100)
		ax = plt.axes(
			projection = 'geo degrees mollweide')

		self = self.findSkyAngles()


		title = ('GRS%s Impact direction posterior for '%(self.grs) + 
					str(int(self.gps)))
		if frame == 'micro':
			self = self.SCtoSun()
			self = self.SuntoMicro()
			self = self.findSkyAngles()
			ax.imshow_hpx(self.healPix_micro, cmap='cylon')
			title += " [Micrometeroid]"
		elif frame == 'sun':
			self = self.SCtoSun()
			self = self.findSkyAngles()
			ax.imshow_hpx(self.healPix_sun, cmap='cylon')
			title += " [sun]"
		else:
			ax.imshow_hpx(self.healPix, cmap='cylon')
			title += " [spacecraft]"

		ax.set_title(title)
		ax.grid(linestyle = ':')
		ax.coords[0].set_ticks(exclude_overlapping = True, spacing = 45 * u.deg)
		ax.coords[1].set_ticks(exclude_overlapping = True, spacing = 30 * u.deg)

		return fig

	# ---------------------------------------#
	#            3D LPF Functions            #
	# ---------------------------------------#

	def define_coords(self):
		"""
		Defines the coordinates of the spacecraft

		"""
		self.H = 8.315000e-01        # Height of spacecraft [m]
		self.xsc = np.zeros(8)       # initializing x array 
		self.ysc = np.zeros(8)	    # initializing y array
		self.xsc[0] =     -9.260000e-01 # x coordinate of spacecraft bottom deck corner 1 [m] 'SC_BOT_CORNER_1_X': 
		self.ysc[0] =     -2.168000e-01 # y coordinate of spacecraft bottom deck corner 1 [m] 'SC_BOT_CORNER_1_Y': 
		self.xsc[1] =     -9.260000e-01 # x coordinate of spacecraft bottom deck corner 2 [m] 'SC_BOT_CORNER_2_X': 
		self.ysc[1] =      2.048000e-01 # y coordinate of spacecraft bottom deck corner 2 [m] 'SC_BOT_CORNER_2_Y': 
		self.xsc[2] =     -5.263000e-01 # x coordinate of spacecraft bottom deck corner 3 [m] 'SC_BOT_CORNER_3_X': 
		self.ysc[2] =     8.970000e-01  # y coordinate of spacecraft bottom deck corner 3 [m] 'SC_BOT_CORNER_3_Y': 
		self.xsc[3] =     5.163000e-01  # x coordinate of spacecraft bottom deck corner 4 [m  'SC_BOT_CORNER_4_X': 
		self.ysc[3] =     8.970000e-01  # y coordinate of spacecraft bottom deck corner 4 [m] 'SC_BOT_CORNER_4_Y': 
		self.xsc[4] =     9.160000e-01  # x coordinate of spacecraft bottom deck corner 5 [m] 'SC_BOT_CORNER_5_X': 
		self.ysc[4] =     2.048000e-01  # y coordinate of spacecraft bottom deck corner 5 [m] 'SC_BOT_CORNER_5_Y': 
		self.xsc[5] =     9.160000e-01  # x coordinate of spacecraft bottom deck corner 6 [m] 'SC_BOT_CORNER_6_X': 
		self.ysc[5] =     -2.168000e-01 # y coordinate of spacecraft bottom deck corner 6 [m] 'SC_BOT_CORNER_6_Y': 
		self.xsc[6] =     5.163000e-01  # x coordinate of spacecraft bottom deck corner 7 [m] 'SC_BOT_CORNER_7_X': 
		self.ysc[6] =     -9.090000e-01 # y coordinate of spacecraft bottom deck corner 7 [m] 'SC_BOT_CORNER_7_Y': 
		self.xsc[7] =     -5.263000e-01 # x coordinate of spacecraft bottom deck corner 8 [m] 'SC_BOT_CORNER_8_X': 
		self.ysc[7] =     -9.090000e-01 # y coordinate of spacecraft bottom deck corner 8 [m] 'SC_BOT_CORNER_8_Y': 


	def dictionaryToDataFrame(self, dictionary):
		"""
		Converts dictionary to pandas dataframe
		"""
		# Creates a dataframe from the given dictionary
		df = pd.DataFrame()
		df['face'] = dictionary['face']
		df['xloc'] = dictionary['rx']
		df['yloc'] = dictionary['ry']
		df['zloc'] = dictionary['rz']
		return df

	#### Helper functions for 3d Patch ###

	# Find equaltion of a line
	def findmb(self, x1, y1, x2, y2):
		m = (y2 - y1) / (x2 - x1)
		b = y1 - m * x1
		return m, b

	def dataFrameOnlyFace(self, df, facenumber):
		"""
		Returns dataframe with only values on a single face

		"""
		
		# Make copy of original df so we dont modify
		# important values
		df_copy = df.copy()
		return df_copy.loc[df['face'] == facenumber, :]
		
	def translate_to_origin(self, df, facenumber):
		# translates side to origin

		# REQUIRES: dataframe only has values in specified face

		## 	 .  o        .   x
		##       \     
		## .      . -> .       .
		##                 o 
		## .      .    .    \  .

		##   .  .        .   .

		df.loc[:, 'xloc'] -= self.xsc[facenumber]
		df.loc[:, 'yloc'] -= self.ysc[facenumber]
		return df


	def translate_from_origin(self, xedges, yedges, facenumber):
		# translates side to origin

		# REQUIRES: dataframe only has values in specified face

		## 	 .  o        .   x
		##       \     
		## .      . <- .       .
		##                 o 
		## .      .    .    \  .

		##   .  .        .   .

		xedges += self.xsc[facenumber]
		yedges += self.ysc[facenumber]

		return xedges, yedges



	def rotate_at_origin(self, df, facenumber, y_old = None, back = False):
		# rotates face to origin
		# if back, df is a numpy array
		# else df is a dataframe

		## 	 .  .        .   .
		##            
		## .      . -> .       .
		##     o           o --   
		## .     \.    .     x .

		##   .  .        .   .

		# fixes indexing problem, xsc[8] = xsc[0]
		if (facenumber == 7):
			base_vector = [self.xsc[0] - self.xsc[facenumber], 
						  self.ysc[0] - self.ysc[facenumber]]
		elif (facenumber < 7):
			base_vector = [self.xsc[facenumber + 1] - self.xsc[facenumber], 
						  self.ysc[facenumber + 1] - self.ysc[facenumber]]
		else:
			print("facenumber = %s"%(facenumber), " is out of range")
			raise ValueError
			return

		# unit version of base vector
		unit_BV = base_vector / np.linalg.norm(base_vector)
		origin = [1, 0]

		cos_theta = np.dot(unit_BV, origin)
		theta = np.arccos(cos_theta)

		# some of the faces need to rotate larger angle
		if facenumber in [0, 1, 7]:
			theta = 2 * np.pi - theta

		# backwards rotation
		if back:
			# Since we are transforming from origin
			# x = xedges
			# y = zeros

			#since we are moving backwards, rotate back
			theta *= -1

			x_old = df
			
			# True for 3d rotation
			if y_old is None:
				y_old = np.zeros_like(df)
			else:
				theta *= -1
				# Works when we have non-zero y values
				RotMatrix = np.array([[np.cos(theta),  np.sin(theta)],
							 		[-np.sin(theta), np.cos(theta)]])

				x, y = np.meshgrid(x_old, y_old)
				return np.einsum('ji, mni -> jmn', RotMatrix, np.dstack([x, y]))

			xedges = x_old * np.cos(theta) - y_old * np.sin(theta) 
			yedges = x_old * np.sin(theta) + y_old * np.cos(theta) 

			return xedges, yedges

		# forwards rotation	
		else:
			# Must make copy so these values do not change
			df_old = df.copy()
			x_old = df_old.loc[:, 'xloc']
			y_old = df_old.loc[:, 'yloc']

			df.loc[:, 'xloc'] = x_old * np.cos(theta) - y_old * np.sin(theta) 
			df.loc[:, 'yloc'] = x_old * np.sin(theta) + y_old * np.cos(theta) 


		return df, theta
	




	def hist(self, df, facenumber, N, length_df):
		## REQURES
		# Already rotated to origin

		# deals with numpy hist2d bug
		# if only 1 hit, just drop the side
		if len(df.index) == 1:

			df = df[df.face != facenumber] 	
			#df.drop(df.index[0])

		Ltotal = self.xsc[5] - self.xsc[0]                   
		Wtotal = self.ysc[2] - self.ysc[7]

		# Bins / Unit Length
		ndensity = N / Ltotal
		
		# Original position base
		if (facenumber == 7):
			base_vector = [self.xsc[0] - self.xsc[facenumber], 
						  self.ysc[0] - self.ysc[facenumber]]
		elif (facenumber < 7):
			base_vector = [self.xsc[facenumber + 1] - self.xsc[facenumber], 
						  self.ysc[facenumber + 1] - self.ysc[facenumber]]

		elif facenumber == 8 or facenumber == 9:
			binsheight = int(Wtotal * ndensity)  

			minfacex = self.xsc[0]
			maxfacex = self.xsc[5]

			minfacey = self.ysc[7]
			maxfacey = self.ysc[2]
			
			#input data
			xs = df.loc[:, 'xloc']
			ys = df.loc[:, 'yloc']

			#Creates Histogram (NxN), Xedges (N), and Yedges (N)
			Hist, xedges, yedges = np.histogram2d(xs, ys, bins = [N, binsheight],
					range = [[minfacex, maxfacex],[minfacey, maxfacey]])
			
			#transforms the Histogram so it can be graphed
			Hist = Hist.T / length_df

			return Hist, xedges, yedges


		else:
			print("facenumber = %s"%(facenumber), " is out of range")
			raise ValueError
			return

		# max face is the length of the side
		maxfacex = np.linalg.norm(base_vector)
		minfacex = 0

		# height of LPF
		maxfacez = self.H
		minfacez = 0

		# unit version of base vector
		unit_BV = base_vector / np.linalg.norm(base_vector)

		# find bins in each direction
		bins_x = int(np.linalg.norm(base_vector) * ndensity)
		bins_z = int(self.H * ndensity)  


		#Creates Histogram in Easy (X,Z) reference frame
		Hist, xedges, zedges = np.histogram2d(df['xloc'], df['zloc'], bins = [bins_x, bins_z],
			range = [[minfacex, maxfacex], [minfacez, maxfacez]])

		Hist = Hist.T / length_df
		
		return Hist, xedges, zedges

	def makeSidePatch(self, ax, Hist, xedges, yedges, zedges, facenumber, 
						norm, cmap = colormap.parula):
		alpha = 1 
		ec = 'white'
		lw = .02 
		

		for t in range(len(zedges) - 1):
			for i in range(len(xedges) - 1):

				# shift back to original position
				x1 = xedges[i] 
				x2 = xedges[i + 1]
				
				y1 = yedges[i] 
				y2 = yedges[i + 1]

				verts = [((x1, y1, zedges[t]),
					(x2, y2, zedges[t]),
					(x2, y2, zedges[t + 1]),
					(x1, y1, zedges[t + 1]))]
				ax.add_collection3d(Poly3DCollection(verts, 
					alpha = alpha, edgecolor = ec, linewidth = lw, 
					facecolor = cmap(norm(Hist[t, i]))))

		return

	def makeTopPatch(self, ax, df, facenumber, N, length_df, 
			norm, cmap = colormap.parula):
		alpha = 1 
		ec = 'white'
		lw = .02 


		if facenumber == 8:
			z = 0   # Zposition            
		elif facenumber == 9:
			z = self.H
		#to Shift graphing Position, Must shift everything

		Ltotal = self.xsc[5] - self.xsc[0]                   
		Wtotal = self.ysc[2] - self.ysc[7]

		# Bins / Unit Length
		ndensity = N / Ltotal
		binsheight = int(Wtotal * ndensity)  
		

		minfacex = self.xsc[0]
		maxfacex = self.xsc[5]

		minfacey = self.ysc[7]
		maxfacey = self.ysc[2]
		
		#input data
		xs = df.loc[:, 'xloc']
		ys = df.loc[:, 'yloc']

		#Creates Histogram (NxN), Xedges (N), and Yedges (N)
		Hist, xedges, yedges = np.histogram2d(xs, ys, bins = [N, binsheight],
				range = [[minfacex, maxfacex],[minfacey, maxfacey]])
		
		#transforms the Histogram so it can be graphed
		Hist = Hist.T / length_df

		# finds slopes of the outside lines
		mtright, btright = self.findmb(self.xsc[3], self.ysc[3], self.xsc[4], self.ysc[4])
		mbright, bbright = self.findmb(self.xsc[6], self.ysc[6], self.xsc[5], self.ysc[5])
		mbleft, bbleft = self.findmb(self.xsc[0], self.ysc[0], self.xsc[7], self.ysc[7])
		mtleft, btleft = self.findmb(self.xsc[1], self.ysc[1], self.xsc[2], self.ysc[2])

		for t in range(len(yedges)-1):
			for i in range(len(xedges)-1):
				verts = [((xedges[i], yedges[t], z),
					(xedges[i + 1], yedges[t], z),
					(xedges[i + 1], yedges[t + 1], z),
					(xedges[i], yedges[t + 1], z))]

				# check left
				if (xedges[i + 1] > self.xsc[3]):
					if (mtright * xedges[i] + btright < yedges[t]):
						continue
					elif (mbright * xedges[i] + bbright > yedges[t + 1]):
						continue
				# check right
				elif (xedges[i + 1] < self.xsc[2]):
					if (mbleft * xedges[i + 1] + bbleft > yedges[t + 1]):
						continue
					elif(mtleft * xedges[i + 1] + btleft < yedges[t]):
						continue

				ax.add_collection3d(Poly3DCollection(verts, 
					alpha = alpha, edgecolor  = ec, linewidth = lw, 
					facecolor = cmap(norm(Hist[t,i]))))
		return

	### Makes the 3D LPF ###
	def make3DLPF(self, N = 50, scale = 'log', GRS_num = None, cmap = colormap.parula, return_ax = False):
		dictionary = self.data
		"""
		Creates a 3D version of the LPF, 2D histogram on each face indicating where 
		the impact was
		Input:
			dictionary = data instance defined in MicroTools
		
		Arguments:
			N = integer defining how many bins histogram uses, 
				the greater N is, the longer it will take to run
				default = 50

			scale = string, defines how colormap is normalized, 
				either 'log' or 'lin'
				default = 'log'

			cmap = matplotlib colormap instance,
				default is parula from colormap.py
		returns: 
		3D figure instance
		"""

		# initalize colors
		my_cmap = matplotlib.cm.get_cmap(cmap) #copy.copy(matplotlib.cm.get_cmap(cmap))
		my_cmap.set_bad(my_cmap(0))
		
		if scale == 'log':
			from matplotlib.colors import LogNorm
			norm = LogNorm(vmin = 1e-3, vmax = 1)
		else:
			norm = matplotlib.colors.Normalize(0, 1)

		# converts dictionary to pandas Dataframe
		df = self.dictionaryToDataFrame(dictionary)

		# initialize figure
		fig3D = plt.figure(figsize = (6, 6))

		# add subplot with equal axes
		ax3d = fig3D.add_subplot(1,1,1, projection = '3d')
		ax3d.set_axis_off()
		ax3d.set_xlim(-1, 1)
		ax3d.set_ylim(-1, 1)
		ax3d.set_zlim(-1, 1)
		ax3d.set_aspect('equal')


		for f in np.arange(0, 10):
			#Gets only values on one face
			df_new = self.dataFrameOnlyFace(df, f)
			
			#vertical sides
			if f < 8:
				# Translated
				df_new = self.translate_to_origin(df_new, f)

				# Rotated
				df_new, theta = self.rotate_at_origin(df_new, f)

				# makes historgram
				Hist, xedges, zedges = self.hist(df_new, f, N, length_df = len(df.index) / N)

				# rotates histogram edges (creates y edges)
				xedges, yedges = self.rotate_at_origin(xedges, f, back = True)

				# translates histogram edges
				xedges, yedges = self.translate_from_origin(xedges, yedges, f)
				self.makeSidePatch(ax3d, Hist, xedges, yedges, zedges, f, norm, cmap = my_cmap)

			else:
				# makes top and bottom patches
				self.makeTopPatch(ax3d, df_new, f, N, 
						length_df = len(df.index) / N, norm = norm, cmap = my_cmap)
		if return_ax:
			return ax3d, fig3D
		else:
			return fig3D

	# ---------------------------------------#
	#          3D LPF GIF Functions          #
	# ---------------------------------------#
	def fillGifDir(self, segmentPlotDir, 
					N = 50, scale = 'log', cmap = colormap.parula):

		GRS_num = '%i'%(self.grs)
		ax, fig = self.make3DLPF(N = N, scale = scale, GRS_num = GRS_num, 
				cmap = colormap.parula, return_ax = True)

		dirnametop = segmentPlotDir + '/gif_top_GRS%s_%s'%(GRS_num, scale)
		dirnamebot = segmentPlotDir + '/gif_bot_GRS%s_%s'%(GRS_num, scale)

		if not os.path.exists(dirnamebot):
			os.mkdir(dirnamebot)
		if not os.path.exists(dirnametop):
			os.mkdir(dirnametop)
		
		step = 15 
		ax.set_title('3D LISA Pathfinder %s Scale GRS%s'%(scale, GRS_num))

		for ii in np.arange(0, 360, step):
			print('gif bottom angle = %s'%(ii))
			ax.view_init(elev = -15, azim = ii)
			fig.savefig(dirnamebot + "/bot_%i.png"%(ii))

		ax.set_title('3D LISA Pathfinder %s Scale GRS%s'%(scale, GRS_num))
		for ii in np.arange(0,360 + step, step):
			print('gif top  angle = %s'%(ii))
			ax.view_init(elev = 15, azim = ii)
			fig.savefig(dirnametop + "/top_%i.png"%(ii))
		plt.close(fig)



	def tryint(self, s):
		try:
			return int(s)
		except:
			return s

	def alphanum_key(self, s):
		""" Turn a string into a list of string and number chunks.
			"z23a" -> ["z", 23, "a"]
		"""
		return [ self.tryint(c) for c in re.split('([0-9]+)', s) ]

	def get_the_subdir(self, a_dir):
		subdir = []
		names  = []
		#print('directory = %s'%(a_dir))
		for name in os.listdir(a_dir):
			#print('name of directory = %s'%(name))
			if os.path.isdir((os.path.join(a_dir,name))):
				names.append(name)
				subdir.append((os.path.join(a_dir, name)))
		return subdir#, names


	def gif_maker(self, plotDir):
		GRS_num = '%i'%(self.grs)
		gif_dirs = self.get_the_subdir(plotDir)

		print(gif_dirs)
		for gif_dir in gif_dirs:
			#make sure subdirectories are correct gif images
			if (not 'top' in gif_dir) and (not 'bot' in gif_dir):
				print("here")
				continue
			filenames = [fil for fil in listdir('%s'%(gif_dir)) if isfile(join('%s'%(gif_dir),fil))]
			images = []
			filenames.sort(key = self.alphanum_key)
			for filename in filenames:	
				images.append(imageio.imread(gif_dir + '/' + filename))
			if 'GRS%s'%GRS_num in gif_dir:
				if 'top' in gif_dir:
					imageio.mimsave(plotDir + '/' + 'GRS%s_top.gif'%(GRS_num), images)
				else:
					imageio.mimsave(plotDir + '/' + 'GRS%s_bot.gif'%(GRS_num), images)
			else:
				continue


	def makePatch(self, ax, facenumber):
		"""
		gets vertices for a rectangular patch

		"""
		# fixes indexing problem, xsc[8] = xsc[0]
		if (facenumber == 7):
			base_vector = [self.xsc[0] - self.xsc[facenumber], 
						  self.ysc[0] - self.ysc[facenumber]]
		elif (facenumber < 7):
			base_vector = [self.xsc[facenumber + 1] - self.xsc[facenumber], 
						  self.ysc[facenumber + 1] - self.ysc[facenumber]]
		elif facenumber > 9:
			print("facenumber = %s"%(facenumber), " is out of range")
			raise ValueError
			return

		if facenumber < 8:
			base_vector = np.asarray(base_vector) 
			unit_base = np.asarray(base_vector) / np.linalg.norm(base_vector)
			side_vector = np.asarray([-1 * unit_base[1], unit_base[0]]) * self.H
			vertex1 = [self.xsc[facenumber], self.ysc[facenumber]]
			vertex2 = vertex1 + base_vector
			vertex3 = vertex2 + side_vector
			vertex4 = vertex3 - base_vector
			
			verts = [vertex1, vertex2, vertex3, vertex4]
		else:
			if facenumber == 9:
				y_push = self.ysc[2] - self.ysc[7] + self.H
			else:
				y_push = 0

			#Creates the Octogon Patch 
			verts = []
			for i in range(len(self.xsc)):
				verts.append([self.xsc[i], self.ysc[i] + y_push])


		
		path = Path(verts)
		patch = patches.PathPatch(path, facecolor = self.sidecolor, lw = 2, alpha = self.alpha)
		ax.add_patch(patch)
		return ax, patch



	def makeFlatLPF(self, N = 50, scale = 'log', cmap = colormap.parula, return_ax = False, dictionary = None):
		if dictionary is None:
			dictionary = self.data
		"""
		Creates a Flattened version of the LPF, 2D histogram on each face indicating where 
		the impact was
		Arguments:
			N = integer defining how many bins histogram uses, 
				the greater N is, the longer it will take to run
				default = 50

			scale = string, defines how colormap is normalized, 
				either 'log' or 'lin'
				default = 'log'

			cmap = matplotlib colormap instance,
				default is parula from colormap.py
		returns: 
			fig
		"""
		self.alpha = 0
		self.sidecolor = '#FF8C00' #orange
		self.colortop = 'navy'     #navy

		# initalize colors
		my_cmap = matplotlib.cm.get_cmap(cmap)
		my_cmap.set_bad(my_cmap(0))
		
		if scale == 'log':
			from matplotlib.colors import LogNorm
			norm = LogNorm(vmin = 1e-3, vmax = 1)
		else:
			norm = matplotlib.colors.Normalize(0, 1)

		# converts dictionary to pandas Dataframe
		df = self.dictionaryToDataFrame(dictionary)

		#Parameterizing Visuals
		fig = plt.figure(figsize = (10,10))              #size of figure
		ax = fig.add_subplot(1,1,1, aspect = 'equal')    #add subplot with equal axes
		ax.set_xlim(-2, 2)                                #xlim
		ax.set_ylim(-2, 4)                                #ylim
		ax.get_xaxis().set_visible(False)
		ax.get_yaxis().set_visible(False)


		for f in np.arange(0, 10):
			#Gets only values on one face
			df_new = self.dataFrameOnlyFace(df, f)
			
			#vertical sides
			if f < 8:
				# Translated
				df_new = self.translate_to_origin(df_new, f)

				# Rotated
				df_new, theta = self.rotate_at_origin(df_new, f)

				# makes historgram
				Hist, xedges, zedges = self.hist(df_new, f, N, length_df = len(df.index) / N)

				# Rotates flat
				yedges = zedges

				# Re-rotates
				xedges, yedges = self.rotate_at_origin(xedges, f, y_old = yedges, back = True)
				
				# Translates
				xedges, yedges = self.translate_from_origin(xedges, yedges, f)

			else:
				Hist, xedges, yedges = self.hist(df_new, f, N, length_df = len(df.index) / N)
				if f == 9:
					for i in range(len(yedges)):
						yedges[i] += self.ysc[2] - self.ysc[7] + self.H
					Hist = np.flipud(Hist)

			ax, patch = self.makePatch(ax, f)
			ax.pcolormesh(xedges, yedges, Hist,
				norm = norm, cmap = my_cmap,
				clip_path = patch, clip_on = True)

			ax.set_title("Impact Location GRS%i"%(self.grs))

		if return_ax:
			return fig, ax
		return fig


class impactClassList(list):
	"""
	A Class for dealing with a list of impact Class instances
	"""

	def __init__(self, grs = 1, getValid = True, BASE_DIR = None):
		"""
		Assumes we are running program from Analysis/scripts

		BASE_DIR = Directory where /Analysis is
		"""
		# Sets up directory structure
		if BASE_DIR is None:
			p = pathlib.PurePath(os.getcwd())
			self.BASE_DIR = str(p.parent)
		else:
			self.BASE_DIR = pathlib.PurePath(BASE_DIR)

		self.dataPath = pathlib.Path(self.BASE_DIR + '/data')
		
		pickles = list(self.dataPath.glob('*_grs1.pickle'))
		print("Reading through pickle files")

		impact_list = []

		for p in pickles:
			# identify segment
			segment = str(p.stem[0:10])
			chainFile = self.BASE_DIR + '/data/' + str(segment) +'_grs%i'%grs + '.pickle'

			impact = impactClass(chainFile)
			impact = impact.SCtoSun()
			impact = impact.SuntoMicro()
			impact = impact.findSkyAngles()
			if getValid:
				if impact.isValid:
					impact_list.append(impact)
					self.impact_list = impact_list
				else:
					continue
			else:
				impact_list.append(impact)

		impact_list.sort(key=operator.attrgetter('gps'))

		self.impact_list = impact_list

	def summaryTable(self, keys = ['Ptot','lat','lon','rx','ry','rz']):
		tableStr = r"""
		\begingroup
		\renewcommand\arraystretch{2}
		\begin{longtable}{|c|c|c|c|c|c|c|c|c|}
			\multicolumn{9}{c}
			{{\bfseries \tablename\  \thetable{}}}\\
			\hline \multicolumn{1}{|c}{\textbf{Date}} & 
			\multicolumn{1}{|c|}{\textbf{GPS}}  & 
			\multicolumn{1}{|c|}{\bf{$\rho_{med}$ [$\mu Ns$]}} & 
			\multicolumn{1}{|c|}{\textbf{Face}} &
			\multicolumn{1}{|c|}{\textbf{Sky Area}} &
			\multicolumn{1}{|c|}{\textbf{$Lat_{SC}$}} &
			\multicolumn{1}{|c|}{\textbf{$Lon_{SC}$}} &
			\multicolumn{1}{|c|}{\textbf{$Lat_{sun}$}} &
			\multicolumn{1}{|c|}{\textbf{$Lon_{sun}$}} \\
			\hline
		\endfirsthead
		
		\multicolumn{9}{c}
			{{\bfseries \tablename\  \thetable{} -- continued from previous page}} \\
		\hline \multicolumn{1}{|c|}{\textbf{Date}} & 
			\multicolumn{1}{|c|}{\textbf{GPS}}  & 
			\multicolumn{1}{|c|}{\bf{$\rho_{med}$ [$\mu Ns$]}} & 
			\multicolumn{1}{|c|}{\textbf{Face}} &
			\multicolumn{1}{|c|}{\textbf{Sky Area}} &
			\multicolumn{1}{|c|}{\textbf{$Lat_{SC}$}} &
			\multicolumn{1}{|c|}{\textbf{$Lon_{SC}$}} &
			\multicolumn{1}{|c|}{\textbf{$Lat_{sun}$}} &
			\multicolumn{1}{|c|}{\textbf{$Lon_{sun}$}} \\
			\hline
		\endhead
		
		\hline \multicolumn{9}{|r|}{{Continued on next page}} \\ \hline
		\endfoot

		\hline
		\endlastfoot""" + '\n'
				
		for impact in self.impact_list:
			tableStr += '\t' + impact.summaryString() + '\n'
		
		
		tableStr += '\t' + r'\hline' + '\n'
		
		tableStr += '\end{longtable} \n'
		tableStr += '\endgroup'
		
		return tableStr

	def fitPowerlaw(self, sortlist, param = 'Ptot', sigma = None):

		# Make momentum array
		xdata = np.asarray([i.getMedian(param) for i in sortlist])
		ydata = np.arange(1, len(sortlist) + 1, 1.0)[::-1]

		if sigma is not None:
			popt, pcov = curve_fit(self.lin_func, np.log(xdata), np.log(ydata), 
					p0 = (1, 1), sigma = sigma)
		else:
			popt, pcov = curve_fit(self.lin_func, np.log(xdata), np.log(ydata), p0 = (1, 1))

		# Undo logarithmic fit
		# y = a * x ** b
		# log(y) = log(a) + b * log(x)
		# Linear : y = mx + c
		# slope = b = m
		# offset = log(a) = c
		b = popt[0]
		a = np.exp(popt[1])

		return [a, b], pcov


	def credible_interval(self, impact, key, credible = 0.90, getMedian = False):

		data = impact.getParam(key) #self.impact_list.sort(key=operator.attrgetter(key))

		#First sorts data in order
		data = np.sort(data, axis = None)
		N = len(data)
		
		n_median = int(N / 2.0)
		median = data[n_median]
		
		#percentage up down
		conup   = (credible + ((1 - credible) / 2.0)) 
		condown =((1 - credible) / 2.0)      
		
		#index value of credible up, down
		nup = int(N * conup)          
		ndown = int(N * condown)  

		credible_up = data[nup]
		credible_down = data[ndown]
		if getMedian:
			return credible_up, credible_down, median
		else:
			return credible_up, credible_down



	def getCredibleIntervals(self, sortlist, param, credible = 0.9, getMedian = True):
		cred_up = np.zeros(len(sortlist))
		cred_down = np.zeros(len(sortlist))
		stdev = np.zeros(len(sortlist))
		median_list = np.zeros(len(sortlist))
		for i in range(len(sortlist)):
			c_up, c_down, median = self.credible_interval(sortlist[i],
												 key = param,
												 credible = credible,
												 getMedian = True)
			cred_up[i] = c_up
			cred_down[i] = c_down
			stdev[i] = np.std(sortlist[i].getParam(param))
			median_list[i] = median

		if getMedian:
			return cred_up, cred_down, stdev, median_list
		return cred_up, cred_down, stdev


	def power_func(self, x, a, b):
		return a * (x ** b) 

	def lin_func(self, x, m, b):
		return m * x + b


	# ---------------------------------------#
	#          Plotting Functions            #
	# ---------------------------------------#
	def plotMomSkyArea(self, credible = 0.9):
		fit_color = "#ffd27a"#92cac6"
		error_color = "#e86e66"
		data_color = "#6b9bb9"
		fig, ax = plt.subplots(figsize = (10, 10))
		
		sortlist = sorted(self.impact_list, key=lambda x: x.getMedian('Ptot'))
		xdata = np.asarray([i.getMedian('Ptot') for i in sortlist]) 
		ydata = np.asarray([i.skyArea for i in sortlist])

		# Get Credible Intervals and stdev
		cred_up, cred_down, stdev, median = self.getCredibleIntervals(sortlist, 'Ptot', credible, getMedian = True)

		# Credible Intervals
		ax.errorbar(xdata, ydata, xerr = [median - cred_down, cred_up - median],
					 fmt = 'o', color = error_color, label = '%i%% Credible'%(credible * 100))

		ax.set_title("Momentum vs Sky Area")
		ax.set_ylabel("Sky Area $Degrees^2$")
		ax.set_xlabel("Momentum $\mu Ns$")
		ax.set_yscale('log')
		ax.set_xscale('log')
		ax.legend()
		return fig

	def plotPowerLaw(self, param = 'Ptot', credible = 0.9, weight = True, show_credible = True):
		fit_color = "#ffd27a"#92cac6"
		error_color = "#e86e66"
		data_color = "#6b9bb9"
		import matplotlib as mpl
		mpl.rcParams['lines.linewidth'] = 3

		# Sort data
		sortlist = sorted(self.impact_list, key=lambda x: x.getMedian(param))

		xdata = np.asarray([i.getMedian(param) for i in sortlist]) #makeArray(sortlist, param, np.median))
		ydata = np.arange(1, len(sortlist) + 1, 1.0)[::-1]

		# Get Credible Intervals and stdev
		cred_up, cred_down, stdev, median = self.getCredibleIntervals(sortlist, param, credible, getMedian = True)

		#Get power Law fit
		if weight:
			popt, pcov = self.fitPowerlaw(sortlist, param, sigma = 1 / (cred_up - cred_down))
		else:
			popt, pcov = self.fitPowerlaw(sortlist, param, sigma = None)

		print('Optimized: a = ', popt[0], 'b =', popt[1] )

		# Get credible intervals

		fig, ax = plt.subplots(figsize = (10,10))

		y = np.exp(self.lin_func(np.log(xdata), *popt))

		# Plot the data
		ax.scatter(xdata, ydata, color = data_color, zorder = 10, label = 'Median Momentum')

		ax.plot(xdata, self.power_func(xdata, *popt),
				color = fit_color,
				linestyle = ':',
				label = r'%1.3e$(\frac{P}{[\mu N s]})^{%1.3e}$'%(popt[0], popt[1]))


		# Credible Intervals
		if show_credible:
			ax.errorbar(xdata, ydata, xerr = [median - cred_down, cred_up - median],
						 fmt = 'o', color = error_color, label = '%i%% Credible'%(credible * 100))
			"""
			ax.plot(cred_up, ydata, color = 'hotpink', zorder = 2)
			ax.plot(cred_down, ydata, color = 'hotpink', zorder = 3)
			ax.fill_betweenx(ydata, cred_up, cred_down,
							 where = cred_up >= cred_down,
							 facecolor='pink',
							 zorder = 1,
							 label = '%i%% Credible'%(100 * credible))
			"""
		else:
			ax.errorbar(xdata, ydata, xerr = stdev,
					fmt = '', color = error_color,  label = '1 Stdev')


		ax.set_xscale('log')
		ax.set_ylabel('rank')
		if param == 'Ptot':
			ax.set_xlabel('$p_{tot}\,[\mu N s]$')
		else:
			ax.set_xlabel(param)


		ax.legend()

		return fig



	


	








		








				


