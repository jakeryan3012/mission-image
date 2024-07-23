#!/usr/bin/env python3

__programName__ = "MHL to CSV Converter"
__author__ = "Josh Unwin/Gary Palmer"
__version__ = "1.1"

import csv
import hashlib
import re

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
new_csv_file_name = ''
sort_enabled = False
skip_summarise_img_seq = False


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
            for file in os.listdir(mhl):
                if not file.startswith("."):
                    if file.endswith(".mhl"):
                        mhl_file_list.append("{}{}".format(mhl, file))
        elif mhl.endswith(".mhl"):
            mhl_file_list.append(mhl)

    return mhl_file_list


def create_hash_list(mhl_file_list):
    combinedHashesList = []

    for mhl in mhl_file_list:
        combinedHashesList += parse_mhl(mhl)

    if sort_enabled:
        combinedHashesList = sorted(combinedHashesList, key=lambda k: k['file'])

    return combinedHashesList


# Takes the list of MHL's from argparse and puts each one through the parse_mhl function.
# It puts the result from the parse_mhl into the variable combinedHashesList (+= concatonates and saves).
# It then runs the full combinedHashesList through the csvGenerator.
def create_csv(hashes):
    processed_rows_count = 0
    mhls_skipped = 0

    with open(save_location + new_csv_file_name + '.csv', 'w') as new_file:
        fieldnames = ['File', 'Size', 'xxHash', 'MD5', 'Hash Date']

        csv_writer = csv.DictWriter(new_file, fieldnames=fieldnames, extrasaction='ignore')

        if use_header:
            csv_writer.writeheader()

        for hash in hashes:
            if '.mhl' in hash.file:
                mhls_skipped += 1
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



# Imports each MHL file, parse it and get the root list of items.
def parse_mhl(mhl_file):
    mhl_file = et.parse(mhl_file)
    root = mhl_file.getroot()
    i = 0
    total = 0
    global softwareName

    for child in root:
        if child.tag == 'creatorinfo':
            for element in child:
                if element.tag == 'tool':
                    if 'mhl ver' in element.text:
                        softwareName = 'Silverstack'
                    if 'YoYotta' in element.text:
                        softwareName = 'YoYotta'

    # Totals the number of hashes in the root, then creates an empty instance of the
    # FileHash class for each hash (stored in a list called hashList)
    for child in root:
        if child.tag == 'hash':
            total += 1
    hashList = [FileHash() for count in range(total)]

    # Searches through the root, finds the relevant tags and adds their contents to the relevant arrays created above.
    for child in root:
        if child.tag == 'hash':
            for element in child:
                if element.tag == 'file':
                    hashList[i].file = element.text
                if element.tag == 'size':
                    hashList[i].size = element.text
                if element.tag == 'xxhash64be':
                    hashList[i].xxhash64be = element.text
                if element.tag == 'md5':
                    hashList[i].md5 = element.text
                if element.tag == 'hashdate':
                    hashList[i].hashdate = element.text
            i += 1
    hashList.sort(key=lambda x: x.file)
    return hashList
    

# Args Parse Method, allows user input and provides feedback.
def args_parse():
    global sort_enabled
    global use_header
    global skip_summarise_img_seq
    parser = argparse.ArgumentParser()

    # parser.add_argument("mhl_file", help="The MHL you wish to use")
    parser.add_argument('-s', '--sort', action='store_true',
                        help="Use if you want the script to attempt to sort the MHLs")
    parser.add_argument('--header', action='store_true', help="Optionally include the header line")
    parser.add_argument('--skip-summarise-img-seq', action='store_true', help="Optionally include the header line")
    parser.add_argument('input_paths', nargs='+', help="The MHLs or directory of MHLs you wish to use")

    parsed_arguments = parser.parse_args()

    sort_enabled = parsed_arguments.sort
    use_header = parsed_arguments.header
    skip_summarise_img_seq = parsed_arguments.skip_summarise_img_seq

    return parsed_arguments.input_paths


def create_save_directory():
    folderChecker = os.path.isdir(save_location)
    if folderChecker == False:
        os.mkdir(save_location)


def copy_csv_content_to_clipboard(csv_path):
    csv = open(csv_path, "r")
    subprocess.run("pbcopy", universal_newlines=True, input=csv.read())
    print("CSV contents has been copied to the clipboard.\n")


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


def main():
    global new_csv_file_name
    global skip_summarise_img_seq
    print(skip_summarise_img_seq)
    print("Converting MHL to csv...")
    create_save_directory()
    input_paths = args_parse()
    mhl_file_list = get_mhl_file_paths(input_paths)
    new_csv_file_name = "_".join(map(lambda x: os.path.basename(x).split("_")[0].split(".")[0], mhl_file_list))
    hashes = create_hash_list(mhl_file_list)
    create_csv(hashes)
    print("Done creating CSV!")
    if skip_summarise_img_seq:
        print("Skipping summarise image sequences")
    else:
        img_seq_checksums_to_clip_checksums(save_location + new_csv_file_name + '.csv')
    copy_csv_content_to_clipboard(save_location + new_csv_file_name + '.csv')


# Runs when opened from command line
if __name__ == '__main__':
    main()
