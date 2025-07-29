"""Grid Bot State Persistence"""

import json
import pickle
import os
from typing import Dict, Any, Optional
from datetime import datetime
import sqlite3


class GridBotPersistence:
    """Handles saving and loading grid bot state"""
    
    def __init__(self, db_path: str = "gridbot_state.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_state (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                state_data BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                buy_price REAL NOT NULL,
                sell_price REAL NOT NULL,
                quantity REAL NOT NULL,
                profit REAL NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                order_id TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_state(self, state: Dict[str, Any]):
        """Save bot state to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Serialize state
            state_blob = pickle.dumps(state)
            symbol = state['config'].symbol
            
            # Check if state exists
            cursor.execute("SELECT id FROM bot_state WHERE symbol = ?", (symbol,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE bot_state 
                    SET state_data = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE symbol = ?
                """, (state_blob, symbol))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO bot_state (symbol, state_data)
                    VALUES (?, ?)
                """, (symbol, state_blob))
            
            conn.commit()
            
        except Exception as e:
            print(f"Error saving state: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def load_state(self, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load bot state from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if symbol:
                cursor.execute("""
                    SELECT state_data FROM bot_state 
                    WHERE symbol = ?
                    ORDER BY updated_at DESC LIMIT 1
                """, (symbol,))
            else:
                cursor.execute("""
                    SELECT state_data FROM bot_state 
                    ORDER BY updated_at DESC LIMIT 1
                """)
            
            result = cursor.fetchone()
            
            if result:
                return pickle.loads(result[0])
            
        except Exception as e:
            print(f"Error loading state: {e}")
        finally:
            conn.close()
        
        return None
    
    def save_trade(self, symbol: str, buy_price: float, sell_price: float, 
                   quantity: float, profit: float):
        """Save completed trade to history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO trade_history (symbol, buy_price, sell_price, quantity, profit)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, buy_price, sell_price, quantity, profit))
            
            conn.commit()
        except Exception as e:
            print(f"Error saving trade: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_order(self, symbol: str, order_id: str, side: str, 
                   price: float, quantity: float, status: str):
        """Save order to history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO order_history (symbol, order_id, side, price, quantity, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, order_id, side, price, quantity, status))
            
            conn.commit()
        except Exception as e:
            print(f"Error saving order: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_trade_history(self, symbol: str, limit: int = 100) -> list:
        """Get trade history for a symbol"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM trade_history 
                WHERE symbol = ?
                ORDER BY completed_at DESC
                LIMIT ?
            """, (symbol, limit))
            
            columns = [desc[0] for desc in cursor.description]
            trades = []
            
            for row in cursor.fetchall():
                trades.append(dict(zip(columns, row)))
            
            return trades
            
        except Exception as e:
            print(f"Error getting trade history: {e}")
            return []
        finally:
            conn.close()
    
    def get_statistics(self, symbol: str) -> dict:
        """Get historical statistics for a symbol"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Total trades
            cursor.execute("""
                SELECT COUNT(*) as total_trades,
                       SUM(profit) as total_profit,
                       AVG(profit) as avg_profit,
                       MAX(profit) as best_trade,
                       MIN(profit) as worst_trade,
                       SUM(quantity * sell_price) as total_volume
                FROM trade_history
                WHERE symbol = ?
            """, (symbol,))
            
            stats = dict(zip([desc[0] for desc in cursor.description], cursor.fetchone()))
            
            # Win rate
            cursor.execute("""
                SELECT COUNT(*) as winning_trades
                FROM trade_history
                WHERE symbol = ? AND profit > 0
            """, (symbol,))
            
            winning_trades = cursor.fetchone()[0]
            stats['win_rate'] = (winning_trades / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
            
            return stats
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
        finally:
            conn.close()
    
    def export_to_json(self, symbol: str, output_path: str):
        """Export bot data to JSON file"""
        data = {
            'symbol': symbol,
            'state': self.load_state(symbol),
            'trade_history': self.get_trade_history(symbol, limit=None),
            'statistics': self.get_statistics(symbol),
            'exported_at': datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Exported data to {output_path}")
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete old trades
            cursor.execute("""
                DELETE FROM trade_history
                WHERE completed_at < datetime('now', '-{} days')
            """.format(days))
            
            # Delete old orders
            cursor.execute("""
                DELETE FROM order_history
                WHERE created_at < datetime('now', '-{} days')
            """.format(days))
            
            conn.commit()
            print(f"Cleaned up data older than {days} days")
            
        except Exception as e:
            print(f"Error cleaning up data: {e}")
            conn.rollback()
        finally:
            conn.close()