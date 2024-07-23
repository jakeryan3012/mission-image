#!/usr/bin/env python3

__program_name__ = "Source/Destination MHL Check"
__description__ = "Goes through a list of MHLs, for each media hash record, it tries to find a match in the destination MHL and checks the checksum matches. Exports a CSV report."
__author__ = "Davide Brambilla/Josh Unwin/Gary Palmer"
__version__ = "1.1"

import csv
import hashlib
import re
import sys
import xxhash
import os
import argparse
import subprocess
import xml.etree.ElementTree as et
import tqdm

USE_MD5 = False
USE_RESTORE = False
SAVE_LOCATION = os.path.expanduser("~/Desktop/MHL_Verification_Reports/")
SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM = False
frames_img_seq_clip = []
output_csv_matched_list = []
output_csv_mismatched_different_file_list = []
output_csv_remaining_yoyo_list = []
output_csv_remaining_restore_list = []
output_csv_remaining_list = []
output_csv_source = []
output_csv_mismatched_same_file_list = []
frames_img_seq_clip = []
img_seq_hash = []
use_ignored_extensions = True
extensions_to_ignore = ['.mhl', '.txt', '.bk', '.db', '.url', '.sav', '.pdf', '.bin', '.csv', '.json', '.metadata_never_index', '.xml', '.fmtsig_sounddev', '.cdl', '.cube', '.drp', '.psla', '.csv', '_sounddev']
skip_summarise_img_seq = False
hashes_filter = ['TRANSCODES', 'DOCUMENTATION', 'MEZZANINE', 'RESUPPLY', 'RENAME', 'SUBMASTER']
is_last_file = []

BLUE = "\033[0;34m"
DEFAULT = "\033[0m"
YELLOW = "\033[0;33m"
GREEN = '\033[1;32m'
RED = '\033[1;31m'
ORANGE = '\033[0;31m'
PURPLE = "\033[0;35m"

def create_save_directory():
    folderChecker = os.path.isdir(SAVE_LOCATION)
    if folderChecker == False:
        os.mkdir(SAVE_LOCATION)

class FileHash:
    def __init__(self, file="", size="", xxhash64be="", md5="", hashdate=""):
        self.file = file
        self.size = size
        self.xxhash64be = xxhash64be
        self.md5 = md5
        self.hashdate = hashdate
    
    def is_image_seq(self):
        lowercase = self.file.lower()
        return lowercase.endswith(('.ari', '.arx', '.dng',))

    def file_extension(self):
        filename, file_extension = os.path.splitext(self.file)
        return file_extension

    def clipname(self):
        if self.file_extension().casefold() == '.dng':
            dng_pattern = r'(\d+)\.dng$' # Match numeric sequence followed by .DNG at the end
            dng_regex = re.compile(dng_pattern, re.IGNORECASE)
            match = dng_regex.search(self.file)
            if match:
                clipname = self.file[:match.start()]
                return clipname
        else:    
            return self.file.split(".")[0]

    def frame_number(self):
        if self.file_extension().casefold() == '.dng':
            dng_pattern = r'(\d+)\.dng$'  # Match numeric sequence followed by .DNG at the end
            dng_regex = re.compile(dng_pattern, re.IGNORECASE)
            match = dng_regex.search(self.file)
            if match:
                frame = match.group(1)
                return frame
        else:
            frame = self.file.split(".")[-2]
            return frame
        
def last_file_clipname(clip):
    filename, file_extension = os.path.splitext(clip)
    if file_extension.casefold() == '.dng':
        dng_pattern = r'(\d+)\.dng$'  # Match numeric sequence followed by .DNG at the end
        dng_regex = re.compile(dng_pattern, re.IGNORECASE)
        match = dng_regex.search(clip)
        if match:
            clipname = clip[:match.start()]
            return clipname
    else:    
        clipname = clip.split(".")[0]
        return clipname
        
