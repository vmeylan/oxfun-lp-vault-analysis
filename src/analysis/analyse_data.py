import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import os
import sys
from datetime import datetime

def format_number(value):
    """
    Format a number with dollar sign, commas, and appropriate suffix.
    - ≥1,000,000: 'm'
    - ≥1,000: 'k'
    - <1,000: no suffix
    Handles negative values appropriately.
    """
    try:
        sign = '-' if value < 0 else ''
        abs_value = abs(value)
        if abs_value >= 1e6:
            return f"{sign}$OX {abs_value / 1e6:.2f}m"
        elif abs_value >= 1e3:
            return f"{sign}$OX {abs_value / 1e3:.0f}k"
        else:
            return f"{sign}$OX {abs_value:.0f}"
    except:
        return value

def load_and_clean_data(csv_path: str) -> pd.DataFrame:
    """
    Load the CSV data into a DataFrame and clean the data.

    Parameters:
    - csv_path: Path to the CSV file.

    Returns:
    - Cleaned DataFrame.
    """
    # Check if the file exists
    if not os.path.isfile(csv_path):
        print(f"Error: The file '{csv_path}' does not exist.")
        sys.exit(1)

    # Load the CSV file
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading '{csv_path}': {e}")
        sys.exit(1)

    # Display initial data
    print("Initial Data:")
    print(df.head().to_string(index=False))

    # Convert 'Date' column to datetime
    try:
        df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    except Exception as e:
        print(f"Error converting 'Date' column to datetime: {e}")
        sys.exit(1)

    # Function to clean numeric columns
    def clean_numeric(column):
        return column.replace({',': '', '"': ''}, regex=True).astype(float)

    # Clean the 'PNL (OX)' column
    try:
        # Remove '+' signs by escaping them
        df['PNL (OX)'] = df['PNL (OX)'].replace({'\\+': ''}, regex=True)
        # Remove commas and quotes, then convert to float
        df['PNL (OX)'] = df['PNL (OX)'].str.replace(',', '').str.replace('"', '').astype(float)
    except Exception as e:
        print(f"Error cleaning 'PNL (OX)' column: {e}")
        sys.exit(1)

    # Clean other numeric columns
    numeric_columns = ['OX Balance', 'OX Value (USD)', 'OX Perps Volume', 'Fees']
    for col in numeric_columns:
        try:
            df[col] = clean_numeric(df[col])
        except Exception as e:
            print(f"Error cleaning '{col}' column: {e}")
            sys.exit(1)

    # Sort the DataFrame by Date in ascending order
    df = df.sort_values(by='Date')

    # Reset index
    df.reset_index(drop=True, inplace=True)

    # Create a formatted DataFrame for printing
    df_formatted = df.copy()
    for col in ['PNL (OX)', 'OX Balance', 'OX Value (USD)', 'OX Perps Volume']:
        df_formatted[col] = df_formatted[col].apply(format_number)

    # Format Fees separately (assuming Fees are in whole numbers without needing 'k' or 'm')
    if 'Fees' in df_formatted.columns:
        df_formatted['Fees'] = df_formatted['Fees'].apply(lambda x: f"$OX {int(x):,}")

    print("\nCleaned Data:")
    print(df_formatted.head().to_string(index=False))

    return df

