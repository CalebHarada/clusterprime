#!/usr/bin/bash

# create a parameters.txt file containing the starting and stopping frame number
# for each slurm array job.
for i in {0..112}; do
    if (( $i % 1 == 0 )); then
        echo $i $(( $i+1 < 113 ? $i+1 : 113 )) >> "parameters.txt"
    fi
done