def args_parse(argv):
    global USE_MD5
    global skip_summarise_img_seq
    global SAVE_LOCATION
    global USE_RESTORE
    global USE_YOYO
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output-dir', help="The directory to save the output CSV file to.", default=SAVE_LOCATION)
    parser.add_argument('-s', '--sources', nargs='+', help="One or more source MHLs (eg: such as MHLs from Silverstack)")
    parser.add_argument('-y', '--yoyo', nargs='+', help="The Yoyo mhl you wish to use")
    parser.add_argument('-r', '--restore', nargs='+', help="The Restore mhl you wish to use")
    parser.add_argument('--skip-summarise-img-seq', action='store_true', help="Include to skip the combine image seq checksums step")
    checksum_type_group = parser.add_mutually_exclusive_group()
    checksum_type_group.add_argument('--xxhash', help="Use xxHash checksum (default)")
    checksum_type_group.add_argument('--md5', action='store_true', help="Use md5 checksum")
    parsed_arguments = parser.parse_args(argv[1:]) # skip the first argument (the script name)
    USE_MD5 = parsed_arguments.md5
    USE_RESTORE = parsed_arguments.restore
    USE_YOYO = parsed_arguments.yoyo
    SAVE_LOCATION = parsed_arguments.output_dir
    skip_summarise_img_seq = parsed_arguments.skip_summarise_img_seq
    
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

def create_hash_object_v2(mhl_hash):
    hash = FileHash()
    for element in mhl_hash:
        if 'path' in element.tag:
            hash.file = element.text
            try:
                hash.size = element.attrib['size']
            except:
                pass
        if 'xxh64' in element.tag:
            hash.xxhash64be = element.text
            try:
                hash.hashdate = element.attrib['hashdate']
            except:
                pass
        if 'md5' in element.tag:
            hash.md5 = element.text
    
    return hash

def build_hash_list(your_mhl_list):
    global hash_list
    hash_dict = {}
    hash_list = []
    duplicates_list = []
    unique_hashes_set = set()
    for input_mhl_file in your_mhl_list:
        
        mhl_name = []
        mhl_name_extract = os.path.splitext(os.path.basename(input_mhl_file))[0]
        mhl_name = FileHash(file=mhl_name_extract, size="", xxhash64be="", md5="", hashdate="")
        mhl_root = et.parse(input_mhl_file.strip()).getroot()
        mhl_version = float(mhl_root.attrib["version"]) 
        if mhl_version >= 2:
            # Extract the namespace from the root tag
            ns = re.match(r'{.*}', mhl_root.tag).group(0)
            hash_elements = mhl_root.findall('.//{}hash'.format(ns)) 
            #getting the child element and filename
            total_elements = len(hash_elements)
    
            for i, child in tqdm.tqdm(enumerate(hash_elements), desc=f'{BLUE}Processing hashes from: {DEFAULT}{mhl_name_extract}{BLUE}', total=total_elements, unit='hash'):
                for parent_node in child:
                    if 'path' in parent_node.tag:
                        filename = parent_node.text
                        #skip duplicates
                        if filename not in unique_hashes_set:
                            unique_hashes_set.add(filename)
                        else:
                            duplicates_list.append(filename)
                            break

                        if not SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM:
                            find_the_last_file(filename, i, mhl_version, hash_elements)
                            
                        if not (any(filename.endswith(ext) for ext in extensions_to_ignore) or any(hf in filename for hf in hashes_filter)):
                            input_hash = create_hash_object_v2(child)
                            not_available(input_hash)
                                                                    
                            if not SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM:                          
                                creating_list_of_hashes(input_hash, is_last_file, hash_dict, mhl_name, hash_list)
                            else:
                                hash_dict.setdefault(mhl_name, []).append(input_hash)
                                hash_list.append(input_hash)
                    
                            
                                                            
        else:
            hash_elements = mhl_root.findall('.//hash')
            total_elements = len(hash_elements)
            for i, child in tqdm.tqdm(enumerate(mhl_root), desc=f'{BLUE}Processing hashes from: {DEFAULT}{mhl_name_extract}{BLUE}', total=total_elements, unit='hash'):
                if child.tag == 'hash':
                    filename = child.find('file').text
                    #skip duplicates
                    if filename not in unique_hashes_set:
                        unique_hashes_set.add(filename)
                    else:
                        duplicates_list.append(filename)
                        continue

                    if not SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM:
                            find_the_last_file(filename, i, mhl_version, hash_elements)

                    if not (any(filename.endswith(ext) for ext in extensions_to_ignore) or any(hf in filename for hf in hashes_filter)):
                        input_hash = create_hash_object(child)
                        not_available(input_hash)

                        if not SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM:                              
                            creating_list_of_hashes(input_hash, is_last_file, hash_dict, mhl_name, hash_list)
                        else:
                            hash_dict.setdefault(mhl_name, []).append(input_hash)
                            hash_list.append(input_hash)

                                                     
    duplicates_count = len(duplicates_list)
    total_file_count = len(hash_list)
    return total_file_count, hash_dict, duplicates_count, hash_list


