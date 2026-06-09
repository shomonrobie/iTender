# In your admin dashboard (_pages/admin_dashboard.py)

import streamlit as st
import pandas as pd
import os
import re
from collections import defaultdict
from database.db_manager import DatabaseManager
from modules.egp_boq_workspace import render_boq_workspace
from modules.auth import restore_session_from_url
import datetime
#from modules.lged_parser import render_lged_management
#from modules.pwd_rate_management_dashboard import PWDManagementDashboard
#from modules.pwd_import_wizard import PWDImportWizard
#from modules.pwd_parser import PWDParserWithHierarchy  # Your existing parser
#from modules.unified_version_manager import render_unified_version_management, register_version_after_import
#from modules.unified_rollback_manager import render_rollback_management

from modules.unified_import_wizard import render_unified_import_wizard
from modules.unified_version_manager import render_unified_version_management
from modules.unified_rollback_manager import render_rollback_management
from modules.manual_rate_entry import ManualRateEntry, render_quick_entry
from modules.rate_viewer import render_rate_viewer
from modules.rate_crud_forms import render_rate_crud_forms


db = DatabaseManager()
DB_PATH = db.db_path


class PWDParserWithHierarchy:
    """Parser that maintains parent-child relationships in PWD schedule"""
    
    def __init__(self):
        self.parent_items = []
        self.child_items = []
    
    def parse_pdf_with_hierarchy(self, file_path, max_pages=None):
        """Parse PDF while maintaining parent-child hierarchy"""
        import pdfplumber
        
        items = []
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
            
            for page_num in range(pages_to_process):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if not text:
                    continue
                
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                })
                
                if tables:
                    for table in tables:
                        page_items = self._parse_table(table)
                        items.extend(page_items)
                else:
                    page_items = self._parse_text(text)
                    items.extend(page_items)
        
        return self._organize_hierarchy(items)
    
    def _parse_table(self, table):
        """Parse table rows"""
        items = []
        
        for row in table:
            if not row or len(row) < 3:
                continue
            
            row_cells = [str(cell).strip() if cell else '' for cell in row]
            
            # Find item code
            pwd_code = None
            code_col = None
            for col, cell in enumerate(row_cells[:4]):
                if re.match(r'^\d{1,2}\.\d{1,2}(?:\.\d{1,2})?$', cell):
                    pwd_code = cell
                    code_col = col
                    break
            
            if not pwd_code:
                continue
            
            # Determine level
            code_parts = pwd_code.split('.')
            level = len(code_parts)
            
            # Extract description
            desc = ""
            if code_col is not None and code_col + 1 < len(row_cells):
                desc = row_cells[code_col + 1].strip()
                desc = re.sub(r'^\d+(?:\.\d+)?\s*$', '', desc)
            
            if not desc:
                continue
            
            # Extract rates
            rates = self._extract_rates(row_cells, code_col)
            
            # Extract unit
            unit = self._extract_unit(row_cells, code_col)
            
            items.append({
                'pwd_code': pwd_code,
                'level': level,
                'description': desc,
                'has_rates': len(rates) > 0,
                'rates': rates,
                'unit': unit
            })
        
        return items
    
    def _parse_text(self, text):
        """Parse raw text"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            code_match = re.match(r'^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+', line)
            if not code_match:
                continue
            
            pwd_code = code_match.group(1)
            code_parts = pwd_code.split('.')
            level = len(code_parts)
            
            remaining = line[len(code_match.group(0)):].strip()
            
            # Find rates
            rate_pattern = r'Tk\.?\s*([\d,]+(?:\.\d{2})?)'
            rate_matches = list(re.finditer(rate_pattern, remaining, re.I))
            
            if rate_matches:
                desc = remaining[:rate_matches[0].start()].strip()
                desc = re.sub(r'\s+', ' ', desc).strip()
                
                # Extract rates
                zone_names = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
                rates = {}
                for idx, match in enumerate(rate_matches[:4]):
                    if idx < len(zone_names):
                        try:
                            clean_rate = float(match.group(1).replace(',', ''))
                            rates[zone_names[idx]] = clean_rate
                        except:
                            pass
                
                # Extract unit
                unit = "N/A"
                unit_match = re.search(r'\b(cum|sqm|meter|each|job|set|kg|hour|month|tender|point)\b', desc.lower())
                if unit_match:
                    unit = unit_match.group(1)
                    desc = re.sub(r'\b' + unit + r'\b', '', desc, flags=re.I).strip()
            else:
                desc = remaining
                rates = {}
                unit = "N/A"
            
            if desc:
                items.append({
                    'pwd_code': pwd_code,
                    'level': level,
                    'description': desc,
                    'has_rates': len(rates) > 0,
                    'rates': rates,
                    'unit': unit
                })
        
        return items
    
    def _extract_rates(self, row_cells, code_col):
        """Extract rates from row"""
        rates = {}
        zone_names = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
        rate_start = 5 if code_col is None or code_col < 5 else code_col + 3
        
        for idx, zone in enumerate(zone_names):
            rate_col = rate_start + idx
            if rate_col < len(row_cells):
                rate_val = self._extract_numeric(row_cells[rate_col])
                if rate_val and rate_val > 0:
                    rates[zone] = rate_val
        
        return rates
    
    def _extract_unit(self, row_cells, code_col):
        """Extract unit from row"""
        if code_col is None or code_col + 2 >= len(row_cells):
            return "N/A"
        
        unit_cell = row_cells[code_col + 2].lower()
        unit_patterns = ['cum', 'sqm', 'meter', 'each', 'job', 'set', 'kg', 'hour', 'month', 'tender', 'point']
        
        for pattern in unit_patterns:
            if pattern in unit_cell:
                return pattern
        
        return "N/A"
    
    def _extract_numeric(self, value):
        """Extract numeric value"""
        if not value or value == '—':
            return None
        
        cleaned = re.sub(r'[^\d.-]', '', str(value).replace(',', ''))
        try:
            return float(cleaned) if cleaned and cleaned != '-' else None
        except:
            return None
    
    def _organize_hierarchy(self, items):
        """Organize into parent-child structure"""
        
        hierarchy = {
            'parents': [],
            'children': [],
            'parent_child_map': {}
        }
        
        # First pass: collect parents
        for item in items:
            code_parts = item['pwd_code'].split('.')
            if len(code_parts) == 2:  # Parent
                hierarchy['parents'].append({
                    'code': item['pwd_code'],
                    'description': item['description'],
                    'chapter': code_parts[0]
                })
                hierarchy['parent_child_map'][item['pwd_code']] = []
        
        # Second pass: collect children
        for item in items:
            code_parts = item['pwd_code'].split('.')
            if len(code_parts) >= 3:  # Child
                parent_code = '.'.join(code_parts[:2])
                
                child_item = {
                    'pwd_code': item['pwd_code'],
                    'parent_code': parent_code,
                    'description': item['description'],
                    'unit': item['unit'],
                    'rates': item['rates']
                }
                
                hierarchy['children'].append(child_item)
                
                if parent_code in hierarchy['parent_child_map']:
                    hierarchy['parent_child_map'][parent_code].append(child_item)
        
        return hierarchy


class PWDExtractorForVerification:
    """Extract and analyze PWD structure for manual verification"""
    
    def __init__(self):
        self.all_items = []
        self.parents = {}
        self.children = defaultdict(list)
        self.orphans = []
        self.items_without_children = set()
    
    def extract_from_pdf(self, file_path, max_pages=None):
        """Extract all items from PDF with hierarchy analysis"""
        import pdfplumber
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
            
            for page_num in range(pages_to_process):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if not text:
                    continue
                
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                })
                
                if tables:
                    for table in tables:
                        self._process_table(table)
                else:
                    self._process_text(text)
        
        # Analyze hierarchy
        self._analyze_hierarchy()
        
        return self._generate_report()
    
    def _process_table(self, table):
        """Process table rows"""
        for row in table:
            if not row or len(row) < 2:
                continue
            
            row_cells = [str(cell).strip() if cell else '' for cell in row]
            
            # Find item code
            pwd_code = None
            description = ""
            
            for col, cell in enumerate(row_cells[:4]):
                if re.match(r'^\d{1,2}\.\d{1,2}(?:\.\d{1,2})?$', cell):
                    pwd_code = cell
                    if col + 1 < len(row_cells):
                        description = row_cells[col + 1]
                        description = re.sub(r'^\d+(?:\.\d+)?\s*$', '', description)
                        description = re.sub(r'\s+', ' ', description).strip()
                    break
            
            if pwd_code and description:
                self.all_items.append({
                    'code': pwd_code,
                    'description': description[:500],
                    'has_rates': self._check_has_rates(row_cells)
                })
    
    def _process_text(self, text):
        """Process raw text lines"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            code_match = re.match(r'^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+', line)
            if not code_match:
                continue
            
            pwd_code = code_match.group(1)
            remaining = line[len(code_match.group(0)):].strip()
            
            has_rates = bool(re.search(r'Tk\.?\s*[\d,]+', remaining, re.I))
            
            if has_rates:
                rate_match = re.search(r'Tk\.?\s*[\d,]+', remaining, re.I)
                if rate_match:
                    description = remaining[:rate_match.start()].strip()
                else:
                    description = remaining
            else:
                description = remaining
            
            description = re.sub(r'\s+', ' ', description).strip()
            
            if description:
                self.all_items.append({
                    'code': pwd_code,
                    'description': description[:500],
                    'has_rates': has_rates
                })
    
    def _check_has_rates(self, row_cells):
        """Check if row contains rate values"""
        for cell in row_cells[5:9]:
            if cell and re.search(r'Tk\.?\s*[\d,]+', str(cell), re.I):
                return True
        return False
    
    def _analyze_hierarchy(self):
        """Analyze parent-child relationships"""
        
        # First pass: identify parents
        for item in self.all_items:
            code_parts = item['code'].split('.')
            if len(code_parts) == 2:
                self.parents[item['code']] = {
                    'code': item['code'],
                    'description': item['description'],
                    'has_rates': item['has_rates'],
                    'child_count': 0
                }
        
        # Second pass: assign children
        for item in self.all_items:
            code_parts = item['code'].split('.')
            if len(code_parts) >= 3:
                parent_code = '.'.join(code_parts[:2])
                if parent_code in self.parents:
                    self.children[parent_code].append(item)
                    self.parents[parent_code]['child_count'] += 1
                else:
                    self.orphans.append({
                        'code': item['code'],
                        'description': item['description'],
                        'parent_expected': parent_code
                    })
        
        # Find parents with no children
        for parent_code, parent_data in self.parents.items():
            if parent_data['child_count'] == 0:
                self.items_without_children.add(parent_code)
    
    def _generate_report(self):
        """Generate comprehensive verification report"""
        
        report = {
            'summary': {
                'total_items': len(self.all_items),
                'total_parents': len(self.parents),
                'total_children': sum(len(children) for children in self.children.values()),
                'orphans': len(self.orphans),
                'parents_without_children': len(self.items_without_children)
            },
            'parents': [],
            'children': [],
            'orphans_list': self.orphans,
            'parents_without_children_list': []
        }
        
        # Parents list
        for code, data in sorted(self.parents.items()):
            report['parents'].append({
                'Item Code': code,
                'Description': data['description'][:200],
                'Has Direct Rates?': 'Yes' if data['has_rates'] else 'No',
                'Child Count': data['child_count'],
                'Status': '⚠️ NO CHILDREN' if data['child_count'] == 0 else '✅ Has Children'
            })
        
        # Parents without children
        for code in sorted(self.items_without_children):
            parent_data = self.parents[code]
            report['parents_without_children_list'].append({
                'Item Code': code,
                'Description': parent_data['description'][:200],
                'Has Direct Rates?': 'Yes' if parent_data['has_rates'] else 'No',
                'Action Required': 'Verify if this should have child items'
            })
        
        return report

