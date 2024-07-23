# Source/Destination MHL Compare Tool

This script takes a list of source MHLs and compares the hashes inside against a destination MHL.
A common usecase is comparing Silverstack MHL's from set against a YoYotta LTO MHL.
It outputs a CSV report which should be pasted into a Google Sheets doc for future reference.

## Usage

### Run directly

To run directly without installing (make sure you are working in the right directory):

`python3 source-destination-mhl-compare.py -s /path/to/source_mhl_1.mhl /path/to/source_mhl_2.mhl -d /path/to/dest_mhl.mhl`

Use `-s` to provide the source MHLs and `-d` to provide the destination MHL. See Options below for more info.

### Install & Run

To install:

- Move script file to a permanent location, such as:

  `~/Desktop/Scripts/source-destination-mhl-compare.py`

- Make the script executable:

  `chmod +x ~/Desktop/Scripts/source-destination-mhl-compare.py`

- Symlink the script to system bin:
  `ln -s ~/Desktop/Scripts/source-destination-mhl-compare.py /usr/local/bin`

After installation, you can run the script directly:

`source-destination-mhl-compare -s /path/to/source_mhl_1.mhl /path/to/source_mhl_2.mhl -d /path/to/dest_mhl.mhl`

Use `-s` to provide the source MHLs and `-d` to provide the destination MHL. See Options below for more info.

## Options

### Required flags:

`-s OR --sources` : A list of source MHLs to check

`-d OR --destination` : A single destination MHL to check against.

### Optional flags:

`--md5` : Compares MD5 checksums instead of xxHash

`--skip-summarise-img-seq` : Skips the summarise image sequence step.

`-o OR --output-dir` : Specify a directory to save the ouput report CSV to (defaults to ~/Desktop/MHL_Verification_Reports/)