def find_the_last_file(filename, i, mhl_version, hash_elements):
    global is_last_file
    potential_last_file = []
    clipname_map = {}
    lowercase = filename.lower()

    if not frames_img_seq_clip and lowercase.endswith(('.ari', '.arx', '.dng')):
        hash_elements_slice = hash_elements[i+1:]
        end_list = len(hash_elements_slice) - 1
        

        for j, lastfile in enumerate(hash_elements_slice):
            
            if mhl_version >= 2:
                for elements in lastfile:
                    if 'path' in elements.tag:
                        last_file_filename = elements.text
            else:
                last_file_filename = lastfile.find('file').text

            if j == end_list:
                if last_file_clipname(filename) == last_file_clipname(last_file_filename):
                    is_last_file = last_file_filename
                    break

            if last_file_clipname(filename) != last_file_clipname(last_file_filename):
                if last_file_clipname(last_file_filename) in clipname_map:
                    is_last_file = clipname_map[last_file_clipname(last_file_filename)]
                else:
                    is_last_file = potential_last_file[-1]
                potential_last_file = []
                break
            else:
                clipname = last_file_clipname(last_file_filename)
                clipname_map[clipname] = last_file_filename
                potential_last_file.append(last_file_filename)

                
def creating_list_of_hashes(your_input_hash, is_last_file, hash_dict, mhl_name, hash_list):
    if your_input_hash.is_image_seq():
        img_seq_hash = build_image_sequenced_clip_row(your_input_hash, is_last_file)
        if img_seq_hash:
            hash_dict.setdefault(mhl_name, []).append(img_seq_hash)
            hash_list.append(img_seq_hash)
            img_seq_hash = []
    elif not your_input_hash.is_image_seq():
            hash_dict.setdefault(mhl_name, []).append(your_input_hash)
            hash_list.append(your_input_hash)
                            
def not_available(input_hash):
    if not input_hash.size:
        input_hash.size = "Not available"
    if not input_hash.xxhash64be:
        input_hash.xxhash64be = "Not available"
    if not input_hash.md5:
        input_hash.md5 = "Not available"
    if not input_hash.hashdate:
        input_hash.hashdate = "Not available"
    return input_hash

def print_info():
    global USE_MD5
    global SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM
    print(f"\t{BLUE}\n{__program_name__} v{__version__} | {__author__}")
    print(f"\t{DEFAULT} List of all possible arguments: [-h [help ...]] [-o OUTPUT_DIR] [-s [SOURCES.mhl ...]] [-y [YOYO.mhl ...]][-r [RESTORE.mhl ...]] [--skip-summarise-img-seq] [--xxhash XXHASH | --md5].")
    print(f"\t{DEFAULT}Comparing source MHLs with destination MHLs with the following settings:")
    if USE_MD5:
        print(f"\t{YELLOW}\t- MD5 flag provided - using md5 checksum.")
    else:
        print(f"\t{YELLOW}\t- Using xxHash checksum. Provide --md5 flag to use MD5.")

    if SKIP_IMAGE_SEQ_TO_CLIP_CHECKSUM:
        print(f"\t{YELLOW}\t- Skipping summarise image sequence to clip step. Skip summarise image sequences step flag provided.")
    else:
        print(f"\t{YELLOW}\t- Summarising image sequences to a single MHL per clip. You can skip this by providing the --skip-summarise-img-seq flag.")
    if USE_YOYO:
        print(f"\t{YELLOW}\t- Yoyo is your first destination.")
    if USE_RESTORE:
        print(f"\t{YELLOW}\t- Restore is your second destination.")
    print("\n")



