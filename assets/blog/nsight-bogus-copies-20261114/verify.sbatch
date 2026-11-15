#!/bin/bash
#SBATCH -p training
#SBATCH -w dgx-009
#SBATCH --gres=gpu:1
#SBATCH -n 1
#SBATCH -c 16
#SBATCH -t 40
#SBATCH -J nsight-verify
#SBATCH -o /home/shiheming/nsight_bench/verify_%j.log
bash "$HOME/nsight_bench/run_verify.sh"
