#!/bin/bash
#SBATCH -J "VEC"
#SBATCH --mail-type=ALL
#SBATCH -p gpu
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=128G
#SBATCH --cpus-per-task=4

echo "Starting the run at: `date`"
python3 train_ntwk.py
echo "Program ended with exit code $? at: `date`"