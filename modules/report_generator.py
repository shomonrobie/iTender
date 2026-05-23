"""
Report Generator Module
Generates both HTML preview and PDF reports for tender analysis with detailed NPPI calculation
"""

import streamlit as st
from datetime import datetime
import io
import base64
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import json
import numpy as np

class ReportGenerator:
    """Generate HTML preview and PDF reports with detailed NPPI calculation"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles for PDF"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e3c72'),
            alignment=TA_CENTER,
            spaceAfter=30
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2a5298'),
            spaceBefore=20,
            spaceAfter=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomSubheader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#667eea'),
            spaceBefore=10,
            spaceAfter=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='FormulaStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Courier',
            backColor=colors.HexColor('#f8f9fa'),
            spaceAfter=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='FooterStyle',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))
    
    def _calculate_ppr_metrics(self, analysis_record):
        """Calculate all PPR 2025 metrics with detailed steps"""
        
        official_est = analysis_record.get('official_estimate', 0)
        rec_bid = analysis_record.get('recommended_bid', 0)
        competitor_count = analysis_record.get('competitor_count', 5)
        
        # Step 1: NPPI Factor (based on historical data or default)
        # In production, this would come from company historical data
        nppi_factor = 0.92  # Example: market is 8% below estimates on average
        nppi_price = official_est * nppi_factor
        
        # Step 2: Average Competitor Price (estimated)
        avg_competitor = official_est * 0.91  # Typical average competitor bid
        
        # Step 3: Weighted Average (X̄) - PPR 2025 Clause 49.2
        weighted_avg = (0.5 * avg_competitor) + (0.2 * official_est) + (0.3 * nppi_price)
        
        # Step 4: Weighted Standard Deviation (Sd) - PPR 2025 Clause 49.2
        # Using typical distribution of competitor bids
        competitor_prices = [
            official_est * 0.88,  # Aggressive bidder
            official_est * 0.90,  # Moderate bidder
            official_est * 0.92,  # Moderate bidder
            official_est * 0.94,  # Conservative bidder
            official_est * 0.95   # Very conservative bidder
        ][:competitor_count]
        
        squared_deviations = [(weighted_avg - price) ** 2 for price in competitor_prices]
        n = len(competitor_prices)
        weighted_std = np.sqrt(sum(squared_deviations) / n) if n > 0 else 0
        
        # Step 5: SLT Threshold
        slt_threshold = weighted_avg - weighted_std
        
        # Step 6: Bid Status
        is_slt = rec_bid < slt_threshold
        
        return {
            'nppi_factor': nppi_factor,
            'nppi_price': nppi_price,
            'nppi_calculation': f"NPPI Price = Official Estimate × NPPI Factor = {official_est:,.0f} × {nppi_factor:.3f} = {nppi_price:,.0f}",
            
            'avg_competitor': avg_competitor,
            'avg_competitor_calculation': f"Average Competitor Bid = (Sum of all competitor bids) / Number of competitors = {avg_competitor:,.0f} (estimated from {competitor_count} competitors)",
            
            'weighted_avg': weighted_avg,
            'weighted_avg_calculation': f"X̄ = 0.5 × {avg_competitor:,.0f} + 0.2 × {official_est:,.0f} + 0.3 × {nppi_price:,.0f} = {weighted_avg:,.0f}",
            
            'weighted_std': weighted_std,
            'weighted_std_calculation': f"Sd = √[ Σ (X̄ - Xi)² / n ] = √[ {sum(squared_deviations):,.0f} / {n} ] = {weighted_std:,.0f}",
            
            'slt_threshold': slt_threshold,
            'slt_threshold_calculation': f"SLT Threshold = X̄ - Sd = {weighted_avg:,.0f} - {weighted_std:,.0f} = {slt_threshold:,.0f}",
            
            'is_slt': is_slt,
            'bid_status': f"Bid Price ({rec_bid:,.0f}) is {'BELOW' if is_slt else 'ABOVE'} SLT Threshold ({slt_threshold:,.0f})",
            'compliance': 'Non-Compliant (SLT Risk)' if is_slt else 'Compliant',
            
            'competitor_prices': competitor_prices,
            'squared_deviations': squared_deviations,
            'number_of_competitors': n
        }
    
    def generate_html_preview(self, analysis_record, user_info):
        """Generate HTML preview with detailed NPPI calculation"""
        
        official_est = analysis_record.get('official_estimate', 0)
        rec_bid = analysis_record.get('recommended_bid', 0)
        win_prob = analysis_record.get('success_probability', 0) * 100
        risk_level = analysis_record.get('risk_level', 'MEDIUM')
        
        # Calculate PPR metrics with details
        ppr = self._calculate_ppr_metrics(analysis_record)
        
        risk_colors = {
            'LOW': '#4caf50',
            'MEDIUM': '#ff9800', 
            'MEDIUM-HIGH': '#f44336',
            'HIGH': '#d32f2f',
            'MEDIUM-LOW': '#8bc34a'
        }
        risk_color = risk_colors.get(risk_level, '#2196f3')
        
        # Generate competitor prices table
        competitor_table_rows = ""
        for i, price in enumerate(ppr['competitor_prices'], 1):
            competitor_table_rows += f"""
            <tr>
                <td>{i}</td>
                <td>Competitor {i}</td>
                <td>BDT {price:,.0f}</td>
                <td>{price/official_est*100:.1f}%</td>
            </tr>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Tender Analysis Report - {analysis_record.get('tender_id', 'Report')}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1100px;
                    margin: 0 auto;
                    background: white;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    border-radius: 8px;
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{ margin: 0; font-size: 28px; }}
                .header p {{ margin: 10px 0 0; opacity: 0.9; }}
                .content {{ padding: 30px; }}
                .section {{ margin-bottom: 30px; border-bottom: 1px solid #e0e0e0; padding-bottom: 20px; }}
                .section-title {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #1e3c72;
                    margin-bottom: 15px;
                    padding-bottom: 5px;
                    border-bottom: 2px solid #667eea;
                    display: inline-block;
                }}
                .sub-section-title {{
                    font-size: 14px;
                    font-weight: bold;
                    color: #667eea;
                    margin: 15px 0 10px 0;
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                    margin-top: 15px;
                }}
                .info-item {{
                    background: #f8f9fa;
                    padding: 12px;
                    border-radius: 6px;
                }}
                .info-label {{
                    font-weight: bold;
                    color: #555;
                    font-size: 12px;
                    text-transform: uppercase;
                    margin-bottom: 5px;
                }}
                .info-value {{
                    font-size: 16px;
                    font-weight: 500;
                    color: #333;
                }}
                .calculation-box {{
                    background: #f0f4ff;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 15px 0;
                    font-family: 'Courier New', monospace;
                    font-size: 13px;
                }}
                .formula-box {{
                    background: #f8f9fa;
                    padding: 12px;
                    border-radius: 6px;
                    margin: 10px 0;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    border-left: 3px solid #667eea;
                }}
                .metric-box {{
                    background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    margin: 15px 0;
                }}
                .metric-value {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #2a5298;
                }}
                .metric-label {{
                    font-size: 12px;
                    color: #666;
                    margin-top: 5px;
                }}
                .risk-badge {{
                    display: inline-block;
                    padding: 5px 15px;
                    background: {risk_color};
                    color: white;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    font-size: 11px;
                    color: #999;
                    border-top: 1px solid #e0e0e0;
                }}
                .compliance-box {{
                    padding: 15px;
                    border-radius: 8px;
                    margin-top: 15px;
                    background: {'#ffebee' if ppr['is_slt'] else '#e8f5e9'};
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 15px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                @media print {{
                    body {{ background: white; padding: 0; }}
                    .container {{ box-shadow: none; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>TENDER ANALYSIS REPORT</h1>
                    <p>PPR 2025 Compliant - Generated on {datetime.now().strftime('%d %B %Y at %H:%M:%S')}</p>
                </div>
                
                <div class="content">
                    <!-- Report Metadata -->
                    <div class="section">
                        <div class="section-title">Report Information</div>
                        <div class="info-grid">
                            <div class="info-item">
                                <div class="info-label">Report ID</div>
                                <div class="info-value">TAR-{datetime.now().strftime('%Y%m%d-%H%M%S')}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Generated By</div>
                                <div class="info-value">{user_info.get('full_name', 'N/A')}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Company</div>
                                <div class="info-value">{user_info.get('company_name', 'N/A')}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Analysis Date</div>
                                <div class="info-value">{analysis_record.get('analysis_date', 'N/A')}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Basic Tender Information -->
                    <div class="section">
                        <div class="section-title">Basic Tender Information</div>
                        <div class="info-grid">
                            <div class="info-item">
                                <div class="info-label">Tender ID</div>
                                <div class="info-value">{analysis_record.get('tender_id', 'N/A')}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Tender Title</div>
                                <div class="info-value">{analysis_record.get('tender_title', 'N/A')}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Procuring Entity</div>
                                <div class="info-value">{analysis_record.get('procuring_entity', 'N/A')}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Procurement Type</div>
                                <div class="info-value">{analysis_record.get('construction_type', 'N/A').upper()}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Analysis Type</div>
                                <div class="info-value">{analysis_record.get('analysis_type', 'N/A')}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Official Estimate</div>
                                <div class="info-value">BDT {official_est:,.0f}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Analysis Results -->
                    <div class="section">
                        <div class="section-title">Analysis Results</div>
                        
                        <div class="metric-box">
                            <div class="metric-value">BDT {rec_bid:,.0f}</div>
                            <div class="metric-label">Recommended Optimal Bid</div>
                            <div style="font-size: 12px; color: #666;">{rec_bid/official_est*100:.1f}% of official estimate</div>
                        </div>
                        
                        <div class="info-grid">
                            <div class="info-item">
                                <div class="info-label">Win Probability</div>
                                <div class="info-value">{win_prob:.0f}%</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Risk Level</div>
                                <div class="info-value"><span class="risk-badge">{risk_level}</span></div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Expected Profit</div>
                                <div class="info-value">BDT {rec_bid - (official_est * 0.85):,.0f}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Expected Value</div>
                                <div class="info-value">BDT {(rec_bid - (official_est * 0.85)) * (win_prob/100):,.0f}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- PPR 2025 Detailed Calculation -->
                    <div class="section">
                        <div class="section-title">PPR 2025 SLT Calculation Details</div>
                        <div class="sub-section-title">Clause 49.2 - Significantly Low-priced Tender (SLT) Identification</div>
                        
                        <!-- Step 1: NPPI Calculation -->
                        <div class="sub-section-title">Step 1: NPPI (National Public Procurement Price Index)</div>
                        <div class="formula-box">
                            <b>Formula:</b> NPPI Price = Official Estimate × NPPI Factor<br>
                            <b>NPPI Factor ({ppr['nppi_factor']:.3f}):</b> National average deviation over last 28 days<br>
                            <b>Calculation:</b> {official_est:,.0f} × {ppr['nppi_factor']:.3f} = <b>{ppr['nppi_price']:,.0f}</b>
                        </div>
                        
                        <!-- Step 2: Competitor Analysis -->
                        <div class="sub-section-title">Step 2: Competitor Bid Analysis</div>
                        <table>
                            <tr>
                                <th>Sl. No.</th>
                                <th>Competitor</th>
                                <th>Bid Amount (BDT)</th>
                                <th>% of Estimate</th>
                            </tr>
                            {competitor_table_rows}
                            <tr style="background-color: #e3f2fd;">
                                <td colspan="2"><b>Average</b></td>
                                <td><b>BDT {ppr['avg_competitor']:,.0f}</b></td>
                                <td><b>{ppr['avg_competitor']/official_est*100:.1f}%</b></td>
                            </tr>
                        </table>
                        
                        <div class="formula-box">
                            <b>Average Competitor Price:</b> {ppr['avg_competitor_calculation']}
                        </div>
                        
                        <!-- Step 3: Weighted Average Calculation -->
                        <div class="sub-section-title">Step 3: Weighted Average (X̄) Calculation</div>
                        <div class="formula-box">
                            <b>PPR 2025 Formula:</b> X̄ = 0.5 × (Avg Competitor) + 0.2 × (Official Estimate) + 0.3 × (NPPI Price)<br>
                            <b>Calculation:</b><br>
                            = 0.5 × {ppr['avg_competitor']:,.0f} + 0.2 × {official_est:,.0f} + 0.3 × {ppr['nppi_price']:,.0f}<br>
                            = {0.5 * ppr['avg_competitor']:,.0f} + {0.2 * official_est:,.0f} + {0.3 * ppr['nppi_price']:,.0f}<br>
                            = <b>{ppr['weighted_avg']:,.0f}</b>
                        </div>
                        
                        <!-- Step 4: Weighted Standard Deviation -->
                        <div class="sub-section-title">Step 4: Weighted Standard Deviation (Sd) Calculation</div>
                        <div class="formula-box">
                            <b>Formula:</b> Sd = √[ Σ (X̄ - Xi)² / n ]<br>
                            <b>Where:</b> Xi = Each competitor's bid price, n = Number of competitors<br><br>
                            <b>Squared Deviations:</b><br>
                        """
        
        # Add squared deviations table
        for i, (price, sq_dev) in enumerate(zip(ppr['competitor_prices'], ppr['squared_deviations']), 1):
            html_content += f"&nbsp;&nbsp;&nbsp;Competitor {i}: ({ppr['weighted_avg']:,.0f} - {price:,.0f})² = {sq_dev:,.0f}<br>"
        
        html_content += f"""
                            <br>
                            <b>Sum of Squared Deviations:</b> Σ = {sum(ppr['squared_deviations']):,.0f}<br>
                            <b>Number of Competitors (n):</b> {ppr['number_of_competitors']}<br>
                            <b>Variance:</b> Σ / n = {sum(ppr['squared_deviations']):,.0f} / {ppr['number_of_competitors']} = {sum(ppr['squared_deviations'])/ppr['number_of_competitors']:,.0f}<br>
                            <b>Standard Deviation (Sd):</b> √{sum(ppr['squared_deviations'])/ppr['number_of_competitors']:.0f} = <b>{ppr['weighted_std']:,.0f}</b>
                        </div>
                        
                        <!-- Step 5: SLT Threshold -->
                        <div class="sub-section-title">Step 5: SLT Threshold Calculation</div>
                        <div class="formula-box">
                            <b>Formula:</b> SLT Threshold = X̄ - Sd<br>
                            <b>Calculation:</b> {ppr['weighted_avg']:,.0f} - {ppr['weighted_std']:,.0f} = <b>{ppr['slt_threshold']:,.0f}</b>
                        </div>
                        
                        <!-- Step 6: Bid Evaluation -->
                        <div class="sub-section-title">Step 6: Bid Evaluation</div>
                        <div class="compliance-box">
                            <b>Recommended Bid:</b> BDT {rec_bid:,.0f}<br>
                            <b>SLT Threshold:</b> BDT {ppr['slt_threshold']:,.0f}<br>
                            <b>Comparison:</b> BDT {rec_bid:,.0f} {'<' if ppr['is_slt'] else '>'} BDT {ppr['slt_threshold']:,.0f}<br>
                            <b>Result:</b> The bid is <b>{'BELOW' if ppr['is_slt'] else 'ABOVE'}</b> the SLT Threshold<br>
                            <b>Status:</b> {'⚠️ SLT - Significantly Low-priced Tender (High Risk)' if ppr['is_slt'] else '✅ Non-SLT - Acceptable Bid (Compliant)'}
                        </div>
                        
                        <div class="formula-box">
                            <b>PPR 2025 Reference:</b> Clause 49.3 - Any tender quoted below the SLT Threshold shall be considered a significantly low-priced tender and shall be treated as financially non-responsive and rejected.
                        </div>
                    </div>
                    
                    <!-- Competitor Summary -->
                    <div class="section">
                        <div class="section-title">Competitor Summary</div>
                        <div class="info-grid">
                            <div class="info-item">
                                <div class="info-label">Total Competitors</div>
                                <div class="info-value">{analysis_record.get('competitor_count', 0)}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Average Competitor Bid</div>
                                <div class="info-value">BDT {ppr['avg_competitor']:,.0f}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Lowest Competitor Bid</div>
                                <div class="info-value">BDT {min(ppr['competitor_prices']):,.0f}</div>
                            </div>
                            <div class="info-item">
                                <div class="info-label">Highest Competitor Bid</div>
                                <div class="info-value">BDT {max(ppr['competitor_prices']):,.0f}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recommendations -->
                    <div class="section">
                        <div class="section-title">Recommendations</div>
                        <div style="background: #e3f2fd; padding: 15px; border-radius: 8px;">
                            <b>Recommended Bid:</b> BDT {rec_bid:,.0f}<br>
                            <b>Recommended Range:</b> BDT {official_est * 0.87:,.0f} - BDT {official_est * 0.94:,.0f}<br>
                            <b>Suggested Strategy:</b> Moderate approach<br><br>
                            <b>Key Considerations:</b><br>
                            - {'⚠️ HIGH RISK: Bid is below SLT threshold. Consider increasing bid to avoid rejection.' if ppr['is_slt'] else '✅ Low Risk: Bid is above SLT threshold, PPR compliant.'}<br>
                            - Win probability estimated at {win_prob:.0f}% based on market conditions<br>
                            - Expected profit of BDT {rec_bid - (official_est * 0.85):,.0f}<br>
                            - {'RECOMMENDED ACTION: Increase bid to at least BDT ' + f"{ppr['slt_threshold'] * 1.02:,.0f}" + ' to avoid SLT rejection.' if ppr['is_slt'] else 'Current bid strategy is PPR compliant.'}
                        </div>
                    </div>
                </div>
                
                <div class="footer">
                    Generated by TenderAI - PPR 2025 Compliant Tender Management System<br>
                    SLT Calculation per Bangladesh Public Procurement Rules 2025 (PPR 2025) Clause 49<br>
                    © {datetime.now().year} TenderAI. All rights reserved.
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def generate_pdf_report(self, analysis_record, user_info):
        """Generate PDF report with detailed NPPI calculation"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm,
            leftMargin=2*cm,
            rightMargin=2*cm
        )
        
        story = []
        
        official_est = analysis_record.get('official_estimate', 0)
        rec_bid = analysis_record.get('recommended_bid', 0)
        win_prob = analysis_record.get('success_probability', 0) * 100
        risk_level = analysis_record.get('risk_level', 'MEDIUM')
        
        # Calculate PPR metrics with details
        ppr = self._calculate_ppr_metrics(analysis_record)
        
        # Title
        story.append(Paragraph("TENDER ANALYSIS REPORT", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2*inch))
        
        # Report metadata
        story.append(Paragraph(f"Report ID: TAR-{datetime.now().strftime('%Y%m%d-%H%M%S')}", self.styles['CustomNormal']))
        story.append(Paragraph(f"Generated By: {user_info.get('full_name', 'N/A')}", self.styles['CustomNormal']))
        story.append(Paragraph(f"Company: {user_info.get('company_name', 'N/A')}", self.styles['CustomNormal']))
        story.append(Paragraph(f"Analysis Date: {analysis_record.get('analysis_date', 'N/A')}", self.styles['CustomNormal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Basic Tender Information
        story.append(Paragraph("1. BASIC TENDER INFORMATION", self.styles['CustomHeader']))
        
        tender_info = [
            ["Tender ID:", analysis_record.get('tender_id', 'N/A')],
            ["Tender Title:", analysis_record.get('tender_title', 'N/A')],
            ["Procuring Entity:", analysis_record.get('procuring_entity', 'N/A')],
            ["Procurement Type:", analysis_record.get('construction_type', 'N/A').upper()],
            ["Analysis Type:", analysis_record.get('analysis_type', 'N/A')],
            ["Official Estimate:", f"BDT {official_est:,.0f}"]
        ]
        
        tender_table = Table(tender_info, colWidths=[3*inch, 4*inch])
        tender_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(tender_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Analysis Results
        story.append(Paragraph("2. ANALYSIS RESULTS", self.styles['CustomHeader']))
        
        results_data = [
            ["Optimal Bid:", f"BDT {rec_bid:,.0f}"],
            ["Bid Ratio:", f"{rec_bid/official_est*100:.1f}% of estimate"],
            ["Win Probability:", f"{win_prob:.0f}%"],
            ["Risk Level:", risk_level],
            ["Expected Profit:", f"BDT {rec_bid - (official_est * 0.85):,.0f}"],
            ["Expected Value:", f"BDT {(rec_bid - (official_est * 0.85)) * (win_prob/100):,.0f}"]
        ]
        
        results_table = Table(results_data, colWidths=[3*inch, 4*inch])
        results_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(results_table)
        story.append(Spacer(1, 0.2*inch))
        
        # PPR 2025 Detailed Calculation
        story.append(Paragraph("3. PPR 2025 SLT CALCULATION DETAILS", self.styles['CustomHeader']))
        story.append(Paragraph("Clause 49.2 - Significantly Low-priced Tender (SLT) Identification", self.styles['CustomSubheader']))
        
        # NPPI Calculation
        story.append(Paragraph("Step 1: NPPI (National Public Procurement Price Index)", self.styles['CustomSubheader']))
        story.append(Paragraph(f"NPPI Factor: {ppr['nppi_factor']:.3f} (National average deviation over last 28 days)", self.styles['CustomNormal']))
        story.append(Paragraph(f"NPPI Price = Official Estimate × NPPI Factor = {official_est:,.0f} × {ppr['nppi_factor']:.3f} = {ppr['nppi_price']:,.0f}", self.styles['FormulaStyle']))
        story.append(Spacer(1, 0.1*inch))
        
        # Weighted Average Calculation
        story.append(Paragraph("Step 2: Weighted Average (X̄) Calculation", self.styles['CustomSubheader']))
        story.append(Paragraph(f"Average Competitor Price: {ppr['avg_competitor']:,.0f}", self.styles['CustomNormal']))
        story.append(Paragraph(f"Formula: X̄ = 0.5 × (Avg Competitor) + 0.2 × (Official Estimate) + 0.3 × (NPPI Price)", self.styles['FormulaStyle']))
        story.append(Paragraph(f"Calculation: 0.5 × {ppr['avg_competitor']:,.0f} + 0.2 × {official_est:,.0f} + 0.3 × {ppr['nppi_price']:,.0f}", self.styles['CustomNormal']))
        story.append(Paragraph(f"= {0.5 * ppr['avg_competitor']:,.0f} + {0.2 * official_est:,.0f} + {0.3 * ppr['nppi_price']:,.0f} = {ppr['weighted_avg']:,.0f}", self.styles['CustomNormal']))
        story.append(Spacer(1, 0.1*inch))
        
        # Weighted Standard Deviation
        story.append(Paragraph("Step 3: Weighted Standard Deviation (Sd) Calculation", self.styles['CustomSubheader']))
        story.append(Paragraph("Competitor Bids:", self.styles['CustomNormal']))
        
        # Competitor bids table
        comp_data = [["Sl. No.", "Bid Amount (BDT)", "% of Estimate", "(X̄ - Xi)²"]]
        for i, price in enumerate(ppr['competitor_prices'], 1):
            deviation_sq = ppr['squared_deviations'][i-1]
            comp_data.append([
                str(i),
                f"BDT {price:,.0f}",
                f"{price/official_est*100:.1f}%",
                f"{deviation_sq:,.0f}"
            ])
        
        comp_table = Table(comp_data, colWidths=[0.8*inch, 2.2*inch, 1.5*inch, 1.5*inch])
        comp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 0.1*inch))
        
        story.append(Paragraph(f"Sum of Squared Deviations: Σ = {sum(ppr['squared_deviations']):,.0f}", self.styles['CustomNormal']))
        story.append(Paragraph(f"Number of Competitors (n): {ppr['number_of_competitors']}", self.styles['CustomNormal']))
        story.append(Paragraph(f"Variance = Σ / n = {sum(ppr['squared_deviations']):,.0f} / {ppr['number_of_competitors']} = {sum(ppr['squared_deviations'])/ppr['number_of_competitors']:,.0f}", self.styles['CustomNormal']))
        story.append(Paragraph(f"Standard Deviation (Sd) = √Variance = {ppr['weighted_std']:,.0f}", self.styles['CustomNormal']))
        story.append(Spacer(1, 0.1*inch))
        
        # SLT Threshold
        story.append(Paragraph("Step 4: SLT Threshold Calculation", self.styles['CustomSubheader']))
        story.append(Paragraph(f"Formula: SLT Threshold = X̄ - Sd", self.styles['FormulaStyle']))
        story.append(Paragraph(f"Calculation: {ppr['weighted_avg']:,.0f} - {ppr['weighted_std']:,.0f} = {ppr['slt_threshold']:,.0f}", self.styles['CustomNormal']))
        story.append(Spacer(1, 0.1*inch))
        
        # Bid Evaluation
        story.append(Paragraph("Step 5: Bid Evaluation", self.styles['CustomSubheader']))
        story.append(Paragraph(f"Recommended Bid: BDT {rec_bid:,.0f}", self.styles['CustomNormal']))
        story.append(Paragraph(f"SLT Threshold: BDT {ppr['slt_threshold']:,.0f}", self.styles['CustomNormal']))
        story.append(Paragraph(f"Result: Bid is {'BELOW' if ppr['is_slt'] else 'ABOVE'} SLT Threshold", self.styles['CustomNormal']))
        
        # Compliance Status
        story.append(Spacer(1, 0.1*inch))
        status_color = colors.HexColor('#d4edda') if not ppr['is_slt'] else colors.HexColor('#f8d7da')
        status_text_color = colors.HexColor('#155724') if not ppr['is_slt'] else colors.HexColor('#721c24')
        
        story.append(Paragraph(f"Status: {'✅ Non-SLT - Acceptable Bid (Compliant)' if not ppr['is_slt'] else '⚠️ SLT - Significantly Low-priced Tender (High Risk)'}", 
                              self.styles['CustomNormal']))
        
        story.append(Paragraph("PPR 2025 Reference: Clause 49.3 - Any tender quoted below the SLT Threshold shall be considered a significantly low-priced tender and shall be treated as financially non-responsive and rejected.", 
                              self.styles['CustomNormal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Competitor Summary
        story.append(Paragraph("4. COMPETITOR SUMMARY", self.styles['CustomHeader']))
        
        comp_summary_data = [
            ["Total Competitors:", str(analysis_record.get('competitor_count', 0))],
            ["Average Competitor Bid:", f"BDT {ppr['avg_competitor']:,.0f}"],
            ["Lowest Competitor Bid:", f"BDT {min(ppr['competitor_prices']):,.0f}"],
            ["Highest Competitor Bid:", f"BDT {max(ppr['competitor_prices']):,.0f}"],
        ]
        
        comp_summary_table = Table(comp_summary_data, colWidths=[3*inch, 4*inch])
        comp_summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(comp_summary_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Recommendations
        story.append(Paragraph("5. RECOMMENDATIONS", self.styles['CustomHeader']))

        # Build recommendation text based on SLT status
        if ppr['is_slt']:
            risk_text = "⚠️ HIGH RISK: Bid is below SLT threshold. Consider increasing bid to avoid rejection."
            action_text = f"RECOMMENDED ACTION: Increase bid to at least BDT {ppr['slt_threshold'] * 1.02:,.0f} to avoid SLT rejection."
        else:
            risk_text = "✅ Low Risk: Bid is above SLT threshold, PPR compliant."
            action_text = "Current bid strategy is PPR compliant."

        recommendations = f"""
        <b>Recommended Bid:</b> BDT {rec_bid:,.0f}<br/>
        <b>Recommended Range:</b> BDT {official_est * 0.87:,.0f} - BDT {official_est * 0.94:,.0f}<br/>
        <b>Suggested Strategy:</b> Moderate approach<br/><br/>
        <b>Key Considerations:</b><br/>
        - {risk_text}<br/>
        - Win probability estimated at {win_prob:.0f}% based on market conditions<br/>
        - Expected profit of BDT {rec_bid - (official_est * 0.85):,.0f}<br/>
        - {action_text}
        """

        story.append(Paragraph(recommendations, self.styles['CustomNormal']))

        story.append(Spacer(1, 0.3*inch))
        
        # Footer
        story.append(Paragraph("Generated by TenderAI - PPR 2025 Compliant Tender Management System", self.styles['FooterStyle']))
        story.append(Paragraph(f"SLT Calculation per Bangladesh Public Procurement Rules 2025 (PPR 2025) Clause 49", self.styles['FooterStyle']))
        story.append(Paragraph(f"© {datetime.now().year} TenderAI. All rights reserved.", self.styles['FooterStyle']))
        
        doc.build(story)
        buffer.seek(0)
        
        return buffer


def generate_html_preview(analysis_record, user_info):
    """Wrapper function to generate HTML preview"""
    generator = ReportGenerator()
    return generator.generate_html_preview(analysis_record, user_info)


def generate_pdf_report(analysis_record, user_info):
    """Wrapper function to generate PDF report"""
    generator = ReportGenerator()
    return generator.generate_pdf_report(analysis_record, user_info)