# Enhanced Australian CGT Calculator

A sophisticated Australian Capital Gains Tax calculator with advanced tax optimization for international securities trading.

## 🎯 Features

### Core Capabilities
- **Tax-Optimal Parcel Selection**: Automatically selects parcels to minimize Australian CGT burden
- **50% CGT Discount**: Properly applies discount for assets held >12 months
- **Multi-Parcel Support**: Handles complex scenarios with multiple purchase parcels per symbol
- **FIFO Alternative**: Includes traditional FIFO processing for comparison
- **AUD Conversion**: Integrates with RBA exchange rates for accurate currency conversion

### Advanced Features
- **Data Quality Assurance**: Comprehensive validation before processing
- **Detailed Audit Trail**: Complete processing logs for every optimization decision
- **Strategy Comparison**: Compare tax outcomes between different strategies
- **Professional Reporting**: ATO-compliant Excel exports

## 🏗️ Architecture

The system consists of five core modules:

1. **`tax_optimizer.py`** - Core parcel selection optimization engine
2. **`cgt_calculator_enhanced.py`** - Main CGT calculation orchestrator
3. **`data_qa.py`** - Data quality validation and inspection
4. **`test_runner.py`** - Automated testing framework
5. **`multi_parcel.htm`** - System documentation and architecture guide

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pandas
- Required dependencies (see requirements.txt)

### Basic Usage

```python
from cgt_calculator_enhanced import calculate_enhanced_cgt
import pandas as pd
import json

# Load your data
sales_df = pd.read_csv('your_sales.csv')
with open('your_cost_basis.json', 'r') as f:
    cost_basis_dict = json.load(f)

# Run enhanced CGT calculation
cgt_df, updated_basis, warnings, logs = calculate_enhanced_cgt(
    sales_df, cost_basis_dict, strategy="tax_optimal"
)

print(f"Total capital gain: ${cgt_df['capital_gain_aud'].sum():.2f}")
```

### Testing

Run the comprehensive test suite:
```bash
python test_runner.py
```

Validate your data quality:
```bash
python data_qa.py
```

## 📊 Expected Data Formats

### Sales Data (CSV)
Required columns:
- `Symbol`: Stock symbol (e.g., 'AAPL', 'MSFT')
- `Trade Date`: Sale date (YYYY-MM-DD format)
- `Type`: Transaction type ('SELL')
- `Quantity`: Number of shares sold
- `Price (USD)`: Sale price per share in USD
- `Proceeds (USD)`: Total gross proceeds
- `Commission (USD)`: Transaction commission

### Cost Basis Data (JSON)
```json
{
  "AAPL": [
    {
      "units": 100.0,
      "price": 150.00,
      "commission": 10.00,
      "date": "15.03.21"
    }
  ]
}
```

## 🎯 Tax Optimization Strategy

The enhanced calculator uses a sophisticated optimization approach:

1. **Phase 1**: Prioritize long-term holdings (>365 days) for 50% CGT discount
2. **Phase 2**: Within each category, select highest cost basis first to minimize gains
3. **Phase 3**: Handle partial parcel sales with proportional commission allocation

This typically results in significant tax savings compared to simple FIFO processing.

## 🔍 Data Quality Checks

Before processing, the system validates:
- ✅ All sold symbols have available cost basis
- ✅ Sufficient units available for each sale
- ✅ Valid date formats and data types
- ✅ No missing or corrupted data

## 📈 Output

The system generates comprehensive CGT reports including:
- Detailed per-parcel calculations
- CGT discount applications
- Tax optimization decisions
- ATO-compliant summaries
- Processing audit trails

## 🧪 Testing Data

The repository includes test data for validation:
- `test_data/test_sales.csv`: Sample sales transactions
- `test_data/test_cost_basis.json`: Sample cost basis data

**Note**: Test data is for development only and should not be used for actual tax calculations.

## ⚠️ Important Disclaimers

- **Professional Advice Required**: This software is for calculation assistance only
- **Verification Needed**: All results should be reviewed by qualified tax professionals
- **No Tax Advice**: This tool does not provide tax advice or guarantee ATO compliance
- **Beta Software**: Thorough testing and validation recommended before production use

## 🔧 Development

### Project Structure
```
enhanced_cgt_test/
├── tax_optimizer.py           # Core optimization engine
├── cgt_calculator_enhanced.py # Main calculation module
├── data_qa.py                 # Data quality assurance
├── test_runner.py             # Testing framework
├── multi_parcel.htm           # Documentation
├── test_data/                 # Test datasets
└── README.md                  # This file
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Run tests to ensure functionality
4. Submit a pull request

## 📋 Roadmap

- [x] Core tax optimization engine
- [x] Enhanced CGT calculator
- [x] Data quality validation
- [x] Comprehensive testing framework
- [ ] Streamlit web interface integration
- [ ] RBA exchange rate integration
- [ ] Advanced analytics dashboard
- [ ] Multi-year portfolio analysis

## 📞 Support

For technical support or questions about the enhanced CGT system:
- Review the architecture documentation (`multi_parcel.htm`)
- Check the test suite for usage examples
- Consult with qualified tax professionals for compliance questions

---

**Version**: 2.0.0-enhanced  
**Last Updated**: June 2025  
**License**: Private/Proprietary