def analyze_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Perform analysis on the DataFrame.

    Parameters:
    - df: Cleaned DataFrame.

    Returns:
    - DataFrame with Cumulative PNL (OX).
    """
    # Group by 'Date' and sum 'PNL (OX)'
    df_grouped = df.groupby('Date', as_index=False)['PNL (OX)'].sum()

    # Calculate Cumulative PNL (OX)
    df_grouped['Cumulative PNL (OX)'] = df_grouped['PNL (OX)'].cumsum()

    # Create a formatted DataFrame for printing
    df_formatted = df_grouped.copy()
    df_formatted['PNL (OX)'] = df_grouped['PNL (OX)'].apply(format_number)
    df_formatted['Cumulative PNL (OX)'] = df_grouped['Cumulative PNL (OX)'].apply(format_number)

    print("\nData with Cumulative PNL (OX):")
    print(df_formatted.head().to_string(index=False))

    return df_grouped


def visualize_cumulative_area(df: pd.DataFrame, output_dir: str):
    """
    Create a chart showing only the cumulative OX PNL with a dynamic overlay:
    a green area when cumulative PNL is positive and a red area when negative.
    The fill opacity adjusts based on the magnitude of the cumulative PNL.
    The chart title is updated with the number of days the PNL was positive and negative,
    including the corresponding percentages since inception and the last cumulative PNL value
    in abbreviated format (e.g. 'm' for million, 'k' for thousand).

    Parameters:
    - df: DataFrame with analysis (should contain 'Date' and 'Cumulative PNL (OX)' columns).
    - output_dir: Directory to save the visualization.

    Returns:
    - HTML div string for the cumulative PNL area chart.
    """
    fig_area = go.Figure()

    # Add the cumulative PNL line
    fig_area.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Cumulative PNL (OX)'],
        mode='lines+markers',
        name='Cumulative PNL (OX)',
        line=dict(color='blue', width=2),
        hovertemplate='Date: %{x}<br>Cumulative PNL: $OX %{y:,.0f}<extra></extra>'
    ))

    # Determine maximum absolute cumulative value for normalization
    max_abs = df['Cumulative PNL (OX)'].abs().max()
    if max_abs == 0:
        max_abs = 1  # Prevent division by zero

    shapes = []
    # Iterate over each segment to add dynamic fill shapes
    for i in range(len(df) - 1):
        x0 = df['Date'].iloc[i]
        x1 = df['Date'].iloc[i + 1]
        y0 = df['Cumulative PNL (OX)'].iloc[i]
        y1 = df['Cumulative PNL (OX)'].iloc[i + 1]

        # Convert dates to string format for the path
        x0_str = pd.Timestamp(x0).strftime('%Y-%m-%d')
        x1_str = pd.Timestamp(x1).strftime('%Y-%m-%d')

        if y0 * y1 >= 0:
            # Segment does not cross zero
            avg = (y0 + y1) / 2
            if avg >= 0:
                base_color = (0, 255, 0)  # Green for positive
            else:
                base_color = (255, 0, 0)  # Red for negative
            opacity = 0.2 + 0.8 * (abs(avg) / max_abs)
            opacity = min(opacity, 1)
            path = f'M {x0_str},0 L {x0_str},{y0} L {x1_str},{y1} L {x1_str},0 Z'
            shapes.append(dict(
                type="path",
                path=path,
                fillcolor=f'rgba({base_color[0]},{base_color[1]},{base_color[2]},{opacity:.2f})',
                line=dict(width=0),
                layer='below',
                xref='x',
                yref='y'
            ))
        else:
            # Segment crosses zero: split into two segments
            # Calculate the crossing point
            ratio = (0 - y0) / (y1 - y0)
            x0_ts = pd.Timestamp(x0).timestamp()
            x1_ts = pd.Timestamp(x1).timestamp()
            x_cross_ts = x0_ts + ratio * (x1_ts - x0_ts)
            x_cross = datetime.fromtimestamp(x_cross_ts)
            x_cross_str = pd.Timestamp(x_cross).strftime('%Y-%m-%d')

            # First segment from x0 to x_cross
            if y0 != 0:
                avg1 = (y0 + 0) / 2
                if avg1 >= 0:
                    base_color = (0, 255, 0)
                else:
                    base_color = (255, 0, 0)
                opacity = 0.2 + 0.8 * (abs(avg1) / max_abs)
                opacity = min(opacity, 1)
                path1 = f'M {x0_str},0 L {x0_str},{y0} L {x_cross_str},0 Z'
                shapes.append(dict(
                    type="path",
                    path=path1,
                    fillcolor=f'rgba({base_color[0]},{base_color[1]},{base_color[2]},{opacity:.2f})',
                    line=dict(width=0),
                    layer='below',
                    xref='x',
                    yref='y'
                ))
            # Second segment from x_cross to x1
            if y1 != 0:
                avg2 = (0 + y1) / 2
                if avg2 >= 0:
                    base_color = (0, 255, 0)
                else:
                    base_color = (255, 0, 0)
                opacity = 0.2 + 0.8 * (abs(avg2) / max_abs)
                opacity = min(opacity, 1)
                path2 = f'M {x_cross_str},0 L {x1_str},{y1} L {x1_str},0 Z'
                shapes.append(dict(
                    type="path",
                    path=path2,
                    fillcolor=f'rgba({base_color[0]},{base_color[1]},{base_color[2]},{opacity:.2f})',
                    line=dict(width=0),
                    layer='below',
                    xref='x',
                    yref='y'
                ))

    # Compute positive and negative day counts
    total_days = len(df)
    positive_days = (df['Cumulative PNL (OX)'] > 0).sum()
    negative_days = (df['Cumulative PNL (OX)'] < 0).sum()
    positive_percent = (positive_days / total_days) * 100
    negative_percent = (negative_days / total_days) * 100

    # Get the last cumulative PNL value and format it using the format_number function
    last_cum = df['Cumulative PNL (OX)'].iloc[-1]
    last_cum_formatted = format_number(last_cum)

    # Compute max, min, and median cumulative PNL values and format them
    max_cum = df['Cumulative PNL (OX)'].max()
    min_cum = df['Cumulative PNL (OX)'].min()
    median_cum = df['Cumulative PNL (OX)'].median()
    max_cum_formatted = format_number(max_cum)
    min_cum_formatted = format_number(min_cum)
    median_cum_formatted = format_number(median_cum)

    title_text = (
        f"OX Cumulative PNL Analysis: Max: {max_cum_formatted}, "
        f"Min: {min_cum_formatted}, Median: {median_cum_formatted}. "
        f"<br>Positive {positive_days} days ({positive_percent:.1f}% of the time) and Negative {negative_days} days "
        f"({negative_percent:.1f}% of the time) since inception."
    )

    fig_area.update_layout(
        title=title_text,
        xaxis=dict(
            title='Date',
            tickformat='%Y-%m-%d',
            tickangle=45
        ),
        yaxis=dict(
            title='Cumulative PNL (OX)'
        ),
        template='plotly_white',
        height=900,
        shapes=shapes,
        legend=dict(
            x=0.5,
            y=1,
            xanchor='center',
            yanchor='top',
            bgcolor='rgba(255,255,255,0.5)'
        )
    )

    # Add dummy traces to explain the area colors in the legend
    fig_area.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode='lines',
        line=dict(color='rgba(0,255,0,0.5)', width=10),
        name='Positive Cumulative $OX PNL Area'
    ))
    fig_area.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode='lines',
        line=dict(color='rgba(255,0,0,0.5)', width=10),
        name='Negative Cumulative $OX PNL Area'
    ))

    cumulative_div = pio.to_html(fig_area, include_plotlyjs=False, full_html=False)

    png_output_path_area = os.path.join(output_dir, 'cumulative_pnl_area_chart.png')
    try:
        fig_area.write_image(png_output_path_area, width=1800, height=900)
        print(f"Static cumulative PNL area chart saved to {png_output_path_area}")
    except Exception as e:
        print(f"Error saving PNG cumulative area chart: {e}")
        print("To save Plotly figures as PNG, you need to install the 'kaleido' package.")
        print("You can install it using: pip install kaleido")

    return cumulative_div, last_cum_formatted


def visualize_pnl(df: pd.DataFrame, output_dir: str):
    """
    Create multiple charts of PNL using Plotly and generate an HTML report.

    Parameters:
    - df: DataFrame with analysis.
    - output_dir: Directory to save the visualization and report.
    """
    # Check if 'PNL (OX)' has data
    if df.empty:
        print("Error: The DataFrame is empty. No data to plot.")
        return

    # Print data to be plotted for debugging
    print("\nData to be plotted:")
    print(df[['Date', 'PNL (OX)']].to_string(index=False))

    # Define colors based on PNL
    try:
        colors = ['green' if pnl >= 0 else 'red' for pnl in df['PNL (OX)']]
    except Exception as e:
        print(f"Error defining colors: {e}")
        return

    # Create the combined bar and line chart
    fig_pnl = go.Figure()

    # Add Daily PNL as Bar
    fig_pnl.add_trace(go.Bar(
        x=df['Date'],
        y=df['PNL (OX)'],
        marker=dict(color=colors),
        name='Daily PNL',
        hovertemplate='Date: %{x}<br>PNL: $OX %{y:,.0f}<extra></extra>'
    ))

    # Add Cumulative PNL (OX) as Line on secondary y-axis
    fig_pnl.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Cumulative PNL (OX)'],
        mode='lines+markers',
        name='Cumulative PNL (OX)',
        yaxis='y2',
        line=dict(color='blue', width=2),
        hovertemplate='Date: %{x}<br>Cumulative PNL (OX): $OX %{y:,.0f}<extra></extra>'
    ))

    # Add a dotted horizontal zero line on the second y-axis for cumulative PNL
    fig_pnl.add_trace(go.Scatter(
        x=[df['Date'].iloc[0], df['Date'].iloc[-1]],
        y=[0, 0],
        mode='lines',
        name='Zero cumulative PNL',
        line=dict(color='black', dash='dot'),
        yaxis='y2',
        hoverinfo='skip'
    ))

    # Update layout for dual y-axis and set chart height with a more descriptive title
    fig_pnl.update_layout(
        title='Daily and Cumulative $OX PNL Chart: Left axis = Daily $OX PNL (bar chart), Right axis = Cumulative $OX PNL (line chart)',
        xaxis=dict(
            title='Date',
            tickformat='%Y-%m-%d',
            tickangle=45
        ),
        yaxis=dict(
            title='Daily $OX PNL',
            titlefont=dict(color='green'),
            tickfont=dict(color='green')
        ),
        yaxis2=dict(
            title='Cumulative $OX PNL',
            titlefont=dict(color='blue'),
            tickfont=dict(color='blue'),
            overlaying='y',
            side='right'
        ),
        legend=dict(x=0.01, y=0.99),
        template='plotly_white',
        bargap=0.2,
        height=900  # Increased height for better visibility
    )

    # Create Histogram of Daily PNL
    fig_hist = go.Figure(data=[
        go.Histogram(
            x=df['PNL (OX)'],
            nbinsx=20,
            marker_color='orange',
            hovertemplate='Count: %{y}<br>PNL Range: $OX %{x:,.0f}<br>to $OX %{x:,.0f}<extra></extra>'
        )
    ])

    fig_hist.update_layout(
        title='Distribution of Daily PNL (OX)',
        xaxis_title='PNL (OX)',
        yaxis_title='Count',
        template='plotly_white',
        bargap=0.2,
        height=900  # Increased height for better visibility
    )

    # Convert plots to HTML divs without the Plotly JS (to include once)
    pnl_div = pio.to_html(fig_pnl, include_plotlyjs=False, full_html=False)
    hist_div = pio.to_html(fig_hist, include_plotlyjs=False, full_html=False)

    # Generate the cumulative PNL area chart div using the new function
    cumulative_div, last_cum_formatted = visualize_cumulative_area(df, output_dir)

    # Compute earliest date and days since inception for header display
    earliest_date = df['Date'].min()
    earliest_date_str = earliest_date.strftime('%Y-%m-%d')
    days_ago = (datetime.today() - earliest_date).days

    # Prepare the table
    df_table = df.copy()
    # Sort descending by Date
    df_table = df_table.sort_values(by='Date', ascending=False)

    # Format numbers for the table
    df_table['PNL (OX)'] = df_table['PNL (OX)'].apply(format_number)
    df_table['Cumulative PNL (OX)'] = df_table['Cumulative PNL (OX)'].apply(format_number)
    # Assuming 'Fees' column exists; format it
    if 'Fees' in df_table.columns:
        df_table['Fees'] = df_table['Fees'].apply(lambda x: f"$OX {int(x):,}")

    # Convert the DataFrame to HTML table
    table_html = df_table.to_html(index=False, classes='table table-striped', escape=False)

    # Add color styling for positive and negative PNL
    # We'll use JavaScript to apply the styles after the table is rendered
    table_js = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const table = document.getElementById('pnl-table');
        if (table) {
            const rows = table.getElementsByTagName('tr');
            // Iterate over table rows (skip header)
            for (let i = 1; i < rows.length; i++) {
                const cells = rows[i].getElementsByTagName('td');
                if (cells.length >= 4) {
                    // Daily PNL is in the second column (index 1)
                    let pnlText = cells[1].innerText;
                    let pnlValue = parseFloat(pnlText.replace('$OX ','').replace('m','e6').replace('k','e3'));
                    if (pnlValue >= 0) {
                        cells[1].style.color = 'green';
                    } else {
                        cells[1].style.color = 'red';
                    }
                    // Cumulative PNL (OX) is in the third column (index 2)
                    let cum_pnlText = cells[2].innerText;
                    let cum_pnlValue = parseFloat(cum_pnlText.replace('$OX ','').replace('m','e6').replace('k','e3'));
                    if (cum_pnlValue >= 0) {
                        cells[2].style.color = 'green';
                    } else {
                        cells[2].style.color = 'red';
                    }
                }
            }
        }
    });
    </script>
    """

    # Modify table_html to include an ID for JavaScript targeting
    table_html = table_html.replace('<table border="1" class="dataframe table table-striped">', '<table id="pnl-table" class="table table-striped">')

    # HTML Template with improved layout and 80% width
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OXFUN Vault Performance Analysis Report - {datetime.today().strftime('%Y-%m-%d')}</title>
        <meta charset="utf-8" />
        <!-- Plotly.js -->
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <!-- DataTables CSS -->
        <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.css">
        <!-- jQuery -->
        <script type="text/javascript" charset="utf8" src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <!-- DataTables JS -->
        <script type="text/javascript" charset="utf8" src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.js"></script>
        <!-- Bootstrap CSS for better styling (optional) -->
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                display: flex;
                justify-content: center;
                position: relative;
            }}
            .content {{
                width: 80%;
            }}
            .plot-container {{
                margin-top: 50px;
                margin-bottom: 50px;
            }}
            table.dataframe {{
                width: 100%;
            }}
            h1, h2, h3 {{
                text-align: center;
            }}
            .github-link {{
                position: absolute;
                top: 10px;
                right: 10px;
                padding-top: 10px;
                padding-right: 10px;
            }}
            .github-link img {{
                width: 32px;
                height: 32px;
            }}
        </style>
    </head>
    <body>
        <div class="github-link">
            <a href="https://github.com/vmeylan/oxfun-lp-vault-analysis" target="_blank" rel="noopener noreferrer">
                <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub">
            </a>
        </div>
        <div class="content">
            <h1>OXFUN LP Vault Performance Analysis Report</h1>
            <h3>"the main counterparty to most traders on the exchange", <a href="https://ox.fun/en/vaults/profile/110428" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">vault 110428</a></h3>
            <h3>Date: {datetime.today().strftime('%Y-%m-%d')}</h3>

            <div class="plot-container">
                <h3>$OX {last_cum_formatted.replace('$OX ', '')} cumulative PNL for the OXFUN Liquidity Provider Strategy vault since inception {earliest_date_str} ({days_ago} days ago)</h3>
                {cumulative_div}
            </div>

            <div class="plot-container">
                <h3>Daily and Cumulative $OX PNL Chart</h3>
                {pnl_div}
            </div>

            <div class="plot-container">
                <h3>Distribution of Daily PNL (OX)</h3>
                {hist_div}
            </div>

            <div class="table-container">
                <h3>PNL Details</h3>
                {table_html}
            </div>
        </div>

        <script>
            // Initialize DataTables
            $(document).ready(function() {{
                $('#pnl-table').DataTable({{
                    "paging": true,
                    "pageLength": 10,
                    "lengthChange": false,
                    "ordering": true,
                    "order": [[0, "desc"]],
                    "info": true,
                    "searching": false
                }});
            }});
        </script>

        {table_js}
    </body>
    </html>
    """

    # Save the HTML report
    html_report_path = os.path.join(output_dir, 'pnl_analysis_report.html')
    try:
        with open(html_report_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        print(f"\nHTML PNL analysis report saved to {html_report_path}")
    except Exception as e:
        print(f"Error saving HTML report: {e}")

    # Save plots as static PNG images
    png_output_path_pnl = os.path.join(output_dir, 'daily_cumulative_pnl_chart.png')
    try:
        fig_pnl.write_image(png_output_path_pnl, width=1800, height=900)
        print(f"Static Daily and Cumulative PNL (OX) chart saved to {png_output_path_pnl}")
    except Exception as e:
        print(f"Error saving PNG plot: {e}")
        print("To save Plotly figures as PNG, you need to install the 'kaleido' package.")
        print("You can install it using: pip install kaleido")

    png_output_path_hist = os.path.join(output_dir, 'pnl_histogram.png')
    try:
        fig_hist.write_image(png_output_path_hist, width=1800, height=900)
        print(f"Static PNL histogram saved to {png_output_path_hist}")
    except Exception as e:
        print(f"Error saving PNG plot: {e}")
        print("To save Plotly figures as PNG, you need to install the 'kaleido' package.")
        print("You can install it using: pip install kaleido")

    # Optionally, show the plots in the default web browser
    # fig_pnl.show()
    # fig_hist.show()


def main():
    # Get today's date in yyyy-mm-dd format
    today_str = datetime.today().strftime('%Y-%m-%d')
    print(f"Today's date: {today_str}")

    # Define the root directory (repo root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    data_dir = os.path.join(repo_root, 'data', today_str)

    # Check if the data directory exists
    if not os.path.exists(data_dir):
        print(f"Error: Data directory '{data_dir}' does not exist. Please run the scraper first.")
        sys.exit(1)

    # Path to the scraped CSV file
    csv_path = os.path.join(data_dir, 'oxfun_data.csv')

    # Load and clean the data
    df = load_and_clean_data(csv_path)

    # Analyze the data
    df_grouped = analyze_data(df)

    # Visualize the PNL and generate the HTML report
    visualize_pnl(df_grouped, data_dir)

    # Optionally, save the cleaned and analyzed data
    cleaned_csv_path = os.path.join(data_dir, 'oxfun_data_cleaned.csv')
    try:
        df_grouped.to_csv(cleaned_csv_path, index=False)
        print(f"\nCleaned data saved to {cleaned_csv_path}")
    except Exception as e:
        print(f"Error saving cleaned data to CSV: {e}")

if __name__ == "__main__":
    main()
