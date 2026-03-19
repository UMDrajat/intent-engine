#!/usr/bin/env python
"""Check database status"""

import os
import sys

# Add parent directory (app root) to path so we can import database module
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from app.database import Ad, AdGroup, AdMetric, Advertiser, Campaign, CreativeAsset, SessionLocal

db = SessionLocal()
try:
    print(f"Advertisers: {db.query(Advertiser).count()}")
    print(f"Campaigns: {db.query(Campaign).count()}")
    print(f"Ad Groups: {db.query(AdGroup).count()}")
    print(f"Ads: {db.query(Ad).count()}")
    print(f"Creative Assets: {db.query(CreativeAsset).count()}")
    print(f"Metrics: {db.query(AdMetric).count()}")
finally:
    db.close()
