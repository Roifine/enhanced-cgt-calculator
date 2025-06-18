#!/usr/bin/env python3
"""
Australian CGT Tax Optimizer - Updated for AUD-Focused Structure
Optimizes parcel selection for maximum after-tax returns using Australian CGT rules
Now works with RBA-converted AUD cost basis data
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import copy


class ParcelOptimizer:
    """
    Australian CGT tax optimization engine - Updated for AUD-focused structure.
    Selects optimal parcels for sale to minimize tax burden.
    
    Now works with RBA-converted parcels that have:
    - price_aud, commission_aud (instead of price, commission)
    - cost_per_unit_aud, total_cost_aud (pre-calculated)
    - Backward compatibility for legacy parcel structure
    """
    
    def __init__(self):
        self.processing_log = []
    
    def optimize_parcel_selection(
        self, 
        cost_basis_parcels: List[Dict], 
        units_to_sell: float, 
        sale_date: datetime
    ) -> Tuple[List[Dict], List[Dict], float]:
        """
        Select optimal parcels for Australian CGT tax efficiency.
        
        Strategy:
        1. Long-term holdings first (>12 months = 50% CGT discount)
        2. Within category: highest cost basis first (minimize gains)
        
        Args:
            cost_basis_parcels: List of parcel dictionaries (AUD-focused or legacy format)
            units_to_sell: Number of units being sold
            sale_date: Date of the sale
            
        Returns:
            (selected_parcels, updated_cost_basis, remaining_units_needed)
        """
        
        self._log(f"🎯 Starting tax optimization for {units_to_sell} units")
        
        # Validate inputs
        if not cost_basis_parcels:
            self._log("❌ No parcels available")
            return [], [], units_to_sell
        
        if units_to_sell <= 0:
            self._log("❌ Invalid sale quantity")
            return [], [], units_to_sell
        
        # Create working copy to avoid mutating input
        available_parcels = copy.deepcopy(cost_basis_parcels)
        
        # Calculate days held for each parcel and add optimization metadata
        enriched_parcels = []
        for i, parcel in enumerate(available_parcels):
            try:
                # Parse purchase date
                purchase_date = self._parse_date(parcel['date'])
                days_held = (sale_date - purchase_date).days
                
                # Get parcel data - handle both AUD-focused and legacy formats
                units = parcel['units']
                price_aud, commission_aud, cost_per_unit_aud, total_cost_aud = self._extract_parcel_costs(parcel)
                
                enriched_parcel = {
                    'original_index': i,
                    'units': units,
                    'price_aud': price_aud,
                    'commission_aud': commission_aud,
                    'price_usd': parcel.get('price_usd', price_aud),              # ADD THIS
                    'commission_usd': parcel.get('commission_usd', commission_aud),  # ADD THIS  
                    'exchange_rate_buy': parcel['exchange_rate_buy'],    # ADD THIS
                    'date': parcel['date'],
                    'purchase_date': purchase_date,
                    'days_held': days_held,
                    'is_long_term': days_held >= 365,
                    'cost_per_unit_aud': cost_per_unit_aud,
                    'total_cost_aud': total_cost_aud
                }
                
                enriched_parcels.append(enriched_parcel)
                
                self._log(f"   📦 Parcel {i}: {units} units @ ${cost_per_unit_aud:.2f}/unit AUD, "
                         f"{days_held} days ({'LT' if days_held >= 365 else 'ST'})")
                
            except Exception as e:
                self._log(f"⚠️ Error processing parcel {i}: {e}")
                continue
        
        if not enriched_parcels:
            self._log("❌ No valid parcels after enrichment")
            return [], [], units_to_sell
        
        # Separate long-term and short-term parcels
        long_term_parcels = [p for p in enriched_parcels if p['is_long_term']]
        short_term_parcels = [p for p in enriched_parcels if not p['is_long_term']]
        
        # Sort by cost per unit AUD (highest first to minimize gains)
        long_term_parcels.sort(key=lambda x: x['cost_per_unit_aud'], reverse=True)
        short_term_parcels.sort(key=lambda x: x['cost_per_unit_aud'], reverse=True)
        
        self._log(f"📊 Available: {len(long_term_parcels)} long-term, {len(short_term_parcels)} short-term")
        
        # Select parcels using tax-optimal strategy
        selected_parcels = []
        remaining_units = units_to_sell
        
        # Phase 1: Use long-term parcels first (50% CGT discount)
        self._log("🔄 Phase 1: Selecting long-term parcels...")
        remaining_units = self._consume_parcels(
            long_term_parcels, remaining_units, selected_parcels, "LONG-TERM"
        )
        
        # Phase 2: Use short-term parcels if needed
        if remaining_units > 0:
            self._log("🔄 Phase 2: Selecting short-term parcels...")
            remaining_units = self._consume_parcels(
                short_term_parcels, remaining_units, selected_parcels, "SHORT-TERM"
            )
        
        # Create updated cost basis (remove consumed units)
        updated_cost_basis = self._create_updated_cost_basis(
            available_parcels, selected_parcels
        )
        
        # Summary
        total_selected = sum(p['units_consumed'] for p in selected_parcels)
        long_term_selected = sum(p['units_consumed'] for p in selected_parcels if p['is_long_term'])
        
        self._log(f"✅ Optimization complete:")
        self._log(f"   📈 Total selected: {total_selected} units")
        self._log(f"   🏆 Long-term units: {long_term_selected} (CGT discount eligible)")
        self._log(f"   📉 Short-term units: {total_selected - long_term_selected}")
        self._log(f"   ⚠️ Remaining needed: {remaining_units}")
        
        return selected_parcels, updated_cost_basis, remaining_units
    
    def _extract_parcel_costs(self, parcel: Dict) -> Tuple[float, float, float, float]:
        """
        Extract cost information from parcel, handling both AUD-focused and legacy formats.
        
        Returns:
            (price_aud, commission_aud, cost_per_unit_aud, total_cost_aud)
        """
        units = parcel['units']
        
        # Try AUD-focused format first (from RBA converter)
        if 'price_aud' in parcel and 'commission_aud' in parcel:
            price_aud = parcel['price_aud']
            commission_aud = parcel['commission_aud']
            
            # Use pre-calculated values if available, otherwise calculate
            cost_per_unit_aud = parcel.get('cost_per_unit_aud', 
                                          price_aud + (commission_aud / units if units > 0 else 0))
            total_cost_aud = parcel.get('total_cost_aud', 
                                       units * cost_per_unit_aud)
            
            self._log(f"   💱 Using AUD-focused format: ${price_aud:.2f} AUD + ${commission_aud:.2f} commission")
            
        # Fallback to legacy format (assume USD, log warning)
        elif 'price' in parcel:
            price_usd = parcel['price']
            commission_usd = parcel.get('commission', 0)
            
            # For legacy format, assume 1:1 conversion and log warning
            price_aud = price_usd
            commission_aud = commission_usd
            cost_per_unit_aud = price_aud + (commission_aud / units if units > 0 else 0)
            total_cost_aud = units * cost_per_unit_aud
            
            self._log(f"   ⚠️ Using legacy format (no currency conversion): ${price_usd:.2f}")
            
        else:
            raise ValueError(f"Parcel missing required price fields: {list(parcel.keys())}")
        
        return price_aud, commission_aud, cost_per_unit_aud, total_cost_aud
    
    def _consume_parcels(
        self, 
        parcels: List[Dict], 
        units_needed: float, 
        selected_parcels: List[Dict], 
        phase_name: str
    ) -> float:
        """Consume units from parcels list, updating selected_parcels."""
        
        if units_needed <= 0:
            return units_needed
        
        for parcel in parcels:
            if units_needed <= 0:
                break
            
            available_units = parcel['units']
            units_to_take = min(units_needed, available_units)
            
            if units_to_take > 0:
                # Calculate proportional commission
                commission_proportion = units_to_take / available_units
                proportional_commission_aud = parcel['commission_aud'] * commission_proportion
                
                selected_parcel = {
                    'original_index': parcel['original_index'],
                    'units_consumed': units_to_take,
                    'units_remaining_in_parcel': available_units - units_to_take,
                    'price': parcel['price_aud'],  # For backward compatibility in CGT calculator
                    'commission': proportional_commission_aud,  # For backward compatibility
                    'price_aud': parcel['price_aud'],  # New AUD-focused fields
                    'commission_aud': proportional_commission_aud,
                    'price_usd': parcel['price_usd'],                           # ✅ ADD
                    'commission_usd': parcel['commission_usd'] * commission_proportion,  # ✅ ADD (proportional!)
                    'exchange_rate_buy': parcel['exchange_rate_buy'], 
                    'date': parcel['date'], 
                    'purchase_date': parcel['purchase_date'],
                    'days_held': parcel['days_held'],
                    'is_long_term': parcel['is_long_term'],
                    'cost_per_unit': parcel['cost_per_unit_aud'],  # For backward compatibility
                    'cost_per_unit_aud': parcel['cost_per_unit_aud'],
                    'total_cost': units_to_take * parcel['cost_per_unit_aud'],  # For backward compatibility
                    'total_cost_aud': units_to_take * parcel['cost_per_unit_aud'],
                    'phase': phase_name
                }
                
                selected_parcels.append(selected_parcel)
                units_needed -= units_to_take
                
                self._log(f"   ✂️ {phase_name}: Consumed {units_to_take} units from "
                         f"{parcel['date']} @ ${parcel['cost_per_unit_aud']:.2f}/unit AUD")
        
        return units_needed
    
    def _create_updated_cost_basis(
        self, 
        original_parcels: List[Dict], 
        selected_parcels: List[Dict]
    ) -> List[Dict]:
        """Create updated cost basis with consumed units removed/reduced."""
        
        # Create consumption map
        consumption_map = {}
        for selected in selected_parcels:
            idx = selected['original_index']
            if idx not in consumption_map:
                consumption_map[idx] = 0
            consumption_map[idx] += selected['units_consumed']
        
        # Build updated cost basis
        updated_parcels = []
        
        for i, parcel in enumerate(original_parcels):
            units_consumed = consumption_map.get(i, 0)
            remaining_units = parcel['units'] - units_consumed
            
            if remaining_units > 0:
                # Keep parcel with reduced units - preserve original structure
                updated_parcel = {
                    'units': remaining_units,
                    'date': parcel['date']
                }
                
                # Handle both AUD-focused and legacy formats
                if 'price_aud' in parcel:
                    # AUD-focused format
                    proportion = remaining_units / parcel['units']
                    updated_parcel.update({
                        'price_aud': parcel['price_aud'],
                        'commission_aud': parcel['commission_aud'] * proportion,
                        'price_usd': parcel.get('price_usd', parcel['price_aud']),           # ✅ PRESERVE
                        'commission_usd': parcel.get('commission_usd', parcel['commission_aud']) * proportion,  # ✅ PRESERVE (proportional)
                        'exchange_rate_buy': parcel.get('exchange_rate_buy', 1.0),          # ✅ PRESERVE
                        'cost_per_unit_aud': parcel.get('cost_per_unit_aud', 
                                                       parcel['price_aud'] + (parcel['commission_aud'] / parcel['units'])),
                        'total_cost_aud': remaining_units * parcel.get('cost_per_unit_aud',
                                                                      parcel['price_aud'] + (parcel['commission_aud'] / parcel['units']))
                    })
                else:
                    # Legacy format
                    updated_parcel.update({
                        'price': parcel['price'],
                        'commission': parcel['commission'] * (remaining_units / parcel['units'])
                    })
                
                updated_parcels.append(updated_parcel)
                
                self._log(f"   📦 Updated parcel {i}: {remaining_units} units remaining "
                         f"(was {parcel['units']}, consumed {units_consumed})")
            else:
                self._log(f"   🗑️ Parcel {i} fully consumed (was {parcel['units']} units)")
        
        return updated_parcels
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in various formats with robust handling."""
        if not date_str:
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
        """Add message to processing log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.processing_log.append(log_entry)
        print(log_entry)  # Also print for immediate feedback
    
    def get_processing_log(self) -> List[str]:
        """Get the complete processing log."""
        return self.processing_log.copy()
    
    def clear_log(self):
        """Clear the processing log."""
        self.processing_log.clear()


def optimize_sale_for_cgt(
    cost_basis_parcels: List[Dict], 
    units_to_sell: float, 
    sale_date: datetime
) -> Tuple[List[Dict], List[Dict], float, List[str]]:
    """
    Convenience function for Australian CGT optimization with AUD-focused structure.
    
    Args:
        cost_basis_parcels: List of parcels (AUD-focused or legacy format)
        units_to_sell: Number of units to sell
        sale_date: Date of sale
        
    Returns:
        (selected_parcels, updated_cost_basis, units_still_needed, processing_log)
    """
    
    optimizer = ParcelOptimizer()
    selected, updated, remaining = optimizer.optimize_parcel_selection(
        cost_basis_parcels, units_to_sell, sale_date
    )
    
    return selected, updated, remaining, optimizer.get_processing_log()