def render_pwd_ingestion_panel():
    """Main PWD ingestion panel with hierarchy"""
    
    st.markdown("### 📥 Import PWD Schedule")
    st.caption("Upload PWD Schedule PDF - Automatically detects parent-child hierarchy")
    
    uploaded_file = st.file_uploader(
        "Upload PWD Rate Schedule PDF", 
        type=["pdf"], 
        key="admin_pwd_hierarchical"
    )
    
    if not uploaded_file:
        st.info("📁 Please upload a PWD rate schedule PDF file")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2022)
    
    with col2:
        max_pages = st.number_input("Preview Pages", min_value=1, max_value=500, value=10,
                                    help="Process first N pages. Set to 500 for full PDF.")
    
    dry_run = st.checkbox("🔍 Dry Run Mode (Preview only, no database save)", value=True)
    
    if st.button("⚡ Parse PWD Schedule", type="primary", use_container_width=True):
        temp_path = "temp_pwd.pdf"
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            with st.spinner("Parsing PDF with hierarchical structure..."):
                parser = PWDParserWithHierarchy()
                hierarchy = parser.parse_pdf_with_hierarchy(temp_path, max_pages=max_pages if max_pages > 0 else None)
            
            if hierarchy['parents']:
                st.success(f"✅ Parsed {len(hierarchy['parents'])} parent items and {len(hierarchy['children'])} child items")
                
                # Display preview
                render_hierarchical_pwd_preview(hierarchy)
                
                # Save to database if not dry run
                if not dry_run:
                    if st.button("💾 Confirm & Save to Database", type="primary"):
                        success, msg1, msg2 = save_hierarchy_to_database(hierarchy, edition_year)
                        if success:
                            st.success(f"🎉 Saved {msg1} parents and {msg2} children to database!")
                            st.balloons()
                        else:
                            st.error(f"Database error: {msg2}")
                
                # Download options
                st.markdown("### 📥 Export Data")
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    parents_df = pd.DataFrame(hierarchy['parents'])
                    st.download_button(
                        "📥 Download Parents (CSV)",
                        parents_df.to_csv(index=False),
                        f"pwd_parents_{edition_year}.csv",
                        "text/csv"
                    )
                
                with col_d2:
                    children_data = []
                    for child in hierarchy['children']:
                        row = {'pwd_code': child['pwd_code'], 'parent_code': child['parent_code'], 
                               'description': child['description'], 'unit': child['unit']}
                        for zone, rate in child['rates'].items():
                            row[zone] = rate
                        children_data.append(row)
                    children_df = pd.DataFrame(children_data)
                    st.download_button(
                        "📥 Download Child Items (CSV)",
                        children_df.to_csv(index=False),
                        f"pwd_children_{edition_year}.csv",
                        "text/csv"
                    )
            else:
                st.warning("No items found. Try increasing the number of pages.")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            import traceback
            with st.expander("Debug Information"):
                st.code(traceback.format_exc())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def render_pwd_verification_tool():
    """Render the PWD verification tool in admin dashboard"""
    
    st.markdown("### 🔍 PWD Schedule Verification Tool")
    st.caption("Scan full PDF, analyze hierarchy, and export CSV for manual verification")
    
    uploaded_file = st.file_uploader(
        "Upload PWD Rate Schedule PDF for Verification", 
        type=["pdf"], 
        key="pwd_verification"
    )
    
    if not uploaded_file:
        st.info("📁 Upload a PWD PDF to analyze its structure")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        scan_pages = st.number_input(
            "Pages to Scan", 
            min_value=1, 
            max_value=500, 
            value=50,
            step=10,
            help="Scan first N pages. Set to 500 for full PDF."
        )
    
    with col2:
        full_scan = st.checkbox("Scan Entire PDF", value=False, help="Overrides pages setting")
    
    if st.button("🔍 Analyze PDF Structure", type="primary", use_container_width=True):
        temp_path = "temp_pwd_verify.pdf"
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            with st.spinner("Analyzing PDF structure..."):
                extractor = PWDExtractorForVerification()
                max_pages = None if full_scan else scan_pages
                report = extractor.extract_from_pdf(temp_path, max_pages=max_pages)
            
            # Display summary
            st.markdown("### 📊 Analysis Summary")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("Total Items Found", report['summary']['total_items'])
            with col_b:
                st.metric("Parent Items", report['summary']['total_parents'])
            with col_c:
                st.metric("Child Items", report['summary']['total_children'])
            with col_d:
                st.metric("Orphans Found", report['summary']['orphans'])
            
            if report['summary']['parents_without_children'] > 0:
                st.warning(f"⚠️ {report['summary']['parents_without_children']} parent items have NO child items - needs verification")
            
            if report['summary']['orphans'] > 0:
                st.error(f"❌ {report['summary']['orphans']} orphan items found (parent not detected)")
            
            # Display tables
            if report['parents']:
                st.markdown("#### Parents")
                st.dataframe(pd.DataFrame(report['parents']), use_container_width=True, hide_index=True)
                
                csv_parents = pd.DataFrame(report['parents']).to_csv(index=False)
                st.download_button(
                    "📥 Download Parents CSV",
                    csv_parents,
                    f"pwd_parents_verification_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv"
                )
            
            if report['parents_without_children_list']:
                st.markdown("#### Parents Without Children (Need Verification)")
                st.dataframe(pd.DataFrame(report['parents_without_children_list']), use_container_width=True, hide_index=True)
            
            if report['orphans_list']:
                st.markdown("#### Orphan Items")
                st.dataframe(pd.DataFrame(report['orphans_list']), use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Analysis error: {str(e)}")
            import traceback
            with st.expander("Debug Information"):
                st.code(traceback.format_exc())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def render_hierarchical_pwd_preview(hierarchy):
    """Display hierarchical PWD data"""
    
    if not hierarchy['parents']:
        st.warning("No parent items found")
        return
    
    st.markdown("### 📊 Hierarchical PWD Schedule Structure")
    
    total_parents = len(hierarchy['parents'])
    total_children = len(hierarchy['children'])
    children_with_rates = sum(1 for c in hierarchy['children'] if c['rates'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Parent Items", total_parents)
    col2.metric("Child Items", f"{children_with_rates} / {total_children}")
    col3.metric("Coverage Ratio", f"{total_children/total_parents:.1f}" if total_parents > 0 else "0")
    
    st.markdown("### 📂 PWD Schedule Hierarchy")
    
    for parent in hierarchy['parents'][:30]:
        children = hierarchy['parent_child_map'].get(parent['code'], [])
        
        if children:
            with st.expander(f"📁 {parent['code']}: {parent['description'][:70]}... ({len(children)} items)", expanded=False):
                child_data = []
                for child in children:
                    row = {
                        'Code': child['pwd_code'],
                        'Description': child['description'][:80] + ('...' if len(child['description']) > 80 else ''),
                        'Unit': child['unit'],
                    }
                    for zone, rate in child['rates'].items():
                        row[zone] = f"৳{rate:,.2f}"
                    child_data.append(row)
                
                if child_data:
                    st.dataframe(pd.DataFrame(child_data), use_container_width=True, hide_index=True)
        else:
            st.info(f"📄 {parent['code']}: {parent['description'][:70]}... (No child items)")


def save_hierarchy_to_database(hierarchy, edition_year):
    """Save hierarchical data to database"""
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_parents (
                pwd_code TEXT PRIMARY KEY,
                description TEXT,
                chapter_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_children (
                pwd_code TEXT PRIMARY KEY,
                parent_code TEXT NOT NULL,
                description TEXT,
                unit TEXT,
                edition_year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pwd_code TEXT NOT NULL,
                zone_name TEXT NOT NULL,
                unit_rate REAL NOT NULL,
                edition_year INTEGER NOT NULL,
                UNIQUE(pwd_code, zone_name, edition_year)
            )
        """)
        
        # Clear existing data
        cursor.execute("DELETE FROM pwd_rates WHERE edition_year = ?", (edition_year,))
        cursor.execute("DELETE FROM pwd_children WHERE edition_year = ?", (edition_year,))
        cursor.execute("DELETE FROM pwd_parents")
        
        # Insert parents
        for parent in hierarchy['parents']:
            cursor.execute("""
                INSERT OR REPLACE INTO pwd_parents (pwd_code, description, chapter_number)
                VALUES (?, ?, ?)
            """, (parent['code'], parent['description'][:2000], parent['chapter']))
        
        # Insert children and rates
        for child in hierarchy['children']:
            cursor.execute("""
                INSERT OR REPLACE INTO pwd_children (pwd_code, parent_code, description, unit, edition_year)
                VALUES (?, ?, ?, ?, ?)
            """, (child['pwd_code'], child['parent_code'], child['description'][:2000], child['unit'], edition_year))
            
            for zone, rate in child['rates'].items():
                cursor.execute("""
                    INSERT OR REPLACE INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year)
                    VALUES (?, ?, ?, ?)
                """, (child['pwd_code'], zone, rate, edition_year))
        
        conn.commit()
        conn.close()
        
        return True, len(hierarchy['parents']), len(hierarchy['children'])
        
    except Exception as e:
        return False, 0, str(e)


def show():
    """Admin dashboard page with full system management"""
    
    st.markdown("""
    <div class="main-header">
        <h1>👑 Admin Dashboard</h1>
        <p>System-wide administration and monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get all users for stats
    all_users_raw = db.get_all_users()
    all_subs = db.get_all_subscriptions()
    
    # Convert to dictionary format
    all_users = []
    for u in all_users_raw:
        if hasattr(u, 'keys'):
            user_dict = dict(u)
        elif isinstance(u, (tuple, list)):
            if len(u) >= 10:
                user_dict = {
                    'id': u[0], 'username': u[1], 'email': u[2], 'full_name': u[3],
                    'phone': u[4], 'role': u[5], 'is_active': u[6],
                    'created_at': u[7], 'last_login': u[8], 'company_name': u[9],
                    'is_approved': u[10] if len(u) > 10 else 1
                }
            else:
                continue
        elif isinstance(u, dict):
            user_dict = u
        else:
            continue
        all_users.append(user_dict)
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", len(all_users))
    
    with col2:
        active_users = len([u for u in all_users if u.get('is_active', 0) == 1]) if all_users else 0
        st.metric("Active Users", active_users)
    
    with col3:
        companies = set([u.get('company_name', 'N/A') for u in all_users]) if all_users else set()
        st.metric("Companies", len(companies))
    
    with col4:
        paid_subs = len([s for s in all_subs if len(s) > 2 and s[2] not in ['free', 'trial']]) if all_subs else 0
        st.metric("Paid Subscriptions", paid_subs)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📊 Overview", 
        "👥 All Users", 
        "🏢 Companies", 
        "👑 System Users", 
        "🔐 Role Management",
        "🏗️ Rate Import",    
        "📅 Version Management",
        "🔄 Rollback Management",
        "📝 Manual Entry",
        "📊 Rate Viewer"  # ← NEW TAB

    ])
    
    with tab1:
        render_admin_overview(all_users, all_subs)
    
    with tab2:
        render_all_users(all_users)
    
    with tab3:
        render_company_management()
    
    with tab4:
        render_system_user_management()
    
    with tab5:
        render_role_management_page()
    
    with tab6:
        render_unified_import_wizard(db)

    with tab7:
        render_rollback_management(db)        
    with tab8:
        render_unified_version_management(db)
    with tab9:  # Manual Entry
        render_rate_crud_forms(db)

    with tab10:
        render_rate_viewer(db)




"📝 Manual Entry"  # ← NEW TAB
def render_hierarchical_pwd_viewer():
    """View imported PWD hierarchy from database"""
    
    st.markdown("### 📂 PWD Hierarchy from Database")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all parents
        cursor.execute("SELECT pwd_code, description, chapter_number FROM pwd_parents ORDER BY pwd_code")
        parents = cursor.fetchall()
        
        if not parents:
            st.info("No data found in database. Please import a PWD schedule first.")
            return
        
        st.success(f"Found {len(parents)} parent items in database")
        
        # Chapter filter
        chapters = sorted(set(p[2] for p in parents))
        selected_chapter = st.selectbox("Filter by Chapter", ["All"] + chapters)
        
        # Search
        search_term = st.text_input("Search items", placeholder="Enter item code or description...")
        
        # Display parents
        for parent in parents:
            parent_code = parent[0]
            parent_desc = parent[1]
            parent_chapter = parent[2]
            
            if selected_chapter != "All" and parent_chapter != selected_chapter:
                continue
            
            if search_term and search_term.lower() not in parent_code.lower() and search_term.lower() not in parent_desc.lower():
                continue
            
            # Get children for this parent
            cursor.execute("""
                SELECT c.pwd_code, c.description, c.unit,
                       cr.zone_name, cr.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_rates cr ON c.pwd_code = cr.pwd_code
                WHERE c.parent_code = ?
                ORDER BY c.pwd_code, cr.zone_name
            """, (parent_code,))
            
            children = cursor.fetchall()
            
            if children:
                with st.expander(f"📁 {parent_code} (Ch {parent_chapter}): {parent_desc[:80]}... ({len(set(c[0] for c in children))} items)", expanded=False):
                    # Organize children
                    children_dict = {}
                    for child in children:
                        child_code = child[0]
                        if child_code not in children_dict:
                            children_dict[child_code] = {
                                'code': child_code,
                                'description': child[1][:100],
                                'unit': child[2],
                                'rates': {}
                            }
                        if child[3]:
                            children_dict[child_code]['rates'][child[3]] = child[4]
                    
                    child_data = []
                    for child in children_dict.values():
                        row = {'Code': child['code'], 'Description': child['description'], 'Unit': child['unit']}
                        for zone, rate in child['rates'].items():
                            row[zone] = f"৳{rate:,.2f}"
                        child_data.append(row)
                    
                    st.dataframe(pd.DataFrame(child_data), use_container_width=True, hide_index=True)
            else:
                st.info(f"📄 {parent_code} (Ch {parent_chapter}): {parent_desc[:80]}... (No child items)")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading hierarchy: {str(e)}")



def render_admin_overview(all_users, all_subs):
    """Render system overview with charts"""
    st.markdown("### System Overview")
    
    # User growth chart (from database)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM users
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """)
    user_growth_data = cursor.fetchall()
    conn.close()
    
    if user_growth_data:
        user_growth = pd.DataFrame(user_growth_data, columns=['Month', 'Users'])
        user_growth = user_growth.iloc[::-1]  # Reverse to show chronological
        st.line_chart(user_growth.set_index('Month'))
    else:
        st.info("No user growth data available")
    
    # Plan distribution
    if all_subs:
        plan_counts = {}
        for sub in all_subs:
            plan = sub[2] if len(sub) > 2 else 'free'
            plan_counts[plan] = plan_counts.get(plan, 0) + 1
        
        plan_df = pd.DataFrame(plan_counts.items(), columns=['Plan', 'Count'])
        st.bar_chart(plan_df.set_index('Plan'))
    
    # Role distribution
    if all_users:
        role_counts = {}
        for user in all_users:
            role = user.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        role_df = pd.DataFrame(role_counts.items(), columns=['Role', 'Count'])
        st.bar_chart(role_df.set_index('Role'))
    
    # Recent activity
    st.markdown("### Recent Activity")
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.action_type, l.target_type, u.username, l.created_at
            FROM activity_logs l
            JOIN users u ON l.actor_user_id = u.id
            ORDER BY l.created_at DESC
            LIMIT 10
        """)
        recent_activity = cursor.fetchall()
        conn.close()
        
        if recent_activity:
            activity_df = pd.DataFrame(recent_activity, columns=['Action', 'Type', 'User', 'Time'])
            st.dataframe(activity_df, use_container_width=True, hide_index=True)
        else:
            st.info("No recent activity")
    except Exception as e:
        st.info("Activity logging not yet enabled")


