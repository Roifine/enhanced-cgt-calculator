#!/usr/bin/env python3
"""
CGT Calculator Streamlit App
Milestone 2: Multi-File UX - Upload Multiple Files → Preview → Process → Download
"""

import streamlit as st
import pandas as pd
import tempfile
import os
import sys
from datetime import datetime
import plotly.graph_objects as go
import streamlit.components.v1

# Must be the first Streamlit command
st.set_page_config(
    page_title="CGT Calculator",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded"  # This forces sidebar open by default
)

# Add src directory to path for backend imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import backend modules
try:
    from csv_processor import process_statement_csv
    from cgt_calculator import calculate_enhanced_cgt_with_rba
except ImportError as e:
    st.error(f"❌ Backend import error: {e}")
    st.error("Please ensure all backend modules are in the 'src/' directory")
    st.stop()

def track_event(event_name, event_category="user_journey", event_label="", value=None):
    """Track Google Analytics events in Streamlit"""
    
    # Build the gtag event call
    gtag_params = {
        'event_category': event_category,
    }
    
    if event_label:
        gtag_params['event_label'] = event_label
    
    if value is not None:
        gtag_params['value'] = value
    
    # Convert params to JavaScript object format
    params_js = ", ".join([f"'{k}': '{v}'" for k, v in gtag_params.items()])
    
    # Inject the tracking script
    st.components.v1.html(f"""
    <script>
    if (typeof gtag !== 'undefined') {{
        gtag('event', '{event_name}', {{{params_js}}});
        console.log('📊 Tracked: {event_name}');
    }} else {{
        console.log('⚠️ Google Analytics not loaded');
    }}
    </script>
    """, height=0)