def print_progress(total_hashes, current_hash):
    if str(current_hash)[-3:] == "000":
                print(f"\t{YELLOW}Currently processing hash {str(current_hash)} of {str(total_hashes)}")
    
def find_matching_cam_yoyo_restore(cam_hash, cam_mhl_name, yoyo_dict, restore_dict, processed_yoyo_hashes, processed_restore_hashes):

    if USE_MD5:
        cam_hash_value = cam_hash.md5
        yoyo_hash_attr = 'md5'
        restore_hash_attr = 'md5'
    else:
        cam_hash_value = cam_hash.xxhash64be
        yoyo_hash_attr = 'xxhash64be'
        restore_hash_attr = 'xxhash64be'   
    match = False
    for yoyo_mhl_name, hashes in yoyo_dict.items():
        for yoyo_hash in hashes:
            if yoyo_hash in processed_yoyo_hashes:
                continue  # Skip already processed yoyo_hash values

            for restore_mhl_name, restore_hashes_list in restore_dict.items():
                for restore_hash in restore_hashes_list:
                    if restore_hash in processed_restore_hashes:
                        continue  # Skip already processed yoyo_hash values

                    if getattr(yoyo_hash, yoyo_hash_attr) == cam_hash_value and getattr(restore_hash, restore_hash_attr) == cam_hash_value:
                        
                        match = True
                        output_line = generate_output_csv_line('MATCHED', cam_mhl_name=cam_mhl_name, cam_hash=cam_hash, yoyo_mhl_name=yoyo_mhl_name, yoyo_hash=yoyo_hash, restore_mhl_name=restore_mhl_name, restore_hash=restore_hash, match=match)
                        processed_yoyo_hashes.add(yoyo_hash) # Mark the yoyo_hash as processed
                        processed_restore_hashes.add(restore_hash) # Mark the restore_hash as processed
                        return output_line

                    elif yoyo_hash.file == cam_hash.file and restore_hash.file == cam_hash.file:
                        match = True
                        output_line = generate_output_csv_line('UNMATCHED_SAME_FILE', cam_mhl_name=cam_mhl_name, cam_hash=cam_hash, yoyo_mhl_name=yoyo_mhl_name, yoyo_hash=yoyo_hash, restore_mhl_name=restore_mhl_name, restore_hash=restore_hash, match=match)
                        processed_yoyo_hashes.add(yoyo_hash) # Mark the yoyo_hash as processed
                        processed_restore_hashes.add(restore_hash) # Mark the restore_hash as processed
                        return output_line
                    
    if not match:
        output_line = generate_output_csv_line('REMAINING_FROM_CAM', cam_mhl_name=cam_mhl_name, cam_hash=cam_hash, match=match)
        return output_line
    return processed_yoyo_hashes, processed_restore_hashes

def find_matching_cam_yoyo(cam_hash, cam_mhl_name, yoyo_dict, processed_yoyo_hashes):
  
    if USE_MD5:
        cam_hash_value = cam_hash.md5
        yoyo_hash_attr = 'md5'
    else:
        cam_hash_value = cam_hash.xxhash64be
        yoyo_hash_attr = 'xxhash64be'
    
    match = False
    for yoyo_mhl_name, hashes in yoyo_dict.items():
        
        for yoyo_hash in hashes:
            if yoyo_hash in processed_yoyo_hashes:
                continue  # Skip already processed yoyo_hash values
            if getattr(yoyo_hash, yoyo_hash_attr) == cam_hash_value:
                match = True
                output_line = generate_output_csv_line('MATCHED', cam_mhl_name=cam_mhl_name, cam_hash=cam_hash, yoyo_mhl_name=yoyo_mhl_name, yoyo_hash=yoyo_hash, match=match)
                processed_yoyo_hashes.add(yoyo_hash) # Mark the yoyo_hash as processed
                return output_line

            elif yoyo_hash.file == cam_hash.file:
                match = True
                output_line = generate_output_csv_line('UNMATCHED_SAME_FILE', cam_mhl_name=cam_mhl_name, cam_hash=cam_hash, yoyo_mhl_name=yoyo_mhl_name, yoyo_hash=yoyo_hash, match=match)
                processed_yoyo_hashes.add(yoyo_hash)
                return output_line
    if not match:
        output_line = generate_output_csv_line('REMAINING_FROM_CAM', cam_mhl_name=cam_mhl_name, cam_hash=cam_hash, match=match)
        return output_line
    return processed_yoyo_hashes

