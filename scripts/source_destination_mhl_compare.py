#!/usr/bin/env python3

__program_name__ = "Source/Destination MHL Check"
__description__ = "Goes through a list of MHLs, for each media hash record, it tries to find a match in the destination MHL and checks the checksum matches. Exports a CSV report."
__author__ = "Josh Unwin/Gary Palmer"
__version__ = "0.8"

import csv
import hashlib
import re
import sys
import xxhash
import os
import argparse
import subprocess
import xml.etree.ElementTree as et

total_source_file_count = 0
total_touched_files = 0
USE_MD5 = False
SAVE_LOCATION = os.path.expanduser("~/Desktop/MHL_Verification_Reports/")
SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM = False
output_csv_matched_list = []
output_csv_unfound_list = []
output_csv_mismatched_list = []
previous_img_sequence_hash = None
frames_in_src_img_seq_clip = []
frames_in_dest_img_seq_clip = []
destination_toc_length = 0
five_percent_toc_length = 0
last_matched_location = 0

BLUE = "\033[0;34m"
DEFAULT = "\033[0m"
YELLOW = "\033[0;33m"
GREEN = '\033[1;32m'
RED = '\033[1;31m'
ORANGE = '\033[0;31m'

class FileHash:
    def __init__(self, file="", size="", xxhash64be="", md5="", hashdate=""):
        self.file = file
        self.size = size
        self.xxhash64be = xxhash64be
        self.md5 = md5
        self.hashdate = hashdate
    
    def is_image_seq(self):
        return self.file.endswith(('.ari', '.arx', '.dng'))

    def file_extension(self):
        filename, file_extension = os.path.splitext(self.file)
        return file_extension

    def clipname(self):
        if self.file_extension() == '.dng':
            dng_pattern = r'R\d\d\d\d\d.dng'
            dng_regex = re.compile(dng_pattern)
            regex_start_pos = dng_regex.search(self.file).regs[0][0]
            return self.file[:regex_start_pos]
        else:    
            return self.file.split(".")[0]

    def frame_number(self):
        if self.file_extension() == '.dng':
            dng_pattern = r'R\d\d\d\d\d.dng'
            dng_regex = re.compile(dng_pattern)
            regex_start_pos = dng_regex.search(self.file).regs[0][0]
            regex_end_pos = dng_regex.search(self.file).regs[0][-1]
            return self.file[regex_start_pos:regex_end_pos-4]
        else:
            return self.file.split(".")[-2]

def args_parse(argv):
    global USE_MD5
    global SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM
    global SAVE_LOCATION
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output-dir', help="The directory to save the output CSV file to.", default=SAVE_LOCATION)
    parser.add_argument('-s', '--sources', nargs='+', help="One or more source MHLs (eg: such as MHLs from Silverstack)")
    parser.add_argument('-d', '--destination', help="The destination mhl you wish to use (eg: such as MHLs from YoYotta)")
    parser.add_argument('--skip-summarise-img-seq', action='store_true', help="Include to skip the combine image seq checksums step")
    checksum_type_group = parser.add_mutually_exclusive_group()
    checksum_type_group.add_argument('--xxhash', help="Use xxHash checksum (default)")
    checksum_type_group.add_argument('--md5', action='store_true', help="Use md5 checksum")
    parsed_arguments = parser.parse_args(argv[1:]) # skip the first argument (the script name)
    USE_MD5 = parsed_arguments.md5
    SAVE_LOCATION = parsed_arguments.output_dir
    SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM = parsed_arguments.skip_summarise_img_seq

    return parsed_arguments


def create_hash_object(mhl_hash):
    hash = FileHash()
    for element in mhl_hash:
        if element.tag == 'file':
            hash.file = element.text
        if element.tag == 'size':
            hash.size = element.text
        if element.tag == 'xxhash64be':
            hash.xxhash64be = element.text
        if element.tag == 'md5':
            hash.md5 = element.text
        if element.tag == 'hashdate':
            hash.hashdate = element.text
    return hash


