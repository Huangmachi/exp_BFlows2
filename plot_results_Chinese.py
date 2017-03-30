# -*- coding: UTF-8 -*-
# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, Chongqing, China.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
chinese_font = FontProperties(fname='/usr/share/matplotlib/mpl-data/fonts/ttf/simhei.ttf')


parser = argparse.ArgumentParser(description="Plot BFlows experiments' results")
parser.add_argument('--k', dest='k', type=int, default=4, choices=[4, 8], help="Switch fanout number")
parser.add_argument('--duration', dest='duration', type=int, default=60, help="Duration (sec) for each iperf traffic generation")
parser.add_argument('--dir', dest='out_dir', help="Directory to store outputs")
parser.add_argument('--fnum', dest='flows_num_per_host', type=int, default=1, help="Number of iperf flows per host")
args = parser.parse_args()


def read_file_1(file_name, delim=','):
	"""
		Read the bwmng.txt file.
	"""
	read_file = open(file_name, 'r')
	lines = read_file.xreadlines()
	lines_list = []
	for line in lines:
		line_list = line.strip().split(delim)
		lines_list.append(line_list)
	read_file.close()

	# Remove the last second's statistics, because they are mostly not intact.
	last_second = lines_list[-1][0]
	_lines_list = lines_list[:]
	for line in _lines_list:
		if line[0] == last_second:
			lines_list.remove(line)

	return lines_list

def read_file_2(file_name):
	"""
		Read the first_packets.txt and successive_packets.txt file.
	"""
	read_file = open(file_name, 'r')
	lines = read_file.xreadlines()
	lines_list = []
	for line in lines:
		if line.startswith('rtt') or line.endswith('ms\n'):
			lines_list.append(line)
	read_file.close()
	return lines_list

def calculate_average(value_list):
	average_value = sum(map(float, value_list)) / len(value_list)
	return average_value

def get_throughput(throughput, traffic, app, input_file):
	"""
		csv output format:
		(Type rate)
		unix_timestamp;iface_name;bytes_out/s;bytes_in/s;bytes_total/s;bytes_in;bytes_out;packets_out/s;packets_in/s;packets_total/s;packets_in;packets_out;errors_out/s;errors_in/s;errors_in;errors_out\n
		(Type svg, sum, max)
		unix timestamp;iface_name;bytes_out;bytes_in;bytes_total;packets_out;packets_in;packets_total;errors_out;errors_in\n
		The bwm-ng mode used is 'rate'.

		throughput = {
						'stag_0.5_0.3':
						{
							'realtime_bisection_bw': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'BFlows':x%, 'ECMP':x%, ...}
						},
						'stag_0.6_0.2':
						{
							'realtime_bisection_bw': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'BFlows':x%, 'ECMP':x%, ...}
						},
						...
					}
	"""
	full_bisection_bw = 10.0 * (args.k ** 3 / 4)   # (unit: Mbit/s)
	lines_list = read_file_1(input_file)
	first_second = int(lines_list[0][0])
	column_bytes_out_rate = 2   # bytes_out/s
	column_bytes_out = 6   # bytes_out

	if app == 'NonBlocking':
		switch = '1001'
	elif app in ['ECMP', 'Hedera', 'PureSDN', 'BFlows']:
		switch = '3[0-9][0-9][0-9]'
	else:
		pass
	sw = re.compile(switch)

	if not throughput.has_key(traffic):
		throughput[traffic] = {}

	if not throughput[traffic].has_key('realtime_bisection_bw'):
		throughput[traffic]['realtime_bisection_bw'] = {}
	if not throughput[traffic].has_key('realtime_throughput'):
		throughput[traffic]['realtime_throughput'] = {}
	if not throughput[traffic].has_key('accumulated_throughput'):
		throughput[traffic]['accumulated_throughput'] = {}
	if not throughput[traffic].has_key('normalized_total_throughput'):
		throughput[traffic]['normalized_total_throughput'] = {}

	if not throughput[traffic]['realtime_bisection_bw'].has_key(app):
		throughput[traffic]['realtime_bisection_bw'][app] = {}
	if not throughput[traffic]['realtime_throughput'].has_key(app):
		throughput[traffic]['realtime_throughput'][app] = {}
	if not throughput[traffic]['accumulated_throughput'].has_key(app):
		throughput[traffic]['accumulated_throughput'][app] = {}
	if not throughput[traffic]['normalized_total_throughput'].has_key(app):
		throughput[traffic]['normalized_total_throughput'][app] = 0

	for i in xrange(args.duration + 1):
		if not throughput[traffic]['realtime_bisection_bw'][app].has_key(i):
			throughput[traffic]['realtime_bisection_bw'][app][i] = 0
		if not throughput[traffic]['realtime_throughput'][app].has_key(i):
			throughput[traffic]['realtime_throughput'][app][i] = 0
		if not throughput[traffic]['accumulated_throughput'][app].has_key(i):
			throughput[traffic]['accumulated_throughput'][app][i] = 0

	for row in lines_list:
		iface_name = row[1]
		if iface_name not in ['total', 'lo', 'eth0', 'enp0s3', 'enp0s8', 'docker0']:
			if switch == '3[0-9][0-9][0-9]':
				if sw.match(iface_name):
					if int(iface_name[-1]) > args.k / 2:   # Choose down-going interfaces only.
						if (int(row[0]) - first_second) <= args.duration:   # Take the good values only.
							throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (10 ** 6)   # Mbit/s
							throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (10 ** 6)   # Mbit
			elif switch == '1001':   # Choose all the interfaces. (For NonBlocking Topo only)
				if sw.match(iface_name):
					if (int(row[0]) - first_second) <= args.duration:
						throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (10 ** 6)   # Mbit/s
						throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (10 ** 6)   # Mbit
			else:
				pass

	for i in xrange(args.duration + 1):
		for j in xrange(i+1):
			throughput[traffic]['accumulated_throughput'][app][i] += throughput[traffic]['realtime_throughput'][app][j]   # Mbit

	throughput[traffic]['normalized_total_throughput'][app] = throughput[traffic]['accumulated_throughput'][app][args.duration] / (full_bisection_bw * args.duration)   # percentage

	return throughput

