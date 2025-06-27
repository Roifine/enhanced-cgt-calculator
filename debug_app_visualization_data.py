#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from csv_processor import process_statement_csv
from cgt_calculator import calculate_enhanced_cgt_with_rba
import pandas as pd

# Use the exact same files as the app
actual_files = [
    'data/2023-2024.csv',
    'data/2024-2025.csv', 
    'data/manual_added_transactions.csv'
]

print('=== APP.PY VISUALIZATION DATA DEBUG ===')
print('Simulating exactly what app.py receives and displays')

try:
    # Step 1: Process CSV files (same as app.py)
    cost_basis_dict, fy24_25_sales, csv_warnings, csv_logs = process_statement_csv(actual_files)

    # Step 2: Run CGT calculation (same as app.py)
    optimized_cgt_df, fifo_cgt_df, comparison_data, updated_cost_basis, cgt_warnings, processing_logs = calculate_enhanced_cgt_with_rba(
        fy24_25_sales, 
        cost_basis_dict, 
        strategy='comparison'
    )

    print('\n=== WHAT APP.PY RECEIVES (optimized_cgt_df) ===')
    net_cgt_records = optimized_cgt_df[optimized_cgt_df['symbol'] == 'NET'].copy()
    
    print(f'NET CGT records in DataFrame: {len(net_cgt_records)}')
    print('\nComplete NET CGT DataFrame:')
    print(net_cgt_records[['symbol', 'sale_date', 'purchase_date', 'units_sold', 'buy_unit_price_usd', 'sale_unit_price_usd']].to_string())

    print('\n=== WHAT create_symbol_timeline() PROCESSES ===')
    print('Each row becomes a pair of dots (buy + sell):')
    
    for idx, record in net_cgt_records.iterrows():
        buy_date = pd.to_datetime(record['purchase_date'])
        sell_date = pd.to_datetime(record['sale_date'])
        buy_price_usd = record.get('buy_unit_price_usd', 0)
        sell_price_usd = record.get('sale_unit_price_usd', 0)
        units = record['units_sold']
        
        print(f'\n--- CGT Record {idx} ---')
        print(f'  🔵 BLUE DOT (Buy):')
        print(f'     Date: {buy_date.strftime("%d %b %Y")}')
        print(f'     Title: "ORIGINAL PURCHASE"')
        print(f'     Units purchased: {units:.0f}')
        print(f'     Price: ${buy_price_usd:.2f} USD')
        print(f'     Used for this sale: {units:.0f} units')
        
        print(f'  🟢 GREEN DOT (Sell):')
        print(f'     Date: {sell_date.strftime("%d %b %Y")}')
        print(f'     Title: "SELL EVENT (PARCEL PORTION)"')
        print(f'     Units (from this parcel): {units:.0f}')
        print(f'     Price: ${sell_price_usd:.2f} USD')
        print(f'     From purchase: {buy_date.strftime("%d %b %Y")}')

    print('\n=== WHAT USER SEES ON TIMELINE ===')
    print('Timeline dots visible to user:')
    
    # Group by dates to show what appears
    buy_dates = {}
    sell_dates = {}
    
    for idx, record in net_cgt_records.iterrows():
        buy_date = pd.to_datetime(record['purchase_date']).strftime("%d %b %Y")
        sell_date = pd.to_datetime(record['sale_date']).strftime("%d %b %Y")
        units = record['units_sold']
        buy_price = record['buy_unit_price_usd']
        sell_price = record['sale_unit_price_usd']
        
        # Collect buy dots
        if buy_date not in buy_dates:
            buy_dates[buy_date] = []
        buy_dates[buy_date].append({
            'units': units,
            'price': buy_price,
            'record_id': idx
        })
        
        # Collect sell dots
        if sell_date not in sell_dates:
            sell_dates[sell_date] = []
        sell_dates[sell_date].append({
            'units': units,
            'price': sell_price,
            'from_purchase': buy_date,
            'record_id': idx
        })
    
    print('\n🔵 BLUE DOTS (Purchases):')
    for date, dots in sorted(buy_dates.items()):
        print(f'  {date}:')
        for i, dot in enumerate(dots):
            print(f'    Dot {i+1}: {dot["units"]:.0f} units @ ${dot["price"]:.2f} (from CGT record {dot["record_id"]})')
    
    print('\n🟢 GREEN DOTS (Sales):')
    for date, dots in sorted(sell_dates.items()):
        print(f'  {date}:')
        for i, dot in enumerate(dots):
            print(f'    Dot {i+1}: {dot["units"]:.0f} units @ ${dot["price"]:.2f} (from {dot["from_purchase"]} parcel, CGT record {dot["record_id"]})')

    print('\n=== TRANSACTION SUMMARY SECTION ===')
    print('What the "Original Transaction Summary" shows:')
    
    transaction_summary = net_cgt_records.groupby(['symbol', 'sale_date']).agg({
        'units_sold': 'sum',
        'sale_unit_price_usd': 'first'
    }).reset_index()
    
    for _, row in transaction_summary.iterrows():
        sale_date = pd.to_datetime(row['sale_date']).strftime('%d %b %Y')
        print(f'  • NET: {row["units_sold"]:.0f} units @ ${row["sale_unit_price_usd"]:.2f} on {sale_date}')

    print('\n=== DETAILED TABLE ===')
    print('What the detailed CGT records table shows:')
    print(net_cgt_records[['symbol', 'sale_date', 'purchase_date', 'units_sold', 'sale_unit_price_usd', 'capital_gain_aud']].to_string())

    print('\n=== SUMMARY ===')
    print('🎯 Key Points:')
    print(f'1. Timeline shows {len(net_cgt_records)} pairs of dots (blue + green)')
    print(f'2. Each dot represents a parcel portion, not a complete transaction')
    print(f'3. Multiple dots on same date = shares came from different purchase parcels')
    print(f'4. Transaction summary aggregates the portions back to original transaction totals')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()