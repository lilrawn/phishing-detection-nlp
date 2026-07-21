#!/usr/bin/env python3
"""
Script to create the combined dataset from raw data files
Run this BEFORE main.py to ensure your datasets are properly loaded
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_collection import DataCollector

print("=" * 60)
print("📊 PHISHING DATASET CREATION TOOL")
print("=" * 60)

collector = DataCollector()

print(f"\n📁 Raw data directory: {collector.raw_data_dir}")
print(f"📁 Processed data directory: {collector.processed_dir}")

if os.path.exists(collector.raw_data_dir):
    print("\n📋 Files found in raw directory:")
    for f in os.listdir(collector.raw_data_dir):
        file_path = os.path.join(collector.raw_data_dir, f)
        if os.path.isfile(file_path):
            print(f"  - {f} ({os.path.getsize(file_path)} bytes)")

combined_df = collector.load_and_combine_datasets()

# Verify the file was saved correctly
output_path = os.path.join(collector.processed_dir, 'combined_dataset.csv')
if os.path.exists(output_path):
    import pandas as pd
    test_df = pd.read_csv(output_path)
    print(f"\n   Verified: {len(test_df)} rows can be read back from {output_path}")