def get_value_list_1(throughput, traffic, item, app):
	"""
		Get the values from the "throughput" data structure.
	"""
	value_list = []
	for i in xrange(args.duration + 1):
		value_list.append(throughput[traffic][item][app][i])
	return value_list

def get_average_bisection_bw(throughput, traffics, app, num, num_groups):
	value_list = []
	for traffic in traffics[(num * num_groups): (num * num_groups + num_groups)]:
		value_list.append(throughput[traffic]['accumulated_throughput'][app][args.duration] / float(args.duration))
	return value_list

def get_value_list_2(value_dict, traffics, item, app, num, num_groups):
	"""
		Get the values from the  data structure.
	"""
	value_list = []
	for traffic in traffics[(num * num_groups): (num * num_groups + num_groups)]:
		value_list.append(value_dict[traffic][item][app])
	return value_list

def get_utilization(utilization, traffic, app, input_file):
	"""
		Get link utilization and link bandwidth utilization.
	"""
	lines_list = read_file_1(input_file)
	first_second = int(lines_list[0][0])
	column_packets_out = 11   # packets_out
	column_packets_in = 10   # packets_in
	column_bytes_out = 6   # bytes_out
	column_bytes_in = 5   # bytes_in

	if not utilization.has_key(traffic):
		utilization[traffic] = {}
	if not utilization[traffic].has_key(app):
		utilization[traffic][app] = {}

	for row in lines_list:
		iface_name = row[1]
		if iface_name.startswith('1'):
			if (int(row[0]) - first_second) <= args.duration:   # Take the good values only.
				if not utilization[traffic][app].has_key(iface_name):
					utilization[traffic][app][iface_name] = {'LU_out':0, 'LU_in':0, 'LBU_out':0, 'LBU_in':0}
				# if int(row[11]) > 2:
				if row[6] not in ['0', '60']:
					utilization[traffic][app][iface_name]['LU_out'] = 1
				# if int(row[10]) > 2:
				if row[5] not in ['0', '60']:
					utilization[traffic][app][iface_name]['LU_in'] = 1
				utilization[traffic][app][iface_name]['LBU_out'] += int(row[6])
				utilization[traffic][app][iface_name]['LBU_in'] += int(row[5])
		elif iface_name.startswith('2'):
			if int(iface_name[-1]) > args.k / 2:   # Choose down-going interfaces only.
				if (int(row[0]) - first_second) <= args.duration:   # Take the good values only.
					if not utilization[traffic][app].has_key(iface_name):
						utilization[traffic][app][iface_name] = {'LU_out':0, 'LU_in':0, 'LBU_out':0, 'LBU_in':0}
					# if int(row[11]) > 2:
					if row[6] not in ['0', '60']:
						utilization[traffic][app][iface_name]['LU_out'] = 1
					# if int(row[10]) > 2:
					if row[5] not in['0', '60']:
						utilization[traffic][app][iface_name]['LU_in'] = 1
					utilization[traffic][app][iface_name]['LBU_out'] += int(row[6])
					utilization[traffic][app][iface_name]['LBU_in'] += int(row[5])
		else:
			pass

	return utilization

