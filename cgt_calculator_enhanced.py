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
        
        return pd.DataFrame(cgt_records), working_cost_basis, warnings_list, self.processing_records
    
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
