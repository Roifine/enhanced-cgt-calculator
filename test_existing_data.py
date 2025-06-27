#!/usr/bin/env python3
"""
Test the fixed system with existing CSV data to ensure it still works correctly.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from csv_processor import process_statement_csv

def test_existing_data():
    """Test with existing CSV data files."""
    
    print("🧪 Testing Fixed System with Existing CSV Data")
    print("=" * 60)
    
    # Test with the existing data files
    csv_files = [
        'data/2023-2024.csv',
        'data/2024-2025.csv'
    ]
    
    try:
        cost_basis_dict, fy24_25_sales, warnings, processing_log = process_statement_csv(csv_files)
        
        print(f"\n📊 Results:")
        print(f"   Cost basis symbols: {len(cost_basis_dict)}")
        print(f"   FY24-25 sales: {len(fy24_25_sales)}")
        print(f"   Warnings: {len(warnings)}")
        
        # Check for overselling warnings
        overselling_warnings = [w for w in warnings if "Insufficient shares" in w]
        if overselling_warnings:
            print(f"\n⚠️ Overselling Issues Detected:")
            for warning in overselling_warnings:
                print(f"   {warning}")
        else:
            print(f"\n✅ No overselling issues detected with existing data")
        
        # Show sample of adjusted cost basis
        print(f"\n📦 Sample Cost Basis (after historical sales adjustment):")
        for symbol, parcels in list(cost_basis_dict.items())[:5]:
            total_units = sum(p['units'] for p in parcels)
            active_parcels = [p for p in parcels if p['units'] > 0]
            print(f"   {symbol}: {total_units} units remaining, {len(active_parcels)} active parcels")
        
        print(f"\n🔍 System Status: {'✅ HEALTHY' if len(overselling_warnings) == 0 else '⚠️ ISSUES FOUND'}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_existing_data()