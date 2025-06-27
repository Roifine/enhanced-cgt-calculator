#!/usr/bin/env python3
"""
CSV Statement Processor for Australian CGT System
Converts broker CSV statements into cost basis JSON + FY24-25 sales DataFrame
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional
import warnings


class StatementProcessor:
    """
    Processes broker CSV statements into cost basis and sales data.
    
    Key Features:
    - Separates BUY transactions (cost basis) from SELL transactions
    - Filters sales to FY24-25 (July 1, 2024 to June 30, 2025)
    - Maintains chronological order for tax optimization
    - Handles multiple date formats and validates data
    """
    def clean_currency_value(self,value):
        """Clean currency values by removing $ signs, commas, and converting to float."""
        if pd.isna(value) or value is None:
            return 0.0
        
        # Convert to string and clean
        cleaned = str(value).strip()
        
        # Remove currency symbols and formatting
        cleaned = cleaned.replace('$', '').replace(',', '').replace(' ', '')
        
        # Handle empty strings
        if not cleaned or cleaned == '':
            return 0.0
        
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    
    def __init__(self):
        self.processing_log = []
        self.warnings = []
        
        # Australian FY24-25 boundaries
        self.fy_start = datetime(2024, 7, 1)
        self.fy_end = datetime(2025, 6, 30)
    
    def process_statement_csv(self, csv_files) -> Tuple[Dict, pd.DataFrame, List[str], List[str]]:
        """
        Main processing function: Multiple CSVs → Cost Basis JSON + Sales DataFrame
        
        Args:
            csv_files: Single CSV file or list of CSV files (file-like objects or paths)
            
        Returns:
            (cost_basis_dict, fy24_25_sales_df, warnings, processing_log)
        """
        
        # Handle single file or multiple files
        if not isinstance(csv_files, list):
            csv_files = [csv_files]
        
        self._log(f"🗂️ Processing {len(csv_files)} broker statement CSV file(s)...")
        
        # Collect all transactions from all files
        all_buy_transactions = pd.DataFrame()
        all_sell_transactions = pd.DataFrame()
        
        try:
            # Process each CSV file
            for i, csv_file in enumerate(csv_files, 1):
                self._log(f"\n📁 Processing file {i}/{len(csv_files)}: {getattr(csv_file, 'name', str(csv_file))}")
                
                # 1. Load and validate CSV structure
                df = self._load_and_validate_csv(csv_file)
            
                
                # 2. Detect currency and normalize columns
                currency = self._detect_currency(df)
                self._log(f"   💱 Detected currency: {currency}")
                
                # 3. Parse and standardize dates
                df = self._parse_dates(df)
                
                # 4. Separate BUY vs SELL transactions for this file
                buy_transactions, sell_transactions = self._separate_transactions(df)
                
                # 5. Add file source for tracking
                buy_transactions['source_file'] = f"File_{i}"
                sell_transactions['source_file'] = f"File_{i}"
                
                # 6. Combine with previous files
                all_buy_transactions = pd.concat([all_buy_transactions, buy_transactions], ignore_index=True)
                all_sell_transactions = pd.concat([all_sell_transactions, sell_transactions], ignore_index=True)
                
                self._log(f"   📊 File {i} added: {len(buy_transactions)} buys, {len(sell_transactions)} sells")
            
            # 7. Combined summary
            self._log(f"\n📊 COMBINED RESULTS FROM {len(csv_files)} FILES:")
            self._log(f"   🟢 Total BUY transactions: {len(all_buy_transactions)}")
            self._log(f"   🔴 Total SELL transactions: {len(all_sell_transactions)}")
            
            # 8. Filter sales to FY24-25 only (from ALL files)
            fy24_25_sales = self._filter_fy24_25_sales(all_sell_transactions)
            
            # 9. Build cost basis JSON from ALL buys (chronologically ordered)
            cost_basis_dict = self._build_cost_basis_json(all_buy_transactions)
            
            # 10. Get historical sales (exclude FY24-25 sales from all sales)
            historical_sales = all_sell_transactions[~all_sell_transactions.index.isin(fy24_25_sales.index)]
            
            # 11. Apply historical sales to cost basis (FIFO consumption)
            adjusted_cost_basis_dict = self._apply_historical_sales_to_cost_basis(cost_basis_dict, historical_sales)
            
            # 12. Validate sufficient shares for each sale using adjusted cost basis
            self._validate_sufficient_shares(adjusted_cost_basis_dict, fy24_25_sales)
            
            # 13. Summary
            self._log_processing_summary(adjusted_cost_basis_dict, fy24_25_sales)
            
            # 14. Convert column names for CGT calculator compatibility (at the very end)
            fy24_25_sales_for_cgt = self._prepare_sales_for_cgt_calculator(fy24_25_sales)
            
            # Return the adjusted cost basis that accounts for historical sales
            return adjusted_cost_basis_dict, fy24_25_sales_for_cgt, self.warnings, self.processing_log
            
        except Exception as e:
            error_msg = f"❌ Processing failed: {str(e)}"
            self._log(error_msg)
            self.warnings.append(error_msg)
            raise
    
    
    def _load_and_validate_csv(self, csv_file) -> pd.DataFrame:
        """Load CSV and validate required columns."""
        
        try:
            # Handle both file path and file-like objects
            if hasattr(csv_file, 'read'):
                df = pd.read_csv(csv_file)
            else:
                df = pd.read_csv(csv_file)
            
            self._log(f"📊 Loaded CSV: {len(df)} total transactions")
            
            # Required columns (flexible naming)
            required_mappings = {
                'symbol': ['Symbol', 'Ticker', 'Stock', 'Security'],
                'date': ['Trade Date', 'Date', 'Transaction Date', 'Execution Date'],
                'type': ['Type', 'Transaction Type', 'Action', 'Side', 'Activity_Type', 'Activity Type'],
                'quantity': ['Quantity', 'Shares', 'Units', 'Qty'],
                'price': ['Price (USD)', 'Price', 'Unit Price', 'Execution Price', 'Price_USD', 'Price USD'],
                'commission': ['Commission (USD)', 'Commission', 'Fees', 'Commission & Fees', 'Commission_USD', 'Commission USD']
            }
            
            # Map columns to standard names
            column_mapping = {}
            for standard_name, possible_names in required_mappings.items():
                found_column = None
                for possible in possible_names:
                    if possible in df.columns:
                        found_column = possible
                        break
                
                if found_column:
                    column_mapping[found_column] = standard_name
                elif standard_name == 'commission':
                    # Commission is optional - we'll add default later
                    self._log(f"   ⚠️ No commission column found, will use default value")
                    continue
                else:
                    raise ValueError(f"Required column not found. Need one of: {possible_names}")
            
            # Rename columns to standard names
            df = df.rename(columns=column_mapping)
            
            # Add commission column if missing (with default value)
            if 'commission' not in df.columns:
                default_commission = 0.0  # Default to $0 commission
                df['commission'] = default_commission
                self._log(f"   ✅ Added default commission column: ${default_commission}")
            
            # Validate we have the required columns now (commission is now guaranteed to exist)
            required_columns = ['symbol', 'date', 'type', 'quantity', 'price', 'commission']
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns after mapping: {missing}")
            
            self._log(f"✅ Column validation passed")
            self._log(f"   📋 Mapped columns: {column_mapping}")
            if 'commission' not in column_mapping:
                self._log(f"   📋 Added default commission column")
            
            return df
            
        except Exception as e:
            error_msg = f"CSV validation failed: {str(e)}"
            self._log(error_msg)
            raise ValueError(error_msg)
    
    def _detect_currency(self, df: pd.DataFrame) -> str:
        """Detect currency from column names and data."""
        
        # Check column names for currency indicators
        price_column = None
        for col in df.columns:
            if 'price' in col.lower():
                price_column = col
                break
        
        if price_column:
            if 'USD' in price_column or '$' in price_column:
                return 'USD'
            elif 'AUD' in price_column or 'A$' in price_column:
                return 'AUD'
        
        # Default to USD (most common for international brokers)
        self._log("⚠️ Currency not explicitly detected, assuming USD")
        return 'USD'
    
    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse dates and add standardized date column."""
        
        self._log("📅 Parsing transaction dates...")
        
        def parse_single_date(date_str):
            """Parse individual date string to your existing format."""
            
            if pd.isna(date_str) or not date_str:
                return None
            
            date_str = str(date_str).strip()
            
            # Common CSV date formats - UPDATED ORDER (most likely first)
            date_formats = [
                "%d-%b-%y",      # 28-Nov-05, 13-Jul-09  ← ADD THIS
                "%d-%b-%Y",      # 28-Nov-2005
                "%Y-%m-%d %H:%M:%S",  # 2023-09-18 10:39:42 (your actual format!)
                "%Y-%m-%d",     # 2024-12-19 (ISO)
                "%d.%m.%y",     # 19.12.24, 17.11.21 (existing)
                "%d.%m.%Y",     # 19.12.2024
                "%m.%d.%y",     # 11.17.21 (US format with dots)
                "%m/%d/%Y",     # 12/19/2024 (US)
                "%d/%m/%Y",     # 19/12/2024 (AU)
                "%d/%m/%y",     # 19/12/24 (AU short) 
                "%m/%d/%y",     # 12/19/24 (US short)
                "%d-%m-%Y",     # 19-12-2024
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    
                    # Handle 2-digit years (same logic as existing parser)
                    if parsed_date.year < 2000:
                        if parsed_date.year < 50:
                            parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
                        else:
                            parsed_date = parsed_date.replace(year=parsed_date.year + 1900)
                    
                    # Convert to your existing format: "18.09.23"
                    return parsed_date.strftime("%d.%m.%y")
                    
                except ValueError:
                    continue
            
            # If no format works, log warning but don't fail
            self.warnings.append(f"⚠️ Could not parse date: {date_str}")
            return None
        
        # Parse dates and create both parsed and datetime columns
        df['parsed_date'] = df['date'].apply(parse_single_date)
        df['datetime'] = pd.to_datetime(df['date'], errors='coerce')  # Removed deprecated parameter
        
        # Count successful parsing
        successful_parses = df['parsed_date'].notna().sum()
        total_rows = len(df)
        
        self._log(f"   ✅ Successfully parsed {successful_parses}/{total_rows} dates")
        
        # Show sample of successful parsing for verification
        if successful_parses > 0:
            sample_parsed = df[df['parsed_date'].notna()][['date', 'parsed_date']].head(3)
            self._log(f"   📋 Sample successful parsing:")
            for _, row in sample_parsed.iterrows():
                self._log(f"      '{row['date']}' → '{row['parsed_date']}'")
        
        if successful_parses < total_rows * 0.95:  # Alert if less than 95% success
            self.warnings.append(f"⚠️ Some dates failed to parse ({total_rows - successful_parses} failures)")
            
            # Show sample failures for debugging
            failed_dates = df[df['parsed_date'].isna()]['date'].head(3).tolist()
            if failed_dates:
                self._log(f"   ❌ Sample failed dates: {failed_dates}")
        
        return df
    
    def _separate_transactions(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Separate BUY and SELL transactions."""
        
        # Normalize transaction types
        df['type_normalized'] = df['type'].str.upper().str.strip()
        
        # Show unique transaction types for debugging
        unique_types = df['type_normalized'].unique()
        self._log(f"   📊 Found transaction types: {list(unique_types)}")
        
        # Identify BUY transactions
        buy_patterns = ['BUY', 'PURCHASE', 'PURCHASED', 'ACQUIRED', 'B', 'BOUGHT', 'LONG', 'PURCH', 'ADDED']
        buy_mask = df['type_normalized'].isin(buy_patterns)
        buy_transactions = df[buy_mask].copy()
        
        # Identify SELL transactions  
        sell_patterns = ['SELL', 'SOLD', 'SALE', 'S', 'SHORT']
        sell_mask = df['type_normalized'].isin(sell_patterns)
        sell_transactions = df[sell_mask].copy()
        
        # 🔧 FIX NEGATIVE QUANTITIES FOR SALES - ADD THIS SECTION:
        if len(sell_transactions) > 0:
        # Check for negative quantities in sales
            negative_count = (sell_transactions['quantity'] < 0).sum()
            if negative_count > 0:
                self._log(f"   🔧 Found {negative_count} negative sale quantities, converting to positive")
                # Convert negative quantities to positive
                sell_transactions['quantity'] = sell_transactions['quantity'].abs()
            
        # Log results
        other_transactions = len(df) - len(buy_transactions) - len(sell_transactions)
        
        self._log(f"📊 Transaction breakdown:")
        self._log(f"   🟢 BUY transactions: {len(buy_transactions)}")
        self._log(f"   🔴 SELL transactions: {len(sell_transactions)}")
        
        if other_transactions > 0:
            self._log(f"   ⚪ Other transactions: {other_transactions} (ignored)")
            other_types = df[~(buy_mask | sell_mask)]['type_normalized'].unique()
            self._log(f"      Types: {', '.join(other_types)}")
            
            # Suggest adding these types
            unknown_types = [t for t in other_types if t not in buy_patterns + sell_patterns]
            if unknown_types:
                self.warnings.append(f"⚠️ Unknown transaction types found: {', '.join(unknown_types)}. Consider adding to buy/sell patterns.")
        
        return buy_transactions, sell_transactions
    
    def _is_date_in_fy24_25(self, parsed_date_str):
        """Check if a parsed date string falls within FY24-25."""
        try:
            dt = datetime.strptime(parsed_date_str, "%d.%m.%y")
            # Handle 2-digit years
            if dt.year < 2000:
                dt = dt.replace(year=dt.year + 2000 if dt.year < 50 else dt.year + 1900)
            return self.fy_start <= dt <= self.fy_end
        except:
            return False

    def _filter_fy24_25_sales(self, sell_transactions: pd.DataFrame) -> pd.DataFrame:
        """Filter SELL transactions to FY24-25 only."""
        
        if sell_transactions.empty:
            self._log("⚠️ No sell transactions found")
            return sell_transactions
        
        # Create the mask
        fy24_25_mask = sell_transactions['parsed_date'].apply(
            lambda x: self._is_date_in_fy24_25(x) if x else False
        )
        
        # Apply the mask
        fy24_25_sales = sell_transactions[fy24_25_mask].copy()
        
        # Log results
        self._log(f"📅 FY24-25 sales filter:")
        self._log(f"   Total sales: {len(sell_transactions)}")
        self._log(f"   FY24-25 sales: {len(fy24_25_sales)}")
        self._log(f"   Period: {self.fy_start.strftime('%d %b %Y')} to {self.fy_end.strftime('%d %b %Y')}")
        
        if len(fy24_25_sales) == 0:
            self.warnings.append("⚠️ No sales found in FY24-25 period")
        
        return fy24_25_sales
    
    def _prepare_sales_for_cgt_calculator(self, fy24_25_sales: pd.DataFrame) -> pd.DataFrame:
        """Convert column names to format expected by CGT calculator."""
        
        if fy24_25_sales.empty:
            return fy24_25_sales
        
        # Convert back to expected column names for CGT calculator compatibility
        expected_columns = {
            'symbol': 'Symbol',
            'date': 'Trade Date', 
            'type': 'Type',
            'quantity': 'Quantity',
            'price': 'Price (USD)',
            'commission': 'Commission (USD)'
        }
        
        # Rename columns back to expected format
        fy24_25_sales_renamed = fy24_25_sales.rename(columns=expected_columns)
        
        self._log(f"   ✅ Column names converted for CGT calculator compatibility")
        
        return fy24_25_sales_renamed
    
    def _build_cost_basis_json(self, buy_transactions: pd.DataFrame) -> Dict:
        """Build cost basis dictionary from BUY transactions."""
        
        if buy_transactions.empty:
            self._log("⚠️ No buy transactions found")
            return {}
        
        self._log(f"🏗️ Building cost basis from {len(buy_transactions)} buy transactions...")
        
        cost_basis_dict = {}
        
        # Group by symbol and sort chronologically within each symbol
        for symbol, symbol_buys in buy_transactions.groupby('symbol'):
            
            # Sort by datetime (chronological order for tax optimization)
            symbol_buys_sorted = symbol_buys.sort_values('datetime')
            
            parcels = []
            for _, transaction in symbol_buys_sorted.iterrows():    
    
                # Handle missing values with sensible defaults and fix negative commissions
                units = float(transaction['quantity']) if pd.notna(transaction['quantity']) else 0.0  # Quantity usually no $ sign
                price = self.clean_currency_value(transaction['price']) if pd.notna(transaction['price']) else 0.0
                commission_raw = self.clean_currency_value(transaction['commission']) if pd.notna(transaction['commission']) else 0.0
                
                # Fix negative commission issue (brokers often show commissions as negative)
                commission = abs(commission_raw) if commission_raw != 0 else 0.0
                if commission_raw < 0:
                    self._log(f"   💰 Fixed negative commission: {commission_raw} → {commission}")
                
                date = transaction['parsed_date'] if pd.notna(transaction['parsed_date']) else "1.1.20"
                
                # Skip invalid transactions
                if units <= 0 or price <= 0:
                    self.warnings.append(f"⚠️ Skipping invalid transaction: {symbol} - units={units}, price={price}")
                    continue
                
                parcel = {
                    "units": units,
                    "price": price,
                    "commission": commission,
                    "date": date
                }
                parcels.append(parcel)
            
            if parcels:
                cost_basis_dict[symbol] = parcels
                total_units = sum(p['units'] for p in parcels)
                self._log(f"   📦 {symbol}: {len(parcels)} parcels, {total_units} total units")
        
        return cost_basis_dict
    
    def _apply_historical_sales_to_cost_basis(self, cost_basis_dict: Dict, all_sell_transactions: pd.DataFrame) -> Dict:
        """Apply FIFO consumption of historical sales to reduce cost basis units."""
        
        self._log("🔧 Applying historical sales to cost basis using FIFO...")
        
        if all_sell_transactions.empty:
            self._log("   ✅ No historical sales to apply")
            return cost_basis_dict
        
        # Create a deep copy to avoid modifying the original
        adjusted_cost_basis = {}
        for symbol, parcels in cost_basis_dict.items():
            adjusted_cost_basis[symbol] = [parcel.copy() for parcel in parcels]
        
        # Group historical sales by symbol and sort chronologically
        for symbol, symbol_sales in all_sell_transactions.groupby('symbol'):
            if symbol not in adjusted_cost_basis:
                continue
                
            # Sort sales chronologically
            symbol_sales_sorted = symbol_sales.sort_values('datetime')
            
            total_historical_sold = 0
            
            # Apply each historical sale using FIFO
            for _, sale in symbol_sales_sorted.iterrows():
                sale_quantity = float(sale['quantity'])
                total_historical_sold += sale_quantity
                remaining_to_consume = sale_quantity
                
                # Consume from cost basis parcels in FIFO order
                for parcel in adjusted_cost_basis[symbol]:
                    if remaining_to_consume <= 0:
                        break
                        
                    if parcel['units'] > 0:
                        consumed = min(parcel['units'], remaining_to_consume)
                        parcel['units'] -= consumed
                        remaining_to_consume -= consumed
                
                # If we couldn't consume all shares, we have an overselling situation
                if remaining_to_consume > 0:
                    self._log(f"   ⚠️ {symbol}: Historical overselling detected - couldn't consume {remaining_to_consume} shares from sale on {sale['parsed_date']}")
            
            # Log the adjustment for this symbol
            if total_historical_sold > 0:
                remaining_units = sum(parcel['units'] for parcel in adjusted_cost_basis[symbol])
                self._log(f"   📊 {symbol}: {total_historical_sold} historical shares consumed, {remaining_units} remaining")
        
        return adjusted_cost_basis

    def _validate_sufficient_shares(self, cost_basis_dict: Dict, fy24_25_sales: pd.DataFrame):
        """Validate that we have sufficient shares for each sale."""
        
        self._log("🔍 Validating sufficient shares for sales...")
        
        if fy24_25_sales.empty:
            return
        
        # Use lowercase column names (renaming happens later)
        for symbol, symbol_sales in fy24_25_sales.groupby('symbol'):
            total_sold = symbol_sales['quantity'].sum()
            
            if symbol in cost_basis_dict:
                total_available = sum(parcel['units'] for parcel in cost_basis_dict[symbol])
                
                if total_sold > total_available:
                    shortage = total_sold - total_available
                    warning = f"⚠️ {symbol}: Insufficient shares! Selling {total_sold}, only have {total_available} (short by {shortage})"
                    self.warnings.append(warning)
                    self._log(f"   {warning}")
                else:
                    self._log(f"   ✅ {symbol}: {total_sold} sold, {total_available} available")
            else:
                warning = f"⚠️ {symbol}: No cost basis found for {total_sold} units being sold"
                self.warnings.append(warning)
                self._log(f"   {warning}")
    
    def _log_processing_summary(self, cost_basis_dict: Dict, fy24_25_sales: pd.DataFrame):
        """Log final processing summary."""
        
        total_symbols_cost_basis = len(cost_basis_dict)
        total_parcels = sum(len(parcels) for parcels in cost_basis_dict.values())
        total_sales = len(fy24_25_sales)
        unique_symbols_sold = fy24_25_sales['symbol'].nunique() if not fy24_25_sales.empty else 0
        
        self._log(f"\n📋 PROCESSING SUMMARY:")
        self._log(f"   📦 Cost basis symbols: {total_symbols_cost_basis}")
        self._log(f"   📦 Total parcels: {total_parcels}")
        self._log(f"   📈 FY24-25 sales: {total_sales} transactions")
        self._log(f"   🏷️ Unique symbols sold: {unique_symbols_sold}")
        self._log(f"   ⚠️ Warnings generated: {len(self.warnings)}")
    
    def _log(self, message: str):
        """Add message to processing log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.processing_log.append(log_entry)
        print(log_entry)  # Also print for immediate feedback


# Convenience function for easy integration
def process_statement_csv(csv_files) -> Tuple[Dict, pd.DataFrame, List[str], List[str]]:
    """
    Convenience function to process broker statement CSV(s).
    
    Args:
        csv_files: Single CSV file or list of CSV files (paths or file-like objects)
        
    Returns:
        (cost_basis_dict, fy24_25_sales_df, warnings, processing_log)
    """
    processor = StatementProcessor()
    return processor.process_statement_csv(csv_files)