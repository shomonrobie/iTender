#
"""
Complete Tender Management Module
Track tender participation, bid submission, deadlines, and winner tracking

Refactored for:
- Proper session state management
- Fixed PDF upload → review → form workflow
- Clean separation of concerns
- Type safety and error handling
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import logging
from typing import Optional, Dict, List, Any
from database.unified_db_manager import UnifiedDatabaseManager
DEBUG_MODE = True
# Initialize logger
logger = logging.getLogger(__name__)
db = UnifiedDatabaseManager()
from modules.rbac import (
    rbac, can_view_tenders, can_create_tender, can_edit_tender,
    can_submit_bid, can_manage_team, can_export_data,
    render_role_badge, render_protected_button
)


# =============================================================================
# 🗄️ DATABASE METHODS (Attached to DatabaseManager instance)
# =============================================================================

def create_tender(company_id: int, tender_data: Dict[str, Any], created_by: int) -> Optional[int]:
    """Create a new tender entry with full e-GP field support (Dynamic Query Generation)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 1. Check for duplicate Tender ID
        cursor.execute('''
        SELECT id FROM company_tenders WHERE company_id = ? AND tender_id = ? AND is_active = 1
        ''', (company_id, tender_data.get('tender_id', '')))
        if cursor.fetchone():
            conn.close()
            return None
        
        # 2. Explicitly define columns (Add/Remove here to match your DB schema)
        columns = [
            'company_id', 'tender_id', 'tender_title', 'procuring_entity', 'division',
            'district', 'thana', 'country', 'procurement_type', 'official_estimate',
            'submission_deadline', 'tender_security', 'document_fee', 'evaluation_type',
            'mode_of_payment', 'eligibility_criteria', 'invitation_ref_no', 'package_no',
            'project_code', 'project_name', 'inviting_official_name', 'inviting_official_designation',
            'inviting_official_phone', 'inviting_official_email', 'inviting_official_address', 
            'inviting_official_city', 'inviting_official_thana', 'inviting_official_district', 
            'notes', 'created_by', 'is_locked', 'is_copy', 'original_tender_id', 'is_active',
            'app_id', 'procuring_entity_code', 'procurement_nature', 'event_type', 
            'budget_type', 'source_of_funds', 'category', 'tender_publication_date',
            'document_selling_end_date', 'pre_bid_meeting_start', 'pre_bid_meeting_end',
            'bid_opening_date', 'security_submission_deadline', 'security_valid_upto',
            'tender_valid_upto'
        ]
        
        # 3. Default values mapping
        defaults = {
            'tender_id': '', 'tender_title': '', 'procuring_entity': '', 'division': 'Dhaka',
            'district': '', 'thana': '', 'country': 'Bangladesh', 'procurement_type': 'works',
            'official_estimate': 0.0, 'tender_security': 0.0, 'document_fee': 0.0,
            'evaluation_type': 'Lot wise', 'mode_of_payment': 'Payment through Bank',
            'eligibility_criteria': 'As Per Tender Documents', 'invitation_ref_no': '',
            'package_no': '', 'project_code': '', 'project_name': '',
            'inviting_official_name': '', 'inviting_official_designation': '',
            'inviting_official_phone': '', 'inviting_official_email': '',
            'inviting_official_address': '', 'inviting_official_city': '',
            'inviting_official_thana': '', 'inviting_official_district': '', 'notes': '',
            'app_id': '', 'procuring_entity_code': '', 'procurement_nature': 'Works',
            'event_type': 'TENDER', 'budget_type': '', 'source_of_funds': 'Government',
            'category': '', 'submission_deadline': None, 'security_submission_deadline': None
        }
        
        # 4. Build values list dynamically (Guarantees count matches columns)
        values = []
        for col in columns:
            if col == 'company_id':
                values.append(company_id)
            elif col == 'created_by':
                values.append(created_by)
            elif col == 'is_locked':
                values.append(0)
            elif col == 'is_copy':
                values.append(0)
            elif col == 'original_tender_id':
                values.append(None)
            elif col == 'is_active':
                values.append(1)
            else:
                val = tender_data.get(col, defaults.get(col))
                # Ensure floats are floats
                if col in ['official_estimate', 'tender_security', 'document_fee']:
                    try: val = float(val) if val is not None else 0.0
                    except: val = 0.0
                values.append(val)
                
        # 5. Execute dynamic query
        placeholders = ', '.join(['?'] * len(columns))
        col_names = ', '.join(columns)
        query = f"INSERT INTO company_tenders ({col_names}) VALUES ({placeholders})"
        
        cursor.execute(query, values)
        tender_db_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tender_db_id
        
    except Exception as e:
        logger.error(f"Failed to create tender: {e}", exc_info=True)
        return None