def create_symbol_timeline(symbol_records):
    """
    Create interactive timeline with buy and sell event dots.
    
    Args:
        symbol_records: DataFrame subset for one symbol
        
    Returns:
        Plotly figure object
    """
    
    if len(symbol_records) == 0:
        return None
    
    # Create timeline figure
    fig = go.Figure()
    
    # Collect all buy and sell events
    buy_events = []
    sell_events = []
    
    for idx, record in symbol_records.iterrows():
        # Extract dates and USD prices
        buy_date = pd.to_datetime(record['purchase_date'])
        sell_date = pd.to_datetime(record['sale_date'])
        buy_price_usd = record.get('buy_unit_price_usd', 0)
        sell_price_usd = record.get('sale_unit_price_usd', 0)
        units = record['units_sold']
        
        # Calculate holding period for context
        holding_days = (sell_date - buy_date).days
        holding_months = round(holding_days / 30.44, 1)
        
        # Buy event
        buy_hover = (
            f"<b>PURCHASE PARCEL PORTION</b><br>"
            f"<b>Original purchase date:</b> {buy_date.strftime('%d %b %Y')}<br>"
            f"<b>Purchase price:</b> ${buy_price_usd:.2f} USD per unit<br>"
            f"<b>Units from this parcel:</b> {units:.0f}<br>"
            f"<b>Cost for these units:</b> ${buy_price_usd * units:,.0f} USD<br>"
            f"<b>Used for sale on:</b> {sell_date.strftime('%d %b %Y')}"
        )
        
        buy_events.append({
            'date': buy_date,
            'price': buy_price_usd,
            'units': units,
            'hover': buy_hover,
            'parcel_id': idx
        })
        
        # Sell event
        sell_hover = (
            f"<b>SALE PARCEL PORTION</b><br>"
            f"<b>Sale date:</b> {sell_date.strftime('%d %b %Y')}<br>"
            f"<b>Units sold from this parcel:</b> {units:.0f}<br>"
            f"<b>Sale price:</b> ${sell_price_usd:.2f} USD per unit<br>"
            f"<b>Sale proceeds:</b> ${sell_price_usd * units:,.0f} USD<br>"
            f"<b>Originally purchased:</b> {buy_date.strftime('%d %b %Y')} @ ${buy_price_usd:.2f}<br>"
            f"<b>Held for:</b> {holding_months:.1f} months<br>"
            f"<b>Capital gain:</b> ${record['capital_gain_aud']:.0f} AUD"
        )
        
        sell_events.append({
            'date': sell_date,
            'price': sell_price_usd,
            'units': units,
            'hover': sell_hover,
            'parcel_id': idx,
            'is_long_term': record['is_long_term']
        })
    
    # Function to calculate y-positions to avoid overlapping dots
    def calculate_y_positions(events):
        """Calculate y positions to avoid overlapping dots on same dates."""
        if not events:
            return []
        
        # Group events by date
        date_groups = {}
        for i, event in enumerate(events):
            date_str = event['date'].strftime('%Y-%m-%d')
            if date_str not in date_groups:
                date_groups[date_str] = []
            date_groups[date_str].append(i)
        
        # Calculate y positions
        y_positions = [0] * len(events)
        offset_step = 0.15  # Vertical spacing between overlapping dots
        
        for date_str, indices in date_groups.items():
            if len(indices) == 1:
                # Single dot on this date - keep at center (y=0)
                y_positions[indices[0]] = 0
            else:
                # Multiple dots on same date - spread them vertically
                num_dots = len(indices)
                # Center the group around y=0
                start_y = -(num_dots - 1) * offset_step / 2
                for i, idx in enumerate(indices):
                    y_positions[idx] = start_y + (i * offset_step)
        
        return y_positions
    
    # Add buy events (blue dots) with offset positioning
    if buy_events:
        buy_dates = [event['date'] for event in buy_events]
        buy_y = calculate_y_positions(buy_events)
        buy_hovers = [event['hover'] for event in buy_events]
        
        fig.add_trace(go.Scatter(
            x=buy_dates,
            y=buy_y,
            mode='markers',
            marker=dict(
                size=15,
                color='#2E86AB',  # Blue for buy
                symbol='circle',
                line=dict(width=2, color='white')
            ),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=buy_hovers,
            name='Buy Events',
            showlegend=False
        ))
    
    # Add sell events (red/green dots based on long-term) with offset positioning
    if sell_events:
        sell_dates = [event['date'] for event in sell_events]
        sell_y = calculate_y_positions(sell_events)
        sell_hovers = [event['hover'] for event in sell_events]
        sell_colors = ['#51cf66' if event['is_long_term'] else '#ff6b6b' for event in sell_events]
        
        fig.add_trace(go.Scatter(
            x=sell_dates,
            y=sell_y,
            mode='markers',
            marker=dict(
                size=15,
                color=sell_colors,
                symbol='circle',
                line=dict(width=2, color='white')
            ),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=sell_hovers,
            name='Sell Events',
            showlegend=False
        ))
    
    # Update layout
    fig.update_layout(
        title="",
        xaxis=dict(
            title="Timeline",
            type='date',
            showgrid=True,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title="",
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=[-0.6, 0.6]  # Expanded range for vertically offset dots
        ),
        height=150,  # Fixed compact height
        margin=dict(l=20, r=20, t=20, b=50),
        hovermode='closest',
        plot_bgcolor='white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def format_date_for_display(date_value):
    """
    Format date as '15 Apr 2024' for display.
    
    Args:
        date_value: datetime object or string
        
    Returns:
        Formatted date string
    """
    try:
        if isinstance(date_value, str):
            # Convert string to datetime if needed
            date_obj = pd.to_datetime(date_value)
        else:
            date_obj = date_value
        
        # Format as "15 Apr 2024"
        return date_obj.strftime('%d %b %Y')
    
    except Exception as e:
        # Fallback for any date parsing issues
        return str(date_value)


def format_currency_aud(amount):
    """
    Format currency amount as $15,000.0 for display.
    
    Args:
        amount: Numeric amount
        
    Returns:
        Formatted currency string
    """
    try:
        # Format with 1 decimal place and thousands separator
        return f"${amount:,.1f}"
    
    except Exception as e:
        # Fallback for any formatting issues
        return f"${float(amount):.1f}" if amount is not None else "$0.0"

def format_cgt_data_for_export(cgt_df: pd.DataFrame) -> pd.DataFrame:
    """
    Format CGT DataFrame for user-friendly CSV export with custom columns and sorting.
    
    Args:
        cgt_df: Raw CGT calculation DataFrame
        
    Returns:
        Formatted DataFrame with user-specified columns
    """
    if len(cgt_df) == 0:
        return pd.DataFrame()
    
    # Create new DataFrame with only the columns user wants, in specified order
    export_df = pd.DataFrame()
    
    # 1. Symbol
    export_df['Symbol'] = cgt_df['symbol']
    
    # 2. Date of sale (DD/MM/YYYY format)
    export_df['Date of Sale'] = pd.to_datetime(cgt_df['sale_date']).dt.strftime('%d/%m/%Y')
    
    # 3. Units sold
    export_df['Units Sold'] = cgt_df['units_sold'].round(2)
    
    # 4. Price sold USD
    export_df['Price Sold USD'] = cgt_df['sale_unit_price_usd'].round(2)
    
    # 5. Commissions sale (USD)
    export_df['Commissions Sale'] = cgt_df['sale_commission_usd'].round(2)
    
    # 6. Commissions buy (USD)
    export_df['Commissions Buy'] = cgt_df['buy_commission_usd'].round(2)
    
    # 7. Total proceedings in USD (net proceeds)
    export_df['Total Proceedings USD'] = cgt_df['net_proceeds_usd'].round(2)
    
    # 8. Total cost in USD (including commission)
    export_df['Total Cost USD'] = cgt_df['cost_basis_usd'].round(2)
    
    # 9. Sale exchange rate
    export_df['Sale Exchange Rate'] = cgt_df['exchange_rate_sell'].round(4)
    
    # 10. Purchase exchange rate
    export_df['Purchase Exchange Rate'] = cgt_df['exchange_rate_buy'].round(4)
    
    # 11. 12 months discount (Yes/No)
    export_df['12 Months Discount'] = cgt_df['is_long_term'].map({True: 'Yes', False: 'No'})
    
    # 12. Capital gains (in AUD)
    export_df['Capital Gains'] = cgt_df['capital_gain_aud'].round(2)
    
    # Sort by Symbol (alphabetically), then by Date of Sale
    export_df = export_df.sort_values(['Symbol', 'Date of Sale'], ascending=[True, True])
    
    # Reset index to get clean row numbers
    export_df = export_df.reset_index(drop=True)
    
    return export_df


# ENHANCED ERROR HANDLING (Optional addition)
def show_results_with_error_handling():
    """Enhanced version with error handling for production."""
    
    try:
        # Call the main show_results function
        show_results()
        
    except KeyError as e:
        st.error(f"❌ Missing required data: {e}")
        st.write("Please ensure your CGT calculation completed successfully.")
        
    except Exception as e:
        st.error(f"❌ Error displaying results: {str(e)}")
        st.write("Please try refreshing the page or re-processing your files.")
        
        # Show debug info in development
        if st.checkbox("Show debug info"):
            st.exception(e)
def save_uploaded_files(uploaded_files):
    """Save multiple uploaded files to temporary locations for backend processing."""
    temp_file_paths = []
    
    for uploaded_file in uploaded_files:
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                temp_file_paths.append(tmp_file.name)
        except Exception as e:
            st.error(f"❌ Error saving file {uploaded_file.name}: {e}")
            # Clean up any successfully created temp files
            for path in temp_file_paths:
                if os.path.exists(path):
                    os.unlink(path)
            return None
    
    return temp_file_paths

def preview_fy24_25_sales(uploaded_files):
    """Preview FY24-25 sale events without full CGT calculation."""
    
    # Create progress container
    progress_container = st.container()
    
    with progress_container:
        st.header("🔍 Preview FY24-25 Sale Events")
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    try:
        # Step 1: Save files
        status_text.text("💾 Saving uploaded files...")
        progress_bar.progress(30)
        
        temp_file_paths = save_uploaded_files(uploaded_files)
        if not temp_file_paths:
            st.error("❌ Failed to save uploaded files")
            return None
        
        # Step 2: Extract FY24-25 sales only
        status_text.text("📊 Extracting FY24-25 sale events...")
        progress_bar.progress(80)
        
        cost_basis_dict, fy24_25_sales, csv_warnings, csv_logs = process_statement_csv(temp_file_paths)
        
        # Step 3: Clean up temp files
        for temp_path in temp_file_paths:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        # Step 4: Complete
        status_text.text("✅ Preview ready!")
        progress_bar.progress(100)
        
        return fy24_25_sales, csv_warnings
        
    except Exception as e:
        # Clean up temp files on error
        if 'temp_file_paths' in locals():
            for temp_path in temp_file_paths:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        st.error(f"❌ Preview failed: {str(e)}")
        return None

def display_sales_preview(fy24_25_sales, warnings=None):
    """Display the FY24-25 sales preview table and calculate button."""
    
    st.markdown("---")
    st.header("📊 FY24-25 Sale Events Preview")
    
    if len(fy24_25_sales) == 0:
        st.warning("⚠️ No sale events found in FY24-25 period (July 1, 2024 - June 30, 2025)")
        return
    
    # Display summary
    st.success(f"✅ Found {len(fy24_25_sales)} sale events in FY24-25 period")
    
    
    # Display the sales table
    st.write("These are the sale transactions that will be used for CGT calculation:")
    
    # Format the dataframe for display with error handling
    try:
        display_df = fy24_25_sales.copy()
        
        # Keep only the specified columns: Symbol, units sold, price USD, date, commission
        desired_columns = []
        column_mapping = {
            'Symbol': 'Symbol',
            'Quantity': 'Units Sold', 
            'Price (USD)': 'Price USD',  # Updated to match CSV processor output
            'Commission (USD)': 'Commission USD',  # Updated to match CSV processor output
            'Trade Date': 'Date'
        }
        
        missing_columns = []
        for original_col, display_name in column_mapping.items():
            if original_col in display_df.columns:
                desired_columns.append(original_col)
            else:
                missing_columns.append(original_col)
        
        if missing_columns:
            st.info(f"ℹ️ Some optional columns not found: {', '.join(missing_columns)}")
        
        if desired_columns:
            display_df = display_df[desired_columns]
            # Rename columns for better display
            display_df = display_df.rename(columns=column_mapping)
        else:
            st.error("❌ No expected columns found in the sales data")
            return
            
    except Exception as e:
        st.error(f"❌ Error preparing sales data for display: {str(e)}")
        return
    
    # Format dates for better display with error handling
    if 'Date' in display_df.columns:
        try:
            display_df['Date'] = pd.to_datetime(display_df['Date'], errors='coerce').dt.date
            # Check if any dates couldn't be parsed
            null_dates = display_df['Date'].isnull().sum()
            if null_dates > 0:
                st.warning(f"⚠️ {null_dates} date(s) could not be parsed and will show as blank")
        except Exception as e:
            st.warning(f"⚠️ Error formatting dates: {str(e)}")
            # Keep original values if formatting fails
            pass
    
    # Format numerical columns with error handling
    if 'Price' in display_df.columns:
        try:
            display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else "N/A")
        except Exception as e:
            st.warning(f"⚠️ Error formatting prices: {str(e)}")
    
    if 'Total Value' in display_df.columns:
        try:
            display_df['Total Value'] = display_df['Total Value'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) and isinstance(x, (int, float)) else "N/A")
        except Exception as e:
            st.warning(f"⚠️ Error formatting total values: {str(e)}")
    
    # Display the table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Show warnings if any
    if warnings:
        with st.expander(f"⚠️ Processing Warnings ({len(warnings)})", expanded=False):
            for warning in warnings:
                st.warning(warning)
    
    # Calculate button
    st.markdown("---")
    st.subheader("🚀 Ready to Calculate?")
    st.write("Review the sale events above. When ready, click below to calculate your CGT liability:")
    
    if st.button("🧮 Calculate CGT", type="primary", use_container_width=True):
        # Store the preview data and trigger full calculation
        st.session_state['preview_completed'] = True
        st.session_state['fy24_25_sales_preview'] = fy24_25_sales
        st.rerun()

