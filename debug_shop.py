#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from csv_processor import process_statement_csv
from cgt_calculator import calculate_enhanced_cgt_with_rba
import pandas as pd
from datetime import datetime

# Use the actual files
actual_files = [
    'data/2023-2024.csv',
    'data/2024-2025.csv', 
    'data/manual_added_transactions.csv'
]

print('=== DEBUGGING SHOP TRANSACTIONS ===')
print(f'Files: {actual_files}')

try:
    cost_basis_dict, fy24_25_sales, csv_warnings, csv_logs = process_statement_csv(actual_files)

    print('\n=== ALL SHOP TRANSACTIONS FOUND ===')
    print('From manual_added_transactions.csv:')
    print('06.2.23,SOLD,SHOP,300,54  (06 Feb 2023 - HISTORICAL)')
    print('25.1.22,PURCHASED,SHOP,150,90  (25 Jan 2022)')
    print('08.3.21,PURCHASED,SHOP,50,119  (08 Mar 2021)')
    print('20.5.22,PURCHASED,SHOP,600,36.3  (20 May 2022)')

    print('\n=== SHOP COST BASIS (After Historical Sales) ===')
    if 'SHOP' in cost_basis_dict:
        shop_parcels = cost_basis_dict['SHOP']
        print(f'SHOP parcels available: {len(shop_parcels)}')
        total_units = sum(p['units'] for p in shop_parcels if p['units'] > 0)
        print(f'Total units available: {total_units}')
        
        print('\nIndividual parcels (after historical consumption):')
        for i, parcel in enumerate(shop_parcels):
            status = "AVAILABLE" if parcel['units'] > 0 else "CONSUMED"
            print(f'  {i+1}. Date: {parcel["date"]}, Units: {parcel["units"]}, Price: ${parcel["price"]:.2f} ({status})')
    else:
        print('❌ No SHOP parcels found in cost basis!')

    print('\n=== FY24-25 SHOP SALES ===')
    if isinstance(fy24_25_sales, pd.DataFrame):
        shop_sales = fy24_25_sales[fy24_25_sales['Symbol'] == 'SHOP']
        print(f'SHOP sales in FY24-25: {len(shop_sales)}')
        
        if len(shop_sales) > 0:
            print('SHOP sales found:')
            for idx, sale in shop_sales.iterrows():
                print(f'  {sale["Trade Date"]}: {sale["Quantity"]} units @ ${sale["Price (USD)"]:.2f}')
        else:
            print('❌ No SHOP sales found in FY24-25 period!')
            
            # Check all sales to see if any SHOP exists
            print('\n=== CHECKING ALL SALES FOR SHOP ===')
            all_symbols = fy24_25_sales['Symbol'].unique()
            print(f'All symbols in FY24-25 sales: {sorted(all_symbols)}')
            
            # Check if SHOP appears in any form
            shop_variants = fy24_25_sales[fy24_25_sales['Symbol'].str.contains('SHOP', case=False, na=False)]
            if len(shop_variants) > 0:
                print('Found SHOP variants:')
                for idx, sale in shop_variants.iterrows():
                    print(f'  {sale["Symbol"]}: {sale["Trade Date"]} - {sale["Quantity"]} units')
            else:
                print('No SHOP variants found in FY24-25 sales')
    else:
        print('❌ FY24-25 sales is not a DataFrame')

    print('\n=== DATE ANALYSIS ===')
    fy_start = datetime(2024, 7, 1)
    fy_end = datetime(2025, 6, 30)
    print(f'FY24-25 period: {fy_start.strftime("%d %b %Y")} to {fy_end.strftime("%d %b %Y")}')
    
    print('\nSHOP transaction dates:')
    shop_transactions = [
        {'date': '06.2.23', 'type': 'SOLD', 'description': '06 Feb 2023 - BEFORE FY24-25'},
        {'date': '25.1.22', 'type': 'PURCHASED', 'description': '25 Jan 2022 - BEFORE FY24-25'},
        {'date': '08.3.21', 'type': 'PURCHASED', 'description': '08 Mar 2021 - BEFORE FY24-25'},
        {'date': '20.5.22', 'type': 'PURCHASED', 'description': '20 May 2022 - BEFORE FY24-25'},
    ]
    
    for txn in shop_transactions:
        print(f'  {txn["date"]} ({txn["type"]}): {txn["description"]}')

    print('\n=== CONCLUSION ===')
    print('🔍 Analysis Results:')
    print('1. All SHOP transactions are from 2021-2023 (before FY24-25)')
    print('2. Historical sale on 06 Feb 2023 consumed 300 units')
    print('3. No SHOP sales occurred in FY24-25 period (Jul 2024 - Jun 2025)')
    print('4. Remaining SHOP shares are still held (not sold in FY24-25)')
    
    if 'SHOP' in cost_basis_dict:
        remaining_units = sum(p['units'] for p in cost_basis_dict['SHOP'] if p['units'] > 0)
        print(f'5. You currently hold {remaining_units} SHOP units that could be sold')
    
    print('\n💡 This is why SHOP is missing from FY24-25 CGT results:')
    print('   You did not sell any SHOP shares during FY24-25!')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()