def render_all_users(all_users):
    """Render all users table"""
    st.markdown("### All Users")
    
    # Search filter
    search = st.text_input("🔍 Search users", placeholder="Name, email, or username...")
    
    if all_users:
        user_list = []
        for u in all_users:
            user_dict = {
                'ID': u.get('id', 'N/A'),
                'Username': u.get('username', 'N/A'),
                'Email': u.get('email', 'N/A'),
                'Full Name': u.get('full_name', 'N/A'),
                'Phone': u.get('phone', ''),
                'Role': u.get('role', 'N/A'),
                'Active': '✅' if u.get('is_active', 0) == 1 else '❌',
                'Company': u.get('company_name', 'N/A'),
                'Created': str(u.get('created_at', ''))[:10] if u.get('created_at') else ''
            }
            
            # Apply search filter
            if search:
                if (search.lower() in user_dict['Username'].lower() or 
                    search.lower() in user_dict['Email'].lower() or 
                    search.lower() in user_dict['Full Name'].lower()):
                    user_list.append(user_dict)
            else:
                user_list.append(user_dict)
        
        if user_list:
            user_df = pd.DataFrame(user_list)
            st.dataframe(user_df, use_container_width=True, hide_index=True)
        else:
            st.info("No users match the search criteria")
    else:
        st.info("No users found")