def smarter_find(search_term, content):
    global total_source_file_count
    global destination_toc_length
    global five_percent_toc_length
    global last_matched_location

    matched_location = content.find(search_term, last_matched_location)

    if matched_location == -1:
        matched_location = content.find(search_term, max(0, last_matched_location - five_percent_toc_length))
    if matched_location == -1:
        matched_location = content.find(search_term)
    last_matched_location = matched_location
    if matched_location == -1:
        print(f"\t{RED}Could not find {search_term} in destination MHL{YELLOW}")
    return matched_location


def find_matching_hash(filename, destination_toc):
    try:
        # matched_location = destination_toc.find(filename)
        matched_location = smarter_find(filename, destination_toc)
        if matched_location == -1:
            return None
        # make an extract_area substring of 2000 chars around the found string for regex parsing. 
        # the max()functions ensure minimum of 0 and 1000 on each side respectively (negative number breaks it)
        extract_area = destination_toc[max(0,matched_location-1000):max(1000,matched_location+1000)]
        matched_hash_string = re.search(f'(?s)<hash>(?:(?!<hash>).)*?{re.escape(filename)}(?:(?!</hash>).)*?</hash>', extract_area).group()
        parsed_match = et.ElementTree(et.fromstring(matched_hash_string))
        return create_hash_object(parsed_match.getroot())
    except:
        print(f"\t{RED}Found match in destination MHL for {filename}, but could not extract the hash. {DEFAULT}")
        return None


def generate_output_csv_line(status, src_hash, dest_hash):
    if dest_hash:
        src_rows = [src_hash.file, src_hash.size, src_hash.xxhash64be, src_hash.md5, src_hash.hashdate]
        dest_rows = [dest_hash.file, dest_hash.size, dest_hash.xxhash64be, dest_hash.md5, dest_hash.hashdate]
        return [status] + src_rows + dest_rows
    else:
        return [status, src_hash.file, src_hash.size, src_hash.xxhash64be, src_hash.md5, src_hash.hashdate]


def generate_hash_file_name(first_clip, last_clip):
    if first_clip.file_extension() == '.dng':
        return f'{first_clip.clipname()}{first_clip.frame_number()}-{last_clip.frame_number()}{first_clip.file_extension()}'
    else:
        return f'{first_clip.clipname()}.{first_clip.frame_number()}-{last_clip.frame_number()}{first_clip.file_extension()}'
        


def generate_img_seq_clip_hash(hash_list):
    # Builds a new combined hash by looping over the list of hashes
    hash_file_name = generate_hash_file_name(hash_list[0], hash_list[-1])
    xxhash64 = xxhash.xxh64()
    xxhash64_output = ""
    md5 = hashlib.md5()
    md5_output = ""
    size = 0

    for hash in hash_list:
        if hash:
            if hash.xxhash64be:
                xxhash64.update(hash.xxhash64be.encode('utf-8'))
                xxhash64_output = xxhash64.hexdigest()
            if hash.md5:
                md5.update(hash.md5.encode('utf-8'))
                md5_output = md5.hexdigest()
            size += int(hash.size)
    return FileHash(file=hash_file_name, size=size, 
                    xxhash64be=xxhash64_output, md5=md5_output, hashdate=hash_list[-1].hashdate)


def build_image_sequenced_clip_row(source_hash, destination_hash, is_last_file):
    global previous_img_sequence_hash
    global frames_in_src_img_seq_clip
    global frames_in_dest_img_seq_clip
    
    if destination_hash is None:
        # Immediately create a missing row for individual frames not found in an image sequence
        row_for_csv_output = check_hash(source_hash, destination_hash)
        add_row_to_output_list(row_for_csv_output)   
    
    if previous_img_sequence_hash:
        if source_hash.clipname() != previous_img_sequence_hash.clipname() or is_last_file:
            # Previous frame is from a different clip or its the last file. We're finished with the last clip.
            if is_last_file:
            # Add last file to the frame list
                frames_in_src_img_seq_clip.append(source_hash)
                frames_in_dest_img_seq_clip.append(destination_hash)
            # 1. Generate a hash for both src and dest for the previous clip frames, check them and add them to the output list
            src_img_seq_hash = generate_img_seq_clip_hash(frames_in_src_img_seq_clip)
            dest_img_seq_hash = generate_img_seq_clip_hash(frames_in_dest_img_seq_clip)
            row_for_csv_output = check_hash(src_img_seq_hash, dest_img_seq_hash)
            add_row_to_output_list(row_for_csv_output)
            # 2. Reset the lists ready for the next clip
            frames_in_src_img_seq_clip = []
            frames_in_dest_img_seq_clip = []
    
    frames_in_src_img_seq_clip.append(source_hash)
    frames_in_dest_img_seq_clip.append(destination_hash)

    previous_img_sequence_hash = source_hash


