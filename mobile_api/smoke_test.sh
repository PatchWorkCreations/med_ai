#!/bin/bash
# Mobile API Smoke Test Script
# Usage: ./smoke_test.sh [base_url]
# Example: ./smoke_test.sh http://localhost:8000

BASE_URL=${1:-http://localhost:8000}
API_BASE="$BASE_URL/api/v1/mobile"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Helper function to print test results
print_test() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $2"
        ((FAILED++))
    fi
}

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Mobile API Smoke Tests${NC}"
echo -e "${BLUE}Base URL: $BASE_URL${NC}"
echo -e "${BLUE}======================================${NC}\n"

# Test 1: Health Check
echo -e "${BLUE}[1/6] Testing Health Endpoint...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE/health/")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_test 0 "Health endpoint responded with 200"
    echo "   Response: $BODY"
else
    print_test 1 "Health endpoint failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 2: Sign Up
echo -e "${BLUE}[2/6] Testing Sign Up...${NC}"
TIMESTAMP=$(date +%s)
TEST_EMAIL="test_$TIMESTAMP@example.com"
TEST_PASSWORD="TestPass123!"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/signup/" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"first_name\":\"Test\",\"last_name\":\"User\"}")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    print_test 0 "Sign up successful"
    TOKEN=$(echo "$BODY" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    echo "   Token: ${TOKEN:0:20}..."
else
    print_test 1 "Sign up failed (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
fi
echo ""

# Test 3: Login
echo -e "${BLUE}[3/6] Testing Login...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/login/" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_test 0 "Login successful"
    TOKEN=$(echo "$BODY" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    echo "   Using token for authenticated tests"
else
    print_test 1 "Login failed (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
fi
echo ""

# Test 4: Auth Status (Authenticated)
echo -e "${BLUE}[4/6] Testing Auth Status...${NC}"
if [ -n "$TOKEN" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE/auth/status/" \
        -H "Authorization: Token $TOKEN")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_test 0 "Auth status check successful"
    else
        print_test 1 "Auth status check failed (HTTP $HTTP_CODE)"
    fi
else
    print_test 1 "Skipped - no token available"
fi
echo ""

# Test 5: Send Chat (Authenticated)
echo -e "${BLUE}[5/6] Testing Send Chat...${NC}"
if [ -n "$TOKEN" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/send-chat/" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"message":"Hello, this is a test!","session_id":"test_session"}')
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_test 0 "Send chat successful"
        echo "   Response preview: ${BODY:0:100}..."
    else
        print_test 1 "Send chat failed (HTTP $HTTP_CODE)"
    fi
else
    print_test 1 "Skipped - no token available"
fi
echo ""

# Test 6: Summarize (Authenticated)
echo -e "${BLUE}[6/6] Testing Summarize...${NC}"
if [ -n "$TOKEN" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/summarize/" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"text":"This is a long text that needs to be summarized. It contains multiple sentences and should be truncated to 200 characters or less in the response."}')
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        print_test 0 "Summarize successful"
        echo "   Response: $BODY"
    else
        print_test 1 "Summarize failed (HTTP $HTTP_CODE)"
    fi
else
    print_test 1 "Skipped - no token available"
fi
echo ""

# Summary
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi

