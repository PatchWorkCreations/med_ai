#!/bin/bash
# Frontend Compatibility Test Script
# Tests endpoints matching iOS frontend expectations

BASE_URL=${1:-http://localhost:8000}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

print_test() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $2"
        ((FAILED++))
    fi
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Frontend Compatibility Tests${NC}"
echo -e "${BLUE}Testing iOS APIService.swift endpoints${NC}"
echo -e "${BLUE}Base URL: $BASE_URL${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 1: Auth Status (Health Check)
echo -e "${BLUE}[1/7] Testing /api/auth/status/${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/auth/status/")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_test 0 "Auth status endpoint (GET /api/auth/status/)"
    echo "   Response: ${BODY:0:80}..."
else
    print_test 1 "Auth status endpoint failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 2: Sign Up
echo -e "${BLUE}[2/7] Testing /api/signup/${NC}"
TIMESTAMP=$(date +%s)
TEST_EMAIL="ios_test_$TIMESTAMP@example.com"
TEST_PASSWORD="TestPass123!"
TEST_NAME="iOS TestUser"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/signup/" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$TEST_NAME\",\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"language\":\"en-US\"}")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    print_test 0 "Sign up endpoint (POST /api/signup/)"
    TOKEN=$(echo "$BODY" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    echo "   Token: ${TOKEN:0:20}..."
    echo "   Email: $TEST_EMAIL"
else
    print_test 1 "Sign up failed (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
fi
echo ""

# Test 3: Login
echo -e "${BLUE}[3/7] Testing /api/login/${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/login/" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_test 0 "Login endpoint (POST /api/login/)"
    TOKEN=$(echo "$BODY" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    echo "   Token refreshed: ${TOKEN:0:20}..."
else
    print_test 1 "Login failed (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
fi
echo ""

# Test 4: Get User Settings
echo -e "${BLUE}[4/7] Testing /api/user/settings/${NC}"
if [ -n "$TOKEN" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/user/settings/" \
        -H "Authorization: Token $TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_test 0 "Get user settings (GET /api/user/settings/)"
        echo "   Response: ${BODY:0:100}..."
    else
        print_test 1 "Get user settings failed (HTTP $HTTP_CODE)"
    fi
else
    print_test 1 "Skipped - no token available"
fi
echo ""

# Test 5: Update User Settings
echo -e "${BLUE}[5/7] Testing /api/user/settings/update/${NC}"
if [ -n "$TOKEN" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/user/settings/update/" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"first_name":"UpdatedFirst","last_name":"UpdatedLast"}')
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_test 0 "Update user settings (POST /api/user/settings/update/)"
    else
        print_test 1 "Update user settings failed (HTTP $HTTP_CODE)"
    fi
else
    print_test 1 "Skipped - no token available"
fi
echo ""

# Test 6: Chat Sessions
echo -e "${BLUE}[6/7] Testing /api/chat/sessions/${NC}"
if [ -n "$TOKEN" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/chat/sessions/" \
        -H "Authorization: Token $TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_test 0 "Get chat sessions (GET /api/chat/sessions/)"
        echo "   Response: ${BODY:0:80}..."
    else
        print_test 1 "Get chat sessions failed (HTTP $HTTP_CODE)"
    fi
else
    print_test 1 "Skipped - no token available"
fi
echo ""

# Test 7: Send Chat Message
echo -e "${BLUE}[7/7] Testing /api/send-chat/${NC}"
if [ -n "$TOKEN" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/send-chat/" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"message":"Hello from iOS test!","session_id":"test123"}')
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_test 0 "Send chat message (POST /api/send-chat/)"
        echo "   Response: ${BODY:0:100}..."
    else
        print_test 1 "Send chat message failed (HTTP $HTTP_CODE)"
    fi
else
    print_test 1 "Skipped - no token available"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ All frontend compatibility tests passed!${NC}"
    echo -e "${YELLOW}Note: Some endpoints return stub data. Connect them to your existing logic.${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed. Check the output above.${NC}"
    exit 1
fi

