"""
Unit tests for source_destination_mhl_compare.py
Run with:
$ pytest test_source_destination_mhl_compare.py -vs

#    ✅ 1. Works with mix of img seq and normal files
#    ✅ 2. Works with arx
#    ✅ 3. Works with dng
#    ✅ 4. Correctly errors when missing frame
#    ✅ 5. File counts correct
#    ✅ 6. Correctly uses xxhash or MD5
#    ✅ 7. Correctly skips image seq checksums
#    ✅ 8. Works with multiple source MHLs
#    ✅ 9. Handles incorrect MD5 or xxHash value
#    - 9. Check what is does with transcodes in destination
"""

import unittest
import source_destination_mhl_compare

class TestMhlCompare(unittest.TestCase):
    def setUp(self):
        source_destination_mhl_compare.reset_for_tests()

    def test_gets_correct_file_counts(self):
        report_summary = source_destination_mhl_compare.main(
            ['source_destination_mhl_compare.py', 
            '-s', 'tests/fixtures/test-file-count-src1.mhl', 'tests/fixtures/test-file-count-src2.mhl',
            '-d', 'tests/fixtures/test-file-count-dest.mhl',
            '--output-dir', 'tests/test_outputs/'
        ])

        assert report_summary['total_source_file_count'] == 20
        assert report_summary["total_touched_files"] == report_summary['total_source_file_count']
        assert report_summary["output_csv_matched_list_length"] == 20
        assert report_summary["output_csv_mismatched_list_length"] == 0
        assert report_summary["output_csv_unfound_list_length"] == 0


    def test_supports_dng(self):
        report_summary = source_destination_mhl_compare.main(
            ['source_destination_mhl_compare.py', 
            '-s', 'tests/fixtures/test-dng-source.mhl',
            '-d', 'tests/fixtures/test-dng-dest.mhl',
            '--output-dir', 'tests/test_outputs/'
        ])

        assert report_summary['total_source_file_count'] == 21
        assert report_summary["total_touched_files"] == report_summary['total_source_file_count']
        assert report_summary["output_csv_matched_list_length"] == 2
        assert report_summary["output_csv_mismatched_list_length"] == 0
        assert report_summary["output_csv_unfound_list_length"] == 0
        

    def test_supports_arx(self):
        report_summary = source_destination_mhl_compare.main(
            ['source_destination_mhl_compare.py', 
            '-s', 'tests/fixtures/test-arx-source.mhl',
            '-d', 'tests/fixtures/test-arx-dest.mhl',
            '--output-dir', 'tests/test_outputs/'
        ])


        assert report_summary['total_source_file_count'] == 20
        assert report_summary["total_touched_files"] == report_summary['total_source_file_count']
        assert report_summary["output_csv_matched_list_length"] == 2
        assert report_summary["output_csv_mismatched_list_length"] == 0
        assert report_summary["output_csv_unfound_list_length"] == 0
    

    def test_detects_missing_frame(self):
        report_summary = source_destination_mhl_compare.main(
            ['source_destination_mhl_compare.py', 
            '-s', 'tests/fixtures/test-missing-frame-source.mhl',
            '-d', 'tests/fixtures/test-missing-frame-dest.mhl',
            '--output-dir', 'tests/test_outputs/'
        ])

        assert report_summary['total_source_file_count'] == 20
        assert report_summary["total_touched_files"] == report_summary['total_source_file_count']
        assert report_summary["output_csv_matched_list_length"] == 1
        assert report_summary["output_csv_mismatched_list_length"] == 1
        assert report_summary["output_csv_unfound_list_length"] == 1


    def test_detects_missing_clip(self):
        # A390C002 mxf is missing from destination
        report_summary = source_destination_mhl_compare.main(
            ['source_destination_mhl_compare.py', 
            '-s', 'tests/fixtures/test-missing-clip-src.mhl',
            '-d', 'tests/fixtures/test-missing-clip-dest.mhl',
            '--output-dir', 'tests/test_outputs/'
        ])

        assert report_summary['total_source_file_count'] == 10
        assert report_summary["total_touched_files"] == report_summary['total_source_file_count']
        assert report_summary["output_csv_matched_list_length"] == 9
        assert report_summary["output_csv_mismatched_list_length"] == 0
        assert report_summary["output_csv_unfound_list_length"] == 1


    def test_detects_wrong_xxhash(self):
        # A390C002 xxhash is wrong in destination
        report_summary = source_destination_mhl_compare.main(
            ['source_destination_mhl_compare.py', 
            '-s', 'tests/fixtures/test-wrong-xxhash-src.mhl',
            '-d', 'tests/fixtures/test-wrong-xxhash-dest.mhl',
            '--output-dir', 'tests/test_outputs/'
        ])

        assert report_summary['total_source_file_count'] == 5
        assert report_summary["total_touched_files"] == report_summary['total_source_file_count']
        assert report_summary["output_csv_matched_list_length"] == 4
        assert report_summary["output_csv_mismatched_list_length"] == 1
        assert report_summary["output_csv_unfound_list_length"] == 0


    def test_detects_wrong_md5(self):
        # A390C002 MD5 is wrong in destination
        report_summary = source_destination_mhl_compare.main(
            ['source_destination_mhl_compare.py', 
            '-s', 'tests/fixtures/test-wrong-md5-src.mhl',
            '-d', 'tests/fixtures/test-wrong-md5-dest.mhl',
            '--output-dir', 'tests/test_outputs/',
            '--md5'
        ])

        assert report_summary['total_source_file_count'] == 5
        assert report_summary["total_touched_files"] == report_summary['total_source_file_count']
        assert report_summary["output_csv_matched_list_length"] == 4
        assert report_summary["output_csv_mismatched_list_length"] == 1
        assert report_summary["output_csv_unfound_list_length"] == 0
    
    def test_skip_image_seq(self):
        report_summary = source_destination_mhl_compare.main(
            ['source_destination_mhl_compare.py', 
            '-s', 'tests/fixtures/test-arx-source.mhl',
            '-d', 'tests/fixtures/test-arx-dest.mhl',
            '--output-dir', 'tests/test_outputs/',
            '--skip-summarise-img-seq'
        ])

        assert report_summary['total_source_file_count'] == 20
        assert report_summary["total_touched_files"] == report_summary['total_source_file_count']
        assert report_summary["output_csv_matched_list_length"] == 20
        assert report_summary["output_csv_mismatched_list_length"] == 0
        assert report_summary["output_csv_unfound_list_length"] == 0
    