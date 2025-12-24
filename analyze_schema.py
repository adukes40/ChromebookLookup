#!/usr/bin/env python3
"""
Analyze database schema and statistics
"""
import sys
import os
from sqlalchemy import text, inspect

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import db
from database.models import Chromebook, User, MerakiClient, SyncLog


def analyze_schema():
    """Analyze and document current database schema"""

    print("=" * 80)
    print("CHROMEBOOK DASHBOARD - DATABASE SCHEMA ANALYSIS")
    print("=" * 80)
    print()

    with db.get_session() as session:
        # Get PostgreSQL version
        result = session.execute(text('SELECT version()'))
        version = result.fetchone()[0]
        print(f"PostgreSQL Version: {version.split(',')[0]}")
        print()

        # List all tables
        result = session.execute(text("""
            SELECT table_name,
                   pg_size_pretty(pg_total_relation_size(quote_ident(table_name)::regclass)) AS size
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        print("=" * 80)
        print("TABLES")
        print("=" * 80)
        for row in result:
            print(f"  {row[0]:<30} {row[1]}")
        print()

        # Get table row counts
        print("=" * 80)
        print("TABLE STATISTICS")
        print("=" * 80)

        # Chromebooks
        count = session.query(Chromebook).count()
        print(f"\nChromebooks: {count:,} records")

        result = session.execute(text("""
            SELECT status, COUNT(*) as count
            FROM chromebooks
            GROUP BY status
            ORDER BY count DESC
        """))
        print("  By Status:")
        for row in result:
            print(f"    {row[0]:<20} {row[1]:>8,}")

        result = session.execute(text("""
            SELECT
                COUNT(CASE WHEN annotated_user IS NOT NULL THEN 1 END) as assigned,
                COUNT(CASE WHEN annotated_user IS NULL THEN 1 END) as unassigned
            FROM chromebooks
        """))
        row = result.fetchone()
        print(f"  Assigned: {row[0]:,}")
        print(f"  Unassigned: {row[1]:,}")

        # Users
        count = session.query(User).count()
        print(f"\nUsers: {count:,} records")

        result = session.execute(text("""
            SELECT
                COUNT(CASE WHEN device_count > 0 THEN 1 END) as with_devices,
                COUNT(CASE WHEN device_count = 0 THEN 1 END) as without_devices
            FROM users
        """))
        row = result.fetchone()
        print(f"  With Devices: {row[0]:,}")
        print(f"  Without Devices: {row[1]:,}")

        # Meraki Clients
        count = session.query(MerakiClient).count()
        print(f"\nMeraki Clients: {count:,} records")

        # Sync Logs
        count = session.query(SyncLog).count()
        print(f"\nSync Logs: {count:,} records")

        result = session.execute(text("""
            SELECT sync_type, status, COUNT(*) as count
            FROM sync_logs
            GROUP BY sync_type, status
            ORDER BY sync_type, status
        """))
        print("  By Type/Status:")
        for row in result:
            print(f"    {row[0]:<15} {row[1]:<15} {row[2]:>6,}")

        # Get last sync info
        result = session.execute(text("""
            SELECT sync_type, completed_at, duration_seconds,
                   records_processed, records_created, records_updated
            FROM sync_logs
            WHERE status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 5
        """))
        print("\n  Last 5 Completed Syncs:")
        for row in result:
            print(f"    {row[0]:<15} {row[1]} ({row[2]}s) - Processed: {row[3]}, Created: {row[4]}, Updated: {row[5]}")

        print()

        # Analyze indexes
        print("=" * 80)
        print("INDEXES")
        print("=" * 80)

        result = session.execute(text("""
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """))

        current_table = None
        for row in result:
            if row[0] != current_table:
                print(f"\n{row[0]}:")
                current_table = row[0]
            print(f"  {row[1]}")
            # print(f"    {row[2]}")

        print()

        # Detailed column information for each table
        print("=" * 80)
        print("DETAILED SCHEMA")
        print("=" * 80)

        inspector = inspect(db.engine)

        for table_name in ['chromebooks', 'users', 'meraki_clients', 'sync_logs']:
            print(f"\n{table_name.upper()}")
            print("-" * 80)
            columns = inspector.get_columns(table_name)

            print(f"{'Column':<30} {'Type':<25} {'Nullable':<10} {'Default'}")
            print("-" * 80)
            for col in columns:
                col_type = str(col['type'])
                nullable = 'YES' if col['nullable'] else 'NO'
                default = str(col['default']) if col['default'] else ''
                print(f"{col['name']:<30} {col_type:<25} {nullable:<10} {default}")

        print()
        print("=" * 80)
        print("FOREIGN KEYS & RELATIONSHIPS")
        print("=" * 80)

        for table_name in ['chromebooks', 'users', 'meraki_clients', 'sync_logs']:
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                print(f"\n{table_name}:")
                for fk in fks:
                    print(f"  {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
            else:
                print(f"\n{table_name}: No foreign keys")

        print()

        # Query performance analysis
        print("=" * 80)
        print("QUERY PERFORMANCE INSIGHTS")
        print("=" * 80)

        # Check for missing indexes
        result = session.execute(text("""
            SELECT
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation
            FROM pg_stats
            WHERE schemaname = 'public'
                AND n_distinct > 100
            ORDER BY tablename, attname
            LIMIT 20
        """))

        print("\nHigh Cardinality Columns (potential index candidates):")
        print(f"{'Table':<20} {'Column':<30} {'Distinct Values':<20}")
        print("-" * 70)
        for row in result:
            print(f"{row[1]:<20} {row[2]:<30} {int(row[3]) if row[3] > 0 else 'N/A':<20}")

        print()

        # Optimization recommendations
        print("=" * 80)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("=" * 80)
        print()

        recommendations = []

        # Check if tables need vacuuming
        result = session.execute(text("""
            SELECT
                schemaname,
                relname,
                n_dead_tup,
                n_live_tup,
                ROUND(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_pct
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
                AND n_dead_tup > 0
            ORDER BY dead_pct DESC
        """))

        vacuum_needed = []
        for row in result:
            if row[4] and row[4] > 10:
                vacuum_needed.append(row[1])
                recommendations.append(f"Consider VACUUM on {row[1]} (Dead tuples: {row[4]:.2f}%)")

        # Check for sequential scans on large tables
        result = session.execute(text("""
            SELECT
                schemaname,
                relname,
                seq_scan,
                idx_scan,
                n_live_tup,
                CASE
                    WHEN seq_scan > 0 THEN ROUND(idx_scan::numeric / seq_scan, 2)
                    ELSE NULL
                END as idx_ratio
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
                AND n_live_tup > 1000
            ORDER BY seq_scan DESC
        """))

        print("Table Scan Statistics:")
        print(f"{'Table':<20} {'Seq Scans':<15} {'Index Scans':<15} {'Rows':<15} {'Index Ratio'}")
        print("-" * 80)
        for row in result:
            print(f"{row[1]:<20} {row[2]:<15} {row[3] or 0:<15} {row[4]:<15} {row[5] or 'N/A'}")

            if row[2] > 1000 and (row[3] is None or row[3] < row[2] * 0.1):
                recommendations.append(f"High sequential scans on {row[1]} - consider adding indexes")

        print()

        if recommendations:
            print("\nRecommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("\nNo immediate optimization recommendations. Database is healthy!")

        print()
        print("=" * 80)


if __name__ == "__main__":
    try:
        analyze_schema()
    except Exception as e:
        print(f"Error analyzing schema: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