def update_tender(tender_id: int, tender_data: Dict[str, Any], updated_by: int) -> bool:
    """Update an existing tender with full e-GP field support"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if tender exists and belongs to company
        cursor.execute('''
        SELECT id FROM company_tenders WHERE id = ? AND company_id = ? AND is_active = 1
        ''', (tender_id, st.session_state.company_id))
        
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Define updatable columns (match your table structure)
        updatable_columns = [
            'tender_id', 'tender_title', 'procuring_entity', 'division',
            'district', 'thana', 'country', 'procurement_type', 'official_estimate',
            'submission_deadline', 'tender_security', 'document_fee', 'evaluation_type',
            'mode_of_payment', 'eligibility_criteria', 'invitation_ref_no', 'package_no',
            'project_code', 'project_name', 'inviting_official_name',
            'inviting_official_designation', 'inviting_official_phone',
            'inviting_official_email', 'inviting_official_address',
            'inviting_official_city', 'inviting_official_thana',
            'inviting_official_district', 'notes', 'app_id', 'procuring_entity_code',
            'procurement_nature', 'event_type', 'budget_type', 'source_of_funds',
            'category', 'tender_publication_date', 'document_selling_end_date',
            'pre_bid_meeting_start', 'pre_bid_meeting_end', 'bid_opening_date',
            'security_submission_deadline', 'security_valid_upto', 'tender_valid_upto'
        ]
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        for col in updatable_columns:
            if col in tender_data and tender_data[col] is not None:
                update_fields.append(f"{col} = ?")
                update_values.append(tender_data[col])
        
        if not update_fields:
            conn.close()
            return False
        
        # Add updated_at timestamp
        update_fields.append("updated_at = ?")
        update_values.append(datetime.now())
        
        # Add tender_id to values
        update_values.append(tender_id)
        
        query = f"UPDATE company_tenders SET {', '.join(update_fields)} WHERE id = ?"
        
        cursor.execute(query, update_values)
        conn.commit()
        
        success = cursor.rowcount > 0
        conn.close()
        
        if success:
            # Log the activity
            logger.info(f"Tender {tender_id} updated by user {updated_by}")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to update tender: {e}", exc_info=True)
        return False


def get_company_tenders(company_id: int, status_filter: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
    """Fetch all tenders for a company, including new e-GP fields"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            t.id, t.company_id, t.tender_id, t.tender_title, t.procuring_entity,
            t.division, t.district, t.thana, t.country, t.procurement_type,
            t.official_estimate, t.submission_deadline, t.tender_security,
            t.document_fee, t.evaluation_type, t.mode_of_payment,
            t.eligibility_criteria, t.invitation_ref_no, t.package_no,
            t.project_code, t.project_name, t.inviting_official_name,
            t.inviting_official_designation, t.inviting_official_phone,
            t.inviting_official_email, t.inviting_official_address,
            t.inviting_official_city, t.inviting_official_thana,
            t.inviting_official_district, t.our_bid_amount, t.bid_submitted_by,
            t.bid_submission_date, t.bid_status, t.evaluation_status,
            t.winning_bid_amount, t.winning_competitor, t.our_rank,
            t.total_bidders, t.award_date, t.notes, t.created_by,
            t.created_at, t.updated_at,
            t.is_locked, t.locked_at, t.locked_by,
            t.is_copy, t.original_tender_id,
            t.is_active, t.deleted_at, t.deleted_by,
            u.full_name as submitted_by_name,
            -- ✅ NEW e-GP FIELDS:
            t.app_id, t.procuring_entity_code, t.procurement_nature,
            t.event_type, t.budget_type, t.source_of_funds, t.category,
            t.tender_publication_date, t.document_selling_end_date,
            t.pre_bid_meeting_start, t.pre_bid_meeting_end,
            t.bid_opening_date, t.security_submission_deadline,
            t.security_valid_upto, t.tender_valid_upto
        FROM company_tenders t
        LEFT JOIN users u ON t.bid_submitted_by = u.id
        WHERE t.company_id = ? AND t.is_active = 1
        '''
        params = [company_id]
        
        if status_filter:
            query += " AND t.bid_status = ?"
            params.append(status_filter)
        
        query += " ORDER BY t.submission_deadline ASC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Failed to fetch company tenders: {e}", exc_info=True)
        return pd.DataFrame()


def update_tender_bid(tender_id: int, bid_amount: float, updated_by: int) -> bool:
    """Update bid amount for a tender with revision history"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get current bid for revision history
        cursor.execute('SELECT our_bid_amount FROM company_tenders WHERE id = ?', (tender_id,))
        current = cursor.fetchone()
        
        if current and current[0] is not None and current[0] != bid_amount:
            # Get next revision number
            cursor.execute('SELECT COALESCE(MAX(revision_number), 0) + 1 FROM bid_revisions WHERE tender_id = ?', (tender_id,))
            next_rev = cursor.fetchone()[0]
            
            cursor.execute('''
            INSERT INTO bid_revisions (tender_id, revision_number, bid_amount, revised_by, reason)
            VALUES (?, ?, ?, ?, ?)
            ''', (tender_id, next_rev, bid_amount, updated_by, 'Bid amount updated via UI'))
        
        cursor.execute('''
        UPDATE company_tenders 
        SET our_bid_amount = ?, updated_at = ?
        WHERE id = ?
        ''', (bid_amount, datetime.now(), tender_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update tender bid: {e}", exc_info=True)
        return False


def submit_bid(tender_id: int, final_bid_amount: float, submitted_by: int) -> bool:
    """Finalize and submit the bid"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE company_tenders 
        SET our_bid_amount = ?, bid_submitted_by = ?, 
            bid_submission_date = ?, bid_status = 'submitted',
            updated_at = ?
        WHERE id = ?
        ''', (final_bid_amount, submitted_by, datetime.now(), datetime.now(), tender_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to submit bid: {e}", exc_info=True)
        return False


def update_tender_result(tender_id: int, winning_bid_amount: float, winning_competitor: str, 
                        our_rank: int, total_bidders: int, award_date: str, bid_status: str) -> bool:
    """Update tender result after award announcement"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE company_tenders 
        SET winning_bid_amount = ?, winning_competitor = ?, our_rank = ?,
            total_bidders = ?, award_date = ?, bid_status = ?,
            evaluation_status = 'completed', updated_at = ?
        WHERE id = ?
        ''', (winning_bid_amount, winning_competitor, our_rank, total_bidders,
              award_date, bid_status, datetime.now(), tender_id))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update tender result: {e}", exc_info=True)
        return False


def assign_team_member(tender_id: int, user_id: int, role: str) -> bool:
    """Assign a team member to a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check for existing assignment to avoid duplicates
        cursor.execute('''
        SELECT id FROM tender_team_assignments 
        WHERE tender_id = ? AND user_id = ?
        ''', (tender_id, user_id))
        
        if cursor.fetchone():
            conn.close()
            return True  # Already assigned
        
        cursor.execute('''
        INSERT INTO tender_team_assignments (tender_id, user_id, role, assigned_at)
        VALUES (?, ?, ?, ?)
        ''', (tender_id, user_id, role, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to assign team member: {e}", exc_info=True)
        return False


def get_tender_team(tender_id: int) -> List[tuple]:
    """Get team members assigned to a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT u.id, u.full_name, u.role, ta.role as assigned_role, ta.assigned_at
        FROM tender_team_assignments ta
        JOIN users u ON ta.user_id = u.id
        WHERE ta.tender_id = ? AND ta.is_active = 1
        ORDER BY ta.assigned_at DESC
        ''', (tender_id,))
        
        team = cursor.fetchall()
        conn.close()
        return team
        
    except Exception as e:
        logger.error(f"Failed to fetch tender team: {e}", exc_info=True)
        return []


def add_milestone(tender_id: int, milestone_name: str, due_date: str, 
                 assigned_to: Optional[int], notes: str) -> Optional[int]:
    """Add a milestone/task for a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO tender_milestones (
            tender_id, milestone_name, due_date, assigned_to, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (tender_id, milestone_name, due_date, assigned_to, notes, datetime.now()))
        
        milestone_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return milestone_id
        
    except Exception as e:
        logger.error(f"Failed to add milestone: {e}", exc_info=True)
        return None


def get_tender_milestones(tender_id: int) -> pd.DataFrame:
    """Get milestones for a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT m.*, u.full_name as assigned_to_name
        FROM tender_milestones m
        LEFT JOIN users u ON m.assigned_to = u.id
        WHERE m.tender_id = ? AND m.is_active = 1
        ORDER BY m.due_date ASC, m.completed DESC
        ''', (tender_id,))
        
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Failed to fetch milestones: {e}", exc_info=True)
        return pd.DataFrame()


def add_bid_revision(tender_id: int, bid_amount: float, revised_by: int, reason: str) -> bool:
    """Add bid revision history"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COALESCE(MAX(revision_number), 0) + 1 FROM bid_revisions WHERE tender_id = ?', (tender_id,))
        next_rev = cursor.fetchone()[0]
        
        cursor.execute('''
        INSERT INTO bid_revisions (tender_id, revision_number, bid_amount, revised_by, reason, revised_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (tender_id, next_rev, bid_amount, revised_by, reason, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to add bid revision: {e}", exc_info=True)
        return False


def get_bid_revisions(tender_id: int) -> List[tuple]:
    """Get bid revision history"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT revision_number, bid_amount, revised_by, reason, revised_at
        FROM bid_revisions 
        WHERE tender_id = ?
        ORDER BY revision_number DESC
        ''', (tender_id,))
        
        revisions = cursor.fetchall()
        conn.close()
        return revisions
        
    except Exception as e:
        logger.error(f"Failed to fetch bid revisions: {e}", exc_info=True)
        return []


def update_tender_lock_status(tender_id: int, locked: bool, locked_by: Optional[int] = None) -> bool:
    """Update the lock status of a tender"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE company_tenders 
        SET is_locked = ?, locked_at = ?, locked_by = ?, updated_at = ?
        WHERE id = ?
        ''', (
            1 if locked else 0,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') if locked else None,
            locked_by,
            datetime.now(),
            tender_id
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update tender lock status: {e}", exc_info=True)
        return False

def create_tender_copy(original_tender_id: int, created_by: int) -> Optional[int]:
    """Create a backup copy of a tender with all e-GP fields"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get table structure
        cursor.execute('PRAGMA table_info(company_tenders)')
        cols = [row[1] for row in cursor.fetchall()]
        
        # Fetch original as dict for safe name-based access
        cursor.execute(f'SELECT {", ".join(cols)} FROM company_tenders WHERE id = ?', (original_tender_id,))
        row = cursor.fetchone()
        if not row: return None
        original = dict(zip(cols, row))
        
        # Prepare insert columns (exclude auto-increment ID)
        insert_cols = [c for c in cols if c != 'id']
        placeholders = ', '.join(['?' for _ in insert_cols])
        
        # Build values list
        values = [original.get(c) for c in insert_cols]
        
        # Helper to safely update values by column name
        def set_val(col_name, new_val):
            if col_name in insert_cols:
                values[insert_cols.index(col_name)] = new_val
        
        # Modify copy-specific fields
        set_val('tender_id', f"{original['tender_id']}_COPY")
        set_val('tender_title', f"{original['tender_title']} (Backup Copy)")
        set_val('is_locked', 0)
        set_val('is_copy', 1)
        set_val('original_tender_id', original_tender_id)
        set_val('created_by', created_by)
        set_val('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        set_val('updated_at', None)
        
        # Reset bid/submission/evaluation fields for the copy
        for field in ['bid_submitted_by', 'bid_status', 'our_bid_amount', 
                      'bid_submission_date', 'evaluation_status', 'winning_bid_amount',
                      'winning_competitor', 'our_rank', 'total_bidders', 'award_date']:
            set_val(field, None)
            
        cursor.execute(f'INSERT INTO company_tenders ({", ".join(insert_cols)}) VALUES ({placeholders})', values)
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return new_id
        
    except Exception as e:
        logger.error(f"Failed to create tender copy: {e}", exc_info=True)
        return None
        
def delete_tender(tender_id: int, deleted_by: int) -> bool:
    """Soft delete a tender (mark as inactive)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE company_tenders 
        SET is_active = 0, deleted_at = ?, deleted_by = ?, updated_at = ?
        WHERE id = ?
        ''', (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            deleted_by,
            datetime.now(),
            tender_id
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete tender: {e}", exc_info=True)
        return False


# Attach methods to db instance
db.create_tender = create_tender
db.get_company_tenders = get_company_tenders
db.update_tender_bid = update_tender_bid
db.submit_bid = submit_bid
db.update_tender_result = update_tender_result
db.assign_team_member = assign_team_member
db.get_tender_team = get_tender_team
db.add_milestone = add_milestone
db.get_tender_milestones = get_tender_milestones
db.add_bid_revision = add_bid_revision
db.get_bid_revisions = get_bid_revisions
db.update_tender_lock_status = update_tender_lock_status
db.create_tender_copy = create_tender_copy
db.delete_tender = delete_tender
db.update_tender = update_tender  # ← ADD THIS LINE


# =============================================================================
# 🎨 UI HELPER FUNCTIONS
# =============================================================================

def _render_tender_card(tender_data: pd.Series, key_prefix: str) -> None:
    """Render a single tender as an expandable card"""
    tender_id = int(tender_data['id'])
    title = str(tender_data.get('tender_title', 'Untitled'))[:60]
    entity = str(tender_data.get('procuring_entity', 'N/A'))[:40]
    deadline = tender_data.get('submission_deadline')
    
    # Format deadline
    if deadline:
        deadline_dt = pd.to_datetime(deadline)
        now = datetime.now()
        time_left = deadline_dt - now
        
        if time_left.total_seconds() < 0:
            deadline_badge = "🔴 Overdue"
            deadline_color = "red"
        elif time_left.days == 0:
            hours = time_left.seconds // 3600
            deadline_badge = f"🟠 Due in {hours}h"
            deadline_color = "orange"
        elif time_left.days <= 3:
            deadline_badge = f"🟡 Due in {time_left.days}d"
            deadline_color = "orange"
        else:
            deadline_badge = f"🟢 Due in {time_left.days}d"
            deadline_color = "green"
    else:
        deadline_badge = "📅 No deadline"
        deadline_color = "gray"
    
    # Lock/copy badges
    status_badges = []
    if tender_data.get('is_copy'):
        status_badges.append('<span style="background:#3b82f6;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;">📋 COPY</span>')
    if tender_data.get('is_locked'):
        status_badges.append('<span style="background:#ef4444;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;">🔒 LOCKED</span>')
    
    status_html = ' '.join(status_badges)
    
    with st.expander(f"📌 {title} • {entity} {status_html}", expanded=False):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            our_bid = tender_data.get('our_bid_amount')
            bid_display = f"BDT {our_bid:,.0f}" if our_bid and our_bid > 0 else "Not set"
            
            st.markdown(f"""
            - **Tender ID:** {tender_data.get('tender_id', 'N/A')}
            - **Official Estimate:** BDT {tender_data.get('official_estimate', 0):,.0f}
            - **Our Bid:** {bid_display}
            """)
        
        with col2:
            st.markdown(f"#### ⏰ Time Remaining")
            st.markdown(f"<h3 style='color:{deadline_color};margin:0;'>{deadline_badge}</h3>", unsafe_allow_html=True)
            if deadline:
                st.caption(f"Deadline: {pd.to_datetime(deadline).strftime('%Y-%m-%d %H:%M')}")
        
        with col3:
            bid_status = str(tender_data.get('bid_status', 'draft')).upper()
            status_color = {"WON": "green", "LOST": "red", "SUBMITTED": "orange", "DRAFT": "gray"}.get(bid_status, "gray")
            st.markdown(f"**Status:** <span style='color:{status_color}'>{bid_status}</span>", unsafe_allow_html=True)
            if tender_data.get('submitted_by_name'):
                st.caption(f"By: {tender_data['submitted_by_name']}")
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Edit bid
            current_bid = float(tender_data.get('our_bid_amount', 0) or 0)
            new_bid = st.number_input("Edit Bid (BDT)", value=current_bid, step=100000.0, format="%.0f", key=f"{key_prefix}_bid_{tender_id}")
            if st.button("💾 Save", key=f"{key_prefix}_save_{tender_id}", use_container_width=True):
                if new_bid != current_bid:
                    if db.update_tender_bid(tender_id, new_bid, st.session_state.user_id):
                        st.success(f"Bid updated to BDT {new_bid:,.0f}")
                        st.rerun()
                    else:
                        st.error("Failed to update bid")
        
        with col2:
            # Submit bid
            if current_bid > 0 and tender_data.get('bid_status') != 'submitted':
                if st.button("📤 Submit", key=f"{key_prefix}_submit_{tender_id}", use_container_width=True):
                    if db.submit_bid(tender_id, current_bid, st.session_state.user_id):
                        st.success("Bid submitted!")
                        st.rerun()
            elif tender_data.get('bid_status') == 'submitted':
                st.success("✅ Submitted")
            else:
                st.warning("Set bid first")
        
        with col3:
            # Team management
            if st.button("👥 Team", key=f"{key_prefix}_team_{tender_id}", use_container_width=True):
                _render_team_management(tender_id, key_prefix)
        
        with col4:
            # Lock/unlock (admin only)
            if st.session_state.user_role == 'admin':
                is_locked = bool(tender_data.get('is_locked', False))
                btn_text = "🔓 Unlock" if is_locked else "🔒 Lock"
                btn_type = "secondary" if is_locked else "primary"
                if st.button(btn_text, key=f"{key_prefix}_lock_{tender_id}", use_container_width=True, type=btn_type):
                    if db.update_tender_lock_status(tender_id, not is_locked, st.session_state.user_id):
                        st.success(f"Tender {'unlocked' if is_locked else 'locked'}")
                        st.rerun()


def _render_team_management(tender_id: int, key_prefix: str) -> None:
    """Render team assignment UI in expander"""
    team = db.get_tender_team(tender_id)
    
    if team:
        st.markdown("**Current Team:**")
        for member in team:
            st.markdown(f"- {member[1]} • {member[3]}")
    
    # Add new member
    st.markdown("**Add Member:**")
    users = db.get_all_users(company_id=st.session_state.company_id)
    user_options = {f"{u[3]} ({u[5]})": u[0] for u in users} if users else {}
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_member = st.selectbox("Member", ["Select"] + list(user_options.keys()), key=f"{key_prefix}_add_member_{tender_id}")
    with col2:
        role = st.selectbox("Role", ["Bid Manager", "Technical Lead", "Financial", "Legal", "Support"], key=f"{key_prefix}_add_role_{tender_id}")
    with col3:
        if st.button("➕ Add", key=f"{key_prefix}_add_btn_{tender_id}"):
            if new_member != "Select" and new_member in user_options:
                if db.assign_team_member(tender_id, user_options[new_member], role):
                    st.success("Member added!")
                    st.rerun()


def _render_milestones(tender_id: int, key_prefix: str) -> None:
    """Render milestone management UI"""
    milestones = db.get_tender_milestones(tender_id)
    
    if not milestones.empty:
        st.markdown("**Milestones:**")
        for _, m in milestones.iterrows():
            icon = "✅" if m.get('completed') else "⏳"
            color = "green" if m.get('completed') else "orange"
            st.markdown(f"- {icon} <span style='color:{color}'>{m['milestone_name']}</span> • Due: {m['due_date'][:10]}", unsafe_allow_html=True)
    
    # Add milestone
    with st.expander("➕ Add Milestone"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Milestone Name", key=f"{key_prefix}_milestone_name_{tender_id}")
            due = st.date_input("Due Date", value=datetime.now() + timedelta(days=7), key=f"{key_prefix}_milestone_due_{tender_id}")
        with col2:
            users = db.get_all_users(company_id=st.session_state.company_id)
            user_options = {f"{u[3]} ({u[5]})": u[0] for u in users} if users else {}
            assigned = st.selectbox("Assign To", ["Select"] + list(user_options.keys()), key=f"{key_prefix}_milestone_assign_{tender_id}")
            notes = st.text_area("Notes", key=f"{key_prefix}_milestone_notes_{tender_id}")
        
        if st.button("Add Milestone", key=f"{key_prefix}_milestone_add_{tender_id}"):
            if name and assigned != "Select":
                assigned_id = user_options[assigned] if assigned in user_options else None
                if db.add_milestone(tender_id, name, due.strftime('%Y-%m-%d'), assigned_id, notes):
                    st.success("Milestone added!")
                    st.rerun()

def render_tender_management() -> None:
    """Main tender management dashboard with RBAC"""
    
    # Render role badge
    render_role_badge()
    st.markdown("---")
    
    # Check if user can view tenders
    if not can_view_tenders():
        st.error("🔒 You don't have permission to view tenders.")
        return
    
    # Create base tabs
    tabs = st.tabs(["📊 Dashboard", "📋 Active Tenders", "🏆 Awarded Tenders"])
    tab_idx = 0
    
    # Dashboard tab
    with tabs[tab_idx]:
        _render_tender_dashboard()
    tab_idx += 1
    
    # Active Tenders tab
    with tabs[tab_idx]:
        _render_active_tenders_table()
    tab_idx += 1
    
    # Awarded Tenders tab
    with tabs[tab_idx]:
        _render_awarded_tenders_table()
    tab_idx += 1
    
    # Add extra tabs conditionally after the main ones
    extra_tabs = []
    extra_contents = []
    
    if can_create_tender():
        extra_tabs.append("➕ New/Edit Tender")
        extra_contents.append(_render_create_tender_form)
    
    if can_export_data():
        extra_tabs.append("📑 Reports")
        extra_contents.append(_render_tender_reports)
    
    if extra_tabs:
        # Create additional tabs
        more_tabs = st.tabs(extra_tabs)
        for i, (tab, content_func) in enumerate(zip(more_tabs, extra_contents)):
            with tab:
                content_func()


def _render_tender_dashboard() -> None:
    """Dashboard with statistics - NO inline editing"""
    st.markdown("### 📊 Tender Statistics")
    tenders_df = db.get_company_tenders(st.session_state.company_id)
    
    if tenders_df.empty:
        st.info("📭 No tenders yet. Create your first tender entry!")
        return
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Tenders", len(tenders_df))
    with col2: st.metric("Active Bids", len(tenders_df[tenders_df['bid_status'] == 'submitted']))
    with col3: st.metric("Won Tenders", len(tenders_df[tenders_df['bid_status'] == 'won']))
    with col4: 
        total = len(tenders_df)
        won = len(tenders_df[tenders_df['bid_status'] == 'won'])
        st.metric("Win Rate", f"{(won/total*100) if total>0 else 0:.0f}%")
    
    # ⏰ Upcoming Deadlines (View-only, no edit buttons)
    st.markdown("### ⏰ Upcoming Deadlines")
    
    tenders_df['deadline_dt'] = pd.to_datetime(tenders_df['submission_deadline'], errors='coerce')
    now = pd.Timestamp.now()
    
    upcoming = tenders_df[
        (tenders_df['deadline_dt'] > now) & 
        (tenders_df['deadline_dt'].notna())
    ].sort_values('deadline_dt').head(5)
    
    if not upcoming.empty:
        display_df = upcoming[[
            'tender_id', 'tender_title', 'procuring_entity', 
            'procurement_type', 'submission_deadline', 'bid_status'
        ]].copy()
        
        display_df['submission_deadline'] = pd.to_datetime(display_df['submission_deadline'], errors='coerce')
        display_df['days_left'] = (display_df['submission_deadline'] - now).dt.days
        display_df['submission_deadline'] = display_df['submission_deadline'].dt.strftime('%d %b %Y').fillna('N/A')
        display_df['bid_status'] = display_df['bid_status'].str.upper()
        
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "tender_id": "Tender ID",
                "tender_title": st.column_config.TextColumn("Tender Title", width="large"),
                "procuring_entity": "Procuring Entity",
                "procurement_type": "Type",
                "submission_deadline": "Deadline",
                "days_left": st.column_config.NumberColumn("Days Left", format="%d"),
                "bid_status": "Status"
            }
        )
    else:
        st.success("✅ No upcoming deadlines! All caught up.")
    
    # 📝 Recent Activities
    st.markdown("### 📝 Recent Activities")
    if 'updated_at' in tenders_df.columns:
        recent = tenders_df.sort_values('updated_at', ascending=False).head(5)
        for _, t in recent.iterrows():
            updated_str = str(t['updated_at'])[:10] if pd.notna(t['updated_at']) else 'Unknown'
            st.markdown(f"- **`{t['tender_id']}`** • {str(t['tender_title'])[:50]}... • `{t['bid_status'].upper()}` • Updated: {updated_str}")

def _render_tender_detail_view(tender_data: Dict[str, Any], is_editable: bool = False, context: str = "default") -> None:
    """Display tender details in read-only format
    
    Args:
        tender_data: Tender data dictionary
        is_editable: Whether to show edit button
        context: Context prefix ('active', 'awarded', etc.) to ensure unique keys
    """
    st.markdown("### 📋 Tender Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Basic Information")
        st.info(f"**Tender ID:** `{tender_data.get('tender_id', 'N/A')}`")
        st.markdown(f"**Title:** {tender_data.get('tender_title', 'N/A')}")
        st.markdown(f"**Procuring Entity:** {tender_data.get('procuring_entity', 'N/A')}")
        st.markdown(f"**Division:** {tender_data.get('division', 'N/A')}")
        st.markdown(f"**District:** {tender_data.get('district', 'N/A')}")
        st.markdown(f"**Procurement Type:** {tender_data.get('procurement_type', 'N/A').upper()}")
    
    with col2:
        st.markdown("#### Financial Information")
        st.info(f"**Official Estimate:** BDT {tender_data.get('official_estimate', 0):,.0f}")
        st.markdown(f"**Tender Security:** BDT {tender_data.get('tender_security', 0):,.0f}")
        st.markdown(f"**Document Fee:** BDT {tender_data.get('document_fee', 0):,.0f}")
        st.markdown(f"**Our Bid:** BDT {tender_data.get('our_bid_amount', 0):,.0f}" if tender_data.get('our_bid_amount') else "**Our Bid:** Not set")
    
    st.markdown("#### Important Dates")
    col1, col2, col3 = st.columns(3)
    with col1:
        deadline = tender_data.get('submission_deadline')
        if deadline:
            try:
                deadline_dt = datetime.strptime(str(deadline)[:10], '%Y-%m-%d') if isinstance(deadline, str) else deadline
                st.markdown(f"**Submission Deadline:** {deadline_dt.strftime('%d %b %Y %H:%M')}")
            except:
                st.markdown(f"**Submission Deadline:** {deadline}")
    with col2:
        pub_date = tender_data.get('tender_publication_date')
        if pub_date:
            try:
                pub_dt = datetime.strptime(str(pub_date)[:10], '%Y-%m-%d') if isinstance(pub_date, str) else pub_date
                st.markdown(f"**Published:** {pub_dt.strftime('%d %b %Y')}")
            except:
                st.markdown(f"**Published:** {pub_date}")
    with col3:
        st.markdown(f"**Status:** `{tender_data.get('bid_status', 'N/A').upper()}`")
        if tender_data.get('is_locked'):
            st.warning("🔒 **LOCKED**")
    
    # Team Members
    if tender_data.get('id'):
        st.markdown("#### 👥 Team Assignment")
        team = db.get_tender_team(tender_data['id'])
        if team:
            team_cols = st.columns(3)
            for i, member in enumerate(team):
                user_id, full_name, user_role, assigned_role, assigned_at = member
                team_cols[i % 3].info(f"**{assigned_role}:** {full_name}")
        else:
            st.caption("No team members assigned")
    
    # Notes
    if tender_data.get('notes'):
        st.markdown("#### 📝 Notes")
        st.caption(tender_data.get('notes'))
    
    # Action buttons with UNIQUE keys
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        # ✅ Unique key with context prefix
        if st.button("← Back to List", width="stretch", key=f"{context}_back_{tender_data.get('id', 'unknown')}"):
            st.session_state.view_tender_detail = None
            st.rerun()
    
    with col2:
        if is_editable and not tender_data.get('is_locked'):
            # ✅ Unique key with context prefix
            if st.button("✏️ Edit This Tender", width="stretch", type="primary", 
                        key=f"{context}_edit_{tender_data.get('id', 'unknown')}"):
                st.session_state.edit_tender_id = tender_data['id']
                st.session_state.extracted_data = tender_data
                st.session_state.edit_mode = True
                st.session_state.view_tender_detail = None
                st.rerun()

def _render_active_tenders_table() -> None:
    """Display active tenders with multi-line rows, robust dates, and compact actions"""
    st.markdown("### 📋 Active Tenders")
    
    # ✅ ADD REFRESH BUTTON HERE - Right after the header, before the table
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_active_tenders"):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")

    tenders_df = db.get_company_tenders(st.session_state.company_id)
    if tenders_df.empty:
        st.info("📭 No active tenders")
        return
    
    active = tenders_df[tenders_df['bid_status'].isin(['draft', 'submitted', 'pending'])].copy()
    if active.empty:
        st.info("📭 No active tenders currently active.")
        return
    
    # 🔍 Robust Date Parsing (Tries multiple columns if submission_deadline is empty)
    def safe_parse_date(row):
        for col in ['submission_deadline', 'security_submission_deadline', 'tender_valid_upto']:
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                try:
                    return pd.to_datetime(val)
                except Exception:
                    pass
        return pd.NaT

    active['deadline_dt'] = active.apply(safe_parse_date, axis=1)
    now = pd.Timestamp.now()
    
    # 📏 Column Ratios: ID, Title(wide), Entity, Type, Deadline, Left, Lock, Bid/Save, View
    col_ratios = [0.6, 4.5, 2.2, 0.6, 1.1, 0.6, 0.4, 2.8, 0.8]
    
    # 📑 Header
    h_cols = st.columns(col_ratios)
    headers = ["ID", "Tender Title & Description", "Procuring Entity", "Type", "Deadline", "Left", "🔒", "Bid / Action", "View"]
    for i, h in enumerate(headers):
        h_cols[i].markdown(f"**{h}**")
    st.divider()
    
    # 🔄 Render Each Tender (Multi-line rows)
    for _, row in active.iterrows():
        is_locked = bool(row.get('is_locked', False))
        tender_id = str(row.get('tender_id', 'N/A'))
        title = str(row.get('tender_title', ''))  # ✅ No truncation: allows multi-line wrap
        entity = str(row.get('procuring_entity', 'N/A'))
        proc_type = str(row.get('procurement_type', '')).upper()
        deadline = row['deadline_dt']
        current_bid = float(row.get('our_bid_amount', 0) or 0.0)
        
        if pd.notna(deadline):
            days_left = (deadline - now).days
            deadline_str = deadline.strftime('%d %b %Y')
        else:
            days_left = None
            deadline_str = "Not set"
            
        cols = st.columns(col_ratios)
        
        cols[0].code(tender_id, language=None)
        cols[1].markdown(f"**{title}**")  # ✅ Wraps naturally
        cols[2].caption(entity)
        cols[3].caption(proc_type)
        cols[4].caption(deadline_str)
        cols[5].markdown(f"`{days_left}d`" if days_left is not None else "`--`")
        cols[6].markdown("🔒" if is_locked else "🔓")
        
        # 💰 Bid Input & Save Button (Side-by-side)
        if not is_locked:
            with cols[7]:
                bid_in, act_btn = st.columns([2.5, 1])
                new_bid = bid_in.number_input(
                    "Bid", value=current_bid, min_value=0.0, step=100000.0,
                    format="%.3f", key=f"bid_{row['id']}", label_visibility="collapsed"
                )
                
                if new_bid != current_bid:
                    if act_btn.button("💾", key=f"save_{row['id']}", width="stretch"):
                        if db.update_tender_bid(row['id'], new_bid, st.session_state.user_id):
                            st.toast("💰 Bid saved!", icon="✅")
                            st.rerun()
                elif current_bid > 0 and row['bid_status'] != 'submitted':
                    if act_btn.button("📤", key=f"sub_{row['id']}", type="primary", width="stretch"):
                        if db.submit_bid(row['id'], new_bid, st.session_state.user_id):
                            st.toast("📤 Submitted!", icon="✅")
                            st.rerun()
                elif row['bid_status'] == 'submitted':
                    act_btn.success("✅")
        else:
            cols[7].caption("Locked")
            
        # 👁️ View Button
        if cols[8].button("👁️", key=f"view_{row['id']}", width="stretch"):
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM company_tenders WHERE id = ?", (int(row['id']),))
                c_list = [desc[0] for desc in cursor.description]
                r = cursor.fetchone()
                conn.close()
                if r:
                    st.session_state.view_tender_detail = dict(zip(c_list, r))
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Load failed: {str(e)}")
                
        st.divider()
        
def _render_awarded_tenders_table() -> None:
    """Display awarded tenders with multi-line rows and view option"""
    
    if st.session_state.get('view_tender_detail'):
        _render_tender_detail_view(st.session_state.view_tender_detail, is_editable=False, context="awarded")
        return

    st.markdown("### 🏆 Awarded Tenders")
    
    tenders_df = db.get_company_tenders(st.session_state.company_id)
    if tenders_df.empty:
        st.info("📭 No tenders found")
        return
    
    awarded = tenders_df[(tenders_df['bid_status'] == 'won') & (tenders_df['is_active'] == 1)].copy()
    if awarded.empty:
        st.info("📭 No awarded tenders yet")
        return
    
    awarded['award_date_dt'] = pd.to_datetime(awarded['award_date'], errors='coerce')
    
    # 📏 Column Ratios: ID, Title(wide), Entity, Type, Estimate, Our Bid, Winning Bid, Award Date, Rank, Result, View
    col_ratios = [0.6, 4.5, 2.2, 0.6, 1.2, 1.2, 1.2, 1.1, 0.8, 1.2, 0.8]
    
    # 📑 Header
    h_cols = st.columns(col_ratios)
    headers = ["ID", "Tender Title", "Procuring Entity", "Type", "Estimate", "Our Bid", "Winning Bid", "Award Date", "Rank", "Result", "View"]
    for i, h in enumerate(headers):
        h_cols[i].markdown(f"**{h}**")
    st.divider()
    
    for _, row in awarded.iterrows():
        tender_id = str(row.get('tender_id', 'N/A'))
        title = str(row.get('tender_title', ''))  # ✅ Multi-line wrap enabled
        entity = str(row.get('procuring_entity', 'N/A'))
        proc_type = str(row.get('procurement_type', '')).upper()
        
        estimate = f"BDT {row['official_estimate']:,.0f}" if pd.notna(row['official_estimate']) else "N/A"
        our_bid = f"BDT {row['our_bid_amount']:,.0f}" if pd.notna(row['our_bid_amount']) and row['our_bid_amount'] > 0 else "N/A"
        winning_bid = f"BDT {row['winning_bid_amount']:,.0f}" if pd.notna(row['winning_bid_amount']) else "N/A"
        award_date = row['award_date_dt'].strftime('%d %b %Y') if pd.notna(row['award_date_dt']) else 'N/A'
        result = "🎉 WINNER" if row['our_rank'] == 1 else f"Rank #{int(row['our_rank'])}" if pd.notna(row['our_rank']) else "N/A"
        
        cols = st.columns(col_ratios)
        
        cols[0].code(tender_id, language=None)
        cols[1].markdown(f"**{title}**")
        cols[2].caption(entity)
        cols[3].caption(proc_type)
        cols[4].caption(estimate)
        cols[5].caption(our_bid)
        cols[6].caption(winning_bid)
        cols[7].caption(award_date)
        cols[8].markdown(f"`{row['our_rank'] if pd.notna(row['our_rank']) else '--'}`")
        cols[9].markdown(f"`{result}`")
        
        if cols[10].button("👁️", key=f"view_awarded_{row['id']}", width="stretch"):
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM company_tenders WHERE id = ?", (int(row['id']),))
                c_list = [desc[0] for desc in cursor.description]
                r = cursor.fetchone()
                conn.close()
                if r:
                    st.session_state.view_tender_detail = dict(zip(c_list, r))
                    st.toast("📋 Loading tender details...", icon="👁️")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to load details: {str(e)}")
                
        st.divider()
    
    # 📥 Export
    csv = awarded.to_csv(index=False)
    st.download_button(
        "📥 Export Awarded Tenders (CSV)",
        data=csv,
        file_name=f"awarded_tenders_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        width="stretch"
    )
    
def _load_tender_for_edit(tender_id: int) -> None:
    """Helper to load tender data and prepare for editing"""
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM company_tenders WHERE id = ?", (tender_id,))
        cols = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        logger.debug(f"🔍 Load Tender #{tender_id} | Row found: {bool(row)} | Cols: {len(cols)}")
        if row: logger.debug(f"📦 Keys set: {list(dict(zip(cols, row)).keys())}")
        conn.close()
        
        if row:
            st.session_state.extracted_data = dict(zip(cols, row))
            st.session_state.skip_review = True
            st.session_state.edit_tender_id = tender_id
            
            # Clear stale form state
            for k in list(st.session_state.keys()):
                if k.startswith('form_') or k in ('_form_submitting', '_form_reset', '_tender_pdf_upload'):
                    del st.session_state[k]
            
            st.toast(f"📝 Tender #{tender_id} loaded. Please click '➕ New/Edit Tender' tab.", icon="✏️")
            
            #st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to load tender: {str(e)}")

def _render_create_tender_form() -> None:
    """New/Edit Tender page with 3 modes: Manual, PDF Upload, or Edit Existing"""
    
    # =========================================================================
    # SESSION STATE INITIALIZATION
    # =========================================================================
    current_mode = st.session_state.get('tender_action_mode', '➕ Create New Tender (Manual)')
    if st.session_state.get('last_mode') != current_mode:
        # Mode changed - clear extracted data
        st.session_state.extracted_data = None
        st.session_state.skip_review = False
        st.session_state._last_pdf_name = None
        st.session_state.last_mode = current_mode

    if 'extracted_data' not in st.session_state: 
        st.session_state.extracted_data = None
    if 'skip_review' not in st.session_state: 
        st.session_state.skip_review = False
    if 'edit_mode' not in st.session_state: 
        st.session_state.edit_mode = False
    if 'edit_tender_id' not in st.session_state: 
        st.session_state.edit_tender_id = None
    if 'tender_action_mode' not in st.session_state:
        st.session_state.tender_action_mode = "➕ Create New Tender (Manual)"

    # =========================================================================
    # MODE SELECTION
    # =========================================================================
    st.markdown("### 📝 Create / Edit Tender")
    
    mode = st.radio(
        "Select Action:",
        options=["➕ Create New Tender (Manual)", "📄 Create from PDF Upload", "✏️ Edit Existing Tender"],
        horizontal=True,
        key="tender_action_mode"
    )
    
    # =========================================================================
    # EDIT EXISTING TENDER MODE
    # =========================================================================
    if mode == "✏️ Edit Existing Tender":
        st.markdown("### 🔍 Search & Select Tender to Edit")
        
        # Search filters
        col1, col2, col3 = st.columns(3)
        with col1:
            search_tender_id = st.text_input("Tender ID", key="search_tid")
        with col2:
            search_title = st.text_input("Tender Title (partial)", key="search_title")
        with col3:
            search_entity = st.text_input("Procuring Entity", key="search_entity")
        
        # Fetch tenders
        all_tenders = db.get_company_tenders(st.session_state.company_id)
        
        if not all_tenders.empty:
            filtered = all_tenders.copy()
            if search_tender_id:
                filtered = filtered[filtered['tender_id'].str.contains(search_tender_id, case=False, na=False)]
            if search_title:
                filtered = filtered[filtered['tender_title'].str.contains(search_title, case=False, na=False)]
            if search_entity:
                filtered = filtered[filtered['procuring_entity'].str.contains(search_entity, case=False, na=False)]
            
            if not filtered.empty:
                # Show tender list
                for idx, row in filtered.iterrows():
                    col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
                    with col1:
                        st.write(row['tender_id'])
                    with col2:
                        st.write(row['tender_title'][:50])
                    with col3:
                        st.write(row['procuring_entity'][:30])
                    with col4:
                        if st.button("✏️ Edit", key=f"edit_btn_{row['id']}"):
                            # Load tender data directly into session state
                            conn = db.get_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT * FROM company_tenders WHERE id = ?", (row['id'],))
                            cols = [desc[0] for desc in cursor.description]
                            tender_row = cursor.fetchone()
                            conn.close()
                            
                            if tender_row:
                                st.session_state.extracted_data = dict(zip(cols, tender_row))
                                st.session_state.edit_mode = True
                                st.session_state.edit_tender_id = row['id']
                                st.session_state.skip_review = True
                                st.rerun()
                    st.markdown("---")
        
        # Show edit form if in edit mode
        if st.session_state.edit_mode and st.session_state.extracted_data:
            _render_tender_form_with_data(editing=True)
        return
    
    # =========================================================================
    # PDF UPLOAD MODE
    # =========================================================================
    elif mode == "📄 Create from PDF Upload":
        st.markdown("### 📄 Upload Tender Notice (PDF)")
        
        uploaded_pdf = st.file_uploader("Choose PDF file", type=['pdf'], key="pdf_uploader")
        
        if uploaded_pdf:
            if st.session_state.extracted_data is None or st.session_state.get('last_pdf') != uploaded_pdf.name:
                try:
                    from modules.pdf_parser import parse_tender_pdf
                    with st.spinner("🔍 Parsing PDF..."):
                        parsed = parse_tender_pdf(uploaded_pdf)
                    if parsed:
                        st.session_state.extracted_data = parsed
                        st.session_state.last_pdf = uploaded_pdf.name
                        st.session_state.skip_review = False
                        st.success("✅ PDF parsed successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        # Show review
        if st.session_state.extracted_data and not st.session_state.skip_review:
            from modules.pdf_review import display_review_page
            def confirm_review():
                st.session_state.skip_review = True
                st.rerun()
            display_review_page(st.session_state.extracted_data, confirm_review)
            return
        
        # Show form
        if st.session_state.extracted_data and st.session_state.skip_review:
            _render_tender_form_with_data(editing=False)
        else:
            _render_tender_form_with_data(editing=False)
        return
    
    # =========================================================================
    # MANUAL MODE
    # =========================================================================
    else:
        _render_tender_form_with_data(editing=False)


def _render_tender_form_with_data(editing: bool = False):
    """Render tender form with data from session_state.extracted_data"""
    
    from utils.helpers import format_currency_bd
    
    # Get data source
    data = st.session_state.extracted_data if editing else st.session_state.get('extracted_data', {})
    
    # Set default values with proper types
    default_values = {
        'tender_id': str(data.get('tender_id', '')) if data else '',
        'tender_title': str(data.get('tender_title', '')) if data else '',
        'procuring_entity': str(data.get('procuring_entity', '')) if data else '',
        'division': str(data.get('division', 'Dhaka')) if data else 'Dhaka',
        'procurement_type': str(data.get('procurement_type', 'works')) if data else 'works',
        'official_estimate': float(data.get('official_estimate', 0.0)) if data else 0.0,
        'submission_deadline': data.get('submission_deadline', datetime.now().date()) if data else datetime.now().date(),
        'tender_security': float(data.get('tender_security', 0.0)) if data else 0.0,
        'document_fee': float(data.get('document_fee', 0.0)) if data else 0.0,
        'project_code': str(data.get('project_code', '')) if data else '',
        'project_name': str(data.get('project_name', '')) if data else '',
        'package_no': str(data.get('package_no', '')) if data else '',
        'budget_type': str(data.get('budget_type', 'Development')) if data else 'Development',
        'notes': str(data.get('notes', '')) if data else ''
    }
    
    # Show edit header with Cancel button
    if editing:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.success(f"📝 **Editing Tender #{st.session_state.edit_tender_id}**")
            st.info("💡 Modify the fields below and click '💾 Update Tender' to save changes.")
        with col2:
            # ✅ Cancel button outside form - direct action
            if st.button("❌ Cancel Edit", key="cancel_edit_btn", use_container_width=True):
                st.session_state.edit_mode = False
                st.session_state.edit_tender_id = None
                st.session_state.extracted_data = None
                st.session_state.skip_review = False
                st.rerun()

    
    # Display current data summary if available
    if default_values['official_estimate'] > 0:
        st.info(f"💰 Current Estimate: {format_currency_bd(default_values['official_estimate'])}")
    
    # Main form
    with st.form("tender_form", clear_on_submit=False):
        st.markdown("### 📝 Core Tender Details")
        col1, col2 = st.columns(2)
        
        with col1:
            tender_id = st.text_input("Tender ID *", value=default_values['tender_id'], key="form_tender_id")
            tender_title = st.text_area("Tender Title *", value=default_values['tender_title'], height=80, key="form_tender_title")
            procuring_entity = st.text_input("Procuring Entity *", value=default_values['procuring_entity'], key="form_procuring_entity")
            divisions = ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
            division_index = divisions.index(default_values['division']) if default_values['division'] in divisions else 0
            division = st.selectbox("Division", divisions, index=division_index, key="form_division")
        
        with col2:
            valid_pt = ["works", "goods", "services"]
            pt_index = valid_pt.index(default_values['procurement_type']) if default_values['procurement_type'] in valid_pt else 0
            procurement_type = st.selectbox("Procurement Type", valid_pt, index=pt_index, key="form_procurement_type")
            
            official_estimate = st.number_input(
                "Official Estimate (BDT) *", 
                min_value=0.0,
                step=1000000.0,
                value=default_values['official_estimate'],
                key="form_official_estimate",
                format="%0.3f"
            )
            
            submission_deadline = st.date_input("Submission Deadline *", value=default_values['submission_deadline'], key="form_deadline")
            
            tender_security = st.number_input(
                "Tender Security (BDT)", 
                min_value=0.0,
                step=10000.0,
                value=default_values['tender_security'],
                key="form_security",
                format="%0.3f"
            )
            
            document_fee = st.number_input(
                "Document Fee (BDT)", 
                min_value=0.0,
                step=500.0,
                value=default_values['document_fee'],
                key="form_doc_fee",
                format="%0.3f"
            )
        
        with st.expander("📝 Additional Information", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                project_code = st.text_input("Project Code", value=default_values['project_code'], key="form_project_code")
                package_no = st.text_input("Package No.", value=default_values['package_no'], key="form_package_no")
                budget_type = st.text_input("Budget Type", value=default_values['budget_type'], key="form_budget_type")
            with col2:
                project_name = st.text_area("Project Name", value=default_values['project_name'], height=60, key="form_project_name")
                notes = st.text_area("Notes", value=default_values['notes'], height=60, key="form_notes")
        
        # Display formatted values for preview
        if official_estimate > 0:
            st.caption(f"💡 Formatted estimate: {format_currency_bd(official_estimate)}")
        
        # Submit button
        btn_text = "💾 Update Tender" if editing else "🚀 Create Tender"
        submitted = st.form_submit_button(btn_text, use_container_width=True, type="primary")
        
        # Cancel button inside form (for manual mode)
        if not editing:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col2:
                if st.form_submit_button("🗑️ Clear Form", use_container_width=True):
                    st.session_state.extracted_data = None
                    st.session_state.skip_review = False
                    st.session_state._last_pdf_name = None
                    st.rerun()
        
        if submitted:
            # Validate
            if not all([tender_id, tender_title, procuring_entity, official_estimate > 0]):
                st.error("❌ Please fill all required fields marked with *")
                return
            
            tender_data = {
                'tender_id': tender_id,
                'tender_title': tender_title,
                'procuring_entity': procuring_entity,
                'division': division,
                'procurement_type': procurement_type,
                'official_estimate': official_estimate,
                'submission_deadline': submission_deadline,
                'tender_security': tender_security,
                'document_fee': document_fee,
                'project_code': project_code,
                'project_name': project_name,
                'package_no': package_no,
                'budget_type': budget_type,
                'notes': notes,
                'is_active': 1
            }
            
            if editing:
                # Update existing tender
                success = db.update_tender(st.session_state.edit_tender_id, tender_data, st.session_state.user_id)

                if success:
                    st.success(f"✅ Tender updated successfully!")
                    st.balloons()
                    # Clear edit session states
                    for key in ['edit_mode', 'edit_tender_id', 'extracted_data', 'skip_review', '_last_pdf_name']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
                else:
                    st.error("❌ Failed to update tender")
            else:
                # Create new tender
                tender_db_id = db.create_tender(st.session_state.company_id, tender_data, st.session_state.user_id)
                if tender_db_id:
                    st.success(f"✅ Tender '{tender_title}' created successfully!")
                    st.balloons()
                    
                    # CRITICAL: Clear ALL PDF and form related session state
                    keys_to_clear = ['extracted_data', 'skip_review', '_last_pdf_name', '_tender_pdf_upload_new']
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    # Force a complete page reset without modifying radio button
                    st.rerun()
                else:
                    st.error("❌ Failed to create tender")


# When fetching active tenders, ensure you're getting all including newly created
def get_active_tenders(company_id):
    """Get all active tenders for a company"""
    query = """
    SELECT * FROM company_tenders 
    WHERE company_id = ? AND is_active = 1 
    ORDER BY submission_deadline ASC
    """
    # Make sure there's no status filter like bid_status = 'draft' only
    # The newly created tender with ID 1283428 should appear here

def _render_create_tender_form_bak() -> None:
    """New/Edit Tender page with 3 modes: Manual, PDF Upload, or Edit Existing"""
    
    # =========================================================================
    # 1️⃣ SESSION STATE INITIALIZATION
    # =========================================================================
    if 'extracted_data' not in st.session_state: st.session_state.extracted_data = None
    if 'skip_review' not in st.session_state: st.session_state.skip_review = False
    if '_form_submitting' not in st.session_state: st.session_state._form_submitting = False
    if '_form_reset' not in st.session_state: st.session_state._form_reset = False
    if 'edit_tender_id' not in st.session_state: st.session_state.edit_tender_id = None
    if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
    if 'last_mode' not in st.session_state: st.session_state.last_mode = None
    
    # ✅ FIX 1: Detect mode change and reset extracted_data
    current_mode = st.session_state.get('tender_action_mode', '➕ Create New Tender (Manual)')
    if st.session_state.last_mode != current_mode and st.session_state.last_mode is not None:
        # Mode changed - clear extracted data
        st.session_state.extracted_data = None
        st.session_state.skip_review = False
        st.session_state.edit_mode = False
        st.session_state.edit_tender_id = None
    st.session_state.last_mode = current_mode
    
    # Handle form reset
    if st.session_state.get('_form_reset'):
        keys_to_clear = [k for k in st.session_state.keys() if k.startswith('form_')] + \
                        ['extracted_data', 'skip_review', '_form_submitting', '_form_reset', 'edit_tender_id', 'edit_mode', '_tender_pdf_upload']
        for k in keys_to_clear:
            if k in st.session_state: del st.session_state[k]
        st.rerun()
    
    # ✅ FIX 2: Define 'extracted' and 'is_editing' HERE
    extracted = st.session_state.extracted_data or {}
    is_editing = st.session_state.get('edit_mode', False) and bool(extracted.get('id'))
    
    # =========================================================================
    # 2️⃣ MODE SELECTION (Manual / PDF / Edit Existing)
    # =========================================================================
    st.markdown("### 📝 Create / Edit Tender")
    
    mode = st.radio(
        "Select Action:",
        options=["➕ Create New Tender (Manual)", "📄 Create from PDF Upload", "✏️ Edit Existing Tender"],
        horizontal=True,
        key="tender_action_mode"
    )
    
    # =========================================================================
    # 3️⃣ EDIT EXISTING TENDER - SEARCH & SELECT
    # =========================================================================
    if mode == "✏️ Edit Existing Tender":
        st.markdown("### 🔍 Search & Select Tender to Edit")
        
        # Search filters
        col1, col2, col3 = st.columns(3)
        with col1:
            search_tender_id = st.text_input("Tender ID", key="search_tid")
        with col2:
            search_title = st.text_input("Tender Title (partial)", key="search_title")
        with col3:
            search_entity = st.text_input("Procuring Entity", key="search_entity")
        
        # Fetch and filter tenders
        all_tenders = db.get_company_tenders(st.session_state.company_id)
        
        if not all_tenders.empty:
            # Apply filters
            filtered = all_tenders.copy()
            if search_tender_id:
                filtered = filtered[filtered['tender_id'].str.contains(search_tender_id, case=False, na=False)]
            if search_title:
                filtered = filtered[filtered['tender_title'].str.contains(search_title, case=False, na=False)]
            if search_entity:
                filtered = filtered[filtered['procuring_entity'].str.contains(search_entity, case=False, na=False)]
            
            if not filtered.empty:
                # Display selection table
                display_df = filtered[[
                    'id', 'tender_id', 'tender_title', 'procuring_entity', 
                    'procurement_type', 'submission_deadline', 'bid_status', 'is_locked'
                ]].copy()
                
                display_df['submission_deadline'] = pd.to_datetime(display_df['submission_deadline'], errors='coerce').dt.strftime('%d %b %Y')
                display_df['locked'] = display_df['is_locked'].apply(lambda x: "🔒 Locked" if x else "🔓 Unlocked")
                
                st.dataframe(
                    display_df.rename(columns={
                        'tender_id': 'Tender ID',
                        'tender_title': 'Title',
                        'procuring_entity': 'Entity',
                        'procurement_type': 'Type',
                        'submission_deadline': 'Deadline',
                        'bid_status': 'Status',
                        'locked': 'Lock'
                    }),
                    width="stretch",  # ✅ FIX: Replaced use_container_width
                    height=300
                )
                
                # Selection dropdown
                tender_options = {f"{row['tender_id']} - {row['tender_title'][:50]}...": row['id'] 
                                 for _, row in filtered.iterrows()}
                
                selected_label = st.selectbox(
                    "Select tender to edit:",
                    options=list(tender_options.keys()),
                    key="edit_tender_select"
                )
                
                if selected_label:
                    selected_id = tender_options[selected_label]
                    
                    # Load tender data
                    if st.button("📥 Load Selected Tender", type="primary", key="load_edit_tender"):
                        try:
                            # 1. Open ONE connection for the entire loading process
                            conn = db.get_connection()
                            cursor = conn.cursor()
                            
                            # 2. Fetch Main Tender Data
                            cursor.execute("SELECT * FROM company_tenders WHERE id = ? AND company_id = ?", 
                                        (selected_id, st.session_state.company_id))
                            cols = [desc[0] for desc in cursor.description]
                            row = cursor.fetchone()
                            
                            if row:
                                # --- A. STORE TENDER DATA ---
                                st.session_state.extracted_data = dict(zip(cols, row))
                                st.session_state.edit_tender_id = selected_id
                                st.session_state.edit_mode = True
                                st.session_state.skip_review = True
                                
                                # Sync Basic Fields
                                st.session_state.form_tender_id = str(st.session_state.extracted_data.get('tender_id', ''))
                                st.session_state.form_tender_title = st.session_state.extracted_data.get('tender_title', '')
                                st.session_state.form_procuring_entity = st.session_state.extracted_data.get('procuring_entity', '')
                                st.session_state.form_division = st.session_state.extracted_data.get('division', 'Dhaka')
                                
                                raw_pt = str(st.session_state.extracted_data.get('procurement_type', 'works')).lower()
                                pt_def = 'goods' if 'goods' in raw_pt else ('services' if 'service' in raw_pt else 'works')
                                st.session_state.form_procurement_type = pt_def
                                
                                st.session_state.form_official_estimate = float(st.session_state.extracted_data.get('official_estimate', 0))
                                
                                # Parse Deadline
                                deadline_val = st.session_state.extracted_data.get('submission_deadline')
                                if deadline_val:
                                    try:
                                        if isinstance(deadline_val, str):
                                            st.session_state.form_deadline = datetime.strptime(deadline_val[:10], '%Y-%m-%d').date()
                                        elif hasattr(deadline_val, 'date'):
                                            st.session_state.form_deadline = deadline_val.date()
                                        else:
                                            st.session_state.form_deadline = datetime.now().date()
                                    except:
                                        st.session_state.form_deadline = datetime.now().date()
                                else:
                                    st.session_state.form_deadline = datetime.now().date()
                                
                                st.session_state.form_security = float(st.session_state.extracted_data.get('tender_security', 0))
                                # --- C. SYNC DATE FIELDS (The Missing Piece) ---
                                # Map DB columns -> Session State Keys
                                date_mappings = {
                                    'submission_deadline': 'form_deadline',
                                    'tender_publication_date': 'form_pub_date',
                                    'document_selling_end_date': 'form_doc_sell',
                                    'pre_bid_meeting_start': 'form_prebid_start',
                                    'pre_bid_meeting_end': 'form_prebid_end',
                                    'bid_opening_date': 'form_opening',
                                    'security_submission_deadline': 'form_sec_deadline',
                                    'security_valid_upto': 'form_sec_valid',
                                    'tender_valid_upto': 'form_tender_valid'
                                }

                                for db_col, state_key in date_mappings.items():
                                    val = row[db_col] if db_col in row else None
                                    
                                    # Parse Date
                                    parsed_date = datetime.now().date() # Default fallback
                                    
                                    if val:
                                        try:
                                            if isinstance(val, datetime):
                                                parsed_date = val.date()
                                            elif isinstance(val, date):
                                                parsed_date = val
                                            else:
                                                # Handle strings like "2026-05-11"
                                                parsed_date = datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
                                        except Exception:
                                            pass # Keep default if parse fails
                                    
                                    # Update Session State
                                    st.session_state[state_key] = parsed_date

                                # --- B. LOAD TEAM ASSIGNMENTS (Using SAME open connection) ---
                                try:
                                    # 1. Build exact ID -> Label map matching your dropdown format
                                    all_users = db.get_all_users(st.session_state.company_id)
                                    id_to_label = {}
                                    if all_users:
                                        for u in all_users:
                                            # u[0]=id, u[3]=name, u[5]=suffix (matches your user_options construction)
                                            uid = u[0]
                                            name = u[3] if len(u) > 3 else "User"
                                            suffix = u[5] if len(u) > 5 else ""
                                            id_to_label[uid] = f"{name} ({suffix})"

                                    # 2. Fetch team (NO is_active check)
                                    cursor.execute('''
                                    SELECT ta.role, ta.user_id 
                                    FROM tender_team_assignments ta
                                    WHERE ta.tender_id = ?
                                    ''', (selected_id,))
                                    team_rows = cursor.fetchall()
                                    
                                    bid_mgr_label = 'Select'
                                    tech_lead_label = 'Select'
                                    additional_labels = []
                                    
                                    for role, uid in team_rows:
                                        label = id_to_label.get(uid, f"Unknown ({uid})")
                                        if role == "Bid Manager":
                                            bid_mgr_label = label
                                        elif role == "Technical Lead":
                                            tech_lead_label = label
                                        else:
                                            additional_labels.append(label)
                                            
                                    # 3. Sync to Session State
                                    st.session_state.form_bid_manager = bid_mgr_label
                                    st.session_state.form_tech_lead = tech_lead_label
                                    st.session_state.form_team_members = additional_labels
                                    
                                    logger.info(f"✅ Loaded team for Tender #{selected_id}: BM={bid_mgr_label}, TL={tech_lead_label}, Members={len(additional_labels)}")
                                    
                                except Exception as e:
                                    logger.error(f"Failed to load team assignments: {e}")
                                    st.session_state.form_bid_manager = 'Select'
                                    st.session_state.form_tech_lead = 'Select'
                                    st.session_state.form_team_members = []

                                # 3. Close Connection ONLY AFTER ALL QUERIES ARE DONE
                                conn.close()
                                
                                st.success(f"✅ Tender **#{selected_id}** (`{st.session_state.extracted_data.get('tender_id')}`) loaded for editing!")
                                st.info("💡 Scroll down to edit fields and save changes.")
                                st.rerun()
                                
                            else:
                                conn.close()
                                st.error("❌ Failed to load tender data (Row not found).")
                                
                        except Exception as e:
                            logger.error(f"Failed to load tender for edit: {e}")
                            st.error(f"❌ Error: {str(e)}")
            else:
                st.info("📭 No tenders found matching your search.")
        else:
            st.info("📭 No tenders available to edit.")
    
    # =========================================================================
    # 4️⃣ PDF UPLOAD MODE
    # =========================================================================
    elif mode == "📄 Create from PDF Upload":
        st.markdown("### 📄 Upload Tender Notice (PDF)")
        st.caption("Upload the tender notice PDF to auto-fill form fields")
        
    # ✅ FIX: Add a unique key and handle upload properly
    uploaded_pdf = st.file_uploader("Choose PDF file", type=['pdf'], key="_tender_pdf_upload_new")
    
    # ✅ FIX: Clear extracted data when no file is uploaded
    if uploaded_pdf is None:
        if st.session_state.extracted_data is not None:
            st.session_state.extracted_data = None
            st.session_state.skip_review = False
        return
    
    # Process new PDF upload
    if uploaded_pdf and (st.session_state.extracted_data is None or st.session_state.get('_last_pdf_name') != uploaded_pdf.name):
        try:
            from modules.pdf_parser import parse_tender_pdf
            with st.spinner("🔍 Parsing PDF..."):
                parsed = parse_tender_pdf(uploaded_pdf)
            if parsed:
                st.session_state.extracted_data = parsed
                st.session_state.skip_review = False
                st.session_state._last_pdf_name = uploaded_pdf.name
                st.success("✅ PDF parsed successfully! Review the extracted data below.")
                st.rerun()
            else:
                st.warning("⚠️ Could not parse PDF. Please fill manually.")
                st.session_state.extracted_data = None
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            st.error(f"❌ PDF Error: {str(e)}")
            st.session_state.extracted_data = None
    
    # Show review page if data exists and not skipped
    if st.session_state.extracted_data and not st.session_state.skip_review:
        from modules.pdf_review import display_review_page
        def _on_review_confirm(): 
            st.session_state.skip_review = True
            st.rerun()
        display_review_page(st.session_state.extracted_data, _on_review_confirm)
        return

    
    # =========================================================================
    # 5️⃣ MANUAL ENTRY OR EDIT MODE - SHOW FORM
    # =========================================================================
    # Show form for Manual mode OR if edit data is loaded
    show_manual_form = (mode == "➕ Create New Tender (Manual)") or (mode == "✏️ Edit Existing Tender" and st.session_state.edit_mode and st.session_state.extracted_data)

    if show_manual_form:
    
        if is_editing:
            st.success(f"📝 **Editing Tender #{st.session_state.edit_tender_id}** (`{extracted.get('tender_id')}`)")
            st.info("💡 Modify the fields below and click '💾 Update Tender' to save changes.")
             # ✅ Add cancel button
            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("❌ Cancel Edit", use_container_width=True):
                    st.session_state.edit_mode = False
                    st.session_state.edit_tender_id = None
                    st.session_state.extracted_data = None
                    st.session_state._form_reset = True
                    st.rerun()
        
        
        # =========================================================================
        # 5️⃣ PRE-INITIALIZE SESSION STATE DEFAULTS (Prevents Streamlit Warnings)
        # =========================================================================
        defaults = {
            'form_tender_id': '', 'form_tender_title': '', 'form_procuring_entity': '', 'form_division': 'Dhaka',
            'form_procurement_type': 'works', 'form_official_estimate': 0.0, 'form_deadline': datetime.now().date(),
            'form_security': 0.0, 'form_project_code': '', 'form_project_name': '', 'form_package_no': '', 'form_budget_type': 'Development',
            'form_app_id': '', 'form_proc_nature': 'Works', 'form_source_funds': 'Government', 'form_category': '',
            'form_pub_date': datetime.now().date(), 'form_doc_sell': datetime.now().date(), 'form_prebid_start': datetime.now().date(),
            'form_prebid_end': datetime.now().date(), 'form_opening': datetime.now().date(), 'form_sec_deadline': datetime.now().date(),
            'form_sec_valid': datetime.now().date(), 'form_tender_valid': datetime.now().date(),
            'form_eval_type': 'Lot wise', 'form_eligibility': 'As Per Tender Documents', 'form_payment': 'Payment through Bank',
            'form_doc_fee': 0.0, 'form_official_name': '', 'form_official_designation': '', 'form_official_phone': '',
            'form_official_address': '', 'form_official_city': '', 'form_official_district': '',
            'form_bid_manager': 'Select', 'form_tech_lead': 'Select', 'form_team_members': [], 'form_notes': ''
        }
        for k, v in defaults.items():
            st.session_state.setdefault(k, v)

        # =========================================================================
        # 6️⃣ MAIN FORM (NO value= ARGUMENTS - Uses Session State Directly)
        # =========================================================================
        with st.form("create_tender_form", clear_on_submit=False):
            st.markdown("### 📝 Core Tender Details")
            col1, col2 = st.columns(2)
            
            with col1:
                st.text_input("Tender ID *", key="form_tender_id")
                st.text_area("Tender Title *", height=80, key="form_tender_title")
                st.text_input("Procuring Entity *", key="form_procuring_entity")
                divisions = ["Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
                st.selectbox("Division", divisions, key="form_division")
            
            with col2:
                valid_pt = ["works", "goods", "services"]
                st.selectbox("Procurement Type", valid_pt, key="form_procurement_type")
                st.number_input("Official Estimate (BDT) *", min_value=0, step=1000000, format="%d", key="form_official_estimate")
                st.date_input("Submission Deadline *", key="form_deadline")
                st.number_input("Tender Security (BDT)", min_value=0, step=10000, format="%d", key="form_security")
            
            # Project & Funding
            with st.expander("💰 Project & Funding Information", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Project Code", key="form_project_code")
                    st.text_area("Project Name", height=60, key="form_project_name")
                    st.text_input("Package No.", key="form_package_no")
                    st.text_input("Budget Type", key="form_budget_type")
                with c2:
                    st.text_input("App ID", key="form_app_id")
                    st.text_input("Procurement Nature", key="form_proc_nature")
                    st.text_input("Source of Funds", key="form_source_funds")
                    st.text_area("CPV/Category", height=60, key="form_category")
            
            # Dates
            with st.expander("📅 Tender Schedule & Dates", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.date_input("Publication Date", key="form_pub_date")
                    st.date_input("Doc Selling Ends", key="form_doc_sell")
                    st.date_input("Pre-Bid Start", key="form_prebid_start")
                    st.date_input("Pre-Bid End", key="form_prebid_end")
                with c2:
                    st.date_input("Bid Opening Date", key="form_opening")
                    st.date_input("Security Submission Deadline", key="form_sec_deadline")
                    st.date_input("Security Valid Up To", key="form_sec_valid")
                    st.date_input("Tender Valid Up To", key="form_tender_valid")
            
            # Evaluation & Payment
            with st.expander("⚙️ Evaluation & Payment", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Evaluation Type", key="form_eval_type")
                    st.text_area("Eligibility Criteria", height=60, key="form_eligibility")
                with c2:
                    st.text_input("Mode of Payment", key="form_payment")
                    st.number_input("Document Fee (BDT)", min_value=0, step=500, format="%d", key="form_doc_fee")
            
            # Contact
            with st.expander("👤 Official Contact Information", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Official Name", key="form_official_name")
                    st.text_input("Designation", key="form_official_designation")
                    st.text_input("Phone", key="form_official_phone")
                with c2:
                    st.text_area("Address", height=60, key="form_official_address")
                    st.text_input("City", key="form_official_city")
                    st.text_input("District", key="form_official_district")
            
            # Team & Notes
            st.markdown("#### 👥 Team Assignment & Notes")
            users = db.get_all_users(company_id=st.session_state.company_id)
            user_options = {f"{u[3]} ({u[5]})": u[0] for u in users} if users else {}
            
            c1, c2 = st.columns(2)
            with c1:
                st.selectbox("Bid Manager", ["Select"] + list(user_options.keys()), key="form_bid_manager")
            with c2:
                st.selectbox("Technical Lead", ["Select"] + list(user_options.keys()), key="form_tech_lead")
            
            st.multiselect("Additional Team Members", list(user_options.keys()), key="form_team_members")
            st.text_area("Additional Notes", height=80, key="form_notes")
            
            # Submit Button
            btn_text = "💾 Update Tender" if is_editing else "🚀 Create Tender"
            form_submitted = st.form_submit_button(btn_text, width="stretch", type="primary")
            
            if form_submitted:
                if st.session_state.get('_form_submitting'):
                    st.warning("⏳ Processing... Please wait.")
                    return
                
                st.session_state._form_submitting = True
                try:
                    # Read form values from Session State directly
                    tid = str(st.session_state.form_tender_id).strip()
                    title = str(st.session_state.form_tender_title).strip()
                    entity = str(st.session_state.form_procuring_entity).strip()
                    est = float(st.session_state.form_official_estimate)
                    
                    if not all([tid, title, entity, est > 0]):
                        st.error("❌ Please fill all required fields marked with *")
                        return

                    tender_data: Dict[str, Any] = {
                        'tender_id': tid, 'tender_title': title, 'procuring_entity': entity,
                        'division': st.session_state.form_division, 'district': st.session_state.get('form_district', ''), 'thana': st.session_state.get('form_thana', ''),
                        'country': 'Bangladesh', 'procurement_type': st.session_state.form_procurement_type,
                        'official_estimate': est, 'submission_deadline': st.session_state.form_deadline,
                        'tender_security': float(st.session_state.form_security), 'document_fee': float(st.session_state.form_doc_fee),
                        'evaluation_type': st.session_state.form_eval_type, 'mode_of_payment': st.session_state.form_payment,
                        'eligibility_criteria': st.session_state.form_eligibility, 'invitation_ref_no': st.session_state.get('form_invitation_ref_no', ''),
                        'package_no': st.session_state.form_package_no, 'project_code': st.session_state.form_project_code, 
                        'project_name': st.session_state.form_project_name,
                        'inviting_official_name': st.session_state.form_official_name, 'inviting_official_designation': st.session_state.form_official_designation,
                        'inviting_official_phone': st.session_state.form_official_phone, 'inviting_official_email': st.session_state.get('form_inviting_official_email', ''),
                        'inviting_official_address': st.session_state.form_official_address, 'inviting_official_city': st.session_state.form_official_city,
                        'inviting_official_thana': st.session_state.get('form_thana', ''), 'inviting_official_district': st.session_state.form_official_district,
                        'notes': st.session_state.form_notes, 'app_id': st.session_state.form_app_id, 
                        'procuring_entity_code': st.session_state.get('form_procuring_entity_code', ''), 'procurement_nature': st.session_state.form_proc_nature, 
                        'event_type': st.session_state.get('form_event_type', 'TENDER'), 'budget_type': st.session_state.form_budget_type, 
                        'source_of_funds': st.session_state.form_source_funds, 'category': st.session_state.form_category,
                        'tender_publication_date': st.session_state.form_pub_date, 'document_selling_end_date': st.session_state.form_doc_sell, 
                        'pre_bid_meeting_start': st.session_state.form_prebid_start, 'pre_bid_meeting_end': st.session_state.form_prebid_end, 
                        'bid_opening_date': st.session_state.form_opening, 'security_submission_deadline': st.session_state.form_sec_deadline, 
                        'security_valid_upto': st.session_state.form_sec_valid, 'tender_valid_upto': st.session_state.form_tender_valid,
                        # ✅ FIX: Use 'extracted' which is now defined at the top
                        'is_locked': extracted.get('is_locked', 0) if is_editing else 0,
                        'is_copy': extracted.get('is_copy', 0) if is_editing else 0,
                        'original_tender_id': extracted.get('original_tender_id') if is_editing else None,
                        'is_active': 1
                    }

                    conn = db.get_connection()
                    cursor = conn.cursor()

                    if is_editing:
                        target_id = int(extracted['id'])
                        # Duplicate check (ignore self)
                        cursor.execute('SELECT id FROM company_tenders WHERE company_id = ? AND tender_id = ? AND is_active = 1 AND id != ?', 
                                      (st.session_state.company_id, tid, target_id))
                        if cursor.fetchone():
                            conn.close()
                            st.error(f"❌ Tender ID `{tid}` already exists for another record.")
                            return

                        # Dynamic UPDATE
                        cols = [k for k in tender_data.keys() if k not in ('id', 'company_id', 'created_by', 'created_at')]
                        set_clause = ", ".join(f"{c} = ?" for c in cols) + ", updated_at = ?"
                        query = f"UPDATE company_tenders SET {set_clause} WHERE id = ? AND company_id = ?"
                        vals = [tender_data[c] for c in cols] + [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), target_id, st.session_state.company_id]
                        
                        with st.spinner("💾 Updating tender..."):
                            cursor.execute(query, vals)
                            try:
                                # Read current form values
                                bid_mgr = st.session_state.get('form_bid_manager', 'Select')
                                tech_lead = st.session_state.get('form_tech_lead', 'Select')
                                add_members = st.session_state.get('form_team_members', []) or []  # Handle None safely
                                
                                # Delete existing assignments
                                cursor.execute("DELETE FROM tender_team_assignments WHERE tender_id = ?", (target_id,))
                                
                                insert_q = 'INSERT INTO tender_team_assignments (tender_id, user_id, role, assigned_at) VALUES (?, ?, ?, ?)'
                                now = datetime.now()
                                inserted_count = 0
                                
                                if bid_mgr != "Select" and bid_mgr in user_options:
                                    cursor.execute(insert_q, (target_id, user_options[bid_mgr], "Bid Manager", now))
                                    inserted_count += 1
                                    
                                if tech_lead != "Select" and tech_lead in user_options:
                                    cursor.execute(insert_q, (target_id, user_options[tech_lead], "Technical Lead", now))
                                    inserted_count += 1
                                    
                                for m in add_members:
                                    if m in user_options:
                                        cursor.execute(insert_q, (target_id, user_options[m], "Team Member", now))
                                        inserted_count += 1
                                        
                                logger.info(f"✅ Team sync complete: {inserted_count} members saved for tender #{target_id}")
                                
                            except Exception as e:
                                logger.error(f"Team sync failed: {e}", exc_info=True)
                                st.warning("⚠️ Team assignments failed to save. Tender updated, but team data unchanged.")
                            conn.commit()
                        st.success(f"✅ Tender #{target_id} updated successfully!")
                        
                    else:
                        cursor.execute('SELECT id FROM company_tenders WHERE company_id = ? AND tender_id = ? AND is_active = 1', 
                                      (st.session_state.company_id, tid))
                        if cursor.fetchone():
                            conn.close()
                            st.error(f"❌ Tender ID `{tid}` already exists.")
                            return
                        conn.close()
                        
                        tender_db_id = db.create_tender(st.session_state.company_id, tender_data, st.session_state.user_id)
                        if not tender_db_id:
                            st.error("❌ Failed to create tender. Check constraints.")
                            return
                            
                        if st.session_state.form_bid_manager != "Select" and st.session_state.form_bid_manager in user_options:
                            db.assign_team_member(tender_db_id, user_options[st.session_state.form_bid_manager], "Bid Manager")
                        if st.session_state.form_tech_lead != "Select" and st.session_state.form_tech_lead in user_options:
                            db.assign_team_member(tender_db_id, user_options[st.session_state.form_tech_lead], "Technical Lead")
                        for m in st.session_state.form_team_members:
                            if m in user_options: db.assign_team_member(tender_db_id, user_options[m], "Team Member")
                        st.success(f"✅ Tender '{title}' created successfully!")

                    st.balloons()
                    st.session_state._form_reset = True
                    st.session_state.edit_tender_id = None
                    st.session_state.edit_mode = False                     
                    st.session_state.extracted_data = None  

                    st.rerun()

                except Exception as e:
                    logger.error(f"Tender operation failed: {e}", exc_info=True)
                    st.error(f"❌ Error: {str(e)}")
                finally:
                    st.session_state._form_submitting = False


def _render_tender_reports() -> None:
    """Generate reports for tenders"""
    st.markdown("### 📊 Tender Reports")
    
    tenders_df = db.get_company_tenders(st.session_state.company_id)
    
    if tenders_df.empty:
        st.info("📭 No data available")
        return
    
    # Summary statistics
    st.markdown("#### 📈 Performance Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        won = len(tenders_df[tenders_df['bid_status'] == 'won'])
        lost = len(tenders_df[tenders_df['bid_status'] == 'lost'])
        pending = len(tenders_df[tenders_df['bid_status'] == 'submitted'])
        
        if won + lost + pending > 0:
            fig = go.Figure(data=[go.Pie(
                labels=['Won', 'Lost', 'Pending'],
                values=[won, lost, pending],
                marker_colors=['#22c55e', '#ef4444', '#f97316'],
                hole=0.3
            )])
            fig.update_layout(title="Bid Status", height=280, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Monthly trend
        if 'bid_submission_date' in tenders_df.columns and not tenders_df['bid_submission_date'].isna().all():
            tenders_df_copy = tenders_df.copy()
            tenders_df_copy['month'] = pd.to_datetime(tenders_df_copy['bid_submission_date']).dt.to_period('M').astype(str)
            monthly = tenders_df_copy.groupby('month').size().reset_index(name='count')
            
            if not monthly.empty:
                fig = go.Figure(data=[go.Bar(
                    x=monthly['month'], 
                    y=monthly['count'], 
                    marker_color='#667eea',
                    text=monthly['count'],
                    textposition='auto'
                )])
                fig.update_layout(title="Monthly Submissions", height=280, margin=dict(t=30, b=0, l=0, r=0), xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        # Win rate by division
        if 'division' in tenders_df.columns:
            div_stats = tenders_df.groupby('division').agg({
                'bid_status': lambda x: (x == 'won').sum(),
                'id': 'count'
            }).reset_index()
            div_stats['win_rate'] = (div_stats['bid_status'] / div_stats['id'] * 100).fillna(0)
            
            if not div_stats.empty:
                fig = go.Figure(data=[go.Bar(
                    x=div_stats['division'], 
                    y=div_stats['win_rate'], 
                    marker_color='#22c55e',
                    text=div_stats['win_rate'].round(1).astype(str) + '%',
                    textposition='auto'
                )])
                fig.update_layout(title="Win Rate by Division", height=280, margin=dict(t=30, b=0, l=0, r=0), yaxis_range=[0, 100], yaxis_title="Win Rate (%)")
                st.plotly_chart(fig, use_container_width=True)
    
    # Export report
    st.markdown("#### 📥 Export Report")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export Summary (CSV)", use_container_width=True):
            csv = tenders_df.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name=f"tender_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col2:
        total = len(tenders_df)
        won = len(tenders_df[tenders_df['bid_status'] == 'won'])
        win_rate = (won / total * 100) if total > 0 else 0
        st.info(f"📊 Total: {total} | Won: {won} | Win Rate: {win_rate:.1f}%")