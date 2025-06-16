#!/usr/bin/env python3
"""
Debug Date Parsing - Test the problematic dates
"""

from datetime import datetime
import pandas as pd

def test_parse_date(date_str: str) -> datetime:
    """Test version of the enhanced date parsing."""
    if not date_str or pd.isna(date_str):
        print(f"❌ Empty date string: '{date_str}'")
        return datetime(2020, 1, 1)
    
    # Clean the date string
    date_str = str(date_str).strip()
    print(f"🔍 Testing date: '{date_str}' (length: {len(date_str)})")
    
    # List of date formats to try
    date_formats = [
        "%d/%m/%y",     # 19/12/24, 01/05/25
        "%d/%m/%Y",     # 19/12/2024, 01/05/2025
        "%d.%m.%y",     # 12.2.21, 23.6.21
        "%d.%m.%Y",     # 12.2.2021
        "%Y-%m-%d",     # 2024-12-19
        "%d-%m-%y",     # 19-12-24
        "%d-%m-%Y",     # 19-12-2024
    ]
    
    for i, fmt in enumerate(date_formats):
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            print(f"✅ Format {i+1} ({fmt}) worked: {parsed_date}")
            
            # Handle 2-digit years
            if parsed_date.year < 2000:
                if parsed_date.year < 50:  # 00-49 = 2000-2049
                    parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
                else:  # 50-99 = 1950-1999
                    parsed_date = parsed_date.replace(year=parsed_date.year + 1900)
                print(f"🔧 Adjusted year: {parsed_date}")
            
            # Sanity check
            if 2000 <= parsed_date.year <= 2030:
                print(f"✅ Final result: {parsed_date}")
                return parsed_date
            else:
                print(f"❌ Year out of range: {parsed_date.year}")
                continue
                
        except ValueError as e:
            print(f"❌ Format {i+1} ({fmt}) failed: {e}")
            continue
    
    print(f"❌ All formats failed for '{date_str}'")
    return datetime(2020, 1, 1)

def test_days_calculation():
    """Test the days calculation."""
    sale_date = datetime(2025, 5, 1)  # May 1, 2025
    
    # Test problematic dates
    test_dates = [
        "04/04/25",   # Should be April 4, 2025 (27 days)
        "07/04/25",   # Should be April 7, 2025 (24 days) 
        "19/12/24",   # Should be Dec 19, 2024 (133 days)
        "01/05/25",   # Should be May 1, 2025 (0 days)
        "12.2.21",    # Should be Feb 12, 2021 (1173 days)
    ]
    
    print(f"\n📅 Testing days calculation (sale date: {sale_date}):")
    print("=" * 60)
    
    for date_str in test_dates:
        print(f"\n🧪 Testing: {date_str}")
        parsed = test_parse_date(date_str)
        days_held = (sale_date - parsed).days
        is_long_term = days_held >= 365
        print(f"🕒 Days held: {days_held} ({'LT' if is_long_term else 'ST'})")

if __name__ == "__main__":
    test_days_calculation()