#! /bin/python3

__programName__ = "Find Files in CSV for Chloe"
__author__ = "Josh Unwin"
__description__ = "Takes a source CSV and a destination TOC and verifies it can find each file in the source"
__version__ = "0.1"


# USAGE:
# python3 find_files_in_csv.py /path/to/source/mhl-to-csv/csv_file.csv /path/to/destination/text/file.csv

# NOTES:
# This expects the first column in source CSV to be the filepath (as per mhl_to_csv export).
# If using mhl_to_csv exported csv, use --skip-summarise-img-seq so all files are included.

import os
import csv
import argparse
from datetime import datetime
import subprocess
import re

PATH_SPLIT_STRING = 'CHLOE_S1/' # This string will be used to split the filepath, anything to the right of this will be treated as the file
currentTime = datetime.now().strftime('%Y%m%d_%H%M%S')
new_csv_file_name = ''
save_location = os.path.expanduser("~/Desktop/CSV_Match_Exports/")

def create_save_directory():
    folderChecker = os.path.isdir(save_location)
    if folderChecker == False:
        os.mkdir(save_location)

def copy_csv_content_to_clipboard(csv_path):
    csv = open(csv_path, "r")
    subprocess.run("pbcopy", universal_newlines=True, input=csv.read())
    print("CSV contents has been copied to the clipboard.\n")

# Args Parse Method, allows user input and provides feedback.
def args_parse():
    parser = argparse.ArgumentParser()

    parser.add_argument('source_csv', help="The source CSV")
    parser.add_argument('destination_file', help="The destination txt file (csv, ALE, txt etc)")

    parsed_arguments = parser.parse_args()

    return parsed_arguments

def main():
    global new_csv_file_name
    print("Finding matches in destination txt for files in source csv...")
    create_save_directory()
    source_file_path_column = 0
    args = args_parse()
    found_list = []
    unfound_list = []
    destination_file = open(args.destination_file)
    destination_contents = destination_file.read()
    line_count = 0
    new_csv_file_name = f'{os.path.basename(args.destination_file).split(".")[0]}-MATCH_CHECK'


    with open(args.source_csv, 'r') as source:
        for line in csv.reader(source):
            try:
                filepath = line[source_file_path_column].split(PATH_SPLIT_STRING)[1] # Split the filepath at CHLOE_S1 to get relative filepath
                matched_loc = destination_contents.find(filepath) # Returns the char position of the found string
                search_area = destination_contents[matched_loc-1000:matched_loc+1000] # make a substring of 2000 chars around the found string for regex parsing
                matched_line = re.search(f'.*{filepath}.*', search_area).group() # Extract the line from the substring (substring is for performance)
                found_list.append(["FOUND", filepath, matched_line])
            except:
                unfound_list.append(["MISSING", filepath])
            if str(line_count)[-3:] == "500":
                print("Progress: line " + str(line_count))
            line_count += 1

    print("Creating MATCH csv...")
    with open(save_location + new_csv_file_name + '.csv', 'w') as new_file:
        fieldnames = ['Status', 'Source File', 'Matched Line']
        csv_writer = csv.writer(new_file)
        csv_writer.writerow(fieldnames)

        for file in found_list:
            csv_writer.writerow(file)
        for file in unfound_list:
            csv_writer.writerow(file)


    destination_file.close()
    copy_csv_content_to_clipboard(save_location + new_csv_file_name + '.csv')
    print(f"Finished! CSV saved to {save_location}")


# Runs when opened from command line
if __name__ == '__main__':
    main()
