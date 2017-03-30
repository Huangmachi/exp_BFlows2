#!/bin/bash
# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, China.

k=$1
cpu=$2
flowsPerHost=$3   # number of iperf flows per host.
duration=$4
out_dir=$5

# Exit on any failure.
set -e

# Check for uninitialized variables.
set -o nounset

ctrlc() {
	killall python
	killall -9 ryu-manager
	mn -c
	exit
}

trap ctrlc INT

# Traffic patterns.
# "stag_0.5_0.3" means 50% under the same Edge switch,
# 30% between different Edge switches in the same Pod,
# and 20% between different Pods.
# "random" means choosing the iperf server randomly.
# Change it if needed.
# traffics="random stag_0.2_0.3 stag_0.3_0.3 stag_0.4_0.3 stag_0.5_0.3 stag_0.6_0.2 stag_0.7_0.2 stag_0.8_0.1"
# traffics="random1 random2 stag1_0.2_0.3 stag2_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag1_0.5_0.3 stag2_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1"
traffics="random1 random2 random3 stag1_0.1_0.2 stag2_0.1_0.2 stag3_0.1_0.2 stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1"

# Run experiments.
for traffic in $traffics
do
	# Create iperf peers.
	sudo python ./create_peers.py --k $k --traffic $traffic --fnum $flowsPerHost
	sleep 1

	# BFlows
	dir=$out_dir/$flowsPerHost/$traffic/BFlows
	mkdir -p $dir
	mn -c
	sudo python ./BFlows/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu

	# ECMP
	dir=$out_dir/$flowsPerHost/$traffic/ECMP
	mkdir -p $dir
	mn -c
	sudo python ./ECMP/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu

	# PureSDN
	dir=$out_dir/$flowsPerHost/$traffic/PureSDN
	mkdir -p $dir
	mn -c
	sudo python ./PureSDN/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu

	# Hedera
	dir=$out_dir/$flowsPerHost/$traffic/Hedera
	mkdir -p $dir
	mn -c
	sudo python ./Hedera/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu

	# NonBlocking
	dir=$out_dir/$flowsPerHost/$traffic/NonBlocking
	mkdir -p $dir
	mn -c
	sudo python ./NonBlocking/NonBlocking.py --k $k --duration $duration --dir $dir --cpu $cpu

done


# # Plot results.
sudo python ./plot_results.py --k $k --duration $duration --dir $out_dir --fnum $flowsPerHost