def preview_uploaded_files(uploaded_files):
    """Display preview information for uploaded files."""
    st.subheader("📋 File Preview")
    
    for i, uploaded_file in enumerate(uploaded_files, 1):
        with st.expander(f"📄 File {i}: {uploaded_file.name}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Size:** {uploaded_file.size:,} bytes")
                st.write(f"**Type:** {uploaded_file.type}")
            
            try:
                # Read full file to show complete structure
                df_preview = pd.read_csv(uploaded_file)
                
                with col2:
                    st.write(f"**Total Rows:** {len(df_preview):,}")
                    st.write(f"**Columns:** {len(df_preview.columns)}")
                
                with col3:
                    # Show date range if we can detect date columns
                    date_cols = [col for col in df_preview.columns if 'date' in col.lower() or 'time' in col.lower()]
                    if date_cols:
                        try:
                            date_col = date_cols[0]
                            dates = pd.to_datetime(df_preview[date_col], errors='coerce')
                            valid_dates = dates.dropna()
                            if len(valid_dates) > 0:
                                st.write(f"**Date Range:** {valid_dates.min().strftime('%Y-%m-%d')} to {valid_dates.max().strftime('%Y-%m-%d')}")
                        except:
                            pass
                
                # Show all column names
                st.write("**All Columns:**")
                st.write(", ".join(df_preview.columns))
                
                # Show expanded preview table (first 10 rows)
                st.write("**Preview (first 10 rows):**")
                st.dataframe(df_preview.head(10), use_container_width=True)
                
                # Reset file pointer for later processing
                uploaded_file.seek(0)
                
            except Exception as e:
                st.error(f"⚠️ Could not preview file: {str(e)}")

