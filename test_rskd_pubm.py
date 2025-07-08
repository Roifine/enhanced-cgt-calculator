#!/usr/bin/env python3
"""
Quick test to verify RSKD and PUBM CGT processing
"""

import sys
import os
sys.path.insert(0, 'src')

from csv_processor import process_statement_csv
from cgt_calculator import calculate_enhanced_cgt_with_rba
import pandas as pd

# Test with files that contain RSKD and PUBM
test_files = [
    'data/2023-2024.csv',
    'data/manual_added_transactions.csv', 
    'data/50074435_20240701_20250701_trades.csv'
]

print('Testing RSKD and PUBM CGT processing...')

# Process CSV files
cost_basis_dict, fy24_25_sales, warnings, logs = process_statement_csv(test_files)

# Run CGT calculation (suppress verbose output)
import io
import contextlib

# Capture stdout to suppress verbose output
captured_output = io.StringIO()
with contextlib.redirect_stdout(captured_output):
    cgt_df, updated_cost_basis, cgt_warnings, cgt_logs = calculate_enhanced_cgt_with_rba(
        fy24_25_sales, cost_basis_dict, strategy='tax_optimal'
    )

print(f'\nFINAL RESULTS:')
print(f'Total CGT records: {len(cgt_df)}')

if len(cgt_df) > 0:
    symbols_with_cgt = sorted(cgt_df['symbol'].unique())
    print(f'Symbols with CGT records: {symbols_with_cgt}')
    
    # Check RSKD
    if 'RSKD' in symbols_with_cgt:
        rskd_records = cgt_df[cgt_df['symbol'] == 'RSKD']
        total_gain = rskd_records['capital_gain_aud'].sum()
        total_taxable = rskd_records['taxable_gain_aud'].sum()
        print(f'\nRSKD: {len(rskd_records)} parcel records')
        print(f'  Total capital gain: ${total_gain:.2f} AUD')
        print(f'  Total taxable gain: ${total_taxable:.2f} AUD')
        print(f'  Long-term records: {len(rskd_records[rskd_records["is_long_term"]])}')
    else:
        print('\nRSKD: NO CGT RECORDS FOUND')
    
    # Check PUBM
    if 'PUBM' in symbols_with_cgt:
        pubm_records = cgt_df[cgt_df['symbol'] == 'PUBM']
        total_gain = pubm_records['capital_gain_aud'].sum()
        total_taxable = pubm_records['taxable_gain_aud'].sum()
        print(f'\nPUBM: {len(pubm_records)} parcel records')
        print(f'  Total capital gain: ${total_gain:.2f} AUD')
        print(f'  Total taxable gain: ${total_taxable:.2f} AUD')
        print(f'  Long-term records: {len(pubm_records[pubm_records["is_long_term"]])}')
    else:
        print('\nPUBM: NO CGT RECORDS FOUND')
else:
    print('NO CGT RECORDS GENERATED AT ALL')

# Check for RSKD/PUBM specific warnings
rskd_pubm_warnings = [w for w in cgt_warnings if 'RSKD' in w or 'PUBM' in w]
if rskd_pubm_warnings:
    print(f'\nRSKD/PUBM specific warnings:')
    for w in rskd_pubm_warnings:
        print(f'  - {w}')
else:
    print(f'\nNo RSKD/PUBM specific warnings found')

print(f'\nTotal warnings: {len(cgt_warnings)}')