def generate_output_csv_single(status, mhl_name, your_hash):
    rows = [your_hash.file, your_hash.size, your_hash.xxhash64be, your_hash.md5, your_hash.hashdate]
    mhl_list = [mhl_name.file]
    return [status] + mhl_list + rows

def generate_output_csv_line(status, **kwargs):

    cam_mhl_name = kwargs.get('cam_mhl_name', None)
    cam_hash = kwargs.get('cam_hash', None)
    yoyo_mhl_name = kwargs.get('yoyo_mhl_name', None)
    yoyo_hash = kwargs.get('yoyo_hash', None)
    restore_mhl_name = kwargs.get('restore_mhl_name', None)
    restore_hash = kwargs.get('restore_hash', None)
    match = kwargs.get('match', None)
    cam_mhl_list = [cam_mhl_name.file]
 
    if USE_RESTORE:
        if match:
            
            cam_rows = [cam_hash.file, cam_hash.size, cam_hash.xxhash64be, cam_hash.md5, cam_hash.hashdate]
            yoyo_rows = [yoyo_hash.file, yoyo_hash.size, yoyo_hash.xxhash64be, yoyo_hash.md5, yoyo_hash.hashdate]
            restore_rows = [restore_hash.file, restore_hash.size, restore_hash.xxhash64be, restore_hash.md5, restore_hash.hashdate]
            yoyo_mhl_list = [yoyo_mhl_name.file]
            restore_mhl_list = [restore_mhl_name.file]
            return [status] + cam_mhl_list + cam_rows + yoyo_mhl_list + yoyo_rows + restore_mhl_list + restore_rows
        else:
            cam_rows = [cam_hash.file, cam_hash.size, cam_hash.xxhash64be, cam_hash.md5, cam_hash.hashdate]
            return [status] + cam_mhl_list + cam_rows
    elif USE_YOYO:
        if match:
            cam_rows = [cam_hash.file, cam_hash.size, cam_hash.xxhash64be, cam_hash.md5, cam_hash.hashdate]
            yoyo_rows = [yoyo_hash.file, yoyo_hash.size, yoyo_hash.xxhash64be, yoyo_hash.md5, yoyo_hash.hashdate]
            yoyo_mhl_list = [yoyo_mhl_name.file]
            return [status] + cam_mhl_list + cam_rows + yoyo_mhl_list + yoyo_rows
        else:
            cam_rows = [cam_hash.file, cam_hash.size, cam_hash.xxhash64be, cam_hash.md5, cam_hash.hashdate]
            return [status] + cam_mhl_list + cam_rows
        
def build_image_sequenced_clip_row(current_hash, is_last_file):
    global frames_img_seq_clip
    
    if current_hash.file == is_last_file:
        frames_img_seq_clip.append(current_hash)            
        # 1. Generate a hash for the previous clip frames, check them and add them to the output list
        output = generate_img_seq_clip_hash(frames_img_seq_clip)
        # 2. Reset the lists ready for the next clip
        frames_img_seq_clip = []
        is_last_file = []
        return output
    
    frames_img_seq_clip.append(current_hash)
 

def generate_hash_file_name(first_clip, last_clip):
    if first_clip.file_extension().casefold() == '.dng':
        return f'{first_clip.clipname()}{first_clip.frame_number()}-{last_clip.frame_number()}{first_clip.file_extension()}'
    else:
        return f'{first_clip.clipname()}.{first_clip.frame_number()}-{last_clip.frame_number()}{first_clip.file_extension()}'

