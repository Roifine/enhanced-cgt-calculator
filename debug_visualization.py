#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from csv_processor import process_statement_csv
from cgt_calculator import calculate_enhanced_cgt_with_rba
import pandas as pd

# Process the NET test file
test_file = 'test_net_debug.csv'
print('=== PROCESSING NET DATA ===')
cost_basis_dict, fy24_25_sales, csv_warnings, csv_logs = process_statement_csv([test_file])

print('\n=== ORIGINAL SALES DATA ===')
print('FY24-25 Sales DataFrame:')
if isinstance(fy24_25_sales, pd.DataFrame):
    net_sales = fy24_25_sales[fy24_25_sales['Symbol'] == 'NET']
    print(net_sales[['Trade Date', 'Symbol', 'Quantity', 'Price (USD)']].to_string())
    print(f'\nTotal sales: {len(net_sales)}')
    for idx, sale in net_sales.iterrows():
        print(f'  {sale["Trade Date"]}: {sale["Quantity"]} units @ ${sale["Price (USD)"]:.2f}')

print('\n=== RUNNING CGT CALCULATION ===')
optimized_cgt_df, fifo_cgt_df, comparison_data, updated_cost_basis, cgt_warnings, processing_logs = calculate_enhanced_cgt_with_rba(
    fy24_25_sales, 
    cost_basis_dict, 
    strategy='comparison'
)

print('\n=== CGT RESULTS DATA (What app.py sees) ===')
net_cgt_records = optimized_cgt_df[optimized_cgt_df['symbol'] == 'NET']
print('CGT Records for NET:')
print(net_cgt_records[['symbol', 'sale_date', 'purchase_date', 'units_sold', 'buy_unit_price_usd', 'sale_unit_price_usd']].to_string())

print('\n=== SIMULATING TIMELINE VISUALIZATION ===')
print('What the timeline shows:')
for idx, record in net_cgt_records.iterrows():
    buy_date = pd.to_datetime(record['purchase_date'])
    sell_date = pd.to_datetime(record['sale_date'])
    buy_price_usd = record.get('buy_unit_price_usd', 0)
    sell_price_usd = record.get('sale_unit_price_usd', 0)
    units = record['units_sold']
    
    print(f'\nRecord {idx}:')
    print(f'  BUY: {buy_date.strftime("%d %b %Y")} - {units:.0f} units @ ${buy_price_usd:.2f}')
    print(f'  SELL: {sell_date.strftime("%d %b %Y")} - {units:.0f} units @ ${sell_price_usd:.2f}')

print('\n=== AGGREGATED BY SALE DATE (What should be shown) ===')
sale_aggregated = net_cgt_records.groupby('sale_date').agg({
    'units_sold': 'sum',
    'sale_unit_price_usd': 'first'  # Same price for all units on same date
}).reset_index()

print('Aggregated sales by date:')
for idx, row in sale_aggregated.iterrows():
    sale_date = pd.to_datetime(row['sale_date'])
    print(f'  {sale_date.strftime("%d %b %Y")}: {row["units_sold"]:.0f} units @ ${row["sale_unit_price_usd"]:.2f}')