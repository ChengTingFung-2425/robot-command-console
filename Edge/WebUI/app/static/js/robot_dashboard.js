/**
 * Robot Dashboard - Video Stream Manager
 * Manages WebSocket connections for robot video feeds with exponential backoff reconnection
 */

// WebSocket connections for video feeds
const robotConnections = {};
const reconnectDelays = {}; // Track reconnection delays per robot

/**
 * Initialize video stream connections for all robots
 * @param {Array} robotIds - Array of robot IDs to connect
 */
function initRobotVideoStreams(robotIds) {
  robotIds.forEach(robotId => {
    reconnectDelays[robotId] = 1000; // Start with 1 second
    connectRobotFeed(robotId);
  });
}

/**
 * Connect to a robot's video feed via WebSocket
 * @param {number} robotId - The robot ID to connect to
 */
function connectRobotFeed(robotId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/api/media/stream/${robotId}`;
  
  const ws = new WebSocket(wsUrl);
  robotConnections[robotId] = ws;
  
  ws.onopen = function() {
    console.log(`機器人 ${robotId} 視訊串流已連線`);
    reconnectDelays[robotId] = 1000; // Reset delay on successful connection
    const placeholder = document.getElementById(`placeholder-${robotId}`);
    if (placeholder) placeholder.style.display = 'none';
  };
  
  ws.onmessage = function(event) {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'video') {
        renderVideoFrame(robotId, data.frame);
      }
    } catch (e) {
      console.error('解析視訊資料失敗:', e);
    }
  };
  
  ws.onerror = function(error) {
    console.error(`機器人 ${robotId} 視訊串流錯誤:`, error);
  };
  
  ws.onclose = function() {
    console.log(`機器人 ${robotId} 視訊串流已斷線`);
    const placeholder = document.getElementById(`placeholder-${robotId}`);
    if (placeholder) placeholder.style.display = 'block';
    
    // Exponential backoff with max delay of 30 seconds
    const delay = Math.min(reconnectDelays[robotId], 30000);
    reconnectDelays[robotId] = delay * 2;
    
    console.log(`將在 ${delay/1000} 秒後重新連線...`);
    setTimeout(() => connectRobotFeed(robotId), delay);
  };
}

/**
 * Render a video frame to the canvas
 * @param {number} robotId - The robot ID
 * @param {string} frameData - Base64 encoded frame data
 */
function renderVideoFrame(robotId, frameData) {
  const canvas = document.getElementById(`robot-video-${robotId}`);
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  const img = new Image();
  
  img.onload = function() {
    // Set canvas size to 4:3 ratio (480x360)
    canvas.width = 480;
    canvas.height = 360;
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  };
  
  img.src = 'data:image/jpeg;base64,' + frameData;
}

/**
 * Cleanup all WebSocket connections on page unload
 */
function cleanupConnections() {
  Object.values(robotConnections).forEach(ws => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  });
}

// Clean up connections when page is unloaded
window.addEventListener('beforeunload', cleanupConnections);