def generate_img_seq_clip_hash(hash_list):
    hash_file_name = generate_hash_file_name(hash_list[0], hash_list[-1])
    xxhash64 = xxhash.xxh64()
    md5 = hashlib.md5()
    size = 0

    for h in hash_list:
        if h and h.xxhash64be:
            xxhash64.update(h.xxhash64be.encode('utf-8'))
        if h and h.md5:
            md5.update(h.md5.encode('utf-8'))
        if h:
            size += int(h.size)
       
    return FileHash(file=hash_file_name, size=size, xxhash64be=xxhash64.hexdigest(), md5=md5.hexdigest(), hashdate=hash_list[-1].hashdate)
        
def add_row_to_output_list(row):
    if row[0] == 'MATCHED':
        output_csv_matched_list.append(row)
    elif row[0] == 'UNMATCHED_SAME_FILE':
        output_csv_mismatched_same_file_list.append(row)
    elif row[0] == 'REMAINING_FROM_CAM':
        output_csv_mismatched_different_file_list.append(row)
    elif row[0] == 'MISSING_SOURCE_FROM_YOYO':
        output_csv_remaining_yoyo_list.append(row)
    elif row[0] == 'MISSING_SOURCE_FROM_RESTORE':
        output_csv_remaining_restore_list.append(row)
    elif row[0] == 'SOURCE_HASH':
        output_csv_source.append(row)

def sorting_list_out(list1, list2, list3, list4, list5, list6):
    list1.sort(key=lambda x: str(x[1]) + str(x[2]))
    list2.sort(key=lambda x: str(x[1]) + str(x[2]))
    list3.sort(key=lambda x: str(x[1]) + str(x[2]))
    list4.sort(key=lambda x: str(x[1]) + str(x[2]))
    list5.sort(key=lambda x: str(x[1]) + str(x[2]))
    list6.sort(key=lambda x: str(x[1]) + str(x[2]))

def export_output_csv():

    with open(SAVE_LOCATION + output_report_csv_name, 'w') as new_file:
        if USE_RESTORE:
            header = ['STATUS', 'SOURCE FILE', 'SOURCE SIZE', 'SOURCE XXHASH', 'SOURCE MD5', 'SOURCE HASH DATE', 'YOYO FILE', 'YOYO SIZE', 'YOYO XXHASH', 'YOYO MD5', 'YOYO HASH DATE', 'RESTORE FILE', 'RESTORE SIZE', 'RESTORE XXHASH', 'RESTORE MD5', 'RESTORE HASH DATE']
        elif USE_YOYO:
            header = ['STATUS', 'SOURCE FILE', 'SOURCE SIZE', 'SOURCE XXHASH', 'SOURCE MD5', 'SOURCE HASH DATE', 'YOYO FILE', 'YOYO SIZE', 'YOYO XXHASH', 'YOYO MD5', 'YOYO HASH DATE']
        else:
            header = ['STATUS', 'SOURCE FILE', 'SOURCE SIZE', 'SOURCE XXHASH', 'SOURCE MD5', 'SOURCE HASH DATE']
        csv_writer = csv.writer(new_file)
        csv_writer.writerow(header)
        
        #Sorting the lists
        sorting_list_out(output_csv_matched_list, output_csv_mismatched_same_file_list, output_csv_mismatched_different_file_list, output_csv_remaining_yoyo_list, output_csv_remaining_restore_list, output_csv_source)
        
        count_rows_list1 = csv_writing_lines(new_file, output_csv_matched_list)
        count_rows_list2 = csv_writing_lines(new_file, output_csv_mismatched_same_file_list)
        count_rows_list3 = csv_writing_lines(new_file, output_csv_mismatched_different_file_list)
        count_rows_list4 = csv_writing_lines(new_file, output_csv_remaining_yoyo_list)
        count_rows_list5 = csv_writing_lines(new_file, output_csv_remaining_restore_list)
        count_rows_list6 = csv_writing_lines(new_file, output_csv_source)

        processed_rows_count = count_rows_list1 + count_rows_list2 + count_rows_list3 + count_rows_list4 + count_rows_list5 + count_rows_list6

    print(f"\tTotal files processed from all the MHLs: {total_count}")
    print(f"\tNumber of lines added to report CSV: {str(processed_rows_count)}\n")
    if USE_YOYO or USE_RESTORE:
        print(f"\t{GREEN}\u2713{DEFAULT} Matched files: {len(output_csv_matched_list)}")
        print(f"\t{RED}\u00D7{DEFAULT} Mismatched files: {len(output_csv_mismatched_same_file_list)}")
        if output_csv_mismatched_different_file_list:
            print(f"\t{ORANGE}?{DEFAULT} Remaining Cam files: {len(output_csv_mismatched_different_file_list)}")
        if output_csv_remaining_yoyo_list:
            print(f"\t{ORANGE}?{DEFAULT} Remaining Yoyo files: {len(output_csv_remaining_yoyo_list)}")
        if output_csv_remaining_restore_list:
            print(f"\t{ORANGE}?{DEFAULT} Remaining Restore files: {len(output_csv_remaining_restore_list)}")
    else:
        print(f"\t{GREEN}\u2713{DEFAULT} Suorce files: {len(output_csv_source)}")
    print(f"\n\tCheck complete. Output report CSV has been saved to {SAVE_LOCATION + output_report_csv_name}")
     
