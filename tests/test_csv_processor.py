#!/usr/bin/env python3
"""
CSV Processor Test Runner
Test the statement processor with actual CSV files
"""

import pandas as pd
import json
import os
from datetime import datetime

# Add src directory to path for imports
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import the CSV processor
from csv_processor import process_statement_csv


def test_csv_processor_interactive():
    """Interactive test of CSV processor with user's file(s)."""
    
    print("🧪 CSV PROCESSOR TEST (MULTIPLE FILES SUPPORTED)")
    print("=" * 60)
    print()
    
    # List available CSV files in current directory and parent
    csv_files = []
    
    # Check current directory
    local_csvs = [f for f in os.listdir('.') if f.endswith('.csv')]
    csv_files.extend(local_csvs)
    
    # Check parent directory (likely has data/)
    try:
        parent_csvs = [f"../{f}" for f in os.listdir('..') if f.endswith('.csv')]
        csv_files.extend(parent_csvs)
    except:
        pass
    
    # Check data directory
    try:
        data_csvs = [f"../data/{f}" for f in os.listdir('../data') if f.endswith('.csv')]
        csv_files.extend(data_csvs)
    except:
        pass
    
    if csv_files:
        print("📁 Available CSV files:")
        for i, file in enumerate(csv_files, 1):
            try:
                size = os.path.getsize(file) if os.path.exists(file) else "unknown"
                print(f"   {i}. {file} ({size} bytes)")
            except:
                print(f"   {i}. {file}")
        print()
        
        # Let user choose files
        print("📋 File selection options:")
        print("   • Single file: Enter one number (e.g., '3')")
        print("   • Multiple files: Enter comma-separated numbers (e.g., '1,3,5')")
        print("   • Custom path: Enter file path")
        print()
        
        while True:
            try:
                choice = input(f"Choose file(s) or enter custom path(s): ").strip()
                
                selected_files = []
                
                if ',' in choice:
                    # Multiple files by number
                    indices = [int(x.strip()) for x in choice.split(',')]
                    for idx in indices:
                        if 1 <= idx <= len(csv_files):
                            selected_files.append(csv_files[idx - 1])
                        else:
                            print(f"❌ Invalid choice: {idx}")
                            continue
                elif choice.isdigit():
                    # Single file by number
                    idx = int(choice)
                    if 1 <= idx <= len(csv_files):
                        selected_files = [csv_files[idx - 1]]
                    else:
                        print(f"❌ Invalid choice: {idx}")
                        continue
                else:
                    # Custom path(s)
                    if ',' in choice:
                        paths = [p.strip() for p in choice.split(',')]
                        for path in paths:
                            if os.path.exists(path):
                                selected_files.append(path)
                            else:
                                print(f"❌ File not found: {path}")
                    else:
                        if os.path.exists(choice):
                            selected_files = [choice]
                        else:
                            print(f"❌ File not found: {choice}")
                            continue
                
                if selected_files:
                    break
                else:
                    print("❌ No valid files selected")
                    
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                return
            except ValueError:
                print("❌ Invalid input format")
    else:
        file_input = input("📁 Enter CSV file path(s) (comma-separated for multiple): ").strip()
        if ',' in file_input:
            selected_files = [f.strip() for f in file_input.split(',')]
        else:
            selected_files = [file_input]
        
        # Validate files exist
        valid_files = []
        for file_path in selected_files:
            if os.path.exists(file_path):
                valid_files.append(file_path)
            else:
                print(f"❌ File not found: {file_path}")
        
        if not valid_files:
            print("❌ No valid files found")
            return
        
        selected_files = valid_files
    
    print(f"\n🗂️ Testing with {len(selected_files)} file(s):")
    for i, file_path in enumerate(selected_files, 1):
        print(f"   {i}. {file_path}")
    print()
    
    try:
        # Run the processor with multiple files
        cost_basis_dict, fy24_25_sales, warnings, processing_log = process_statement_csv(selected_files)
        
        # Display results
        print("\n" + "="*60)
        print("📊 PROCESSING RESULTS")
        print("="*60)
        
        # Cost basis summary
        print(f"\n📦 COST BASIS SUMMARY:")
        print(f"   Total symbols: {len(cost_basis_dict)}")
        
        total_parcels = 0
        for symbol, parcels in cost_basis_dict.items():
            total_units = sum(p['units'] for p in parcels)
            print(f"   {symbol}: {len(parcels)} parcels, {total_units} units total")
            total_parcels += len(parcels)
        
        print(f"   Total parcels: {total_parcels}")
        
        # Sales summary
        print(f"\n📈 FY24-25 SALES SUMMARY:")
        print(f"   Total sales transactions: {len(fy24_25_sales)}")
        
        if not fy24_25_sales.empty:
            sales_by_symbol = fy24_25_sales.groupby('symbol')['quantity'].agg(['count', 'sum'])
            for symbol, data in sales_by_symbol.iterrows():
                print(f"   {symbol}: {data['count']} transactions, {data['sum']} units sold")
        
        # Warnings
        print(f"\n⚠️ WARNINGS ({len(warnings)}):")
        if warnings:
            for warning in warnings[:5]:  # Show first 5
                print(f"   • {warning}")
            if len(warnings) > 5:
                print(f"   ... and {len(warnings) - 5} more warnings")
        else:
            print("   ✅ No warnings!")
        
        # Show sample cost basis structure
        print(f"\n📋 SAMPLE COST BASIS STRUCTURE:")
        if cost_basis_dict:
            sample_symbol = list(cost_basis_dict.keys())[0]
            sample_parcels = cost_basis_dict[sample_symbol][:2]  # First 2 parcels
            print(f"   {sample_symbol}:")
            for i, parcel in enumerate(sample_parcels):
                print(f"     Parcel {i+1}: {parcel['units']} units @ ${parcel['price']} + ${parcel['commission']} commission on {parcel['date']}")
        
        # Show sample sales data
        print(f"\n📋 SAMPLE SALES DATA:")
        if not fy24_25_sales.empty:
            sample_sale = fy24_25_sales.iloc[0]
            print(f"   {sample_sale['symbol']}: {sample_sale['quantity']} units @ ${sample_sale['price']} on {sample_sale['parsed_date']}")
        
        # Export options
        print(f"\n💾 EXPORT OPTIONS:")
        export_choice = input("Export results? (c=cost_basis.json, s=sales.csv, b=both, n=none): ").lower().strip()
        
        if export_choice in ['c', 'b']:
            json_filename = f"cost_basis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_filename, 'w') as f:
                json.dump(cost_basis_dict, f, indent=2)
            print(f"   ✅ Cost basis exported to: {json_filename}")
        
        if export_choice in ['s', 'b']:
            csv_filename = f"fy24_25_sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            fy24_25_sales.to_csv(csv_filename, index=False)
            print(f"   ✅ Sales exported to: {csv_filename}")
        
        # Processing log
        show_log = input("\nShow detailed processing log? (y/n): ").lower().strip()
        if show_log == 'y':
            print(f"\n📋 DETAILED PROCESSING LOG:")
            for log_entry in processing_log:
                print(f"   {log_entry}")
        
        return True
        
    except Exception as e:
        print(f"❌ PROCESSING FAILED: {str(e)}")
        import traceback
        print(f"\nFull error traceback:")
        traceback.print_exc()
        return False


