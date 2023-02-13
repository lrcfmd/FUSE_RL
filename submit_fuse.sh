#!/bin/bash -l
# Use the current working directory
#SBATCH -D ./
# Use the current environment for this job.
#SBATCH --export=ALL
# Define job name
#SBATCH -J fuse_rl
# Define a standard output file. When the job is running, %u will be replaced by user name,
# %N will be replaced by the name of the node that runs the batch script, and %j will be replaced by job id number.
# Request the partition
#SBATCH -p nodes,rosseinsky
# Request the number of nodes
#SBATCH -N 1
# Request the number of cores
#SBATCH -n 1
###SBATCH --exclusive
# This asks for 10 hours of time.
#SBATCH -t 3-00:00:00
#SBATCH --array=1-40
#SBATCH -o comp1.%j.out
#SBATCH -e comp1.%j.err
ulimit -s unlimited
module purge

# Load VASP module
module load apps/gulp/5.1-intel2018
# List all modules
#module load apps/gulp/5.1-gfortran 
# Specify which version of VASP to use (vasp541 or vasp544)
EXEC=/users/cc0u514b/Apps/anaconda3/bin/python
#
# Should not need to edit below this line
#
echo =========================================================   
echo SLURM job: submitted  date = `date`      
date_start=`date +%s`

echo Executable file:                              
echo MPI parallel job.                                  
echo -------------  
echo Job output begins                                           
echo -----------------                                           
echo

hostname

echo "Print the following environmetal variables:"
echo "Job name                     : $SLURM_JOB_NAME"
echo "Job ID                       : $SLURM_JOB_ID"
echo "Job user                     : $SLURM_JOB_USER"
echo "Job array index              : $SLURM_ARRAY_TASK_ID"
echo "Submit directory             : $SLURM_SUBMIT_DIR"
echo "Temporary directory          : $TMPDIR"
echo "Submit host                  : $SLURM_SUBMIT_HOST"
echo "Queue/Partition name         : $SLURM_JOB_PARTITION"
echo "Node list                    : $SLURM_JOB_NODELIST"
echo "Hostname of 1st node         : $HOSTNAME"
echo "Number of nodes allocated    : $SLURM_JOB_NUM_NODES or $SLURM_NNODES"
echo "Number of processes          : $SLURM_NTASKS"
echo "Number of processes per node : $SLURM_TASKS_PER_NODE"
echo "Requested tasks per node     : $SLURM_NTASKS_PER_NODE"
echo "Requested CPUs per task      : $SLURM_CPUS_PER_TASK"
echo "Scheduling priority          : $SLURM_PRIO_PROCESS"




echo "Running parallel job:"

# If you use all of the slots specified in the -pe line above, you do not need
# to specify how many MPI processes to use - that is the default
# the ret flag is the return code, so you can spot easily if your code failed.
#export ASE_GULP_COMMAND='mpirun /users/cc0u514b/Apps/gulp-4.5_intel/Src/gulp < gulp.gin > gulp.got'
export OMP_NUM_THREADS=$SLURM_NTASKS
export ASE_GULP_COMMAND='gulp < gulp.gin > gulp.got'
export GULP_LIB=""

cd $SLURM_ARRAY_TASK_ID
$EXEC input.py $SLURM_ARRAY_TASK_ID >> run.txt

ret=$?


# If you only wanted to some of those cores, specify the precise number:
#mpirun  -np 12 $EXEC 
#ret=$?


echo   
echo ---------------                                           
echo Job output ends                                           
date_end=`date +%s`
seconds=$((date_end-date_start))
minutes=$((seconds/60))
seconds=$((seconds-60*minutes))
hours=$((minutes/60))
minutes=$((minutes-60*hours))
echo =========================================================   
echo SLURM job: finished   date = `date`   
echo Total run time : $hours Hours $minutes Minutes $seconds Seconds
echo =========================================================   
exit $ret
