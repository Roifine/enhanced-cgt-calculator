#!/usr/bin/env python3
"""
Data QA Script - Inspect loaded data vs source files
"""

import pandas as pd
import json

import os

def show_file_sources():
    """Show which files we're using for QA."""
    print("📁 FILE SOURCES:")
    
    sales_file = 'test_data/test_sales.csv'
    cost_basis_file = 'test_data/test_cost_basis.json'
    
    if os.path.exists(sales_file):
        size = os.path.getsize(sales_file)
        mtime = os.path.getmtime(sales_file)
        date = pd.to_datetime(mtime, unit='s').strftime('%Y-%m-%d %H:%M')
        print(f"   Sales: {sales_file} ({size} bytes, modified {date})")
    
    if os.path.exists(cost_basis_file):
        size = os.path.getsize(cost_basis_file)
        mtime = os.path.getmtime(cost_basis_file)
        date = pd.to_datetime(mtime, unit='s').strftime('%Y-%m-%d %H:%M')
        print(f"   Cost Basis: {cost_basis_file} ({size} bytes, modified {date})")
    
    print(f"   Original Sales: 50074435_20240701_20250527_parsed_sales_only_20250611_125325.csv")
    print(f"   Original Cost Basis: COMPLETE_unified_cost_basis_with_FIFO_as_of_2024_06_30.json")
def inspect_loaded_data():
    """Inspect what was actually loaded from our test files."""
    
    print("🔍 DATA QUALITY ASSURANCE")
    print("=" * 40)
    
    # Show file sources first
    show_file_sources()
    """Inspect what was actually loaded from our test files."""
    
    print("🔍 DATA QUALITY ASSURANCE")
    print("=" * 40)
    
    # Load and inspect sales data
    print("\n📉 SALES DATA INSPECTION:")
    sales_df = pd.read_csv('test_data/test_sales.csv')
    print(f"   Total sales transactions: {len(sales_df)}")
    print(f"   Columns: {list(sales_df.columns)}")
    print(f"   Date range: {sales_df['Trade Date'].min()} to {sales_df['Trade Date'].max()}")
    
    # Show first few sales
    print(f"\n📋 First 5 sales transactions:")
    for idx, row in sales_df.head().iterrows():
        print(f"   {idx+1}. {row['Symbol']}: {row['Quantity']} units @ ${row['Price (USD)']} on {row['Trade Date']}")
    
    # Show unique symbols in sales
    sales_symbols = sorted(sales_df['Symbol'].unique())
    print(f"\n🏷️  Symbols being sold ({len(sales_symbols)}): {', '.join(sales_symbols)}")
    
    # Load and inspect cost basis
    print(f"\n📦 COST BASIS INSPECTION:")
    with open('test_data/test_cost_basis.json', 'r') as f:
        cost_basis = json.load(f)
    
    print(f"   Total symbols with cost basis: {len(cost_basis)}")
    
    cost_basis_symbols = sorted(cost_basis.keys())
    print(f"   Symbols with cost basis: {', '.join(cost_basis_symbols)}")
    
    # Check for missing cost basis
    missing_cost_basis = [s for s in sales_symbols if s not in cost_basis_symbols]
    if missing_cost_basis:
        print(f"\n⚠️  MISSING COST BASIS for: {', '.join(missing_cost_basis)}")
    else:
        print(f"\n✅ All sales symbols have cost basis available")
    
    # Show cost basis details for sold symbols
    print(f"\n📊 COST BASIS DETAILS FOR SOLD SYMBOLS:")
    for symbol in sales_symbols:
        if symbol in cost_basis:
            parcels = cost_basis[symbol]
            total_units = sum(p['units'] for p in parcels)
            total_sold = sales_df[sales_df['Symbol'] == symbol]['Quantity'].sum()
            
            print(f"\n   {symbol}:")
            print(f"     Available units: {total_units}")
            print(f"     Units being sold: {total_sold}")
            print(f"     Sufficient units: {'✅ Yes' if total_units >= total_sold else '❌ No - Short by ' + str(total_sold - total_units)}")
            print(f"     Parcels: {len(parcels)}")
            
            for i, parcel in enumerate(parcels):
                print(f"       {i+1}. {parcel['units']} units @ ${parcel['price']} from {parcel['date']}")
    
    # Summary
    print(f"\n📋 QA SUMMARY:")
    print(f"   ✅ Sales transactions: {len(sales_df)}")
    print(f"   ✅ Symbols being sold: {len(sales_symbols)}")
    print(f"   ✅ Symbols with cost basis: {len(cost_basis)}")
    print(f"   {'✅' if not missing_cost_basis else '❌'} Cost basis coverage: {'Complete' if not missing_cost_basis else 'Missing ' + str(len(missing_cost_basis))}")

if __name__ == "__main__":
    inspect_loaded_data()
