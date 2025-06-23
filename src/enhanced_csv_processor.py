#!/usr/bin/env python3
"""
Enhanced CSV Processor with Multi-Format Support
Handles CSV files (Stake, IBKR, etc.) and HTML files (CommSec International)
"""

import pandas as pd
import os
import tempfile
from typing import List, Dict, Tuple, Union
from datetime import datetime
import warnings

# Import the new CommSec HTML parser
from commsec_html_parser import parse_commsec_html


def detect_file_format(file_path: str) -> str:
    """
    Detect whether file is CSV, HTML, or other format.
    
    Args:
        file_path: Path to the file
        
    Returns:
        'csv', 'html', or 'unknown'
    """
    
    # Check file extension first
    _, ext = os.path.splitext(file_path.lower())
    
    if ext == '.csv':
        return 'csv'
    elif ext in ['.html', '.htm']:
        return 'html'
    
    # If extension is unclear, check file content
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_chunk = f.read(1024).lower()
            
        if '<html' in first_chunk or '<table' in first_chunk or '<!doctype' in first_chunk:
            return 'html'
        elif ',' in first_chunk and first_chunk.count(',') > first_chunk.count('<'):
            return 'csv'
    
    except Exception:
        pass
    
    return 'unknown'


def process_single_file(file_path: str, file_source: str = "") -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Process a single file (CSV or HTML) and return standardized DataFrame.
    
    Args:
        file_path: Path to the file
        file_source: Description of file source (for logging)
        
    Returns:
        (dataframe, processing_log, warnings)
    """
    
    processing_log = []
    warnings_list = []
    
    def log_message(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {msg}"
        processing_log.append(log_entry)
        print(log_entry)
    
    log_message(f"📄 Processing file: {os.path.basename(file_path)} ({file_source})")
    
    # Detect file format
    file_format = detect_file_format(file_path)
    log_message(f"   📋 Detected format: {file_format.upper()}")
    
    try:
        if file_format == 'html':
            # Use CommSec HTML parser
            log_message("   🏦 Using CommSec International HTML parser...")
            df, html_log, html_warnings = parse_commsec_html(file_path)
            processing_log.extend(html_log)
            warnings_list.extend(html_warnings)
            
        elif file_format == 'csv':
            # Use standard CSV processing
            log_message("   📊 Using standard CSV parser...")
            df, csv_log, csv_warnings = process_csv_file(file_path)
            processing_log.extend(csv_log)
            warnings_list.extend(csv_warnings)
            
        else:
            error_msg = f"❌ Unsupported file format: {file_format}"
            log_message(error_msg)
            warnings_list.append(error_msg)
            return pd.DataFrame(), processing_log, warnings_list
        
        # Validate result
        if df.empty:
            warning_msg = f"⚠️ No valid transactions found in {os.path.basename(file_path)}"
            log_message(warning_msg)
            warnings_list.append(warning_msg)
        else:
            log_message(f"   ✅ Successfully processed {len(df)} transactions")
            
            # Add source tracking
            df['source_file'] = os.path.basename(file_path)
            df['source_format'] = file_format.upper()
        
        return df, processing_log, warnings_list
        
    except Exception as e:
        error_msg = f"❌ Error processing {os.path.basename(file_path)}: {str(e)}"
        log_message(error_msg)
        warnings_list.append(error_msg)
        return pd.DataFrame(), processing_log, warnings_list


def process_csv_file(file_path: str) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Process CSV file with robust parsing for different broker formats.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        (dataframe, processing_log, warnings)
    """
    
    processing_log = []
    warnings_list = []
    
    def log_message(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {msg}"
        processing_log.append(log_entry)
        print(log_entry)
    
    try:
        # Try different CSV reading strategies
        csv_strategies = [
            # Strategy 1: Standard UTF-8
            {'encoding': 'utf-8', 'sep': ','},
            # Strategy 2: Excel CSV
            {'encoding': 'utf-8', 'sep': ',', 'thousands': ','},
            # Strategy 3: Different encoding
            {'encoding': 'latin-1', 'sep': ','},
            # Strategy 4: Tab-separated
            {'encoding': 'utf-8', 'sep': '\t'},
        ]
        
        df = None
        for i, strategy in enumerate(csv_strategies):
            try:
                log_message(f"      🔄 Trying CSV strategy {i+1}...")
                df = pd.read_csv(file_path, **strategy)
                
                if len(df) > 0 and len(df.columns) > 3:  # Basic validation
                    log_message(f"      ✅ Strategy {i+1} successful: {len(df)} rows, {len(df.columns)} columns")
                    break
                    
            except Exception as e:
                log_message(f"      ❌ Strategy {i+1} failed: {str(e)}")
                continue
        
        if df is None or df.empty:
            raise ValueError("All CSV parsing strategies failed")
        
        # Standardize column names
        df = standardize_csv_columns(df)
        log_message(f"      📋 Standardized columns: {list(df.columns)}")
        
        # Data type conversions and cleaning
        df = clean_csv_data(df, processing_log)
        
        # Filter valid transactions
        df = filter_valid_transactions(df, warnings_list)
        
        return df, processing_log, warnings_list
        
    except Exception as e:
        error_msg = f"❌ CSV processing failed: {str(e)}"
        log_message(error_msg)
        warnings_list.append(error_msg)
        return pd.DataFrame(), processing_log, warnings_list


def standardize_csv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names across different broker CSV formats.
    
    Args:
        df: Raw DataFrame from CSV
        
    Returns:
        DataFrame with standardized column names
    """
    
    # Column mapping patterns for different brokers
    column_mapping = {
        # Symbol variations
        'symbol': ['Symbol', 'Stock Symbol', 'Ticker', 'Code', 'Security', 'Instrument'],
        
        # Date variations  
        'Trade Date': ['Trade Date', 'Date', 'Settlement Date', 'Execution Date', 'Transaction Date'],
        
        # Transaction type
        'Type': ['Type', 'Side', 'Buy/Sell', 'Transaction Type', 'Action', 'Direction'],
        
        # Quantity
        'Quantity': ['Quantity', 'Units', 'Shares', 'Qty', 'Amount', 'Volume'],
        
        # Price
        'Price (USD)': ['Price (USD)', 'Price', 'Unit Price', 'Execution Price', 'Price USD'],
        
        # Proceeds
        'Proceeds (USD)': ['Proceeds (USD)', 'Proceeds', 'Gross Amount', 'Total', 'Amount USD'],
        
        # Commission
        'Commission (USD)': ['Commission (USD)', 'Commission', 'Brokerage', 'Fees', 'Charges']
    }
    
    # Create reverse mapping (broker column -> standard column)
    reverse_mapping = {}
    for standard_col, variations in column_mapping.items():
        for variation in variations:
            reverse_mapping[variation.lower()] = standard_col
    
    # Map actual columns
    new_columns = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        
        # Direct match
        if col_lower in reverse_mapping:
            new_columns[col] = reverse_mapping[col_lower]
        # Partial match
        else:
            for broker_col, standard_col in reverse_mapping.items():
                if broker_col in col_lower or col_lower in broker_col:
                    new_columns[col] = standard_col
                    break
    
    # Rename columns
    df = df.rename(columns=new_columns)
    
    return df


def clean_csv_data(df: pd.DataFrame, processing_log: List[str]) -> pd.DataFrame:
    """
    Clean and convert data types in CSV DataFrame.
    
    Args:
        df: DataFrame with standardized columns
        processing_log: Log list to append messages
        
    Returns:
        Cleaned DataFrame
    """
    
    def log_message(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {msg}"
        processing_log.append(log_entry)
        print(log_entry)
    
    try:
        # Handle dates
        if 'Trade Date' in df.columns:
            df['Trade Date'] = pd.to_datetime(df['Trade Date'], errors='coerce')
            invalid_dates = df['Trade Date'].isna().sum()
            if invalid_dates > 0:
                log_message(f"      ⚠️ {invalid_dates} invalid dates found")
        
        # Handle transaction types
        if 'Type' in df.columns:
            df['Type'] = df['Type'].astype(str).str.upper().str.strip()
            # Standardize buy/sell variations
            df['Type'] = df['Type'].replace({
                'B': 'BUY', 'BOUGHT': 'BUY', 'PURCHASE': 'BUY',
                'S': 'SELL', 'SOLD': 'SELL', 'SALE': 'SELL'
            })
        
        # Handle numeric columns
        numeric_columns = ['Quantity', 'Price (USD)', 'Proceeds (USD)', 'Commission (USD)']
        
        for col in numeric_columns:
            if col in df.columns:
                # Remove currency symbols and convert to numeric
                df[col] = df[col].astype(str).str.replace(r'[$,]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Handle negative commissions (some brokers export as negative)
        if 'Commission (USD)' in df.columns:
            df['Commission (USD)'] = df['Commission (USD)'].abs()
        
        log_message(f"      ✅ Data cleaning completed")
        
        return df
        
    except Exception as e:
        log_message(f"      ❌ Data cleaning error: {str(e)}")
        return df


def filter_valid_transactions(df: pd.DataFrame, warnings_list: List[str]) -> pd.DataFrame:
    """
    Filter out invalid transactions and log warnings.
    
    Args:
        df: Cleaned DataFrame
        warnings_list: List to append warnings
        
    Returns:
        Filtered DataFrame
    """
    
    initial_count = len(df)
    
    # Filter conditions
    valid_mask = (
        df.get('Symbol', '').astype(str).str.strip().ne('') &  # Has symbol
        df.get('Trade Date', pd.NaT).notna() &  # Has valid date
        df.get('Type', '').isin(['BUY', 'SELL']) &  # Valid transaction type
        (df.get('Quantity', 0) > 0) &  # Positive quantity
        (df.get('Price (USD)', 0) > 0)  # Positive price
    )
    
    filtered_df = df[valid_mask].copy()
    
    removed_count = initial_count - len(filtered_df)
    if removed_count > 0:
        warning_msg = f"⚠️ Filtered out {removed_count} invalid transactions"
        warnings_list.append(warning_msg)
    
    return filtered_df


def process_statement_csv(file_paths: List[str]) -> Tuple[Dict, pd.DataFrame, List[str], List[str]]:
    """
    Enhanced version of process_statement_csv that handles both CSV and HTML files.
    
    Args:
        file_paths: List of file paths (CSV or HTML)
        
    Returns:
        (cost_basis_dict, fy24_25_sales, warnings, processing_log)
    """
    
    all_processing_logs = []
    all_warnings = []
    all_transactions = []
    
    def log_main_message(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {msg}"
        all_processing_logs.append(log_entry)
        print(log_entry)
    
    log_main_message("🚀 ENHANCED MULTI-FORMAT PROCESSOR STARTING")
    log_main_message(f"📁 Processing {len(file_paths)} files")
    
    # Process each file
    for i, file_path in enumerate(file_paths, 1):
        log_main_message(f"\n📄 File {i}/{len(file_paths)}: {os.path.basename(file_path)}")
        
        # Process individual file
        df, file_logs, file_warnings = process_single_file(file_path, f"File {i}")
        
        # Collect logs and warnings
        all_processing_logs.extend(file_logs)
        all_warnings.extend(file_warnings)
        
        # Collect transactions
        if not df.empty:
            all_transactions.append(df)
            log_main_message(f"   ✅ Added {len(df)} transactions from {os.path.basename(file_path)}")
        else:
            log_main_message(f"   ⚠️ No valid transactions from {os.path.basename(file_path)}")
    
    # Combine all transactions
    if all_transactions:
        combined_df = pd.concat(all_transactions, ignore_index=True)
        log_main_message(f"\n📊 Combined total: {len(combined_df)} transactions")
    else:
        log_main_message(f"\n❌ No valid transactions found in any files")
        return {}, pd.DataFrame(), all_warnings, all_processing_logs
    
    # Sort by date
    combined_df = combined_df.sort_values('Trade Date').reset_index(drop=True)
    
    # Build cost basis dictionary (BUY transactions)
    log_main_message(f"\n🏗️ Building cost basis dictionary...")
    cost_basis_dict = build_cost_basis_dict(combined_df, all_processing_logs)
    
    # Filter FY 2024-25 sales
    log_main_message(f"\n📅 Filtering FY 2024-25 sales...")
    fy24_25_sales = filter_fy_sales(combined_df, all_processing_logs)
    
    # Final summary
    log_main_message(f"\n✅ PROCESSING COMPLETE:")
    log_main_message(f"   📦 Cost basis symbols: {len(cost_basis_dict)}")
    log_main_message(f"   💰 FY24-25 sales: {len(fy24_25_sales)}")
    log_main_message(f"   ⚠️ Warnings: {len(all_warnings)}")
    
    return cost_basis_dict, fy24_25_sales, all_warnings, all_processing_logs


def build_cost_basis_dict(df: pd.DataFrame, processing_log: List[str]) -> Dict:
    """
    Build cost basis dictionary from BUY transactions.
    
    Args:
        df: Combined transactions DataFrame
        processing_log: Log list to append messages
        
    Returns:
        Cost basis dictionary {symbol: [parcels]}
    """
    
    def log_message(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {msg}"
        processing_log.append(log_entry)
        print(log_entry)
    
    # Filter BUY transactions
    buy_transactions = df[df['Type'] == 'BUY'].copy()
    log_message(f"   📈 Found {len(buy_transactions)} BUY transactions")
    
    cost_basis_dict = {}
    
    for _, transaction in buy_transactions.iterrows():
        symbol = transaction['Symbol']
        
        # Create parcel
        parcel = {
            'units': float(transaction['Quantity']),
            'price': float(transaction['Price (USD)']),
            'commission': float(transaction.get('Commission (USD)', 0)),
            'date': transaction['Trade Date'].strftime('%d/%m/%y') if pd.notna(transaction['Trade Date']) else ''
        }
        
        # Add to cost basis dict
        if symbol not in cost_basis_dict:
            cost_basis_dict[symbol] = []
        
        cost_basis_dict[symbol].append(parcel)
    
    log_message(f"   📦 Built cost basis for {len(cost_basis_dict)} symbols")
    
    return cost_basis_dict


def filter_fy_sales(df: pd.DataFrame, processing_log: List[str]) -> pd.DataFrame:
    """
    Filter sales transactions for FY 2024-25 (July 1, 2024 to June 30, 2025).
    
    Args:
        df: Combined transactions DataFrame
        processing_log: Log list to append messages
        
    Returns:
        Filtered sales DataFrame
    """
    
    def log_message(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {msg}"
        processing_log.append(log_entry)
        print(log_entry)
    
    # Define FY 2024-25 date range
    fy_start = pd.Timestamp('2024-07-01')
    fy_end = pd.Timestamp('2025-06-30')
    
    # Filter SELL transactions in date range
    sales_mask = (
        (df['Type'] == 'SELL') &
        (df['Trade Date'] >= fy_start) &
        (df['Trade Date'] <= fy_end)
    )
    
    fy_sales = df[sales_mask].copy()
    
    log_message(f"   💰 Found {len(fy_sales)} sales in FY 2024-25")
    
    if len(fy_sales) > 0:
        symbols_sold = fy_sales['Symbol'].nunique()
        log_message(f"   🏷️ Unique symbols sold: {symbols_sold}")
    
    return fy_sales


# Convenience function for Streamlit integration
def process_uploaded_files(uploaded_files) -> Tuple[Dict, pd.DataFrame, List[str], List[str]]:
    """
    Process files uploaded via Streamlit file_uploader.
    
    Args:
        uploaded_files: List of Streamlit UploadedFile objects
        
    Returns:
        (cost_basis_dict, fy24_25_sales, warnings, processing_log)
    """
    
    temp_file_paths = []
    
    try:
        # Save uploaded files to temporary locations
        for uploaded_file in uploaded_files:
            # Determine file extension
            file_extension = '.html' if uploaded_file.name.lower().endswith('.html') else '.csv'
            
            with tempfile.NamedTemporaryFile(mode='wb', suffix=file_extension, delete=False) as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                temp_file_paths.append(tmp_file.name)
        
        # Process using enhanced processor
        return process_statement_csv(temp_file_paths)
        
    finally:
        # Clean up temporary files
        for temp_path in temp_file_paths:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    print("🧪 Enhanced CSV/HTML Processor")
    print("Supports:")
    print("  📄 CSV files: Stake, Interactive Brokers, etc.")
    print("  🌐 HTML files: CommSec International")
    print("  🔧 Multi-format processing in single workflow")