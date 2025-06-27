#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from csv_processor import process_statement_csv
from cgt_calculator import calculate_enhanced_cgt_with_rba
import pandas as pd

# Use the actual files you're using
actual_files = [
    'data/2023-2024.csv',
    'data/2024-2025.csv', 
    'data/manual_added_transactions.csv'
]

print('=== PROCESSING YOUR ACTUAL DATA FILES ===')
print(f'Files: {actual_files}')

try:
    cost_basis_dict, fy24_25_sales, csv_warnings, csv_logs = process_statement_csv(actual_files)

    print('\n=== NET COST BASIS (After Historical Sales) ===')
    if 'NET' in cost_basis_dict:
        net_parcels = cost_basis_dict['NET']
        print(f'NET parcels available: {len(net_parcels)}')
        total_units = sum(p['units'] for p in net_parcels if p['units'] > 0)
        print(f'Total units available: {total_units}')
        
        print('\nIndividual parcels (after historical consumption):')
        for i, parcel in enumerate(net_parcels):
            status = "AVAILABLE" if parcel['units'] > 0 else "CONSUMED"
            print(f'  {i+1}. Date: {parcel["date"]}, Units: {parcel["units"]}, Price: ${parcel["price"]:.2f} ({status})')
    else:
        print('No NET parcels found!')

    print('\n=== FY24-25 SALES DATA ===')
    if isinstance(fy24_25_sales, pd.DataFrame):
        net_sales = fy24_25_sales[fy24_25_sales['Symbol'] == 'NET']
        print(f'NET sales in FY24-25: {len(net_sales)}')
        
        print('\nOriginal Sales Transactions:')
        for idx, sale in net_sales.iterrows():
            print(f'  {sale["Trade Date"]}: {sale["Quantity"]} units @ ${sale["Price (USD)"]:.2f}')
        
        print(f'\nTotal FY24-25 NET sales: {net_sales["Quantity"].sum()} units')

    print('\n=== RUNNING CGT CALCULATION ===')
    optimized_cgt_df, fifo_cgt_df, comparison_data, updated_cost_basis, cgt_warnings, processing_logs = calculate_enhanced_cgt_with_rba(
        fy24_25_sales, 
        cost_basis_dict, 
        strategy='comparison'
    )

    print('\n=== CGT RESULTS (What app.py receives) ===')
    net_cgt_records = optimized_cgt_df[optimized_cgt_df['symbol'] == 'NET']
    print(f'NET CGT records: {len(net_cgt_records)}')
    
    if len(net_cgt_records) > 0:
        print('\nDetailed CGT Records:')
        for idx, record in net_cgt_records.iterrows():
            print(f'  Record {idx}:')
            print(f'    Sale Date: {record["sale_date"]}')
            print(f'    Purchase Date: {record["purchase_date"]}') 
            print(f'    Units Sold: {record["units_sold"]}')
            print(f'    Buy Price: ${record["buy_unit_price_usd"]:.2f}')
            print(f'    Sale Price: ${record["sale_unit_price_usd"]:.2f}')
            print()

    print('\n=== TIMELINE VISUALIZATION SIMULATION ===')
    print('What the app.py timeline would show:')
    
    # Group by sale date to show what SHOULD appear
    if len(net_cgt_records) > 0:
        sale_summary = net_cgt_records.groupby('sale_date').agg({
            'units_sold': 'sum',
            'sale_unit_price_usd': 'first'
        }).reset_index()
        
        print('\nAggregated by sale date (correct display):')
        for idx, row in sale_summary.iterrows():
            sale_date = pd.to_datetime(row['sale_date'])
            print(f'  {sale_date.strftime("%d %b %Y")}: {row["units_sold"]:.0f} units @ ${row["sale_unit_price_usd"]:.2f}')
        
        print('\nIndividual CGT records (current display):')
        for idx, record in net_cgt_records.iterrows():
            sale_date = pd.to_datetime(record['sale_date'])
            print(f'  {sale_date.strftime("%d %b %Y")}: {record["units_sold"]:.0f} units @ ${record["sale_unit_price_usd"]:.2f} (from {record["purchase_date"]} parcel)')

    if csv_warnings or cgt_warnings:
        print(f'\n=== WARNINGS ===')
        for warning in csv_warnings + cgt_warnings:
            print(f'  {warning}')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()