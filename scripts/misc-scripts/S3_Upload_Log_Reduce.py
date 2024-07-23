import sys
import os

def run():
    # Counters for printing at the end
    removed_counter = 0
    skipped_counter = 0
    uploading_counter = 0
    checksum_counter = 0

    file = sys.argv[1]
    input_name = os.path.basename(file).split(".")[0]
    path = os.path.dirname(file) + '/'
    reduced_log = ""

    # Opening up the inputted log and parsing through each line
    with open(file, "r") as f:
        lines = f.readlines()
    for line in lines:

        if "Active uploads: " in line:
            uploading_counter += 1
            removed_counter += 1
        elif "skipping " in line:
            skipped_counter += 1
            removed_counter += 1
        elif "Active checksums: " in line:
            checksum_counter += 1
            removed_counter += 1
        else:
            reduced_log += f"{line} \n"

    with open(path + input_name + '_reduced.log', 'w') as f:
        f.write(reduced_log)

    # Printouts to console
    print(f"Number of uploading lines removed: {uploading_counter}")
    print(f"Number of skipped lines removed: {skipped_counter}")
    print(f"Number of checksum lines removed: {checksum_counter}")
    print(f"Total number of lines removed: {removed_counter}")


if __name__ == '__main__':
    run()
