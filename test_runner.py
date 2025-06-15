#!/usr/bin/env python3
"""
Simple Test Runner for Enhanced CGT System
"""

import pandas as pd
import json
from datetime import datetime

# Import our enhanced modules
from tax_optimizer import optimize_sale_for_cgt
from cgt_calculator_enhanced import calculate_enhanced_cgt

def run_basic_test():
    """Run a basic test of the enhanced CGT system."""
    
    print("🧪 TESTING ENHANCED CGT SYSTEM")
    print("=" * 40)
    
    try:
        # Load test data
        print("📂 Loading test data...")
        
        # Load sales CSV
        sales_df = pd.read_csv('test_data/test_sales.csv')
        print(f"   ✅ Sales loaded: {len(sales_df)} transactions")
        
        # Load cost basis JSON  
        with open('test_data/test_cost_basis.json', 'r') as f:
            cost_basis_dict = json.load(f)
        print(f"   ✅ Cost basis loaded: {len(cost_basis_dict)} symbols")
        
        # Convert Trade Date to datetime
        sales_df['Trade Date'] = pd.to_datetime(sales_df['Trade Date'])
        
        print("\n🧮 Running enhanced CGT calculation...")
        
        # Run enhanced CGT calculation
        cgt_df, updated_cost_basis, warnings, processing_log = calculate_enhanced_cgt(
            sales_df, cost_basis_dict, strategy="tax_optimal"
        )
        
        print(f"\n📊 RESULTS:")
        print(f"   CGT records generated: {len(cgt_df)}")
        print(f"   Warnings: {len(warnings)}")
        print(f"   Updated symbols: {len(updated_cost_basis)}")
        print(f"   Processing log entries: {len(processing_log)}")
        
        if len(warnings) > 0:
            print(f"\n⚠️ Warnings:")
            for warning in warnings[:3]:  # Show first 3
                print(f"   • {warning}")
        
        print(f"\n✅ Basic test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_basic_test()
    if success:
        print("\n🎉 Ready for full testing!")
    else:
        print("\n🔧 Need to fix issues before proceeding.")
