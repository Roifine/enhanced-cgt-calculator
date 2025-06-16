#!/usr/bin/env python3
"""
Enhanced Australian CGT Calculator with Tax Optimization
Uses tax-optimal parcel selection for maximum after-tax returns
"""

import pandas as pd
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
import traceback

# Import the tax optimizer
from tax_optimizer import optimize_sale_for_cgt


def safe_commission(value, default_missing=30.0, min_reasonable=0.0):
    """Handle commission with reasonable defaults"""
    if value is None or pd.isna(value) or str(value).strip() == "":
        return default_missing  # Missing data → $30
    
    try:
        num_value = float(value)
        return max(min_reasonable, num_value)  # Keep explicit zeros, ensure non-negative
    except (ValueError, TypeError):
        return default_missing


class EnhancedCGTCalculator:
    """
    Enhanced Australian CGT calculator with tax optimization.
    Maintains compatibility with existing RBA/AUD system.
    """
    
    def __init__(self, rba_converter=None):
        self.rba_converter = rba_converter
        self.processing_records = []
        self.optimization_savings = []
    
    def calculate_optimized_cgt(
        self, 
        sales_df: pd.DataFrame, 
        cost_basis_dict: Dict,
        strategy: str = "tax_optimal"
    ) -> Tuple[pd.DataFrame, Dict, List[str], List[Dict]]:
        """
        Calculate Australian CGT with tax optimization.
        
        Args:
            sales_df: DataFrame with sales transactions
            cost_basis_dict: Cost basis dictionary (will be updated)
            strategy: "tax_optimal" or "fifo" 
            
        Returns:
            (cgt_df, updated_cost_basis, warnings, processing_records)
        """
        
        self._log("🇦🇺 ENHANCED AUSTRALIAN CGT CALCULATION WITH TAX OPTIMIZATION")
        self._log(f"📊 Processing {len(sales_df)} sales transactions")
        self._log(f"🎯 Strategy: {strategy.upper()}")
        self._log("=" * 60)
        
        # Create working copy of cost basis dictionary
        working_cost_basis = {}
        for symbol, parcels in cost_basis_dict.items():
            working_cost_basis[symbol] = [parcel.copy() for parcel in parcels]
        
        cgt_records = []
        warnings_list = []
        
        # Process each sale transaction
        for idx, sale in sales_df.iterrows():
            try:
                self._log(f"\n🔄 Processing Sale {idx + 1}/{len(sales_df)}: {sale['Symbol']}")
                
                # Extract sale details
                symbol = sale['Symbol']
                sale_date = pd.to_datetime(sale['Trade Date'])
                units_sold = float(sale['Quantity'])
                sale_price_usd = float(sale['Price (USD)'])
                sale_commission_usd = safe_commission(sale['Commission (USD)'])
                
                self._log(f"   📈 {symbol}: {units_sold} units @ ${sale_price_usd:.2f} on {sale_date.strftime('%Y-%m-%d')}")
                self._log(f"   💰 Sale commission: ${sale_commission_usd:.2f}")
                
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
                
                # Calculate CGT for each selected parcel
                for parcel in selected_parcels:
                    cgt_record = self._calculate_parcel_cgt(
                        symbol, sale_date, parcel, sale_price_usd, sale_commission_usd, units_sold
                    )
                    cgt_records.append(cgt_record)
                    
                    self._log(f"   ✅ Parcel: {parcel['units_consumed']:.1f} units from {parcel['date']} "
                             f"({'LT' if parcel['is_long_term'] else 'ST'}) - "
                             f"Gain: ${cgt_record['capital_gain_aud']:.2f}")
                
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
            self._log(f"   💰 Total capital gain: ${cgt_df['capital_gain_aud'].sum():.2f}")
            self._log(f"   🏆 Long-term transactions: {sum(1 for r in cgt_records if r['is_long_term'])}")
            
            if len(cgt_records) > 0:
                long_term_gains = cgt_df[cgt_df['is_long_term'] & (cgt_df['capital_gain_aud'] > 0)]['capital_gain_aud'].sum()
                discount_savings = long_term_gains * 0.5
                self._log(f"   🎯 CGT discount savings: ${discount_savings:.2f}")
        else:
            cgt_df = pd.DataFrame()
            self._log("⚠️ No CGT records generated")
        
        return cgt_df, working_cost_basis, warnings_list, self.processing_records
    
    def _fifo_selection(self, parcels: List[Dict], units_needed: float, sale_date: datetime) -> Tuple[List[Dict], List[Dict], float]:
        """
        Simple FIFO parcel selection for comparison.
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
                # Add to selected parcels
                purchase_date = self._parse_date(parcel['date'])
                days_held = (sale_date - purchase_date).days
                commission = safe_commission(parcel['commission'])
                
                selected_parcel = {
                    'original_index': i,
                    'units_consumed': to_take,
                    'units_remaining_in_parcel': available - to_take,
                    'price': parcel['price'],
                    'commission': commission * (to_take / available),
                    'date': parcel['date'],
                    'purchase_date': purchase_date,
                    'days_held': days_held,
                    'is_long_term': days_held >= 365,
                    'cost_per_unit': parcel['price'] + (commission / available),
                    'total_cost': to_take * (parcel['price'] + (commission / available)),
                    'phase': 'FIFO'
                }
                selected_parcels.append(selected_parcel)
                remaining_units -= to_take
                
                # Add remaining portion to updated parcels
                if available - to_take > 0:
                    remaining_parcel = parcel.copy()
                    remaining_parcel['units'] = available - to_take
                    remaining_parcel['commission'] = commission * ((available - to_take) / available)
                    updated_parcels.append(remaining_parcel)
            else:
                updated_parcels.append(parcel.copy())
        
        return selected_parcels, updated_parcels, remaining_units
    
    def _calculate_parcel_cgt(self, symbol: str, sale_date: datetime, parcel: Dict, 
                             sale_price_usd: float, sale_commission_usd: float, 
                             total_units_sold: float) -> Dict:
        """
        Calculate CGT for a single parcel portion.
        """
        units_sold = parcel['units_consumed']
        
        # Calculate proportional sale commission
        commission_proportion = units_sold / total_units_sold
        allocated_sale_commission = sale_commission_usd * commission_proportion
        
        # Cost basis (in USD for now - AUD conversion would happen later)
        cost_basis_usd = parcel['total_cost']
        
        # Sale proceeds (net of commission)
        gross_proceeds_usd = units_sold * sale_price_usd
        net_proceeds_usd = gross_proceeds_usd - allocated_sale_commission
        
        # Capital gain/loss (in USD for now)
        capital_gain_usd = net_proceeds_usd - cost_basis_usd
        
        # For now, using 1:1 USD to AUD (would integrate with RBA rates later)
        # TODO: Integrate with existing RBA exchange rate system
        exchange_rate = 1.0  # Placeholder
        
        capital_gain_aud = capital_gain_usd * exchange_rate
        cost_basis_aud = cost_basis_usd * exchange_rate
        net_proceeds_aud = net_proceeds_usd * exchange_rate
        
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
            'sale_price_usd': sale_price_usd,
            'gross_proceeds_aud': gross_proceeds_usd * exchange_rate,
            'sale_commission_aud': allocated_sale_commission * exchange_rate,
            'net_proceeds_aud': net_proceeds_aud,
            'capital_gain_aud': capital_gain_aud,
            'cgt_discount_rate': cgt_discount_rate,
            'taxable_gain_aud': taxable_gain_aud,
            'exchange_rate': exchange_rate,
            'parcel_source': parcel['date'],
            'optimization_phase': parcel.get('phase', 'UNKNOWN')
        }
    
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


# Convenience functions for compatibility
def calculate_enhanced_cgt(sales_df, cost_basis_dict, rba_converter=None, strategy="tax_optimal"):
    """
    Convenience function for enhanced CGT calculation.
    Compatible with existing code structure.
    """
    calculator = EnhancedCGTCalculator(rba_converter)
    return calculator.calculate_optimized_cgt(sales_df, cost_basis_dict, strategy)