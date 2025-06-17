#!/usr/bin/env python3
"""
CGT System Detective Script
Comprehensive debugging to identify why CGT records aren't being generated
"""

import pandas as pd
import json
import sys
import os
import inspect
from datetime import datetime

def debug_imports():
    """Debug which modules are actually being imported."""
    print("🔍 DEBUGGING IMPORTS")
    print("=" * 40)
    
    try:
        # Check if the files exist
        files_to_check = [
            'tax_optimizer.py',
            'tax_optimizer_aud_updated.py', 
            'enhanced_cgt_with_rba.py',
            'rba_converter.py'
        ]
        
        for file in files_to_check:
            if os.path.exists(file):
                size = os.path.getsize(file)
                print(f"   ✅ {file}: {size:,} bytes")
            else:
                print(f"   ❌ {file}: NOT FOUND")
        
        print(f"\n📂 Current working directory: {os.getcwd()}")
        print(f"🐍 Python path: {sys.path[0]}")
        
        # Try importing modules and check their source
        print(f"\n📦 TESTING IMPORTS:")
        
        try:
            from tax_optimizer_aud_updated import optimize_sale_for_cgt as new_optimizer
            print(f"   ✅ NEW tax optimizer imported successfully")
            print(f"      Source: {inspect.getfile(new_optimizer)}")
        except Exception as e:
            print(f"   ❌ NEW tax optimizer import failed: {e}")
        
        try:
            from tax_optimizer import optimize_sale_for_cgt as old_optimizer
            print(f"   ⚠️  OLD tax optimizer still available")
            print(f"      Source: {inspect.getfile(old_optimizer)}")
        except Exception as e:
            print(f"   ✅ OLD tax optimizer not found (good): {e}")
        
        try:
            from enhanced_cgt_with_rba import calculate_enhanced_cgt_with_rba
            print(f"   ✅ Enhanced CGT calculator imported")
            print(f"      Source: {inspect.getfile(calculate_enhanced_cgt_with_rba)}")
        except Exception as e:
            print(f"   ❌ Enhanced CGT calculator import failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import debugging failed: {e}")
        return False