# Add this function to your app.py file 
# Place it anywhere before the sidebar_feedback() function

def save_simple_feedback(feedback_text, email=""):
    """Save simple feedback to CSV file."""
    import csv
    import os
    from datetime import datetime
    
    feedback_file = 'user_feedback.csv'
    file_exists = os.path.isfile(feedback_file)
    
    try:
        with open(feedback_file, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'feedback', 'email', 'location']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'feedback': feedback_text.strip(),
                'email': email.strip(),
                'location': 'sidebar'
            })
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        return False


def sidebar_feedback():
    """Always-available feedback in sidebar"""
    with st.sidebar:
        st.markdown("### 💬 Quick Feedback")
        
        if 'sidebar_feedback_submitted' not in st.session_state:
            st.session_state['sidebar_feedback_submitted'] = False
        
        if not st.session_state['sidebar_feedback_submitted']:
            with st.form("sidebar_feedback"):
                feedback = st.text_area(
                    "How's the tool?",
                    placeholder="Works great! Could use...",
                    height=80
                )
                email = st.text_input("Email (optional)", placeholder="you@email.com")
                
                
                # New consent checkbox
                consent_contact = st.checkbox(
                    "I agree to be contacted for further feedback",
                    help="Optional: We may reach out to learn more about your experience"
                 )
                
                if st.form_submit_button("Send", use_container_width=True):
                    if feedback.strip():
                        # Save feedback (same function as before)
                        save_simple_feedback(feedback, email)
                        st.session_state['sidebar_feedback_submitted'] = True
                        st.rerun()
        else:
            st.success("Thanks! 🙏")
            if st.button("More feedback?", use_container_width=True):
                st.session_state['sidebar_feedback_submitted'] = False
                st.rerun()
                

