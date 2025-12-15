#!/usr/bin/env python3
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import psycopg2

# Database configuration
DB_CONFIG = {
    "dbname": "malla_analyze",
    "user": "malla",
    "password": "REPLACEME",
    "host": "psql.patinhas.da4.org",
}

# Email configuration
SMTP_HOST = "smtp.gmail.com"  # or your SMTP server
SMTP_PORT = 587
SMTP_USER = "REPLACE@ME"
SMTP_PASSWORD = "REPLACEME"
TO_EMAIL = "REPLACE@ME"
FROM_EMAIL = "REPLACE@ME"

QUERY = """
WITH gateway_nodes AS (
    SELECT DISTINCT ni.node_id
    FROM packet_history ph
    INNER JOIN node_info ni ON ni.hex_id = ph.gateway_id
    WHERE ph.gateway_id IS NOT NULL AND ni.node_id IS NOT NULL
),
gateway_performance AS (
    SELECT
        ph.gateway_id,
        gw.short_name AS gateway_short_name,
        gw.long_name AS gateway_long_name,
        gw.hw_model,
        COUNT(*) AS direct_packet_count,
        AVG(ph.rssi) AS avg_rssi,
        AVG(ph.snr) AS avg_snr,
        STDDEV_POP(ph.rssi) AS rssi_consistency,
        COUNT(DISTINCT ph.from_node_id) AS unique_nodes_heard
    FROM packet_history ph
    LEFT JOIN node_info gw ON gw.hex_id = ph.gateway_id
    WHERE (ph.relay_node IS NULL OR ph.relay_node = 0)
        AND ph.gateway_id IS NOT NULL
        AND ph.rssi IS NOT NULL
        AND ph.timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '24 hours')
        AND ph.from_node_id NOT IN (SELECT node_id FROM gateway_nodes)
    GROUP BY ph.gateway_id, gw.short_name, gw.long_name, gw.hw_model
    HAVING COUNT(*) >= 50
)
SELECT
    gateway_id,
    gateway_short_name,
    gateway_long_name,
    hw_model,
    direct_packet_count,
    ROUND(avg_rssi::numeric, 2) AS avg_rssi,
    ROUND(avg_snr::numeric, 2) AS avg_snr,
    ROUND(rssi_consistency::numeric, 2) AS rssi_stddev,
    unique_nodes_heard,
    RANK() OVER (ORDER BY avg_rssi DESC) AS rssi_rank,
    RANK() OVER (ORDER BY avg_snr DESC) AS snr_rank,
    RANK() OVER (ORDER BY unique_nodes_heard DESC) AS coverage_rank,
    RANK() OVER (ORDER BY direct_packet_count DESC) AS volume_rank,
    -- FIXED: Use DESC in all ORDER BY clauses
    ROUND(
        (((1 - PERCENT_RANK() OVER (ORDER BY avg_rssi DESC)) * 0.25 +
          (1 - PERCENT_RANK() OVER (ORDER BY avg_snr DESC)) * 0.15 +
          (1 - PERCENT_RANK() OVER (ORDER BY unique_nodes_heard DESC)) * 0.30 +
          (1 - PERCENT_RANK() OVER (ORDER BY direct_packet_count DESC)) * 0.30) * 100)::numeric
    , 2) AS performance_score
FROM gateway_performance
ORDER BY performance_score DESC;
"""


def generate_html_table(rows, columns):
    """Generate an HTML table from query results."""
    html = (
        """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; }
            th { background-color: #4CAF50; color: white; padding: 12px; text-align: left; }
            td { border: 1px solid #ddd; padding: 8px; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            tr:hover { background-color: #ddd; }
            .header { background-color: #333; color: white; padding: 20px; }
            .footer { margin-top: 20px; color: #666; font-size: 12px; }
            .rank-1 { background-color: #ffd700 !important; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Gateway Performance Report - """
        + datetime.now().strftime("%Y-%m-%d %H:%M")
        + """</h2>
        </div>
        <table>
            <thead>
                <tr>
    """
    )

    # Add headers
    for col in columns:
        html += f"<th>{col.replace('_', ' ').title()}</th>"
    html += "</tr></thead><tbody>"

    # Add rows
    for i, row in enumerate(rows):
        row_class = "rank-1" if i == 0 else ""
        html += f"<tr class='{row_class}'>"
        for value in row:
            html += f"<td>{value if value is not None else 'N/A'}</td>"
        html += "</tr>"

    html += """
            </tbody>
        </table>
        <div class="footer">
            <p>Report generated from last 24 hours of direct mesh packet receptions (excluding inter-gateway traffic).</p>
            <p>Performance Score: Weighted combination of RSSI (25%), SNR (15%), Coverage (30%), and Volume (30%).</p>
        </div>
    </body>
    </html>
    """
    return html


def send_email(subject, html_body):
    """Send email with HTML content."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    html_part = MIMEText(html_body, "html")
    msg.attach(html_part)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"Email sent successfully to {TO_EMAIL}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise


def main():
    """Main execution function."""
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Execute query
        cursor.execute(QUERY)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        if not rows:
            print("No data returned from query")
            return

        # Generate HTML table
        html_body = generate_html_table(rows, columns)

        # Send email
        subject = f"Meshtastic Gateway Performance Report - {datetime.now().strftime('%Y-%m-%d')}"
        send_email(subject, html_body)

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
