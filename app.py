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

def prepare_symbol_table_data(symbol_records):
        """
        Prepare symbol records for display table with proper formatting.
        
        Args:
            symbol_records: DataFrame subset for one symbol
            
        Returns:
            DataFrame formatted for display
        """
    
        # Create display dataframe
        display_df = pd.DataFrame()
        
        # Format Sale Date
        display_df['Sale Date'] = symbol_records['sale_date'].apply(format_date_for_display)
        
        # Units Sold (keep as number for proper sorting)
        display_df['Units Sold'] = symbol_records['units_sold']
        
        # Total Proceeds AUD (formatted as currency string)
        display_df['Total Proceeds AUD'] = symbol_records['net_proceeds_aud'].apply(format_currency_aud)
        
        # Cost AUD (formatted as currency string)
        display_df['Cost AUD'] = symbol_records['cost_basis_aud'].apply(format_currency_aud)
        
        # LONG TERM (Yes/No)
        display_df['LONG TERM'] = symbol_records['is_long_term'].apply(lambda x: 'Yes' if x else 'No')
        
        # Capital Gain AUD (formatted as currency string)
        display_df['Capital Gain (AUD)'] = symbol_records['capital_gain_aud'].apply(format_currency_aud)
        
        # Sort by sale date (most recent first)
        display_df = display_df.sort_values('Sale Date', ascending=False)
        
        return display_df


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

def preview_uploaded_files(uploaded_files):
    """Display preview information for uploaded files."""
    st.subheader("📋 File Preview")
    
    for i, uploaded_file in enumerate(uploaded_files, 1):
        with st.expander(f"📄 File {i}: {uploaded_file.name}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Size:** {uploaded_file.size:,} bytes")
                st.write(f"**Type:** {uploaded_file.type}")
            
            try:
                # Read first few rows to show structure
                df_preview = pd.read_csv(uploaded_file, nrows=5)
                
                with col2:
                    st.write(f"**Columns:** {len(df_preview.columns)}")
                    st.write(f"**Detected columns:** {', '.join(df_preview.columns[:3])}...")
                
                # Show preview table
                st.write("**Preview (first 5 rows):**")
                st.dataframe(df_preview, use_container_width=True)
                
                # Reset file pointer for later processing
                uploaded_file.seek(0)
                
            except Exception as e:
                st.error(f"⚠️ Could not preview file: {str(e)}")
                

def main():
    """Main Streamlit application."""
    
    # Page configuration
    st.set_page_config(
        page_title="CGT Calculator",
        page_icon="🧮",
        layout="wide"
    )
    
    # Header
    st.title("🧮 Australian CGT Calculator")
    st.markdown("**Multi-File Support - Upload Multiple CSVs → Preview → Process → Download Results**")
    st.markdown("---")
    
    # Step 1: File Upload
    st.header("📁 Step 1: Upload CSV Files")
    
    uploaded_files = st.file_uploader(
        "Choose CSV files with your trading data",
        type=['csv'],
        accept_multiple_files=True,
        help="Upload one or more CSV files from your brokers (CommSec, Interactive Brokers, etc.)"
    )
    
    if uploaded_files:
        # Show file info summary
        total_size = sum(f.size for f in uploaded_files)
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded ({total_size:,} bytes total)")
        
        # File preview section
        preview_uploaded_files(uploaded_files)
        
        st.markdown("---")
        
        # Process button
        if st.button("🚀 Process All Files", type="primary", use_container_width=True):
            process_multiple_files(uploaded_files)
    
    # Step 2: Show Results (if available)
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
                    "$18,201 - $45,000 (19%)",
                    "$45,001 - $120,000 (32.5%)",
                    "$120,001 - $180,000 (37%)",
                    "$180,001+ (45%)"
                ],
                key="tax_bracket",
                help="Capital gains are added to your other income. Select the bracket that includes your total income (salary + capital gains)."
            )
            
            # Calculate and display estimated tax
            if tax_bracket != "Select your income bracket":
                # Extract tax rate from selection
                if "19%" in tax_bracket:
                    rate = 0.19
                elif "32.5%" in tax_bracket:
                    rate = 0.325
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
            st.subheader("📋 Transaction Breakdown by Symbol")
            st.write("Detailed view of each symbol's transactions and tax calculations:")
            
            # Group CGT data by symbol
            for symbol in sorted(cgt_df['symbol'].unique()):
                symbol_records = cgt_df[cgt_df['symbol'] == symbol].copy()
                
                # Calculate total capital gain for this symbol
                total_capital_gain = symbol_records['capital_gain_aud'].sum()
                transaction_count = len(symbol_records)
                
                # Create expandable section for each symbol
                with st.expander(f"**{symbol}** - {transaction_count} Transaction{'s' if transaction_count != 1 else ''} (Capital gain to report ${total_capital_gain:.1f})", expanded=True):
                    
                    # Prepare data for display
                    display_data = prepare_symbol_table_data(symbol_records)
                    
                    # Display the table
                    st.dataframe(
                        display_data,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Sale Date": st.column_config.TextColumn("Sale Date", width="medium"),
                            "Units Sold": st.column_config.NumberColumn("Units Sold", format="%.0f"),
                            "Total Proceeds AUD": st.column_config.TextColumn("Total Proceeds AUD", width="medium"),
                            "Cost AUD": st.column_config.TextColumn("Cost AUD", width="medium"),
                            "LONG TERM": st.column_config.TextColumn("LONG TERM", width="small"),
                            "Capital Gain (AUD)": st.column_config.TextColumn("Capital Gain (AUD)", width="medium")
                        }
                    )
        # Results table
        st.subheader("📋 Detailed CGT Records")
        
        # Add some helpful info about the table
        st.write("Each row represents a portion of a parcel sold, optimized for minimum tax liability.")
        
        st.dataframe(
            cgt_df,
            use_container_width=True,
            hide_index=True
        )
        
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
                'Files Processed',
                'CGT Records Generated', 
                'Total Capital Gain (AUD)',
                'Total Taxable Gain (AUD)',
                'CGT Discount Savings (AUD)',
                'Long-term Holdings Count',
                'Short-term Holdings Count',
                'Processing Strategy',
                'Processing Date'
            ],
            'Value': [
                len(processed_files),
                len(cgt_df),
                f"${total_gain:,.2f}",
                f"${total_taxable:,.2f}", 
                f"${cgt_discount_savings:,.2f}",
                long_term_count,
                len(cgt_df) - long_term_count,
                'Tax-optimal selection',
                processing_time.strftime('%Y-%m-%d %H:%M:%S') if processing_time else 'Unknown'
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        # Create Excel file in memory
        from io import BytesIO
        buffer = BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Sheet 1: Detailed CGT Records
            cgt_df.to_excel(writer, sheet_name='CGT Records', index=False)
            
            # Sheet 2: Summary
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add processed files list to summary sheet
            files_df = pd.DataFrame({'Processed Files': processed_files})
            files_df.to_excel(writer, sheet_name='Summary', startrow=len(summary_df) + 3, index=False)
        
        excel_data = buffer.getvalue()
        
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