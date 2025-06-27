#!/usr/bin/env python3
"""
Comprehensive NET Transaction Verification Test
Uses existing data files and manual NET transactions to verify CGT calculations
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from csv_processor import process_statement_csv
from cgt_calculator import calculate_enhanced_cgt_with_rba

def create_net_test_data():
    """Create complete NET transaction data for verification."""
    
    # Create combined CSV with all NET transactions based on your data
    net_transactions = """Date,Activity_Type,Symbol,Quantity,Price_USD,USD_Amount,AUD_Amount
06.10.21,PURCHASED,NET,65,113.0,-7375.0,-10161.0
08.12.21,PURCHASED,NET,78,147.38,-11531.0,-16102.0
10.01.22,PURCHASED,NET,150,104.739,-15759.0,-22010.0
22.03.22,SOLD,NET,150,125.0,18691.0,24843.0
20.05.22,PURCHASED,NET,300,55.54,-16714.0,-23785.0
09.11.22,PURCHASED,NET,300,41.0,-12338.0,-19165.0
09.02.24,SOLD,NET,200,112.0,22356.0,35000.0
07.02.24,SOLD,NET,113,157.0,17705.52,28241.0
04.04.24,PURCHASED,NET,150,99.0,-14850.0,-23821.0
01.05.24,SOLD,NET,100,124.0,12375.2,19360.0"""
    
    # Write to temporary file
    temp_file = '/tmp/net_complete_transactions.csv'
    with open(temp_file, 'w') as f:
        f.write(net_transactions)
    
    return temp_file

def manual_net_calculation():
    """Manual calculation for verification."""
    
    print("\n" + "="*60)
    print("📊 MANUAL NET CALCULATION FOR VERIFICATION")
    print("="*60)
    
    # Define NET purchases (chronological order)
    purchases = [
        {'date': '06.10.21', 'units': 65, 'price_usd': 113.0, 'total_usd': 7375.0},
        {'date': '08.12.21', 'units': 78, 'price_usd': 147.38, 'total_usd': 11531.0},
        {'date': '10.01.22', 'units': 150, 'price_usd': 104.739, 'total_usd': 15759.0},
        {'date': '20.05.22', 'units': 300, 'price_usd': 55.54, 'total_usd': 16662.0},  # Adjusted
        {'date': '09.11.22', 'units': 300, 'price_usd': 41.0, 'total_usd': 12300.0},   # Adjusted
        {'date': '04.04.25', 'units': 150, 'price_usd': 99.0, 'total_usd': 14850.0},
    ]
    
    # Historical sales (pre-FY25)
    historical_sales = [
        {'date': '22.03.22', 'units': 150, 'price_usd': 125.0},
        {'date': '09.02.24', 'units': 200, 'price_usd': 112.0},
    ]
    
    # FY24-25 sales
    fy25_sales = [
        {'date': '07.02.25', 'units': 113, 'price_usd': 157.0},
        {'date': '01.05.25', 'units': 100, 'price_usd': 124.0},
    ]
    
    print("\n🟢 PURCHASES (Chronological):")
    total_purchased = 0
    for i, purchase in enumerate(purchases, 1):
        total_purchased += purchase['units']
        print(f"  {i}. {purchase['date']}: {purchase['units']} units @ ${purchase['price_usd']:.2f}")
    print(f"     Total purchased: {total_purchased} units")
    
    print("\n🔴 HISTORICAL SALES (Applied via FIFO):")
    remaining_units = total_purchased
    consumed_units = 0
    for sale in historical_sales:
        consumed_units += sale['units']
        remaining_units -= sale['units']
        print(f"  {sale['date']}: Sold {sale['units']} units @ ${sale['price_usd']:.2f}")
    print(f"     Historical sales consumed: {consumed_units} units")
    print(f"     Remaining for FY25: {remaining_units} units")
    
    print("\n🔵 FY24-25 SALES:")
    fy25_total = 0
    for sale in fy25_sales:
        fy25_total += sale['units']
        print(f"  {sale['date']}: {sale['units']} units @ ${sale['price_usd']:.2f}")
    print(f"     Total FY25 sales: {fy25_total} units")
    print(f"     Units remaining after FY25: {remaining_units - fy25_total} units")
    
    # FIFO cost basis analysis
    print("\n📦 COST BASIS ANALYSIS (After Historical FIFO Consumption):")
    print("Historical sales consumed units in FIFO order:")
    print("  1. 65 units from 06.10.21 @ $113.00 (consumed)")
    print("  2. 78 units from 08.12.21 @ $147.38 (consumed)")
    print("  3. 150 units from 10.01.22 @ $104.739 (consumed)")
    print("  4. 57 units from 20.05.22 @ $55.54 (consumed)")
    print("  Remaining parcels for FY25 sales:")
    print("  5. 243 units from 20.05.22 @ $55.54 (available)")
    print("  6. 300 units from 09.11.22 @ $41.00 (available)")
    print("  7. 150 units from 04.04.25 @ $99.00 (available)")
    
    print("\n💰 EXPECTED FY25 CGT RESULTS:")
    print("Sale 1 (07.02.25): 113 units @ $157.00")
    print("  - Uses 113 units from 20.05.22 parcel @ $55.54")
    print("  - Gain per unit: $157.00 - $55.54 = $101.46")
    print("  - Total gain: 113 × $101.46 = $11,465 USD")
    print("  - Long-term (>12 months) = 50% CGT discount")
    
    print("\nSale 2 (01.05.25): 100 units @ $124.00")
    print("  - Uses 100 units from remaining 20.05.22 parcel @ $55.54")
    print("  - Gain per unit: $124.00 - $55.54 = $68.46")
    print("  - Total gain: 100 × $68.46 = $6,846 USD")
    print("  - Long-term (>12 months) = 50% CGT discount")
    
    print(f"\nExpected total USD gain: ${11465 + 6846:,}")
    print(f"Expected total AUD gain (after currency conversion): ~${(11465 + 6846) * 1.6:.0f}")
    
    return {
        'total_purchased': total_purchased,
        'historical_consumed': consumed_units,
        'remaining_before_fy25': remaining_units,
        'fy25_sales': fy25_total,
        'expected_usd_gain': 11465 + 6846
    }

def test_net_with_system():
    """Test NET transactions with the actual system."""
    
    print("\n" + "="*60)
    print("🧪 SYSTEM CALCULATION TEST")
    print("="*60)
    
    # Create test data file
    test_file = create_net_test_data()
    
    try:
        # Process with the system
        cost_basis_dict, fy24_25_sales, csv_warnings, csv_logs = process_statement_csv([test_file])
        
        print(f"\n📊 PROCESSING RESULTS:")
        print(f"   Cost basis symbols: {len(cost_basis_dict)}")
        print(f"   FY24-25 sales: {len(fy24_25_sales)}")
        print(f"   Warnings: {len(csv_warnings)}")
        
        # Show NET cost basis
        if 'NET' in cost_basis_dict:
            net_parcels = cost_basis_dict['NET']
            print(f"\n📦 NET COST BASIS (After Historical Sales):")
            total_units = 0
            for i, parcel in enumerate(net_parcels, 1):
                if parcel['units'] > 0:
                    total_units += parcel['units']
                    print(f"   {i}. {parcel['date']}: {parcel['units']} units @ ${parcel['price']:.2f}")
                else:
                    print(f"   {i}. {parcel['date']}: {parcel['units']} units @ ${parcel['price']:.2f} (consumed)")
            print(f"   Total available: {total_units} units")
        
        # Show FY25 sales
        if isinstance(fy24_25_sales, pd.DataFrame):
            net_sales = fy24_25_sales[fy24_25_sales['Symbol'] == 'NET']
            print(f"\n📈 FY24-25 NET SALES:")
            for idx, sale in net_sales.iterrows():
                print(f"   {sale['Trade Date']}: {sale['Quantity']} units @ ${sale['Price (USD)']:.2f}")
        
        # Run CGT calculation
        if not fy24_25_sales.empty:
            print(f"\n🧮 RUNNING CGT CALCULATION...")
            optimized_cgt_df, fifo_cgt_df, comparison_data, updated_cost_basis, cgt_warnings, processing_logs = calculate_enhanced_cgt_with_rba(
                fy24_25_sales, 
                cost_basis_dict, 
                strategy="comparison"
            )
            
            # Show results
            net_results = optimized_cgt_df[optimized_cgt_df['symbol'] == 'NET']
            print(f"\n💰 CGT RESULTS FOR NET:")
            total_gain_aud = 0
            total_taxable_aud = 0
            
            for idx, result in net_results.iterrows():
                total_gain_aud += result['capital_gain_aud']
                total_taxable_aud += result['taxable_gain_aud']
                print(f"   Sale {idx+1}: {result['units_sold']} units")
                print(f"     Purchase: {result['purchase_date']} @ ${result['buy_unit_price_usd']:.2f} USD")
                print(f"     Sale: {result['sale_date']} @ ${result['sale_unit_price_usd']:.2f} USD")
                print(f"     Capital gain: ${result['capital_gain_aud']:.2f} AUD")
                print(f"     Taxable gain: ${result['taxable_gain_aud']:.2f} AUD")
                print(f"     Long-term: {result['is_long_term']}")
                print()
            
            print(f"   TOTAL CAPITAL GAIN: ${total_gain_aud:.2f} AUD")
            print(f"   TOTAL TAXABLE GAIN: ${total_taxable_aud:.2f} AUD")
            
            return {
                'system_total_gain_aud': total_gain_aud,
                'system_taxable_gain_aud': total_taxable_aud,
                'system_records': len(net_results)
            }
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.unlink(test_file)

def compare_results(manual_results, system_results):
    """Compare manual vs system results."""
    
    print("\n" + "="*60)
    print("🔍 VERIFICATION COMPARISON")
    print("="*60)
    
    if system_results:
        print(f"\n📊 SUMMARY:")
        print(f"   Manual expected USD gain: ${manual_results['expected_usd_gain']:,}")
        print(f"   System calculated AUD gain: ${system_results['system_total_gain_aud']:,.2f}")
        print(f"   System taxable AUD gain: ${system_results['system_taxable_gain_aud']:,.2f}")
        print(f"   CGT records generated: {system_results['system_records']}")
        
        # Rough currency conversion check (USD to AUD ~1.6)
        expected_aud_gain = manual_results['expected_usd_gain'] * 1.6
        actual_aud_gain = system_results['system_total_gain_aud']
        
        print(f"\n💱 CURRENCY CONVERSION CHECK:")
        print(f"   Expected AUD (rough): ${expected_aud_gain:,.0f}")
        print(f"   System calculated AUD: ${actual_aud_gain:,.2f}")
        print(f"   Difference: ${abs(expected_aud_gain - actual_aud_gain):,.2f}")
        
        # Verification status
        if abs(expected_aud_gain - actual_aud_gain) / expected_aud_gain < 0.1:  # Within 10%
            print(f"\n✅ VERIFICATION PASSED: Results are within expected range")
        else:
            print(f"\n⚠️ VERIFICATION NEEDS REVIEW: Significant difference found")
        
        print(f"\n🔍 The system is using professional RBA exchange rates")
        print(f"   which explains any differences from rough estimates.")
    else:
        print(f"\n❌ VERIFICATION FAILED: System test did not complete")

def main():
    """Run the complete NET verification test."""
    
    print("🧪 NET TRANSACTION VERIFICATION TEST")
    print("="*60)
    print("This test verifies NET CGT calculations using:")
    print("• Manual calculations based on your transaction data")
    print("• System processing with actual CGT calculator")
    print("• Professional RBA currency conversion")
    print("• FIFO cost basis consumption for historical sales")
    
    # Run manual calculation
    manual_results = manual_net_calculation()
    
    # Run system test
    system_results = test_net_with_system()
    
    # Compare results
    compare_results(manual_results, system_results)
    
    print(f"\n🏁 NET VERIFICATION TEST COMPLETE")

if __name__ == "__main__":
    main()