def csv_writing_lines(file, csv_list):
    processed_rows_count = 0
    csv_writer = csv.writer(file)
    processed_lines = set()
    for line in csv_list:
 
        if USE_RESTORE:
            key_indices = [1, 7, 13]
        elif USE_YOYO:
            key_indices = [1, 7]
        else:
            key_indices = [1]

        key = tuple(line[i] for i in key_indices if i < len(line))

        if key not in processed_lines:
            if USE_RESTORE:
                if csv_list == output_csv_matched_list or csv_list == output_csv_mismatched_same_file_list:
                    mhl_name_line = ['', line[1], '', '', '', '', line[7], '', '', '', '', line[13]]
                elif csv_list == output_csv_mismatched_different_file_list:
                    mhl_name_line = ['', line[1]]
                elif csv_list == output_csv_remaining_yoyo_list:
                    mhl_name_line = ['', '' , '', '', '', '', line[1]]
                elif csv_list == output_csv_remaining_restore_list:
                    mhl_name_line = ['', '' , '', '', '', '', '' , '', '', '', '', line[1]]

            elif USE_YOYO: 
                if csv_list == output_csv_matched_list or csv_list == output_csv_mismatched_same_file_list:
                    mhl_name_line = ['', line[1], '', '', '', '', line[7]]
                elif csv_list == output_csv_mismatched_different_file_list:
                    mhl_name_line = ['', line[1]]
                elif csv_list == output_csv_remaining_yoyo_list:
                    mhl_name_line = ['', '' , '', '', '', '', line[1]]
            else:
                if csv_list == output_csv_source:
                        mhl_name_line = ['', line[1]]
                
            csv_writer.writerow([]) 
            csv_writer.writerow(mhl_name_line)
            #csv_writer.writerow(data_line)
            processed_lines.add(key)
            processed_rows_count += 1
        
        data_line = [line[i] for i in range(len(line)) if i not in key_indices]
        if csv_list == output_csv_remaining_yoyo_list:
            data_line = [line[0], '', '', '', '', '', line[2], line[3], line[4], line[5], line[6]]
        elif csv_list == output_csv_remaining_restore_list:
            data_line = [line[0], '', '', '', '', '', '', '', '', '', '', line[2], line[3], line[4], line[5], line[6]]  
        
        processed_rows_count += 1
        csv_writer.writerow(data_line)

    return processed_rows_count

def copy_csv_content_to_clipboard(csv_path):
    csv = open(csv_path, "r")
    subprocess.run("pbcopy", universal_newlines=True, input=csv.read())
    print("\tCSV report contents has been copied to the clipboard.\n")

def remaining_yoyo_or_restore(processed_hashes, mhl_dict, yoyo):
    for key, hashes_list in mhl_dict.items():
        for current_hash in hashes_list:
            if current_hash not in processed_hashes:
                if yoyo:
                    output_row = generate_output_csv_single('MISSING_SOURCE_FROM_YOYO', key, current_hash)

                else:
                    output_row = generate_output_csv_single('MISSING_SOURCE_FROM_RESTORE', key, current_hash)

                add_row_to_output_list(output_row)
      
