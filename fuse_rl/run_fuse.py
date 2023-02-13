import datetime
import time
import numpy
import sys
from ase import *
from .create_random_string import *
from .error_check_structure import *
from .assemble_structure import *
from .create_random_instructions import *
from .possible_solutions import *
from .run_gulp import *
from .run_vasp import *
from .run_qe import *
from .compute_amd import *
from ase.visualize import *
import warnings
from decimal import *
import os
import platform
import glob
from .get_distances import *
import math
from .make_basin_move import *
from .make_ga_move import *
import random
from .create_ml_model import *
#import spglib
import shutil
from .plot_results import plot_graph
from .check_prev_structure import *
from ase.build import sort
from .run_multiple_calculators import run_calculators
from rlcsp import Reinforce
from rlcsp import State
from shutil import copyfile

#-------------------------------------------------------------------------------
#Known issues / to do list:
# - Currently the neutral input formula type does not work with the GA, by the looks
# of it, I never built the function for it! Need to mimic how it is done for ionic
# for neutral (removing the parts which split the structures into anions and cations
#
#
#-------------------------------------------------------------------------------

warnings.filterwarnings("ignore") # currently use this as python raises RuntimeError
# warnings when a physically unreasonable unit cell is generated, this is caught
# and structures rejected by the "converged" variable, so the warnings aren't really
# needed. Comment this out for debugging.

t1=datetime.datetime.now()

print("################################################################################")
print("#									      #")
print("#		       Flexible Unit Structure Engine			      #")
print("#				 (FUSE+RLCSP)					      #")
print("#				 v1.05					      #")
print("#									      #")
print("################################################################################")
print("\n\n")


backup_files = ['start_points.p',
				"initial_structures.p",
				"ini_energies.p",
				"r.p",
				"ca.p",
				'cubes.p',
				"T.p",
				"graph_output.csv",
				"sa.p",
				"search.p",
				"amds.p",
				"amd_matches.p",
				"search_structures.p",
				"moves.p",
				"generation_moves.p",
				"energies.p",
				"current_structure.p",
				"current_structure.cif",
				"generation_complete.p",
				"generation.p",
				"generation_energies.p",
				"search_structures.p",
				'log_file.csv',
				'accepted_energies.txt',
				"spacegroups.csv",
				'bondtable.npz',
				'hexagonal.p',
				'tetragonal.p',
				'lowest_energy_structure.cif',
				'monoclinic.p',
				'orthorhombic.p',
				'output.txt',
				'run_output.png',
				'run.txt']

backup_dir = 'backup'

def save_backup_files():
	if not os.path.isdir(backup_dir):
		os.mkdir(backup_dir)

	for f in backup_files:
		try:
			if os.path.exists(f):
				copyfile(f, f'{backup_dir}/{f}')
		except FileNotFoundError:
			print(f'FileNotFoundError: Failed to save {backup_dir}/{f}')

def restore_backup_files():
	if os.path.isdir(backup_dir):
		for f in backup_files:
			try:
				if os.path.exists(f'{backup_dir}/{f}'):
					copyfile(f'{backup_dir}/{f}', f)
			except FileNotFoundError:
				print(f'FileNotFoundError: Failed to save {f}')



