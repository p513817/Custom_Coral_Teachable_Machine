#!/bin/bash
	echo "start!"
	#sleep 3
	source ~/.profile
	workon tflite
	cd /home/pi/Desktop/project-teachable
	python test_v2.py
	$SHELL 