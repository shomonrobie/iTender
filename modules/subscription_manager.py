# modules/subscription_manager.py

import streamlit as st
import pandas as pd
from datetime import datetime

# Plan definitions with limits and permissions
PLANS = {
    'free': {
        'name': 'Free',
        'price_monthly': 0,
        'price_yearly': 0,
        'analyses_limit': 5,
        'max_boq_generations': 5,
        'max_bid_optimizations': 5,
        'extension_auto_fills': 5,  # ← ADD THIS LINE
        'users_limit': 1,
        'can_edit_rates': False,
        'can_delete_rates': False,
        'can_create_versions': False,
        'can_export_data': False,
        'can_manage_team': False,
        'color': '#gray',
        'features': [
            '✓ 5 BOQ generations/month',
            '✓ 5 Bid optimizations/month',
            '✓ 5 Tender analyses/month',
            '✓ View rates only',
            '✓ Email support',
            '✓ 7-day history'
        ]
    },
    'basic': {
        'name': 'Basic',
        'price_monthly': 4999,
        'price_yearly': 49990,
        'analyses_limit': 30,
        'max_boq_generations': 30,
        'max_bid_optimizations': 30,
        'extension_auto_fills': 30,  # ← ADD THIS LINE
        'users_limit': 3,
        'can_edit_rates': False,
        'can_delete_rates': False,
        'can_create_versions': False,
        'can_export_data': True,
        'can_manage_team': False,
        'color': '#4CAF50',
        'features': [
            '✓ 30 BOQ generations/month',
            '✓ 30 Bid optimizations/month',
            '✓ 30 Tender analyses/month',
            '✓ Export reports (CSV/Excel)',
            '✓ AI-powered predictions',
            '✓ 30-day history',
            '✓ Email support'
        ]
    },
    'professional': {
        'name': 'Professional',
        'price_monthly': 14999,
        'price_yearly': 149990,
        'analyses_limit': -1,
        'max_boq_generations': 100,
        'max_bid_optimizations': 100,
        'extension_auto_fills': 100,  # ← ADD THIS LINE
        'users_limit': 10,
        'can_edit_rates': True,
        'can_delete_rates': False,
        'can_create_versions': True,
        'can_export_data': True,
        'can_manage_team': True,
        'color': '#2196F3',
        'features': [
            '✓ 100 BOQ generations/month',
            '✓ 100 Bid optimizations/month',
            '✓ Unlimited tender analyses',
            '✓ Edit rates & create versions',
            '✓ Team collaboration (up to 10 users)',
            '✓ Competitor tracking',
            '✓ API access',
            '✓ Priority support'
        ]
    },
    'enterprise': {
        'name': 'Enterprise',
        'price_monthly': 49999,
        'price_yearly': 499990,
        'analyses_limit': -1,
        'max_boq_generations': -1,
        'max_bid_optimizations': -1,
        'extension_auto_fills': -1,  # ← ADD THIS LINE (unlimited)
        'users_limit': -1,
        'can_edit_rates': True,
        'can_delete_rates': True,
        'can_create_versions': True,
        'can_export_data': True,
        'can_manage_team': True,
        'color': '#9C27B0',
        'features': [
            '✓ Unlimited BOQ generations',
            '✓ Unlimited Bid optimizations',
            '✓ Unlimited Tender analyses',
            '✓ Delete rates & manage all data',
            '✓ Unlimited team members',
            '✓ Custom AI model',
            '✓ Dedicated support',
            '✓ SLA guarantee',
            '✓ On-premise deployment option'
        ]
    }
}