def run_fuse(composition='',search='',initial_gen='',max_atoms='',vac_ratio=4,ap_scale=1.0,
	 max_ax=40,restart=False,ctype='',kwds='',gulp_opts='',lib='',shel='',vasp_opts='',
	 kcut=30,serial=True,write_all_structures=False,ratt_dist=0.05,density_cutoff=0.4,
	 check_bonds=True,btol=0.25,check_distances=True,dist_cutoff=1.2,iterations=0,
	 search_gen=1,n_moves={1:18,2:5,3:3,4:3,5:3,6:2,7:1,8:1},r_moves={3:1,4:1,5:1,6:2,7:3,8:3},rmax='',T=0.02,ratio=[4,1],
	 imax_atoms='',compute_space_groups=False,pool_size=0.1,max_pool_size=2500,produce_steps=False,melt_threshold=500,
	 write_graph=False,swap_searches=False,swap_threshold=500,check_previous=False,
	 new_structure_attempts=5000,calcs='',qe_opts='',swap_back='',use_amds=False,
	 amd_rep=[2,2,2],amd_k=10,gulp_command='gulp < gulp.gin > gulp.got',record_data_log=True,
	 invert_charge=False,
	 params_db={},
	 alpha=0.01,
	 reinforce_table='reinforce',
	 theta_table='theta',
	 reinforce_id=0,
	 reg_params={'e_threshold': 0, 'beta': 0},
	 reward_type=Reinforce.change_in_features,
     reinforce_debug=False,
	 target_energy=0,
	 write_graph_end=True
	 ):

	new_structure = None
	gulp_time = 0
	fuse_time = 0
	reinforce_select_time = 0
	reinforce_update_time = 0
	start_t = time.time()

	### run possible solutions to get library of unit cell dimensions in sub-modules
	cubic_solutions,tetragonal_solutions,hexagonal_solutions,orthorhombic_solutions,monoclinic_solutions=possible_solutions(max_ax,restart)
	#############################################################################

	### try to read in restart_files ############################################
	T_0=T
	success = False
	is_backup = False
	while restart == True and not success:
		try:
			if check_previous == True:
				prev_start_points = pickle.load(open(f"start_points.p", 'rb'))
			initial_population = pickle.load(open(f"initial_structures.p", 'rb'))
			ini_energies = pickle.load(open(f"ini_energies.p", 'rb'))
			r = pickle.load(open(f"r.p", 'rb'))
			ca = pickle.load(open(f"ca.p", 'rb'))
			if ca >= melt_threshold:
				T = pickle.load(open(f"T.p", 'rb'))
			# if write_graph == True:
			temp = pandas.read_csv(f"graph_output.csv")
			graph = temp.to_dict(orient='list')
			if 'file_name' in graph:
				del graph['file_name']
			if swap_searches == True:
				sa = pickle.load(open(f"sa.p", 'rb'))

			search = pickle.load(open(f"search.p", 'rb'))
			if use_amds == True:
				amds = pickle.load(open(f"amds.p", 'rb'))
				amd_matches = pickle.load(open(f"amd_matches.p", 'rb'))
		except:
			restart = False

		#When constructed, will also need to be able to read in results from a search
		#routine
		try:
			search_structures=pickle.load(open("search_structures.p",'rb'))
		except:
			pass #put pass in, as search may not yet have begun, so search structures
		#may not yet exist!

		try:
			moves=pickle.load(open("moves.p",'rb'))
		except:
			pass #put pass in, as search may not yet have begun, so search structures
		#may not yet exist!

		try:
			generation_moves=pickle.load(open("generation_moves.p",'rb'))
		except:
			generation_moves=[]

		try:
			ini_energies = []
			energies=pickle.load(open("energies.p",'rb'))
			ini_energies=pickle.load(open("ini_energies.p",'rb'))
		except:
			restart = False

		if len(ini_energies) >= initial_gen:
			initial_complete=1
		else:
			initial_complete=0
			ncalc=len(ini_energies)

		if initial_complete==1:
			try:
				current_structure=pickle.load(open("current_structure.p",'rb'))
			except:
				restart=False

		try:
			generation_complete=pickle.load(open("generation_complete.p",'rb'))
			if generation_complete == False:
				generation = pickle.load(open("generation.p", 'rb'))
				generation_energies = pickle.load(open("generation_energies.p", 'rb'))
		except:
			restart=False

		if initial_complete==1:
			try:
				search_structures=pickle.load(open("search_structures.p",'rb'))
				count=len(list(search_structures.keys()))
			except:
				restart=False

		if restart:
			success = True
			if is_backup:
				print("Backup restart files read... ")
			else:
				print("Restart files read... ")
		else:
			# if we failed with restart files we try to load the backup
			if not is_backup:
				print("Error in reading restart files, try backup")
				is_backup = True
				restart = True
				restore_backup_files()
			else:
				print("Error in reading restart files, starting fresh calculation")
	#############################################################################

	sys.stdout.flush()

	### startup bits ############################################################
	if restart == False:
		prev_start_points=[]
		ini_energies=[]
		energies=[]
		generation_complete=True
		r=0
		ca=0
		sa=0
		# if write_graph==True:
		graph={}
		T_0=T
		if use_amds==True:
			amds=[]
			amd_matches=0
	itr = 0 # number of structures computed in current run of code

	moves = n_moves

	if produce_steps==True:
		if not os.path.isdir("steps"):
			os.mkdir("steps")
		if restart==False:
			if platform.system() == 'Windows':
				os.chdir("steps")
				files=glob.glob("*.cif")
				for z in range(len(files)):
					os.remove(files[z])
				os.chdir("../")
			if platform.system() == 'Linux':
				try:
					os.system("rm steps/*")
				except:
					pass

	#############################################################################

	#### create output files/folders to write to ################################
	if restart == False:
		o=open("output.txt",'w')
	if restart == True:
		o=open("output.txt",'a')

	if compute_space_groups == True:
		#### PS EDIT
		# Open csv file for spacegroups here
		spg=open("spacegroups.csv",'a')
		#### PS EDIT

	if write_all_structures == True:
		if not os.path.isdir("structures"):
			os.mkdir("structures")
		os.chdir("structures")

		if restart == False:
			if glob.glob("*.cif") != []:
				if platform.system()=='Windows':
					os.system("del *.cif")
				if platform.system()=='Linux':
					os.system("rm *.cif")
		os.chdir("../")

	o.write("################################################################################")
	o.write("\n#										 #")
	o.write("\n#			   Flexible Unit Structure Engine			 #")
	o.write("\n#				     (FUSE +CSP)				 #")
	o.write("\n#				     v1.04					 #")
	o.write("\n#										 #")
	o.write("\n################################################################################")
	o.write("\n\n")

	### write to output file if restarts have been read #########################
	if restart == True:
		o.write("\nrestart files read... ")
	#############################################################################

	#############################################################################

	#### Print out the composition from the input file ##########################
	keys=list(composition.keys())
	string=""
	for i in range(len(keys)):
		string+=keys[i]
		if len(composition[keys[0]])==1:
			if composition[keys[i]][0] != 1:
				string+=str(composition[keys[i]][0])

		if len(composition[keys[0]])==2:
			if composition[keys[i]][0] != 1:
				string+=str(composition[keys[i]][0])
	#############################################################################

	####compute maximum number of formula units allowed##########################
	### work out how many atoms per formular unit ###############################
	atoms_per_fu = 0
	for i in range(len(keys)):
		atoms_per_fu += composition[keys[i]][0]


	max_fus=int(max_atoms/atoms_per_fu)
	imax_fus=int(imax_atoms/atoms_per_fu)
	if max_fus == 0:
		print ("ERROR: maximum number of Fus equals 0!, please increase maximum number of atoms in input!")
		sys.exit()

	if imax_fus == 0:
		imax_fus=1

	print ("Input formula = "+string+"\nMaximum number of formula units = "+str(max_fus))
	o.write("\nInput formula = "+string+"\nMaximum number of formula units = "+str(max_fus))
	#############################################################################

	### create a string containing the atomic numbers for 1 FU ##################
	fu=[]
	for i in range(len(keys)):
		for j in range(composition[keys[i]][0]):
			fu.append(Atoms(keys[i]).get_atomic_numbers()[0])
	#############################################################################

	#### check if the composition is presented as ionic #########################
	if len(composition[keys[0]]) != 1:
		print ("Ionic input formula")
		o.write("\nIonic input formula")
		charge=0
		system_type="ionic"
		for i in range(len(keys)):
			for j in range(composition[keys[i]][0]):
				charge += composition[keys[i]][1]

		if charge == 0:
			neutral=1

		if charge != 0:
			neutral=0

	if len(composition[keys[0]]) == 1:
		print ("Neutral input formula")
		o.write("\nNeutral input formula")
		neutral=1
		system_type="neutral"

	if neutral != 1:
		print ("Error: Non-charge neutral formular input")
		o.write("\nError: Non-charge neutral formular input")
		sys.exit()
	if neutral ==1:
		pass
	#############################################################################
	# try and load bond table depending on which type of system we're in
	if restart == True:
		try:
			bondtable=numpy.load("bondtable.npz",allow_pickle=True)
			bondtable=bondtable['bond_table'].item()
		except:
			if system_type == 'ionic':
				if invert_charge == False:
					import fuse_rl.bond_table_ionic
					bondtable=numpy.load("bondtable.npz",allow_pickle=True)
					bondtable=bondtable['bond_table'].item()

				if invert_charge == True:
					import fuse_rl.bond_table_ionic_invert
					bondtable=numpy.load("bondtable.npz",allow_pickle=True)
					bondtable=bondtable['bond_table'].item()


			if system_type == 'neutral':
				import fuse_rl.bond_table_atomic
				bondtable=numpy.load("bondtable.npz",allow_pickle=True)
				bondtable=bondtable['bond_table'].item()
	if restart == False:
		if system_type == 'ionic':
			if invert_charge == False:
				import fuse_rl.bond_table_ionic
				bondtable=numpy.load("bondtable.npz",allow_pickle=True)
				bondtable=bondtable['bond_table'].item()

			if invert_charge == True:
				import fuse_rl.bond_table_ionic_invert
				bondtable=numpy.load("bondtable.npz",allow_pickle=True)
				bondtable=bondtable['bond_table'].item()


		if system_type == 'neutral':
			import fuse_rl.bond_table_atomic
			bondtable=numpy.load("bondtable.npz",allow_pickle=True)
			bondtable=bondtable['bond_table'].item()


	#### compute the ap to be used for the sub-modules ##########################
	# convert the fu back to symbols
	symbol_fu=[]
	for i in range(len(fu)):
		temp=Atoms(numbers=[fu[i]])
		symbol_fu.append(temp.get_chemical_symbols()[0])
	# read in shannon radi table
	temp=numpy.load("bondtable.npz",allow_pickle=True)
	bond_table=temp['bond_table'].item()
	ap=0
	if system_type=="neutral":
		for i in range(len(symbol_fu)):
			average = 0
			temp=list(bond_table[symbol_fu[i]].keys())
			for j in range(len(temp)):
				average+=bond_table[symbol_fu[i]][temp[j]][-1]
			average=average/len(temp)
			ap+=average

	ap=ap/len(symbol_fu)
	ap=4*ap

	if system_type=="ionic":
		cat_ap=0
		an_ap=0
		cats=0
		anis=0
		for i in range(len(symbol_fu)):
			sym=symbol_fu[i]
			try:
				if composition[sym][-1] > 0:
					cat_ap+=bond_table[sym][composition[sym][-1]][-1]
					cats+=1
				if composition[sym][-1] < 0:
					an_ap+=bond_table[sym][composition[sym][-1]][-1]
					anis+=1

			except KeyError:
				print("***** WARNING: dectected ionic species not included in bond table, treating species as an average of it's bondtable entry *****")
				average=0
				temp=list(bond_table[symbol_fu[i]].keys())
				for j in range(len(temp)):
					average+=bond_table[symbol_fu[i]][temp[j]][-1]
				average=average/len(temp)
				ap+=average

		cat_ap = (cat_ap / cats)*2
		an_ap  = (an_ap  / anis)*2
		ap = cat_ap + an_ap

	if ap_scale != '':
		ap=ap*ap_scale
	ap = float(Decimal(ap).quantize(Decimal('1e-4')))
	print("ap calculated to be: "+str(ap)+" Angstroms")
	o.write("\nap calculated to be: "+str(ap)+" Angstroms")
	#############################################################################

	#try to work out maximum density ############################################
	# currently this won't work for neutral compounds ,especially if one or more elements
	# can present as either an anion or cation
	mass=0
	volume=0
	if system_type == 'neutral':
		for i in range(len(fu)):
			temp=Atoms(numbers=[fu[i]])
			mass+=temp.get_masses()[0]
			temp=temp.get_chemical_symbols()[0]
			temp=bondtable[temp]
			if len(list(temp.keys())) > 1:
				rs=[]
				keys=list(temp.keys())
				for j in range(len(list(temp.keys()))):
					rs.append(temp[keys[j]][-1])
				volume+=((4/3)*math.pi*(min(rs)**3))
			else:
				volume+=((4/3)*math.pi*(temp[list(temp.keys())[0]][-1]**3))
		ideal_density=mass/volume

	if system_type == 'ionic':
		for i in range(len(fu)):
			try:
				temp=Atoms(numbers=[fu[i]])
				mass+=temp.get_masses()[0]
				temp=temp.get_chemical_symbols()[0]
				sym=temp
				temp=bondtable[temp]
				chg_state=composition[sym][1]
				rs=temp[chg_state][-1]
				volume+=((4/3)*math.pi*(rs**3))
			except KeyError:
				temp=Atoms(numbers=[fu[i]])
				mass+=temp.get_masses()[0]
				temp=temp.get_chemical_symbols()[0]
				temp=bondtable[temp]
				if len(list(temp.keys())) > 1:
					rs=[]
					keys=list(temp.keys())
					for j in range(len(list(temp.keys()))):
						rs.append(temp[keys[j]][-1])
					volume+=((4/3)*math.pi*(min(rs)**3))
				else:
					volume+=((4/3)*math.pi*(temp[list(temp.keys())[0]][-1]**3))


		ideal_density=mass/volume

	#############################################################################

	#### check the search type to be used #######################################
	if swap_searches == True:
		print("Search routine: Mixed")
		o.write("\nSearch routine: Mixed")

	if swap_searches == False:
		if search == 1:
			print ("Search routine: Basin Hopping")
			o.write("\nSearch routine: Basin Hopping")
		if search == 2:
			print ("Search routine: Genetic Algorithm")
			o.write("\nSearch routine: Genetic Algorithm")
		if search == 3:
			print ("Search routine: Machine Learning")
			o.write("\nSearch routine: Machine Learning")


	#############################################################################

	#### work on generation of initial population ###############################
	if restart == False:
		r=0
		print ("\n\n############################ Generating Initial Population ############################\n\n")
		o.write("\n\n############################ Generating Initial Population ############################\n")
		initial_population={}
		built=0
		sizes={}
		x=0
		while built < initial_gen:
			try:
				#print(composition)
				string,instructions=create_random_string(cubic_solutions,tetragonal_solutions,hexagonal_solutions,orthorhombic_solutions,monoclinic_solutions,atoms_per_fu,fu,vac_ratio=vac_ratio,max_fus=imax_fus,system_type=system_type,composition=composition,ap=ap)
				### ^^^ this gives the random string required to make a structure, now
				#generate random assembly instructions
				instructions=create_random_instructions(string,ap,cubic_solutions,tetragonal_solutions,hexagonal_solutions,orthorhombic_solutions,monoclinic_solutions,instructions)
				#print(instructions)
				if instructions == None:
					continue
				#send string & instructions to the structure assembler
				#print(instructions)
				atoms,instructions=assemble_structure(string,instructions)
				#print(instructions)
				#view(atoms)
				if len(atoms) % len(fu) != 0:
					continue

				#print("hello")
				if atoms == None:
					continue

				accept=error_check_structure(atoms,ideal_density,density_cutoff,check_bonds,btol,system_type,fu,composition,bondtable,ap,check_distances,dist_cutoff,target_number_atoms=imax_atoms)

				if accept == 0:
					continue

				if len(atoms) > imax_atoms:
					continue
				if len(atoms) % len(fu) != 0:
					continue

				if use_amds == True:
						amd=compute_amd(atoms1=atoms,rep=amd_rep,k=amd_k)
						if amd in amds:
							amd_matches+=1
							continue

						if not amd in amds:
							amds.append(amd)


				if check_previous == True:
					if prev_start_points != []:
						check=check_prev_structure(atoms,prev_start_points)
						#print(check,end='\n\n')
					else:
						check = False

					if check == False:
						x=0
					if check == None:
						continue
					if check == True:
						x+=1
						if x == new_structure_attempts:
							print("Failed to generate new unique structures, will stop calculation after this generation")
							f=open("stop.txt",'w')
							f.close()
							check_previous=False
						continue


				#sys.exit()
				temp_atoms=atoms.copy()
				sort(temp_atoms)
				if check_previous==True:
					pass
					#prev_start_points.append(spglib.standardize_cell(temp_atoms,symprec=1e-5))
				#print(prev_start_points)
				atoms.rattle(ratt_dist)
				initial_population[built+1]=[atoms,string,instructions]
				print (str("built " + str(built+1) + " of " + str(initial_gen)),end="\r")
				### for debugging, just have a routine here that creates a dictionary to plot
				# the distribution of number of atoms per structure #########################
				try:
					sizes[len(atoms)]+=1
				except:
					sizes[len(atoms)]=1
				built += 1
			except:
				pass
		#view(atoms)
		#print(sizes)
		#sys.exit()
	#############################################################################

	log_filename = "log_file.csv"

	####	now go through and actually do something with the structures!! ########
	if restart == False:
		ncalc=0 # keep track of which structure from the initial population has been computed
		initial_complete = 0 # keep track of if the initialisation loop has been completed
		search_structures={}
		ini_energies=[]

		# create and save log file (for its header)
		log_file = {'step': [],
					'starting_modules': [],
					'modules': [],
					'move_type': [],
					'energy': [],
					'mc_outcome': []}

		step = 0
		out_data = pandas.DataFrame(log_file)
		out_data.to_csv(log_filename, index=False)

		if os.path.exists("accepted_energies.txt"):
			os.remove("accepted_energies.txt")

	if restart == True:
		try:
			df = pandas.read_csv(log_filename)
			step = df['step'].max()
		except pandas.errors.EmptyDataError as e:
			print(f'Error during reading {log_filename}: {e}')
			step = 0

		if initial_complete == 0:
			count=1
			print("\n\n############################ Resuming Initial Population ############################\n")
			o.write("\n\n############################ Resuming Initial Population ############################\n")

	actions = ['1', '2', '3', '4', '5', '6', '7', '9', '10']
	reinforce = Reinforce(actions=actions,
						  params_db=params_db,
						  alpha=alpha,
						  reinforce_table=reinforce_table,
						  theta_table=theta_table,
						  reward_type=reward_type,
						  features_set=['energy'],
						  episode_length=1,
						  max_energy=0,
						  reinforce_id=reinforce_id,
						  debug=reinforce_debug,
						  reg_params=reg_params)
	reinforce.step_energy_limit = 100
	old_energy = 0

	if initial_complete == 0:
		if serial == True: # run the structures one at a time
			#itr=0 # number of structures computed in this loop
			for i in range(0+(ncalc), initial_gen):
				if itr == iterations:
					break
				nstruct=len(list(initial_population.keys()))
				o.write("\n")
				atoms=initial_population[i+1][0]
				#print(initial_population[i+1])
				iat=len(atoms)
				print (str("structure " + str(i+1) +" of " + str(nstruct)),end="\r")

				if compute_space_groups == True:
					pass
					#### PS EDIT
					# Use spglib to obtain spacegroup and record in csv file
					#spg.write('%i %s\n' %(i, spglib.get_spacegroup(atoms)))
					#### PS EDIT

				if ctype == 'gulp':
					try:
						atoms,energy,converged=run_gulp(atoms=atoms,shel=shel,kwds=kwds,opts=gulp_opts,lib=lib,produce_steps=produce_steps,gulp_command=gulp_command)
					except:
						converged = False
						energy = 1.e20

				if ctype == 'vasp':
					try:
						atoms,energy,converged=run_vasp(atoms=atoms,vasp_opts=vasp_opts,kcut=kcut,produce_steps=produce_steps,dist_cutoff=dist_cutoff)
					except:
						#print('except')
						converged = False
						energy = 1.e20

				if ctype == 'qe':
					try:
						atoms,energy,converged=run_qe(atoms=atoms,qe_opts=qe_opts,kcut=kcut,produce_steps=produce_steps)
					except:
						converged=False
						energy=1.e20

				if ctype == 'mixed':

					try:
						atoms,energy,converged=run_calculators(atoms=atoms,vasp_opts=
						vasp_opts,kcut=kcut,produce_steps=produce_steps,shel=shel,
						kwds=kwds,gulp_opts=gulp_opts,lib=lib,calcs=calcs,dist_cutoff=dist_cutoff,qe_opts=qe_opts,
						gulp_command=gulp_command)

					except:
						converged = False
						energy = 1.e20

				if target_energy == -27.394619:
					print(f'Current energy is {energy}')

				if len(atoms) != iat:
					converged = False
					energy = 1.e20
				if converged != False:
					if produce_steps==True:
						targets=glob.glob("atoms*.cif")
						targets.sort()
						for z in range(len(targets)):
							label=str("steps/I"+str(i+1)+"_"+str(z+1)+str(".cif"))
							shutil.copy(targets[z],label)
				energy = energy/len(atoms)
				energy = float(Decimal(energy).quantize(Decimal('1e-6')))
				if target_energy == -27.394619:
					print(f'Current energy 1 is {energy}')

				if energy < 0:
					if old_energy == 0:
						old_energy = energy
					reinforce.update_f_scaling(State(old_energy), State(energy), '7', reinforce.alpha)
					old_energy = energy
				initial_population[i+1].append(energy)
				initial_population[i+1].append("ini")
				initial_population[i+1][0]=atoms
				#print(str("I{0:=6n}".format(i+1)+"  {0:0=6.6n}	  eV/atom".format(float(energy)).rjust(25)))
				o.write(str("I{0:=7n}".format(i+1)+"  {0:=6.6n}	  eV/atom".format(float(energy)).rjust(25)))
				if write_all_structures == True:
					try:
						write(str("structures/"+str("I-")+str('{0:0=7n}'.format(i+1)+".cif")),atoms)
					except:
						pass

				# if write_graph==True:
				#if converged != False:
				if i==0:
					graph['move']=['ini']
					graph['type']=["I"]
					graph['step']=[i+1]
					graph['energies']=[energy]
					if swap_searches==False:
						if search == 1:
							graph['temp']=[T]
					else:
							graph['temp']=[T]
					graph['current_energy'] = [0]
				else:
					try:
						graph['move'].append('ini')
						graph['type'].append("I")
						graph['step'].append(i+1)
						graph['energies'].append(energy)
						graph['current_energy'].append(0)
						if swap_searches==False:
							if search == 1:
								graph['temp'].append(T)
						else:
							graph['temp'].append(T)
					except:
						graph['move']=['ini']
						graph['type']=["I"]
						graph['step']=[i+1]
						graph['energies']=[energy]
						if swap_searches==False:
							if search == 1:
								graph['temp']=[T]
						else:
							pass
								#graph['temp']=[T]
						graph['current_energy'] = [0]

					graph_to_write=pandas.DataFrame(graph)
					graph_to_write.to_csv(path_or_buf="graph_output.csv",index=False)
					if i % 10 == 0:
						if write_graph:
							if swap_searches==False:
								plot_graph(search=search)
							else:
								plot_graph()

				ini_energies.append(energy)
				energies=[min(ini_energies)]
				if os.path.isfile("stop.txt"):
					print ("** Stopping caclulation **")
					os.remove("stop.txt")
					break
				itr+=1
				#print(initial_population[i+1])
				o.flush()
		if itr + ncalc == initial_gen:
			initial_complete = 1
			#if write_graph==True:
			#	plot_graph()
		if initial_complete == 1:
			energies=[]
			print("Initial population completed")
			o.write(str("\nInitial population completed"))
			print(str("lowest energy initial structure: " + str(ini_energies.index(min(ini_energies))+1) + " , " + str(min(ini_energies)))+" eV/atom")
			o.write(str("\n\nLowest energy initial structure: " + str(ini_energies.index(min(ini_energies))+1) + " , " + str(min(ini_energies)))+" eV/atom")
			current_structure=initial_population[ini_energies.index(min(ini_energies))+1]
			search_structures[0]=initial_population[ini_energies.index(min(ini_energies))+1]
			energies=[search_structures[0][3]]
			if target_energy == -27.394619:
				print(f'Energies: {energies}')
