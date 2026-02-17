#!/usr/bin/env node
// Debug script to check mobile app API connection
// Run with: node debug-connection.js

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'https://pegasus-api-ui64fwvjyq-uc.a.run.app';

console.log('🔍 Debugging Mobile App API Connection\n');
console.log(`API URL from env: ${process.env.EXPO_PUBLIC_API_URL || '(not set)'}`);
console.log(`Using URL: ${API_URL}\n`);

async function testEndpoint(endpoint, description) {
    try {
        console.log(`Testing ${description}...`);
        const response = await fetch(`${API_URL}${endpoint}`);

        if (!response.ok) {
            console.log(`  ❌ HTTP ${response.status}: ${response.statusText}`);
            const text = await response.text();
            console.log(`  Response: ${text.substring(0, 200)}\n`);
            return false;
        }

        const data = await response.json();
        console.log(`  ✅ Success`);
        console.log(`  Response: ${JSON.stringify(data, null, 2).substring(0, 200)}...\n`);
        return true;
    } catch (error) {
        console.log(`  ❌ Error: ${error.message}`);
        console.log(`  Type: ${error.constructor.name}\n`);
        return false;
    }
}

async function runDiagnostics() {
    console.log('═══════════════════════════════════════════\n');

    const results = {
        health: await testEndpoint('/health', 'Health Check'),
        presets: await testEndpoint('/presets', 'Presets'),
        courses: await testEndpoint('/courses', 'Courses'),
        lectures: await testEndpoint('/lectures?limit=10&offset=0', 'Lectures'),
    };

    console.log('═══════════════════════════════════════════\n');
    console.log('Summary:');
    Object.entries(results).forEach(([name, success]) => {
        console.log(`  ${success ? '✅' : '❌'} ${name}`);
    });

    const allPassed = Object.values(results).every(r => r);

    if (allPassed) {
        console.log('\n🎉 All endpoints working!');
        console.log('\nIf mobile app still fails, try:');
        console.log('1. Kill Expo completely: killall -9 node');
        console.log('2. Clear cache: npx expo start --clear');
        console.log('3. Check device/simulator can reach the URL');
        console.log('4. If on physical device, ensure WiFi connected');
    } else {
        console.log('\n❌ Some endpoints failed!');
        console.log('\nTroubleshooting:');
        console.log('1. Check backend is deployed: gcloud run services describe pegasus-api --region=us-central1');
        console.log('2. Check database connection');
        console.log('3. Review Cloud Run logs for errors');
    }
}

runDiagnostics().catch(console.error);