class SubscriptionManager:
    """Manage company subscriptions and permissions"""
    
    def __init__(self, db):
        self.db = db
    
    def get_company_subscription(self, company_id):
        """Get active subscription for a company"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*, p.plan_name, p.max_boq_generations, p.max_bid_optimizations,
                       p.max_tender_analyses, p.max_users, p.can_export_data,
                       p.can_edit_rates, p.can_delete_rates, p.can_create_versions,
                       p.can_manage_team
                FROM subscriptions s
                LEFT JOIN subscription_plans p ON s.plan = p.plan_name
                WHERE s.company_id = ? AND s.status = 'active'
                ORDER BY s.created_at DESC LIMIT 1
            """, (company_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Get the plan from subscriptions table
                plan_name = row[3]  # plan column index
                
                # Get plan config
                plan_config = PLANS.get(plan_name, PLANS['free'])
                
                # Get usage values (handle potential missing columns)
                boq_used = 0
                bid_used = 0
                analyses_used = 0
                
                # Try to get column indices
                try:
                    # Try to find column positions
                    cursor.execute("PRAGMA table_info(subscriptions)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'boq_used' in columns:
                        boq_used = row[columns.index('boq_used')] if len(row) > columns.index('boq_used') else 0
                    if 'bid_optimizations_used' in columns:
                        bid_used = row[columns.index('bid_optimizations_used')] if len(row) > columns.index('bid_optimizations_used') else 0
                    if 'analyses_used' in columns:
                        analyses_used = row[columns.index('analyses_used')] if len(row) > columns.index('analyses_used') else 0
                except:
                    pass
                
                return {
                    'plan': plan_name,
                    'plan_name': plan_config['name'],
                    'status': row[4] if len(row) > 4 else 'active',
                    'analyses_used': analyses_used,
                    'boq_used': boq_used,
                    'bid_optimizations_used': bid_used,
                    'max_boq_generations': plan_config['max_boq_generations'],
                    'max_bid_optimizations': plan_config['max_bid_optimizations'],
                    'max_tender_analyses': plan_config['analyses_limit'],
                    'max_users': plan_config['users_limit'],
                    'can_export_data': plan_config['can_export_data'],
                    'can_edit_rates': plan_config['can_edit_rates'],
                    'can_delete_rates': plan_config['can_delete_rates'],
                    'can_create_versions': plan_config['can_create_versions'],
                    'can_manage_team': plan_config['can_manage_team'],
                    'end_date': row[5] if len(row) > 5 else None
                }
            
            # Return default free plan if no subscription found
            return self._get_default_free_plan()
            
        except Exception as e:
            print(f"Error getting subscription: {e}")
            return self._get_default_free_plan()
    def get_extension_limit_for_plan(self, plan_name: str) -> int:
        """Get extension auto-fill limit for a plan (configurable by admin)"""
        # This can be stored in database or config file
        # For now, use hardcoded limits
        plan_limits = {
            'free': 5,
            'basic': 30,
            'professional': 100,
            'enterprise': -1  # Unlimited
        }
        return plan_limits.get(plan_name, 5)
    
    def update_extension_limit_for_plan(self, plan_name: str, new_limit: int) -> bool:
        """Update extension limit for a plan (admin only)"""
        # Store in database
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE subscription_plans 
                SET extension_auto_fills = ? 
                WHERE plan_name = ?
            """, (new_limit, plan_name))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating plan limit: {e}")
            return False
    def _get_default_free_plan(self):
        """Return default free plan"""
        free_plan = PLANS['free']
        return {
            'plan': 'free',
            'plan_name': free_plan['name'],
            'status': 'active',
            'analyses_used': 0,
            'boq_used': 0,
            'bid_optimizations_used': 0,
            'max_boq_generations': free_plan['max_boq_generations'],
            'max_bid_optimizations': free_plan['max_bid_optimizations'],
            'max_tender_analyses': free_plan['analyses_limit'],
            'max_users': free_plan['users_limit'],
            'can_export_data': free_plan['can_export_data'],
            'can_edit_rates': free_plan['can_edit_rates'],
            'can_delete_rates': free_plan['can_delete_rates'],
            'can_create_versions': free_plan['can_create_versions'],
            'can_manage_team': free_plan['can_manage_team'],
            'end_date': None
        }
    def check_extension_limit(self, company_id: int) -> Tuple[bool, int, str]:
        """
        Check if company has reached its extension auto-fill limit.
        
        Returns:
            (can_proceed, remaining, message)
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get subscription plan
            sub = self.get_company_subscription(company_id)
            plan = sub.get('plan', 'free')
            
            # Get limit from plan
            plan_config = PLANS.get(plan, PLANS['free'])
            limit = plan_config.get('extension_auto_fills', 5)
            
            # Get current month usage
            now = datetime.now()
            start_of_month = datetime(now.year, now.month, 1)
            
            cursor.execute("""
                SELECT COUNT(*) FROM extension_auto_fill_log
                WHERE company_id = ? AND filled_at >= ?
            """, (company_id, start_of_month))
            
            used = cursor.fetchone()[0] or 0
            conn.close()
            
            if limit == -1:
                return True, -1, "Unlimited auto-fills"
            
            remaining = max(0, limit - used)
            
            if remaining > 0:
                return True, remaining, f"{remaining} auto-fills remaining this month"
            else:
                return False, 0, f"You've used all {limit} auto-fills this month. Please upgrade your plan."
                
        except Exception as e:
            print(f"Error checking extension limit: {e}")
            return True, -1, "Unable to check limit, proceeding anyway"

    def check_limit(self, company_id, resource_type):
        """
        Check if company has reached its limit for a resource.
        
        Args:
            company_id: Company ID
            resource_type: 'boq', 'bid_optimization', 'analysis', 'users'
        
        Returns:
            (can_proceed, remaining, message)
        """
        sub = self.get_company_subscription(company_id)
        
        resource_map = {
            'boq': ('max_boq_generations', 'boq_used', 'BOQ generations'),
            'bid_optimization': ('max_bid_optimizations', 'bid_optimizations_used', 'bid optimizations'),
            'analysis': ('max_tender_analyses', 'analyses_used', 'tender analyses'),
            'users': ('max_users', None, 'users')
        }
        
        if resource_type not in resource_map:
            return True, -1, "Unknown resource"
        
        max_field, used_field, name = resource_map[resource_type]
        max_limit = sub.get(max_field, 5)
        
        if resource_type == 'users':
            current_used = self._get_company_user_count(company_id)
        else:
            current_used = sub.get(used_field, 0)
        
        if max_limit == -1:
            return True, -1, f"Unlimited {name}"
        
        remaining = max_limit - current_used
        
        if remaining > 0:
            return True, remaining, f"{remaining} {name} remaining"
        else:
            return False, 0, f"No {name} remaining. Please upgrade your plan."
    
    def increment_usage(self, company_id, resource_type):
        """Increment usage counter for a company resource"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        field_map = {
            'boq': 'boq_used',
            'bid_optimization': 'bid_optimizations_used',
            'analysis': 'analyses_used'
        }
        
        if resource_type not in field_map:
            return False
        
        field = field_map[resource_type]
        
        try:
            cursor.execute(f"""
                UPDATE subscriptions 
                SET {field} = {field} + 1, updated_at = ?
                WHERE company_id = ? AND status = 'active'
            """, (datetime.now(), company_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error incrementing usage: {e}")
            conn.close()
            return False
    
    def _get_company_user_count(self, company_id):
        """Get number of active users in a company"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE company_id = ? AND is_active = 1
            """, (company_id,))
            
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 1
    
    def has_permission(self, company_id, permission):
        """Check if company has a specific permission"""
        sub = self.get_company_subscription(company_id)
        
        permission_map = {
            'edit_rates': sub.get('can_edit_rates', False),
            'delete_rates': sub.get('can_delete_rates', False),
            'create_versions': sub.get('can_create_versions', False),
            'export_data': sub.get('can_export_data', False),
            'manage_team': sub.get('can_manage_team', False)
        }
        
        return permission_map.get(permission, False)


def check_subscription_and_permission(db, resource_type=None, permission=None):
    """
    Check subscription limits and permissions.
    
    Args:
        db: Database instance
        resource_type: 'boq', 'bid_optimization', 'analysis', 'users'
        permission: 'edit_rates', 'delete_rates', 'create_versions', 'export_data', 'manage_team'
    
    Returns:
        (can_proceed, message)
    """
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role', 'viewer')
    
    # Admins bypass limits
    if user_role in ['admin', 'system_admin']:
        return True, "OK"
    
    if not company_id:
        return False, "No company associated with this account"
    
    sub_manager = SubscriptionManager(db)
    
    if resource_type:
        can_proceed, remaining, message = sub_manager.check_limit(company_id, resource_type)
        if not can_proceed:
            return False, message
    
    if permission:
        has_perm = sub_manager.has_permission(company_id, permission)
        if not has_perm:
            return False, f"You don't have permission to {permission.replace('_', ' ')}. Please upgrade your plan."
    
    return True, "OK"