#			write(str("structures/"+str("BH-")+str('{0:0=7n}'.format(0)+".cif")),atoms)
			write("lowest_energy_structure.cif",search_structures[0][0])
			write("current_structure.cif",search_structures[0][0])
	#############################################################################

	fuse_time += time.time() - start_t
	start_t = time.time()

	# simulator = ActionSimulator(sl=[1])
	# simulator.add_dataset('fuse.csv')

	if not os.path.exists("accepted_energies.txt"):
		acpt = open("accepted_energies.txt", 'w')
		acpt.write("\n" + '0'.ljust(5) + str('{0:4s}'.format(str("NE = "))) + str('{0:4.8f}'.format(current_structure[3]).ljust(35)) + str(" eV/atom"))
		acpt.close()

	o.close()
	o=open("output.txt",'a')

	### now we can move onto using some of the searching routines ###############
	start=1
	if initial_complete == 1:
		if search != 3:

			actions_counter = {m: 0 for m in actions}
			max_failed_actions = 500
			action_executed = True
			excluded_actions = []
			selected_move = '1'

			while r < rmax:
				if start == 1:
					if restart == False:
						#plot_graph(search)
						count=1
					if swap_searches == False:
						if search == 1:
							print ("\n\n################################# Basin Hopping search ##################################\n")
							print ("Current lowest energy structure: " + str(energies.index(min(energies))) + " , " + str(min(energies))+" eV/atom\n")
							o.write("\n\n################################# Basin Hopping search ##################################\n")
							o.write("\n\nCurrent lowest energy structure: " + str(energies.index(min(energies))) + " , " + str(min(energies))+" eV/atom\n")
							start=0
						if search == 2:
							print ("\n\n################################# Genetic Algorithm search ##################################\n")
							print ("Current lowest energy structure: " + str(energies.index(min(energies))) + " , " + str(min(energies))+" eV/atom\n")
							o.write("\n\n################################# Genetic Algorithm search ##################################\n")
							o.write("\n\nCurrent lowest energy structure: " + str(energies.index(min(energies))) + " , " + str(min(energies))+" eV/atom\n")
							start=0

					else:
							print ("\n\n################################# Mixed Search Routine ##################################\n")
							print ("Current lowest energy structure: " + str(energies.index(min(energies))) + " , " + str(min(energies))+" eV/atom\n")
							o.write("\n\n################################# Mixed Search Routine ##################################\n")
							o.write("\n\nCurrent lowest energy structure: " + str(energies.index(min(energies))) + " , " + str(min(energies))+" eV/atom\n")
							start=0

				# first need to generate structures for the following generation ############
				if generation_complete==True:
					x=0
					built = 0
					generation=[]
					generation_energies=[]
					generation_moves=[]

					while built < search_gen:
						#print("built",built)

						if search == 1:
							# print(f'Current structure energy: {current_structure[3]}')
							old_state = State(current_structure[3])

							fuse_time += time.time() - start_t
							start_t = time.time()
							if action_executed or actions_counter[selected_move] >= max_failed_actions:
								if action_executed:
									actions_counter = {m: 0 for m in actions}
									excluded_actions = []
									action_executed = False
								elif selected_move not in excluded_actions:
									excluded_actions.append(selected_move)
								if len(excluded_actions) >= len(reinforce.actions):
									excluded_actions = []
								# treat move 5 separately as we can say prior the move that it can be done
								if '5' not in excluded_actions and len(current_structure[0]) * 2 > max_atoms:
									excluded_actions.append('5')
								if '4' not in excluded_actions and current_structure[2][4] <= 2:
									excluded_actions.append('4')
								selected_move = reinforce.select_action(old_state, excluded_actions=excluded_actions)
								print(f'Move {selected_move}, attempts {actions_counter[selected_move]}')
							else:
								actions_counter[selected_move] += 1
								if actions_counter[selected_move] > max_failed_actions and selected_move not in excluded_actions:
									excluded_actions.append(selected_move)
								print(f'Move {selected_move}, attempts {actions_counter[selected_move]}')
							# selected_move = random.choice(actions)
							# print(selected_move)
							reinforce_select_time += time.time() - start_t
							start_t = time.time()

							new_structure = make_basin_move(current_structure,atoms_per_fu,fu,vac_ratio,max_fus,system_type,
														  composition,ap,cubic_solutions,tetragonal_solutions,hexagonal_solutions,
														  orthorhombic_solutions,monoclinic_solutions,moves={int(selected_move):1},max_atoms=max_atoms,
														  initial_population=initial_population,search_structures=search_structures)

							# if we find out that the selected move is not allowed in this structure
							# we add id to the list of prohibited actions
							if new_structure is False:
								print(f'{selected_move} is not allowed')
								actions_counter[selected_move] = max_failed_actions
								continue

							if new_structure is None:
								continue

							move = str(new_structure[-1])
							del new_structure[-1]

						if search ==2:
							new_structure=make_ga_move(ratio=ratio,ini_structures=initial_population,search_structures=search_structures,pool_size=pool_size,atoms_per_fu=atoms_per_fu,fu=fu,vac_ratio=vac_ratio,max_fus=max_fus,system_type=system_type,composition=composition,ap=ap,cubic_solutions=cubic_solutions,tetragonal_solutions=tetragonal_solutions,hexagonal_solutions=hexagonal_solutions,orthorhombic_solutions=orthorhombic_solutions,monoclinic_solutions=monoclinic_solutions,max_atoms=max_atoms,moves=moves,max_pool_size=max_pool_size)
							move = "G"
						#print("\n",len(new_structure),"\n")
						atoms=new_structure[0]
						string=new_structure[1]
						instructions=new_structure[2]
						#move="place_holder"
						if atoms == None:
							continue

						#print("\n\n", str(move), "\n\n")

						accept=error_check_structure(atoms,ideal_density,density_cutoff,check_bonds,btol,system_type,fu,composition,bondtable,ap,check_distances,dist_cutoff,target_number_atoms=max_atoms)
						if accept == 0:
							continue
						if len(atoms) > max_atoms:
							continue
						if len(atoms) % len(fu) != 0:
							continue

						if check_previous == True:
							if prev_start_points != []:
								check=check_prev_structure(atoms,prev_start_points)
								#print(check)
							else:
								check = False

							if check == False:
								x=0

							if check == None:
								continue
							if check == True:
								x+=1
								if x == new_structure_attempts:
									print("Failed to generate new unique structures, will stop calculation after this generation")
									f=open("stop.txt",'w')
									f.close()
									check_previous=False
								continue

						if use_amds == True:
							amd=compute_amd(atoms1=atoms,rep=amd_rep,k=amd_k)
							if amd in amds:
								amd_matches+=1
								continue

							if not amd in amds:
								amds.append(amd)

						#initial_population[built+1]=[atoms,string,instructions]
						print (str("built " + str(built+1) + " of " + str(search_gen)),end="\r")
						temp_atoms=atoms.copy()
						sort(temp_atoms)
						if check_previous == True:
							pass
							#prev_start_points.append(spglib.standardize_cell(temp_atoms,symprec=1e-5))
						atoms.rattle(ratt_dist)
						generation.append(new_structure)
						if search == 1:
							generation_moves.append(str(move))
						else:
							generation_moves.append("G")
						built += 1
					generation_complete=False
			#############################################################################
				## now need to go through & relax structures ################################
				#print(generation_moves)
				o.close()
				o=open("output.txt",'a')
				pickle.dump(generation_moves,open("generation_moves.p",'wb'))
				if itr < iterations:
					if serial == True:
						scalc=len(generation_energies)
						if generation_complete==False:
							for i in range(0+scalc,search_gen):
								if itr == iterations:
									break
								nstruct=len(generation)
								o.write("\n")
								atoms=generation[i][0]
								iat=len(atoms)
								print (str("structure " + str(i+1) +" of " + str(nstruct)),end="\r")

								if compute_space_groups == True:
									pass
									#### PS EDIT
									# Use spglib to obtain spacegroup and record in csv file
									#spg.write('%i %s\n' %(count+initial_gen, spglib.get_spacegroup(atoms)))
									#### PS EDIT

								if ctype == 'gulp':
									try:
										fuse_time += time.time() - start_t
										start_t = time.time()
										atoms,energy,converged=run_gulp(atoms=atoms,shel=shel,kwds=kwds,opts=gulp_opts,
																		lib=lib,produce_steps=produce_steps,gulp_command=gulp_command)
									except:
										converged = False
										energy = 1.e20

									gulp_time += time.time() - start_t
									start_t = time.time()

								if ctype == 'vasp':
									try:
										atoms,energy,converged=run_vasp(atoms=atoms,vasp_opts=vasp_opts,kcut=kcut,produce_steps=produce_steps,dist_cutoff=dist_cutoff)
									except:
										converged = False
										energy = 1.e20

								if ctype == 'qe':
									try:
										atoms,energy,converged=run_qe(atoms=atoms,qe_opts=qe_opts,kcut=kcut,produce_steps=produce_steps)
									except:
										converged=False
										energy=1.e20

								if ctype == 'mixed':
									try:
										atoms,energy,converged=run_calculators(atoms=atoms,vasp_opts=
											vasp_opts,kcut=kcut,produce_steps=produce_steps,shel=shel,
											kwds=kwds,gulp_opts=gulp_opts,lib=lib,calcs=calcs,dist_cutoff=dist_cutoff,qe_opts=qe_opts,
											gulp_command=gulp_command)

									except:
										converged = False
										energy = 1.e20

								if len(atoms) != iat:
									converged = False
									energy = 1.e20
								if converged != True:
									if produce_steps==True:
										targets=glob.glob("atoms*.cif")
										targets.sort()
										for z in range(len(targets)):
											label=str("steps/S"+str(count)+"_"+str(z+1)+str(".cif"))
											shutil.copy(targets[z],label)

								energy = energy/len(atoms)
								energy = float(Decimal(energy).quantize(Decimal('1e-6')))

								action_executed = True

								# new_state, outcome = simulator.simulate_action(old_state, selected_move)
								# energy = new_state.energy
								generation[i].append(energy)
								generation[i][0]=atoms
								#print(str("I{0:=6n}".format(i+1)+"  {0:0=6.6n}	  eV/atom".format(float(energy)).rjust(25)))
								if search == 1:
									o.write(str("BH{0:=7n}".format(count)+"	 {0:=6.6n}   eV/atom".format(float(energy)).rjust(25)))
								if search == 2:
									o.write(str("GA{0:=7n}".format(count)+"	 {0:=6.6n}   eV/atom".format(float(energy)).rjust(25)))

								if write_all_structures == True:
									try:
										write(str("structures/"+str("S-")+str('{0:0=7n}'.format(count)+".cif")),atoms)
									except:
										pass
								# if write_graph==True:
								try:
									if converged != False:
										graph['move'].append(str(generation_moves[i]))
										graph['type'].append("S")
										graph['step'].append(count+initial_gen)
										graph['energies'].append(energy)
										if swap_searches == False:
											if search == 1:
												graph['temp'].append(T)
										else:
												graph['temp'].append(T)
										graph['current_energy'].append(current_structure[3])
										graph_write=pandas.DataFrame(graph)
										graph_write.to_csv(path_or_buf="graph_output.csv",index=False)
									if count % 10 == 0:
										if write_graph:
											if swap_searches==False:
												plot_graph(search=search)
											else:
												plot_graph()
								except:
									graph['move']=[str(generation_moves[i])]
									graph['type']=["S"]
									graph['step']=[count+initial_gen]
									graph['energies']=[energy]
									if swap_searches == False:
										if search == 1:
											graph['temp']=[T]
									else:
										graph['temp']=[T]
									graph['current_energy']=[current_structure[-1]]
									graph_write=pandas.DataFrame(graph)
									graph_write.to_csv(path_or_buf="graph_output.csv",index=False)
								if count % 10 == 0:
									if write_graph:
										if swap_searches == False:
											plot_graph(search=search)
										else:
											plot_graph()
										#print(graph)

								generation_energies.append(energy)
								search_structures[count]=[atoms,generation[i][1],generation[i][2],energy,generation_moves[i]]
								itr+=1
								count+=1
								if len(generation_energies) == search_gen:
									generation_complete=True
									print("Generation completed: ",end=' ')
									o.write("\nGeneration completed: ")
								if os.path.isfile("stop.txt"):
									print ("** Stopping caclulation **")
									### while this will now run all of the initial population, need to then log & store the data!
									# now need to write out what we've got so far...
									print ("Writing restart files...")
									o.write("\nWriting restart files...\n")
									min_structure_num=energies.index(min(energies))
									min_structure=search_structures[min_structure_num][0]
									write("lowest_energy_structure.cif",min_structure)
									pickle.dump(initial_population,open("initial_structures.p",'wb'))
									pickle.dump(energies,open("energies.p",'wb'))
									pickle.dump(search_structures,open("search_structures.p",'wb'))
									if initial_complete==1:
										pickle.dump(current_structure,open("current_structure.p",'wb'))
									pickle.dump(generation_complete,open("generation_complete.p",'wb'))
									if generation_complete==False:
										pickle.dump(generation,open("generation.p",'wb'))
										pickle.dump(generation_energies,open("generation_energies.p",'wb'))
									pickle.dump(search_structures,open("search_structures.p",'wb'))
									pickle.dump(r,open("r.p",'wb'))
									pickle.dump(ini_energies,open("ini_energies.p",'wb'))
									pickle.dump(ca,open("ca.p",'wb'))
									pickle.dump(T,open("T.p",'wb'))
									pickle.dump(search,open("search.p",'wb'))
									if check_previous == True:
										pickle.dump(prev_start_points,open("start_points.p",'wb'))
									if swap_searches == True:
										pickle.dump(sa,open("sa.p",'wb'))
									pickle.dump(moves,open("moves.p",'wb'))
									# if write_graph == True:
									graph_to_write=graph.copy()
									graph_to_write['file_name']=[]
									for x in range(len(graph_write['step'])):
										number=graph_to_write['step'][x]
										if graph_to_write['type'][x] == 'S':
											number -= initial_gen

										label=str( graph_to_write['type'][x] + "_" + str("{0:06d}").format(number) + ".cif")
										graph_to_write['file_name'].append(label)

									graph_to_write=pandas.DataFrame(graph_to_write)
									graph_to_write.to_csv(path_or_buf="graph_output.csv",index=False)
									if write_graph:
										if swap_searches == False:
											plot_graph(search=search)
										else:
											plot_graph()

									if use_amds == True:
										pickle.dump(amds,open("amds.p",'wb'))
										pickle.dump(amd_matches,open("amd_matches.p",'wb'))
									#############################################################################

									### print out total runtime #################################################
									t2=datetime.datetime.now()
									print("\ntotal time: "+str(t2-t1)+" hours:minutes:seconds")
									o.write("\n\ntotal time: "+str(t2-t1)+" hours:minutes:seconds\n")
									o.close()
									os.remove("stop.txt")
									save_backup_files()
									sys.exit()
								else:
									if energy <= min(energies):
										min_structure = search_structures[count-1][0]
										write("lowest_energy_structure.cif", min_structure)
									pickle.dump(initial_population,open("initial_structures.p",'wb'))
									pickle.dump(energies,open("energies.p",'wb'))
									pickle.dump(search_structures,open("search_structures.p",'wb'))
									if initial_complete==1:
										pickle.dump(current_structure,open("current_structure.p",'wb'))
									pickle.dump(generation_complete,open("generation_complete.p",'wb'))
									if generation_complete==False:
										pickle.dump(generation,open("generation.p",'wb'))
										pickle.dump(generation_energies,open("generation_energies.p",'wb'))
									pickle.dump(search_structures,open("search_structures.p",'wb'))
									pickle.dump(r,open("r.p",'wb'))
									pickle.dump(ini_energies,open("ini_energies.p",'wb'))
									pickle.dump(ca,open("ca.p",'wb'))
									pickle.dump(T,open("T.p",'wb'))
									if swap_searches == True:
										pickle.dump(sa,open("sa.p",'wb'))
									pickle.dump(moves,open("moves.p",'wb'))
									pickle.dump(search,open("search.p",'wb'))
									if check_previous == True:
										pickle.dump(prev_start_points,open("start_points.p",'wb'))
									if use_amds == True:
										pickle.dump(amds,open("amds.p",'wb'))
										pickle.dump(amd_matches,open("amd_matches.p",'wb'))
						if generation_complete == True:
							#if write_graph==True:
							#	plot_graph(search)
							# MC Accept part #############################################
							mc_output = 'R'
							old_structure = current_structure.copy()
							if min(generation_energies) < current_structure[3]:
							#if min(generation_energies) < min(energies):
								idx=generation_energies.index(min(generation_energies))
								current_structure=generation[idx].copy()
								mc_output = 'A'
								new=1
								if min(generation_energies) < min(energies):
									r=0
									sa=0
								if min(generation_energies) != min(energies):
									ca=0
									#if swap_searches == True:
									#	sa=0
									if search == 1:
										moves = n_moves
								T=T_0
								if min(generation_energies) < min(energies):
									write("lowest_energy_structure.cif",current_structure[0])

								write("current_structure.cif",current_structure[0])
							if min(generation_energies) >= min(energies):
								if min(generation_energies) < 0:
									new=0
									if search == 1:
										rand=random.random()
										diff=min(generation_energies)-min(energies)
										Test=math.exp(-diff/T)
										if Test>=rand:
											new=2
											idx=generation_energies.index(min(generation_energies))
											current_structure=generation[idx].copy()
											mc_output = 'mcA'
											write("current_structure.cif",current_structure[0])

											#T=T_0
											#ca=0
								else:
									mc_output = 'cR'
								r+=len(generation)
								ca+=len(generation)
								if swap_searches == True:
									sa+=len(generation)
							#print(("Ca "+str(ca)),end='')
							##############################################################
							dE=float(Decimal(min(generation_energies)-min(energies)).quantize(Decimal('1e-6')))
							if use_amds != True:
								print(str("E = "+str("{0: .5e}").format(min(generation_energies)) + " dE vs. global = " + str("{0: .4e}").format(dE).rjust(7)+" r: "+str(r).rjust(4)),end='')
							if use_amds == True:
								print(str("E = "+str("{0: .5e}").format(min(generation_energies)) + " dE vs. global = " + str("{0: .4e}").format(dE).rjust(7)+" r: "+str(r).rjust(4)+" Amd match = "+str(amd_matches)),end='')

							if search == 1:
								print("	 T = "+str("{0:.5f}").format(T))
							else:
								print('')
							#print(sa)

							if use_amds != True:
								o.write("E = "+str("{0: .5e}").format(min(generation_energies)) + " dE vs. global = " + str("{0: .4e}").format(dE).rjust(7)+" r: "+str(r).rjust(4))
							if use_amds == True:
								o.write("E = "+str("{0: .5e}").format(min(generation_energies)) + " dE vs. global = " + str("{0: .4e}").format(dE).rjust(7)+" r: "+str(r).rjust(4) + " Amd match = "+str(amd_matches))

							if search == 1:
								o.write("  T = "+str("{0:.5f}").format(T)+"\n")
							else:
								o.write("\n")

							unique_energy = generation_energies[0] not in energies

							for j in range(len(generation_energies)):
								energies.append(generation_energies[j])

							#print(generation_energies)
							#try:
							#	start_point=max(list(search_structures.keys()))
							#except:
							#	start_point=0
							#for j in range(len(generation)):
							#	search_structures[start_point+j+1]=generation[j]
							o.flush()

							if energy != new_structure[3]:
								print('DEBUG')

							fuse_time += time.time() - start_t
							start_t = time.time()
							new_state = State(energy, unique=unique_energy)
							reinforce.update(selected_move, old_state, new_state)
							action_executed = True

							reinforce_update_time += time.time() - start_t
							start_t = time.time()

							o.write(f'Step {step}. Time elapsed for fuse: {fuse_time}, gulp: {gulp_time}, '
								  f'reinforce_select: {reinforce_select_time}, '
								  f'reinforce_update: {reinforce_update_time}\n')

							step += 1
							log_file = {'step': [step],
										'starting_modules': [old_structure[0].symbols],
										'modules': [new_structure[0].symbols],
										'move_type': [selected_move],
										'energy': [energy],
										'mc_outcome': [mc_output]}

							try:
								out_data = pandas.DataFrame(log_file)
								out_data.to_csv(log_filename, mode='a', header=False, index=False)
							except ValueError:
								print(log_file)
								sys.exit()

					#######################################################################

					#######################################################################

					if search == 1:
						if ca >= melt_threshold:
							T+=(random.random()/100)
							T=float(Decimal(T).quantize(Decimal('1e-6')))
							moves=r_moves
					if swap_searches == True:
						if sa >= swap_threshold:
							if search == 1:
								search = 2
								sa=0
								if swap_back==False:
									swap_searches = False
								continue
							if search == 2:
								search = 1
								sa=0
								if swap_back == False:
									swap_searches = False
								continue

				sys.stdout.flush()

				if itr >= iterations:
					break

				# if we found the target energy stop searching
				if 0 > target_energy >= min(energies):
					break

				# save backup files after each successful iteration
				save_backup_files()

					#############################################################################
		if search == 3:
			if start ==1:
				print ("\n\n################################# Machine Learning search ##################################\n")
				print ("Current lowest energy structure: " + str(energies.index(min(energies))) + " , " + str(min(energies))+" eV/atom\n")
				o.write("\n\n################################# Machine Learning search ##################################\n")
				o.write("\n\nCurrent lowest energy structure: " + str(energies.index(min(energies))) + " , " + str(min(energies))+" eV/atom\n")
				start=0

			# step 1, construct ML model
			model = create_ml_model(ini_structures=initial_population,search_structures=search_structures)
			# step 2, genearte & predict energies for a new generation
			sys.exit()


	if r >= rmax:
		print("\n*** Break conditions met stopping calculation ***\n")
		o.write("\n\n*** Break conditions met stopping calculation ***\n")
		print("Global minimum energy: "+str(min(energies))+" Structure: "+str(energies.index(min(energies))))
		o.write("\nGlobal minimum energy: "+str(min(energies))+" Structure: "+str(energies.index(min(energies))))
	elif 0 > target_energy >= min(energies):
		print("\n*** Target minimum found stopping calculation ***\n")
		o.write("\n\n*** Target minimum found stopping calculation ***\n")
		print("Global minimum energy: "+str(min(energies))+" Structure: "+str(energies.index(min(energies))))
		o.write("\nGlobal minimum energy: "+str(min(energies))+" Structure: "+str(energies.index(min(energies))))
		acpt = open("accepted_energies.txt", 'a')
		acpt.write(f"\nTarget energy found: {min(energies)}")
		acpt.close()
	else:
		if iterations > 0:
			print("\n*** Max number of steps reached stopping calculation ***")
			o.write("\n\n*** Max number of steps reached stopping calculation ***")
			print("Current global minimum energy: "+str(min(energies))+" Structure: "+str(energies.index(min(energies))))
			o.write("\nCurrent Global minimum energy: "+str(min(energies))+" Structure: "+str(energies.index(min(energies))))

	### while this will now run all of the initial population, need to then log & store the data!
	# now need to write out what we've got so far...
	print ("Writing restart files...")

	try:
		min_structure_num=energies.index(min(energies))
		min_structure=search_structures[min_structure_num][0]
		write("lowest_energy_structure.cif",min_structure)
	except KeyError:
		pass

	if write_graph_end:
		graph_to_write=graph.copy()
		graph_to_write['file_name']=[]
		for x in range(len(graph_to_write['step'])):
			number=graph_to_write['step'][x]
			if graph_to_write['type'][x] == 'S':
				number -= initial_gen

			label=str( graph_to_write['type'][x] + "_" + str("{0:06d}").format(number) + ".cif")
			graph_to_write['file_name'].append(label)

		graph_to_write=pandas.DataFrame(graph_to_write)
		graph_to_write.to_csv(path_or_buf="graph_output.csv",index=False)
		if swap_searches == False:
			plot_graph(search=search)
		else:
			plot_graph()


	o.write("\nWriting restart files...\n")
	pickle.dump(initial_population,open("initial_structures.p",'wb'))
	pickle.dump(energies,open("energies.p",'wb'))
	pickle.dump(search_structures,open("search_structures.p",'wb'))
	if initial_complete==1:
		pickle.dump(current_structure,open("current_structure.p",'wb'))
	pickle.dump(generation_complete,open("generation_complete.p",'wb'))
	if generation_complete==False:
		pickle.dump(generation,open("generation.p",'wb'))
		pickle.dump(generation_energies,open("generation_energies.p",'wb'))
	pickle.dump(search_structures,open("search_structures.p",'wb'))
	pickle.dump(r,open("r.p",'wb'))
	pickle.dump(ini_energies,open("ini_energies.p",'wb'))
	pickle.dump(ca,open("ca.p",'wb'))
	pickle.dump(T,open("T.p",'wb'))
	pickle.dump(search,open("search.p",'wb'))
	if check_previous == True:
		pickle.dump(prev_start_points,open("start_points.p",'wb'))
	if swap_searches == True:
		pickle.dump(sa,open("sa.p",'wb'))
	pickle.dump(moves,open("moves.p",'wb'))
	if compute_space_groups == True:
		pass
		#### PS EDIT
		# Close spacegroup file
		#spg.close()
		#### PS EDIT

	if use_amds == True:
		pickle.dump(amds,open("amds.p",'wb'))
		pickle.dump(amd_matches,open("amd_matches.p",'wb'))

	#############################################################################

	### print out total runtime #################################################
	t2=datetime.datetime.now()
	print("\ntotal time: "+str(t2-t1)+" hours:minutes:seconds")
	o.write("\n\ntotal time: "+str(t2-t1)+" hours:minutes:seconds\n")
	o.close()
