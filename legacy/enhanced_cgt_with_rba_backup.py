#!/usr/bin/env python3
"""
Enhanced Australian CGT Calculator with Professional RBA Integration
Replaces placeholder USD→AUD conversion with real RBA historical rates
"""

import pandas as pd
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
import traceback

# Import the tax optimizer and RBA converter
from tax_optimizer_aud_updated import optimize_sale_for_cgt
from rba_converter import RBAExchangeRateConverter


def safe_commission(value, default_missing=30.0, min_reasonable=0.0):
    """Handle commission with reasonable defaults"""
    if value is None or pd.isna(value) or str(value).strip() == "":
        return default_missing  # Missing data → $30
    
    try:
        num_value = float(value)
        return max(min_reasonable, num_value)  # Keep explicit zeros, ensure non-negative
    except (ValueError, TypeError):
        return default_missing


class EnhancedCGTCalculatorWithRBA:
    """
    Enhanced Australian CGT calculator with professional RBA integration.
    Provides accurate USD→AUD conversion for both cost basis and sale proceeds.
    """
    
    def __init__(self, fx_file_paths: List[str] = None):
        """
        Initialize with RBA exchange rate converter.
        
        Args:
            fx_file_paths: Optional custom paths to RBA FX CSV files
        """
        self.processing_records = []
        self.optimization_savings = []
        self.currency_conversions = []
        
        # Initialize RBA converter
        try:
            self.rba_converter = RBAExchangeRateConverter(fx_file_paths, logger=self)
            converter_summary = self.rba_converter.get_conversion_summary()
            self._log(f"🏦 RBA Integration: {converter_summary['status']}")
            self._log(f"   📅 Coverage: {converter_summary['date_range']}")
            
            if converter_summary['load_warnings']:
                for warning in converter_summary['load_warnings']:
                    self._log(f"   {warning}")
                    
        except Exception as e:
            error_msg = f"❌ RBA Converter initialization failed: {str(e)}"
            self._log(error_msg)
            raise ValueError(error_msg)
    
    def calculate_optimized_cgt(
        self, 
        sales_df: pd.DataFrame, 
        cost_basis_dict: Dict,
        strategy: str = "tax_optimal"
    ) -> Tuple[pd.DataFrame, Dict, List[str], List[Dict]]:
        """
        Calculate Australian CGT with tax optimization and accurate RBA currency conversion.
        
        Args:
            sales_df: DataFrame with sales transactions
            cost_basis_dict: Cost basis dictionary (will be updated)
            strategy: "tax_optimal" or "fifo" 
            
        Returns:
            (cgt_df, updated_cost_basis, warnings, processing_records)
        """
        
        self._log("🇦🇺 ENHANCED AUSTRALIAN CGT CALCULATION WITH RBA INTEGRATION")
        self._log(f"📊 Processing {len(sales_df)} sales transactions")
        self._log(f"🎯 Strategy: {strategy.upper()}")
        self._log(f"💱 Currency: Professional RBA USD→AUD conversion")
        self._log("=" * 70)
        
        # Create working copy of cost basis dictionary with AUD conversion
        self._log("\n🔄 Step 1: Converting cost basis parcels to AUD...")
        working_cost_basis = self._convert_cost_basis_to_aud(cost_basis_dict)
        
        cgt_records = []
        warnings_list = []
        
        # Process each sale transaction
        self._log("\n🔄 Step 2: Processing sales with tax optimization...")
        for idx, sale in sales_df.iterrows():
            try:
                self._log(f"\n📈 Processing Sale {idx + 1}/{len(sales_df)}: {sale['Symbol']}")
                
                # Extract sale details
                symbol = sale['Symbol']
                sale_date = pd.to_datetime(sale['Trade Date'])
                units_sold = float(sale['Quantity'])
                sale_price_usd = float(sale['Price (USD)'])
                sale_commission_usd = safe_commission(sale['Commission (USD)'])
                
                self._log(f"   📋 {symbol}: {units_sold} units @ ${sale_price_usd:.2f} USD on {sale_date.strftime('%Y-%m-%d')}")
                self._log(f"   💰 Sale commission: ${sale_commission_usd:.2f} USD")
                
                # Convert sale amounts to AUD using sale date
                sale_price_aud, price_conversion = self.rba_converter.convert_usd_to_aud(
                    sale_price_usd, sale_date, f"{symbol} sale price"
                )
                sale_commission_aud, commission_conversion = self.rba_converter.convert_usd_to_aud(
                    sale_commission_usd, sale_date, f"{symbol} sale commission"
                )
                
                self.currency_conversions.extend([price_conversion, commission_conversion])
                
                # Check if we have cost basis for this symbol
                if symbol not in working_cost_basis:
                    warning = f"⚠️ No cost basis found for {symbol}"
                    warnings_list.append(warning)
                    self._log(f"   {warning}")
                    continue
                
                available_parcels = working_cost_basis[symbol]
                if not available_parcels:
                    warning = f"⚠️ No remaining parcels for {symbol}"
                    warnings_list.append(warning)
                    self._log(f"   {warning}")
                    continue
                
                # Use tax optimizer to select optimal parcels
                if strategy == "tax_optimal":
                    selected_parcels, updated_parcels, units_remaining, optimizer_log = optimize_sale_for_cgt(
                        available_parcels, units_sold, sale_date
                    )
                    # Merge optimizer logs with main processing log
                    for log_entry in optimizer_log:
                        self.processing_records.append(log_entry)
                else:  # FIFO fallback
                    selected_parcels, updated_parcels, units_remaining = self._fifo_selection(
                        available_parcels, units_sold, sale_date
                    )
                
                # Check if we could fulfill the sale
                if units_remaining > 0.001:  # Small tolerance for floating point
                    warning = f"⚠️ Insufficient units for {symbol}: need {units_sold}, short by {units_remaining:.3f}"
                    warnings_list.append(warning)
                    self._log(f"   {warning}")
                
                # Update working cost basis
                working_cost_basis[symbol] = updated_parcels
                
                # Calculate CGT for each selected parcel (now with real RBA rates)
                for parcel in selected_parcels:
                    cgt_record = self._calculate_parcel_cgt_with_rba(
                        symbol, sale_date, parcel, sale_price_aud, sale_commission_aud, 
                        units_sold, price_conversion['aud_usd_rate']
                    )
                    cgt_records.append(cgt_record)
                    
                    self._log(f"   ✅ Parcel: {parcel['units_consumed']:.1f} units from {parcel['date']} "
                             f"({'LT' if parcel['is_long_term'] else 'ST'}) - "
                             f"Gain: ${cgt_record['capital_gain_aud']:.2f} AUD")
                
                self.optimization_savings.append({
                    'symbol': symbol,
                    'strategy': strategy,
                    'long_term_units': sum(p['units_consumed'] for p in selected_parcels if p['is_long_term']),
                    'total_units': sum(p['units_consumed'] for p in selected_parcels)
                })
                
            except Exception as e:
                error_msg = f"❌ Error processing {sale.get('Symbol', 'Unknown')}: {str(e)}"
                warnings_list.append(error_msg)
                self._log(error_msg)
                # Log the full traceback for debugging
                self._log(f"   Debug traceback: {traceback.format_exc()}")
                continue
        
        # Create results DataFrame
        if cgt_records:
            cgt_df = pd.DataFrame(cgt_records)
            self._log(f"\n✅ CGT Calculation Complete:")
            self._log(f"   📊 {len(cgt_records)} parcel transactions processed")
            self._log(f"   💰 Total capital gain: ${cgt_df['capital_gain_aud'].sum():.2f} AUD")
            self._log(f"   🏆 Long-term transactions: {sum(1 for r in cgt_records if r['is_long_term'])}")
            
            if len(cgt_records) > 0:
                long_term_gains = cgt_df[cgt_df['is_long_term'] & (cgt_df['capital_gain_aud'] > 0)]['capital_gain_aud'].sum()
                discount_savings = long_term_gains * 0.5
                self._log(f"   🎯 CGT discount savings: ${discount_savings:.2f} AUD")
                
            # Currency conversion summary
            total_conversions = len(self.currency_conversions)
            fallback_conversions = sum(1 for c in self.currency_conversions if c.get('used_fallback', False))
            self._log(f"   💱 Currency conversions: {total_conversions} total ({fallback_conversions} used fallback)")
        else:
            cgt_df = pd.DataFrame()
            self._log("⚠️ No CGT records generated")
        
        return cgt_df, working_cost_basis, warnings_list, self.processing_records
    
    def _convert_cost_basis_to_aud(self, cost_basis_dict: Dict) -> Dict:
        """
        Convert all cost basis parcels from USD to AUD using purchase dates.
        
        Args:
            cost_basis_dict: Original cost basis in USD
            
        Returns:
            Dictionary with AUD-converted cost basis
        """
        aud_cost_basis = {}
        
        for symbol, parcels in cost_basis_dict.items():
            self._log(f"   💱 Converting {symbol}: {len(parcels)} parcels")
            aud_parcels = []
            
            for parcel in parcels:
                try:
                    aud_parcel, conversion_info = self.rba_converter.convert_cost_basis_parcel(parcel)
                    aud_parcels.append(aud_parcel)
                    
                    # Store conversion info for audit trail
                    self.currency_conversions.extend([
                        conversion_info['price_conversion'],
                        conversion_info['commission_conversion']
                    ])
                    
                except Exception as e:
                    error_msg = f"⚠️ Error converting parcel for {symbol}: {str(e)}"
                    self._log(error_msg)
                    # Keep original parcel with warning
                    aud_parcels.append(parcel)
            
            aud_cost_basis[symbol] = aud_parcels
        
        return aud_cost_basis
    
    def _calculate_parcel_cgt_with_rba(
        self, 
        symbol: str, 
        sale_date: datetime, 
        parcel: Dict, 
        sale_price_aud: float, 
        sale_commission_aud: float, 
        total_units_sold: float,
        exchange_rate: float
    ) -> Dict:
        """
        Calculate CGT for a single parcel portion with real RBA conversion.
        
        *** THIS REPLACES THE PLACEHOLDER INTEGRATION POINT ***
        """
        units_sold = parcel['units_consumed']
        
        # Calculate proportional sale commission
        commission_proportion = units_sold / total_units_sold
        allocated_sale_commission_aud = sale_commission_aud * commission_proportion
        
        # Cost basis (already in AUD from conversion)
        cost_basis_aud = parcel['total_cost']
        
        # Sale proceeds (already in AUD)
        gross_proceeds_aud = units_sold * sale_price_aud
        net_proceeds_aud = gross_proceeds_aud - allocated_sale_commission_aud
        
        # Capital gain/loss (all in AUD)
        capital_gain_aud = net_proceeds_aud - cost_basis_aud
        
        # Apply CGT discount for long-term holdings
        is_long_term = parcel['is_long_term']
        cgt_discount_rate = 0.5 if is_long_term else 0.0
        taxable_gain_aud = capital_gain_aud * (1 - cgt_discount_rate) if capital_gain_aud > 0 else capital_gain_aud
        
        return {
            'symbol': symbol,
            'sale_date': sale_date,
            'purchase_date': parcel['purchase_date'],
            'units_sold': units_sold,
            'days_held': parcel['days_held'],
            'is_long_term': is_long_term,
            'cost_basis_aud': cost_basis_aud,
            'sale_price_aud': sale_price_aud,
            'gross_proceeds_aud': gross_proceeds_aud,
            'sale_commission_aud': allocated_sale_commission_aud,
            'net_proceeds_aud': net_proceeds_aud,
            'capital_gain_aud': capital_gain_aud,
            'cgt_discount_rate': cgt_discount_rate,
            'taxable_gain_aud': taxable_gain_aud,
            'exchange_rate': exchange_rate,
            'parcel_source': parcel['date'],
            'optimization_phase': parcel.get('phase', 'UNKNOWN'),
            'rba_conversion': True  # Flag indicating real RBA rates used
        }
    
    def _fifo_selection(self, parcels: List[Dict], units_needed: float, sale_date: datetime) -> Tuple[List[Dict], List[Dict], float]:
        """
        Simple FIFO parcel selection for comparison - Updated for AUD-focused structure.
        """
        self._log("🔄 Using FIFO strategy")
        
        selected_parcels = []
        remaining_units = units_needed
        updated_parcels = []
        
        for i, parcel in enumerate(parcels):
            if remaining_units <= 0:
                # Add remaining parcels unchanged
                updated_parcels.append(parcel.copy())
                continue
                
            available = parcel['units']
            to_take = min(remaining_units, available)
            
            if to_take > 0:
                # Get purchase date - handle both formats
                purchase_date = parcel.get('purchase_date')
                if purchase_date is None:
                    try:
                        purchase_date = self._parse_date(parcel['date'])
                    except:
                        purchase_date = datetime(2020, 1, 1)
                
                days_held = (sale_date - purchase_date).days
                
                # Extract cost information - handle both AUD-focused and legacy formats
                if 'price_aud' in parcel:
                    # AUD-focused format
                    price_aud = parcel['price_aud']
                    commission_aud = parcel.get('commission_aud', 0)
                    cost_per_unit_aud = parcel.get('cost_per_unit_aud', 
                                                  price_aud + (commission_aud / available if available > 0 else 0))
                    proportional_commission = commission_aud * (to_take / available)
                    total_cost_aud = to_take * cost_per_unit_aud
                else:
                    # Legacy format fallback
                    price = parcel.get('price', 0)
                    commission = parcel.get('commission', 0)
                    cost_per_unit_aud = price + (commission / available if available > 0 else 0)
                    proportional_commission = commission * (to_take / available)
                    total_cost_aud = to_take * cost_per_unit_aud
                    price_aud = price
                
                selected_parcel = {
                    'original_index': i,
                    'units_consumed': to_take,
                    'units_remaining_in_parcel': available - to_take,
                    'price': price_aud,  # For backward compatibility
                    'commission': proportional_commission,  # For backward compatibility
                    'price_aud': price_aud,
                    'commission_aud': proportional_commission,
                    'date': parcel['date'],
                    'purchase_date': purchase_date,
                    'days_held': days_held,
                    'is_long_term': days_held >= 365,
                    'cost_per_unit': cost_per_unit_aud,  # For backward compatibility
                    'cost_per_unit_aud': cost_per_unit_aud,
                    'total_cost': total_cost_aud,  # For backward compatibility
                    'total_cost_aud': total_cost_aud,
                    'phase': 'FIFO'
                }
                selected_parcels.append(selected_parcel)
                remaining_units -= to_take
                
                # Add remaining portion to updated parcels
                if available - to_take > 0:
                    remaining_parcel = parcel.copy()
                    remaining_parcel['units'] = available - to_take
                    
                    # Update proportional commission for remaining portion
                    if 'commission_aud' in remaining_parcel:
                        remaining_parcel['commission_aud'] = commission_aud * ((available - to_take) / available)
                    elif 'commission' in remaining_parcel:
                        remaining_parcel['commission'] = remaining_parcel['commission'] * ((available - to_take) / available)
                    
                    updated_parcels.append(remaining_parcel)
            else:
                updated_parcels.append(parcel.copy())
        
        return selected_parcels, updated_parcels, remaining_units
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in various formats with robust handling."""
        if not date_str or pd.isna(date_str):
            self._log(f"⚠️ Empty date string, using default")
            return datetime(2020, 1, 1)
        
        # Clean the date string
        date_str = str(date_str).strip()
        
        # List of date formats to try, in order of likelihood
        date_formats = [
            "%d/%m/%y",     # 19/12/24, 01/05/25
            "%d/%m/%Y",     # 19/12/2024, 01/05/2025
            "%d.%m.%y",     # 12.2.21, 23.6.21
            "%d.%m.%Y",     # 12.2.2021
            "%Y-%m-%d",     # 2024-12-19
            "%d-%m-%y",     # 19-12-24
            "%d-%m-%Y",     # 19-12-2024
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                # Additional validation: ensure the date makes sense
                if parsed_date.year < 2000:
                    # Handle 2-digit years that might be interpreted incorrectly
                    if parsed_date.year < 50:  # 00-49 = 2000-2049
                        parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
                    else:  # 50-99 = 1950-1999
                        parsed_date = parsed_date.replace(year=parsed_date.year + 1900)
                
                # Sanity check: date should be between 2000 and 2030
                if 2000 <= parsed_date.year <= 2030:
                    return parsed_date
                else:
                    continue  # Try next format
                    
            except ValueError:
                continue  # Try next format
        
        # If all formats fail, log the issue and use a safe default
        self._log(f"⚠️ Could not parse date '{date_str}' with any known format, using default")
        return datetime(2020, 1, 1)
    
    def _log(self, message: str):
        """Add to processing log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.processing_records.append(log_entry)
        print(log_entry)
    
    def get_currency_audit_trail(self) -> pd.DataFrame:
        """Get detailed audit trail of all currency conversions."""
        if not self.currency_conversions:
            return pd.DataFrame()
        
        return pd.DataFrame(self.currency_conversions)


# Convenience functions for compatibility
def calculate_enhanced_cgt_with_rba(sales_df, cost_basis_dict, fx_file_paths=None, strategy="tax_optimal"):
    """
    Convenience function for enhanced CGT calculation with RBA integration.
    Compatible with existing code structure.
    """
    calculator = EnhancedCGTCalculatorWithRBA(fx_file_paths)
    return calculator.calculate_optimized_cgt(sales_df, cost_basis_dict, strategy)