def get_link_utilization_ratio(utilization, traffics, app, num, num_groups):
	value_list = []
	num_list = []
	for traffic in traffics[(num * num_groups): (num * num_groups + num_groups)]:
		num = 0
		for interface in utilization[traffic][app].keys():
			if utilization[traffic][app][interface]['LU_out'] == 1:
				num += 1
			if utilization[traffic][app][interface]['LU_in'] == 1:
				num += 1
		num_list.append(num)
		ratio = float(num) / (len(utilization[traffic][app].keys()) * 2)
		value_list.append(ratio)
	print "num_list:", num_list
	return value_list

def get_value_list_3(utilization, traffic, app):
	"""
		Get link bandwidth utilization ratio.
	"""
	value_list = []
	link_bandwidth_utilization = {}
	utilization_list = []
	for i in np.linspace(0, 1, 101):
		link_bandwidth_utilization[i] = 0

	for interface in utilization[traffic][app].keys():
		ratio_out = float(utilization[traffic][app][interface]['LBU_out'] * 8) / (10 * (10 ** 6) * args.duration)
		ratio_in = float(utilization[traffic][app][interface]['LBU_in'] * 8) / (10 * (10 ** 6) * args.duration)
		utilization_list.append(ratio_out)
		utilization_list.append(ratio_in)

	for ratio in utilization_list:
		for seq in link_bandwidth_utilization.keys():
			if ratio <= seq:
				link_bandwidth_utilization[seq] += 1

	for seq in link_bandwidth_utilization.keys():
		link_bandwidth_utilization[seq] = float(link_bandwidth_utilization[seq]) / len(utilization_list)

	for seq in sorted(link_bandwidth_utilization.keys()):
		value_list.append(link_bandwidth_utilization[seq])

	return value_list

