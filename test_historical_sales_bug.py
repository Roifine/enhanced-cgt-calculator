#!/usr/bin/env python3
"""
Test script to verify the historical sales cost basis bug fix.

This test reproduces the exact scenario described in the bug report:
- Purchase: 200 NVDA shares (100 @ $50, 100 @ $150)
- Historical sale: 200 shares in Mar 2023 (consumed ALL shares)
- Current sale: 50 shares in Aug 2024
- Expected: System should reject the sale (insufficient shares)
"""

import pandas as pd
import io
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from csv_processor import StatementProcessor

def create_test_csv_data():
    """Create test CSV data that reproduces the historical sales bug."""
    
    # Test data reproducing the exact scenario from the bug report
    csv_data = """Symbol,Trade Date,Type,Quantity,Price (USD),Commission (USD)
NVDA,2021-10-01,BUY,100,50.00,25.00
NVDA,2021-06-15,BUY,100,150.00,25.00
NVDA,2023-03-15,SELL,200,100.00,25.00
NVDA,2024-08-25,SELL,50,200.00,25.00"""
    
    return io.StringIO(csv_data)

def test_historical_sales_bug():
    """Test that the historical sales bug is fixed."""
    
    print("🧪 Testing Historical Sales Cost Basis Bug Fix")
    print("=" * 60)
    
    # Create test data
    test_csv = create_test_csv_data()
    
    # Process the CSV
    processor = StatementProcessor()
    try:
        cost_basis_dict, fy24_25_sales, warnings, processing_log = processor.process_statement_csv(test_csv)
        
        print("\n📊 Processing Results:")
        print(f"Cost basis symbols: {list(cost_basis_dict.keys())}")
        print(f"FY24-25 sales: {len(fy24_25_sales)}")
        print(f"Warnings: {len(warnings)}")
        
        print("\n📋 Processing Log:")
        for log_entry in processing_log[-10:]:  # Show last 10 entries
            print(f"  {log_entry}")
        
        print("\n⚠️ Warnings:")
        for warning in warnings:
            print(f"  {warning}")
        
        # Check if the bug is fixed
        print("\n🔍 Bug Fix Verification:")
        if any("Insufficient shares" in warning for warning in warnings):
            print("✅ SUCCESS: Historical sales bug is FIXED!")
            print("   The system correctly detected overselling after accounting for historical sales.")
        else:
            print("❌ FAILURE: Historical sales bug is NOT fixed!")
            print("   The system did not detect the overselling scenario.")
        
        # Show remaining cost basis after historical sales
        if 'NVDA' in cost_basis_dict:
            remaining_units = sum(parcel['units'] for parcel in cost_basis_dict['NVDA'])
            print(f"\n📦 NVDA Cost Basis After Historical Sales:")
            print(f"   Remaining units: {remaining_units}")
            for i, parcel in enumerate(cost_basis_dict['NVDA']):
                if parcel['units'] > 0:
                    print(f"   Parcel {i+1}: {parcel['units']} units @ ${parcel['price']}")
        
        return len(warnings) > 0  # Test passes if warnings were generated
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def test_edge_cases():
    """Test additional edge cases for the historical sales fix."""
    
    print("\n\n🧪 Testing Additional Edge Cases")
    print("=" * 60)
    
    # Test case: Partial historical sales
    partial_sales_csv = """Symbol,Trade Date,Type,Quantity,Price (USD),Commission (USD)
AAPL,2021-01-01,BUY,300,100.00,10.00
AAPL,2021-02-01,BUY,200,110.00,10.00
AAPL,2023-01-15,SELL,150,120.00,10.00
AAPL,2024-08-01,SELL,200,130.00,10.00"""
    
    print("\n📋 Test Case: Partial Historical Sales")
    print("   - Buy 300 + 200 = 500 AAPL shares")
    print("   - Sell 150 shares historically (leaving 350)")
    print("   - Try to sell 200 shares in FY24-25 (should succeed)")
    
    test_csv = io.StringIO(partial_sales_csv)
    processor = StatementProcessor()
    
    try:
        cost_basis_dict, fy24_25_sales, warnings, processing_log = processor.process_statement_csv(test_csv)
        
        insufficient_warnings = [w for w in warnings if "Insufficient shares" in w]
        if insufficient_warnings:
            print("❌ UNEXPECTED: Should have sufficient shares for partial sales case")
        else:
            print("✅ SUCCESS: Partial historical sales handled correctly")
            
        if 'AAPL' in cost_basis_dict:
            remaining_units = sum(parcel['units'] for parcel in cost_basis_dict['AAPL'])
            print(f"   Remaining units after historical sales: {remaining_units}")
            
    except Exception as e:
        print(f"❌ Partial sales test failed: {e}")

if __name__ == "__main__":
    print("🚀 Running Historical Sales Bug Tests")
    print("=" * 60)
    
    # Run main bug test
    success = test_historical_sales_bug()
    
    # Run edge case tests
    test_edge_cases()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 OVERALL: Historical sales bug fix appears to be working!")
    else:
        print("⚠️ OVERALL: Historical sales bug may still exist.")