def debug_data_structure():
    """Debug the actual data structure being passed to tax optimizer."""
    print("\n\n🔍 DEBUGGING DATA STRUCTURE")
    print("=" * 40)
    
    try:
        # Load cost basis and inspect structure
        with open('test_data/test_cost_basis.json', 'r') as f:
            cost_basis_dict = json.load(f)
        
        print(f"📦 Original cost basis loaded: {len(cost_basis_dict)} symbols")
        
        # Show sample original structure
        sample_symbol = list(cost_basis_dict.keys())[0]
        sample_parcels = cost_basis_dict[sample_symbol]
        
        print(f"\n📋 ORIGINAL STRUCTURE ({sample_symbol}):")
        for i, parcel in enumerate(sample_parcels[:2]):
            print(f"   Parcel {i}: {list(parcel.keys())}")
            print(f"      Data: {parcel}")
        
        # Test RBA conversion
        print(f"\n💱 TESTING RBA CONVERSION:")
        try:
            from rba_converter import RBAExchangeRateConverter
            converter = RBAExchangeRateConverter()
            
            # Convert one parcel and inspect structure
            test_parcel = sample_parcels[0]
            aud_parcel, conversion_info = converter.convert_cost_basis_parcel(test_parcel)
            
            print(f"   ✅ RBA conversion successful")
            print(f"   📋 CONVERTED STRUCTURE:")
            print(f"      Fields: {list(aud_parcel.keys())}")
            print(f"      Data: {aud_parcel}")
            
        except Exception as e:
            print(f"   ❌ RBA conversion failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test full cost basis conversion
        print(f"\n🔄 TESTING FULL COST BASIS CONVERSION:")
        try:
            from enhanced_cgt_with_rba import EnhancedCGTCalculatorWithRBA
            calculator = EnhancedCGTCalculatorWithRBA()
            
            # Convert cost basis to AUD
            aud_cost_basis = calculator._convert_cost_basis_to_aud({sample_symbol: sample_parcels})
            
            if sample_symbol in aud_cost_basis:
                converted_parcels = aud_cost_basis[sample_symbol]
                print(f"   ✅ Full conversion successful")
                print(f"   📋 FULLY CONVERTED STRUCTURE:")
                for i, parcel in enumerate(converted_parcels[:2]):
                    print(f"      Parcel {i} fields: {list(parcel.keys())}")
                    print(f"      Sample data: {parcel}")
            else:
                print(f"   ❌ Conversion failed - symbol not found")
                
        except Exception as e:
            print(f"   ❌ Full conversion failed: {e}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Data structure debugging failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_tax_optimizer():
    """Test the tax optimizer directly with different data structures."""
    print("\n\n🔍 DEBUGGING TAX OPTIMIZER")
    print("=" * 40)
    
    try:
        # Test new tax optimizer with different parcel structures
        from tax_optimizer_aud_updated import ParcelOptimizer
        
        optimizer = ParcelOptimizer()
        print(f"   ✅ NEW tax optimizer created")
        
        # Test with AUD-focused structure
        print(f"\n📦 TESTING AUD-FOCUSED PARCEL:")
        aud_parcel = {
            'units': 100.0,
            'price_aud': 150.0,
            'commission_aud': 25.0,
            'cost_per_unit_aud': 150.25,
            'total_cost_aud': 15025.0,
            'date': '12.2.21'
        }
        
        try:
            price_aud, commission_aud, cost_per_unit_aud, total_cost_aud = optimizer._extract_parcel_costs(aud_parcel)
            print(f"   ✅ AUD parcel extraction successful:")
            print(f"      Price: ${price_aud:.2f} AUD")
            print(f"      Commission: ${commission_aud:.2f} AUD")
            print(f"      Cost per unit: ${cost_per_unit_aud:.2f} AUD")
        except Exception as e:
            print(f"   ❌ AUD parcel extraction failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test with legacy structure
        print(f"\n📦 TESTING LEGACY PARCEL:")
        legacy_parcel = {
            'units': 50.0,
            'price': 75.0,
            'commission': 15.0,
            'date': '15.6.21'
        }
        
        try:
            price_aud, commission_aud, cost_per_unit_aud, total_cost_aud = optimizer._extract_parcel_costs(legacy_parcel)
            print(f"   ✅ Legacy parcel extraction successful:")
            print(f"      Price: ${price_aud:.2f}")
            print(f"      Commission: ${commission_aud:.2f}")
            print(f"      Cost per unit: ${cost_per_unit_aud:.2f}")
        except Exception as e:
            print(f"   ❌ Legacy parcel extraction failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test with real converted data
        print(f"\n📦 TESTING WITH REAL CONVERTED DATA:")
        try:
            with open('test_data/test_cost_basis.json', 'r') as f:
                cost_basis_dict = json.load(f)
            
            from rba_converter import RBAExchangeRateConverter
            converter = RBAExchangeRateConverter()
            
            # Get a real parcel and convert it
            sample_symbol = 'CYBR'  # This was in the error
            if sample_symbol in cost_basis_dict:
                original_parcel = cost_basis_dict[sample_symbol][0]
                converted_parcel, _ = converter.convert_cost_basis_parcel(original_parcel)
                
                print(f"   📋 Real converted parcel ({sample_symbol}):")
                print(f"      Fields: {list(converted_parcel.keys())}")
                
                # Test extraction
                price_aud, commission_aud, cost_per_unit_aud, total_cost_aud = optimizer._extract_parcel_costs(converted_parcel)
                print(f"   ✅ Real parcel extraction successful:")
                print(f"      Price: ${price_aud:.2f} AUD")
                print(f"      Commission: ${commission_aud:.2f} AUD")
                print(f"      Cost per unit: ${cost_per_unit_aud:.2f} AUD")
            else:
                print(f"   ⚠️ {sample_symbol} not found in cost basis")
                
        except Exception as e:
            print(f"   ❌ Real data test failed: {e}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Tax optimizer debugging failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_end_to_end():
    """Test the complete end-to-end flow with one transaction."""
    print("\n\n🔍 DEBUGGING END-TO-END FLOW")
    print("=" * 40)
    
    try:
        # Load minimal test data
        sales_df = pd.read_csv('test_data/test_sales.csv')
        with open('test_data/test_cost_basis.json', 'r') as f:
            cost_basis_dict = json.load(f)
        
        sales_df['Trade Date'] = pd.to_datetime(sales_df['Trade Date'])
        
        # Test with just one transaction
        test_sale = sales_df.iloc[0:1].copy()  # First sale only
        test_symbol = test_sale['Symbol'].iloc[0]
        
        print(f"📈 Testing with one transaction: {test_symbol}")
        print(f"   Sale details: {test_sale.iloc[0].to_dict()}")
        
        # Check if cost basis exists
        if test_symbol in cost_basis_dict:
            print(f"   ✅ Cost basis found: {len(cost_basis_dict[test_symbol])} parcels")
            
            # Show original parcels
            for i, parcel in enumerate(cost_basis_dict[test_symbol]):
                print(f"      Parcel {i}: {parcel}")
        else:
            print(f"   ❌ No cost basis for {test_symbol}")
            return False
        
        # Test the full calculation
        print(f"\n🧮 TESTING FULL CALCULATION:")
        try:
            from enhanced_cgt_with_rba import calculate_enhanced_cgt_with_rba
            
            cgt_df, updated_cost_basis, warnings, processing_log = calculate_enhanced_cgt_with_rba(
                test_sale, {test_symbol: cost_basis_dict[test_symbol]}, strategy="tax_optimal"
            )
            
            print(f"   📊 Results:")
            print(f"      CGT records: {len(cgt_df)}")
            print(f"      Warnings: {len(warnings)}")
            print(f"      Log entries: {len(processing_log)}")
            
            if len(warnings) > 0:
                print(f"   ⚠️ Warnings:")
                for warning in warnings:
                    print(f"      {warning}")
            
            if len(processing_log) > 0:
                print(f"   📋 Last 10 log entries:")
                for entry in processing_log[-10:]:
                    print(f"      {entry}")
            
            return len(cgt_df) > 0
            
        except Exception as e:
            print(f"   ❌ Full calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ End-to-end debugging failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_module_versions():
    """Check which version of each module is actually loaded."""
    print("\n\n🔍 DEBUGGING MODULE VERSIONS")
    print("=" * 40)
    
    try:
        # Check sys.modules to see what's loaded
        relevant_modules = [mod for mod in sys.modules.keys() if 'tax_' in mod or 'cgt_' in mod or 'rba_' in mod]
        
        print(f"📦 Loaded modules:")
        for mod in relevant_modules:
            module_obj = sys.modules[mod]
            if hasattr(module_obj, '__file__'):
                print(f"   {mod}: {module_obj.__file__}")
            else:
                print(f"   {mod}: (built-in)")
        
        # Try to check function signatures
        print(f"\n🔍 FUNCTION SIGNATURES:")
        try:
            from enhanced_cgt_with_rba import EnhancedCGTCalculatorWithRBA
            calculator = EnhancedCGTCalculatorWithRBA()
            
            # Check which tax optimizer is being imported inside the module
            print(f"   Checking internal imports...")
            
            # Look at the source code to see imports
            import inspect
            source = inspect.getsource(EnhancedCGTCalculatorWithRBA)
            
            if 'tax_optimizer_aud_updated' in source:
                print(f"   ✅ Using tax_optimizer_aud_updated")
            elif 'tax_optimizer' in source:
                print(f"   ⚠️ Using old tax_optimizer")
            else:
                print(f"   ❓ Import not clear from source")
                
        except Exception as e:
            print(f"   ❌ Function signature check failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Module version debugging failed: {e}")
        return False

def run_comprehensive_debugging():
    """Run all debugging tests."""
    
    print("🕵️ COMPREHENSIVE CGT SYSTEM DEBUGGING")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Working directory: {os.getcwd()}")
    print()
    
    debug_results = []
    
    # Run all debug tests
    debug_results.append(("Import Debugging", debug_imports()))
    debug_results.append(("Data Structure Debugging", debug_data_structure()))
    debug_results.append(("Tax Optimizer Debugging", debug_tax_optimizer()))
    debug_results.append(("Module Version Debugging", debug_module_versions()))
    debug_results.append(("End-to-End Debugging", debug_end_to_end()))
    
    # Summary
    print(f"\n📊 DEBUGGING SUMMARY")
    print("=" * 30)
    
    passed = 0
    total = len(debug_results)
    
    for test_name, result in debug_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} debug tests passed")
    
    if passed < total:
        print(f"\n🔧 INVESTIGATION LEADS:")
        for test_name, result in debug_results:
            if not result:
                print(f"   🔍 Focus on: {test_name}")
        
        print(f"\n💡 POTENTIAL CAUSES:")
        print(f"   • Import caching - try restarting Python session")
        print(f"   • File not saved properly - re-download artifacts")
        print(f"   • Path issues - check working directory")
        print(f"   • Module conflicts - old vs new tax optimizer")
        print(f"   • Data structure mismatch - check parcel fields")
    else:
        print(f"\n🎉 All debug tests passed - issue should be resolved!")

if __name__ == "__main__":
    run_comprehensive_debugging()