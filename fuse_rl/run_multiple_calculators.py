from ase import *
from ase.io import *
from ase.calculators.vasp import Vasp
from .gulp import *
from ase.calculators.gulp import GULP
import platform
import re
import os
import math
import sys
from .run_gulp import *
from .run_vasp import *
from .run_qe import *
import glob

################################################################################################
import shlex
import re
import numpy
from numpy import arccos, pi, dot
from numpy.linalg import norm

#def cellpar(atoms):
#	cell = atoms.cell
#	a = norm(cell[0])
#	b = norm(cell[1])
#	c = norm(cell[2])
#	alpha = arccos(dot(cell[1], cell[2])/(b*c))*180./pi
#	beta  = arccos(dot(cell[0], cell[2])/(a*c))*180./pi
#	gamma = arccos(dot(cell[0], cell[1])/(a*b))*180./pi
#
#	cell = []
#	cell=[a,b,c,alpha,beta,gamma]
#	return cell
################################################################################################

def run_calculators(atoms='',vasp_opts='',kcut='',produce_steps='',
	shel=None,kwds='',gulp_opts='',lib='',calcs='',dist_cutoff='',qe_opts='',
	gulp_command='gulp < gulp.gin > gulp.got'):
	converged = None
	energy=0
	for x in range(len(calcs)):
		short_contact = False
		
		temp_atoms=atoms.repeat([2,2,2])
		temp1=temp_atoms.get_all_distances()
		temp2=[]
		for i in range(len(temp1)):
			for j in range(len(temp1[i])):
				if temp1[i][j] != 0:
					temp2.append(temp1[i][j])
		distances=min(temp2)
		if distances <= dist_cutoff:
			short_contact = True
		
		if short_contact == False:
			if energy < 10.:
				if calcs[x] == 'gulp':
					atoms, energy, converged = run_gulp(atoms=atoms,shel=shel,kwds=kwds,opts=gulp_opts,lib=lib,produce_steps=produce_steps,gulp_command=gulp_command)
			
				elif calcs[x] == 'vasp':
					atoms,energy,converged=run_vasp(atoms=atoms,vasp_opts=vasp_opts,kcut=kcut,produce_steps=produce_steps,dist_cutoff=dist_cutoff)
	
				elif calcs[x] == 'qe':
					atoms,energy,converged=run_qe(atoms=atoms,qe_opts=qe_opts,kcut=kcut,produce_steps=produce_steps)
	
	try:
		if glob.glob("gulptmp*") != []:
			if platform.system() == 'Windows':
				files=glob.glob("gulptmp*")
				for z in range(len(files)):
					os.remove(files[z])
			if platform.system() == 'Linux':
				os.system("rm gulptmp*")
	except:
		pass

	
	return atoms,energy,converged
