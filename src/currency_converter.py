#!/usr/bin/env python3
"""
Professional RBA Exchange Rate Converter for Australian CGT System
Integrates with Enhanced CGT Calculator for accurate USD→AUD conversions
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import warnings


class RBAExchangeRateConverter:
    """
    Professional RBA exchange rate converter with caching and error handling.
    
    Handles USD→AUD conversion using official RBA daily rates with:
    - Efficient in-memory caching
    - Forward-fill for weekends/holidays
    - Comprehensive error handling
    - Audit trail logging
    """
    
    def __init__(self, fx_file_paths: List[str] = None, logger=None):
        """
        Initialize with RBA FX data files.
        
        Args:
            fx_file_paths: List of RBA CSV file paths
            logger: Optional logger for audit trail
        """
        self.rates_cache = {}  # {date_str: aud_usd_rate}
        self.logger = logger
        self.load_warnings = []
        
        # Default file paths if not provided - updated for new structure
        if fx_file_paths is None:
            # Try to find data directory from different locations
            possible_data_paths = [
                '../data/rates',  # From src/ directory
                'data/rates',     # From project root
                '../../data/rates',  # From tests/ directory
                'test_data/rates',   # Fallback to old location
            ]
            
            fx_file_paths = None
            for data_path in possible_data_paths:
                if os.path.exists(data_path):
                    fx_file_paths = [
                        os.path.join(data_path, 'FX_2018-2022.csv'),
                        os.path.join(data_path, 'FX_2023-2025.csv')
                    ]
                    self._log(f"📂 Found data directory at: {data_path}")
                    break
            
            if fx_file_paths is None:
                # Last resort - try absolute path
                current_file_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_file_dir)
                data_rates_path = os.path.join(project_root, 'data', 'rates')
                
                if os.path.exists(data_rates_path):
                    fx_file_paths = [
                        os.path.join(data_rates_path, 'FX_2018-2022.csv'),
                        os.path.join(data_rates_path, 'FX_2023-2025.csv')
                    ]
                    self._log(f"📂 Found data directory at: {data_rates_path}")
                else:
                    # Final fallback
                    fx_file_paths = [
                        'test_data/rates/FX_2018-2022.csv',
                        'test_data/rates/FX_2023-2025.csv'
                    ]
        
        self._load_rba_rates(fx_file_paths)
        self._log(f"🏦 RBA Converter initialized with {len(self.rates_cache)} daily rates")
    
    def _load_rba_rates(self, file_paths: List[str]):
        """Load and parse RBA FX data files into cache."""
        
        for file_path in file_paths:
            try:
                if not os.path.exists(file_path):
                    warning = f"⚠️ RBA file not found: {file_path}"
                    self.load_warnings.append(warning)
                    self._log(warning)
                    continue
                
                self._log(f"📂 Loading RBA rates from {file_path}")
                
                # Read RBA CSV file
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Parse RBA format (skip header lines until we find data)
                rates_loaded = 0
                for line in lines:
                    line = line.strip()
                    if not line or ',' not in line:
                        continue
                    
                    # Skip header/metadata lines
                    if any(header in line for header in ['Title', 'Description', 'Frequency', 'Source', 'Series']):
                        continue
                    
                    # Parse date,rate lines
                    parts = line.split(',')
                    if len(parts) >= 2:
                        date_str = parts[0].strip()
                        rate_str = parts[1].strip()
                        
                        if date_str and rate_str:
                            try:
                                # Parse RBA date format (DD-MMM-YYYY)
                                date_obj = datetime.strptime(date_str, '%d-%b-%Y')
                                rate = float(rate_str)
                                
                                # Store as YYYY-MM-DD for consistent lookup
                                cache_key = date_obj.strftime('%Y-%m-%d')
                                self.rates_cache[cache_key] = rate
                                rates_loaded += 1
                                
                            except (ValueError, TypeError) as e:
                                # Skip invalid date/rate entries
                                continue
                
                self._log(f"   ✅ Loaded {rates_loaded} rates from {file_path}")
                
            except Exception as e:
                error_msg = f"❌ Error loading {file_path}: {str(e)}"
                self.load_warnings.append(error_msg)
                self._log(error_msg)
        
        # Validate we have some data
        if not self.rates_cache:
            error_msg = "❌ CRITICAL: No RBA exchange rates loaded!"
            self.load_warnings.append(error_msg)
            self._log(error_msg)
            raise ValueError("No RBA exchange rates available")
        
        # Log date range for validation
        dates = sorted(self.rates_cache.keys())
        self._log(f"   📅 Rate coverage: {dates[0]} to {dates[-1]}")
    
    def get_usd_to_aud_rate(self, transaction_date: datetime) -> Tuple[float, bool]:
        """
        Get USD→AUD conversion rate for a specific date.
        
        RBA rates are AUD/USD (A$1 = X USD), so to convert USD to AUD:
        AUD_amount = USD_amount ÷ AUD_USD_rate
        
        Args:
            transaction_date: Date of the transaction
            
        Returns:
            (conversion_rate, used_fallback): Rate to divide USD by, and fallback flag
        """
        date_key = transaction_date.strftime('%Y-%m-%d')
        
        # Direct lookup first
        if date_key in self.rates_cache:
            return self.rates_cache[date_key], False
        
        # Forward-fill fallback (find previous business day)
        self._log(f"⚠️ No rate for {date_key}, using forward-fill...")
        
        current_date = transaction_date
        max_lookback = 10  # Maximum days to look back
        
        for i in range(max_lookback):
            current_date -= timedelta(days=1)
            fallback_key = current_date.strftime('%Y-%m-%d')
            
            if fallback_key in self.rates_cache:
                rate = self.rates_cache[fallback_key]
                self._log(f"   📅 Using rate from {fallback_key}: {rate}")
                return rate, True
        
        # If no rate found within lookback period
        error_msg = f"❌ No RBA rate available for {date_key} or {max_lookback} days prior"
        self._log(error_msg)
        raise ValueError(error_msg)
    
    def convert_usd_to_aud(self, usd_amount: float, transaction_date: datetime, 
                          context: str = "") -> Tuple[float, Dict]:
        """
        Convert USD amount to AUD using historical RBA rates.
        
        Args:
            usd_amount: Amount in USD
            transaction_date: Date for rate lookup
            context: Description for logging (e.g., "AAPL sale", "MSFT cost basis")
            
        Returns:
            (aud_amount, conversion_info): Converted amount and metadata
        """
        try:
            aud_usd_rate, used_fallback = self.get_usd_to_aud_rate(transaction_date)
            
            # Convert: USD ÷ (AUD/USD rate) = AUD
            aud_amount = usd_amount / aud_usd_rate
            
            conversion_info = {
                'usd_amount': usd_amount,
                'aud_amount': aud_amount,
                'aud_usd_rate': aud_usd_rate,
                'transaction_date': transaction_date,
                'used_fallback': used_fallback,
                'context': context
            }
            
            fallback_flag = " (fallback)" if used_fallback else ""
            self._log(f"   💱 {context}: ${usd_amount:.2f} USD → ${aud_amount:.2f} AUD "
                     f"@ {aud_usd_rate:.4f}{fallback_flag}")
            
            return aud_amount, conversion_info
            
        except Exception as e:
            error_msg = f"❌ Currency conversion failed for {context}: {str(e)}"
            self._log(error_msg)
            raise ValueError(error_msg)
    
    def convert_cost_basis_parcel(self, parcel: Dict) -> Tuple[Dict, Dict]:
        """
        Convert a cost basis parcel from USD to AUD.
        
        Args:
            parcel: Cost basis parcel dictionary
            
        Returns:
            (aud_parcel, conversion_info): Converted parcel and metadata
        """
        try:
            # Parse purchase date
            purchase_date = self._parse_parcel_date(parcel['date'])
            
            # Convert price and commission
            usd_price = float(parcel['price'])
            usd_commission = float(parcel.get('commission', 0))
            units = float(parcel['units'])
            
            # Convert price per unit
            aud_price, price_info = self.convert_usd_to_aud(
                usd_price, purchase_date, f"Cost basis price"
            )
            
            # Convert total commission
            aud_commission, commission_info = self.convert_usd_to_aud(
                usd_commission, purchase_date, f"Commission"
            )
            
            # Create AUD parcel
            aud_parcel = {
                'units': units,
                'price_usd': usd_price,
                'price_aud': aud_price,
                'commission_usd': usd_commission,
                'commission_aud': aud_commission,
                'exchange_rate_buy': price_info['aud_usd_rate'], 
                'date': parcel['date'],
                'purchase_date': purchase_date,
                'cost_per_unit_aud': aud_price + (aud_commission / units if units > 0 else 0),
                'total_cost_aud': units * (aud_price + (aud_commission / units if units > 0 else 0))
            }
            # ADD THIS DEBUG LINE RIGHT AFTER:
            print(f"🔍 CURRENCY CONVERTER: Created aud_parcel with exchange_rate_buy = {aud_parcel['exchange_rate_buy']}")
            conversion_info = {
                'price_conversion': price_info,
                'commission_conversion': commission_info
            }
            
            return aud_parcel, conversion_info
            
        except Exception as e:
            error_msg = f"❌ Error converting cost basis parcel: {str(e)}"
            self._log(error_msg)
            raise ValueError(error_msg)
    
    def _parse_parcel_date(self, date_str: str) -> datetime:
        """Parse cost basis date string into datetime object."""
        if not date_str:
            raise ValueError("Empty date string")
        
        date_str = str(date_str).strip()
        
        # Common date formats in cost basis data
        date_formats = [
            "%d/%m/%y",     # 19/12/24
            "%d/%m/%Y",     # 19/12/2024
            "%d.%m.%y",     # 12.2.21
            "%d.%m.%Y",     # 12.2.2021
            "%Y-%m-%d",     # 2024-12-19
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                
                # Handle 2-digit years
                if parsed_date.year < 2000:
                    if parsed_date.year < 50:
                        parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
                    else:
                        parsed_date = parsed_date.replace(year=parsed_date.year + 1900)
                
                # Sanity check
                if 2000 <= parsed_date.year <= 2030:
                    return parsed_date
                    
            except ValueError:
                continue
        
        raise ValueError(f"Could not parse date: {date_str}")
    
    def _log(self, message: str):
        """Log message to logger if available, otherwise print."""
        if self.logger and hasattr(self.logger, '_log'):
            self.logger._log(message)
        else:
            print(message)
    
    def get_conversion_summary(self) -> Dict:
        """Get summary of converter status and capabilities."""
        dates = sorted(self.rates_cache.keys()) if self.rates_cache else []
        
        return {
            'rates_loaded': len(self.rates_cache),
            'date_range': f"{dates[0]} to {dates[-1]}" if dates else "No rates",
            'load_warnings': self.load_warnings,
            'status': 'Ready' if self.rates_cache else 'ERROR: No rates loaded'
        }


# Integration helper for backwards compatibility
def create_rba_converter(fx_file_paths: List[str] = None, logger=None) -> RBAExchangeRateConverter:
    """
    Factory function to create RBA converter instance.
    
    Returns:
        Configured RBAExchangeRateConverter instance
    """
    return RBAExchangeRateConverter(fx_file_paths, logger)