def quick_inspect_csv(csv_file):
    """Quick inspection of CSV structure before processing."""
    
    print(f"🔍 QUICK CSV INSPECTION: {csv_file}")
    print("-" * 40)
    
    try:
        # Load just the first few rows
        df = pd.read_csv(csv_file, nrows=5)
        
        print(f"Columns ({len(df.columns)}):")
        for i, col in enumerate(df.columns):
            print(f"   {i+1}. {col}")
        
        print(f"\nFirst few rows:")
        print(df.to_string(index=False))
        
        # Load full file for summary stats
        df_full = pd.read_csv(csv_file)
        print(f"\nTotal rows: {len(df_full)}")
        
        # Check for transaction types
        if 'Type' in df_full.columns:
            type_counts = df_full['Type'].value_counts()
            print(f"Transaction types:")
            for type_name, count in type_counts.items():
                print(f"   {type_name}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error inspecting CSV: {e}")
        return False


if __name__ == "__main__":
    print("🚀 CSV PROCESSOR TESTING TOOL")
    print("=" * 40)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Option to inspect CSV first
    inspect_first = input("Inspect CSV structure first? (y/n): ").lower().strip()
    
    if inspect_first == 'y':
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        if csv_files:
            print("\n📁 Available CSV files:")
            for i, file in enumerate(csv_files, 1):
                print(f"   {i}. {file}")
            
            try:
                choice = int(input(f"\nChoose file to inspect (1-{len(csv_files)}): "))
                if 1 <= choice <= len(csv_files):
                    quick_inspect_csv(csv_files[choice - 1])
                    print()
            except (ValueError, IndexError):
                print("Invalid choice")
        
        proceed = input("Proceed with full processing? (y/n): ").lower().strip()
        if proceed != 'y':
            print("👋 Exiting...")
            exit()
    
    # Run the full test
    success = test_csv_processor_interactive()
    
    print(f"\n💡 MULTI-FILE PROCESSING TIPS:")
    print(f"   ✅ Upload ALL your historical CSV files to get complete cost basis")
    print(f"   ✅ Include recent files for short-term trades (buy and sell in FY24-25)")
    print(f"   ✅ The processor combines ALL buys for cost basis, filters sales to FY24-25")
    print(f"   ✅ This solves the missing cost basis issue!")
    
    if success:
        print("\n🎉 CSV PROCESSOR TEST COMPLETED SUCCESSFULLY!")
        print("✅ Ready to integrate with Streamlit interface")
        print("🚀 NEXT: Build Streamlit app with multi-file upload support")
    else:
        print("\n🔧 Test failed - check errors above")