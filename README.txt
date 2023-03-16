The original version of FUSE is generally available from: https://github.com/lrcfmd/FUSE-stable
The version provided uses Reinforcement Learning package RLCSP (https://github.com/lrcfmd/rlcsp) to optimize basin hopping routine.
The input files 'input\_\<composition\>.py' for five compositions are provided to run FUSE with RLCSP.

################################################################################

Instructions for installing FUSE:

Requirements:

1) Python3.6 or later

once you have python3 installed, you need to download the following 
dependencies:

all of which can be installed via pip:

1) numpy
2) scipy
3) ase (you will need to be familiar with ase to configure the vasp calculatior
is you want to use DFT details can be found in ase's documentation here
: https://wiki.fysik.dtu.dk/ase/index.html)
4) spglib
5) scikit-learn
6) matplotlib

you should then install RLCSP from https://github.com/lrcfmd/rlcsp.git

you can then install FUSE by typing:

python3 setup.py install

################################################################################

in order to run FUSE, you will require a computational chemistry code, currently
supported
are GULP and VASP.

using GULP (more information can be found on the ase website in their 
documentation on calculators):

prior to running FUSE with GULP, the following environment variables need to be 
set:

"GULP_LIB" - path to interatomic potential libraries (it will also work if you 
set to '')

"ASE_GULP_COMMAND" - system command to run gulp, e.g. ASE_GULP_COMMAND='mpirun 
-np 16 gulp < gulp.gin > gulp.got'

you will additionally need an interatomic potential library to run calculations,
typically this needs to be in the same directory as the input file for FUSE, and
the 'lib' variable in the input file needs to be set to the name of the
potential library

################################################################################

using VASP (more information can be found on the ase website in their 
documentation on calculators):

Two enviornment variables need to be set to use VASP:

VASP_PP_PATH - this is the path to pseudo poential files for VASP

VASP_SCRIPT - path to a python script containing the required system command to 
run vasp (see example "vasp.py")




