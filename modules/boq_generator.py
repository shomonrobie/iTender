# modules/boq_generator.py (updated)

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
from io import BytesIO
import re
from utils.currency_transformer import number_to_bangladesh_taka_words, number_to_bangladesh_taka_words_simple
from database.db_manager import DatabaseManager

db = DatabaseManager()
DB_PATH = db.db_path

class BOQGenerator:
    """BOQ Generation with subscription limits, tender linking, and bid tracking"""
    
    def __init__(self):
        self._init_boq_tracking()
    
    def _init_boq_tracking(self):
        """Initialize BOQ generation tracking table with tender linking"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # BOQ generation history with tender link
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS boq_generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                company_id INTEGER,
                tender_id TEXT,
                tender_title TEXT,
                procuring_entity TEXT,
                file_name TEXT,
                item_count INTEGER,
                total_estimated_cost REAL,
                selected_zone TEXT,
                rate_source TEXT,
                edition_year INTEGER,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed',
                notes TEXT,
                FOREIGN KEY (tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE SET NULL
            )
        """)
        
        # Bid submission tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bid_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boq_history_id INTEGER,
                tender_id TEXT,
                company_id INTEGER,
                submitted_bid_amount REAL,
                bid_document_path TEXT,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                submitted_by TEXT,
                status TEXT DEFAULT 'draft',
                notes TEXT,
                FOREIGN KEY (boq_history_id) REFERENCES boq_generation_history(id),
                FOREIGN KEY (tender_id) REFERENCES tenders_boq_meta(tender_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_user_plan(self, user_id, company_id):
        """Get user's subscription plan"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT plan FROM subscriptions 
            WHERE user_id = ? OR company_id = ?
            ORDER BY CASE WHEN company_id = ? THEN 1 ELSE 2 END
            LIMIT 1
        """, (user_id, company_id, company_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return 'free'
    
    def get_remaining_boq_count(self, user_id, company_id):
        """Get remaining BOQ generations for user this month"""
        
        # Get user role from session
        user_role = st.session_state.get('user_role', 'viewer')
        
        # Admins have unlimited access
        if user_role in ['admin', 'system_admin']:
            return -1, "Unlimited BOQ generations (Admin)", 'enterprise'
        
        plan = self.get_user_plan(user_id, company_id)
        
        BOQ_LIMITS = {
            'free': 5,
            'basic': 20,
            'professional': 50,
            'enterprise': -1
        }
        
        monthly_limit = BOQ_LIMITS.get(plan, 5)
        
        if monthly_limit == -1:
            return -1, "Unlimited BOQ generations", plan
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        current_month_start = date.today().replace(day=1)
        
        cursor.execute("""
            SELECT COUNT(*) FROM boq_generation_history 
            WHERE (user_id = ? OR company_id = ?)
            AND generated_at >= ?
        """, (user_id, company_id, current_month_start))
        
        used_count = cursor.fetchone()[0]
        conn.close()
        
        remaining = max(0, monthly_limit - used_count)
        return remaining, f"{remaining} of {monthly_limit} remaining this month", plan

    
    def get_tender_details(self, tender_id):
        """Get tender details from database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tender_id, ministry_or_agency, selected_zone, workflow_status, official_budget_cap
            FROM tenders_boq_meta 
            WHERE tender_id = ?
        """, (tender_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'tender_id': result[0],
                'ministry_or_agency': result[1],
                'selected_zone': result[2],
                'workflow_status': result[3],
                'official_budget_cap': result[4]
            }
        return None
    
    def record_boq_generation(self, user_id, company_id, tender_id, tender_title, procuring_entity,
                              file_name, item_count, total_cost, zone, source, edition_year):
        """Record BOQ generation with tender link"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO boq_generation_history 
            (user_id, company_id, tender_id, tender_title, procuring_entity, file_name, 
             item_count, total_estimated_cost, selected_zone, rate_source, edition_year, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, company_id, tender_id, tender_title, procuring_entity, file_name,
              item_count, total_cost, zone, source, edition_year, 'completed'))
        
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return history_id
    
    def record_bid_submission(self, boq_history_id, tender_id, company_id, bid_amount, submitted_by):
        """Record bid submission"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO bid_submissions (boq_history_id, tender_id, company_id, submitted_bid_amount, submitted_by, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (boq_history_id, tender_id, company_id, bid_amount, submitted_by, 'submitted'))
        
        conn.commit()
        conn.close()
    
    def get_rates_from_database(self, source='PWD', zone='Dhaka', edition_year=2022):
        """Get all rates from database for matching"""
        conn = sqlite3.connect(DB_PATH)
        
        if source == 'PWD':
            df = pd.read_sql_query("""
                SELECT c.pwd_code as code, c.description, c.unit, r.unit_rate
                FROM pwd_children c
                JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                WHERE r.zone_name = ? AND r.edition_year = ?
            """, conn, params=(zone, edition_year))
        else:
            df = pd.read_sql_query("""
                SELECT c.code, c.description, c.unit, r.unit_rate
                FROM lged_children c
                JOIN lged_zone_rates r ON c.id = r.child_id
                WHERE r.zone_name = ?
            """, conn, params=(zone,))
        
        conn.close()
        return df
    
    def match_boq_items(self, df_boq, rates_df):
        """Match BOQ items with database rates"""
        
        matched_items = []
        unmatched_items = []
        
        # Clean the rates data
        rates_df['code'] = rates_df['code'].astype(str).str.strip()
        rates_df['description'] = rates_df['description'].astype(str).str.lower().str.strip()
        
        # Create lookup dictionaries
        code_lookup = {}
        desc_lookup = {}
        
        for _, row in rates_df.iterrows():
            code = row['code']
            desc = row['description']
            rate = row['unit_rate']
            unit = row['unit']
            
            code_lookup[code] = (rate, unit)
            
            # Store multiple descriptions (full and without brackets)
            desc_lookup[desc] = (rate, unit)
            # Also store without PWD reference
            desc_clean = re.sub(r'\[PWD[^\]]+\]', '', desc).strip()
            if desc_clean != desc:
                desc_lookup[desc_clean] = (rate, unit)
        
        for idx, row in df_boq.iterrows():
            item_code = str(row.get('Item Code (if any)', '')).strip()
            item_desc = str(row.get('Description of Item', '')).strip()
            quantity = float(row.get('Quantity', 0)) if pd.notna(row.get('Quantity', 0)) else 0
            
            # Skip if quantity is zero or description is empty
            if quantity == 0 or not item_desc or item_desc == 'nan':
                continue
            
            matched_rate = None
            matched_unit = None
            match_method = None
            
            # Try exact code match
            if item_code and item_code in code_lookup:
                matched_rate, matched_unit = code_lookup[item_code]
                match_method = "Exact Code Match"
            
            # Try exact description match (case insensitive)
            elif not matched_rate:
                item_desc_lower = item_desc.lower().strip()
                if item_desc_lower in desc_lookup:
                    matched_rate, matched_unit = desc_lookup[item_desc_lower]
                    match_method = "Exact Description Match"
            
            # Try partial description match (remove common words)
            elif not matched_rate:
                # Remove common boilerplate words
                stop_words = {'providing', 'including', 'supplying', 'fitting', 'fixing', 
                            'construction', 'complete', 'direction', 'engineer', 'charge'}
                item_words = set(item_desc_lower.split()) - stop_words
                
                best_match = None
                best_score = 0
                
                for db_desc, (rate, unit) in desc_lookup.items():
                    db_words = set(db_desc.split()) - stop_words
                    common = item_words.intersection(db_words)
                    score = len(common)
                    
                    if score > best_score and score >= 2:
                        best_score = score
                        best_match = (rate, unit)
                
                if best_match:
                    matched_rate, matched_unit = best_match
                    match_method = "Partial Description Match"
            
            item_data = {
                'Item Code': item_code,
                'Description': item_desc,
                'Unit': matched_unit if matched_unit else row.get('Measurement Unit', ''),
                'Quantity': quantity,
                'Unit Rate': matched_rate if matched_rate else 0,
                'Total Price': (quantity * matched_rate) if matched_rate else 0,
                'Match Status': match_method if match_method else 'Not Found'
            }
            
            if matched_rate:
                matched_items.append(item_data)
            else:
                unmatched_items.append(item_data)
        
        return matched_items, unmatched_items

    
    def generate_boq_excel(self, matched_items, unmatched_items, source, zone, edition_year, tender_id):
        """Generate BOQ Excel file without Match Status column"""
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Matched Items - Remove Match Status column
            if matched_items:
                # Create a copy without the Match Status column
                matched_df = pd.DataFrame(matched_items)
                matched_df = matched_df.drop(columns=['Match Status'], errors='ignore')
                
                matched_df['Unit Price (BDT)'] = matched_df['Unit Rate'].apply(lambda x: f"{x:,.2f}")
                matched_df['Total Price (BDT)'] = matched_df['Total Price'].apply(lambda x: f"{x:,.2f}")
                matched_df['Unit Price In Words'] = matched_df['Unit Rate'].apply(number_to_bangladesh_taka_words)
                matched_df['Total Price In Words'] = matched_df['Total Price'].apply(number_to_bangladesh_taka_words)
                matched_df.to_excel(writer, sheet_name='Matched Items', index=False)
            
            # Sheet 2: Unmatched Items - Remove Match Status column
            if unmatched_items:
                unmatched_df = pd.DataFrame(unmatched_items)
                unmatched_df = unmatched_df.drop(columns=['Match Status'], errors='ignore')
                unmatched_df.to_excel(writer, sheet_name='Unmatched Items', index=False)
            
            # Sheet 3: Summary (keep as is)
            total_cost = sum(item['Total Price'] for item in matched_items)
            summary_data = {
                'Parameter': ['Tender ID', 'Rate Source', 'Zone', 'Edition Year', 'Total Items', 'Matched', 'Unmatched', 'Total Estimated Cost', 'Generated On'],
                'Value': [
                    tender_id, source, zone, edition_year,
                    len(matched_items) + len(unmatched_items),
                    len(matched_items), len(unmatched_items),
                    f"BDT {total_cost:,.2f}",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        output.seek(0)
        return output, total_cost
