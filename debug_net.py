#!/usr/bin/env python3
import sys
import os
import pandas as pd
from datetime import datetime

# Add src directory to path
current_dir = '/Users/roifine/My python projects/enhanced_cgt_test'
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import the processing modules
from csv_processor import process_statement_csv
from cgt_calculator import calculate_enhanced_cgt_with_rba

def debug_net_transactions():
    # Process the NET test file
    test_file = '/Users/roifine/My python projects/enhanced_cgt_test/test_net_debug.csv'
    print('Processing NET transactions...')

    try:
        cost_basis_dict, fy24_25_sales, csv_warnings, csv_logs = process_statement_csv([test_file])
        
        print(f'\n=== COST BASIS SUMMARY ===')
        if 'NET' in cost_basis_dict:
            net_parcels = cost_basis_dict['NET']
            print(f'NET parcels available: {len(net_parcels)}')
            total_units = sum(p['units'] for p in net_parcels)
            print(f'Total units available: {total_units}')
            
            print('\nIndividual parcels:')
            for i, parcel in enumerate(net_parcels):
                print(f'  {i+1}. Date: {parcel["date"]}, Units: {parcel["units"]}, Price: ${parcel["price"]:.2f}')
        else:
            print('No NET parcels found in cost basis!')
        
        print(f'\n=== FY24-25 SALES ===')
        print(f'Total FY24-25 sales: {len(fy24_25_sales)}')
        print(f'Sales data type: {type(fy24_25_sales)}')
        
        # Check if sales is a DataFrame
        if isinstance(fy24_25_sales, pd.DataFrame):
            print(f'Sales DataFrame shape: {fy24_25_sales.shape}')
            if not fy24_25_sales.empty:
                print(f'First sale item: {fy24_25_sales.iloc[0].to_dict()}')
            
            print(f'DataFrame columns: {list(fy24_25_sales.columns)}')
            net_sales = fy24_25_sales[fy24_25_sales['Symbol'] == 'NET']
            print(f'NET sales in FY24-25: {len(net_sales)}')
            for idx, sale in net_sales.iterrows():
                print(f'  Sale: {sale["Trade Date"]} - {sale["Quantity"]} units @ ${sale["Price (USD)"]:.2f}')
        else:
            # Assume it's a list of DataFrames or records
            for i, sale in enumerate(fy24_25_sales):
                print(f'  Sale {i+1}: {sale}')
        
        print(f'\n=== RUNNING CGT CALCULATION ===')
        if isinstance(fy24_25_sales, pd.DataFrame) and not fy24_25_sales.empty:
            optimized_cgt_df, fifo_cgt_df, comparison_data, updated_cost_basis, cgt_warnings, processing_logs = calculate_enhanced_cgt_with_rba(
                fy24_25_sales, 
                cost_basis_dict, 
                strategy="comparison"
            )
            
            print(f'CGT records generated: {len(optimized_cgt_df)}')
            if len(optimized_cgt_df) > 0:
                print('\nCGT Results:')
                print(optimized_cgt_df[['symbol', 'purchase_date', 'sale_date', 'units_sold', 'capital_gain_aud', 'taxable_gain_aud']])
        
        print(f'\n=== WARNINGS ===')
        for warning in csv_warnings + cgt_warnings:
            print(f'  {warning}')
                
    except Exception as e:
        print(f'Error processing: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_net_transactions()