def plot_results():
	"""
		Plot the results:
		1. Plot realtime bisection bandwidth
		2. Plot average bisection bandwidth
		3. Plot accumulated throughput
		4. Plot normalized total throughput

		throughput = {
						'stag_0.5_0.3':
						{
							'realtime_bisection_bw': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'BFlows':x%, 'ECMP':x%, ...}
						},
						'stag_0.6_0.2':
						{
							'realtime_bisection_bw': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'BFlows':x%, 'ECMP':x%, ...}
						},
						...
					}
	"""
	full_bisection_bw = 10.0 * (args.k ** 3 / 4)   # (unit: Mbit/s)
	utmost_throughput = full_bisection_bw * args.duration
	# _traffics = "random stag_0.2_0.3 stag_0.3_0.3 stag_0.4_0.3 stag_0.5_0.3 stag_0.6_0.2 stag_0.7_0.2 stag_0.8_0.1"
	# _traffics = "random1 random2 stag1_0.2_0.3 stag2_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag1_0.5_0.3 stag2_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1"
	_traffics = "random1 random2 random3 stag1_0.1_0.2 stag2_0.1_0.2 stag3_0.1_0.2 stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1"
	traffics = _traffics.split(' ')
	apps = ['BFlows', 'ECMP', 'PureSDN', 'Hedera', 'NonBlocking']
	throughput = {}
	utilization = {}

	for traffic in traffics:
		for app in apps:
			bwmng_file = args.out_dir + '/%s/%s/%s/bwmng.txt' % (args.flows_num_per_host, traffic, app)
			throughput = get_throughput(throughput, traffic, app, bwmng_file)
			utilization = get_utilization(utilization, traffic, app, bwmng_file)

	# 1. Plot realtime throughput.
	item = 'realtime_bisection_bw'
	fig = plt.figure()
	fig.set_size_inches(20, 34)
	num_subplot = len(traffics)
	num_raw = 9
	num_column = num_subplot / num_raw
	NO_subplot = 1
	x = np.arange(0, args.duration + 1)
	for traffic in traffics:
		plt.subplot(num_raw, num_column, NO_subplot)
		y1 = get_value_list_1(throughput, traffic, item, 'BFlows')
		y2 = get_value_list_1(throughput, traffic, item, 'ECMP')
		y3 = get_value_list_1(throughput, traffic, item, 'PureSDN')
		y4 = get_value_list_1(throughput, traffic, item, 'Hedera')
		y5 = get_value_list_1(throughput, traffic, item, 'NonBlocking')
		plt.plot(x, y1, 'r-', linewidth=2, label="BFlows")
		plt.plot(x, y2, 'b-', linewidth=2, label="ECMP")
		plt.plot(x, y3, 'g-', linewidth=2, label="PureSDN")
		plt.plot(x, y4, 'y-', linewidth=2, label="Hedera")
		plt.plot(x, y5, 'k-', linewidth=2, label="NonBlocking")
		plt.title('%s' % traffic, fontsize='xx-large')
		plt.xlabel(u'时间 (s)', fontsize='xx-large', fontproperties=chinese_font)
		plt.xlim(0, args.duration)
		plt.xticks(np.arange(0, args.duration + 1, 10))
		plt.ylabel(u'实时吞吐率\n(Mbps)', fontsize='xx-large', fontproperties=chinese_font)
		plt.ylim(0, full_bisection_bw)
		plt.yticks(np.linspace(0, full_bisection_bw, 11))
		plt.legend(loc='upper right', ncol=len(apps), fontsize='xx-small')
		plt.grid(True)
		NO_subplot += 1
	plt.subplots_adjust(top=0.98, bottom=0.02, left=0.1, right=0.95, hspace=0.3, wspace=0.35)
	plt.savefig(args.out_dir + '/%s-1.realtime_throughput.png' % args.flows_num_per_host)

	# 2. Plot average throughput.
	fig = plt.figure()
	fig.set_size_inches(12, 15)
	num_subplot = 3
	num_raw = 3
	num_column = num_subplot / num_raw
	num_groups = len(traffics) / num_subplot
	num_bar = len(apps)
	NO_subplot = 1
	for num in xrange(num_subplot):
		plt.subplot(num_raw, num_column, NO_subplot)
		ECMP_value_list = get_average_bisection_bw(throughput, traffics, 'ECMP', num, num_groups)
		Hedera_value_list = get_average_bisection_bw(throughput, traffics, 'Hedera', num, num_groups)
		PureSDN_value_list = get_average_bisection_bw(throughput, traffics, 'PureSDN', num, num_groups)
		BFlows_value_list = get_average_bisection_bw(throughput, traffics, 'BFlows', num, num_groups)
		NonBlocking_value_list = get_average_bisection_bw(throughput, traffics, 'NonBlocking', num, num_groups)
		index = np.arange(num_groups) + 0.15
		bar_width = 0.13
		plt.bar(index, ECMP_value_list, bar_width, color='b', label='ECMP')
		plt.bar(index + 1 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
		plt.bar(index + 2 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
		plt.bar(index + 3 * bar_width, BFlows_value_list, bar_width, color='r', label='BFlows')
		plt.bar(index + 4 * bar_width, NonBlocking_value_list, bar_width, color='k', label='NonBlocking')
		plt.xticks(index + num_bar / 2.0 * bar_width, traffics[(num * num_groups): (num * num_groups + num_groups)], fontsize='small')
		plt.ylabel(u'平均吞吐率\n(Mbps)', fontsize='xx-large', fontproperties=chinese_font)
		plt.ylim(0, full_bisection_bw)
		plt.yticks(np.linspace(0, full_bisection_bw, 11))
		plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
		plt.tight_layout()
		plt.grid(axis='y')
		NO_subplot += 1
	plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.95, hspace=0.15, wspace=0.35)
	plt.savefig(args.out_dir + '/%s-2.average_throughput.png' % args.flows_num_per_host)

	# 3. Plot accumulated throughput.
	item = 'accumulated_throughput'
	fig = plt.figure()
	fig.set_size_inches(20, 34)
	num_subplot = len(traffics)
	num_raw = 9
	num_column = num_subplot / num_raw
	NO_subplot = 1
	x = np.arange(0, args.duration + 1)
	for traffic in traffics:
		plt.subplot(num_raw, num_column, NO_subplot)
		y1 = get_value_list_1(throughput, traffic, item, 'BFlows')
		y2 = get_value_list_1(throughput, traffic, item, 'ECMP')
		y3 = get_value_list_1(throughput, traffic, item, 'PureSDN')
		y4 = get_value_list_1(throughput, traffic, item, 'Hedera')
		y5 = get_value_list_1(throughput, traffic, item, 'NonBlocking')
		plt.plot(x, y1, 'r-', linewidth=2, label="BFlows")
		plt.plot(x, y2, 'b-', linewidth=2, label="ECMP")
		plt.plot(x, y3, 'g-', linewidth=2, label="PureSDN")
		plt.plot(x, y4, 'y-', linewidth=2, label="Hedera")
		plt.plot(x, y5, 'k-', linewidth=2, label="NonBlocking")
		plt.title('%s' % traffic, fontsize='xx-large')
		plt.xlabel(u'时间 (s)', fontsize='xx-large', fontproperties=chinese_font)
		plt.xlim(0, args.duration)
		plt.xticks(np.arange(0, args.duration + 1, 10))
		plt.ylabel(u'累计吞吐量\n(Mbit)', fontsize='xx-large', fontproperties=chinese_font)
		plt.ylim(0, utmost_throughput)
		plt.yticks(np.linspace(0, utmost_throughput, 11))
		plt.legend(loc='upper left', fontsize='large')
		plt.grid(True)
		NO_subplot += 1
	plt.subplots_adjust(top=0.98, bottom=0.02, left=0.1, right=0.95, hspace=0.3, wspace=0.35)
	plt.savefig(args.out_dir + '/%s-3.accumulated_throughput.png' % args.flows_num_per_host)

	# 4. Plot normalized total throughput.
	item = 'normalized_total_throughput'
	fig = plt.figure()
	fig.set_size_inches(12, 15)
	num_subplot = 3
	num_raw = 3
	num_column = num_subplot / num_raw
	num_groups = len(traffics) / num_subplot
	num_bar = len(apps)
	NO_subplot = 1
	for num in xrange(num_subplot):
		plt.subplot(num_raw, num_column, NO_subplot)
		ECMP_value_list = get_value_list_2(throughput, traffics, item, 'ECMP', num, num_groups)
		Hedera_value_list = get_value_list_2(throughput, traffics, item, 'Hedera', num, num_groups)
		PureSDN_value_list = get_value_list_2(throughput, traffics, item, 'PureSDN', num, num_groups)
		BFlows_value_list = get_value_list_2(throughput, traffics, item, 'BFlows', num, num_groups)
		NonBlocking_value_list = get_value_list_2(throughput, traffics, item, 'NonBlocking', num, num_groups)
		index = np.arange(num_groups) + 0.15
		bar_width = 0.13
		plt.bar(index, ECMP_value_list, bar_width, color='b', label='ECMP')
		plt.bar(index + 1 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
		plt.bar(index + 2 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
		plt.bar(index + 3 * bar_width, BFlows_value_list, bar_width, color='r', label='BFlows')
		plt.bar(index + 4 * bar_width, NonBlocking_value_list, bar_width, color='k', label='NonBlocking')
		plt.xticks(index + num_bar / 2.0 * bar_width, traffics[(num * num_groups): (num * num_groups + num_groups)], fontsize='small')
		plt.ylabel(u'标准化总吞吐量\n', fontsize='xx-large', fontproperties=chinese_font)
		plt.ylim(0, 1)
		plt.yticks(np.linspace(0, 1, 11))
		plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
		plt.tight_layout()
		plt.grid(axis='y')
		NO_subplot += 1
	plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.95, hspace=0.15, wspace=0.35)
	plt.savefig(args.out_dir + '/%s-4.normalized_total_throughput.png' % args.flows_num_per_host)

	# 5. Plot link utilization ratio.
	fig = plt.figure()
	fig.set_size_inches(12, 15)
	num_subplot = 3
	num_raw = 3
	num_column = num_subplot / num_raw
	num_groups = len(traffics) / num_subplot
	num_bar = len(apps) - 1
	NO_subplot = 1
	for num in xrange(num_subplot):
		plt.subplot(num_raw, num_column, NO_subplot)
		ECMP_value_list = get_link_utilization_ratio(utilization, traffics, 'ECMP', num, num_groups)
		Hedera_value_list = get_link_utilization_ratio(utilization, traffics, 'Hedera', num, num_groups)
		PureSDN_value_list = get_link_utilization_ratio(utilization, traffics, 'PureSDN', num, num_groups)
		BFlows_value_list = get_link_utilization_ratio(utilization, traffics, 'BFlows', num, num_groups)
		index = np.arange(num_groups) + 0.15
		bar_width = 0.15
		plt.bar(index, ECMP_value_list, bar_width, color='b', label='ECMP')
		plt.bar(index + 1 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
		plt.bar(index + 2 * bar_width, PureSDN_value_list, bar_width, color='g', label='PureSDN')
		plt.bar(index + 3 * bar_width, BFlows_value_list, bar_width, color='r', label='BFlows')
		plt.xticks(index + num_bar / 2.0 * bar_width, traffics[(num * num_groups): (num * num_groups + num_groups)], fontsize='small')
		plt.ylabel(u'链路利用率\n', fontsize='xx-large', fontproperties=chinese_font)
		plt.ylim(0, 1)
		plt.yticks(np.linspace(0, 1, 11))
		plt.legend(loc='lower right', ncol=len(apps)-1, fontsize='small')
		plt.tight_layout()
		plt.grid(axis='y')
		NO_subplot += 1
	plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.95, hspace=0.15, wspace=0.35)
	plt.savefig(args.out_dir + '/%s-5.link_utilization_ratio.png' % args.flows_num_per_host)

	# 6. Plot link bandwidth utilization ratio.
	fig = plt.figure()
	fig.set_size_inches(20, 34)
	num_subplot = len(traffics)
	num_raw = 9
	num_column = num_subplot / num_raw
	NO_subplot = 1
	x = np.linspace(0, 1, 101)
	for traffic in traffics:
		plt.subplot(num_raw, num_column, NO_subplot)
		y1 = get_value_list_3(utilization, traffic, 'ECMP')
		y2 = get_value_list_3(utilization, traffic, 'Hedera')
		y3 = get_value_list_3(utilization, traffic, 'PureSDN')
		y4 = get_value_list_3(utilization, traffic, 'BFlows')
		print "y1[10]:", y1[10]
		print "y2[10]:", y2[10]
		print "y3[10]:", y3[10]
		print "y4[10]:", y4[10]
		plt.plot(x, y1, 'b-', linewidth=2, label="ECMP")
		plt.plot(x, y2, 'y-', linewidth=2, label="Hedera")
		plt.plot(x, y3, 'g-', linewidth=2, label="PureSDN")
		plt.plot(x, y4, 'r-', linewidth=2, label="BFlows")
		plt.title('%s' % traffic, fontsize='xx-large')
		plt.xlabel(u'链路带宽利用率', fontsize='xx-large', fontproperties=chinese_font)
		plt.xlim(0, 1)
		plt.xticks(np.linspace(0, 1, 11))
		plt.ylabel(u'链路带宽利用率\n累积分布函数', fontsize='xx-large', fontproperties=chinese_font)
		plt.ylim(0, 1)
		plt.yticks(np.linspace(0, 1, 11))
		plt.legend(loc='lower right', ncol=len(apps)-1, fontsize='xx-small')
		plt.grid(True)
		NO_subplot += 1
	plt.subplots_adjust(top=0.98, bottom=0.02, left=0.1, right=0.95, hspace=0.3, wspace=0.35)
	plt.savefig(args.out_dir + '/%s-6.link_bandwidth_utilization_ratio.png' % args.flows_num_per_host)


if __name__ == '__main__':
	plot_results()