def check_hash(source_hash, destination_hash):
    if destination_hash is None:
        output_line = generate_output_csv_line('UNFOUND', source_hash, destination_hash)
    else:
        if USE_MD5:
            if source_hash.md5 == destination_hash.md5:
                output_line = generate_output_csv_line('MATCHED', source_hash, destination_hash)
            else:
                output_line = generate_output_csv_line('MISMATCHED', source_hash, destination_hash)
                print(f"\t{RED}The MD5 checksum for {source_hash.file} does not match. src: {source_hash.md5} dest: {destination_hash.md5}")
        else:
            if source_hash.xxhash64be == destination_hash.xxhash64be:
                output_line = generate_output_csv_line('MATCHED', source_hash, destination_hash)
            else:
                output_line = generate_output_csv_line('MISMATCHED', source_hash, destination_hash)
                print(f"\t{RED}The xxHash checksum for {source_hash.file} does not match. src: {source_hash.xxhash64be} dest: {destination_hash.xxhash64be}")
    return output_line


def export_output_csv():
    processed_rows_count = 0
    mhls_skipped = 0

    with open(SAVE_LOCATION + output_report_csv_name, 'w') as new_file:
        header = ['Status', 'Src File', 'Src Size', 'Src xxHash', 'Src MD5', 'Src Hash Date', 'Dest File', 'Dest Size', 'Dest xxHash', 'Dest MD5', 'Dest Hash Date']
        csv_writer = csv.writer(new_file)
        csv_writer.writerow(header)

        for line in output_csv_matched_list + output_csv_mismatched_list + output_csv_unfound_list:
            if '.mhl' in line:
                mhls_skipped += 1
            else:
                processed_rows_count += 1
                csv_writer.writerow(line)

    print(f"\n\t{DEFAULT}.mhl files are skipped. Total found in source MHLs: {mhls_skipped}")
    print(f"\tTotal files processed from source MHLs: {total_touched_files}")
    print(f"\tNumber of files added to report CSV: {str(processed_rows_count)}\n")
    print(f"\t{GREEN}\u2713{DEFAULT} Matched files: {len(output_csv_matched_list)}")
    print(f"\t{RED}\u00D7{DEFAULT} Unfound files: {len(output_csv_unfound_list)}")
    print(f"\t{ORANGE}?{DEFAULT} Mismatched files: {len(output_csv_mismatched_list)}")
    print(f"\n\tCheck complete. Output report CSV has been saved to {SAVE_LOCATION + output_report_csv_name}")
    print(f"\tPlease note this only reports files present in the source MHLs, any additional files on the destination are not included.")


def create_save_directory():
    folderChecker = os.path.isdir(SAVE_LOCATION)
    if folderChecker == False:
        os.mkdir(SAVE_LOCATION)


def print_info():
    global USE_MD5
    global SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM
    print(f"\t{BLUE}\n{__program_name__} v{__version__} | {__author__}")
    print(f"\t{DEFAULT}Comparing source MHLs with destination MHLs with the following settings:")
    if USE_MD5:
        print(f"\t{YELLOW}\t- MD5 flag provided - using md5 checksum.")
    else:
        print(f"\t{YELLOW}\t- Using xxHash checksum. Provide --md5 flag to use MD5.")

    if SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM:
        print(f"\t{YELLOW}\t- Skipping summarise image sequence to clip step. Skip summarise image sequences step flag provided.")
    else:
        print(f"\t{YELLOW}\t- Summarising image sequences to a single MHL per clip. You can skip this by providing the --skip-summarise-img-seq flag.")
    print("\n")


