#!/bin/bash
# Job name:
#SBATCH --job-name=ngc752_reduce
#
# Account:
#SBATCH --account=nahiku
#
# Partition:
#SBATCH --partition=nahiku
#
# Wall clock limit:
#SBATCH --time=0-10:00:00
#
# Job array settings:
#SBATCH --array=1-113
#SBATCH --cpus-per-task=1
#SBATCH --mem=16GB
#
# Errors and outputs
#SBATCH --error=slurm_out/ngc752_reduce.%A_%a.err ## %A - filled with jobid
#SBATCH --output=slurm_out/ngc752_reduce.%A_%a.out ## %A - filled with jobid
#
# Email options:
#SBATCH --mail-type=ALL
#SBATCH --mail-user=ckharada@hawaii.edu
#
# Command(s) to run:
module purge
module load lang/Anaconda3
source activate clusterprime_env
#
# run this after creating the parameters.txt file using the bash script
fid=$(sed -n "${SLURM_ARRAY_TASK_ID}p" parameters.txt)
echo "${fid}"
python NGC752_reduce.py ${fid}

