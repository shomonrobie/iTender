import io
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from database.db_manager import DatabaseManager
def debug_print(*args, **kwargs):
    print(*args, **kwargs)
DEBUG_MODE = True  # Set to False in production
db = DatabaseManager()

def generate_babui_detailed_report(report_data: dict, user_info: dict = None) -> io.BytesIO:
    """
    Generates a comprehensive, print-ready PDF report for Babui TenderAI.
    Handles missing data gracefully and includes all requested sections.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    # ─── Custom Styles ───────────────────────────────────────────────────────
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#0f172a'), alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=13, textColor=colors.HexColor('#2563eb'), alignment=TA_CENTER, spaceAfter=16, fontName='Helvetica-Bold')
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#1e40af'), spaceBefore=14, spaceAfter=6, borderPadding=4, fontName='Helvetica-Bold')
    normal_style = styles['Normal']

    # ─── Safe Data Extraction ────────────────────────────────────────────────
    def safe_float(val, default=0.0):
        try: return float(val) if val is not None else default
        except: return default
    def safe_str(val, default="N/A"):
        return str(val).strip() if val is not None and str(val).strip() else default

    est = safe_float(report_data.get('official_estimate', 1), 1.0)
    bid = safe_float(report_data.get('recommended_bid', 0), 0.0)
    slt = safe_float(report_data.get('slt_threshold', est * 0.8), est * 0.8)
    nppi = safe_float(report_data.get('nppi_factor', 0.92), 0.92)
    win_prob = safe_float(report_data.get('success_probability', 0.6), 0.6)
    comp_count = int(safe_float(report_data.get('competitor_count', len(report_data.get('competitor_bids', [])))))
    bid_source = safe_str(report_data.get('bid_source', 'Auto-Generated'))
    risk_tol = safe_str(report_data.get('risk_tolerance', 'moderate')).title()
    comparison = report_data.get('comparison', {})
    comp_bids = report_data.get('competitor_bids', [])

    # ─── HEADER ─────────────────────────────────────────────────────────────
    story.append(Paragraph("🤖 Babui TenderAI", title_style))
    story.append(Paragraph("AI Enhanced Bid Management System", subtitle_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Analysis ID: {report_data.get('id', 'N/A')}",
                           ParagraphStyle('Date', parent=normal_style, alignment=TA_CENTER, fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 12))

    # ─── TENDER INFORMATION ──────────────────────────────────────────────────
    story.append(Paragraph("📋 Tender Information", section_style))
    info_data = [
        ["Tender ID", safe_str(report_data.get('tender_id')), "Procuring Entity", safe_str(report_data.get('procuring_entity'))],
        ["Official Estimate", f"BDT {est:,.0f}", "Procurement Type", safe_str(report_data.get('procurement_type', 'goods')).upper()],
        ["Submission Deadline", safe_str(report_data.get('submission_deadline', 'N/A'))[:10], "Risk Tolerance", risk_tol],
        ["Location", f"{safe_str(report_data.get('division', ''))} / {safe_str(report_data.get('district', ''))}", "Competitors", f"{comp_count} ({bid_source})"]
    ]
    info_table = Table(info_data, colWidths=[1.4*inch, 1.8*inch, 1.4*inch, 1.8*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f8fafc')),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('ALIGN',(0,0),(-1,-1),'LEFT'),
        ('TOPPADDING',(0,0),(-1,-1),6),
        ('BOTTOMPADDING',(0,0),(-1,-1),6)
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # ─── AI RECOMMENDATIONS ──────────────────────────────────────────────────
    story.append(Paragraph("🎯 AI Recommendations", section_style))
    rec_text = (
        f"Based on {comp_count} competitor bids and PPR 2025 compliance metrics, the optimal bid is "
        f"<b>BDT {bid:,.0f}</b> ({bid/est*100:.1f}% of estimate). This bid maintains a "
        f"<b>{win_prob*100:.0f}%</b> win probability while staying safely above the SLT threshold of "
        f"BDT {slt:,.0f}. Risk assessment indicates a <b>" + safe_str(report_data.get('risk_level', 'MEDIUM')) + "</b> risk profile."
    )
    story.append(Paragraph(rec_text, ParagraphStyle('Rec', parent=normal_style, fontSize=10, spaceAfter=8)))
    story.append(Spacer(1, 8))

    # ─── THREE-TIER ANALYSIS COMPARISON ──────────────────────────────────────
    story.append(Paragraph("📊 Three-Tier Analysis Comparison", section_style))
    tier_rows = [["Tier", "Method", "Optimal Bid (BDT)", "Win Prob (%)", "Confidence (%)", "Risk"]]
    for tier in ['basic', 'advanced', 'enhanced']:
        if tier in comparison:
            r = comparison[tier]
            tier_rows.append([
                tier.upper(),
                safe_str(r.get('method', '')),
                f"{safe_float(r.get('optimal_bid', 0)):,.0f}",
                f"{safe_float(r.get('win_probability', 0))*100:.0f}%",
                f"{safe_float(r.get('confidence_score', 0.7))*100:.0f}%",
                safe_str(r.get('risk_level', 'N/A'))
            ])
    tier_table = Table(tier_rows, colWidths=[1*inch, 1.3*inch, 1.2*inch, 1*inch, 1.2*inch, 1*inch])
    tier_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dbeafe')),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5)
    ]))
    story.append(tier_table)
    story.append(Spacer(1, 12))

    # ─── COMPETITOR INTELLIGENCE ─────────────────────────────────────────────
    story.append(Paragraph("👥 Competitor Intelligence", section_style))
    if comp_bids:
        comp_rows = [["Competitor", "Bid Amount (BDT)", "% of Estimate", "Deviation"]]
        for i, cb in enumerate(comp_bids, 1):
            cb_bid = safe_float(cb.get('bid', 0))
            pct = (cb_bid / est * 100) if est > 0 else 0
            dev = ((cb_bid - est) / est * 100) if est > 0 else 0
            comp_rows.append([
                safe_str(cb.get('name', f'Competitor {i}')),
                f"{cb_bid:,.0f}",
                f"{pct:.1f}%",
                f"{dev:+.1f}%"
            ])
        comp_table = Table(comp_rows, colWidths=[1.8*inch, 1.5*inch, 1*inch, 1*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f0fdf4')),
            ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ('FONTSIZE',(0,0),(-1,-1),9),
            ('TOPPADDING',(0,0),(-1,-1),5),
            ('BOTTOMPADDING',(0,0),(-1,-1),5)
        ]))
        story.append(comp_table)
    else:
        story.append(Paragraph("No competitor data provided.", normal_style))
    story.append(Spacer(1, 12))

    # ─── PPR 2025 COMPLIANCE CHECK ───────────────────────────────────────────
    story.append(Paragraph("📜 PPR 2025 Compliance Check", section_style))
    is_compliant = bid >= slt
    status_color = colors.green if is_compliant else colors.red
    status_text = "✅ COMPLIANT" if is_compliant else "⚠️ SLT RISK"
    
    ppr_data = [
        ["Metric", "Value", "Status"],
        ["SLT Threshold", f"BDT {slt:,.0f}", "Reference"],
        ["Recommended Bid", f"BDT {bid:,.0f}", status_text],
        ["NPPI Factor", f"{nppi:.3f}", "Applied"],
        ["Bid Ratio", f"{bid/est*100:.1f}%" if est > 0 else "N/A", "Of Estimate"],
        ["Win Probability", f"{win_prob*100:.0f}%", "Statistical"]
    ]
    ppr_table = Table(ppr_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
    ppr_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcfce7')),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('TEXTCOLOR',(2,2),(2,2),status_color),
        ('BACKGROUND',(2,2),(2,2),colors.HexColor('#dcfce7') if is_compliant else '#fee2e2'),
        ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5)
    ]))
    story.append(ppr_table)
    story.append(Spacer(1, 12))

    # ─── FINANCIAL PROJECTIONS ───────────────────────────────────────────────
    story.append(Paragraph("💰 Financial Projections", section_style))
    cost = est * 0.85
    profit = bid - cost
    exp_val = profit * win_prob
    fin_data = [
        ["Metric", "Value", "Interpretation"],
        ["Estimated Cost", f"BDT {cost:,.0f}", "85% of official estimate"],
        ["Expected Profit", f"BDT {profit:,.0f}", "If bid wins"],
        ["Expected Value", f"BDT {exp_val:,.0f}", "Profit × Win Probability"]
    ]
    fin_table = Table(fin_data, colWidths=[1.5*inch, 1.5*inch, 2*inch])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#fef3c7')),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5)
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 16))

    # ─── FOOTER ──────────────────────────────────────────────────────────────
    disclaimer = Paragraph(
        "<b>Disclaimer:</b> This AI-generated analysis complies with Bangladesh PPR 2025 guidelines. Final bidding decisions should consider project-specific risks, internal cost structures, and strategic objectives. NPPI factor derived from 28-day market averages.",
        ParagraphStyle('Disc', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER, spaceBefore=12)
    )
    story.append(disclaimer)
    if user_info:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Prepared for: {safe_str(user_info.get('full_name'))} | {safe_str(user_info.get('company_name'))}",
                               ParagraphStyle('Foot', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)))

    doc.build(story)
    buffer.seek(0)
    return buffer

def _generate_and_download_pdf(analysis_id: int, analysis_record: dict) -> None:
    """Helper with bulletproof logging and fallbacks"""
    debug_print("🚀 PDF HELPER START | id={analysis_id}, record_type={type(analysis_record)}, keys={list(analysis_record.keys())[:5] if analysis_record else 'EMPTY'}")
    #logger.info(f"🚀 PDF HELPER START | id={analysis_id}, record_type={type(analysis_record)}, keys={list(analysis_record.keys())[:5] if analysis_record else 'EMPTY'}")
    
    with st.spinner("🔄 Generating PDF report..."):
        try:
            from modules.pdf_generator import generate_enhanced_analysis_report
            
            user_info = {
                'full_name': st.session_state.get('full_name', 'N/A'),
                'company_name': st.session_state.get('company_name', 'N/A'),
                'role': st.session_state.get('user_role', 'N/A'),
                'email': st.session_state.get('user_email', 'N/A'),
            }
            #logger.debug(f"👤 User: {user_info.get('full_name')}")
            debug_print(f"👤 User Info: {user_info}")

            # ✅ Fetch from DB if ID provided
            if analysis_id:
                #logger.debug(f"🗄️ Fetching DB record for id={analysis_id}")
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tender_analyses WHERE id = ?', (analysis_id,))
                saved = cursor.fetchone()
                conn.close()
                
                if saved and cursor.description:
                    cols = [d[0] for d in cursor.description]
                    db_record = dict(zip(cols, saved))
                    report_data = {**analysis_record, **db_record}  # DB overwrites session
                    #logger.debug(f"✅ Merged DB + session | final keys: {list(report_data.keys())[:10]}")
                else:
                    report_data = analysis_record
                    #logger.warning(f"⚠️ No DB record for id={analysis_id}, using session data only")
            else:
                report_data = analysis_record
                #logger.info("ℹ️ No analysis_id provided, using session data only")
            
            # ✅ SAFE TYPE CONVERSIONS (Critical for PDF values)
            #logger.debug("🔧 Applying safe type conversions...")
            est = float(report_data.get('official_estimate') or 1)
            bid = float(report_data.get('recommended_bid') or 0)
            slt = float(report_data.get('slt_threshold') or (est * 0.80))
            nppi = float(report_data.get('nppi_factor') or 0.92)
            win_prob = float(report_data.get('success_probability') or 0.6)
            
            # Update report_data with converted values
            report_data.update({
                'official_estimate': est,
                'recommended_bid': bid,
                'slt_threshold': slt,
                'nppi_factor': nppi,
                'success_probability': win_prob
            })
            #logger.info(f"💰 Converted values: est={est}, bid={bid}, slt={slt}, nppi={nppi}")
            debug_print(f"💰 Converted values: est={est}, bid={bid}, slt={slt}, nppi={nppi}")
            # ✅ Generate PDF
            #logger.debug("📄 Calling generate_enhanced_analysis_report()...")
            pdf_buffer = generate_enhanced_analysis_report(report_data, user_info, include_charts=False)
            
            # ✅ Validate buffer
            if not pdf_buffer:
                #logger.error("❌ PDF buffer is None")
                st.error("❌ PDF generation returned None")
                return
            if pdf_buffer.getbuffer().nbytes == 0:
                #logger.error("❌ PDF buffer is empty (0 bytes)")
                st.error("❌ PDF generation returned empty buffer")
                return
            
            #logger.info(f"✅ PDF generated successfully | size={pdf_buffer.getbuffer().nbytes} bytes")
            
            # ✅ STORE in session state (CRITICAL STEP)
            safe_tid = str(report_data.get('tender_id', 'report')).replace('/', '_').replace('\\', '_').replace(' ', '_')
            filename = f"Enhanced_Analysis_{safe_tid}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            
            st.session_state._pdf_buffer = pdf_buffer
            st.session_state._pdf_filename = filename
            
            #logger.info(f"💾 Stored buffer in session state | filename={filename}")
            st.success("✅ PDF generated! Scroll down to download.")
            
            # ✅ Force immediate rerun to show download button (optional but reliable)
            # st.rerun()  # Uncomment if button doesn't appear without this
            
        except ImportError as e:
            #logger.error(f"❌ ImportError in PDF helper: {e}")
            st.warning(f"⚠️ PDF module not available: {e}")
        except Exception as e:
            #logger.error(f"❌ PDF helper failed: {type(e).__name__}: {str(e)}", exc_info=True)
            st.error(f"❌ PDF error: {str(e)}")
            if DEBUG_MODE:
                with st.expander("🐛 PDF Helper Traceback"):
                    st.code(traceback.format_exc(), language="python")


def generate_analysis_report(analysis_data: dict, tender_info: dict, user_info: dict = None) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1e3a8a'), alignment=TA_CENTER, spaceAfter=12)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2563eb'), spaceBefore=12, spaceAfter=6)
    normal_style = styles['Normal']

    # Header
    story.append(Paragraph("🎯 Three-Tier Bid Analysis Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                           ParagraphStyle('Date', parent=normal_style, alignment=TA_CENTER, fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 12))

    # Tender Info
    story.append(Paragraph("📋 Tender Information", section_style))
    est = tender_info.get('official_estimate', 1)
    info_data = [
        ["Tender ID", tender_info.get('tender_id', 'N/A'), "Procuring Entity", tender_info.get('procuring_entity', 'N/A')],
        ["Official Estimate", f"BDT {est:,.0f}", "Procurement Type", str(tender_info.get('procurement_type', '')).upper()],
        ["Submission Deadline", str(tender_info.get('submission_deadline', 'N/A'))[:10], "Risk Tolerance", tender_info.get('risk_tolerance', 'moderate').title()]
    ]
    info_table = Table(info_data, colWidths=[1.2*inch, 1.8*inch, 1.2*inch, 1.8*inch])
    info_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f1f5f9')),('GRID',(0,0),(-1,-1),0.5,colors.grey),('FONTSIZE',(0,0),(-1,-1),9)]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # Competitor Bids
    comp_bids = analysis_data.get('current_competitor_bids', [])
    if comp_bids:
        story.append(Paragraph("👥 Competitor Bids", section_style))
        comp_data = [["Competitor", "Bid Amount (BDT)", "% of Estimate"]]
        for cb in comp_bids:
            pct = (cb['bid'] / est * 100) if est > 0 else 0
            comp_data.append([cb.get('name', 'Unknown'), f"{cb['bid']:,.0f}", f"{pct:.1f}%"])
        comp_table = Table(comp_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        comp_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e0f2fe')),('GRID',(0,0),(-1,-1),0.5,colors.grey),('FONTSIZE',(0,0),(-1,-1),9)]))
        story.append(comp_table)
        story.append(Spacer(1, 12))

    # Three-Tier Comparison
    story.append(Paragraph("📊 Three-Tier Analysis Comparison", section_style))
    comparison = analysis_data.get('current_comparison', {})
    tier_data = [["Tier", "Optimal Bid (BDT)", "Win Prob (%)", "Risk Level", "Confidence (%)"]]
    for t in ["basic", "advanced", "enhanced"]:
        if t in comparison:
            r = comparison[t]
            tier_data.append([t.replace('_', ' ').title(), f"{r['optimal_bid']:,.0f}", 
                              f"{r.get('win_probability', 0)*100:.1f}", r.get('risk_level', 'N/A'), 
                              f"{r.get('confidence_score', 0)*100:.1f}"])
    tier_table = Table(tier_data, colWidths=[1.2*inch, 1.3*inch, 1*inch, 1*inch, 1*inch])
    tier_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dbeafe')),('GRID',(0,0),(-1,-1),0.5,colors.grey),('FONTSIZE',(0,0),(-1,-1),9)]))
    story.append(tier_table)
    story.append(Spacer(1, 12))

    # PPR 2025 Compliance
    story.append(Paragraph("📜 PPR 2025 Compliance Check", section_style))
    adv = comparison.get('advanced', comparison.get('basic', {}))
    slt = adv.get('slt_threshold', 0)
    rec_bid = adv.get('optimal_bid', 0)
    nppi = adv.get('nppi_factor', 0)
    compliant = rec_bid >= slt
    
    ppr_data = [["Metric", "Value", "Status"],
                ["SLT Threshold", f"BDT {slt:,.0f}", "Reference"],
                ["Recommended Bid", f"BDT {rec_bid:,.0f}", "✅ Compliant" if compliant else "⚠️ Below SLT"],
                ["NPPI Factor", f"{nppi:.3f}", "Applied"],
                ["Bid Ratio", f"{rec_bid/est*100:.1f}%" if est else "N/A", "Of Estimate"]]
    ppr_table = Table(ppr_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
    ppr_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcfce7')),('GRID',(0,0),(-1,-1),0.5,colors.grey),
                                   ('FONTSIZE',(0,0),(-1,-1),9),('TEXTCOLOR',(2,2),(2,2),colors.green if compliant else colors.red)]))
    story.append(ppr_table)
    story.append(Spacer(1, 12))

    # Footer
    disclaimer = Paragraph("<b>Disclaimer:</b> Analysis complies with Bangladesh PPR 2025. Final decisions should consider project-specific risks and internal cost structures.", 
                           ParagraphStyle('Disc', parent=normal_style, fontSize=8, textColor=colors.grey, alignment=TA_CENTER))
    story.append(disclaimer)
    if user_info:
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Prepared for: {user_info.get('full_name', 'N/A')} | {user_info.get('company_name', 'N/A')}", 
                               ParagraphStyle('Foot', parent=normal_style, fontSize=8, alignment=TA_CENTER, textColor=colors.grey)))

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_enhanced_analysis_report(analysis_data: dict, user_info: dict, include_charts: bool = True) -> io.BytesIO:
    """Enhanced PDF with safe fallbacks for missing/None values"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e3a8a'), alignment=TA_CENTER, spaceAfter=16)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2563eb'), spaceBefore=16, spaceAfter=8)
    
    # Header
    story.append(Paragraph("🎯 Enhanced Bid Analysis Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} • {user_info.get('company_name', 'N/A')}", 
                           ParagraphStyle('Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.grey)))
    story.append(Spacer(1, 16))
    
    # ✅ SAFE: Extract values with fallbacks
    est = float(analysis_data.get('official_estimate', 1) or 1)
    rec = float(analysis_data.get('recommended_bid', 0) or 0)
    slt = float(analysis_data.get('slt_threshold', est * 0.80) or (est * 0.80))
    nppi = float(analysis_data.get('nppi_factor', 0.92) or 0.92)
    win_prob = float(analysis_data.get('success_probability', 0.6) or 0.6)
    debug_print(f"Extracted - Estimate: {est}, Recommended: {rec}, SLT: {slt}, NPPI: {nppi}, Win Prob: {win_prob}")
    
    # Tender Summary Card
    story.append(Paragraph("📋 Tender Overview", section_style))
    summary_data = [
        ["Tender ID", str(analysis_data.get('tender_id', 'N/A') or 'N/A'), "Estimate", f"BDT {est:,.0f}"],
        ["Entity", str(analysis_data.get('procuring_entity', 'N/A') or 'N/A')[:40], "Recommended", f"BDT {rec:,.0f}" if rec > 0 else "N/A"],
        ["Type", str(analysis_data.get('procurement_type', '') or 'N/A').upper(), "Ratio", f"{rec/est*100:.1f}%" if est > 0 else "N/A"],
        ["Deadline", str(analysis_data.get('submission_deadline', 'N/A') or 'N/A')[:10], "Risk", str(analysis_data.get('risk_level', 'N/A') or 'N/A')]
    ]
    summary_table = Table(summary_data, colWidths=[1.3*inch, 1.7*inch, 1.3*inch, 1.7*inch])
    summary_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f1f5f9')),('GRID',(0,0),(-1,-1),0.5,colors.grey),('FONTSIZE',(0,0),(-1,-1),9)]))
    story.append(summary_table)
    story.append(Spacer(1, 12))
    
    # PPR Compliance Section
    story.append(Paragraph("📈 PPR 2025 Compliance Dashboard", section_style))
    is_compliant = rec >= slt if rec > 0 and slt > 0 else False
    status = "✅ COMPLIANT" if is_compliant else "⚠️ SLT RISK"
    status_color = colors.green if is_compliant else colors.red
    
    ppr_data = [
        ["Metric", "Value", "Status"],
        ["SLT Threshold", f"BDT {slt:,.0f}" if slt > 0 else "N/A", "Reference"],
        ["Recommended Bid", f"BDT {rec:,.0f}" if rec > 0 else "N/A", status],
        ["NPPI Factor", f"{nppi:.3f}" if nppi > 0 else "N/A", "Applied"],
        ["Bid Ratio", f"{rec/est*100:.1f}%" if est > 0 and rec > 0 else "N/A", "Of Estimate"]
    ]
    ppr_table = Table(ppr_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
    ppr_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcfce7')),('GRID',(0,0),(-1,-1),0.5,colors.grey),('FONTSIZE',(0,0),(-1,-1),9),('TEXTCOLOR',(2,2),(2,2),status_color)]))
    story.append(ppr_table)
    story.append(Spacer(1, 12))
    
    # Financial Projection (with safe math)
    story.append(Paragraph("💰 Financial Projection", section_style))
    cost = est * 0.85
    profit = rec - cost if rec > 0 else 0
    exp_value = profit * win_prob
    
    fin_data = [
        ["Metric", "Value", "Interpretation"],
        ["Estimated Cost", f"BDT {cost:,.0f}", "85% of official estimate"],
        ["Expected Profit", f"BDT {profit:,.0f}" if profit != 0 else "N/A", "If bid wins"],
        ["Win Probability", f"{win_prob*100:.0f}%", "Statistical likelihood"],
        ["Expected Value", f"BDT {exp_value:,.0f}" if exp_value != 0 else "N/A", "Profit × Win Probability"]
    ]
    fin_table = Table(fin_data, colWidths=[1.5*inch, 1.5*inch, 2*inch])
    fin_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dbeafe')),('GRID',(0,0),(-1,-1),0.5,colors.grey),('FONTSIZE',(0,0),(-1,-1),9)]))
    story.append(fin_table)
    
    # Footer
    disclaimer = Paragraph(
        "<b>Disclaimer:</b> Analysis complies with Bangladesh PPR 2025. Final decisions should consider project-specific risks.",
        ParagraphStyle('Disc', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER, spaceBefore=12)
    )
    story.append(disclaimer)
    
    doc.build(story)
    buffer.seek(0)
    return buffer