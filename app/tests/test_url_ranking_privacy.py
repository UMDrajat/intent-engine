#!/usr/bin/env python3
"""
Test suite for URL ranking privacy logic in Intent Engine.
Verifies that privacy-friendly domains get higher scores and big-tech domains get lower scores.
"""

import unittest
from app.ranking.optimized_url_ranker import PrivacyDatabase

class TestURLRankingPrivacy(unittest.TestCase):
    
    def test_privacy_scores(self):
        """Test privacy scores for known domains"""
        # Privacy-friendly domains should be >= 0.9
        self.assertGreaterEqual(PrivacyDatabase.get_privacy_score("protonmail.com"), 0.9)
        self.assertGreaterEqual(PrivacyDatabase.get_privacy_score("duckduckgo.com"), 0.9)
        self.assertGreaterEqual(PrivacyDatabase.get_privacy_score("mullvad.net"), 0.9)
        
        # Big Tech domains should be <= 0.3
        self.assertLessEqual(PrivacyDatabase.get_privacy_score("google.com"), 0.3)
        self.assertLessEqual(PrivacyDatabase.get_privacy_score("facebook.com"), 0.3)
        self.assertLessEqual(PrivacyDatabase.get_privacy_score("microsoft.com"), 0.3)
        
        # Subdomains should also be categorized correctly
        self.assertLessEqual(PrivacyDatabase.get_privacy_score("mail.google.com"), 0.3)
        self.assertGreaterEqual(PrivacyDatabase.get_privacy_score("api.protonvpn.com"), 0.9)
        
        # Unknown domains should be 0.5
        self.assertEqual(PrivacyDatabase.get_privacy_score("some-random-new-domain.com"), 0.5)

    def test_big_tech_check(self):
        """Test the is_big_tech classification"""
        self.assertTrue(PrivacyDatabase.is_big_tech("google.com"))
        self.assertTrue(PrivacyDatabase.is_big_tech("youtube.com"))
        self.assertTrue(PrivacyDatabase.is_big_tech("facebook.com"))
        self.assertTrue(PrivacyDatabase.is_big_tech("office.com"))
        
        self.assertFalse(PrivacyDatabase.is_big_tech("proton.me"))
        self.assertFalse(PrivacyDatabase.is_big_tech("mozilla.org"))
        self.assertFalse(PrivacyDatabase.is_big_tech("wikipedia.org"))

    def test_tracker_count(self):
        """Test tracker count detection"""
        self.assertGreater(PrivacyDatabase.count_trackers("google-analytics.com"), 0)
        self.assertGreater(PrivacyDatabase.count_trackers("facebook.net"), 0)
        self.assertEqual(PrivacyDatabase.count_trackers("protonmail.com"), 0)

if __name__ == "__main__":
    unittest.main()