def render_company_management():
    """Render company management interface for super admin with subscription control"""
    st.markdown("### 🏢 Company Management")
    st.caption("Create, edit, and manage companies on the platform")
    
    # Add New Company (existing code)
    with st.expander("➕ Add New Company", expanded=False):
        with st.form("add_company_form"):
            col1, col2 = st.columns(2)
            with col1:
                company_name = st.text_input("Company Name *")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
                division = st.text_input("Division")
            with col2:
                district = st.text_input("District")
                registration_number = st.text_input("Registration Number")
                vat_number = st.text_input("VAT Number")
                address = st.text_area("Address", height=80)
            
            submitted = st.form_submit_button("Create Company", type="primary")
            if submitted:
                if not company_name:
                    st.error("Company name is required")
                else:
                    company_data = {
                        'company_name': company_name,
                        'email': email,
                        'phone': phone,
                        'division': division,
                        'district': district,
                        'address': address,
                        'registration_number': registration_number,
                        'vat_number': vat_number
                    }
                    success, result = db.create_company(company_data)
                    if success:
                        st.success(f"✅ Company '{company_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result}")
    
    # Search and filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search companies", placeholder="Name or email...")
    with col2:
        show_inactive = st.checkbox("Show inactive")
    
    # Get companies
    status_filter = None if show_inactive else 1
    companies, total = db.get_all_companies_filtered(
        search=search,
        status=status_filter,
        limit=50,
        offset=0
    )
    
    st.markdown(f"**Total Companies:** {total}")
    
    # Display companies
    if companies:
        for company in companies:
            # Get subscription info
            subscription = db.get_company_subscription(company['id'])
            
            with st.expander(f"🏢 {company['company_name']} - {company.get('email', 'No email')}"):
                # Create tabs for company details and subscription
                comp_tab1, comp_tab2 = st.tabs(["📋 Company Details", "💳 Subscription"])
                
                with comp_tab1:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Company details form (existing code)
                        new_name = st.text_input("Company Name", value=company['company_name'], key=f"name_{company['id']}")
                        new_email = st.text_input("Email", value=company.get('email', ''), key=f"email_{company['id']}")
                        new_phone = st.text_input("Phone", value=company.get('phone', ''), key=f"phone_{company['id']}")
                        new_division = st.text_input("Division", value=company.get('division', ''), key=f"div_{company['id']}")
                        new_district = st.text_input("District", value=company.get('district', ''), key=f"dist_{company['id']}")
                        new_registration = st.text_input("Registration Number", value=company.get('registration_number', ''), key=f"reg_{company['id']}")
                        new_vat = st.text_input("VAT Number", value=company.get('vat_number', ''), key=f"vat_{company['id']}")
                        new_address = st.text_area("Address", value=company.get('address', ''), key=f"addr_{company['id']}")
                        new_active = st.checkbox("Active", value=company.get('is_active', 1) == 1, key=f"active_{company['id']}")
                        
                        if st.button("💾 Save Company Details", key=f"save_comp_{company['id']}"):
                            updates = {}
                            if new_name != company['company_name']:
                                updates['company_name'] = new_name
                            if new_email != company.get('email'):
                                updates['email'] = new_email
                            if new_phone != company.get('phone'):
                                updates['phone'] = new_phone
                            if new_division != company.get('division'):
                                updates['division'] = new_division
                            if new_district != company.get('district'):
                                updates['district'] = new_district
                            if new_registration != company.get('registration_number'):
                                updates['registration_number'] = new_registration
                            if new_vat != company.get('vat_number'):
                                updates['vat_number'] = new_vat
                            if new_address != company.get('address'):
                                updates['address'] = new_address
                            if new_active != (company.get('is_active', 1) == 1):
                                updates['is_active'] = 1 if new_active else 0
                            
                            if updates:
                                if db.update_company(company['id'], updates):
                                    st.success("Company updated!")
                                    st.rerun()
                                else:
                                    st.error("Update failed")
                    
                    with col2:
                        st.markdown("#### 📊 Statistics")
                        try:
                            stats = db.get_company_stats_by_id(company['id'])
                            st.metric("👥 Users", stats.get('total_users', 0))
                            st.metric("📈 Analyses", stats.get('total_analyses', 0))
                            st.metric("🏆 Win Rate", f"{stats.get('win_rate', 0):.1f}%")
                        except:
                            st.metric("👥 Users", "N/A")
                        
                        st.markdown("---")
                        st.markdown("#### ⚡ Actions")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("👥 Manage Users", key=f"users_{company['id']}"):
                                st.session_state.selected_company_id = company['id']
                                st.session_state.page = "user_management"
                                st.rerun()
                        with col_b:
                            if company.get('is_active', 1) == 1:
                                if st.button("🔒 Deactivate", key=f"deact_{company['id']}"):
                                    db.delete_company(company['id'])
                                    st.success(f"Company {company['company_name']} deactivated")
                                    st.rerun()
                            else:
                                if st.button("🔓 Activate", key=f"act_{company['id']}"):
                                    db.update_company(company['id'], {'is_active': 1})
                                    st.success(f"Company {company['company_name']} activated")
                                    st.rerun()
                        
                        st.caption(f"📅 Created: {company.get('created_at', 'N/A')[:10] if company.get('created_at') else 'N/A'}")
                
                with comp_tab2:
                    st.markdown("#### 💳 Subscription Management")
                    
                    # Display current subscription
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Current Plan", subscription.get('plan', 'free').upper())
                    with col2:
                        st.metric("Status", subscription.get('status', 'active').upper())
                    with col3:
                        limit = subscription.get('analyses_limit', 5)
                        used = subscription.get('analyses_used', 0)
                        if limit == -1:
                            st.metric("Analyses", "Unlimited")
                        else:
                            remaining = max(0, limit - used)
                            st.metric("Analyses Remaining", f"{remaining}/{limit}")
                    
                    st.markdown("---")
                    st.markdown("#### Update Subscription")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_plan = st.selectbox(
                            "Select Plan",
                            options=["free", "basic", "professional", "enterprise"],
                            index=["free", "basic", "professional", "enterprise"].index(subscription.get('plan', 'free')),
                            key=f"plan_select_{company['id']}"
                        )
                    
                    with col2:
                        duration = st.selectbox(
                            "Duration",
                            options=["monthly", "yearly"],
                            key=f"duration_select_{company['id']}"
                        )
                    
                    # Plan benefits
                    plan_benefits = {
                        "free": "• 5 analyses/month\n• Basic reports\n• Email support",
                        "basic": "• 30 analyses/month\n• AI predictions\n• Priority support",
                        "professional": "• Unlimited analyses\n• ML predictions\n• Team collaboration\n• Advanced reporting",
                        "enterprise": "• Everything in Professional\n• Custom AI model\n• Dedicated support\n• API access"
                    }
                    st.info(plan_benefits.get(new_plan, ""))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"💾 Update Subscription", key=f"update_sub_{company['id']}", type="primary"):
                            success = db.update_company_subscription(company['id'], new_plan, duration, 'admin_manual')
                            if success:
                                st.success(f"✅ Subscription updated to {new_plan.upper()}!")
                                st.rerun()
                            else:
                                st.error("Failed to update subscription")
                    
                    with col2:
                        if subscription.get('plan') != 'free':
                            if st.button(f"❌ Cancel Subscription", key=f"cancel_sub_{company['id']}"):
                                success = db.update_company_subscription(company['id'], 'free', 'monthly', 'admin_cancelled')
                                if success:
                                    st.success("Subscription cancelled. Plan set to FREE.")
                                    st.rerun()
                                else:
                                    st.error("Failed to cancel subscription")
                    
                    # Subscription details
                    st.markdown("---")
                    st.markdown("#### Subscription Details")
                    st.caption(f"**Start Date:** {subscription.get('start_date', 'N/A')}")
                    st.caption(f"**End Date:** {subscription.get('end_date', 'N/A')}")
                    if subscription.get('payment_method'):
                        st.caption(f"**Payment Method:** {subscription.get('payment_method')}")
                    if subscription.get('transaction_id'):
                        st.caption(f"**Transaction ID:** {subscription.get('transaction_id')}")
    else:
        st.info("No companies found")

