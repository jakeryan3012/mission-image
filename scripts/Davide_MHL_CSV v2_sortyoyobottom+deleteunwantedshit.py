#!/usr/bin/env python3

__programName__ = "MHL to CSV Converter"
__author__ = "Josh Unwin/Gary Palmer"
__version__ = "1.3"

import csv
import hashlib
import re
import pathlib
import xxhash
import os
import sys
import argparse
import subprocess
from datetime import datetime
import operator
from operator import itemgetter
import xml.etree.ElementTree as et

softwareName = ''
currentTime = datetime.now().strftime('%Y%m%d_%H%M%S')
save_location = os.path.expanduser("~/Desktop/MHL_Exports/")
new_csv_file_name = 'TEST'
sort_enabled = False
skip_summarise_img_seq = False
use_ignored_extensions = True
extensions_to_ignore = ['.pdf', '.bin', '.csv', '.json', '.metadata_never_index', '.xml', '.fmtsig_sounddev', '.cdl', '.cube', '.ale', '.drp', '.psla', '.csv']


class FileHash:
    file = ''
    size = ''
    xxhash64be = ''
    md5 = ''
    hashdate = ''        


# This function is just for troubleshooting, it prints the list of hashes.
def printHashList(hashlist):
    for hash in hashlist:
        print(hash.file + "," + hash.size + "," + hash.xxhash64be + "," + hash.md5 + "," + hash.hashdate)



# checks for dir, makes list of mhl files if so, else returns input list
def get_mhl_file_paths(input_paths):
    mhl_file_list = []

    for mhl in input_paths:
        # print(mhl)
        if os.path.isdir(mhl):
            for file in os.listdir(mhl):        # it checks whether the path is a directory using the os.path.isdir() function.
                if not file.startswith("."):
                    if file.endswith(".mhl"):
                        mhl_file_list.append("{}{}".format(mhl, file))
                        # If it is a directory, the function iterates over each file in the directory (excluding hidden files that start with a .) Then the append function appends the full path of the file to the mhl_file_list using string formatting
        elif mhl.endswith(".mhl"):
        #  If the input file path (mhl) is not a directory but ends with ".mhl", the function appends the full path of the file to the mhl_file_list
            mhl_file_list.append(mhl)

    return mhl_file_list
    #returns the mhl_file_list, which is a list of paths to ".mhl" files (either standalone files or those within directories).



#This loop iterates over each ".mhl" file path in the input mhl_file_list. 
#For each file path (mhl), it calls the parse_mhl() function on that file, and return a list of hash objects. 

def create_hash_list(mhl_file_list):
    combinedHashesList = []

    for mhl in mhl_file_list:
        combinedHashesList += parse_mhl(mhl)
        #The += operator appends the resulting list of hash objects to the combinedHashesList
        #This if statement checks whether a global variable sort_enabled is True. 
        #If it is, the function sorts the list of hash objects in combinedHashesList by the file attribute using the sorted()

    if sort_enabled:
        combinedHashesList = sorted(combinedHashesList, key=lambda k: k['file'])
        
  

    return combinedHashesList


# Takes the list of MHL's from argparse and puts each one through the parse_mhl function.
# It puts the result from the parse_mhl into the variable combinedHashesList (+= concatonates and saves).
# It then runs the full combinedHashesList through the csvGenerator.



# This function takes in a list of hash objects and initializes two counters: processed_rows_count and mhls_skipped.
def create_csv(hashes):
    processed_rows_count = 0   
    mhls_skipped = 0

    
    

# opens a new file for writing
    with open(save_location + new_csv_file_name + '.csv', 'w') as new_file:
        fieldnames = ['File', 'Size', 'xxHash', 'MD5', 'Hash Date']
        # It then creates a csv.DictWriter object called csv_writer that writes to the newly created file.

        csv_writer = csv.DictWriter(new_file, fieldnames=fieldnames, extrasaction='ignore')
        
        #If use_header is True, then the function writes the first row to the CSV file using the writeheader() method of the csv.DictWriter object.

        if use_header:
            csv_writer.writeheader()
            
