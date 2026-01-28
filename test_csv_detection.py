#!/usr/bin/env python3
"""
Test CSV detection logic
"""
import os
import sys
from pathlib import Path
import time

# Add current directory to path to import from api.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the necessary components
class MockLogger:
    def info(self, msg):
        print(f"INFO: {msg}")
    def error(self, msg):
        print(f"ERROR: {msg}")
    def debug(self, msg):
        print(f"DEBUG: {msg}")
    def warning(self, msg):
        print(f"WARNING: {msg}")

logger = MockLogger()

def _find_latest_csv(max_age_seconds: int = 30) -> str:
    """Find the latest CSV file in the results directory (search recursively)"""
    try:
        current_time = time.time()
        
        # Search for CSV files in the current directory and all subdirectories
        csv_files = list(Path(".").glob("**/*.csv"))
        if not csv_files:
            print("No CSV files found")
            return None
        
        # Filter files by modification time (only recent files)
        recent_csv_files = []
        for csv_file in csv_files:
            try:
                mtime = csv_file.stat().st_mtime
                age_seconds = current_time - mtime
                if age_seconds <= max_age_seconds:
                    recent_csv_files.append((csv_file, mtime))
                    print(f"  Found recent CSV: {csv_file} (age: {age_seconds:.1f}s)")
                else:
                    print(f"  Skipping old CSV: {csv_file} (age: {age_seconds:.1f}s)")
            except Exception as e:
                print(f"  Error checking file {csv_file}: {e}")
                continue
        
        if not recent_csv_files:
            print(f"No CSV files modified within last {max_age_seconds} seconds")
            return None
        
        # Get the most recently modified CSV file among recent files
        latest_csv, latest_mtime = max(recent_csv_files, key=lambda x: x[1])
        
        # Return absolute path
        result = str(latest_csv.absolute())
        print(f"Latest CSV: {result} (modified {current_time - latest_mtime:.1f}s ago)")
        return result
    except Exception as e:
        print(f"Error finding latest CSV: {e}")
        return None

def _find_csv_by_filename(filename: str) -> str:
    """Find a CSV file by filename (search recursively)"""
    try:
        # Search for CSV files with the given filename in all subdirectories
        csv_files = list(Path(".").glob(f"**/{filename}"))
        if csv_files:
            # Return the first matching CSV file (should be unique)
            result = str(csv_files[0].absolute())
            print(f"Found CSV by exact filename: {result}")
            return result
        
        # If not found with exact match, try case-insensitive search
        for csv_file in Path(".").glob("**/*.csv"):
            if csv_file.name.lower() == filename.lower():
                result = str(csv_file.absolute())
                print(f"Found CSV by case-insensitive match: {result}")
                return result
        
        print(f"CSV file '{filename}' not found")
        return None
    except Exception as e:
        print(f"Error finding CSV by filename '{filename}': {e}")
        return None

def test_csv_detection():
    """Test CSV detection functions"""
    print("Testing CSV detection logic")
    print("=" * 60)
    
    # First, list all CSV files
    print("\nAll CSV files found:")
    csv_files = list(Path(".").glob("**/*.csv"))
    for csv_file in csv_files[:10]:  # Show first 10
        try:
            mtime = csv_file.stat().st_mtime
            age = time.time() - mtime
            print(f"  {csv_file} (age: {age:.1f}s)")
        except:
            print(f"  {csv_file}")
    
    if len(csv_files) > 10:
        print(f"  ... and {len(csv_files) - 10} more")
    
    # Test finding latest CSV
    print("\n1. Testing _find_latest_csv():")
    latest = _find_latest_csv(max_age_seconds=60)
    print(f"   Result: {latest}")
    
    # Test finding by filename
    print("\n2. Testing _find_csv_by_filename():")
    
    # Try to find a CSV file we know exists
    if csv_files:
        test_filename = csv_files[0].name
        print(f"   Looking for filename: {test_filename}")
        found = _find_csv_by_filename(test_filename)
        print(f"   Result: {found}")
    
    # Test with a filename from logs
    print("\n3. Testing with filename from logs:")
    log_filename = "query_results_387c5c52.csv"
    print(f"   Looking for: {log_filename}")
    found = _find_csv_by_filename(log_filename)
    print(f"   Result: {found}")
    
    # Test regex pattern for capturing filename
    print("\n4. Testing regex pattern for capturing CSV filename:")
    test_texts = [
        "Results saved to file: query_results_387c5c52.csv",
        "Saved to file: query_results_abc123.csv",
        "saved to file: query_results_def456.csv",
        "Some other text query_results_ghi789.csv more text",
        "No CSV here"
    ]
    
    import re
    pattern1 = r'(?:Results saved to file:|Saved to file:|saved to file:)\s*([\w\-_]+\.csv)'
    pattern2 = r'([\w\-_]+\.csv)'
    
    for text in test_texts:
        print(f"\n   Text: {text}")
        match1 = re.search(pattern1, text)
        if match1:
            print(f"   Pattern1 match: {match1.group(1)}")
        else:
            print(f"   Pattern1: no match")
        
        match2 = re.search(pattern2, text)
        if match2 and 'query_results' in match2.group(1):
            print(f"   Pattern2 match: {match2.group(1)}")
        else:
            print(f"   Pattern2: no match or not a query_results file")

if __name__ == "__main__":
    test_csv_detection()