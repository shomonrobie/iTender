"""
Database Manager for TenderAI System
Handles all database operations including users, subscriptions, tenders, and competitor tracking
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from unittest import result
import pandas as pd
import numpy as np
import logging
import bcrypt
import os
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Union  # ← Add this line
import secrets
import string


logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        # Only initialize if tables don't exist
        if not self._tables_exist():
            self.init_database()
    
    def _tables_exist(self):
        """Check if database tables already exist"""
        conn = self.get_connection()        
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def get_connection(self):
        """Get a fresh SQLite connection with FK enforcement"""
        import os
        conn = sqlite3.connect(self.db_path)
        #print(f"🗄️ APP DB PATH: {os.path.abspath(self.db_path)}")  # Adjust variable name to match yours
        conn.row_factory = sqlite3.Row  # Optional: enables dict-like access
        #conn.execute("PRAGMA foreign_keys = ON;")        
        
        return conn
        
    
    def init_database(self):
        """Initialize all database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ==================== EXISTING TABLES ====================
        
        # Companies table
        cursor.execute('''
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
        ''')
        
        # Users table
        cursor.execute('''
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
        ''')
        
        # Subscriptions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan TEXT DEFAULT 'free',
            status TEXT DEFAULT 'active',
            start_date DATE,
            end_date DATE,
            analyses_used INTEGER DEFAULT 0,
            analyses_limit INTEGER DEFAULT 5,
            payment_method TEXT,
            transaction_id TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
                
        # 3. Create consultant-client mapping table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS consultant_clients (
            id INTEGER PRIMARY KEY,
            consultant_user_id INTEGER REFERENCES users(id),
            client_company_id INTEGER REFERENCES companies(id),
            role TEXT DEFAULT 'manager',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(consultant_user_id, client_company_id)
        )''')

        # 4. Indexes for fast lookups
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sub_user ON subscriptions(user_id);
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sub_company ON subscriptions(company_id);
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_consultant_client ON consultant_clients(consultant_user_id);
        ''')
        # Tender analyses table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tender_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company_id INTEGER,
            tender_id TEXT,
            tender_title TEXT,
            procuring_entity TEXT,
            division TEXT,
            construction_type TEXT,
            official_estimate REAL,
            recommended_bid REAL,
            actual_bid REAL,
            success_probability REAL,
            risk_level TEXT,
            competitor_count INTEGER,
            bid_status TEXT,
            analysis_type TEXT,
            analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
        ''')
        
        # Contact messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'unread',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # ==================== HISTORICAL DATA TABLES ====================
        
        # Historical tenders table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company_id INTEGER,
            tender_id TEXT,
            tender_title TEXT,
            procuring_entity TEXT,
            procurement_type TEXT,
            official_estimate REAL,
            awarded_price REAL,
            num_competitors INTEGER,
            total_bidders INTEGER,
            our_rank INTEGER,
            award_date DATE,
            competitors_data TEXT,
            winning_competitor TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
        ''')
        
        # Company NPPI table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_nppi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            procurement_type TEXT,
            nppi_factor REAL,
            data_points INTEGER,
            calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (actor_user_id) REFERENCES users(id)
            -- Index for fast lookups
            CREATE INDEX IF NOT EXISTS idx_activity_company ON activity_logs(company_id);
            CREATE INDEX IF NOT EXISTS idx_activity_actor ON activity_logs(actor_user_id);
            CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_logs(created_at);
        )
        ''')

       
        # ==================== COMPETITOR MASTER TABLE ====================
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitor_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            competitor_name TEXT,
            business_type TEXT,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            notes TEXT,
            first_seen DATE,
            last_seen DATE,
            total_bids INTEGER DEFAULT 0,
            total_wins INTEGER DEFAULT 0,
            avg_bid_ratio REAL DEFAULT 0.90,
            preferred_strategy TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id),
            UNIQUE(company_id, competitor_name)
        )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT UNIQUE NOT NULL,
                permissions TEXT,  -- JSON string of permissions
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_company ON historical_tenders(company_id, procurement_type, award_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nppi_company ON company_nppi(company_id, procurement_type, calculation_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_competitor_master ON competitor_master(company_id, competitor_name)')
        
        # ==================== DEFAULT DATA ====================
        
        # Create default admin company if not exists
        cursor.execute('INSERT OR IGNORE INTO companies (company_name) VALUES ("System Admin")')
        cursor.execute('SELECT id FROM companies WHERE company_name = "System Admin"')
        admin_company_id = cursor.fetchone()[0]
        
        # Create admin user
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute('''
        INSERT OR IGNORE INTO users (company_id, username, password, email, full_name, role)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (admin_company_id, "admin", admin_pass, "admin@tenderai.com", "System Administrator", "admin"))
        
        # Create demo company
        cursor.execute('''
        INSERT OR IGNORE INTO companies (company_name, email, phone, division)
        VALUES (?, ?, ?, ?)
        ''', ("ABC Construction Ltd", "info@abcconstruction.com", "017XXXXXXXX", "Dhaka"))
        
        cursor.execute('SELECT id FROM companies WHERE company_name = "ABC Construction Ltd"')
        demo_company = cursor.fetchone()
        
        if demo_company:
            demo_company_id = demo_company[0]
            
            # Create demo users
            demo_users = [
                ("john.doe", "John@123", "john@abcconstruction.com", "John Doe", "company_admin"),
                ("jane.smith", "Jane@123", "jane@abcconstruction.com", "Jane Smith", "manager"),
                ("rahim.khan", "Rahim@123", "rahim@abcconstruction.com", "Rahim Khan", "analyst"),
            ]
            
            for user in demo_users:
                hashed_pass = hashlib.sha256(user[1].encode()).hexdigest()
                cursor.execute('''
                INSERT OR IGNORE INTO users (company_id, username, password, email, full_name, role)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (demo_company_id, user[0], hashed_pass, user[2], user[3], user[4]))
        
        # Insert default role permissions if not present
        default_permissions = {
            'admin': {
                'manage_users': True, 'manage_tenders': True, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': True,
                'manage_team': True, 'delete_any': True
            },
            'company_admin': {
                'manage_users': True, 'manage_tenders': True, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': True,
                'manage_team': True, 'delete_any': False
            },
            'manager': {
                'manage_users': False, 'manage_tenders': True, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': False,
                'manage_team': False, 'delete_any': False
            },
            'analyst': {
                'manage_users': False, 'manage_tenders': False, 'run_analysis': True,
                'view_reports': True, 'export_data': False, 'change_plans': False,
                'manage_team': False, 'delete_any': False
            },
            'viewer': {
                'manage_users': False, 'manage_tenders': False, 'run_analysis': False,
                'view_reports': True, 'export_data': False, 'change_plans': False,
                'manage_team': False, 'delete_any': False
            }
        }
        for role, perms in default_permissions.items():
            import json
            cursor.execute('''
            INSERT OR IGNORE INTO role_permissions (role, permissions) VALUES (?, ?)
            ''', (role, json.dumps(perms)))

        conn.commit()
        conn.close()
        print("Database initialized successfully")
    
    # ==================== AUTHENTICATION METHODS ====================
    def store_password_reset_token(self, email: str, token: str, expires_in_minutes: int = 60):
        """Store password reset token"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            expires_at = (datetime.now() + timedelta(minutes=expires_in_minutes)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT OR REPLACE INTO password_reset_tokens 
                (email, token, expires_at) 
                VALUES (?, ?, ?)
            ''', (email, token, expires_at))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store reset token: {e}")
            return False
        finally:
            conn.close()

    def verify_reset_token(self, token: str):
        """Verify reset token and return email if valid"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT email FROM password_reset_tokens 
                WHERE token = ? AND expires_at > ?
            ''', (token, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def update_password(self, email: str, new_password: str):
        """Update user password with bcrypt"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed, email))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def authenticate_user(self, username, password):
        """Improved authentication with clear error messages"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT u.id, u.username, u.email, u.full_name, u.role, u.is_active, 
                u.company_id, u.password, u.last_login, u.is_approved, u.account_type
            FROM users u
            WHERE (u.username = ? OR u.email = ?)
            ''', (username, username))
            
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return None, "invalid_credentials", "❌ Username or email not found."

            is_active = user[5]
            if not is_active:
                conn.close()
                return None, "inactive", "⚠️ Your account is inactive. Please contact support."

            stored_pass = user[7]  # password column
            
            password_match = False
            error_message = "❌ Invalid password."
            
            if stored_pass and password:
                try:
                    if str(stored_pass).startswith('$2b$') or str(stored_pass).startswith('$2y$'):
                        # bcrypt hash
                        import bcrypt
                        password_match = bcrypt.checkpw(
                            password.encode('utf-8'), 
                            str(stored_pass).encode('utf-8')
                        )
                    else:
                        # Legacy SHA256
                        import hashlib
                        hashed_input = hashlib.sha256(password.encode()).hexdigest()
                        password_match = (hashed_input == stored_pass)
                except Exception as e:
                    print(f"Hash verification error: {e}")
                    password_match = False

            if not password_match:
                conn.close()
                return None, "invalid_password", error_message

            # Success - update last login
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (now_str, user[0]))
            conn.commit()
            conn.close()
            
            status = "approved" if user[9] else "pending_approval"
            return user, status, "success"

        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return None, "auth_error", "❌ System error during login. Please try again."


    
    def create_user(self, company_id, user_data, created_by):
        """Create a new user with pending approval"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        hashed_pass = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute('''
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, role,
                    is_active, created_by, is_approved, account_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_id, user_data['username'], hashed_pass, user_data['email'],
                    user_data['full_name'], user_data.get('phone', ''), user_data.get('role', 'user'),
                    1, created_by, 0,  # is_approved = 0 (pending)
                    user_data.get('account_type', 'company')
                ))
            user_id = cursor.lastrowid
            
            # Create subscription record (pending approval)
            cursor.execute('''
            INSERT INTO subscriptions (user_id, plan, status, analyses_limit)
            VALUES (?, 'free', 'pending_approval', 0)
            ''', (user_id,))
            
            conn.commit()
            
            # Log the registration
            self.log_team_activity(company_id, user_id, "registration", "user", str(user_id), 
                                f"New user registration pending approval: {user_data['username']}")
            
            return True, user_id
        except sqlite3.IntegrityError as e:
            return False, str(e)
        finally:
            conn.close()



    
    def create_company_bak(self, company_data):
        """Create a new company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO companies (company_name, email, phone, division)
            VALUES (?, ?, ?, ?)
            ''', (company_data['company_name'], company_data.get('email', ''), 
                  company_data.get('phone', ''), company_data.get('division', 'Dhaka')))
            company_id = cursor.lastrowid
            conn.commit()
            return True, company_id
        except sqlite3.IntegrityError:
            return False, "Company name already exists"
        finally:
            conn.close()
    
    # ==================== USER MANAGEMENT METHODS ====================
    
    def get_all_users(self, company_id=None, role=None):
        """Get all users as dictionaries"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
            u.created_at, u.last_login, c.company_name, u.is_approved
        FROM users u
        JOIN companies c ON u.company_id = c.id
        WHERE 1=1
        '''
        params = []
        
        if company_id:
            query += " AND u.company_id = ?"
            params.append(company_id)
        if role:
            query += " AND u.role = ?"
            params.append(role)
        
        query += " ORDER BY u.created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        users = []
        for row in rows:
            users.append({
                'id': row[0], 'username': row[1], 'email': row[2], 'full_name': row[3],
                'phone': row[4], 'role': row[5], 'is_active': row[6],
                'created_at': row[7], 'last_login': row[8], 'company_name': row[9],
                'is_approved': row[10] if len(row) > 10 else 1
            })
        return users

    def update_user_bak(self, user_id: int, updates: dict) -> bool:
        """Update user fields (full_name, email, phone, role, is_active)"""
        allowed_fields = ['full_name', 'email', 'phone', 'role', 'is_active']
        set_clause = []
        params = []
        for field, value in updates.items():
            if field in allowed_fields:
                set_clause.append(f"{field} = ?")
                params.append(value)
        if not set_clause:
            return False
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(set_clause)} WHERE id = ?"
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update user failed: {e}")
            return False
        finally:
            conn.close()

    def reset_user_password_bak(self, user_id: int, new_password: str) -> bool:
        """Reset user password (bcrypt hash)"""
        import bcrypt
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            return False
        finally:
            conn.close()

    def delete_user_bak(self, user_id: int) -> bool:
        """Soft delete or hard delete? We'll hard delete for simplicity"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Delete user failed: {e}")
            return False
        finally:
            conn.close()

    def get_all_users_bak(self, company_id=None, role=None):
        """Get all users with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
               u.created_at, u.last_login, c.company_name
        FROM users u
        JOIN companies c ON u.company_id = c.id
        WHERE 1=1
        '''
        params = []
        
        if company_id:
            query += " AND u.company_id = ?"
            params.append(company_id)
        if role:
            query += " AND u.role = ?"
            params.append(role)
        
        query += " ORDER BY u.created_at DESC"
        
        cursor.execute(query, params)
        users = cursor.fetchall()
        conn.close()
        return users
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT u.*, c.company_name, c.id as company_id
        FROM users u
        JOIN companies c ON u.company_id = c.id
        WHERE u.id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def update_user_role(self, user_id, new_role, updated_by):
        """Update user role"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        conn.close()
        return True
    
    def update_user_status(self, user_id, is_active):
        """Activate/deactivate user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (is_active, user_id))
        conn.commit()
        conn.close()
    
    def delete_user(self, user_id):
        """Delete user (non-admin only)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ? AND role != "admin"', (user_id,))
        cursor.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    # ==================== SUBSCRIPTION METHODS ====================
    
    def get_user_subscription(self, user_id):
        """Get user's subscription details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT plan, status, start_date, end_date, analyses_used, analyses_limit
        FROM subscriptions WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'plan': result[0],
                'status': result[1],
                'start_date': result[2],
                'end_date': result[3],
                'analyses_used': result[4] or 0,
                'analyses_limit': result[5] or 5
            }
        return {'plan': 'free', 'status': 'active', 'analyses_used': 0, 'analyses_limit': 5}
    
    def get_effective_subscription(self, user_id: int, company_id: Optional[int] = None) -> Dict[str, Any]:
        """Resolve subscription with NULL-safe queries"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Priority 1: Company subscription (only if company_id provided)
            if company_id:
                cursor.execute('''
                SELECT plan, status, analyses_used, analyses_limit 
                FROM subscriptions 
                WHERE company_id = ? AND status = 'active' AND company_id IS NOT NULL
                LIMIT 1
                ''', (company_id,))
                row = cursor.fetchone()
                if row and row[1] == 'active':
                    conn.close()
                    return {
                        'owner_type': 'company', 'owner_id': company_id,
                        'plan': row[0] or 'free', 'status': 'active',
                        'analyses_used': row[2] or 0, 'analyses_limit': row[3] or 5
                    }
            
            # Priority 2: Personal/consultant subscription
            cursor.execute('''
            SELECT plan, status, analyses_used, analyses_limit 
            FROM subscriptions 
            WHERE user_id = ? AND status = 'active' AND user_id IS NOT NULL
            LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            if row and row[1] == 'active':
                conn.close()
                return {
                    'owner_type': 'user', 'owner_id': user_id,
                    'plan': row[0] or 'free', 'status': 'active',
                    'analyses_used': row[2] or 0, 'analyses_limit': row[3] or 5
                }
                
            conn.close()
            return {'owner_type': 'free', 'plan': 'free', 'status': 'active', 
                    'analyses_used': 0, 'analyses_limit': 5}
                    
        except Exception as e:
            logger.error(f"Subscription lookup error: {e}")
            return {'owner_type': 'free', 'plan': 'free', 'analyses_used': 0, 'analyses_limit': 5}
    
    def update_subscription(self, user_id, plan, duration='monthly', payment_method=None, transaction_id=None):
        """Update user's subscription"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        start_date = datetime.now().date()
        
        plan_limits = {
            'free': {'limit': 5},
            'basic': {'limit': 30},
            'professional': {'limit': -1},
            'enterprise': {'limit': -1}
        }
        
        if duration == 'monthly':
            end_date = start_date + timedelta(days=30)
        else:
            end_date = start_date + timedelta(days=365)
        
        # Check if subscription exists
        cursor.execute('SELECT id FROM subscriptions WHERE user_id = ?', (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute('''
            UPDATE subscriptions 
            SET plan = ?, status = 'active', start_date = ?, end_date = ?, 
                analyses_limit = ?, payment_method = ?, transaction_id = ?, updated_at = ?
            WHERE user_id = ?
            ''', (plan, start_date, end_date, plan_limits[plan]['limit'], 
                  payment_method, transaction_id, datetime.now(), user_id))
        else:
            cursor.execute('''
            INSERT INTO subscriptions (user_id, plan, status, start_date, end_date, 
                                       analyses_limit, payment_method, transaction_id)
            VALUES (?, ?, 'active', ?, ?, ?, ?, ?)
            ''', (user_id, plan, start_date, end_date, plan_limits[plan]['limit'], 
                  payment_method, transaction_id))
        
        conn.commit()
        conn.close()
        return True
    
    def increment_analysis_usage(self, user_id):
        """Increment analysis counter"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE subscriptions SET analyses_used = analyses_used + 1 
        WHERE user_id = ? AND analyses_limit != -1
        ''', (user_id,))
        conn.commit()
        conn.close()
    
    def can_perform_analysis(self, user_id):
        """Check if user can perform an analysis"""
        sub = self.get_user_subscription(user_id)
        if sub['analyses_limit'] == -1:
            return True, "Unlimited"
        remaining = sub['analyses_limit'] - sub['analyses_used']
        return remaining > 0, remaining
    
    def get_all_subscriptions(self):
        """Get all subscriptions for admin"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT s.*, u.username, u.email, u.full_name, c.company_name
        FROM subscriptions s
        JOIN users u ON s.user_id = u.id
        JOIN companies c ON u.company_id = c.id
        ORDER BY s.updated_at DESC
        ''')
        subs = cursor.fetchall()
        conn.close()
        return subs
    
    def log_team_activity(self, company_id: int, actor_user_id: int, 
                     action_type: str, target_type: str, target_id: str,
                     details: str = None) -> bool:
        """
        Log team management activity for audit trail.
        
        Args:
            company_id: Company where action occurred
            actor_user_id: User who performed the action
            action_type: e.g., 'registration', 'update', 'delete', 'login'
            target_type: e.g., 'user', 'tender', 'analysis'
            target_id: ID of the affected resource
            details: Optional JSON string with additional context
        
        Returns:
            bool: True if logged successfully
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO activity_logs (
                company_id, actor_user_id, action_type, target_type, 
                target_id, details, ip_address, user_agent, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id,
                actor_user_id,
                action_type,
                target_type,
                target_id,
                details,
                st.context.headers.get("X-Forwarded-For", "unknown") if 'st' in globals() else None,
                st.context.headers.get("User-Agent", "unknown") if 'st' in globals() else None,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            # Don't crash the app if logging fails
            return False
    # ==================== TENDER ANALYSIS METHODS ====================
    
    def save_analysis(self, user_id, company_id, analysis_data):
        """Save tender analysis to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get existing columns in the table
            cursor.execute("PRAGMA table_info(tender_analyses)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            # Prepare competitor bids as JSON if present
            competitor_bids_json = None
            if 'competitor_bids' in analysis_data and analysis_data['competitor_bids']:
                import json
                competitor_bids_json = json.dumps(analysis_data['competitor_bids'])
            
            # Base fields that should always exist
            base_fields = [
                'user_id', 'company_id', 'tender_id', 'tender_title', 'procuring_entity',
                'division', 'district', 'thana', 'construction_type', 'official_estimate',
                'recommended_bid', 'success_probability', 'risk_level', 'competitor_count',
                'bid_status', 'analysis_date'
            ]
            
            base_values = [
                user_id, company_id,
                analysis_data.get('tender_id', ''),
                analysis_data.get('tender_title', ''),
                analysis_data.get('procuring_entity', ''),
                analysis_data.get('division', ''),
                analysis_data.get('district', ''),
                analysis_data.get('thana', ''),
                analysis_data.get('construction_type', ''),
                analysis_data.get('official_estimate', 0),
                analysis_data.get('recommended_bid', 0),
                analysis_data.get('success_probability', 0),
                analysis_data.get('risk_level', 'MEDIUM'),
                analysis_data.get('competitor_count', 0),
                analysis_data.get('bid_status', 'Pending'),
                datetime.now()
            ]
            
            # Optional fields (only include if they exist in table and data)
            optional_fields = []
            optional_values = []
            
            # Check and add analysis_type
            if 'analysis_type' in existing_columns and 'analysis_type' in analysis_data:
                optional_fields.append('analysis_type')
                optional_values.append(analysis_data.get('analysis_type', 'Basic'))
            
            # Check and add competitor_bids
            if 'competitor_bids' in existing_columns:
                optional_fields.append('competitor_bids')
                optional_values.append(competitor_bids_json)
            
            # Check and add risk_strategy
            if 'risk_strategy' in existing_columns and 'risk_strategy' in analysis_data:
                optional_fields.append('risk_strategy')
                optional_values.append(analysis_data.get('risk_strategy', 'moderate'))
            
            # Check and add confidence_score
            if 'confidence_score' in existing_columns and 'confidence_score' in analysis_data:
                optional_fields.append('confidence_score')
                optional_values.append(analysis_data.get('confidence_score', 0.70))
            
            # Check and add expected_profit
            if 'expected_profit' in existing_columns and 'expected_profit' in analysis_data:
                optional_fields.append('expected_profit')
                optional_values.append(analysis_data.get('expected_profit', 0))
            
            # Check and add expected_value
            if 'expected_value' in existing_columns and 'expected_value' in analysis_data:
                optional_fields.append('expected_value')
                optional_values.append(analysis_data.get('expected_value', 0))
            
            # Check and add slt_threshold
            if 'slt_threshold' in existing_columns and 'slt_threshold' in analysis_data:
                optional_fields.append('slt_threshold')
                optional_values.append(analysis_data.get('slt_threshold', 0))
            
            # Check and add nppi_factor
            if 'nppi_factor' in existing_columns and 'nppi_factor' in analysis_data:
                optional_fields.append('nppi_factor')
                optional_values.append(analysis_data.get('nppi_factor', 0.92))
            
            # Check and add weighted_average
            if 'weighted_average' in existing_columns and 'weighted_average' in analysis_data:
                optional_fields.append('weighted_average')
                optional_values.append(analysis_data.get('weighted_average', 0))
            
            # Build the final query
            all_fields = base_fields + optional_fields
            all_values = base_values + optional_values
            placeholders = ','.join(['?' for _ in range(len(all_fields))])
            
            query = f"INSERT INTO tender_analyses ({','.join(all_fields)}) VALUES ({placeholders})"
            
            cursor.execute(query, all_values)
            
            analysis_id = cursor.lastrowid
            conn.commit()
            
            print(f"[DEBUG] Analysis saved successfully with ID: {analysis_id}")
            
            conn.close()
            return analysis_id
            
        except Exception as e:
            print(f"[DEBUG ERROR] save_analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            conn.close()
            return None


    def get_pending_users(self, company_id):
        """Get all pending approval users for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT id, username, email, full_name, phone, role, created_at, created_by
        FROM users 
        WHERE company_id = ? AND is_approved = 0 AND registration_complete = 0 AND is_active = 1
        ORDER BY created_at ASC
        ''', (company_id,))
        users = cursor.fetchall()
        conn.close()
        return users


    def approve_user(self, user_id, approved_by):
        """Approve a pending user registration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE users 
            SET is_approved = 1, approved_by = ?, approved_at = ?
            WHERE id = ?
            ''', (approved_by, datetime.now(), user_id))
            
            # Update subscription to active
            cursor.execute('''
            UPDATE subscriptions 
            SET status = 'active', analyses_limit = 5
            WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error approving user: {e}")
            return False
        finally:
            conn.close()



    def reject_user(self, user_id, rejected_by):
        """Reject a pending user registration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users 
        SET is_active = 0, registration_complete = 0
        WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        return True


    def is_user_approved(self, user_id):
        """Check if user is approved"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_approved, is_active FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0] == 1 and result[1] == 1
        return False
    def get_user_analyses(self, user_id, company_id, role, limit=50):
        """Get user's tender analyses with role-based filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Debug print
        print(f"🔍 get_user_analyses called with: user_id={user_id}, company_id={company_id}, role={role}")
        
        # System admin can see all analyses across all companies
        if role in ['admin', 'system_admin']:
            cursor.execute('''
                SELECT * FROM tender_analyses 
                ORDER BY analysis_date DESC LIMIT ?
            ''', (limit,))
        # Company admin and manager can see all analyses for their company
        elif role in ['company_admin', 'manager']:
            cursor.execute('''
                SELECT * FROM tender_analyses 
                WHERE company_id = ? 
                ORDER BY analysis_date DESC LIMIT ?
            ''', (company_id, limit))
        # Regular users can only see their own analyses
        else:
            cursor.execute('''
                SELECT * FROM tender_analyses 
                WHERE user_id = ? AND company_id = ?
                ORDER BY analysis_date DESC LIMIT ?
            ''', (user_id, company_id, limit))
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        print(f"🔍 Found {len(data)} analyses for role={role}, company_id={company_id}")
        
        if data:
            df = pd.DataFrame(data, columns=columns)
            
            # Parse competitor_bids JSON if present
            if 'competitor_bids' in df.columns:
                import json
                def parse_competitor_bids(value):
                    if value is None:
                        return []
                    if isinstance(value, str):
                        try:
                            if value and value != 'null':
                                return json.loads(value)
                        except:
                            pass
                    return []
                df['competitor_bids'] = df['competitor_bids'].apply(parse_competitor_bids)
            
            return df
        return pd.DataFrame()


    def get_user_analyses_bak(self, user_id, company_id, role, limit=50):
        """Get user's tender analyses with role-based filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Admin can see all analyses across the company
        if role in ['admin']:
            cursor.execute('''
            SELECT * FROM tender_analyses 
            WHERE company_id = ? 
            ORDER BY analysis_date DESC LIMIT ?
            ''', (company_id, limit))
        # Company admin and manager can see all company analyses
        elif role in ['company_admin', 'manager']:
            cursor.execute('''
            SELECT * FROM tender_analyses 
            WHERE company_id = ? 
            ORDER BY analysis_date DESC LIMIT ?
            ''', (company_id, limit))
        # Regular users can only see their own analyses
        else:
            cursor.execute('''
            SELECT * FROM tender_analyses 
            WHERE user_id = ? AND company_id = ?
            ORDER BY analysis_date DESC LIMIT ?
            ''', (user_id, company_id, limit))
        
        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        if data:
            df = pd.DataFrame(data, columns=columns)
            
            # Parse competitor_bids JSON if present - with proper error handling
            if 'competitor_bids' in df.columns:
                import json
                def parse_competitor_bids(value):
                    if value is None:
                        return []
                    if isinstance(value, (int, float)):
                        return []
                    if isinstance(value, str):
                        try:
                            if value and value != 'null':
                                parsed = json.loads(value)
                                return parsed if isinstance(parsed, list) else []
                        except:
                            pass
                    return []
                
                df['competitor_bids'] = df['competitor_bids'].apply(parse_competitor_bids)
            
            # Convert date column to datetime with error handling
            if 'analysis_date' in df.columns:
                try:
                    # Try to parse with different formats
                    df['analysis_date'] = pd.to_datetime(df['analysis_date'], errors='coerce')
                except Exception as e:
                    print(f"Date conversion error: {e}")
                    # If conversion fails, keep as is
                    pass
            
            return df
        return pd.DataFrame()

    def get_all_companies(self) -> List[tuple]:
        """Fetch all companies from database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id, company_name, email, phone, division, district, 
                created_at, status 
            FROM companies 
            ORDER BY company_name ASC
            ''')
            companies = cursor.fetchall()
            conn.close()
            return companies
        except Exception as e:
            logger.error(f"Failed to fetch companies: {e}")
            return []
    def get_company_stats(self, company_id):
        """Get company statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE company_id = ?', (company_id,))
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tender_analyses WHERE company_id = ?', (company_id,))
        total_analyses = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM tender_analyses 
            WHERE company_id = ? AND bid_status = 'Won'
        ''', (company_id,))
        won_tenders = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"📊 Company {company_id} Stats: Users={total_users}, Analyses={total_analyses}, Wins={won_tenders}")
        
        return {
            'total_users': total_users,
            'total_analyses': total_analyses,
            'won_tenders': won_tenders,
            'win_rate': (won_tenders / total_analyses * 100) if total_analyses > 0 else 0
        }


    
    # ==================== CONTACT METHODS ====================
    
    def save_contact_message(self, name, email, subject, message):
        """Save contact message"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO contact_messages (name, email, subject, message)
        VALUES (?, ?, ?, ?)
        ''', (name, email, subject, message))
        conn.commit()
        conn.close()
        return True
    
    # ==================== HISTORICAL DATA METHODS ====================
    
    def save_historical_tender(self, user_id, company_id, data):
        """Save historical tender data with competitor details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO historical_tenders (
            user_id, company_id, tender_id, tender_title, procuring_entity,
            procurement_type, official_estimate, awarded_price, num_competitors,
            total_bidders, our_rank, award_date, competitors_data, 
            winning_competitor, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, company_id, data['tender_id'], data['tender_title'],
            data['procuring_entity'], data['procurement_type'], data['official_estimate'],
            data['awarded_price'], data.get('num_competitors', 0),
            data.get('total_bidders', 0), data.get('our_rank', 0),
            data['award_date'], data.get('competitors_data'), 
            data.get('winning_competitor'), data.get('notes', '')
        ))
        
        tender_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tender_id
    
    def get_historical_tenders_old(self, company_id, procurement_type=None, winner_type=None, limit=100):
        """Get historical tenders with winner filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT id, tender_id, tender_title, procuring_entity, procurement_type,
            official_estimate, awarded_price, our_awarded_price, num_competitors,
            total_bidders, our_rank, award_date, competitors_data, winning_competitor,
            winning_company_type, notes, created_at
        FROM historical_tenders 
        WHERE company_id = ?
        '''
        params = [company_id]
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        if winner_type and winner_type != "All":
            query += " AND winning_company_type = ?"
            params.append(winner_type)
        
        query += " ORDER BY award_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        if data:
            return pd.DataFrame(data, columns=columns)
        return pd.DataFrame()
    
    def update_historical_tender_winner(self, tender_id, winner_name, winner_type, winning_price):
        """Update winner information for an existing historical tender"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE historical_tenders 
        SET winning_competitor = ?, winning_company_type = ?, awarded_price = ?
        WHERE id = ?
        ''', (winner_name, winner_type, winning_price, tender_id))
        
        conn.commit()
        conn.close()
        return True

    def get_competitor_performance_against_us(self, company_id, competitor_name=None):
        """Get competitor performance statistics against our company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            winning_competitor,
            COUNT(*) as times_won,
            AVG(awarded_price / official_estimate) as avg_winning_ratio
        FROM historical_tenders 
        WHERE company_id = ? 
        AND winning_company_type = 'Competitor'
        '''
        params = [company_id]
        
        if competitor_name:
            query += " AND winning_competitor = ?"
            params.append(competitor_name)
        
        query += " GROUP BY winning_competitor ORDER BY times_won DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        if results:
            return [{'competitor': r[0], 'wins': r[1], 'avg_ratio': r[2]} for r in results]
        return []

    def get_historical_tenders(self, company_id, procurement_type=None, winner_type=None, limit=100):
        """Get historical tenders with winner information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            h.id, h.tender_id, h.tender_title, h.procuring_entity, h.procurement_type,
            h.official_estimate, h.awarded_price, h.our_awarded_price, h.num_competitors,
            h.total_bidders, h.our_rank, h.award_date, h.competitors_data, 
            h.winning_competitor, h.winning_company_type, h.notes, h.created_at,
            c.company_name
        FROM historical_tenders h
        JOIN companies c ON h.company_id = c.id
        WHERE h.company_id = ?
        '''
        params = [company_id]
        
        if procurement_type:
            query += " AND h.procurement_type = ?"
            params.append(procurement_type)
        
        if winner_type and winner_type != "All":
            query += " AND h.winning_company_type = ?"
            params.append(winner_type)
        
        query += " ORDER BY h.award_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        if data:
            return pd.DataFrame(data, columns=columns)
        return pd.DataFrame()

    def get_winning_statistics(self, company_id, procurement_type=None):
        """Get winning statistics for analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            COUNT(*) as total_tenders,
            SUM(CASE WHEN winning_company_type = 'Our Company' THEN 1 ELSE 0 END) as our_wins,
            SUM(CASE WHEN winning_company_type = 'Competitor' THEN 1 ELSE 0 END) as competitor_wins,
            SUM(CASE WHEN winning_company_type = 'Unknown' THEN 1 ELSE 0 END) as unknown_wins,
            AVG(CASE WHEN winning_company_type = 'Our Company' THEN awarded_price ELSE NULL END) as avg_our_winning_price,
            AVG(CASE WHEN winning_company_type = 'Competitor' THEN awarded_price ELSE NULL END) as avg_competitor_winning_price,
            AVG(official_estimate) as avg_estimate,
            MIN(CASE WHEN winning_company_type = 'Our Company' THEN awarded_price ELSE NULL END) as min_our_winning_price,
            MAX(CASE WHEN winning_company_type = 'Our Company' THEN awarded_price ELSE NULL END) as max_our_winning_price,
            MIN(CASE WHEN winning_company_type = 'Competitor' THEN awarded_price ELSE NULL END) as min_competitor_winning_price,
            MAX(CASE WHEN winning_company_type = 'Competitor' THEN awarded_price ELSE NULL END) as max_competitor_winning_price
        FROM historical_tenders 
        WHERE company_id = ?
        '''
        params = [company_id]
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_tenders': result[0] or 0,
                'our_wins': result[1] or 0,
                'competitor_wins': result[2] or 0,
                'unknown_wins': result[3] or 0,
                'our_win_rate': (result[1] / result[0] * 100) if result[0] > 0 else 0,
                'avg_our_winning_price': result[4] or 0,
                'avg_competitor_winning_price': result[5] or 0,
                'avg_estimate': result[6] or 0,
                'min_our_winning_price': result[7] or 0,
                'max_our_winning_price': result[8] or 0,
                'min_competitor_winning_price': result[9] or 0,
                'max_competitor_winning_price': result[10] or 0
            }
        return None


    def get_winner_trends(self, company_id, procurement_type=None, months=12):
        """Get winner trends over time"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            strftime('%Y-%m', award_date) as month,
            COUNT(*) as total,
            SUM(CASE WHEN winning_company_type = 'Our Company' THEN 1 ELSE 0 END) as our_wins,
            SUM(CASE WHEN winning_company_type = 'Competitor' THEN 1 ELSE 0 END) as competitor_wins
        FROM historical_tenders 
        WHERE company_id = ?
        AND award_date >= date('now', ?)
        '''
        params = [company_id, f'-{months} months']
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        query += " GROUP BY strftime('%Y-%m', award_date) ORDER BY month DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        if results:
            return pd.DataFrame(results, columns=['month', 'total', 'our_wins', 'competitor_wins'])
        return pd.DataFrame()

    def get_nppi_for_company(self, company_id, procurement_type='goods'):
        """Get the latest NPPI for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT nppi_factor, calculation_date, data_points
        FROM company_nppi
        WHERE company_id = ? AND procurement_type = ?
        ORDER BY calculation_date DESC LIMIT 1
        ''', (company_id, procurement_type))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'nppi_factor': result[0],
                'calculation_date': result[1],
                'data_points': result[2]
            }
        return None
    
    def save_company_nppi(self, company_id, procurement_type, nppi_factor, data_points):
        """Save calculated NPPI for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO company_nppi (company_id, procurement_type, nppi_factor, data_points)
        VALUES (?, ?, ?, ?)
        ''', (company_id, procurement_type, nppi_factor, data_points))
        
        conn.commit()
        conn.close()
    
    # ==================== COMPETITOR MASTER METHODS ====================
    
    def get_competitor_master_list(self, company_id, active_only=True):
        """Get all competitors for a company from master list"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT id, competitor_name, business_type, total_bids, total_wins,
               avg_bid_ratio, preferred_strategy, last_seen, is_active
        FROM competitor_master 
        WHERE company_id = ?
        '''
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY total_bids DESC"
        
        cursor.execute(query, (company_id,))
        competitors = cursor.fetchall()
        conn.close()
        
        return competitors
    
    def add_competitor_to_master(self, company_id, competitor_data):
        """Add or update competitor in master list"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if competitor exists
        cursor.execute('''
        SELECT id, total_bids, total_wins, avg_bid_ratio 
        FROM competitor_master 
        WHERE company_id = ? AND competitor_name = ?
        ''', (company_id, competitor_data['competitor_name']))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing competitor
            comp_id, total_bids, total_wins, avg_ratio = existing
            new_total_bids = total_bids + 1
            new_total_wins = total_wins + (1 if competitor_data.get('was_winner', False) else 0)
            
            # Update rolling average
            new_avg_ratio = (avg_ratio * total_bids + competitor_data['bid_ratio']) / new_total_bids if new_total_bids > 0 else competitor_data['bid_ratio']
            
            cursor.execute('''
            UPDATE competitor_master 
            SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                last_seen = ?, updated_at = ?
            WHERE id = ?
            ''', (new_total_bids, new_total_wins, new_avg_ratio, 
                  datetime.now().date(), datetime.now(), comp_id))
        else:
            # Add new competitor
            cursor.execute('''
            INSERT INTO competitor_master (
                company_id, competitor_name, business_type, contact_person,
                phone, email, address, notes, first_seen, last_seen,
                total_bids, total_wins, avg_bid_ratio, preferred_strategy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id, competitor_data['competitor_name'],
                competitor_data.get('business_type', ''),
                competitor_data.get('contact_person', ''),
                competitor_data.get('phone', ''),
                competitor_data.get('email', ''),
                competitor_data.get('address', ''),
                competitor_data.get('notes', ''),
                datetime.now().date(), datetime.now().date(),
                1, 1 if competitor_data.get('was_winner', False) else 0,
                competitor_data['bid_ratio'],
                competitor_data.get('preferred_strategy', 'Unknown')
            ))
            comp_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return comp_id
    
    def get_competitor_by_id(self, competitor_id):
        """Get competitor details by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM competitor_master WHERE id = ?', (competitor_id,))
        competitor = cursor.fetchone()
        conn.close()
        return competitor
    
    def update_competitor_master(self, competitor_id, update_data):
        """Update competitor information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        fields = []
        values = []
        for key, value in update_data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        values.append(competitor_id)
        query = f"UPDATE competitor_master SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
        values.insert(0, datetime.now())
        
        cursor.execute(query, values)
        conn.commit()
        conn.close()
    
    def delete_competitor(self, competitor_id):
        """Soft delete competitor (mark inactive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE competitor_master SET is_active = 0 WHERE id = ?', (competitor_id,))
        conn.commit()
        conn.close()
    
    def update_competitor_stats_from_bid(self, company_id, competitor_name, bid_ratio, was_winner):
        """Update competitor statistics from a bid"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if competitor exists
        cursor.execute('''
        SELECT id, total_bids, total_wins, avg_bid_ratio 
        FROM competitor_master 
        WHERE company_id = ? AND competitor_name = ?
        ''', (company_id, competitor_name))
        
        existing = cursor.fetchone()
        
        if existing:
            comp_id, total_bids, total_wins, avg_ratio = existing
            new_total_bids = total_bids + 1
            new_total_wins = total_wins + (1 if was_winner else 0)
            new_avg_ratio = (avg_ratio * total_bids + bid_ratio) / new_total_bids
            
            cursor.execute('''
            UPDATE competitor_master 
            SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                last_seen = ?, updated_at = ?
            WHERE id = ?
            ''', (new_total_bids, new_total_wins, new_avg_ratio, 
                  datetime.now().date(), datetime.now(), comp_id))
        else:
            # Add new competitor
            cursor.execute('''
            INSERT INTO competitor_master (
                company_id, competitor_name, first_seen, last_seen,
                total_bids, total_wins, avg_bid_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (company_id, competitor_name, datetime.now().date(), datetime.now().date(),
                  1, 1 if was_winner else 0, bid_ratio))
        
        conn.commit()
        conn.close()
    def update_historical_tender_schema(self):
        """Add new columns for winner tracking if not exists"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Add winning_company_type column
        try:
            cursor.execute("ALTER TABLE historical_tenders ADD COLUMN winning_company_type TEXT")
            print("✓ Added winning_company_type column")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Add our_awarded_price column
        try:
            cursor.execute("ALTER TABLE historical_tenders ADD COLUMN our_awarded_price REAL")
            print("✓ Added our_awarded_price column")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()

    def get_historical_tenders_with_winner(self, company_id, procurement_type=None, winner_type=None, limit=100):
        """Get historical tenders with winner filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT * FROM historical_tenders 
        WHERE company_id = ?
        '''
        params = [company_id]
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        if winner_type and winner_type != "All":
            query += " AND winning_company_type = ?"
            params.append(winner_type)
        
        query += " ORDER BY award_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        if data:
            return pd.DataFrame(data, columns=columns)
        return pd.DataFrame()

    def get_winning_statistics(self, company_id, procurement_type=None):
        """Get winning statistics for analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            COUNT(*) as total_tenders,
            SUM(CASE WHEN winning_company_type = 'Our Company' THEN 1 ELSE 0 END) as our_wins,
            SUM(CASE WHEN winning_company_type = 'Competitor' THEN 1 ELSE 0 END) as competitor_wins,
            AVG(CASE WHEN winning_company_type = 'Our Company' THEN awarded_price ELSE NULL END) as avg_our_winning_price,
            AVG(CASE WHEN winning_company_type = 'Competitor' THEN awarded_price ELSE NULL END) as avg_competitor_winning_price,
            AVG(official_estimate) as avg_estimate
        FROM historical_tenders 
        WHERE company_id = ?
        '''
        params = [company_id]
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_tenders': result[0] or 0,
                'our_wins': result[1] or 0,
                'competitor_wins': result[2] or 0,
                'our_win_rate': (result[1] / result[0] * 100) if result[0] > 0 else 0,
                'avg_our_winning_price': result[3] or 0,
                'avg_competitor_winning_price': result[4] or 0,
                'avg_estimate': result[5] or 0
            }
        return None
    def save_historical_tender(self, user_id, company_id, data):
        """Save historical tender data with competitor details and winner info"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO historical_tenders (
            user_id, company_id, tender_id, tender_title, procuring_entity,
            procurement_type, official_estimate, awarded_price, our_awarded_price,
            num_competitors, total_bidders, our_rank, award_date, competitors_data,
            winning_competitor, winning_company_type, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, company_id, data['tender_id'], data['tender_title'],
            data['procuring_entity'], data['procurement_type'], data['official_estimate'],
            data['awarded_price'], data.get('our_awarded_price'),
            data.get('num_competitors', 0), data.get('total_bidders', 0),
            data.get('our_rank'), data['award_date'], data.get('competitors_data'),
            data.get('winning_competitor'), data.get('winning_company_type'),
            data.get('notes', '')
        ))
        
        tender_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tender_id

    def add_tender_lot(self, tender_id, lot_data):
        """Add lot information for a tender"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO tender_lots (tender_id, lot_no, lot_description, location, 
                                security_amount, estimated_value, start_date, completion_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tender_id, lot_data.get('lot_no'), lot_data.get('description'),
            lot_data.get('location'), lot_data.get('security_amount', 0),
            lot_data.get('estimated_value', 0), lot_data.get('start_date'),
            lot_data.get('completion_date')))
        
        conn.commit()
        conn.close()
    def update_tender_lock_status(self, tender_id: int, locked: bool) -> bool:
        """Update the lock status of a tender"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE company_tenders 
            SET is_locked = ?, locked_at = ?, locked_by = ?
            WHERE id = ?
            ''', (
                1 if locked else 0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') if locked else None,
                st.session_state.user_id if locked else None,
                tender_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to update tender lock status: {e}")
            return False


    def create_tender_copy(self, original_tender_id: int, created_by: int) -> Optional[int]:
        """Create a backup copy of a locked tender"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Fetch original tender
            cursor.execute('SELECT * FROM company_tenders WHERE id = ?', (original_tender_id,))
            original = cursor.fetchone()
            if not original:
                return None
            
            # Create copy with new ID and copy flags
            cursor.execute('''
            INSERT INTO company_tenders (
                company_id, tender_id, tender_title, procuring_entity, official_estimate,
                submission_deadline, procurement_type, division, district, thana,
                tender_security, document_fee, evaluation_type, created_at,
                is_locked, is_copy, original_tender_id, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                original[1],  # company_id
                f"{original[2]}_COPY",  # tender_id with COPY suffix
                f"{original[3]} (Backup Copy)",  # title with indicator
                original[4], original[5], original[6], original[7],
                original[8], original[9], original[10], original[11],
                original[12], original[13], datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                0,  # is_locked = False for copy
                1,  # is_copy = True
                original_tender_id,  # reference to original
                created_by
            ))
            
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
            
        except Exception as e:
            logger.error(f"Failed to create tender copy: {e}")
            return None


    def delete_tender(self, tender_id: int) -> bool:
        """Soft delete a tender (mark as inactive)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE company_tenders 
            SET is_active = 0, deleted_at = ?, deleted_by = ?
            WHERE id = ?
            ''', (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                st.session_state.user_id,
                tender_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to delete tender: {e}")
            return False
        


    def increment_analysis_usage(self, user_id: int, company_id: Optional[int] = None) -> bool:
        """Increment usage on the active subscription (company first, then personal)"""
        try:
            sub = self.get_effective_subscription(user_id, company_id)
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if sub['owner_type'] == 'company':
                cursor.execute('''
                UPDATE subscriptions SET analyses_used = analyses_used + 1, updated_at = CURRENT_TIMESTAMP
                WHERE company_id = ?
                ''', (company_id,))
            elif sub['owner_type'] == 'user':
                cursor.execute('''
                UPDATE subscriptions SET analyses_used = analyses_used + 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                ''', (user_id,))
                
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Usage increment error: {e}")
            return False


    def add_consultant_client(self, consultant_id: int, client_company_id: int, role: str = 'manager') -> bool:
        """Link a consultant to a client company"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            INSERT OR IGNORE INTO consultant_clients (consultant_user_id, client_company_id, role)
            VALUES (?, ?, ?)
            ''', (consultant_id, client_company_id, role))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Client relationship error: {e}")
            return False

    def create_individual_user(self, user_data: Dict) -> tuple:
        """Create an individual user (no company)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create a personal company for the individual
            personal_company_name = f"{user_data['full_name']} (Individual)"
            
            cursor.execute('''
                INSERT INTO companies (company_name, email, phone, division, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (personal_company_name, user_data['email'], user_data.get('phone', ''), 'Dhaka', 1))
            
            company_id = cursor.lastrowid
            
            # Hash password
            import bcrypt
            hashed = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute('''
                INSERT INTO users (company_id, username, password, email, full_name, phone, 
                                role, account_type, status, is_approved, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id,
                user_data['username'],
                hashed,
                user_data['email'],
                user_data['full_name'],
                user_data.get('phone', ''),
                user_data['role'],
                'individual',
                'active',
                1,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return True, user_id
        except Exception as e:
            logger.error(f"Individual user creation failed: {e}")
            return False, str(e)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, password, email, full_name, role, company_id, 
                    is_approved, account_type, auth_provider, created_at
                FROM users 
                WHERE email = ?
            """, (email,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'password': row[2],
                    'email': row[3],
                    'full_name': row[4],
                    'role': row[5],
                    'company_id': row[6],
                    'is_approved': row[7],
                    'account_type': row[8],
                    'auth_provider': row[9],
                    'created_at': row[10]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def get_company_by_id(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, company_name, email, phone, division, district, is_individual, created_at
                FROM companies 
                WHERE id = ?
            """, (company_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'company_name': row[1],
                    'email': row[2],
                    'phone': row[3],
                    'division': row[4],
                    'district': row[5],
                    'is_individual': row[6],
                    'created_at': row[7]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting company by ID: {e}")
            return None

    def migrate_schema(self):
        """Auto-migrate database schema for new features"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Define new columns to add
        new_columns = {
            'users': [
                ("auth_provider", "TEXT DEFAULT 'email'"),
                ("email_verified", "BOOLEAN DEFAULT 0"),
                ("email_verified_at", "TIMESTAMP"),
                ("verification_token", "TEXT"),
                ("reset_token", "TEXT"),
                ("reset_token_expires", "TIMESTAMP"),
                ("specialization", "TEXT"),
                ("years_experience", "INTEGER")
            ],
            'companies': [
                ("is_individual", "BOOLEAN DEFAULT 0")
            ]
        }
        
        # Add missing columns
        for table, columns in new_columns.items():
            for col_name, col_type in columns:
                if col_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                        print(f"✅ Added column: {table}.{col_name}")
                    except Exception as e:
                        print(f"⚠️ Could not add {table}.{col_name}: {e}")
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)",
            "CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token)"
        ]
        
        for index in indexes:
            try:
                cursor.execute(index)
            except Exception as e:
                print(f"⚠️ Could not create index: {e}")
        
        conn.commit()
        conn.close()


    def get_consultant_clients(self, consultant_id: int) -> List[Dict]:
        """Fetch all client companies linked to a consultant"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT c.id, c.company_name, c.email, cc.role, cc.created_at
            FROM consultant_clients cc
            JOIN companies c ON cc.client_company_id = c.id
            WHERE cc.consultant_user_id = ?
            ''', (consultant_id,))
            clients = [{'id': r[0], 'company_name': r[1], 'email': r[2], 'role': r[3]} for r in cursor.fetchall()]
            conn.close()
            return clients
        except Exception as e:
            logger.error(f"Fetch consultant clients error: {e}")
            return []
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, username, email FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {'id': row[0], 'username': row[1], 'email': row[2]}
            return None
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    def get_all_users_filtered_bak(self, company_id, search="", role="", status=None, limit=20, offset=0):
        """Return filtered users list and total count"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                u.created_at, u.last_login, c.company_name, u.is_approved
            FROM users u
            JOIN companies c ON u.company_id = c.id
            WHERE u.company_id = ?
        """

        params = [company_id]
        
        if search:
            query += " AND (u.username LIKE ? OR u.email LIKE ? OR u.full_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if role:
            query += " AND u.role = ?"
            params.append(role)
        if status is not None:
            query += " AND u.is_active = ?"
            params.append(status)
        
        # Count total
        count_query = query.replace("SELECT u.id, u.username, ...", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Paginated results
        query += " ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        users = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts for easier handling
        result = []
        for row in users:
            result.append({
                'id': row[0], 'username': row[1], 'email': row[2], 'full_name': row[3],
                'phone': row[4], 'role': row[5], 'is_active': row[6],
                'created_at': row[7], 'last_login': row[8], 'company_name': row[9],
                'is_approved': row[10] if len(row) > 10 else 1
            })

        return result, total

    def update_user(self, user_id, updates):
        """Update user fields including company_id"""
        allowed_fields = ['full_name', 'email', 'phone', 'role', 'is_active', 'company_id']
        set_clause = []
        params = []
        for field, value in updates.items():
            if field in allowed_fields:
                set_clause.append(f"{field} = ?")
                params.append(value)
        if not set_clause:
            return False
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(set_clause)} WHERE id = ?"
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update user failed: {e}")
            return False
        finally:
            conn.close()

    def generate_random_password(self, length=12):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def reset_user_password(self, user_id, new_password=None):
        """Reset user password. If new_password not provided, generate random."""
        if not new_password:
            new_password = self.generate_random_password()
        import bcrypt
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
            conn.commit()
            return True, new_password
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            return False, None
        finally:
            conn.close()

    def delete_user(self, user_id):
        """Hard delete user (only allowed for non-admin users)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # First check if user is admin - prevent deletion of admin
            cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
            role = cursor.fetchone()
            if role and role[0] == 'admin':
                conn.close()
                return False
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Delete user failed: {e}")
            return False
        finally:
            conn.close()

    def get_role_permissions(self, role):
        """Get permissions for a given role as dict"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT permissions FROM role_permissions WHERE role = ?", (role,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return {}

    def get_all_roles(self):
        """Get all defined roles with their permissions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Check if table exists first
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='role_permissions'")
            if not cursor.fetchone():
                # Table doesn't exist - create it
                self._create_role_permissions_table()
            
            cursor.execute("SELECT role, permissions FROM role_permissions ORDER BY role")
            rows = cursor.fetchall()
            conn.close()
            roles = []
            for row in rows:
                try:
                    perms = json.loads(row[1]) if row[1] else {}
                except:
                    perms = {}
                roles.append({
                    'role': row[0],
                    'permissions': perms
                })
            return roles
        except Exception as e:
            logger.error(f"Error getting roles: {e}")
            conn.close()
            return []

    def update_role_permissions(self, role, permissions):
        """Update permissions for a role (permissions is dict)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE role_permissions SET permissions = ?, updated_at = ?
                WHERE role = ?
            ''', (json.dumps(permissions), datetime.now(), role))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update role permissions failed: {e}")
            return False
        finally:
            conn.close()
      # ==================== COMPANY CRUD OPERATIONS ====================
    
    def get_all_companies_filtered(self, search="", status=None, limit=20, offset=0):
        """Get all companies with pagination and filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, company_name, email, phone, division, district, 
                   address, registration_number, vat_number, created_at, is_active
            FROM companies
            WHERE 1=1
        """
        params = []
        
        if search:
            query += " AND (company_name LIKE ? OR email LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if status is not None:
            query += " AND is_active = ?"
            params.append(status)
        
        # Count total
        count_query = query.replace("SELECT id, company_name, ...", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Paginated results
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        companies = []
        for row in rows:
            companies.append({
                'id': row[0], 'company_name': row[1], 'email': row[2],
                'phone': row[3], 'division': row[4], 'district': row[5],
                'address': row[6], 'registration_number': row[7],
                'vat_number': row[8], 'created_at': row[9], 'is_active': row[10]
            })
        return companies, total

    def create_company(self, company_data):
        """Create a new company with full details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO companies (
                    company_name, email, phone, division, district, 
                    address, registration_number, vat_number, website, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_data['company_name'],
                company_data.get('email', ''),
                company_data.get('phone', ''),
                company_data.get('division', ''),
                company_data.get('district', ''),
                company_data.get('address', ''),
                company_data.get('registration_number', ''),
                company_data.get('vat_number', ''),
                company_data.get('website', ''),
                1
            ))
            company_id = cursor.lastrowid
            conn.commit()
            return True, company_id
        except sqlite3.IntegrityError as e:
            return False, f"Company name already exists: {e}"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def update_company(self, company_id, updates):
        """Update company information"""
        allowed_fields = ['company_name', 'email', 'phone', 'division', 'district', 
                         'address', 'registration_number', 'vat_number', 'website', 'is_active']
        set_clause = []
        params = []
        for field, value in updates.items():
            if field in allowed_fields:
                set_clause.append(f"{field} = ?")
                params.append(value)
        if not set_clause:
            return False
        params.append(company_id)
        query = f"UPDATE companies SET {', '.join(set_clause)} WHERE id = ?"
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update company failed: {e}")
            return False
        finally:
            conn.close()

    def delete_company(self, company_id):
        """Soft delete a company (mark inactive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # First, deactivate all users in this company
            cursor.execute("UPDATE users SET is_active = 0 WHERE company_id = ?", (company_id,))
            # Then deactivate the company
            cursor.execute("UPDATE companies SET is_active = 0 WHERE id = ?", (company_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Delete company failed: {e}")
            return False
        finally:
            conn.close()

    def get_company_by_id(self, company_id):
        """Get company by ID as dictionary"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    # ==================== SYSTEM USER MANAGEMENT ====================
    
    def get_system_users(self):
        """Get all system-level users (company_id IS NULL)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, full_name, phone, role, is_active, 
                   created_at, last_login
            FROM users
            WHERE company_id IS NULL
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0], 'username': row[1], 'email': row[2], 'full_name': row[3],
                'phone': row[4], 'role': row[5], 'is_active': row[6],
                'created_at': row[7], 'last_login': row[8]
            })
        return users

    def create_system_user(self, user_data, created_by):
        """Create a system-level user (no company)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        hashed_pass = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute('''
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, role,
                    is_active, created_by, is_approved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                None, user_data['username'], hashed_pass, user_data['email'],
                user_data['full_name'], user_data.get('phone', ''), user_data.get('role', 'viewer'),
                1, created_by, 1
            ))
            user_id = cursor.lastrowid
            
            # Create subscription record
            cursor.execute('''
            INSERT INTO subscriptions (user_id, plan, status, analyses_limit)
            VALUES (?, ?, ?, ?)
            ''', (user_id, 'professional', 'active', -1))
            
            conn.commit()
            return True, user_id
        except sqlite3.IntegrityError as e:
            return False, str(e)
        finally:
            conn.close()

    def get_company_users(self, company_id):
        """Get all users belonging to a specific company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, full_name, phone, role, is_active, 
                   created_at, last_login
            FROM users
            WHERE company_id = ?
            ORDER BY created_at DESC
        """, (company_id,))
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0], 'username': row[1], 'email': row[2], 'full_name': row[3],
                'phone': row[4], 'role': row[5], 'is_active': row[6],
                'created_at': row[7], 'last_login': row[8]
            })
        return users

    # ==================== ENHANCED GET_ALL_USERS_FILTERED ====================
    
    def get_all_users_filtered(self, company_id=None, search="", role="", status=None, limit=20, offset=0):
        """Get users filtered by company, search, role, status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build base query
        if company_id == -1:
            # Special case: get system users only (company_id IS NULL)
            query = """
                SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                    u.created_at, u.last_login, NULL as company_name, u.is_approved
                FROM users u
                WHERE u.company_id IS NULL
            """
            params = []
        elif company_id and company_id > 0:
            # Get users for a specific company
            query = """
                SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                    u.created_at, u.last_login, c.company_name, u.is_approved
                FROM users u
                LEFT JOIN companies c ON u.company_id = c.id
                WHERE u.company_id = ?
            """
            params = [company_id]
        else:
            # Get all users (including system users) - for system admin
            query = """
                SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                    u.created_at, u.last_login, c.company_name, u.is_approved
                FROM users u
                LEFT JOIN companies c ON u.company_id = c.id
                WHERE 1=1
            """
            params = []
        
        # Add search filter
        if search:
            query += " AND (u.username LIKE ? OR u.email LIKE ? OR u.full_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
        # Add role filter
        if role:
            query += " AND u.role = ?"
            params.append(role)
        
        # Add status filter
        if status is not None:
            query += " AND u.is_active = ?"
            params.append(status)
        
        # Create count query (remove SELECT part and ORDER BY, LIMIT, OFFSET)
        count_query = query
        # Remove the SELECT part for count
        if "SELECT u.id" in count_query:
            count_query = count_query.replace(
                "SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, u.created_at, u.last_login, c.company_name, u.is_approved",
                "SELECT COUNT(*)"
            )
        
        # Execute count query
        try:
            cursor.execute(count_query, params)
            count_result = cursor.fetchone()
            total = count_result[0] if count_result else 0
        except Exception as e:
            print(f"Count query error: {e}")
            total = 0
        
        # Add pagination
        query += " ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute main query
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        except Exception as e:
            print(f"Main query error: {e}")
            rows = []
        
        conn.close()
        
        # Convert to list of dicts
        users = []
        for row in rows:
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'full_name': row[3],
                'phone': row[4] if len(row) > 4 else '',
                'role': row[5] if len(row) > 5 else 'viewer',
                'is_active': row[6] if len(row) > 6 else 1,
                'created_at': row[7] if len(row) > 7 else None,
                'last_login': row[8] if len(row) > 8 else None,
                'company_name': row[9] if len(row) > 9 else None,
                'is_approved': row[10] if len(row) > 10 else 1
            })
        
        return users, total

    def create_company_user_bak(self, company_id, user_data, created_by):
        """Create a company-level user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        hashed_pass = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute('''
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, role,
                    is_active, created_by, is_approved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id, user_data['username'], hashed_pass, user_data['email'],
                user_data['full_name'], user_data.get('phone', ''), user_data.get('role', 'viewer'),
                1, created_by, 1
            ))
            user_id = cursor.lastrowid
            
            # Create subscription record
            cursor.execute('''
            INSERT INTO subscriptions (user_id, plan, status, analyses_limit)
            VALUES (?, ?, ?, ?)
            ''', (user_id, 'free', 'active', 5))
            
            conn.commit()
            return True, user_id
        except sqlite3.IntegrityError as e:
            return False, str(e)
        finally:
            conn.close()

    def get_company_stats_by_id(self, company_id):
        """Get statistics for a specific company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE company_id = ?', (company_id,))
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tender_analyses WHERE company_id = ?', (company_id,))
        total_analyses = cursor.fetchone()[0]
        
        cursor.execute('''
        SELECT COUNT(*) FROM tender_analyses 
        WHERE company_id = ? AND bid_status = 'Won'
        ''', (company_id,))
        won_tenders = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_analyses': total_analyses,
            'won_tenders': won_tenders,
            'win_rate': (won_tenders / total_analyses * 100) if total_analyses > 0 else 0
        }
    def get_company_stats(self, company_id):
        """Get company statistics including users and analyses"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE company_id = ?', (company_id,))
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tender_analyses WHERE company_id = ?', (company_id,))
        total_analyses = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM tender_analyses 
            WHERE company_id = ? AND bid_status = 'Won'
        ''', (company_id,))
        won_tenders = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_analyses': total_analyses,
            'won_tenders': won_tenders,
            'win_rate': (won_tenders / total_analyses * 100) if total_analyses > 0 else 0
        }

    def get_tender_analyses_by_company(self, company_id, tender_id=None):
        """Get all analyses for a company, optionally for a specific tender"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if tender_id:
            cursor.execute('''
                SELECT id, tender_title, recommended_bid, success_probability, 
                    risk_level, analysis_date, user_id
                FROM tender_analyses
                WHERE company_id = ? AND tender_id = ?
                ORDER BY analysis_date DESC
            ''', (company_id, tender_id))
        else:
            cursor.execute('''
                SELECT id, tender_id, tender_title, recommended_bid, success_probability,
                    risk_level, analysis_date
                FROM tender_analyses
                WHERE company_id = ?
                ORDER BY analysis_date DESC
                LIMIT 20
            ''', (company_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        analyses = []
        for row in rows:
            analyses.append({
                'id': row[0],
                'tender_title': row[1],
                'recommended_bid': row[2],
                'win_probability': f"{row[3]*100:.0f}%" if row[3] else 'N/A',
                'risk_level': row[4],
                'date': row[5][:16] if row[5] else 'N/A'
            })
        return analyses

    def create_company_user(self, company_id, user_data, created_by):
        """Create a user under a specific company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        hashed_pass = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute('''
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, role,
                    is_active, created_by, is_approved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id, user_data['username'], hashed_pass, user_data['email'],
                user_data['full_name'], user_data.get('phone', ''), user_data.get('role', 'viewer'),
                1, created_by, 1
            ))
            user_id = cursor.lastrowid
            
            # Create subscription record
            cursor.execute('''
                INSERT INTO subscriptions (user_id, plan, status, analyses_limit)
                VALUES (?, ?, ?, ?)
            ''', (user_id, 'free', 'active', 5))
            
            conn.commit()
            return True, user_id
        except sqlite3.IntegrityError as e:
            return False, str(e)
        finally:
            conn.close()

    def init_role_permissions(self):
        """Initialize or update role permissions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Define role hierarchy and permissions
        role_permissions_config = {
            # System-level roles (company_id = NULL)
            'system_admin': {
                'level': 100,
                'can_manage_all_companies': True,
                'can_create_company': True,
                'can_delete_company': True,
                'can_manage_system_users': True,
                'can_view_all_analyses': True,
                'can_manage_subscriptions': True,
                'can_manage_roles': True,
                'can_view_system_logs': True,
                'description': 'Full platform access'
            },
            'system_support': {
                'level': 80,
                'can_manage_all_companies': True,
                'can_create_company': False,
                'can_delete_company': False,
                'can_manage_system_users': False,
                'can_view_all_analyses': True,
                'can_manage_subscriptions': False,
                'can_manage_roles': False,
                'can_view_system_logs': True,
                'description': 'Can view all companies, support access'
            },
            'system_auditor': {
                'level': 70,
                'can_manage_all_companies': False,
                'can_create_company': False,
                'can_delete_company': False,
                'can_manage_system_users': False,
                'can_view_all_analyses': True,
                'can_manage_subscriptions': False,
                'can_manage_roles': False,
                'can_view_system_logs': True,
                'description': 'Read-only across platform'
            },
            # Company-level roles (has company_id)
            'company_admin': {
                'level': 50,
                'can_manage_company_users': True,
                'can_create_user': True,
                'can_delete_user': True,
                'can_manage_tenders': True,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': True,
                'can_edit_company_settings': True,
                'description': 'Full company management'
            },
            'company_manager': {
                'level': 40,
                'can_manage_company_users': False,
                'can_create_user': True,
                'can_delete_user': False,
                'can_manage_tenders': True,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': False,
                'can_edit_company_settings': False,
                'description': 'Can manage tenders and create users'
            },
            'analyst': {
                'level': 30,
                'can_manage_company_users': False,
                'can_create_user': False,
                'can_delete_user': False,
                'can_manage_tenders': True,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': False,
                'can_edit_company_settings': False,
                'description': 'Can run analyses and view reports'
            },
            'viewer': {
                'level': 10,
                'can_manage_company_users': False,
                'can_create_user': False,
                'can_delete_user': False,
                'can_manage_tenders': False,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': False,
                'can_edit_company_settings': False,
                'description': 'Read-only access'
            }
        }
        
        for role, perms in role_permissions_config.items():
            cursor.execute('''
                INSERT OR REPLACE INTO role_permissions (role, permissions, updated_at)
                VALUES (?, ?, ?)
            ''', (role, json.dumps(perms), datetime.now()))
        
        conn.commit()
        conn.close()
        print("✅ Role permissions initialized")
    def migrate_user_columns(self):
        """Add missing columns to users table for system users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Columns to add if missing
        columns_to_add = {
            'account_type': "TEXT DEFAULT 'company'",
            'is_approved': "BOOLEAN DEFAULT 1",
            'registration_complete': "BOOLEAN DEFAULT 1",
            'approved_by': "INTEGER",
            'approved_at': "TIMESTAMP",
            'auth_provider': "TEXT DEFAULT 'email'",
            'email_verified': "BOOLEAN DEFAULT 1",
            'verification_token': "TEXT",
            'reset_token': "TEXT",
            'reset_token_expires': "TIMESTAMP"
        }
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    print(f"⚠️ Could not add {col_name}: {e}")
        
        conn.commit()
        conn.close() 
    def get_all_pending_users(self):
        """Get all pending user registrations across all companies (for system admin)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Fix: Include users where is_approved = 0, regardless of registration_complete
        cursor.execute('''
            SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, 
                u.created_at, u.created_by, c.company_name, u.is_approved, u.is_active
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.id
            WHERE u.is_approved = 0
            ORDER BY u.created_at ASC
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        result = []
        for user in users:
            result.append({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'full_name': user[3],
                'phone': user[4] if len(user) > 4 else '',
                'role': user[5] if len(user) > 5 else 'user',
                'created_at': user[6] if len(user) > 6 else '',
                'created_by': user[7] if len(user) > 7 else None,
                'company_name': user[8] if len(user) > 8 else 'N/A',
                'is_approved': user[9] if len(user) > 9 else 0,
                'is_active': user[10] if len(user) > 10 else 1
            })
        
        print(f"🔍 Found {len(result)} pending users")  # Debug
        return result


    
    def migrate_company_isolation(self):
        """Ensure proper company isolation and add missing columns"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns in tender_analyses
        cursor.execute("PRAGMA table_info(tender_analyses)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Add company_id to tender_analyses if missing
        if 'company_id' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE tender_analyses ADD COLUMN company_id INTEGER REFERENCES companies(id)")
                print("✅ Added company_id to tender_analyses")
            except Exception as e:
                print(f"⚠️ Could not add company_id to tender_analyses: {e}")
        
        # Get existing columns in users
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        # Add is_company_admin flag to users if missing
        if 'is_company_admin' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN is_company_admin BOOLEAN DEFAULT 0")
                print("✅ Added is_company_admin to users")
            except Exception as e:
                print(f"⚠️ Could not add is_company_admin: {e}")
        
        # Add company_admin_approved_by if missing
        if 'company_admin_approved_by' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN company_admin_approved_by INTEGER")
                print("✅ Added company_admin_approved_by to users")
            except Exception as e:
                print(f"⚠️ Could not add company_admin_approved_by: {e}")
        
        # Add company_admin_approved_at if missing
        if 'company_admin_approved_at' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN company_admin_approved_at TIMESTAMP")
                print("✅ Added company_admin_approved_at to users")
            except Exception as e:
                print(f"⚠️ Could not add company_admin_approved_at: {e}")
        
        # Create indexes for faster company-based queries
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_company ON tender_analyses(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id)")
            print("✅ Created company isolation indexes")
        except Exception as e:
            print(f"⚠️ Could not create indexes: {e}")
        
        conn.commit()
        conn.close()
        print("✅ Company isolation migration completed")

    def get_company_subscription(self, company_id):
        """Get subscription details for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if company has a direct subscription
        cursor.execute('''
            SELECT id, plan, status, start_date, end_date, analyses_used, analyses_limit,
                payment_method, transaction_id, updated_at
            FROM subscriptions 
            WHERE company_id = ? AND company_id IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
        ''', (company_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'plan': result[1],
                'status': result[2],
                'start_date': result[3],
                'end_date': result[4],
                'analyses_used': result[5] or 0,
                'analyses_limit': result[6] or 5,
                'payment_method': result[7],
                'transaction_id': result[8],
                'updated_at': result[9]
            }
        
        # Return default if no subscription exists
        return {
            'plan': 'free',
            'status': 'active',
            'analyses_used': 0,
            'analyses_limit': 5,
            'start_date': datetime.now().date(),
            'end_date': datetime.now().date() + timedelta(days=30)
        }

    def update_company_subscription(self, company_id, plan, duration='monthly', payment_method='admin', transaction_id=None):
        """Update or create subscription for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        start_date = datetime.now().date()
        
        # Plan limits and pricing
        plan_limits = {
            'free': {'limit': 5, 'price': 0},
            'basic': {'limit': 30, 'price': 4999},
            'professional': {'limit': -1, 'price': 14999},
            'enterprise': {'limit': -1, 'price': 49999}
        }
        
        if duration == 'monthly':
            end_date = start_date + timedelta(days=30)
        else:
            end_date = start_date + timedelta(days=365)
        
        # Check if subscription exists
        cursor.execute('SELECT id FROM subscriptions WHERE company_id = ? AND company_id IS NOT NULL', (company_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE subscriptions 
                SET plan = ?, status = 'active', start_date = ?, end_date = ?, 
                    analyses_limit = ?, payment_method = ?, transaction_id = ?, updated_at = ?
                WHERE company_id = ?
            ''', (plan, start_date, end_date, plan_limits[plan]['limit'], 
                payment_method, transaction_id or f"ADMIN_{datetime.now().strftime('%Y%m%d%H%M%S')}", 
                datetime.now(), company_id))
        else:
            cursor.execute('''
                INSERT INTO subscriptions (company_id, plan, status, start_date, end_date, 
                                        analyses_limit, payment_method, transaction_id)
                VALUES (?, ?, 'active', ?, ?, ?, ?, ?)
            ''', (company_id, plan, start_date, end_date, plan_limits[plan]['limit'], 
                payment_method, transaction_id or f"ADMIN_{datetime.now().strftime('%Y%m%d%H%M%S')}"))
        
        conn.commit()
        conn.close()
        return True
    def migrate_subscriptions_table(self):
        """Add missing columns to subscriptions table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(subscriptions)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Add created_at if missing (without default first)
        if 'created_at' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE subscriptions ADD COLUMN created_at TIMESTAMP")
                # Set default value for existing rows
                cursor.execute("UPDATE subscriptions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
                print("✅ Added created_at to subscriptions")
            except Exception as e:
                print(f"⚠️ Could not add created_at: {e}")
        
        # Add company_id if missing
        if 'company_id' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE subscriptions ADD COLUMN company_id INTEGER REFERENCES companies(id)")
                print("✅ Added company_id to subscriptions")
            except Exception as e:
                print(f"⚠️ Could not add company_id: {e}")
        
        # Add updated_at if missing (without default first)
        if 'updated_at' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE subscriptions ADD COLUMN updated_at TIMESTAMP")
                # Set default value for existing rows
                cursor.execute("UPDATE subscriptions SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
                print("✅ Added updated_at to subscriptions")
            except Exception as e:
                print(f"⚠️ Could not add updated_at: {e}")
        
        conn.commit()
        conn.close()
        print("✅ Subscriptions table migration completed")
    
    def migrate_tender_analyses_table(self):
        """Add missing columns to tender_analyses table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(tender_analyses)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Define missing columns to add
        columns_to_add = {
            'district': "TEXT",
            'thana': "TEXT",
            'risk_strategy': "TEXT",
            'confidence_score': "REAL DEFAULT 0.70",
            'expected_profit': "REAL DEFAULT 0",
            'expected_value': "REAL DEFAULT 0",
            'competitor_bids': "TEXT",  # JSON string
            'slt_threshold': "REAL DEFAULT 0",
            'nppi_factor': "REAL DEFAULT 0.92",
            'weighted_average': "REAL DEFAULT 0"
        }
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE tender_analyses ADD COLUMN {col_name} {col_type}")
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    print(f"⚠️ Could not add {col_name}: {e}")
        
        conn.commit()
        conn.close()
        print("✅ Tender analyses table migration completed")    
        # Singleton instance
db = DatabaseManager()