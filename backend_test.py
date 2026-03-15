#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for PlayRank
Tests all authentication, user management, group management, match tracking,
leaderboard, and activity feed endpoints.
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configuration - Use timestamp to ensure unique test data
TIMESTAMP = str(int(time.time()))
BASE_URL = "https://score-social.preview.emergentagent.com/api"
TEST_EMAIL_1 = f"alice.player.{TIMESTAMP}@example.com"
TEST_EMAIL_2 = f"bob.gamer.{TIMESTAMP}@example.com"
TEST_USERNAME_1 = f"alice_player_{TIMESTAMP[-6:]}"
TEST_USERNAME_2 = f"bob_gamer_{TIMESTAMP[-6:]}"
TEST_PASSWORD = "TestPass123!"

class PlayRankTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.token_1 = None
        self.token_2 = None
        self.user_1 = None
        self.user_2 = None
        self.group_id = None
        self.game_type_id = None
        self.match_id = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log test progress"""
        print(f"[{level}] {message}")
    
    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    headers: Optional[Dict] = None, token: Optional[str] = None) -> requests.Response:
        """Make HTTP request with optional authentication"""
        url = f"{self.base_url}{endpoint}"
        request_headers = headers or {}
        
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        
        if method.upper() == "GET":
            response = self.session.get(url, headers=request_headers)
        elif method.upper() == "POST":
            response = self.session.post(url, json=data, headers=request_headers)
        elif method.upper() == "PUT":
            response = self.session.put(url, json=data, headers=request_headers)
        elif method.upper() == "DELETE":
            response = self.session.delete(url, headers=request_headers)
        
        return response

    def test_auth_register(self) -> bool:
        """Test user registration endpoints"""
        self.log("Testing user registration...")
        
        # Test 1: Valid registration - User 1
        try:
            data = {
                "email": TEST_EMAIL_1,
                "password": TEST_PASSWORD,
                "username": TEST_USERNAME_1
            }
            response = self.make_request("POST", "/auth/register", data)
            
            if response.status_code == 200:
                result = response.json()
                if "access_token" in result and "user" in result:
                    self.token_1 = result["access_token"]
                    self.user_1 = result["user"]
                    self.log(f"✅ User 1 registration successful: {self.user_1['username']}")
                else:
                    self.log("❌ Registration response missing required fields", "ERROR")
                    return False
            else:
                self.log(f"❌ Registration failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Registration error: {str(e)}", "ERROR")
            return False
        
        # Test 2: Valid registration - User 2
        try:
            data = {
                "email": TEST_EMAIL_2,
                "password": TEST_PASSWORD,
                "username": TEST_USERNAME_2
            }
            response = self.make_request("POST", "/auth/register", data)
            
            if response.status_code == 200:
                result = response.json()
                self.token_2 = result["access_token"]
                self.user_2 = result["user"]
                self.log(f"✅ User 2 registration successful: {self.user_2['username']}")
            else:
                self.log(f"❌ Second registration failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Second registration error: {str(e)}", "ERROR")
            return False
            
        # Test 3: Duplicate email registration (should fail)
        try:
            data = {
                "email": TEST_EMAIL_1,
                "password": TEST_PASSWORD,
                "username": "different_username"
            }
            response = self.make_request("POST", "/auth/register", data)
            
            if response.status_code == 400:
                self.log("✅ Duplicate email registration properly rejected")
            else:
                self.log(f"❌ Duplicate email should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Duplicate email test error: {str(e)}", "ERROR")
            return False
            
        # Test 4: Duplicate username registration (should fail)
        try:
            data = {
                "email": "different@email.com",
                "password": TEST_PASSWORD,
                "username": TEST_USERNAME_1
            }
            response = self.make_request("POST", "/auth/register", data)
            
            if response.status_code == 400:
                self.log("✅ Duplicate username registration properly rejected")
            else:
                self.log(f"❌ Duplicate username should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Duplicate username test error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_auth_login(self) -> bool:
        """Test user login endpoints"""
        self.log("Testing user login...")
        
        # Test 1: Valid login
        try:
            data = {
                "email": TEST_EMAIL_1,
                "password": TEST_PASSWORD
            }
            response = self.make_request("POST", "/auth/login", data)
            
            if response.status_code == 200:
                result = response.json()
                if "access_token" in result and "user" in result:
                    self.log("✅ Valid login successful")
                else:
                    self.log("❌ Login response missing required fields", "ERROR")
                    return False
            else:
                self.log(f"❌ Valid login failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Login error: {str(e)}", "ERROR")
            return False
            
        # Test 2: Invalid password (should fail)
        try:
            data = {
                "email": TEST_EMAIL_1,
                "password": "wrongpassword"
            }
            response = self.make_request("POST", "/auth/login", data)
            
            if response.status_code == 401:
                self.log("✅ Invalid password properly rejected")
            else:
                self.log(f"❌ Invalid password should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Invalid password test error: {str(e)}", "ERROR")
            return False
            
        # Test 3: Invalid email (should fail)
        try:
            data = {
                "email": "nonexistent@email.com",
                "password": TEST_PASSWORD
            }
            response = self.make_request("POST", "/auth/login", data)
            
            if response.status_code == 401:
                self.log("✅ Invalid email properly rejected")
            else:
                self.log(f"❌ Invalid email should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Invalid email test error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_auth_me(self) -> bool:
        """Test get current user endpoint"""
        self.log("Testing get current user...")
        
        # Test 1: Valid token
        try:
            response = self.make_request("GET", "/auth/me", token=self.token_1)
            
            if response.status_code == 200:
                user_data = response.json()
                if user_data["username"] == TEST_USERNAME_1:
                    self.log("✅ Get current user successful")
                else:
                    self.log("❌ User data mismatch", "ERROR")
                    return False
            else:
                self.log(f"❌ Get current user failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get current user error: {str(e)}", "ERROR")
            return False
            
        # Test 2: No token (should fail)
        try:
            response = self.make_request("GET", "/auth/me")
            
            if response.status_code == 403:
                self.log("✅ No token properly rejected")
            else:
                self.log(f"❌ No token should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ No token test error: {str(e)}", "ERROR")
            return False
            
        # Test 3: Invalid token (should fail)
        try:
            response = self.make_request("GET", "/auth/me", token="invalid_token")
            
            if response.status_code in [401, 403]:
                self.log("✅ Invalid token properly rejected")
            else:
                self.log(f"❌ Invalid token should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Invalid token test error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_user_profile_update(self) -> bool:
        """Test user profile update endpoint"""
        self.log("Testing user profile update...")
        
        # Test 1: Valid profile update
        try:
            data = {
                "bio": "Love competitive gaming!",
                "favorite_games": ["Chess", "Poker"],
                "external_accounts": {
                    "steam": "alice_steam",
                    "discord": "alice#1234"
                }
            }
            response = self.make_request("PUT", "/users/profile", data, token=self.token_1)
            
            if response.status_code == 200:
                result = response.json()
                if result["bio"] == data["bio"] and result["favorite_games"] == data["favorite_games"]:
                    self.log("✅ Profile update successful")
                else:
                    self.log("❌ Profile update data mismatch", "ERROR")
                    return False
            else:
                self.log(f"❌ Profile update failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Profile update error: {str(e)}", "ERROR")
            return False
            
        # Test 2: Username update with duplicate (should fail)
        try:
            data = {
                "username": TEST_USERNAME_2  # Should conflict with user 2
            }
            response = self.make_request("PUT", "/users/profile", data, token=self.token_1)
            
            if response.status_code == 400:
                self.log("✅ Duplicate username update properly rejected")
            else:
                self.log(f"❌ Duplicate username should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Duplicate username test error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_get_user(self) -> bool:
        """Test get other user endpoint"""
        self.log("Testing get user...")
        
        # Test 1: Valid user ID
        try:
            response = self.make_request("GET", f"/users/{self.user_2['id']}", token=self.token_1)
            
            if response.status_code == 200:
                user_data = response.json()
                if user_data["username"] == TEST_USERNAME_2:
                    self.log("✅ Get user successful")
                else:
                    self.log("❌ Get user data mismatch", "ERROR")
                    return False
            else:
                self.log(f"❌ Get user failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get user error: {str(e)}", "ERROR")
            return False
            
        # Test 2: Invalid user ID (should fail)
        try:
            response = self.make_request("GET", "/users/invalid_user_id", token=self.token_1)
            
            if response.status_code in [400, 404, 500]:
                self.log("✅ Invalid user ID properly handled")
            else:
                self.log(f"❌ Invalid user ID should be handled, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Invalid user ID test error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_group_create(self) -> bool:
        """Test group creation endpoint"""
        self.log("Testing group creation...")
        
        # Test 1: Valid group creation
        try:
            data = {
                "name": "Chess Masters",
                "icon": "♟️",
                "description": "For chess enthusiasts and competitive players"
            }
            response = self.make_request("POST", "/groups", data, token=self.token_1)
            
            if response.status_code == 200:
                result = response.json()
                if result["name"] == data["name"] and result["owner_id"] == self.user_1["id"]:
                    self.group_id = result["id"]
                    self.log(f"✅ Group creation successful: {result['name']}")
                else:
                    self.log("❌ Group creation data mismatch", "ERROR")
                    return False
            else:
                self.log(f"❌ Group creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Group creation error: {str(e)}", "ERROR")
            return False
            
        # Test 2: No authentication (should fail)
        try:
            data = {
                "name": "Unauthorized Group",
                "description": "This should fail"
            }
            response = self.make_request("POST", "/groups", data)
            
            if response.status_code == 403:
                self.log("✅ Unauthorized group creation properly rejected")
            else:
                self.log(f"❌ Unauthorized creation should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Unauthorized creation test error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_group_get_all(self) -> bool:
        """Test get all user groups endpoint"""
        self.log("Testing get all user groups...")
        
        try:
            response = self.make_request("GET", "/groups", token=self.token_1)
            
            if response.status_code == 200:
                groups = response.json()
                if len(groups) >= 1:
                    found_group = any(g["id"] == self.group_id for g in groups)
                    if found_group:
                        self.log("✅ Get all groups successful")
                    else:
                        self.log("❌ Created group not found in list", "ERROR")
                        return False
                else:
                    self.log("❌ No groups returned", "ERROR")
                    return False
            else:
                self.log(f"❌ Get all groups failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get all groups error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_group_get_specific(self) -> bool:
        """Test get specific group endpoint"""
        self.log("Testing get specific group...")
        
        # Test 1: Valid group access by member
        try:
            response = self.make_request("GET", f"/groups/{self.group_id}", token=self.token_1)
            
            if response.status_code == 200:
                group_data = response.json()
                if group_data["id"] == self.group_id:
                    self.log("✅ Get specific group successful")
                else:
                    self.log("❌ Group data mismatch", "ERROR")
                    return False
            else:
                self.log(f"❌ Get specific group failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get specific group error: {str(e)}", "ERROR")
            return False
            
        # Test 2: Access by non-member (should fail)
        try:
            response = self.make_request("GET", f"/groups/{self.group_id}", token=self.token_2)
            
            if response.status_code == 403:
                self.log("✅ Non-member access properly rejected")
            else:
                self.log(f"❌ Non-member access should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Non-member access test error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_group_update(self) -> bool:
        """Test group update endpoint"""
        self.log("Testing group update...")
        
        # Test 1: Valid update by owner
        try:
            data = {
                "description": "Updated: Premium chess training group"
            }
            response = self.make_request("PUT", f"/groups/{self.group_id}", data, token=self.token_1)
            
            if response.status_code == 200:
                result = response.json()
                if result["description"] == data["description"]:
                    self.log("✅ Group update successful")
                else:
                    self.log("❌ Group update data mismatch", "ERROR")
                    return False
            else:
                self.log(f"❌ Group update failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Group update error: {str(e)}", "ERROR")
            return False
            
        # Test 2: Update by non-owner (should fail)
        try:
            data = {
                "name": "Hijacked Group"
            }
            response = self.make_request("PUT", f"/groups/{self.group_id}", data, token=self.token_2)
            
            if response.status_code == 403:
                self.log("✅ Non-owner update properly rejected")
            else:
                self.log(f"❌ Non-owner update should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Non-owner update test error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_group_join(self) -> bool:
        """Test group join endpoint"""
        self.log("Testing group join...")
        
        # Test 1: Valid join
        try:
            response = self.make_request("POST", f"/groups/{self.group_id}/join", token=self.token_2)
            
            if response.status_code == 200:
                result = response.json()
                if "message" in result:
                    self.log("✅ Group join successful")
                else:
                    self.log("❌ Join response missing message", "ERROR")
                    return False
            else:
                self.log(f"❌ Group join failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Group join error: {str(e)}", "ERROR")
            return False
            
        # Test 2: Join again (should fail)
        try:
            response = self.make_request("POST", f"/groups/{self.group_id}/join", token=self.token_2)
            
            if response.status_code == 400:
                self.log("✅ Duplicate join properly rejected")
            else:
                self.log(f"❌ Duplicate join should be rejected, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Duplicate join test error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_group_members(self) -> bool:
        """Test get group members endpoint"""
        self.log("Testing get group members...")
        
        try:
            response = self.make_request("GET", f"/groups/{self.group_id}/members", token=self.token_1)
            
            if response.status_code == 200:
                members = response.json()
                if len(members) == 2:  # Both users should be members now
                    member_usernames = [m["username"] for m in members]
                    if TEST_USERNAME_1 in member_usernames and TEST_USERNAME_2 in member_usernames:
                        self.log("✅ Get group members successful")
                    else:
                        self.log("❌ Member list incomplete", "ERROR")
                        return False
                else:
                    self.log(f"❌ Expected 2 members, got {len(members)}", "ERROR")
                    return False
            else:
                self.log(f"❌ Get group members failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get group members error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_game_types(self) -> bool:
        """Test game type creation and retrieval"""
        self.log("Testing game types...")
        
        # Test 1: Create game type
        try:
            data = {
                "name": "Classical Chess",
                "icon": "♛"
            }
            response = self.make_request("POST", f"/groups/{self.group_id}/game-types", data, token=self.token_1)
            
            if response.status_code == 200:
                result = response.json()
                if result["name"] == data["name"] and result["group_id"] == self.group_id:
                    self.game_type_id = result["id"]
                    self.log("✅ Game type creation successful")
                else:
                    self.log("❌ Game type creation data mismatch", "ERROR")
                    return False
            else:
                self.log(f"❌ Game type creation failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Game type creation error: {str(e)}", "ERROR")
            return False
            
        # Test 2: Get game types
        try:
            response = self.make_request("GET", f"/groups/{self.group_id}/game-types", token=self.token_1)
            
            if response.status_code == 200:
                game_types = response.json()
                if len(game_types) >= 1:
                    found_type = any(gt["id"] == self.game_type_id for gt in game_types)
                    if found_type:
                        self.log("✅ Get game types successful")
                    else:
                        self.log("❌ Created game type not found", "ERROR")
                        return False
                else:
                    self.log("❌ No game types returned", "ERROR")
                    return False
            else:
                self.log(f"❌ Get game types failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get game types error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_matches(self) -> bool:
        """Test match creation and retrieval"""
        self.log("Testing matches...")
        
        # Test 1: Create match
        try:
            data = {
                "game_type_id": self.game_type_id,
                "group_id": self.group_id,
                "date": datetime.utcnow().isoformat(),
                "players": [self.user_1["id"], self.user_2["id"]],
                "winner_ids": [self.user_1["id"]],
                "score": "1-0",
                "notes": "Great match!"
            }
            response = self.make_request("POST", "/matches", data, token=self.token_1)
            
            if response.status_code == 200:
                result = response.json()
                if (result["game_type_id"] == data["game_type_id"] and 
                    result["group_id"] == data["group_id"] and
                    result["winner_ids"] == data["winner_ids"]):
                    self.match_id = result["id"]
                    self.log("✅ Match creation successful")
                else:
                    self.log("❌ Match creation data mismatch", "ERROR")
                    return False
            else:
                self.log(f"❌ Match creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Match creation error: {str(e)}", "ERROR")
            return False
            
        # Test 2: Get group matches
        try:
            response = self.make_request("GET", f"/groups/{self.group_id}/matches", token=self.token_1)
            
            if response.status_code == 200:
                matches = response.json()
                if len(matches) >= 1:
                    found_match = any(m["id"] == self.match_id for m in matches)
                    if found_match:
                        self.log("✅ Get group matches successful")
                    else:
                        self.log("❌ Created match not found", "ERROR")
                        return False
                else:
                    self.log("❌ No matches returned", "ERROR")
                    return False
            else:
                self.log(f"❌ Get group matches failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get group matches error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_leaderboard(self) -> bool:
        """Test leaderboard endpoint"""
        self.log("Testing leaderboard...")
        
        try:
            response = self.make_request("GET", f"/groups/{self.group_id}/leaderboard", token=self.token_1)
            
            if response.status_code == 200:
                leaderboard = response.json()
                if len(leaderboard) >= 1:
                    # Check if user stats are calculated correctly
                    user_1_stats = next((entry for entry in leaderboard if entry["user_id"] == self.user_1["id"]), None)
                    if user_1_stats and user_1_stats["wins"] >= 1:
                        self.log("✅ Get leaderboard successful")
                    else:
                        self.log("❌ Leaderboard stats incorrect", "ERROR")
                        return False
                else:
                    self.log("❌ Empty leaderboard", "ERROR")
                    return False
            else:
                self.log(f"❌ Get leaderboard failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get leaderboard error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_user_stats(self) -> bool:
        """Test user stats endpoint"""
        self.log("Testing user stats...")
        
        try:
            response = self.make_request("GET", f"/groups/{self.group_id}/stats/{self.user_1['id']}", token=self.token_1)
            
            if response.status_code == 200:
                stats = response.json()
                if (stats["user_id"] == self.user_1["id"] and 
                    stats["group_id"] == self.group_id and
                    stats["total_matches"] >= 1):
                    self.log("✅ Get user stats successful")
                else:
                    self.log("❌ User stats data incorrect", "ERROR")
                    return False
            else:
                self.log(f"❌ Get user stats failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get user stats error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_activities(self) -> bool:
        """Test activity feed endpoint"""
        self.log("Testing activity feed...")
        
        try:
            response = self.make_request("GET", f"/groups/{self.group_id}/activities", token=self.token_1)
            
            if response.status_code == 200:
                activities = response.json()
                if len(activities) >= 1:
                    # Should have activities for group creation, member join, match creation
                    activity_types = [a["activity_type"] for a in activities]
                    expected_types = ["group_created", "member_joined", "match_added"]
                    if any(t in activity_types for t in expected_types):
                        self.log("✅ Get activities successful")
                    else:
                        self.log("❌ Expected activities not found", "ERROR")
                        return False
                else:
                    self.log("❌ No activities returned", "ERROR")
                    return False
            else:
                self.log(f"❌ Get activities failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get activities error: {str(e)}", "ERROR")
            return False
            
        return True

    def test_messages(self) -> bool:
        """Test messages endpoint"""
        self.log("Testing messages...")
        
        try:
            response = self.make_request("GET", f"/groups/{self.group_id}/messages", token=self.token_1)
            
            if response.status_code == 200:
                messages = response.json()
                # Messages list can be empty initially, just check the endpoint works
                self.log("✅ Get messages successful")
            else:
                self.log(f"❌ Get messages failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get messages error: {str(e)}", "ERROR")
            return False
            
        return True

    def run_all_tests(self) -> bool:
        """Run all test suites"""
        self.log("=" * 50)
        self.log("Starting PlayRank Backend API Tests")
        self.log("=" * 50)
        
        test_results = []
        
        # Authentication Tests
        test_results.append(("Auth Registration", self.test_auth_register()))
        test_results.append(("Auth Login", self.test_auth_login()))
        test_results.append(("Auth Get Me", self.test_auth_me()))
        
        # User Profile Tests
        test_results.append(("User Profile Update", self.test_user_profile_update()))
        test_results.append(("Get User", self.test_get_user()))
        
        # Group Management Tests
        test_results.append(("Group Creation", self.test_group_create()))
        test_results.append(("Get All Groups", self.test_group_get_all()))
        test_results.append(("Get Specific Group", self.test_group_get_specific()))
        test_results.append(("Group Update", self.test_group_update()))
        test_results.append(("Group Join", self.test_group_join()))
        test_results.append(("Group Members", self.test_group_members()))
        
        # Game Types Tests
        test_results.append(("Game Types", self.test_game_types()))
        
        # Match Tracking Tests
        test_results.append(("Matches", self.test_matches()))
        
        # Leaderboard & Stats Tests
        test_results.append(("Leaderboard", self.test_leaderboard()))
        test_results.append(("User Stats", self.test_user_stats()))
        
        # Activity Feed Tests
        test_results.append(("Activities", self.test_activities()))
        
        # Message Tests
        test_results.append(("Messages", self.test_messages()))
        
        # Print results summary
        self.log("=" * 50)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 50)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "PASS" if result else "FAIL"
            self.log(f"{test_name}: {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        self.log("=" * 50)
        self.log(f"TOTAL: {passed} PASSED, {failed} FAILED")
        self.log("=" * 50)
        
        return failed == 0

if __name__ == "__main__":
    tester = PlayRankTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)