# hash is used to iterate over each item in the hashes list, 
# and the information contained in each HashRecord instance is written to a new row in the CSV file

        for hash in hashes:
            if '.mhl' in hash.file: # If the file does have an .mhl extension, it means that it is a Metadata Hash List (MHL) file and not an actual file that needs to be included in the CSV file. Therefore, the code skips the current HashRecord instance and moves on to the next one, without writing it to the CSV file.
                mhls_skipped += 1
                pass
            elif "DOCUMENTATION" in hash.file or "TRANSCODES" in hash.file or "_sounddev" in hash.file or "MEZZANINE" in hash.file or "RESUPPLY" in hash.file or "RENAME" in hash.file:
                pass
            else:
                processed_rows_count += 1
                csv_writer.writerow({'File': hash.file, 'Size': hash.size, 'xxHash': hash.xxhash64be, 'MD5': hash.md5,
                                     'Hash Date': hash.hashdate})

    print(
        f"\nNumber of .MHL file records inside MHL files is: {mhls_skipped} these are not necessary to check and have been skipped.")
    print(
        f"\nMHL to CSV Converter {__version__} - {__author__} \nYour MHL's have been converted to a csv called " + new_csv_file_name +
        ".csv. It has been saved to /Desktop/MHL_Exports/ \n\nNumber of files added to CSV: " + str(
            processed_rows_count) + "\n")


# extract the file hash information from an XML element containing the hash information in the version 1 format. This function takes a single argument, hash, which is the XML element containing the hash information
def parse_v1_hash(hash):
    hash_object = FileHash()
    for element in hash:
        if element.tag == 'file':
            hash_object.file = element.text
        if element.tag == 'size':
            hash_object.size = element.text
        if element.tag == 'xxhash64be':
            hash_object.xxhash64be = element.text
        if element.tag == 'md5':
            hash_object.md5 = element.text
        if element.tag == 'hashdate':
            hash_object.hashdate = element.text
    
    return hash_object

def parse_v2_hash(hash):
    hash_object = FileHash()
    for element in hash:
        if 'path' in element.tag:
            hash_object.file = element.text
            try:
                hash_object.size = element.attrib['size']
            except:
                pass
        if 'xxh64' in element.tag:
            hash_object.xxhash64be = element.text
            try:
                hash_object.hashdate = element.attrib['hashdate']
            except:
                pass
        if 'md5' in element.tag:
            hash_object.md5 = element.text
    
    return hash_object


# Imports each MHL file, parse it and get the root list of items.
# The function then loops through the root element's child nodes and extracts the hash information for each file in the MHL. 
# It optionally ignores files with extensions in the extensions_to_ignore list. Finally, it sorts the hash list by filename and returns it.

def parse_mhl(mhl_file):
    mhl_file = et.parse(mhl_file)
    root = mhl_file.getroot()
    mhl_version = float(root.attrib["version"])
    hash_list = []
    global softwareName
    global use_ignored_extensions

    for child in root:
        if child.tag == 'creatorinfo':
            for element in child:
                if element.tag == 'tool':
                    if 'mhl ver' in element.text.lower():
                        softwareName = 'Silverstack'
                    if 'yoyotta' in element.text.lower():
                        softwareName = 'YoYotta'
                    if 'arri' in element.text.lower():
                        softwareName = 'Arri'
    
    parent_node_for_hashes = root
    hash_parser = parse_v1_hash
    if mhl_version >= 2:
        hash_parser = parse_v2_hash
        for index, child in enumerate(root):
            if 'hashes' in child.tag:
                parent_node_for_hashes = root[index]

    for child in parent_node_for_hashes:
        if child.tag == 'hash':
            hash = hash_parser(child)
            if use_ignored_extensions:
                if not pathlib.Path(hash.file).suffix.lower() in extensions_to_ignore:
                    hash_list.append(hash)
            else:
                hash_list.append(hash)

    # Sort the hash_list by file name, keeping the rows that do not have "CAMERA_MASTER" or "SOUND_RUSHES" text in hash.file at the top of the list
    hash_list.sort(key=lambda x: x.file)
    return hash_list
    

