#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from csv_processor import process_statement_csv
from cgt_calculator import calculate_enhanced_cgt_with_rba
import pandas as pd

# Use the exact same files that the app uses
actual_files = [
    'data/2023-2024.csv',
    'data/2024-2025.csv', 
    'data/manual_added_transactions.csv'
]

print('=== DEBUGGING LIVE DATA FOR NET ===')
print(f'Files: {actual_files}')

try:
    cost_basis_dict, fy24_25_sales, csv_warnings, csv_logs = process_statement_csv(actual_files)

    print('\n=== FY24-25 NET SALES FROM CSV ===')
    if isinstance(fy24_25_sales, pd.DataFrame):
        net_sales = fy24_25_sales[fy24_25_sales['Symbol'] == 'NET']
        print('Raw NET sales data:')
        for idx, sale in net_sales.iterrows():
            print(f'  {sale["Trade Date"]}: {sale["Quantity"]} units @ ${sale["Price (USD)"]:.2f}')
        
        total_net_sales = net_sales['Quantity'].sum()
        print(f'\nTotal NET units sold in FY24-25: {total_net_sales}')

    print('\n=== RUNNING CGT CALCULATION ===')
    optimized_cgt_df, fifo_cgt_df, comparison_data, updated_cost_basis, cgt_warnings, processing_logs = calculate_enhanced_cgt_with_rba(
        fy24_25_sales, 
        cost_basis_dict, 
        strategy='comparison'
    )

    print('\n=== NET CGT RECORDS (What timeline sees) ===')
    net_cgt_records = optimized_cgt_df[optimized_cgt_df['symbol'] == 'NET']
    
    if len(net_cgt_records) > 0:
        print('Individual CGT records (what each dot shows):')
        for idx, record in net_cgt_records.iterrows():
            sale_date = pd.to_datetime(record['sale_date']).strftime('%d %b %Y')
            purchase_date = pd.to_datetime(record['purchase_date']).strftime('%d %b %Y')
            print(f'  Record {idx}: {record["units_sold"]:.0f} units sold on {sale_date} (from {purchase_date} purchase)')
        
        print(f'\nTotal CGT records: {len(net_cgt_records)}')
        
        # Group by sale date to see what SHOULD be displayed as totals
        print('\n=== AGGREGATED BY SALE DATE ===')
        sale_summary = net_cgt_records.groupby('sale_date').agg({
            'units_sold': 'sum',
            'sale_unit_price_usd': 'first'
        }).reset_index()
        
        print('What the summary should show:')
        for idx, row in sale_summary.iterrows():
            sale_date = pd.to_datetime(row['sale_date']).strftime('%d %b %Y')
            print(f'  {sale_date}: {row["units_sold"]:.0f} units @ ${row["sale_unit_price_usd"]:.2f} (TOTAL)')
        
        # Check for any data inconsistencies
        print('\n=== CHECKING FOR DATA ISSUES ===')
        original_total = net_sales['Quantity'].sum() if len(net_sales) > 0 else 0
        cgt_total = net_cgt_records['units_sold'].sum()
        
        print(f'Original sales total: {original_total} units')
        print(f'CGT records total: {cgt_total:.0f} units')
        
        if abs(original_total - cgt_total) > 0.1:
            print('⚠️ MISMATCH detected between original sales and CGT records!')
        else:
            print('✅ Totals match - the issue is in display logic')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()