def main(argv):
    global output_report_csv_name
    global total_cam_file_count
    global total_yoyo_file_count
    global total_restore_file_count
    global extensions_to_ignore
    global total_count
    cam_duplicates_count = 0
    yoyo_duplicates_count = 0
    restore_duplicates_count = 0
    total_yoyo_file_count = 0
    total_restore_file_count = 0
    yoyo_hashes_list = []
    restore_hashes_list = []
    arguments = args_parse(argv)
    print_info()
    create_save_directory()
    output_report_csv_name = "_".join(map(lambda x: os.path.basename(x).split("_")[0].split(".")[0], arguments.sources))
    output_report_csv_name += "_verified.csv"
    print(f"\t{ORANGE}Gathering all hashes from your MHLs...\n")
    total_cam_file_count, cam_mhl_dict, cam_duplicates_count, cam_hashes_list = build_hash_list(arguments.sources)
    
    print(f"{DEFAULT}{total_cam_file_count} hashes in cam MHLs.\n") 
    if USE_YOYO:
        total_yoyo_file_count, yoyo_mhl_dict, yoyo_duplicates_count, yoyo_hashes_list = build_hash_list(arguments.yoyo)
        print(f"{DEFAULT}{total_yoyo_file_count} hashes in yoyo MHLs.\n")
    
    if USE_RESTORE:
        total_restore_file_count, restore_mhl_dict, restore_duplicates_count, restore_hashes_list = build_hash_list(arguments.restore)
        print(f"{DEFAULT}{total_restore_file_count} hashes in restore MHLs.\n")

    if cam_duplicates_count or yoyo_duplicates_count or restore_duplicates_count:
        print(f"\t{BLUE}Duplicates ignored from MHL input list...\n")
        print(f"\t{DEFAULT}{cam_duplicates_count} duplicates in cam MHLs.\n")
        if USE_YOYO:
            print(f"\t{DEFAULT}{yoyo_duplicates_count} duplicates in yoyo MHLs.\n")
        if USE_RESTORE:
            print(f"\t{DEFAULT}{restore_duplicates_count} duplicates in restore MHLs.\n")

    total_count = total_cam_file_count + total_yoyo_file_count + total_restore_file_count

    print(f"\t{DEFAULT}Finding matches and comparing checksums...")
    
    processed_yoyo_hashes = set()  # Set to store processed yoyo_hash values
    processed_restore_hashes = set() # Set to store processed restore_hash values

    for mhl_name_key, hashes in cam_mhl_dict.items():
        for i, current_camera_hash in enumerate(hashes):

            if USE_RESTORE:
                print_progress(total_cam_file_count, i)
                output_row = find_matching_cam_yoyo_restore(current_camera_hash, mhl_name_key, yoyo_mhl_dict, restore_mhl_dict, processed_yoyo_hashes, processed_restore_hashes)
        
            elif USE_YOYO:
                print_progress(total_cam_file_count, i)
                output_row = find_matching_cam_yoyo(current_camera_hash, mhl_name_key, yoyo_mhl_dict, processed_yoyo_hashes)
            
            else:
                print_progress(total_cam_file_count, i)
                output_row = generate_output_csv_single('SOURCE_HASH', mhl_name_key, current_camera_hash)

            add_row_to_output_list(output_row)
    
    if USE_YOYO:
        yoyo = True
        remaining_yoyo_or_restore(processed_yoyo_hashes, yoyo_mhl_dict, yoyo)
    if USE_RESTORE:
        yoyo = False
        remaining_yoyo_or_restore(processed_restore_hashes, restore_mhl_dict, yoyo)
     
    export_output_csv()
    copy_csv_content_to_clipboard(SAVE_LOCATION + output_report_csv_name)
        
# Runs when opened from command line, passing sys.argv through to allow tests to run script
if __name__ == '__main__':
    sys.exit(main(sys.argv))

    

        