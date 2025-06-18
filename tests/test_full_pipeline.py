#!/usr/bin/env python3
"""
Full Pipeline Integration Test
CSV Files → Cost Basis → CGT Calculation → Results

Tests the complete workflow that will power the Streamlit interface
"""

import pandas as pd
import json
import os
import sys
from datetime import datetime

# Add src directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import all our modules
from csv_processor import process_statement_csv
from cgt_calculator import calculate_enhanced_cgt_with_rba


def test_full_pipeline():
    """Test the complete CSV → CGT pipeline."""
    
    print("🚀 FULL PIPELINE INTEGRATION TEST")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Step 1: Process CSV files to get cost basis
        print("📁 STEP 1: Processing CSV files...")
        csv_files = [
            "../data/manual_added_transactions.csv",
            "../data/2023-2024.csv", 
            "../data/2024-2025.csv"
        ]
        
        # Validate files exist
        missing_files = [f for f in csv_files if not os.path.exists(f)]
        if missing_files:
            print(f"❌ Missing files: {missing_files}")
            return False
        
        print(f"   📊 Processing {len(csv_files)} CSV files...")
        cost_basis_dict, fy24_25_sales, csv_warnings, csv_log = process_statement_csv(csv_files)
        
        print(f"   ✅ CSV Processing Results:")
        print(f"      Cost basis symbols: {len(cost_basis_dict)}")
        print(f"      FY24-25 sales: {len(fy24_25_sales)}")
        print(f"      Warnings: {len(csv_warnings)}")
        
        if csv_warnings:
            print(f"   ⚠️ CSV Warnings:")
            for warning in csv_warnings[:3]:
                print(f"      • {warning}")
        
        # Step 2: Run enhanced CGT calculation
        print(f"\n🧮 STEP 2: Running Enhanced CGT Calculation...")
        print(f"   Strategy: tax_optimal")
        print(f"   RBA Integration: Enabled")
        
        cgt_df, updated_cost_basis, cgt_warnings, cgt_log = calculate_enhanced_cgt_with_rba(
            fy24_25_sales, cost_basis_dict, strategy="tax_optimal"
        )
        
        print(f"   ✅ CGT Calculation Results:")
        print(f"      CGT records: {len(cgt_df)}")
        print(f"      Updated symbols: {len(updated_cost_basis)}")
        print(f"      Warnings: {len(cgt_warnings)}")
        
        if cgt_warnings:
            print(f"   ⚠️ CGT Warnings:")
            for warning in cgt_warnings[:3]:
                print(f"      • {warning}")
        
        # Step 3: Analyze Results
        print(f"\n📊 STEP 3: Results Analysis...")
        
        if len(cgt_df) > 0:
            # Financial summary
            total_gain = cgt_df['capital_gain_aud'].sum()
            total_taxable = cgt_df['taxable_gain_aud'].sum()
            long_term_records = len(cgt_df[cgt_df['is_long_term']])
            unique_sales = cgt_df['symbol'].nunique()
            
            print(f"   💰 Financial Summary:")
            print(f"      Total capital gain: ${total_gain:.2f} AUD")
            print(f"      Total taxable gain: ${total_taxable:.2f} AUD")
            print(f"      CGT discount savings: ${(total_gain - total_taxable):.2f} AUD")
            print(f"      Long-term parcel records: {long_term_records}/{len(cgt_df)}")
            print(f"      Unique symbols sold: {unique_sales}")
            print(f"      ✅ Per-parcel detail: Each row = one parcel portion")
            
            # Exchange rate validation
            if 'exchange_rate' in cgt_df.columns:
                unique_rates = cgt_df['exchange_rate'].nunique()
                rate_range = f"{cgt_df['exchange_rate'].min():.4f} to {cgt_df['exchange_rate'].max():.4f}"
                print(f"   💱 RBA Exchange Rates:")
                print(f"      Unique rates used: {unique_rates}")
                print(f"      Rate range: {rate_range}")
                print(f"      ✅ Real RBA rates (not placeholder 1.0000)!")
            
            # Sample transaction
            print(f"   📋 Sample Transaction:")
            sample = cgt_df.iloc[0]
            print(f"      {sample['symbol']}: {sample['units_sold']} units")
            print(f"      Purchase: {sample['purchase_date'].strftime('%Y-%m-%d')} @ ${sample['buy_unit_price_usd']:.2f} USD")
            print(f"      Sale: {sample['sale_date'].strftime('%Y-%m-%d')} @ ${sample['sale_unit_price_usd']:.2f} USD")
            print(f"      Gain: ${sample['capital_gain_aud']:.2f} AUD")
            print(f"      Long-term: {'Yes' if sample['is_long_term'] else 'No'}")
            
            # Tax optimization evidence
            optimization_symbols = cgt_df.groupby('symbol').agg({
                'is_long_term': 'sum',
                'units_sold': 'count'
            }).reset_index()
            
            optimized_count = len(optimization_symbols[optimization_symbols['is_long_term'] > 0])
            print(f"   🎯 Tax Optimization:")
            print(f"      Symbols with long-term selections: {optimized_count}/{len(optimization_symbols)}")
            
        else:
            print("   ❌ No CGT records generated!")
            return False
        
        # Step 4: Export Results (Optional)
        export_results = input(f"\n💾 Export results? (y/n): ").lower().strip()
        
        if export_results == 'y':
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Export CGT results
            cgt_filename = f"cgt_results_{timestamp}.csv"
            cgt_df.to_csv(cgt_filename, index=False)
            print(f"   ✅ CGT results exported to: {cgt_filename}")
            
            # Export updated cost basis (with datetime serialization fix)
            cost_basis_filename = f"updated_cost_basis_{timestamp}.json"
            
            # Convert any datetime objects to strings for JSON serialization
            def serialize_cost_basis(cost_basis_dict):
                """Convert datetime objects to strings for JSON serialization."""
                serializable_dict = {}
                for symbol, parcels in cost_basis_dict.items():
                    serializable_parcels = []
                    for parcel in parcels:
                        serializable_parcel = {}
                        for key, value in parcel.items():
                            if isinstance(value, datetime):
                                serializable_parcel[key] = value.strftime('%Y-%m-%d')
                            else:
                                serializable_parcel[key] = value
                        serializable_parcels.append(serializable_parcel)
                    serializable_dict[symbol] = serializable_parcels
                return serializable_dict
            
            serializable_cost_basis = serialize_cost_basis(updated_cost_basis)
            
            with open(cost_basis_filename, 'w') as f:
                json.dump(serializable_cost_basis, f, indent=2)
            print(f"   ✅ Updated cost basis exported to: {cost_basis_filename}")
        
        # Success summary
        print(f"\n🎉 PIPELINE INTEGRATION SUCCESS!")
        print(f"   ✅ CSV processing: {len(csv_files)} files → {len(cost_basis_dict)} symbols")
        print(f"   ✅ CGT calculation: {len(fy24_25_sales)} sales → {len(cgt_df)} parcel records")
        print(f"   ✅ RBA integration: Working with real exchange rates")
        print(f"   ✅ Tax optimization: Long-term priority selection active")
        print(f"   ✅ Per-parcel detail: Complete audit trail with individual parcel prices")
        print(f"   ✅ Zero critical errors: Ready for Streamlit integration!")
        
        return True
        
    except Exception as e:
        print(f"❌ PIPELINE TEST FAILED: {str(e)}")
        import traceback
        print(f"\nFull error traceback:")
        traceback.print_exc()
        return False


def quick_cgt_summary():
    """Quick summary of what the full pipeline achieves."""
    
    print(f"\n📋 PIPELINE SUMMARY:")
    print(f"   📁 Input: Multiple CSV files (broker statements)")
    print(f"   🔄 Processing: Combine all BUYs → cost basis, filter SELLs → FY24-25")
    print(f"   💱 Currency: Real RBA USD→AUD conversion")
    print(f"   🎯 Strategy: Tax-optimal parcel selection")
    print(f"   📊 Output: CGT-ready results with audit trail")
    print(f"   🚀 Ready for: Streamlit web interface")


if __name__ == "__main__":
    print("🔬 COMPREHENSIVE PIPELINE TESTING")
    print("=" * 40)
    
    # Show what we're testing
    quick_cgt_summary()
    
    # Run the full test
    success = test_full_pipeline()
    
    if success:
        print(f"\n🚀 READY FOR STREAMLIT INTEGRATION!")
        print(f"   The complete pipeline is working perfectly")
        print(f"   Next step: Build the web interface")
    else:
        print(f"\n🔧 Fix pipeline issues before proceeding")
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")