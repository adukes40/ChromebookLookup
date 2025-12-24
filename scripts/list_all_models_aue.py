#!/usr/bin/env python3
"""
List all Chromebook models in the fleet with their AUE status
Helps identify which models need AUE dates added
"""
import sys
sys.path.insert(0, '/opt/chromebook-dashboard')

from database.connection import db
from database.models import Chromebook
from sqlalchemy import func
from datetime import datetime

def list_all_models():
    with db.get_session() as session:
        # Get all models with counts and AUE dates
        models = session.query(
            Chromebook.model,
            Chromebook.aue_date,
            func.count(Chromebook.device_id).label('count')
        ).filter(
            Chromebook.model.isnot(None)
        ).group_by(Chromebook.model, Chromebook.aue_date).order_by(
            func.count(Chromebook.device_id).desc()
        ).all()
        
        # Categorize by status
        active_models = []
        expired_models = []
        unknown_models = []
        
        for model, aue_date, count in models:
            if aue_date:
                try:
                    aue_dt = datetime.strptime(aue_date, '%Y-%m-%d')
                    is_expired = aue_dt < datetime.now()
                    
                    if is_expired:
                        expired_models.append((model, aue_date, count))
                    else:
                        active_models.append((model, aue_date, count))
                except:
                    unknown_models.append((model, aue_date, count))
            else:
                unknown_models.append((model, None, count))
        
        # Print Active Models
        print("=" * 100)
        print("ACTIVE MODELS (AUE Date in Future)")
        print("=" * 100)
        print(f"{'Model':<60} {'AUE Date':<12} {'Count':>8}")
        print("-" * 100)
        for model, aue, count in sorted(active_models, key=lambda x: x[2], reverse=True):
            print(f"{model:<60} {aue[:7]:<12} {count:>8,}")
        
        print(f"\nTotal Active: {len(active_models)} models, {sum(c for _,_,c in active_models):,} devices")
        
        # Print Expired Models
        print("\n" + "=" * 100)
        print("EXPIRED MODELS (AUE Date Passed)")
        print("=" * 100)
        print(f"{'Model':<60} {'AUE Date':<12} {'Count':>8}")
        print("-" * 100)
        for model, aue, count in sorted(expired_models, key=lambda x: x[2], reverse=True):
            print(f"{model:<60} {aue[:7]:<12} {count:>8,}")
        
        print(f"\nTotal Expired: {len(expired_models)} models, {sum(c for _,_,c in expired_models):,} devices")
        
        # Print Unknown/Missing AUE
        print("\n" + "=" * 100)
        print("UNKNOWN AUE (Needs to be Added to aue_corrections.py)")
        print("=" * 100)
        print(f"{'Model':<60} {'AUE Date':<12} {'Count':>8}")
        print("-" * 100)
        for model, aue, count in sorted(unknown_models, key=lambda x: x[2], reverse=True):
            aue_display = aue[:7] if aue else "MISSING"
            print(f"{model:<60} {aue_display:<12} {count:>8,}")
        
        print(f"\nTotal Unknown: {len(unknown_models)} models, {sum(c for _,_,c in unknown_models):,} devices")
        
        # Print Python code to add to corrections file
        if unknown_models:
            print("\n" + "=" * 100)
            print("ADD THESE TO /opt/chromebook-dashboard/scripts/aue_corrections.py:")
            print("=" * 100)
            for model, _, count in unknown_models[:20]:  # Show top 20
                print(f'    "{model}": "YYYY-MM-01",  # {count:,} devices - LOOKUP AUE DATE')

if __name__ == '__main__':
    list_all_models()
