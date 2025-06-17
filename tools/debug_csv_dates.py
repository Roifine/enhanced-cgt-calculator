#!/usr/bin/env python3
"""
Debug CSV Date Parsing Issues
Quick inspection of actual date formats in your CSV
"""

import pandas as pd
import os

def debug_csv_dates():
    """Debug the date parsing issues in the CSV."""
    
    print("🔍 DEBUGGING CSV DATE FORMATS")
    print("=" * 40)
    
    # Look for CSV files in multiple locations
    possible_paths = [
        '.',
        '..',
        '../data',
        '../../data',
    ]
    
    csv_files = []
    for path in possible_paths:
        try:
            files_in_path = [f for f in os.listdir(path) if f.endswith('.csv')]
            csv_files.extend([os.path.join(path, f) for f in files_in_path if os.path.exists(os.path.join(path, f))])
        except:
            continue
    
    if not csv_files:
        print("❌ No CSV files found")
        return
    
    print(f"📁 Found {len(csv_files)} CSV files:")
    for i, f in enumerate(csv_files):
        print(f"   {i+1}. {f}")
    
    # Ask user which file to debug
    choice = input(f"\nChoose file to debug (1-{len(csv_files)}): ").strip()
    
    try:
        file_index = int(choice) - 1
        target_file = csv_files[file_index]
    except:
        print("Using first file...")
        target_file = csv_files[0]
    
    print(f"🎯 Analyzing: {target_file}")
    
    try:
        # Load CSV
        df = pd.read_csv(target_file)
        print(f"✅ Loaded {len(df)} rows")
        
        # Show ALL columns
        print(f"\n📋 ALL COLUMNS ({len(df.columns)}):")
        for i, col in enumerate(df.columns):
            print(f"   {i+1}. '{col}'")
        
        # Find date column
        date_columns = [col for col in df.columns if 'date' in col.lower() or 'Date' in col]
        print(f"\n📅 Date columns found: {date_columns}")
        
        if not date_columns:
            print("❌ No date columns found!")
            print("Let's check first few rows of all data:")
            print(df.head(3).to_string())
            return
        
        date_col = date_columns[0]
        print(f"🎯 Using column: '{date_col}'")
        
        # Show raw date values (more samples)
        print(f"\n📋 RAW DATE VALUES (first 15):")
        sample_dates = df[date_col].head(15).tolist()
        for i, date_val in enumerate(sample_dates):
            print(f"   {i+1:2d}. '{date_val}' (type: {type(date_val).__name__}, len: {len(str(date_val)) if date_val is not None else 0})")
        
        # Show unique date patterns
        print(f"\n🔍 UNIQUE DATE FORMATS (first 20 unique values):")
        unique_dates = df[date_col].dropna().unique()[:20]
        for i, date_val in enumerate(unique_dates):
            date_str = str(date_val).strip()
            print(f"   {i+1:2d}. '{date_str}'")
        
        # Test our parsing function on these dates
        print(f"\n🧪 TESTING DATE PARSING:")
        
        def test_parse_date(date_str):
            """Test the parsing function"""
            if pd.isna(date_str) or not date_str:
                return "EMPTY"
            
            date_str = str(date_str).strip()
            
            date_formats = [
                "%Y-%m-%d",     # 2024-12-19 (ISO)
                "%m/%d/%Y",     # 12/19/2024 (US)
                "%d/%m/%Y",     # 19/12/2024 (AU)
                "%d-%m-%Y",     # 19-12-2024
                "%d.%m.%Y",     # 19.12.2024
                "%d.%m.%y",     # 19.12.24 (existing)
                "%Y-%m-%d %H:%M:%S",  # 2024-12-19 10:30:45
                "%m/%d/%y",     # 12/19/24
                "%d/%m/%y",     # 19/12/24
            ]
            
            for fmt in date_formats:
                try:
                    from datetime import datetime
                    parsed_date = datetime.strptime(date_str, fmt)
                    
                    # Handle 2-digit years
                    if parsed_date.year < 2000:
                        if parsed_date.year < 50:
                            parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
                        else:
                            parsed_date = parsed_date.replace(year=parsed_date.year + 1900)
                    
                    return f"SUCCESS with {fmt} → {parsed_date.strftime('%d.%m.%y')}"
                    
                except ValueError:
                    continue
            
            return "FAILED - no format matched"
        
        # Test first 10 unique dates
        test_dates = df[date_col].dropna().unique()[:10]
        for date_val in test_dates:
            result = test_parse_date(date_val)
            print(f"   '{date_val}' → {result}")
        
        # Also show commission and transaction type info
        print(f"\n💰 COMMISSION ANALYSIS:")
        commission_cols = [col for col in df.columns if 'commission' in col.lower()]
        
        if commission_cols:
            comm_col = commission_cols[0]
            print(f"📊 Commission column: '{comm_col}'")
            
            sample_commissions = df[comm_col].head(10).tolist()
            print(f"Sample commission values:")
            for i, comm_val in enumerate(sample_commissions):
                print(f"   {i+1:2d}. {comm_val} (type: {type(comm_val).__name__})")
        
        print(f"\n📊 TRANSACTION TYPE ANALYSIS:")
        type_cols = [col for col in df.columns if col.lower() in ['type', 'transaction type', 'action']]
        if type_cols:
            type_col = type_cols[0]
            type_counts = df[type_col].value_counts()
            print(f"Transaction types in '{type_col}':")
            for type_name, count in type_counts.items():
                print(f"   {type_name}: {count}")
        
    except Exception as e:
        print(f"❌ Error analyzing CSV: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_csv_dates()