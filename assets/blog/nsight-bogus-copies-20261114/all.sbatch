#!/bin/bash
#SBATCH -p training
#SBATCH -w dgx-009
#SBATCH --gres=gpu:1
#SBATCH -n 1
#SBATCH -c 16
#SBATCH -t 40
#SBATCH -J nsight-all
#SBATCH -o /home/shiheming/nsight_bench/all_%j.log
bash /home/shiheming/nsight_bench/run_all.sh
