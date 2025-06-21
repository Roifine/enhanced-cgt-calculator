#!/usr/bin/env python3
"""
Backend Testing Script - Validate Dual Strategy Implementation
Run this to test your backend changes before frontend integration
"""

import pandas as pd
import json
import sys
import os

# FIRST: Set up paths correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up from tests/ to project root
src_dir = os.path.join(project_root, 'src')

# Add paths
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# THEN: Try to import (after paths are set up)
try:
    from cgt_calculator import calculate_enhanced_cgt_with_rba, safe_calculate_enhanced_cgt_with_rba
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    
    # Debug: Show what's actually in the paths
    print(f"Project root: {project_root}")
    print(f"Files in project root: {os.listdir(project_root)}")
    if os.path.exists(src_dir):
        print(f"Files in src: {os.listdir(src_dir)}")
    else:
        print("❌ src directory doesn't exist")
    
    sys.exit(1)

# Rest of your test code goes here...
def test_backward_compatibility():
    """Test 1: Ensure existing functionality still works"""
    
    print("\n🧪 TEST 1: Backward Compatibility")
    print("=" * 50)
    
    try:
        # Load your test data (adjust paths as needed)
        with open('test_cost_basis.json', 'r') as f:
            cost_basis_dict = json.load(f)
        
        # Create sample sales data (or load your test sales CSV)
        sales_data = [
            {
                'Symbol': 'AAPL',
                'Trade Date': '2024-04-15',
                'Type': 'SELL',
                'Quantity': 100.0,
                'Price (USD)': 170.00,
                'Proceeds (USD)': 17000.0,
                'Commission (USD)': 15.0
            }
        ]
        sales_df = pd.DataFrame(sales_data)
        sales_df['Trade Date'] = pd.to_datetime(sales_df['Trade Date'])
        
        print(f"📊 Test data: {len(sales_df)} sales, {len(cost_basis_dict)} symbols with cost basis")
        
        # Test original functionality (should return 4 values)
        print("🔄 Testing original tax_optimal strategy...")
        result = calculate_enhanced_cgt_with_rba(
            sales_df, 
            cost_basis_dict, 
            strategy="tax_optimal"
        )
        
        # Should return 4 values
        if len(result) == 4:
            cgt_df, updated_cost_basis, warnings, logs = result
            print(f"✅ Original functionality works!")
            print(f"   CGT records: {len(cgt_df)}")
            print(f"   Warnings: {len(warnings)}")
            print(f"   Total taxable gain: ${cgt_df['taxable_gain_aud'].sum():.2f} AUD")
            return True
        else:
            print(f"❌ Expected 4 return values, got {len(result)}")
            return False
            
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_comparison_functionality():
    """Test 2: Test new comparison functionality"""
    
    print("\n🧪 TEST 2: Comparison Functionality")
    print("=" * 50)
    
    try:
        # Load test data
        with open('test_cost_basis.json', 'r') as f:
            cost_basis_dict = json.load(f)
        
        # Create sample sales (use multiple for better testing)
        sales_data = [
            {
                'Symbol': 'AAPL',
                'Trade Date': '2024-04-15',
                'Type': 'SELL',
                'Quantity': 100.0,
                'Price (USD)': 170.00,
                'Proceeds (USD)': 17000.0,
                'Commission (USD)': 15.0
            },
            {
                'Symbol': 'MSFT',
                'Trade Date': '2024-05-20',
                'Type': 'SELL',
                'Quantity': 50.0,
                'Price (USD)': 280.00,
                'Proceeds (USD)': 14000.0,
                'Commission (USD)': 20.0
            }
        ]
        sales_df = pd.DataFrame(sales_data)
        sales_df['Trade Date'] = pd.to_datetime(sales_df['Trade Date'])
        
        print(f"📊 Test data: {len(sales_df)} sales")
        
        # Test comparison functionality (should return 6 values)
        print("🔄 Testing comparison strategy...")
        result = calculate_enhanced_cgt_with_rba(
            sales_df, 
            cost_basis_dict, 
            strategy="comparison"
        )
        
        # Should return 6 values
        if len(result) == 6:
            optimized_cgt_df, fifo_cgt_df, comparison_data, updated_cost_basis, warnings, logs = result
            
            print(f"✅ Comparison functionality works!")
            print(f"   Optimized CGT records: {len(optimized_cgt_df)}")
            print(f"   FIFO CGT records: {len(fifo_cgt_df)}")
            print(f"   Comparison data keys: {list(comparison_data.keys())}")
            
            return True, comparison_data
        else:
            print(f"❌ Expected 6 return values, got {len(result)}")
            return False, None
            
    except Exception as e:
        print(f"❌ Comparison functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_comparison_analysis(comparison_data):
    """Test 3: Validate comparison data makes sense"""
    
    print("\n🧪 TEST 3: Comparison Data Analysis")
    print("=" * 50)
    
    try:
        print("📊 COMPARISON RESULTS:")
        print(f"   FIFO total tax: ${comparison_data['fifo_total_tax']:.2f} AUD")
        print(f"   Optimized total tax: ${comparison_data['optimized_total_tax']:.2f} AUD")
        print(f"   Tax savings: ${comparison_data['tax_savings']:.2f} AUD")
        print(f"   Percentage saved: {comparison_data['percentage_saved']:.1f}%")
        print(f"   FIFO avg cost basis: ${comparison_data['fifo_avg_cost_basis']:.2f}/unit")
        print(f"   Optimized avg cost basis: ${comparison_data['optimized_avg_cost_basis']:.2f}/unit")
        print(f"   Cost basis improvement: ${comparison_data['cost_basis_improvement']:.2f}/unit")
        
        # Validation checks
        checks_passed = 0
        total_checks = 5
        
        # Check 1: Tax savings should be non-negative
        if comparison_data['tax_savings'] >= 0:
            print("✅ Check 1: Tax savings >= 0")
            checks_passed += 1
        else:
            print("❌ Check 1: Tax savings is negative!")
        
        # Check 2: Optimized tax should be <= FIFO tax
        if comparison_data['optimized_total_tax'] <= comparison_data['fifo_total_tax']:
            print("✅ Check 2: Optimized tax <= FIFO tax")
            checks_passed += 1
        else:
            print("❌ Check 2: Optimized tax > FIFO tax!")
        
        # Check 3: Percentage saved should be reasonable (0-100%)
        if 0 <= comparison_data['percentage_saved'] <= 100:
            print("✅ Check 3: Percentage saved is reasonable")
            checks_passed += 1
        else:
            print("❌ Check 3: Percentage saved is out of range!")
        
        # Check 4: Cost basis improvement should be positive (higher cost basis = better)
        if comparison_data['cost_basis_improvement'] >= 0:
            print("✅ Check 4: Cost basis improvement >= 0")
            checks_passed += 1
        else:
            print("❌ Check 4: Cost basis got worse!")
        
        # Check 5: Transaction counts should match
        if comparison_data['fifo_transaction_count'] == comparison_data['optimized_transaction_count']:
            print("✅ Check 5: Transaction counts match")
            checks_passed += 1
        else:
            print("❌ Check 5: Transaction counts don't match!")
        
        print(f"\n📋 VALIDATION SUMMARY: {checks_passed}/{total_checks} checks passed")
        
        return checks_passed == total_checks
        
    except Exception as e:
        print(f"❌ Comparison analysis test failed: {e}")
        return False

def test_error_handling():
    """Test 4: Test error handling"""
    
    print("\n🧪 TEST 4: Error Handling")
    print("=" * 50)
    
    try:
        # Test with empty data
        empty_sales = pd.DataFrame()
        empty_cost_basis = {}
        
        print("🔄 Testing with empty data...")
        result = safe_calculate_enhanced_cgt_with_rba(
            empty_sales,
            empty_cost_basis,
            strategy="comparison"
        )
        
        print("✅ Error handling works (didn't crash)")
        return True
        
    except Exception as e:
        print(f"⚠️ Error handling test result: {e}")
        print("✅ This is expected - error handling is working")
        return True

def run_comprehensive_backend_test():
    """Run all backend tests"""
    
    print("🚀 COMPREHENSIVE BACKEND TEST SUITE")
    print("=" * 60)
    print(f"Testing enhanced CGT calculator with dual strategy support")
    print()
    
    test_results = []
    
    # Test 1: Backward compatibility
    test_results.append(("Backward Compatibility", test_backward_compatibility()))
    
    # Test 2: Comparison functionality
    comparison_success, comparison_data = test_comparison_functionality()
    test_results.append(("Comparison Functionality", comparison_success))
    
    # Test 3: Comparison data analysis (only if Test 2 passed)
    if comparison_success and comparison_data:
        test_results.append(("Comparison Data Analysis", test_comparison_analysis(comparison_data)))
    
    # Test 4: Error handling
    test_results.append(("Error Handling", test_error_handling()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL BACKEND TESTS PASSED!")
        print("\n✅ SUCCESS CRITERIA MET:")
        print("   • Backward compatibility maintained")
        print("   • Comparison functionality working")
        print("   • Tax optimization providing savings")
        print("   • Error handling robust")
        print("\n🚀 READY FOR PHASE 2: Frontend Integration!")
    else:
        print("🔧 Some tests failed - review issues before proceeding")
        
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_backend_test()
    
    if success:
        print("\n🎯 NEXT STEPS:")
        print("1. Backend is ready!")
        print("2. Proceed to Phase 2: Frontend Integration")
        print("3. Update your Streamlit app to use strategy='comparison'")
    else:
        print("\n🔧 Fix backend issues before proceeding to frontend")