import csv
import sys
import os
from os.path import basename
import hashlib
import xxhash
import re
import subprocess

"""
Ref 
Gary@mission for help 
2021
"""

def mangle_csv_for_mhl_check(csv_file_path, output_file_path) -> None:
    """
    Usage: This rearranges a csv from AWS CLI to one we use in MHL spreadsheets
    :param csv_file_path: Input csv path
    :param output_file_path: (optional) csv output path, else defaults to working dir, input filename + _mangled.csv
    :return: outputs csv to paste into GSheets (Could impl google api but not worth it atm)
    """
    with open(csv_file_path, newline='') as csvfile:
        csv_for_mhl_sheet: list = []
        num_original_rows = 0
        reader = csv.reader(csvfile, delimiter=" ", skipinitialspace=True)
        for row in reader:
            num_original_rows += 1
            if len(row) >= 4:
                date = row[0]
                time = row[1]
                size = row[2]
                data_file_path = ''.join(row[3:]) # Join rows from 3 onwards to cover cases where there are spaces in the filename (csv from AWS is space separated)
            elif len(row) == 3:
                if "Objects" in row[1]:
                    totals_objects = row
                elif "Size" in row[1]:
                    totals_summary = row

                ## parse out existential MHLs evaluating themselves
            if not data_file_path.endswith((".mhl", ".mhl-back")):
                corrected_row = [data_file_path, size, "", "", f"{date}-{time}"]
                csv_for_mhl_sheet.append(corrected_row)
        with open(output_file_path, mode='w', newline='', encoding='utf-8') as manged_file:
            wr = csv.writer(manged_file, quoting=csv.QUOTE_MINIMAL,delimiter=",")
            for row in csv_for_mhl_sheet:
                wr.writerow(row)
            print("AWS_CLI -> MHL Gsheet:")
            print("Output successful")
            # print(f"{' '.join(totals_objects)}")
            print(f"Total Printed Lines: {len(csv_for_mhl_sheet)}")
            print(f"Total Original Lines: {num_original_rows}")
            print(f"Removed { num_original_rows - len(csv_for_mhl_sheet) } mhl entries")
            # print(f"{' '.join(totals_summary)}")


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

    with open(csv_path, 'w') as new_file:
        fieldnames = ['File', 'Size', 'xxHash', 'MD5', 'Hash Date']

        csv_writer = csv.DictWriter(new_file, fieldnames=fieldnames, extrasaction='ignore')

        for line in output_csv:
            csv_writer.writerow({'File': str(line[0]), 'Size': line[1], 'xxHash': line[2], 'MD5': line[3],
                                 'Hash Date': line[4]})
    print("Done summarising!")


def copy_csv_content_to_clipboard(csv_path):
    csv = open(csv_path, "r")
    subprocess.run("pbcopy", universal_newlines=True, input=csv.read())
    print("CSV contents has been copied to the clipboard.\n")


if __name__ == '__main__':
    csv_file_path = sys.argv[1]
    if len(sys.argv) == 3:
        output_file_path = sys.argv[2]
    else:
        output_file_path = f"{basename(csv_file_path)[:-4]}_mangled.csv"
    mangle_csv_for_mhl_check(csv_file_path, output_file_path)
    img_seq_checksums_to_clip_checksums(output_file_path)
    copy_csv_content_to_clipboard(output_file_path)