def main():
    """Main Streamlit application."""
    # Page configuration
    st.set_page_config(
        page_title="CGT Calculator",
        page_icon="🧮",
        layout="wide"
    )
    
    # Google Analytics initialization with cross-domain tracking
    st.components.v1.html("""
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-GPFCSTT5L0"></script>
    <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());

    gtag('config', 'G-GPFCSTT5L0', {
        // ✅ ADD CROSS-DOMAIN TRACKING
        'linker': {
            'domains': ['auscgtcalculator.com', 'enhanced-cgt-calculator-tt4ky7nudjf7mctexxxaff.streamlit.app']
        },
        'allow_linker': true,
        'cookie_domain': 'auto',
        'cookie_flags': 'SameSite=None;Secure'
    });

    console.log('✅ Google Analytics loaded with cross-domain tracking');
    </script>
    """, height=0)
    
    # feedback form in sidebar
    sidebar_feedback()
    
    track_event("calculator_page_view", "user_journey", "streamlit_app")  # ← ADD THIS
    
    # Hidden admin via URL parameter
    if st.query_params.get("admin") == "true":
        admin_pass = st.text_input("Admin Password", type="password")
        
        if admin_pass == "cgt2025":  # 🔐 Change this to your secret password!
            try:
                feedback_df = pd.read_csv('user_feedback.csv')
                st.success(f"📊 {len(feedback_df)} feedback entries found")
                
                # Show newest first
                feedback_df = feedback_df.sort_values('timestamp', ascending=False)
                st.dataframe(feedback_df, use_container_width=True)
                
                # Download option
                csv_data = feedback_df.to_csv(index=False)
                st.download_button(
                    "📥 Download All Feedback", 
                    data=csv_data, 
                    file_name=f"feedback_export_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
            except FileNotFoundError:
                st.info("📝 No feedback submitted yet - file will be created when first feedback is received")
            except Exception as e:
                st.error(f"Error loading feedback: {str(e)}")
        
        st.stop()  # Don't show the rest of the app in admin mode
        
    # Header
    st.markdown("<h1 style='text-align: center;'>Shares Tax Calculator</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center;'>Smart, secure, and simple", unsafe_allow_html=True)
    st.markdown("---")
    
    # Step 1: File Upload
    st.header("📁 Step 1: Upload Your Trading Statements for FY 2024-25")
   
    
    uploaded_files = st.file_uploader(
        "Drop your CSV files here",
        type=['csv'],
        accept_multiple_files=True,
        help="Trading Activity Statements (not individual trade confirmations) • CSV format • Multiple files OK"
    )
    # What you need checklist
    st.success("""
    📋 **What You Need:**

    ✅ **FY 2024-25 transactions** with Symbol, Date, Buy/Sell, Quantity, Price (required)

    ✅ **Previous years complete transactions** (optional, great if you bought shares in previous years and you sold them this year)

    ✅ **We automatically handle:** Different column names, extra columns are fine to leave in
    """)

    if uploaded_files:
        # Show file info summary
        total_size = sum(f.size for f in uploaded_files)
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded ({total_size:,} bytes total)")
        
        # File preview section
        preview_uploaded_files(uploaded_files)
        
        st.markdown("---")
        
        # Step 2: Preview or Process buttons
        if 'preview_sales' not in st.session_state:
            # Show preview button first
            if st.button("🔍 Preview FY24-25 Sales", type="primary", use_container_width=True):
                result = preview_fy24_25_sales(uploaded_files)
                if result:
                    fy24_25_sales, warnings = result
                    st.session_state['preview_sales'] = fy24_25_sales
                    st.session_state['preview_warnings'] = warnings
                    st.rerun()
        
        # Step 3: Show preview if available
        if 'preview_sales' in st.session_state and not st.session_state.get('preview_completed', False):
            display_sales_preview(
                st.session_state['preview_sales'], 
                st.session_state.get('preview_warnings', [])
            )
        
        # Step 4: Process full calculation if preview completed
        if st.session_state.get('preview_completed', False) and 'cgt_results' not in st.session_state:
            process_multiple_files(uploaded_files)
    
    # Step 5: Show Results (if available)
    if 'cgt_results' in st.session_state:
        show_results()

def process_multiple_files(uploaded_files):
    """Process multiple uploaded files using backend modules with progress tracking."""
    
    # Create progress containers
    progress_container = st.container()
    status_container = st.container()
    
    with progress_container:
        st.header("🔄 Processing Files")
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    try:
        # Step 1: Save files and show progress
        status_text.text("💾 Saving uploaded files...")
        progress_bar.progress(10)
        
        temp_file_paths = save_uploaded_files(uploaded_files)
        if not temp_file_paths:
            status_container.error("❌ Failed to save uploaded files")
            return
        
        # Step 2: CSV Processing
        status_text.text("📊 Processing CSV files...")
        progress_bar.progress(30)
        
        cost_basis_dict, fy24_25_sales, csv_warnings, csv_logs = process_statement_csv(temp_file_paths)
        
        # Step 3: CGT Calculation
        status_text.text("💱 Calculating CGT with RBA exchange rates...")
        progress_bar.progress(70)
        
        optimized_cgt_df, fifo_cgt_df, comparison_data, updated_cost_basis, cgt_warnings, processing_logs = calculate_enhanced_cgt_with_rba(
        fy24_25_sales, 
        cost_basis_dict, 
        strategy="comparison"
        )
        
        # Step 4: Finalize
        status_text.text("✅ Processing complete!")
        progress_bar.progress(100)
        
        # Clean up temp files
        for temp_path in temp_file_paths:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        # Store results in session state
        st.session_state['cgt_results'] = optimized_cgt_df  # Use optimized for display
        st.session_state['fifo_results'] = fifo_cgt_df
        st.session_state['comparison_data'] = comparison_data
        st.session_state['cost_basis'] = cost_basis_dict
        st.session_state['updated_cost_basis'] = updated_cost_basis
        st.session_state['csv_warnings'] = csv_warnings
        st.session_state['cgt_warnings'] = cgt_warnings
        st.session_state['processing_timestamp'] = datetime.now()
        st.session_state['processed_files'] = [f.name for f in uploaded_files]
        
        # Show success message with details
        with status_container:
            if len(optimized_cgt_df) > 0:
                st.success(f"🎉 Successfully processed {len(uploaded_files)} files and generated {len(optimized_cgt_df)} CGT records!")
                
                # Show processing summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Files Processed", len(uploaded_files))
                with col2:
                    st.metric("Symbols Found", len(cost_basis_dict))
                with col3:
                    st.metric("FY24-25 Sales", len(fy24_25_sales))
            else:
                st.warning("⚠️ Processing complete but no CGT records generated. Check the warnings below.")
        
        # Force page rerun to show results
        st.rerun()
        
    except Exception as e:
        track_event("processing_error", "errors", str(e)[:50])  # ← ADD THIS (truncate error)
        # Clean up temp files on error
        if 'temp_file_paths' in locals():
            for temp_path in temp_file_paths:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        with status_container:
            st.error(f"❌ Processing failed: {str(e)}")
            
            # Show detailed error information
            with st.expander("🔍 Error Details", expanded=False):
                st.code(str(e))
                st.write("**Troubleshooting tips:**")
                st.write("• Check that your CSV files have the expected columns (Symbol, Trade Date, Type, etc.)")
                st.write("• Ensure files are not corrupted or empty")
                st.write("• Try processing files individually to identify which one is causing issues")

def show_results():
    """Display processing results and download options."""
    
    st.markdown("---")
    st.header("📊 Step 2: Results")
    
    cgt_df = st.session_state['cgt_results']
    csv_warnings = st.session_state.get('csv_warnings', [])
    cgt_warnings = st.session_state.get('cgt_warnings', [])
    processing_time = st.session_state.get('processing_timestamp')
    processed_files = st.session_state.get('processed_files', [])
    
    # File processing summary
    with st.expander(f"📁 Processed Files ({len(processed_files)})", expanded=False):
        for i, filename in enumerate(processed_files, 1):
            st.write(f"{i}. {filename}")
    
    # Summary metrics
    if len(cgt_df) > 0:
        st.subheader("💰 Financial Summary")
        col1, col2, col3 = st.columns(3)

        with col1:
            total_gain = cgt_df['capital_gain_aud'].sum()
            st.metric("Total Capital Gain", f"${total_gain:,.2f} AUD")

        with col2:
            total_taxable = cgt_df['taxable_gain_aud'].sum()
            st.metric("Taxable Capital Gain", f"${total_taxable:,.2f} AUD")
        
        with col3:
            # Tax calculator
            total_taxable = cgt_df['taxable_gain_aud'].sum()
            
            # Income bracket selector
            tax_bracket = st.selectbox(
                "Estimated Tax You'll Pay",
                options=[
                    "Select your income bracket",
                    "$0 - $18,200 (0%)",
                    "$18,201 - $45,000 (16%)",
                    "$45,001 - $135,000 (30%)",
                    "$135,001 - $190,000 (37%)",
                    "$190,001+ (45%)"
                ],
                key="tax_bracket",
                help="Capital gains are added to your other income. Select the bracket that includes your total income (salary + capital gains)."
            )
            
            # Calculate and display estimated tax
            if tax_bracket != "Select your income bracket":
                # Extract tax rate from selection
                if "0%" in tax_bracket:
                    rate = 0.0
                elif "16%" in tax_bracket:
                    rate = 0.16
                elif "30%" in tax_bracket:
                    rate = 0.30
                elif "37%" in tax_bracket:
                    rate = 0.37
                elif "45%" in tax_bracket:
                    rate = 0.45
                
                estimated_tax = total_taxable * rate
                st.metric("", f"${estimated_tax:,.0f} AUD")
            else:
                st.metric("", "")
                
        
        # Get comparison data for result box
        comparison_data = st.session_state.get('comparison_data', {})
        fifo_reportable = comparison_data.get('fifo_total_tax', 0)
        optimized_reportable = comparison_data.get('optimized_total_tax', 0)
        difference = fifo_reportable - optimized_reportable
        
        # Show optimization result above the chart
        if difference > 0:
            st.success(f"""
            **Result: You report ${difference:,.0f} less ({(difference/fifo_reportable*100):.1f}% reduction) using tax-optimal strategy**
            
            **How we optimized:**
            • Prioritized parcels eligible for 50% CGT discount
            • Selected higher cost basis parcels to minimize gains
            • Optimized for Australian tax rules
            """)
        
    
        st.subheader("📊 Strategy Comparison")    
        # Simple Visual Strategy Comparison Chart (Bulletproof Version)
        st.write("Visual comparison of reportable capital gains by strategy")
        
        
        # Create simple bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=['FIFO', 'Tax-Optimal'],
                y=[fifo_reportable, optimized_reportable],
                marker_color=['#ff6b6b', '#51cf66'],  # Red and Green
                text=[f'${fifo_reportable:,.0f}', f'${optimized_reportable:,.0f}'],
                textposition='auto'
            )
        ])
        
        # Basic layout
        fig.update_layout(
            title='Reportable Capital Gains Comparison',
            xaxis_title="Strategy",
            yaxis_title="Amount (AUD)",
            height=400
        )
        
        # Display the chart
        st.plotly_chart(fig, use_container_width=True)
        
        
        if len(cgt_df) > 0:
            st.subheader("📊 Transaction Timeline by Symbol")
            st.write("Visual timeline showing when you bought and sold each parcel, with buy/sell prices in USD:")
            
            # Group CGT data by symbol
            for symbol in sorted(cgt_df['symbol'].unique()):
                symbol_records = cgt_df[cgt_df['symbol'] == symbol].copy()
                
                # Calculate total capital gain for this symbol
                total_capital_gain = symbol_records['capital_gain_aud'].sum()
                transaction_count = len(symbol_records)
                
                # Calculate summary stats
                long_term_count = sum(symbol_records['is_long_term'])
                short_term_count = transaction_count - long_term_count
                
                # Create expandable section for each symbol
                with st.expander(f"**{symbol}** - {transaction_count} Transaction{'s' if transaction_count != 1 else ''} (Capital gain to report ${total_capital_gain:.0f} AUD)", expanded=False):
                    
                    # Create and display timeline
                    timeline_fig = create_symbol_timeline(symbol_records)
                    if timeline_fig:
                        st.plotly_chart(timeline_fig, use_container_width=True)
                        
                        # Add explanatory text
                        st.caption("🔵 Blue = Purchase parcel portions • 🟢 Green = Long-term sales (>12 months) • 🔴 Red = Short-term sales (<12 months)")
                    else:
                        st.warning("Could not create timeline for this symbol")
        
        # CSV Preview section
        st.subheader("👀 Preview CSV Report")
        
        # Generate formatted CSV data for preview
        csv_preview_df = format_cgt_data_for_export(cgt_df)
        
        if len(csv_preview_df) > 0:
            st.write("Preview of your CGT report (first 5 rows):")
            preview_rows = min(5, len(csv_preview_df))
            st.dataframe(
                csv_preview_df.head(preview_rows), 
                use_container_width=True,
                hide_index=True
            )
            
            if len(csv_preview_df) > 5:
                st.caption(f"Showing {preview_rows} of {len(csv_preview_df)} total rows")
            else:
                st.caption(f"Showing all {len(csv_preview_df)} rows")
        else:
            st.warning("No data available for preview")

        # Download section
        st.subheader("💾 Download Results")
        
        # Create Excel file with multiple sheets
        timestamp = processing_time.strftime("%Y%m%d_%H%M%S") if processing_time else "export"
        excel_filename = f"cgt_results_{timestamp}.xlsx"
        
        # Create summary data for Sheet 2
        long_term_count = len(cgt_df[cgt_df['is_long_term']])  # ✅ Define it first
        cgt_discount_savings = 0
        if long_term_count > 0:
            cgt_discount_savings = cgt_df[cgt_df['is_long_term'] & (cgt_df['capital_gain_aud'] > 0)]['capital_gain_aud'].sum() * 0.5
        
        summary_data = {
            'Metric': [
                'Total Capital Gain (AUD)',
                'Total Taxable Gain/Loss (AUD)'
            ],
            'Value': [
                f"${total_gain:,.2f}",
                f"${total_taxable:,.2f}"
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        # Create Excel file in memory
        from io import BytesIO
        buffer = BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Sheet 1: User-friendly CGT Records (formatted)
            formatted_cgt_df = format_cgt_data_for_export(cgt_df)
            formatted_cgt_df.to_excel(writer, sheet_name='CGT Records', index=False)
            
            # Sheet 2: Summary
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add processed files list to summary sheet
            files_df = pd.DataFrame({'Processed Files': processed_files})
            files_df.to_excel(writer, sheet_name='Summary', startrow=len(summary_df) + 3, index=False)
            
            # Sheet 3: Raw Technical Data (for debugging/reference)
            cgt_df.to_excel(writer, sheet_name='Technical Data', index=False)
        
        excel_data = buffer.getvalue()
        
        track_event("results_with_download_ready", "user_success", "excel_report")
        
        st.download_button(
            label="📥 Download Complete Report (Excel)",
            data=excel_data,
            file_name=excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
           

        
    else:
        st.warning("⚠️ No CGT records were generated from your files.")
    
    # Show warnings if any
    all_warnings = csv_warnings + cgt_warnings
    if all_warnings:
        with st.expander(f"⚠️ Warnings ({len(all_warnings)})", expanded=False):
            for warning in all_warnings:
                st.warning(warning)
    
    # Processing info
    if processing_time:
        st.caption(f"Processed {len(processed_files)} file(s) at {processing_time.strftime('%Y-%m-%d %H:%M:%S')} using tax-optimal strategy")
    

if __name__ == "__main__":
    main()
    