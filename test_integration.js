#!/usr/bin/env node
/**
 * Integration test for Electron POC
 * Tests the main process logic without GUI
 */

const { spawn } = require('child_process');
const path = require('path');
const crypto = require('crypto');

// 生成 token
function generateToken() {
  return crypto.randomBytes(32).toString('hex');
}

// 啟動 Flask 服務
function startPythonService(token) {
  return new Promise((resolve, reject) => {
    const pythonScript = path.join(__dirname, 'flask_service.py');
    
    console.log('🚀 Starting Flask service...');
    console.log('📝 Token (first 8 chars):', token.substring(0, 8) + '...');
    
    const pythonProcess = spawn('python3', [pythonScript], {
      env: { ...process.env, APP_TOKEN: token, PORT: '5000' },
      stdio: 'pipe'
    });
    
    pythonProcess.stdout.on('data', (data) => {
      console.log(`[Flask] ${data.toString().trim()}`);
    });
    
    pythonProcess.stderr.on('data', (data) => {
      console.error(`[Flask Error] ${data.toString().trim()}`);
    });
    
    pythonProcess.on('error', (error) => {
      console.error('❌ Failed to start Flask service:', error);
      reject(error);
    });
    
    pythonProcess.on('exit', (code) => {
      console.log(`Flask service exited with code ${code}`);
    });
    
    // 給服務一些時間啟動
    setTimeout(() => {
      resolve(pythonProcess);
    }, 3000);
  });
}

// 健康檢查
async function checkHealth() {
  console.log('\n🔍 Performing health check...');
  
  const maxRetries = 5;
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://127.0.0.1:5000/health');
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Health check passed:', JSON.stringify(data, null, 2));
        return true;
      }
    } catch (error) {
      console.log(`⏳ Attempt ${i + 1}/${maxRetries}: ${error.message}`);
    }
    
    if (i < maxRetries - 1) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  
  console.error('❌ Health check failed after all retries');
  return false;
}

// 測試 API ping（需要認證）
async function testPing(token) {
  console.log('\n🏓 Testing /api/ping with authentication...');
  
  try {
    const response = await fetch('http://127.0.0.1:5000/api/ping', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    
    if (response.ok) {
      console.log('✅ Ping test passed:', JSON.stringify(data, null, 2));
      return true;
    } else {
      console.error('❌ Ping test failed:', data);
      return false;
    }
  } catch (error) {
    console.error('❌ Ping test error:', error.message);
    return false;
  }
}

// 測試無效 token
async function testInvalidToken() {
  console.log('\n🔐 Testing /api/ping with invalid token...');
  
  try {
    const response = await fetch('http://127.0.0.1:5000/api/ping', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer invalid_token_123',
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    
    if (response.status === 401) {
      console.log('✅ Invalid token correctly rejected:', JSON.stringify(data, null, 2));
      return true;
    } else {
      console.error('❌ Invalid token should have been rejected');
      return false;
    }
  } catch (error) {
    console.error('❌ Invalid token test error:', error.message);
    return false;
  }
}

// 主測試流程
async function main() {
  console.log('🎮 Robot Command Console - Electron POC Integration Test\n');
  console.log('='.repeat(60));
  
  const token = generateToken();
  let pythonProcess = null;
  let allTestsPassed = true;
  
  try {
    // 啟動 Flask 服務
    pythonProcess = await startPythonService(token);
    
    // 健康檢查
    const healthOk = await checkHealth();
    if (!healthOk) {
      allTestsPassed = false;
    }
    
    // 測試有效 token
    const pingOk = await testPing(token);
    if (!pingOk) {
      allTestsPassed = false;
    }
    
    // 測試無效 token
    const invalidTokenOk = await testInvalidToken();
    if (!invalidTokenOk) {
      allTestsPassed = false;
    }
    
    // 總結
    console.log('\n' + '='.repeat(60));
    if (allTestsPassed) {
      console.log('🎉 All tests passed! Integration working correctly.');
      console.log('\n✅ Electron POC Phase 1 verification complete:');
      console.log('   - Token generation: ✅');
      console.log('   - Flask service startup: ✅');
      console.log('   - Health check endpoint: ✅');
      console.log('   - Token authentication: ✅');
      console.log('   - Invalid token rejection: ✅');
    } else {
      console.log('❌ Some tests failed. Check logs above.');
      process.exit(1);
    }
    
  } catch (error) {
    console.error('💥 Test failed with error:', error);
    process.exit(1);
  } finally {
    // 清理
    if (pythonProcess) {
      console.log('\n🧹 Cleaning up...');
      pythonProcess.kill('SIGTERM');
      
      // 給進程一些時間終止
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  
  console.log('👋 Test complete.\n');
}

// 執行測試
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