def copy_csv_content_to_clipboard(csv_path):
    csv = open(csv_path, "r")
    subprocess.run("pbcopy", universal_newlines=True, input=csv.read())
    print("\tCSV report contents has been copied to the clipboard.\n")


def add_row_to_output_list(row):
    if row[0] == 'MATCHED':
        output_csv_matched_list.append(row)
    elif row[0] == 'MISMATCHED':
        output_csv_mismatched_list.append(row)
    elif row[0] == 'UNFOUND':
        output_csv_unfound_list.append(row)


def print_progress(total_hashes, current_hash):
    if str(current_hash)[-3:] == "000":
                print(f"\t{YELLOW}Currently processing hash {str(current_hash)} of {str(total_hashes)}")


def build_hash_list(sources):
    global total_source_file_count
    print(f"\t{DEFAULT}Gathering all hashes from source MHLs...")
    hash_list = []
    for source_mhl_file in sources:
        mhl_root = et.parse(source_mhl_file.strip()).getroot()

        for child in mhl_root:
            if child.tag == 'hash':
                source_hash = create_hash_object(child)
                hash_list.append(source_hash)
    total_source_file_count = len(hash_list)
    print(f"\t{total_source_file_count} hashes in source MHLs.\n")
    return hash_list


def main(argv):
    global output_report_csv_name
    global total_source_file_count
    global total_touched_files
    global destination_toc_length
    global five_percent_toc_length
    arguments = args_parse(argv)
    print_info()
    create_save_directory()
    destination_toc = open(arguments.destination.strip()).read()
    destination_toc_length = len(destination_toc)
    five_percent_toc_length = int(destination_toc_length / 20)
    output_report_csv_name = "_".join(map(lambda x: os.path.basename(x).split("_")[0].split(".")[0], arguments.sources))
    output_report_csv_name += "_verified.csv"

    source_hash_list = build_hash_list(arguments.sources)
    print(f"\t{DEFAULT}Finding matches and comparing checksums...")
        
    for index, source_hash in enumerate(source_hash_list):
        print_progress(total_source_file_count, index)
        destination_hash = find_matching_hash(source_hash.file, destination_toc)

        if not SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM and source_hash.is_image_seq():
            total_touched_files += 1
            is_last_file = (index == total_source_file_count - 1)
            build_image_sequenced_clip_row(source_hash, destination_hash, is_last_file) 
        else:
            total_touched_files += 1
            row_for_csv_output = check_hash(source_hash, destination_hash)
            add_row_to_output_list(row_for_csv_output)
                    
    export_output_csv()
    copy_csv_content_to_clipboard(SAVE_LOCATION + output_report_csv_name)

    # Counts returned when running tests 
    if __name__ != '__main__':
        return {
            "total_source_file_count": total_source_file_count,
            "total_touched_files": total_touched_files,
            "output_csv_matched_list_length": len(output_csv_matched_list),
            "output_csv_mismatched_list_length": len(output_csv_mismatched_list),
            "output_csv_unfound_list_length": len(output_csv_unfound_list), 
        }


# Runs when opened from command line, passing sys.argv through to allow tests to run script
if __name__ == '__main__':
    sys.exit(main(sys.argv))


def reset_for_tests():
    # Tests dont run independently, so we need to reset the global variables
    global total_source_file_count
    global total_touched_files
    global USE_MD5
    global SAVE_LOCATION
    global SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM
    global output_csv_matched_list
    global output_csv_unfound_list
    global output_csv_mismatched_list
    global previous_img_sequence_hash
    global frames_in_src_img_seq_clip
    global frames_in_dest_img_seq_clip
    global destination_toc_length
    global five_percent_toc_length
    global last_matched_location
    total_source_file_count = 0
    total_touched_files = 0
    USE_MD5 = False
    SAVE_LOCATION = os.path.expanduser("~/Desktop/MHL_Verification_Reports/")
    SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM = False
    output_csv_matched_list = []
    output_csv_unfound_list = []
    output_csv_mismatched_list = []
    previous_img_sequence_hash = None
    frames_in_src_img_seq_clip = []
    frames_in_dest_img_seq_clip = []
    destination_toc_length = 0
    five_percent_toc_length = 0
    last_matched_location = 0