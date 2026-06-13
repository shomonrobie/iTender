# debug_qry.py - FIXED ENCODING VERSION

import sqlite3
import os
import sys

db_path = "data/tender_system.db"

def check_database_structure():
    """Check all tables and their structure in the database"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    # First connection for main inspection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("="*60)
    print("DATABASE STRUCTURE CHECK")
    print("="*60)
    print(f"Database path: {os.path.abspath(db_path)}")
    print()
    
    # 1. Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print(f"📊 TOTAL TABLES: {len(tables)}")
    print("-"*40)
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 TABLE: {table_name}")
        print("-"*30)
        
        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"   Columns ({len(columns)}):")
        for col in columns:
            col_id, col_name, col_type, notnull, default_val, pk = col
            pk_marker = "🔑 PRIMARY KEY" if pk else ""
            null_marker = "NOT NULL" if notnull else ""
            default_marker = f"DEFAULT {default_val}" if default_val is not None else ""
            print(f"     - {col_name}: {col_type} {null_marker} {default_marker} {pk_marker}".strip())
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        print(f"   📈 Row count: {row_count}")
    
    # 2. Specifically check companies table in detail
    print("\n" + "="*60)
    print("🔍 DETAILED COMPANIES TABLE CHECK")
    print("="*60)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
    if cursor.fetchone():
        # Get all columns
        cursor.execute("PRAGMA table_info(companies)")
        columns = cursor.fetchall()
        
        print("\n📋 Companies Table Columns:")
        for col in columns:
            col_id, col_name, col_type, notnull, default_val, pk = col
            null_str = "NOT NULL" if notnull else "NULL"
            print(f"   - {col_name}: {col_type} ({null_str})")
        
        # Get sample data
        cursor.execute("SELECT * FROM companies LIMIT 5")
        sample_rows = cursor.fetchall()
        
        if sample_rows:
            print(f"\n📊 Sample Data ({len(sample_rows)} rows):")
            col_names = [col[1] for col in columns]
            for row in sample_rows:
                print("\n   Row:")
                for i, col_name in enumerate(col_names):
                    value = row[i] if i < len(row) else None
                    print(f"     {col_name}: {value}")
        else:
            print("\n⚠️ No data in companies table")
            
        # Check for required columns
        required_columns = ['id', 'company_name', 'is_active', 'created_at']
        existing_columns = [col[1] for col in columns]
        
        print("\n✅ Required Columns Check:")
        for req_col in required_columns:
            if req_col in existing_columns:
                print(f"   ✓ {req_col} exists")
            else:
                print(f"   ✗ {req_col} MISSING!")
    
    else:
        print("❌ Companies table does NOT exist!")
    
    # 3. Check migration tracking
    print("\n" + "="*60)
    print("🔍 MIGRATION TRACKING")
    print("="*60)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
    if cursor.fetchone():
        cursor.execute("SELECT version, name, applied_at, success FROM schema_migrations ORDER BY id")
        migrations = cursor.fetchall()
        
        print(f"\n📋 Applied Migrations ({len(migrations)}):")
        for mig in migrations:
            version, name, applied_at, success = mig
            status = "✅" if success else "❌"
            applied_at_str = applied_at if applied_at else "N/A"
            print(f"   {status} {version} - {name} (applied: {applied_at_str})")
    else:
        print("⚠️ schema_migrations table not found - migrations may not be tracked")
    
    # 4. Check for missing tables needed by the app
    print("\n" + "="*60)
    print("🔍 REQUIRED TABLES CHECK")
    print("="*60)
    
    required_tables = [
        'companies',
        'users', 
        'subscriptions',
        'subscription_plans',
        'tender_analyses',
        'extension_auto_fill_log',
        'personnel',
        'equipment',
        'experience_record',
        'financial_capacity',
        'document_registry',
        'company_profile'
    ]
    
    missing_tables = []
    for req_table in required_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{req_table}'")
        if cursor.fetchone():
            print(f"   ✅ {req_table}")
        else:
            print(f"   ❌ {req_table} - MISSING!")
            missing_tables.append(req_table)
    
    # 5. Close the first connection
    conn.close()
    
    return missing_tables


def fix_missing_version_attributes():
    """Fix missing version attributes in migration files with proper encoding"""
    import os
    
    migrations_dir = "migrations"
    if not os.path.exists(migrations_dir):
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return
    
    print("\n" + "="*60)
    print("🔧 FIXING MIGRATION VERSION ATTRIBUTES")
    print("="*60)
    
    migration_files = [
        'v001_initial_schema.py',
        'v002_add_subscription_permissions.py',
        'v003_add_rate_chapters_sections.py',
        'v004_add_company_subscriptions.py',
        'v006_boq_tables.py',
        'v007_scenarion_tables.py',
        'v008_extension_tables.py',
        'v009_knowledge_repository.py',
        'v010_fix_companies_table.py'
    ]
    
    for filename in migration_files:
        filepath = os.path.join(migrations_dir, filename)
        if os.path.exists(filepath):
            try:
                # Try different encodings
                content = None
                for encoding in ['utf-8', 'latin-1', 'cp1252', 'utf-16']:
                    try:
                        with open(filepath, 'r', encoding=encoding) as f:
                            content = f.read()
                        print(f"   Read {filename} with {encoding} encoding")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    print(f"   ❌ Could not read {filename} - encoding issue")
                    continue
                
                # Extract version from filename
                version = filename.replace('.py', '')
                
                # Check if version attribute exists
                if 'version = "' not in content and "version = '" not in content:
                    # Add version attribute at the top
                    new_content = f'version = "{version}"\n\n{content}'
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"   ✅ Added version attribute to {filename}")
                else:
                    print(f"   ⏭️  {filename} already has version attribute")
            except Exception as e:
                print(f"   ⚠️ Error processing {filename}: {e}")
        else:
            print(f"   ⚠️ {filename} not found")


def quick_fix_all_tables():
    """Quick fix to create all missing tables"""
    import sqlite3
    
    print("\n" + "="*60)
    print("🔧 RUNNING QUICK FIX FOR ALL TABLES")
    print("="*60)
    
    if not os.path.exists(db_path):
        print(f"❌ Database directory not found, creating...")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create companies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            registration_number TEXT,
            vat_number TEXT,
            address TEXT,
            district TEXT,
            division TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            is_individual BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ companies table checked/created")
    
    # Insert default company if empty
    cursor.execute("SELECT COUNT(*) FROM companies")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO companies (company_name, email, is_active)
            VALUES ('System Admin', 'admin@tenderai.com', 1)
        """)
        print("   ✅ Default company inserted")
    
    # Create users table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            phone TEXT,
            role TEXT DEFAULT 'user',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
    """)
    print("   ✅ users table checked/created")
    
    # Create extension_auto_fill_log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extension_auto_fill_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            field_label TEXT,
            confidence_score REAL,
            page_url TEXT,
            filled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ extension_auto_fill_log table checked/created")
    
    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_extension_log_company 
        ON extension_auto_fill_log(company_id, filled_at)
    """)
    print("   ✅ Index created on extension_auto_fill_log")
    
    # Create personnel table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            designation TEXT NOT NULL,
            employee_id TEXT,
            nid_number TEXT,
            date_of_birth DATE,
            personal_phone TEXT,
            personal_email TEXT,
            joining_date DATE,
            educational_qualification TEXT,
            skills TEXT,
            is_key_personnel BOOLEAN DEFAULT 0,
            employment_status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER
        )
    """)
    print("   ✅ personnel table checked/created")
    
    # Create equipment table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            equipment_name TEXT NOT NULL,
            equipment_type TEXT,
            model TEXT,
            serial_number TEXT,
            capacity REAL,
            ownership_type TEXT,
            purchase_date DATE,
            purchase_cost REAL,
            current_status TEXT DEFAULT 'available',
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER
        )
    """)
    print("   ✅ equipment table checked/created")
    
    # Create experience_record table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experience_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            client_name TEXT NOT NULL,
            contract_value REAL,
            completion_date DATE,
            nature_of_work TEXT,
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER
        )
    """)
    print("   ✅ experience_record table checked/created")
    
    # Create financial_capacity table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_capacity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            fiscal_year TEXT NOT NULL,
            annual_turnover REAL,
            net_worth REAL,
            working_capital REAL,
            credit_limit REAL,
            is_audited BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ financial_capacity table checked/created")
    
    # Create company_profile table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL UNIQUE,
            legal_name TEXT,
            trade_name TEXT,
            registration_number TEXT,
            registered_address TEXT,
            phone_primary TEXT,
            email_primary TEXT,
            division TEXT,
            district TEXT,
            website TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER
        )
    """)
    print("   ✅ company_profile table checked/created")
    
    # Create document_registry table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            document_uuid TEXT UNIQUE NOT NULL,
            document_name TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT,
            file_size INTEGER,
            mime_type TEXT,
            description TEXT,
            tags TEXT,
            category TEXT,
            document_date DATE,
            expiry_date DATE,
            extracted_text TEXT,
            version_number INTEGER DEFAULT 1,
            is_latest_version BOOLEAN DEFAULT 1,
            uploaded_by INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ document_registry table checked/created")
    
    # Insert default admin user if no users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        import bcrypt
        hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("""
            INSERT INTO users (company_id, username, password, email, full_name, role, is_active)
            VALUES (1, 'admin', ?, 'admin@tenderai.com', 'System Administrator', 'system_admin', 1)
        """, (hashed,))
        print("   ✅ Default admin user created (username: admin, password: admin123)")
    
    conn.commit()
    conn.close()
    
    print("\n✅ All tables created/verified successfully!")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("TenderAI Database Diagnostic Tool")
    print("="*60)
    
    # First check database structure
    missing_tables = check_database_structure()
    
    # Fix missing version attributes in migration files
    fix_missing_version_attributes()
    
    # Check if there are missing tables
    if missing_tables:
        print("\n" + "="*60)
        print(f"⚠️ Missing tables detected: {len(missing_tables)}")
        print("="*60)
        
        response = input("\nDo you want to create all missing tables automatically? (y/n): ")
        if response.lower() == 'y':
            quick_fix_all_tables()
        else:
            print("\n⚠️ Skipping table creation. You can run the script again later.")
    else:
        print("\n✅ No missing tables detected!")
    
    print("\n" + "="*60)
    print("✅ Script completed!")
    print("\nNext steps:")
    print("1. Restart your Streamlit app: streamlit run main.py")
    print("2. The extension admin page should now work")
    print("="*60)