# Args Parse Method, allows user input and provides feedback.
#The required argument is input_paths: a list of MHL files or directories containing MHL files that the script will parse.
def args_parse():
    global sort_enabled
    global use_header
    global skip_summarise_img_seq
    global use_ignored_extensions
    parser = argparse.ArgumentParser()

    # parser.add_argument("mhl_file", help="The MHL you wish to use")
    parser.add_argument('-s', '--sort', action='store_true',
                        help="Use if you want the script to attempt to sort the MHLs")
    parser.add_argument('--header', action='store_true', help="Optionally include the header line")
    parser.add_argument('--skip-summarise-img-seq', action='store_true', help="Optionally include the header line")
    parser.add_argument('--ignore-sidecar-files', '-i', action='store_true', help="Optionally ignore files with extensions in extensions_to_ignore")
    parser.add_argument('input_paths', nargs='+', help="The MHLs or directory of MHLs you wish to use")

    parsed_arguments = parser.parse_args()

    sort_enabled = parsed_arguments.sort
    use_header = parsed_arguments.header
    skip_summarise_img_seq = parsed_arguments.skip_summarise_img_seq
    use_ignored_extensions = parsed_arguments.ignore_sidecar_files
    
    

    return parsed_arguments.input_paths


def create_save_directory():
    folderChecker = os.path.isdir(save_location)
    if folderChecker == False:
        os.mkdir(save_location)


def copy_csv_content_to_clipboard(csv_path):
    csv = open(csv_path, "r")
    subprocess.run("pbcopy", universal_newlines=True, input=csv.read())
    print("CSV contents has been copied to the clipboard.\n")

# This function takes a list of frames and combines them into a single clip. 
def summarise_img_seq(frame_combiner):     
    xxhash64 = xxhash.xxh64()
    xxhash64_output = ""
    md5 = hashlib.md5()
    md5_output = ""
    size = 0
    file_ext = frame_combiner[0][0].split(".")[-1]
    if file_ext == "arx" or file_ext == "ari":
        clip_name_no_frames = frame_combiner[0][0].split(".")[:-1][0]
        first_frame_counter = frame_combiner[0][0].split(".")[-2]
        last_frame_counter = frame_combiner[-1][0].split(".")[-2]
        clip_name = f'{clip_name_no_frames}.{first_frame_counter}-{last_frame_counter}.{file_ext}'
    elif file_ext == "dng":
        dng_pattern = r'R\d\d\d\d\d.dng'
        dng_regex = re.compile(dng_pattern)
        regex_start_pos = dng_regex.search(frame_combiner[0][0]).regs[0][0]
        regex_end_pos = dng_regex.search(frame_combiner[0][0]).regs[0][1]
        clip_name_no_frames = f"{frame_combiner[0][0][:regex_start_pos]}"
        first_frame_counter = frame_combiner[0][0][regex_start_pos:regex_end_pos-4]
        last_frame_counter = frame_combiner[-1][0][regex_start_pos:regex_end_pos-4]
        clip_name = f'{clip_name_no_frames}{first_frame_counter}-{last_frame_counter}.{file_ext}'

    date = frame_combiner[-1][4]
    for line in frame_combiner:
        xxhash_field = line[2].lower()
        md5_field = line[3].lower()
        if xxhash_field:
            xxhash64.update(xxhash_field)
            xxhash64_output = xxhash64.hexdigest()
        if md5_field:
            md5.update(md5_field.encode('utf-8'))
            md5_output = md5.hexdigest()
        size += int(line[1])
    return [clip_name, size, xxhash64_output, md5_output, date]

# Checks if a file name is a DNG file and returns a boolean indicating whether it is, and the prefix of the file name before the frame number
def is_frame_dng(file_name):
    dng_pattern = r'R\d\d\d\d\d.dng'
    dng_regex = re.compile(dng_pattern)
    is_dng = dng_regex.findall(file_name)
    if is_dng:
        regex_start_pos = dng_regex.search(file_name).regs[0][0]
        return True, file_name[:regex_start_pos]
    else:
        return None, None

