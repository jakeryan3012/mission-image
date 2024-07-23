#!/bin/bash

# This will export csv's of an AWS output of each subdirectory in the directory you pass.
# Requires AWS CLI to be installed and setup.
# Provide 2 arguments, 1: The path in AWS you want to extract. 2. The destination for csvs on your machine.

path=$1
output_path=$2

aws s3 ls $path | \
while read line ; \
	do dir=$(echo $line | awk '{print $2}') && \
	echo $dir
	aws s3 ls "${path}${dir}" --recursive 2>&1 | tee "${output_path}/${dir%?}.csv"
done