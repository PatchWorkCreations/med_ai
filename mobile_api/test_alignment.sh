#!/bin/bash

echo "🧪 Testing Frontend-Backend Alignment"
echo "======================================"
echo ""

BASE_URL="http://localhost:8000"

# Test 1: Health check
echo "1️⃣ Testing health check..."
STATUS=$(curl -s "$BASE_URL/api/auth/status/" | grep -o '"status":"ok"')
if [ "$STATUS" == '"status":"ok"' ]; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

# Test 2: Sign up
echo ""
echo "2️⃣ Testing sign up..."
TIMESTAMP=$(date +%s)
SIGNUP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/signup/" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test User\",\"email\":\"test$TIMESTAMP@example.com\",\"password\":\"TestPass123!\"}")

TOKEN=$(echo "$SIGNUP_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
if [ -n "$TOKEN" ]; then
    echo "✅ Sign up passed"
    echo "   Token: $TOKEN"
else
    echo "❌ Sign up failed"
    echo "   Response: $SIGNUP_RESPONSE"
    exit 1
fi

# Test 3: Get user settings
echo ""
echo "3️⃣ Testing get user settings..."
SETTINGS=$(curl -s "$BASE_URL/api/user/settings/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN")

EMAIL=$(echo "$SETTINGS" | grep -o "test$TIMESTAMP@example.com")
if [ -n "$EMAIL" ]; then
    echo "✅ Get user settings passed"
else
    echo "❌ Get user settings failed"
    echo "   Response: $SETTINGS"
fi

# Test 4: Send chat message (THE CRITICAL ONE!)
echo ""
echo "4️⃣ Testing send chat message..."
CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/send-chat/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"message":"Hello, test message"}')

CHAT_CONTENT=$(echo "$CHAT_RESPONSE" | grep -o '"content"')
if [ -n "$CHAT_CONTENT" ]; then
    echo "✅ Send chat message passed"
    echo "   Response: $CHAT_RESPONSE"
else
    echo "❌ Send chat message failed"
    echo "   Response: $CHAT_RESPONSE"
fi

# Test 5: Create chat session
echo ""
echo "5️⃣ Testing create chat session..."
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/api/chat/sessions/new/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $TOKEN" \
  -d '{"title":"Test Session","tone":"plain"}')

SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$SESSION_ID" ]; then
    echo "✅ Create chat session passed"
    echo "   Session ID: $SESSION_ID"
else
    echo "❌ Create chat session failed"
    echo "   Response: $SESSION_RESPONSE"
fi

echo ""
echo "======================================"
echo "🎉 All alignment tests completed!"