def img_seq_checksums_to_clip_checksums(csv_path):
    print("Summarising image sequences (for .ari, .arx or .dng media)...")
    with open(csv_path, 'r') as data:
        last_clip_name = ""
        output_csv = []
        frame_combiner = []
        for line in csv.reader(data):
            filename_with_path, file_ext = os.path.splitext(line[0])
            try:
                frame_counter_when_img_seq = filename_with_path.split(".")[-1]
            except:
                frame_counter_when_img_seq = ''
            is_dng_frame, dng_frame_name = is_frame_dng(line[0])
            if is_dng_frame:
                cur_clip_name = dng_frame_name
            else:
                cur_clip_name = line[0].split(".")[0]
            if frame_counter_when_img_seq.isdigit() and (file_ext == ".arx" or file_ext == ".ari") or is_dng_frame:
                # initialise last_clip_name
                if not last_clip_name:
                    last_clip_name = cur_clip_name
                # if continuing frames
                if cur_clip_name == last_clip_name:
                    frame_combiner.append(line)
                # if starting new img seq
                else:
                    # if existing append that first
                    if frame_combiner:
                        clip_summarised = summarise_img_seq(frame_combiner)
                        output_csv.append(clip_summarised)
                        frame_combiner = []
                    frame_combiner.append(line)
                    last_clip_name = cur_clip_name
            # append remaining seq if next element is not img seq
            else:
                if frame_combiner:
                    clip_summarised = summarise_img_seq(frame_combiner)
                    output_csv.append(clip_summarised)
                    frame_combiner = []
                output_csv.append(line)
        if frame_combiner:
            clip_summarised = summarise_img_seq(frame_combiner)
            output_csv.append(clip_summarised)
            frame_combiner = []

    with open(save_location + new_csv_file_name + '.csv', 'w') as new_file:
        fieldnames = ['File', 'Size', 'xxHash', 'MD5', 'Hash Date']

        csv_writer = csv.DictWriter(new_file, fieldnames=fieldnames, extrasaction='ignore')

        if use_header:
            csv_writer.writeheader()
        for line in output_csv:
            csv_writer.writerow({'File': str(line[0]), 'Size': line[1], 'xxHash': line[2], 'MD5': line[3],
                                 'Hash Date': line[4]})
    print("Done summarising!")
    
    
 # This function moves all the rows that have 'CAMERA_MASTER' or SOUND_RUSHES' inside the hash_obj.file to the bottom
def sort_hash_list(hash_list):
    camera_sound_hashes = []
    other_hashes = []
    
    
    
    for hash_obj in hash_list:
        if 'CAMERA_MASTER' in hash_obj.file or 'SOUND_RUSHES' in hash_obj.file:
            camera_sound_hashes.append(hash_obj)
        elif 'DOCUMENTATION' not in hash_obj.file and 'TRANSCODES' not in hash_obj.file and '_sounddev' not in hash_obj.file and 'MEZZANINE' not in hash_obj.file and 'RESUPPLY' not in hash_obj.file and 'RENAME' not in hash_obj.file:
        
            other_hashes.append(hash_obj)
    
    
    
    
    # Sort the camera and sound hashes to the bottom
    camera_sound_hashes.sort(key=lambda x: x.file)
    other_hashes.sort(key=lambda x: x.file)
    
    # Combine the sorted lists
    sorted_hash_list = other_hashes + camera_sound_hashes
    
    # Print the sorted list
    for hash_obj in sorted_hash_list:
        print(hash_obj.file)
    
    return sorted_hash_list
    
    
def remove_duplicates(hashes):
    unique_hashes = {}
    for h in hashes:
        if h.file not in unique_hashes:
            unique_hashes[h.file] = h
        else:
            print(f"Removed duplicate file: {h.file}")
    return list(unique_hashes.values())



def main():
    global new_csv_file_name
    global skip_summarise_img_seq
    print("Converting MHL to csv...")
    create_save_directory()
    input_paths = args_parse()
    mhl_file_list = get_mhl_file_paths(input_paths)
    new_csv_file_name = 'TEST'
    hashes = create_hash_list(mhl_file_list)
    hashes = remove_duplicates(hashes)
    sorted_hashes = sort_hash_list(hashes)  # Sort the hash list
    create_csv(sorted_hashes)
    print("Done creating CSV!")
    if skip_summarise_img_seq:
        print("Skipping summarise image sequences")
    else:
        img_seq_checksums_to_clip_checksums(save_location + new_csv_file_name + '.csv')
    copy_csv_content_to_clipboard(save_location + new_csv_file_name + '.csv')




# Runs when opened from command line
if __name__ == '__main__':
    main()