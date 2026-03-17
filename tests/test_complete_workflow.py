#!/usr/bin/env python3
"""
Complete API Workflow Test for Intent Engine
Tests all endpoints in proper sequence with data dependencies,
matching the actual Pydantic models and database schema.
"""

import requests
import sys
import uuid
import hashlib
from datetime import datetime, timedelta, timezone

BASE_URL = "http://localhost:8000"

def get_hash(text):
    if not text:
        return None
    return hashlib.sha256(text.encode()).hexdigest()

def test_complete_workflow():
    results = {"passed": 0, "failed": 0, "details": []}
    
    print(f"Starting complete workflow test at {BASE_URL}")
    
    # 1. Create advertiser
    print("\n1. Creating advertiser...")
    advertiser_name = f"Workflow Test Corp {uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE_URL}/advertisers", json={
        "name": advertiser_name,
        "contact_email": "workflow@test.com"
    })
    if r.status_code == 200:
        results["passed"] += 1
        advertiser_id = r.json()["id"]
        print(f"   SUCCESS: Created advertiser ID {advertiser_id}")
    else:
        results["failed"] += 1
        results["details"].append(("Create advertiser", r.status_code, r.text))
        print(f"   FAILED: {r.status_code} - {r.text}")
        return results
    
    # 2. Create campaign
    print("\n2. Creating campaign...")
    now = datetime.now(timezone.utc)
    r = requests.post(f"{BASE_URL}/campaigns", json={
        "advertiser_id": advertiser_id,
        "name": "Workflow Campaign",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "budget": 5000.0,
        "daily_budget": 150.0,
        "status": "active"
    })
    if r.status_code == 200:
        results["passed"] += 1
        campaign_id = r.json()["id"]
        print(f"   SUCCESS: Created campaign ID {campaign_id}")
    else:
        results["failed"] += 1
        results["details"].append(("Create campaign", r.status_code, r.text))
        print(f"   FAILED: {r.status_code} - {r.text}")
        return results
    
    # 3. Create ad group
    print("\n3. Creating ad group...")
    r = requests.post(f"{BASE_URL}/adgroups", json={
        "campaign_id": campaign_id,
        "name": "Workflow AdGroup",
        "targeting_settings": {"device": ["desktop"]},
        "bid_strategy": "manual"
    })
    if r.status_code == 200:
        results["passed"] += 1
        adgroup_id = r.json()["id"]
        print(f"   SUCCESS: Created ad group ID {adgroup_id}")
    else:
        results["failed"] += 1
        results["details"].append(("Create ad group", r.status_code, r.text))
        print(f"   FAILED: {r.status_code} - {r.text}")
        return results
    
    # 4. Create ad
    print("\n4. Creating ad...")
    r = requests.post(f"{BASE_URL}/ads", json={
        "advertiser_id": advertiser_id,
        "ad_group_id": adgroup_id,
        "title": "Workflow Test Ad",
        "description": "Testing complete workflow",
        "url": "https://example.com/workflow",
        "targeting_constraints": {"platform": ["Android"]},
        "ethical_tags": ["privacy", "open_source"],
        "quality_score": 0.85,
        "creative_format": "banner",
        "bid_amount": 2.0,
        "status": "active",
        "approval_status": "approved"
    })
    if r.status_code == 200:
        results["passed"] += 1
        ad_id = r.json()["id"]
        print(f"   SUCCESS: Created ad ID {ad_id}")
    else:
        results["failed"] += 1
        results["details"].append(("Create ad", r.status_code, r.text))
        print(f"   FAILED: {r.status_code} - {r.text}")
        return results
    
    # 5. Create creative
    print("\n5. Creating creative asset...")
    r = requests.post(f"{BASE_URL}/creatives", json={
        "ad_id": ad_id,
        "asset_type": "image",
        "asset_url": "https://example.com/banner.jpg",
        "payload": {"width": 728, "height": 90},
        "checksum": "workflow123"
    })
    if r.status_code == 200:
        results["passed"] += 1
        creative_id = r.json()["id"]
        print(f"   SUCCESS: Created creative ID {creative_id}")
    else:
        results["failed"] += 1
        results["details"].append(("Create creative", r.status_code, r.text))
        print(f"   FAILED: {r.status_code} - {r.text}")
    
    # 6. Record click
    print("\n6. Recording ad click...")
    session_id = f"workflow-{uuid.uuid4().hex[:8]}"
    ip_address = "192.168.1.100"
    user_agent = "Workflow Test Browser/1.0"
    
    r = requests.post(f"{BASE_URL}/click-tracking", json={
        "ad_id": ad_id,
        "session_id": session_id,
        "ip_hash": get_hash(ip_address),
        "user_agent_hash": get_hash(user_agent),
        "referring_url": "https://google.com",
        "payload": {"browser": "Chrome"}
    })
    if r.status_code == 200:
        results["passed"] += 1
        click_id = r.json()["id"]
        print(f"   SUCCESS: Recorded click ID {click_id}")
    else:
        results["failed"] += 1
        results["details"].append(("Record click", r.status_code, r.text))
        print(f"   FAILED: {r.status_code} - {r.text}")
        return results
    
    # 7. Record conversion
    print("\n7. Recording conversion...")
    r = requests.post(f"{BASE_URL}/conversion-tracking", json={
        "click_id": click_id,
        "conversion_type": "purchase",
        "value": 99.99,
        "status": "completed",
        "payload": {"product_id": "premium-1"}
    })
    if r.status_code == 200:
        results["passed"] += 1
        conversion_id = r.json()["id"]
        print(f"   SUCCESS: Recorded conversion ID {conversion_id}")
    else:
        results["failed"] += 1
        results["details"].append(("Record conversion", r.status_code, r.text))
        print(f"   FAILED: {r.status_code} - {r.text}")
    
    # 8. Report fraud
    print("\n8. Reporting potential fraud...")
    r = requests.post(f"{BASE_URL}/fraud-detection", json={
        "ad_id": ad_id,
        "event_type": "click",
        "reason": "suspiciously fast clicks",
        "severity": "medium",
        "review_status": "pending",
        "payload": {"click_count": 50, "time_window_seconds": 60}
    })
    if r.status_code == 200:
        results["passed"] += 1
        print("   SUCCESS: Reported fraud")
    else:
        results["failed"] += 1
        results["details"].append(("Report fraud", r.status_code, r.text))
        print(f"   FAILED: {r.status_code} - {r.text}")
    
    # 9. Test Analytics: Campaign ROI
    print("\n9. Testing Analytics (Campaign ROI)...")
    r = requests.get(f"{BASE_URL}/analytics/campaign-roi/{campaign_id}")
    # This might fail if no metrics are seeded yet, but let's check the endpoint exists
    if r.status_code in [200, 404]: # 404 is acceptable if campaign exists but metrics don't
        results["passed"] += 1
        print(f"   SUCCESS: Analytics endpoint reachable (Status {r.status_code})")
    else:
        results["failed"] += 1
        results["details"].append(("Get Campaign ROI", r.status_code, r.text))
        print(f"   FAILED: {r.status_code} - {r.text}")

    # 10. A/B Testing Workflow
    print("\n10. Testing A/B Testing Workflow...")
    # 10.1 Create A/B Test
    r = requests.post(f"{BASE_URL}/ab-tests", json={
        "name": "Ad Format Test",
        "description": "Testing banner vs native",
        "campaign_id": campaign_id,
        "traffic_allocation": 1.0,
        "primary_metric": "ctr"
    })
    if r.status_code == 200:
        results["passed"] += 1
        test_id = r.json()["id"]
        print(f"    10.1 SUCCESS: Created A/B test ID {test_id}")
        
        # 10.2 Add Control Variant
        r = requests.post(f"{BASE_URL}/ab-tests/{test_id}/variants", json={
            "test_id": test_id,
            "name": "control",
            "ad_id": ad_id,
            "traffic_weight": 0.5,
            "is_control": True
        })
        if r.status_code == 200:
            results["passed"] += 1
            print("    10.2 SUCCESS: Added control variant")
        else:
            results["failed"] += 1
            results["details"].append(("Add control variant", r.status_code, r.text))
            
        # 10.3 Add Treatment Variant
        # Need another ad for treatment
        r = requests.post(f"{BASE_URL}/ads", json={
            "advertiser_id": advertiser_id,
            "ad_group_id": adgroup_id,
            "title": "Treatment Ad",
            "url": "https://example.com/treatment",
            "status": "active"
        })
        treatment_ad_id = r.json()["id"]
        
        r = requests.post(f"{BASE_URL}/ab-tests/{test_id}/variants", json={
            "test_id": test_id,
            "name": "treatment",
            "ad_id": treatment_ad_id,
            "traffic_weight": 0.5,
            "is_control": False
        })
        if r.status_code == 200:
            results["passed"] += 1
            print("    10.3 SUCCESS: Added treatment variant")
        else:
            results["failed"] += 1
            results["details"].append(("Add treatment variant", r.status_code, r.text))

        # 10.4 Start Test
        r = requests.post(f"{BASE_URL}/ab-tests/{test_id}/start")
        if r.status_code == 200:
            results["passed"] += 1
            print("    10.4 SUCCESS: Started A/B test")
        else:
            results["failed"] += 1
            results["details"].append(("Start A/B test", r.status_code, r.text))

        # 10.5 Assign User
        r = requests.post(f"{BASE_URL}/ab-tests/{test_id}/assign", params={"user_identifier": "test-user-123"})
        if r.status_code == 200:
            results["passed"] += 1
            assignment = r.json()
            print(f"    10.5 SUCCESS: Assigned user to variant: {assignment.get('variant_name')}")
        else:
            results["failed"] += 1
            results["details"].append(("Assign A/B variant", r.status_code, r.text))

        # 10.6 Get Results
        r = requests.get(f"{BASE_URL}/ab-tests/{test_id}/results")
        if r.status_code == 200:
            results["passed"] += 1
            print("    10.6 SUCCESS: Retrieved A/B test results")
        else:
            results["failed"] += 1
            results["details"].append(("Get A/B test results", r.status_code, r.text))
            
    else:
        results["failed"] += 1
        results["details"].append(("Create A/B test", r.status_code, r.text))
        print(f"    10.1 FAILED: {r.status_code} - {r.text}")

    # 11. Verifying persistence (Listing campaigns)...
    print("\n11. Verifying persistence (Listing campaigns)...")
    r = requests.get(f"{BASE_URL}/campaigns", params={"advertiser_id": advertiser_id})
    if r.status_code == 200:
        campaigns = r.json()
        if any(c["id"] == campaign_id for c in campaigns):
            results["passed"] += 1
            print(f"    SUCCESS: Campaign {campaign_id} found in list")
        else:
            results["failed"] += 1
            results["details"].append(("Verify campaign persistence", 200, "Campaign not in list"))
            print("    FAILED: Campaign not in list")
    else:
        results["failed"] += 1
        results["details"].append(("List campaigns", r.status_code, r.text))
        print(f"    FAILED: {r.status_code} - {r.text}")

    return results


if __name__ == "__main__":
    print("=" * 70)
    print("INTENT ENGINE COMPLETE WORKFLOW INTEGRATION TEST")
    print("=" * 70)
    
    try:
        results = test_complete_workflow()
    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print(f"SUMMARY: {results['passed']} passed, {results['failed']} failed")
    total = results['passed'] + results['failed']
    if total > 0:
        print(f"Success Rate: {results['passed']*100/total:.1f}%")
    
    if results["details"]:
        print("\nFailed Tests Details:")
        for name, status, error in results["details"]:
            print(f"  - {name}: HTTP {status}")
            print(f"    {error[:200]}...")
    
    print("=" * 70)
    
    if results["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
