#!/usr/bin/env python3
"""
Comprehensive AUE corrections from Google's official support page
https://support.google.com/chrome/a/answer/6220366
Last updated: December 2025
"""
import sys
sys.path.insert(0, '/opt/chromebook-dashboard')

from database.connection import db
from database.models import Chromebook

# Complete AUE dates from Google's official page (YYYY-MM-DD format)
CORRECT_AUE_DATES = {
    # Acer
    "Acer Chromebook 11 (C720, C720P)": "2019-06-01",
    "Acer Chromebook 11 (C732, C732T, C732L, C732LT)": "2027-06-01",
    "Acer Chromebook 11 (C740)": "2021-06-01",
    "Acer Chromebook 11 (C771, C771T)": "2023-06-01",
    "Acer Chromebook 11 (CB311-8H, CB311-8HT)": "2027-06-01",
    "Acer Chromebook 11 N7 (C731, C731T, CB311-7H, CB311-7HT)": "2022-06-01",
    "Acer Chromebook 13 (CB713-1W)": "2028-06-01",
    "Acer Chromebook 14 (CB3-431)": "2022-06-01",
    "Acer Chromebook 15 (CB315-1H, CB315-1HT)": "2027-06-01",
    "Acer Chromebook 15 (CB515-1H, CB515-1HT)": "2027-06-01",
    "Acer Chromebook 311 (C722/C722T)": "2030-06-01",
    "Acer Chromebook 311 (C733, C733U, C733T, CB311-9H, CB311-9HT)": "2029-06-01",
    "Acer Chromebook 311 (CB311-10H, C721)": "2029-06-01",
    "Acer Chromebook 311 (CB311-11H/CB311-11HT)": "2030-06-01",
    "Acer Chromebook 311 (CB311-12H/CB311-12HT)": "2033-06-01",
    "Acer Chromebook 314 (C933, C933T, C933L, C933LT, CB314-1H, CB314-1HT)": "2029-06-01",
    "Acer Chromebook 314 (CB314-2H/CB314-2HT, C922)": "2030-06-01",
    "Acer Chromebook 315 (CB315-2H, CB315-2HT)": "2029-06-01",
    "Acer Chromebook 315 (CB315-3H, CB315-3HT)": "2029-06-01",
    "Acer Chromebook 511 (C734, C734T, C733-R, C733T-R)": "2031-06-01",
    "Acer Chromebook 511( C736, C736T, C736L, C736LT )": "2033-06-01",
    "Acer Chromebook 512 (C851, C851T, CB512)": "2029-06-01",
    "Acer Chromebook 514": "2027-06-01",
    "Acer Chromebook 714 (CB714-1W, CB714-1WT)": "2028-06-01",
    "Acer Chromebook 715 (CB715-1W, CB715-1WT)": "2028-06-01",
    "Acer Chromebook R11 (CB5-132T, C738T)": "2022-06-01",
    "Acer Chromebook R13 (CB5-312T)": "2026-08-01",
    "Acer Chromebook Spin 11 (CP311-1H, CP311-1HN)": "2027-06-01",
    "Acer Chromebook Spin 11 (R751T, R751TN, CP511-1H, CP511-1HN)": "2027-06-01",
    "Acer Chromebook Spin 13 (CP713-1WN)": "2028-06-01",
    "Acer Chromebook Spin 15 (CP315-1H)": "2027-06-01",
    "Acer Chromebook Spin 311 (CP311-2H, CP311-2HN)": "2029-06-01",
    "Acer Chromebook Spin 311 (CP311-3H)": "2030-06-01",
    "Acer Chromebook Spin 311 (R721T)": "2029-06-01",
    "Acer Chromebook Spin 311 (R722T)": "2030-06-01",
    "Acer Chromebook Spin 511 (R752T, R752TN, CP511-2HT)": "2029-06-01",
    "Acer Chromebook Spin 512 (R851TN, R852T, R852TN)": "2029-06-01",
    "Acer Chromebook Plus 514 (CB514-3H, CB514-3HT)": "2033-06-01",
    
    # Dell
    "Dell Chromebook 11": "2019-06-01",
    "Dell Chromebook 11 (3120)": "2021-09-01",
    "Dell Chromebook 11 (3180)": "2022-06-01",
    "Dell Chromebook 11 (5190)": "2027-06-01",
    "Dell Chromebook 3100": "2029-06-01",
    "Dell Chromebook 3110": "2031-06-01",
    "Dell Chromebook 3120": "2033-06-01",
    "Dell Chromebook 11 2-in-1 (3189)": "2022-06-01",
    "Dell Chromebook 11 2-in-1 (5190)": "2027-06-01",
    "Dell Chromebook 3100 2-in-1": "2029-06-01",
    "Dell Chromebook 3110 2-in-1": "2031-06-01",
    "Dell Chromebook 3120 2-in-1": "2033-06-01",
    "Dell Chromebook 13 (7310)": "2021-06-01",
    "Dell Chromebook 13 (3380)": "2023-06-01",
    "Dell Chromebook 3400": "2029-06-01",
    "Dell Inspiron Chromebook 14 2-in-1 (7486)": "2028-06-01",
    
    # HP
    "HP Chromebook 11 G3": "2021-09-01",
    "HP Chromebook 11 G4": "2021-09-01",
    "HP Chromebook 11 G4 EE": "2021-09-01",
    "HP Chromebook 11 G3/G4/G4 EE": "2021-09-01",
    "HP Chromebook 11 G5": "2022-06-01",
    "HP Chromebook 11 G5 EE": "2022-06-01",
    "HP Chromebook 11 G6 EE": "2027-06-01",
    "HP Chromebook 11A G6 EE": "2029-06-01",
    "HP Chromebook 11 G7 EE": "2029-06-01",
    "HP Chromebook 11 G8 EE": "2029-06-01",
    "HP Chromebook 11A G8 EE": "2029-06-01",
    "HP Chromebook 11A G6 EE/ HP Chromebook 11A G8 EE": "2029-06-01",
    "HP Chromebook 11 G9 EE": "2031-06-01",
    "HP Chromebook 11-v0": "2022-06-01",
    "Chromebook 11-v0": "2022-06-01",
    "HP Chromebook 14": "2019-06-01",
    "HP Chromebook 14 G3": "2019-10-01",
    "HP Chromebook 14 G4": "2021-09-01",
    "HP Chromebook 14 G5": "2027-06-01",
    "HP Chromebook 14 G6": "2029-06-01",
    "HP Chromebook 14 G7": "2031-06-01",
    "HP Chromebook x360 11 G1 EE": "2027-06-01",
    "HP Chromebook x360 11 G2 EE": "2029-06-01",
    "HP Chromebook x360 11 G3 EE": "2029-06-01",
    "HP Chromebook x360 11 G4 EE": "2031-06-01",
    "HP Chromebook x360 14 G1": "2028-06-01",
    
    # Lenovo
    "Lenovo 100e Chromebook": "2027-06-01",
    "Lenovo 100e Chromebook 2nd Gen": "2029-06-01",
    "Lenovo 100e Chromebook 2nd Gen AST": "2029-06-01",
    "Lenovo 100e Chromebook Gen 3": "2031-06-01",
    "Lenovo 100e Chromebook Gen 3 AMD": "2031-06-01",
    "Lenovo 100e Chromebook Gen 4": "2033-06-01",
    "Lenovo 100e Chromebook Gen 4 (ADL-N)": "2033-06-01",
    "Lenovo 300e Chromebook": "2027-06-01",
    "Lenovo 300e Chromebook 2nd Gen": "2029-06-01",
    "Lenovo 300e Chromebook 2nd Gen AST": "2029-06-01",
    "Lenovo 300e Chromebook Gen 3": "2031-06-01",
    "Lenovo 500e Chromebook": "2027-06-01",
    "Lenovo 500e Chromebook 2nd Gen": "2029-06-01",
    "Lenovo 500e Chromebook Gen 3": "2031-06-01",
    "Lenovo N20 Chromebook": "2019-06-01",
    "Lenovo N21 Chromebook": "2021-09-01",
    "Lenovo N22 Chromebook": "2022-06-01",
    "Lenovo N23 Chromebook": "2022-06-01",
    "Lenovo N23 Yoga Chromebook": "2027-06-01",
    "Lenovo N42 Chromebook": "2022-06-01",
    "Lenovo Chromebook Duet": "2030-06-01",
    "Lenovo Chromebook Duet EDU G2": "2034-06-01",
    "Lenovo IdeaPad C330 Chromebook": "2027-06-01",
}

def update_aue_dates():
    with db.get_session() as session:
        total_updated = 0
        
        for model, correct_aue in CORRECT_AUE_DATES.items():
            count = session.query(Chromebook).filter(
                Chromebook.model == model
            ).update({'aue_date': correct_aue})
            
            if count > 0:
                print(f"✓ Updated {count:5d} devices: {model} → {correct_aue[:7]}")
                total_updated += count
        
        session.commit()
        print(f"\n✅ Total updated: {total_updated} devices")

if __name__ == '__main__':
    update_aue_dates()
