#!/bin/bash
# Test upload to Cloud Run backend from mobile app perspective

set -e

API_URL="${EXPO_PUBLIC_API_URL:-https://pegasus-api-988514135894.us-central1.run.app}"

echo "🧪 Testing Pegasus Mobile Upload Flow"
echo "API URL: $API_URL"
echo ""

# 1. Test health check
echo "1️⃣ Testing health endpoint..."
HEALTH=$(curl -s "$API_URL/health")
echo "✅ Health: $HEALTH"
echo ""

# 2. Test presets endpoint
echo "2️⃣ Testing presets endpoint..."
PRESETS=$(curl -s "$API_URL/presets" | jq -r '.presets | length')
echo "✅ Found $PRESETS presets"
echo ""

# 3. Test courses endpoint
echo "3️⃣ Testing courses endpoint..."
COURSES=$(curl -s "$API_URL/courses" | jq -r '.courses | length')
echo "✅ Found $COURSES courses"
echo ""

# 4. Create a test audio file
echo "4️⃣ Creating test audio file..."
TEST_FILE="/tmp/test-lecture-$(date +%s).m4a"
# Create a small silent audio file (1 second of silence)
ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 1 -c:a aac "$TEST_FILE" -y >/dev/null 2>&1 || {
    echo "⚠️  ffmpeg not available, creating dummy file"
    echo "dummy audio data" > "$TEST_FILE"
}
echo "✅ Created test file: $TEST_FILE ($(stat -f%z "$TEST_FILE" 2>/dev/null || stat -c%s "$TEST_FILE") bytes)"
echo ""

# 5. Test upload
echo "5️⃣ Testing lecture upload..."
LECTURE_ID="test-lecture-$(date +%s)"
COURSE_ID="test-course-123"

RESPONSE=$(curl -s -X POST "$API_URL/lectures/ingest" \
  -F "audio=@$TEST_FILE;type=audio/m4a" \
  -F "course_id=$COURSE_ID" \
  -F "lecture_id=$LECTURE_ID" \
  -F "title=Test Lecture Upload" \
  -F "preset_id=beginner-mode" \
  -F "lecture_mode=audio" \
  -F "auto_transcribe=false")

if echo "$RESPONSE" | jq -e '.lectureId' >/dev/null 2>&1; then
    echo "✅ Upload successful!"
    echo "$RESPONSE" | jq .
else
    echo "❌ Upload failed!"
    echo "Response: $RESPONSE"
    exit 1
fi

echo ""
echo "6️⃣ Cleaning up test file..."
rm -f "$TEST_FILE"
echo "✅ Cleanup complete"

echo ""
echo "🎉 All tests passed! Mobile upload should work."
echo ""
echo "📱 Next steps:"
echo "1. Restart Expo: npx expo start --clear"
echo "2. Make sure mobile/.env has EXPO_PUBLIC_API_URL set"
echo "3. Try uploading from the mobile app"
