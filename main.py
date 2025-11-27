import mysql.connector
import sqlite3
import sys
from decimal import Decimal
from datetime import date, datetime, timedelta

# MySQL connection settings
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  
    'database': 'university'
}

# SQLite database file
SQLITE_DB = 'university.db'


def convert_value(value):
    """Convert MySQL values to SQLite compatible types"""
    if value is None:
        return None
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (datetime, date)):
        return str(value)
    elif isinstance(value, timedelta):
        return str(value)
    elif isinstance(value, bytes):
        return value
    elif isinstance(value, (list, dict)):
        return str(value)
    else:
        return value


def convert_row(row):
    """Convert all values in a row"""
    return tuple(convert_value(val) for val in row)


def get_mysql_connection():
    """Connect to MySQL database"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        print("✓ Connected to MySQL successfully")
        return conn
    except mysql.connector.Error as e:
        print(f"✗ MySQL connection error: {e}")
        sys.exit(1)


def get_sqlite_connection():
    """Connect to SQLite database"""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        print(f"✓ SQLite database '{SQLITE_DB}' created/opened")
        return conn
    except sqlite3.Error as e:
        print(f"✗ SQLite error: {e}")
        sys.exit(1)


def mysql_type_to_sqlite(mysql_type):
    """Convert MySQL data types to SQLite types"""
    mysql_type = mysql_type.upper()
    
    if any(t in mysql_type for t in ['INT', 'TINYINT', 'SMALLINT', 'MEDIUMINT', 'BIGINT', 'BOOLEAN', 'BOOL']):
        return 'INTEGER'
    elif any(t in mysql_type for t in ['FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC']):
        return 'REAL'
    elif any(t in mysql_type for t in ['BLOB', 'BINARY', 'VARBINARY', 'LONGBLOB', 'MEDIUMBLOB', 'TINYBLOB']):
        return 'BLOB'
    else:
        return 'TEXT'


def get_all_tables(mysql_cursor):
    """Get list of all tables in MySQL database"""
    mysql_cursor.execute("SHOW TABLES")
    tables = [table[0] for table in mysql_cursor.fetchall()]
    return tables


def get_table_structure(mysql_cursor, table_name):
    """Get column information for a table"""
    mysql_cursor.execute(f"DESCRIBE `{table_name}`")
    columns = mysql_cursor.fetchall()
    return columns


def get_primary_keys(mysql_cursor, table_name):
    """Get primary key columns for a table"""
    mysql_cursor.execute(f"""
        SELECT COLUMN_NAME 
        FROM information_schema.KEY_COLUMN_USAGE 
        WHERE TABLE_SCHEMA = '{MYSQL_CONFIG['database']}' 
        AND TABLE_NAME = '{table_name}' 
        AND CONSTRAINT_NAME = 'PRIMARY'
        ORDER BY ORDINAL_POSITION
    """)
    return [row[0] for row in mysql_cursor.fetchall()]


def create_sqlite_table(sqlite_cursor, table_name, columns, primary_keys):
    """Create table in SQLite with same structure"""
    column_definitions = []
    
    for col in columns:
        col_name = col[0]
        col_type = col[1]
        is_nullable = col[2]
        default_value = col[4]
        extra = col[5] if len(col) > 5 else ''
        
        sqlite_type = mysql_type_to_sqlite(col_type)
        col_def = f'`{col_name}` {sqlite_type}'
        
        if is_nullable == 'NO':
            col_def += ' NOT NULL'
        
        if 'auto_increment' in extra.lower():
            col_def = f'`{col_name}` INTEGER PRIMARY KEY AUTOINCREMENT'
            column_definitions.append(col_def)
            continue
        
        if default_value is not None:
            if sqlite_type == 'TEXT':
                col_def += f" DEFAULT '{default_value}'"
            else:
                col_def += f" DEFAULT {default_value}"
        
        column_definitions.append(col_def)
    
    # Add primary key constraint if not auto_increment
    pk_cols = [col[0] for col in columns if 'auto_increment' in (col[5] if len(col) > 5 else '').lower()]
    if primary_keys and not pk_cols:
        pk_str = ', '.join([f'`{pk}`' for pk in primary_keys])
        column_definitions.append(f'PRIMARY KEY ({pk_str})')
    
    create_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n  " + ",\n  ".join(column_definitions) + "\n)"
    
    sqlite_cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
    sqlite_cursor.execute(create_sql)
    
    return True


def copy_table_data(mysql_cursor, sqlite_cursor, sqlite_conn, table_name):
    """Copy all data from MySQL table to SQLite table"""
    mysql_cursor.execute(f"SELECT * FROM `{table_name}`")
    rows = mysql_cursor.fetchall()
    
    if not rows:
        return 0
    
    # Get column count
    mysql_cursor.execute(f"DESCRIBE `{table_name}`")
    columns = mysql_cursor.fetchall()
    col_count = len(columns)
    
    placeholders = ', '.join(['?' for _ in range(col_count)])
    insert_sql = f"INSERT INTO `{table_name}` VALUES ({placeholders})"
    
    # Convert and insert data in batches
    batch_size = 1000
    total_rows = 0
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        # Convert each row to SQLite compatible types
        converted_batch = [convert_row(row) for row in batch]
        sqlite_cursor.executemany(insert_sql, converted_batch)
        sqlite_conn.commit()
        total_rows += len(batch)
    
    return total_rows


def migrate_database():
    """Main function to migrate all data from MySQL to SQLite"""
    print("=" * 50)
    print("   MySQL to SQLite Migration Tool")
    print("=" * 50)
    print()
    
    # Connect to databases
    mysql_conn = get_mysql_connection()
    mysql_cursor = mysql_conn.cursor()
    
    sqlite_conn = get_sqlite_connection()
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get all tables
    tables = get_all_tables(mysql_cursor)
    print(f"\n✓ Found {len(tables)} tables in database '{MYSQL_CONFIG['database']}'")
    print("-" * 50)
    
    # Migrate each table
    total_tables = 0
    total_rows = 0
    
    for table_name in tables:
        print(f"\n▶ Processing table: {table_name}")
        
        # Get table structure
        columns = get_table_structure(mysql_cursor, table_name)
        primary_keys = get_primary_keys(mysql_cursor, table_name)
        
        # Create table in SQLite
        create_sqlite_table(sqlite_cursor, table_name, columns, primary_keys)
        print(f"  ✓ Table structure created ({len(columns)} columns)")
        
        # Copy data
        rows_copied = copy_table_data(mysql_cursor, sqlite_cursor, sqlite_conn, table_name)
        print(f"  ✓ Copied {rows_copied} rows")
        
        total_tables += 1
        total_rows += rows_copied
    
    # Close connections
    mysql_cursor.close()
    mysql_conn.close()
    sqlite_cursor.close()
    sqlite_conn.close()
    
    # Summary
    print("\n" + "=" * 50)
    print("   Migration Complete!")
    print("=" * 50)
    print(f"  • Tables migrated: {total_tables}")
    print(f"  • Total rows copied: {total_rows}")
    print(f"  • SQLite file: {SQLITE_DB}")
    print("=" * 50)


if __name__ == "__main__":
    migrate_database()