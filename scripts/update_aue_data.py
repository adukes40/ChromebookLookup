#!/usr/bin/env python3
"""
Scrape Google's AUE support page and update database with correct dates
"""
import requests
from bs4 import BeautifulSoup
import sys
import os

# Add parent directory to path
sys.path.insert(0, '/opt/chromebook-dashboard')

from database.connection import db
from database.models import Chromebook
from datetime import datetime

def scrape_google_aue_page():
    """Scrape the Google AUE support page"""
    url = "https://support.google.com/chrome/a/answer/6220366?hl=en"
    
    print("Fetching Google AUE data...")
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all tables (one per manufacturer)
    tables = soup.find_all('table')
    
    aue_mapping = {}
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip header
            cols = row.find_all('td')
            if len(cols) >= 2:
                model = cols[0].get_text(strip=True)
                aue_date = cols[1].get_text(strip=True)
                
                # Convert "Jun 2029" to "2029-06"
                if aue_date and aue_date != 'N/A':
                    try:
                        dt = datetime.strptime(aue_date, '%b %Y')
                        aue_mapping[model] = dt.strftime('%Y-%m-%d')
                    except:
                        pass
    
    print(f"✓ Found {len(aue_mapping)} models with AUE dates")
    return aue_mapping

def update_database(aue_mapping):
    """Update database with AUE dates based on model matching"""
    
    with db.get_session() as session:
        # Get all unique models
        models = session.query(Chromebook.model).distinct().all()
        
        updated = 0
        for (model,) in models:
            if not model:
                continue
            
            # Try exact match first
            aue_date = aue_mapping.get(model)
            
            # Try partial matching if no exact match
            if not aue_date:
                for aue_model, date in aue_mapping.items():
                    if aue_model.lower() in model.lower() or model.lower() in aue_model.lower():
                        aue_date = date
                        break
            
            if aue_date:
                # Update all devices with this model
                count = session.query(Chromebook).filter(
                    Chromebook.model == model,
                    Chromebook.aue_date.is_(None)  # Only update if not already set
                ).update({'aue_date': aue_date})
                
                if count > 0:
                    print(f"  Updated {count} devices: {model} → {aue_date}")
                    updated += count
        
        session.commit()
        print(f"\n✓ Updated {updated} total devices")

if __name__ == '__main__':
    aue_mapping = scrape_google_aue_page()
    update_database(aue_mapping)
    print("\n✅ AUE data update complete!")
