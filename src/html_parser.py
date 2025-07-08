import pandas as pd
from bs4 import BeautifulSoup
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def parse_interactive_brokers_html(html_file_path):
    """
    Parse Interactive Brokers HTML trade confirmation report to CSV format.
    
    Args:
        html_file_path (str): Path to the HTML file
        
    Returns:
        pd.DataFrame: DataFrame with trade data in standardized format
    """
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the trades table
    trades_table = soup.find('table', {'id': 'summaryDetailTable'})
    if not trades_table:
        raise ValueError("Could not find trades table in HTML file")
    
    trades_data = []
    
    # Find all trade rows (not header or subtotal rows)
    trade_rows = trades_table.find_all('tr')
    
    for row in trade_rows:
        cells = row.find_all('td')
        
        # Skip header rows, subtotal rows, and asset category rows
        if (len(cells) < 10 or 
            row.get('class') and 'subtotal' in row.get('class') or
            row.get('class') and 'row-summary' in row.get('class') or
            any(cell.get('class') and ('header-asset' in cell.get('class') or 
                                     'header-currency' in cell.get('class')) for cell in cells)):
            continue
            
        # Extract trade data
        if len(cells) >= 13:
            try:
                # Parse date/time
                date_time_str = cells[2].get_text(strip=True)
                date_part = date_time_str.split(',')[0]  # Get date part before comma
                trade_date = datetime.strptime(date_part, '%Y-%m-%d').date()
                
                # Clean numeric values
                quantity_str = cells[6].get_text(strip=True).replace(',', '')
                price_str = cells[7].get_text(strip=True).replace(',', '')
                proceeds_str = cells[8].get_text(strip=True).replace(',', '').replace('-', '')
                comm_str = cells[9].get_text(strip=True).replace(',', '').replace('-', '')
                
                trade_data = {
                    'Symbol': cells[1].get_text(strip=True),
                    'Trade Date': trade_date.strftime('%Y-%m-%d'),
                    'Type': cells[5].get_text(strip=True),
                    'Quantity': float(quantity_str) if quantity_str else 0,
                    'Price': float(price_str) if price_str else 0,
                    'Proceeds': float(proceeds_str) if proceeds_str else 0,
                    'Commission': float(comm_str) if comm_str else 29.0,
                    'Exchange': cells[4].get_text(strip=True),
                    'Settlement Date': cells[3].get_text(strip=True),
                    'Order Type': cells[11].get_text(strip=True) if len(cells) > 11 else '',
                    'Code': cells[12].get_text(strip=True) if len(cells) > 12 else ''
                }
                
                trades_data.append(trade_data)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping row due to parsing error: {e}")
                continue
    
    if not trades_data:
        raise ValueError("No trade data found in HTML file")
    
    df = pd.DataFrame(trades_data)
    
    # Standardize column names to match expected CSV format
    column_mapping = {
        'Symbol': 'Symbol',
        'Trade Date': 'Date',
        'Type': 'Type',
        'Quantity': 'Quantity',
        'Price': 'Price',
        'Proceeds': 'Proceeds',
        'Commission': 'Commission'
    }
    
    # Keep only the columns we need and rename them
    df_standard = df[list(column_mapping.keys())].rename(columns=column_mapping)
    
    return df_standard

def convert_html_to_csv(html_file_path, output_csv_path=None):
    """
    Convert Interactive Brokers HTML file to CSV format.
    
    Args:
        html_file_path (str): Path to the HTML file
        output_csv_path (str, optional): Path for output CSV. If None, creates one based on input filename
        
    Returns:
        str: Path to the created CSV file
    """
    df = parse_interactive_brokers_html(html_file_path)
    
    if output_csv_path is None:
        # Create CSV filename based on HTML filename
        base_name = html_file_path.replace('.htm', '').replace('.html', '')
        output_csv_path = f"{base_name}_trades.csv"
    
    df.to_csv(output_csv_path, index=False)
    logger.info(f"Converted HTML to CSV: {output_csv_path}")
    logger.info(f"Found {len(df)} trades")
    
    return output_csv_path