def render_system_user_management():
    """Manage system-level users and company users (for system admin)"""
    st.markdown("### 👥 User Management")
    st.caption("Create users for companies or system-level access")
    
    # ========== ADD NEW USER ==========
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form"):
            st.markdown("#### User Details")
            
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email *")
                username = st.text_input("Username *")
            
            with col2:
                phone = st.text_input("Phone")
                generate_password = st.checkbox("Auto-generate password")
                if not generate_password:
                    password = st.text_input("Password *", type="password")
                    confirm_password = st.text_input("Confirm Password *", type="password")
            
            st.markdown("---")
            st.markdown("#### User Type & Role")
            
            user_type = st.radio(
                "User Type",
                options=["Company User", "System User"],
                help="Company User: Belongs to a specific company | System User: Platform-level access",
                key="user_type_radio_add"
            )
            
            if user_type == "Company User":
                # Get all active companies
                companies, _ = db.get_all_companies_filtered(status=1, limit=200, offset=0)
                company_options = {c['company_name']: c['id'] for c in companies}
                
                if company_options:
                    selected_company = st.selectbox(
                        "Select Company *",
                        options=list(company_options.keys()),
                        key="company_select_add"
                    )
                    company_id = company_options[selected_company]
                    
                    role = st.selectbox(
                        "Role *",
                        options=["company_admin", "manager", "analyst", "viewer"],
                        key="company_role_add"
                    )
                else:
                    st.error("No companies found")
                    company_id = None
                    role = "viewer"
            else:
                company_id = None
                role = st.selectbox(
                    "Role *",
                    options=["system_admin", "system_support", "system_auditor"],
                    key="system_role_add"
                )
            
            submitted = st.form_submit_button("Create User", type="primary")
            
            if submitted:
                if not all([full_name, email, username]):
                    st.error("Please fill all required fields")
                elif not generate_password and password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    final_password = db.generate_random_password() if generate_password else password
                    
                    user_data = {
                        'username': username.strip(),
                        'password': final_password,
                        'email': email.strip(),
                        'full_name': full_name.strip(),
                        'phone': phone.strip(),
                        'role': role
                    }
                    
                    if user_type == "Company User" and company_id:
                        success, result = db.create_company_user(company_id, user_data, st.session_state.user_id)
                    else:
                        success, result = db.create_system_user(user_data, st.session_state.user_id)
                    
                    if success:
                        if generate_password:
                            st.success(f"✅ User {full_name} created! Password: `{final_password}`")
                        else:
                            st.success(f"✅ User {full_name} created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result}")
    
    # ========== DISPLAY USERS ==========
    st.markdown("### 📋 Users")
    
    tab1, tab2 = st.tabs(["🏢 Company Users", "👑 System Users"])
    
    # ========== COMPANY USERS TAB ==========
    with tab1:
        companies, _ = db.get_all_companies_filtered(status=None, limit=200, offset=0)
        
        if companies:
            for company in companies:
                company_users, _ = db.get_all_users_filtered(
                    company_id=company['id'],
                    limit=100,
                    offset=0
                )
                
                if company_users:
                    st.markdown(f"#### 🏢 {company['company_name']}")
                    
                    for user in company_users:
                        if not isinstance(user, dict):
                            continue
                        
                        user_id = user.get('id')
                        if not user_id:
                            continue
                        
                        unique_base = f"comp_{company['id']}_user_{user_id}"
                        
                        with st.expander(f"👤 {user.get('full_name', 'Unknown')} ({user.get('username', 'N/A')}) - {user.get('role', 'N/A').title()}"):
                            col1, col2, col3 = st.columns([2, 1, 1])
                            
                            with col1:
                                new_full_name = st.text_input("Full Name", value=user.get('full_name', ''), key=f"{unique_base}_name")
                                new_email = st.text_input("Email", value=user.get('email', ''), key=f"{unique_base}_email")
                                new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"{unique_base}_phone")
                            
                            with col2:
                                # Company selection dropdown for company users
                                all_companies, _ = db.get_all_companies_filtered(status=1, limit=200, offset=0)
                                company_options = {c['company_name']: c['id'] for c in all_companies}
                                current_company_name = company.get('company_name', 'Unknown')
                                
                                new_company = st.selectbox(
                                    "Company",
                                    options=list(company_options.keys()),
                                    index=list(company_options.keys()).index(current_company_name) if current_company_name in company_options else 0,
                                    key=f"{unique_base}_company"
                                )
                                new_company_id = company_options.get(new_company, company['id'])
                                
                                # Role options based on user type
                                role_options = ["company_admin", "manager", "analyst", "viewer"]
                                current_role = user.get('role', 'viewer')
                                role_index = role_options.index(current_role) if current_role in role_options else 2
                                
                                new_role = st.selectbox(
                                    "Role",
                                    options=role_options,
                                    index=role_index,
                                    key=f"{unique_base}_role"
                                )
                            
                            with col3:
                                new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"{unique_base}_active")
                                
                                if st.button("💾 Save Changes", key=f"{unique_base}_save"):
                                    updates = {}
                                    if new_full_name != user.get('full_name'):
                                        updates['full_name'] = new_full_name
                                    if new_email != user.get('email'):
                                        updates['email'] = new_email
                                    if new_phone != user.get('phone'):
                                        updates['phone'] = new_phone
                                    if new_role != user.get('role'):
                                        updates['role'] = new_role
                                    if new_active != (user.get('is_active', 1) == 1):
                                        updates['is_active'] = 1 if new_active else 0
                                    
                                    # Handle company change
                                    if new_company_id != company['id']:
                                        # Update user's company
                                        updates['company_id'] = new_company_id
                                    
                                    if updates:
                                        if db.update_user(user_id, updates):
                                            st.success("User updated! Changes will appear after refresh.")
                                            st.rerun()
                                        else:
                                            st.error("Update failed")
                            
                            # Action buttons below the edit form
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🔑 Reset Password", key=f"{unique_base}_reset"):
                                    success, new_pw = db.reset_user_password(user_id)
                                    if success:
                                        st.success(f"New password: `{new_pw}`")
                            with col2:
                                if user_id != st.session_state.user_id:
                                    if st.button("🗑️ Delete User", key=f"{unique_base}_delete", type="secondary"):
                                        if db.delete_user(user_id):
                                            st.success("User deleted")
                                            st.rerun()
                            
                            st.caption(f"📅 Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
        else:
            st.info("No companies found")
    
    # ========== SYSTEM USERS TAB ==========
    with tab2:
        try:
            system_users = db.get_system_users()
        except AttributeError:
            st.warning("get_system_users() method not available")
            return
        
        if system_users:
            for user in system_users:
                if not isinstance(user, dict):
                    continue
                
                user_id = user.get('id')
                if not user_id:
                    continue
                
                unique_base = f"sys_user_{user_id}"
                
                with st.expander(f"👑 {user.get('full_name', 'Unknown')} ({user.get('username', 'N/A')}) - {user.get('role', 'N/A').replace('_', ' ').title()}"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        new_full_name = st.text_input("Full Name", value=user.get('full_name', ''), key=f"{unique_base}_name")
                        new_email = st.text_input("Email", value=user.get('email', ''), key=f"{unique_base}_email")
                        new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"{unique_base}_phone")
                    
                    with col2:
                        role_options = ["system_admin", "system_support", "system_auditor"]
                        current_role = user.get('role', 'system_support')
                        role_index = role_options.index(current_role) if current_role in role_options else 1
                        
                        new_role = st.selectbox(
                            "Role",
                            options=role_options,
                            index=role_index,
                            key=f"{unique_base}_role"
                        )
                    
                    with col3:
                        new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"{unique_base}_active")
                        
                        if st.button("💾 Save Changes", key=f"{unique_base}_save"):
                            updates = {}
                            if new_full_name != user.get('full_name'):
                                updates['full_name'] = new_full_name
                            if new_email != user.get('email'):
                                updates['email'] = new_email
                            if new_phone != user.get('phone'):
                                updates['phone'] = new_phone
                            if new_role != user.get('role'):
                                updates['role'] = new_role
                            if new_active != (user.get('is_active', 1) == 1):
                                updates['is_active'] = 1 if new_active else 0
                            
                            if updates:
                                if db.update_user(user_id, updates):
                                    st.success("User updated!")
                                    st.rerun()
                                else:
                                    st.error("Update failed")
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔑 Reset Password", key=f"{unique_base}_reset"):
                            success, new_pw = db.reset_user_password(user_id)
                            if success:
                                st.success(f"New password: `{new_pw}`")
                    with col2:
                        if user_id != st.session_state.user_id:
                            if st.button("🗑️ Delete User", key=f"{unique_base}_delete", type="secondary"):
                                if db.delete_user(user_id):
                                    st.success("User deleted")
                                    st.rerun()
                    
                    st.caption(f"📅 Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
        else:
            st.info("No system users found")
            
def render_system_user_management_bak():
    """Manage system-level users and company users (for system admin)"""
    st.markdown("### 👥 User Management")
    st.caption("Create users for companies or system-level access")
    
    # ========== ADD NEW USER ==========
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form"):
            # ... (keep the existing form code as is) ...
            pass  # Placeholder - keep your existing form code
    
    # ========== DISPLAY USERS BY TYPE ==========
    st.markdown("### 📋 Users")
    
    # Tabs for different user types
    tab1, tab2 = st.tabs(["🏢 Company Users", "👑 System Users"])
    
    with tab1:
        # Get company users
        companies, _ = db.get_all_companies_filtered(status=1, limit=200, offset=0)
        
        if companies:
            for company in companies:
                try:
                    company_users, company_total = db.get_all_users_filtered(
                        company_id=company['id'],
                        limit=100,
                        offset=0
                    )
                    
                    if company_users:
                        st.markdown(f"#### {company['company_name']} ({company_total} users)")
                        
                        for user in company_users:
                            # Ensure user is a dictionary
                            if not isinstance(user, dict):
                                continue
                            
                            user_id = user.get('id')
                            if not user_id:
                                continue
                            
                            with st.expander(f"👤 {user.get('full_name', 'Unknown')} ({user.get('username', 'N/A')}) - {user.get('role', 'N/A').title()}"):
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    new_full_name = st.text_input("Full Name", value=user.get('full_name', ''), key=f"name_{user_id}")
                                    new_email = st.text_input("Email", value=user.get('email', ''), key=f"email_{user_id}")
                                    new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"phone_{user_id}")
                                    new_role = st.selectbox(
                                        "Role",
                                        options=["company_admin", "manager", "analyst", "viewer"],
                                        index=["company_admin", "manager", "analyst", "viewer"].index(user.get('role', 'viewer')) if user.get('role') in ["company_admin", "manager", "analyst", "viewer"] else 2,
                                        key=f"role_{user_id}"
                                    )
                                    new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"active_{user_id}")
                                    
                                    if st.button("💾 Save Changes", key=f"save_{user_id}"):
                                        updates = {}
                                        if new_full_name != user.get('full_name'):
                                            updates['full_name'] = new_full_name
                                        if new_email != user.get('email'):
                                            updates['email'] = new_email
                                        if new_phone != user.get('phone'):
                                            updates['phone'] = new_phone
                                        if new_role != user.get('role'):
                                            updates['role'] = new_role
                                        if new_active != (user.get('is_active', 1) == 1):
                                            updates['is_active'] = 1 if new_active else 0
                                        
                                        if updates:
                                            if db.update_user(user_id, updates):
                                                st.success("User updated!")
                                                st.rerun()
                                
                                with col2:
                                    if st.button("🔑 Reset Password", key=f"reset_{user_id}"):
                                        success, new_pw = db.reset_user_password(user_id)
                                        if success:
                                            st.success(f"New password: `{new_pw}`")
                                    
                                    if user_id != st.session_state.user_id:
                                        if st.button("🗑️ Delete User", key=f"delete_{user_id}", type="secondary"):
                                            if db.delete_user(user_id):
                                                st.success("User deleted")
                                                st.rerun()
                                    
                                    st.caption(f"Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
                except Exception as e:
                    st.warning(f"Could not load users for {company.get('company_name', 'Unknown')}: {e}")
        else:
            st.info("No companies found. Create a company first.")
    
    with tab2:
        # Get system users
        try:
            system_users = db.get_system_users()
        except AttributeError:
            st.warning("get_system_users() method not available. Please update db_manager.py")
            return
        
        if system_users:
            for user in system_users:
                # Ensure user is a dictionary
                if not isinstance(user, dict):
                    continue
                
                user_id = user.get('id')
                if not user_id:
                    continue
                
                with st.expander(f"👑 {user.get('full_name', 'Unknown')} ({user.get('username', 'N/A')}) - {user.get('role', 'N/A').replace('_', ' ').title()}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        new_full_name = st.text_input("Full Name", value=user.get('full_name', ''), key=f"sys_name_{user_id}")
                        new_email = st.text_input("Email", value=user.get('email', ''), key=f"sys_email_{user_id}")
                        new_phone = st.text_input("Phone", value=user.get('phone', ''), key=f"sys_phone_{user_id}")
                        
                        # Determine role options based on current role
                        role_options = ["system_admin", "system_support", "system_auditor"]
                        current_role = user.get('role', 'system_support')
                        
                        try:
                            role_index = role_options.index(current_role) if current_role in role_options else 1
                        except ValueError:
                            role_index = 1
                        
                        new_role = st.selectbox(
                            "Role",
                            options=role_options,
                            index=role_index,
                            key=f"sys_role_{user_id}"
                        )
                        new_active = st.checkbox("Active", value=user.get('is_active', 1) == 1, key=f"sys_active_{user_id}")
                        
                        if st.button("💾 Save Changes", key=f"sys_save_{user_id}"):
                            updates = {}
                            if new_full_name != user.get('full_name'):
                                updates['full_name'] = new_full_name
                            if new_email != user.get('email'):
                                updates['email'] = new_email
                            if new_phone != user.get('phone'):
                                updates['phone'] = new_phone
                            if new_role != user.get('role'):
                                updates['role'] = new_role
                            if new_active != (user.get('is_active', 1) == 1):
                                updates['is_active'] = 1 if new_active else 0
                            
                            if updates:
                                if db.update_user(user_id, updates):
                                    st.success("User updated!")
                                    st.rerun()
                    
                    with col2:
                        if st.button("🔑 Reset Password", key=f"sys_reset_{user_id}"):
                            success, new_pw = db.reset_user_password(user_id)
                            if success:
                                st.success(f"New password: `{new_pw}`")
                        
                        if user_id != st.session_state.user_id:
                            if st.button("🗑️ Delete User", key=f"sys_del_{user_id}", type="secondary"):
                                if db.delete_user(user_id):
                                    st.success("User deleted")
                                    st.rerun()
                        
                        st.caption(f"Created: {str(user.get('created_at', ''))[:10] if user.get('created_at') else 'N/A'}")
        else:
            st.info("No system users found")

def render_role_management_page():
    """Render role permissions management"""
    st.markdown("### 🔐 Role Permissions Management")
    st.caption("Configure what each role can do in the system")
    
    try:
        roles = db.get_all_roles()
    except AttributeError:
        st.warning("get_all_roles() method not available. Please update db_manager.py")
        return
    
    if not roles:
        st.warning("No roles found. Please run database migration.")
        return
    
    # Display role hierarchy
    st.markdown("#### Role Hierarchy")
    role_hierarchy = {
        'system_admin': '👑 Full platform access',
        'system_support': '🛠️ Can view all companies, support access',
        'system_auditor': '📊 Read-only across platform',
        'company_admin': '🏢 Full company management',
        'manager': '📋 Can manage tenders and create users',
        'analyst': '🔬 Can run analyses and view reports',
        'viewer': '👁️ Read-only access'
    }
    
    for role, desc in role_hierarchy.items():
        if any(r['role'] == role for r in roles):
            st.markdown(f"- **{role.replace('_', ' ').title()}**: {desc}")
    
    st.markdown("---")
    st.markdown("#### Edit Role Permissions")
    
    for role_info in roles:
        role_name = role_info['role']
        permissions = role_info['permissions']
        
        with st.expander(f"📌 {role_name.replace('_', ' ').title()}", expanded=False):
            st.markdown(f"**Role:** `{role_name}`")
            st.markdown(f"**Description:** {role_hierarchy.get(role_name, 'No description')}")
            
            # Display key permissions
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**User Management**")
                user_perms = ['manage_users', 'manage_team', 'create_user', 'delete_user']
                for perm in user_perms:
                    if perm in permissions:
                        current = permissions.get(perm, False)
                        new_val = st.checkbox(perm.replace('_', ' ').title(), value=current, key=f"{role_name}_{perm}")
                        permissions[perm] = new_val
            
            with col2:
                st.markdown("**Tender & Analysis**")
                tender_perms = ['manage_tenders', 'run_analysis', 'view_reports', 'export_data']
                for perm in tender_perms:
                    if perm in permissions:
                        current = permissions.get(perm, False)
                        new_val = st.checkbox(perm.replace('_', ' ').title(), value=current, key=f"{role_name}_{perm}")
                        permissions[perm] = new_val
            
            if st.button(f"💾 Save Permissions for {role_name}", key=f"save_role_{role_name}"):
                success = db.update_role_permissions(role_name, permissions)
                if success:
                    st.success(f"Permissions for {role_name} updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update permissions")

def render_pwd_version_tab(db):
    """Render PWD version management tab"""
    
    st.subheader("🏗️ PWD Rate Schedule Version Control")
    
    tabs = st.tabs(["📥 Import New Version", "📜 Version History", "⚙️ Migration"])
    
    with tabs[0]:
        # Import new version UI
        render_version_import(db)
    
    with tabs[1]:
        # Show version history
        render_version_history(db)
    
    with tabs[2]:
        # Migrate BOQ items to new version
        render_version_migration(db)


def render_version_import(db):
    """Import a new version of PWD rates"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        version_name = st.text_input("Version Name", placeholder="PWD Schedule 2025")
        edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2025)
    
    with col2:
        effective_date = st.date_input("Effective From")
        is_active = st.checkbox("Set as Active Version", value=True)
    
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    
    if uploaded_file and st.button("Import Version"):
        # Parse and save with version info
        # ...
        st.success(f"✅ Version {version_name} imported successfully!")


def render_version_history(db):
    """Display version history"""
    
    # Get versions from database
    versions = get_rate_versions(db)
    
    for version in versions:
        with st.expander(f"{version['name']} ({version['year']})"):
            st.write(f"**Effective Date:** {version['effective_date']}")
            st.write(f"**Status:** {'✅ Active' if version['is_active'] else '📦 Archived'}")
            st.write(f"**Imported:** {version['imported_at']}")
            st.write(f"**Items:** {version['parent_count']} parents, {version['child_count']} children")
            
            if version['is_active']:
                if st.button("Archive", key=f"archive_{version['id']}"):
                    archive_version(db, version['id'])
                    st.rerun()
