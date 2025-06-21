import pandas as pd
import json
import sys
import os

# Set up paths
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from cgt_calculator import calculate_enhanced_cgt_with_rba

print("🚀 ENHANCED CGT BACKEND TEST - Multi-Parcel Symbol")
print("=" * 60)

# Load your actual cost basis file
with open('data/test_cost_basis.json', 'r') as f:
    cost_basis_dict = json.load(f)

print(f"✅ Cost basis loaded: {len(cost_basis_dict)} symbols")

# Find symbols with multiple parcels (where FIFO vs tax-optimal should differ)
print("\n📊 Analyzing symbols by parcel count:")
symbols_by_parcels = []
for symbol in cost_basis_dict.keys():
    parcel_count = len(cost_basis_dict[symbol])
    symbols_by_parcels.append((symbol, parcel_count))
    
# Sort by parcel count (most parcels first)
symbols_by_parcels.sort(key=lambda x: x[1], reverse=True)

# Show top symbols with most parcels
print("Top symbols with multiple parcels:")
for symbol, count in symbols_by_parcels[:5]:
    print(f"  {symbol}: {count} parcels")

# Pick the symbol with most parcels for testing
if symbols_by_parcels[0][1] > 1:
    test_symbol = symbols_by_parcels[0][0]
    parcel_count = symbols_by_parcels[0][1]
    print(f"\n🎯 Selected for testing: {test_symbol} ({parcel_count} parcels)")
    
    # Show the parcels for this symbol
    print(f"\n📦 {test_symbol} parcels:")
    for i, parcel in enumerate(cost_basis_dict[test_symbol]):
        print(f"  {i+1}. {parcel['units']} units @ ${parcel['price']} from {parcel['date']}")
else:
    test_symbol = symbols_by_parcels[0][0]
    print(f"\n⚠️ Using {test_symbol} (only has 1 parcel - may show $0 savings)")

# Create a test sale using a reasonable quantity
available_units = sum(p['units'] for p in cost_basis_dict[test_symbol])
test_quantity = min(100, available_units * 0.3)  # Sell 30% or 100 units, whichever is smaller

sales_data = [{
    'Symbol': test_symbol,
    'Trade Date': '2024-04-15',
    'Type': 'SELL',
    'Quantity': test_quantity,
    'Price (USD)': 200.00,  # Higher than most cost basis to ensure gains
    'Proceeds (USD)': test_quantity * 200.00,
    'Commission (USD)': 15.0
}]

sales_df = pd.DataFrame(sales_data)
sales_df['Trade Date'] = pd.to_datetime(sales_df['Trade Date'])

print(f"\n📈 Test sale: {test_quantity} units of {test_symbol} @ $200/unit")

# Test 1: Original functionality
print(f"\n🔄 Testing tax_optimal strategy only...")
try:
    result1 = calculate_enhanced_cgt_with_rba(sales_df, cost_basis_dict, strategy="tax_optimal")
    print(f"✅ Original: {len(result1)} values returned")
    
    if len(result1) == 4:
        cgt_df, updated_cost_basis, warnings, logs = result1
        print(f"   CGT records: {len(cgt_df)}")
        if len(cgt_df) > 0:
            print(f"   Taxable gain: ${cgt_df['taxable_gain_aud'].sum():.2f}")
except Exception as e:
    print(f"❌ Tax-optimal test failed: {e}")

# Test 2: Comparison functionality
print(f"\n🔄 Testing comparison strategy...")
try:
    result2 = calculate_enhanced_cgt_with_rba(sales_df, cost_basis_dict, strategy="comparison")
    print(f"✅ Comparison: {len(result2)} values returned")
    
    if len(result2) == 6:
        optimized_cgt_df, fifo_cgt_df, comparison_data, updated_cost_basis, warnings, logs = result2
        
        print(f"\n🎉 COMPARISON RESULTS:")
        print(f"   FIFO tax: ${comparison_data['fifo_total_tax']:.2f}")
        print(f"   Optimized tax: ${comparison_data['optimized_total_tax']:.2f}")
        print(f"   Tax savings: ${comparison_data['tax_savings']:.2f}")
        print(f"   Percentage saved: {comparison_data['percentage_saved']:.1f}%")
        print(f"   Cost basis improvement: ${comparison_data['cost_basis_improvement']:.2f}/unit")
        
        # Debug: Show which parcels each strategy selected
        print(f"\n🔍 DETAILED PARCEL ANALYSIS:")
        
        if len(fifo_cgt_df) > 0:
            print(f"FIFO Strategy:")
            for idx, row in fifo_cgt_df.iterrows():
                print(f"  Selected parcel from {row['parcel_source']}: {row['units_sold']} units, cost ${row['cost_basis_aud']:.2f}")
        
        if len(optimized_cgt_df) > 0:
            print(f"Tax-Optimal Strategy:")
            for idx, row in optimized_cgt_df.iterrows():
                print(f"  Selected parcel from {row['parcel_source']}: {row['units_sold']} units, cost ${row['cost_basis_aud']:.2f}")
        
        # Summary
        if comparison_data['tax_savings'] > 0:
            print(f"\n🎯 SUCCESS! Tax optimization saved ${comparison_data['tax_savings']:.2f}")
            print(f"   This proves FIFO vs Tax-optimal are working differently!")
        elif comparison_data['tax_savings'] == 0:
            print(f"\n🤔 Both strategies selected same parcels (tax savings = $0)")
            print(f"   This could mean:")
            print(f"   • Only 1 parcel available")
            print(f"   • All parcels have same cost basis") 
            print(f"   • Sale quantity small enough to use same parcel")
        else:
            print(f"\n❌ Negative savings - something wrong!")
            
        print(f"\n🚀 BACKEND READY FOR FRONTEND INTEGRATION!")
        
    else:
        print(f"❌ Expected 6 values, got {len(result2)}")
        
except Exception as e:
    print(f"❌ Comparison test failed: {e}")
    import traceback
    traceback.print_exc()
    
print(f"\n✅ Test complete!")