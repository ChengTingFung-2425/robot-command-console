/**
 * Robot Command Blocks - Blockly Integration
 * 定義機器人動作積木與程式碼產生器
 */

// ============================================
// 自定義積木顏色主題
// ============================================
const BLOCK_COLORS = {
  movement: 210,    // 藍色 - 移動類
  gesture: 120,     // 綠色 - 姿態類
  combat: 0,        // 紅色 - 戰鬥類
  dance: 290,       // 紫色 - 舞蹈類
  exercise: 160,    // 青色 - 運動類
  control: 65,      // 黃色 - 控制流程
};

// ============================================
// 積木定義：移動類
// ============================================
Blockly.Blocks['robot_go_forward'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🤖 前進")
        .appendField(new Blockly.FieldNumber(3.5, 0.1, 600, 0.1), "DURATION")
        .appendField("秒");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.movement);
    this.setTooltip("讓機器人向前移動（3.5秒）");
    this.setHelpUrl("");
  }
};

Blockly.Blocks['robot_back_fast'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🤖 快速後退")
        .appendField(new Blockly.FieldNumber(4.5, 0.1, 600, 0.1), "DURATION")
        .appendField("秒");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.movement);
    this.setTooltip("讓機器人快速向後移動（4.5秒）");
  }
};

Blockly.Blocks['robot_turn_left'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🤖 左轉")
        .appendField(new Blockly.FieldNumber(4, 0.1, 600, 0.1), "DURATION")
        .appendField("秒");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.movement);
    this.setTooltip("讓機器人向左轉（4秒）");
  }
};

Blockly.Blocks['robot_turn_right'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🤖 右轉")
        .appendField(new Blockly.FieldNumber(4, 0.1, 600, 0.1), "DURATION")
        .appendField("秒");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.movement);
    this.setTooltip("讓機器人向右轉（4秒）");
  }
};

Blockly.Blocks['robot_left_move_fast'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🤖 快速左移")
        .appendField(new Blockly.FieldNumber(3, 0.1, 600, 0.1), "DURATION")
        .appendField("秒");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.movement);
    this.setTooltip("讓機器人快速向左移動（3秒）");
  }
};

Blockly.Blocks['robot_right_move_fast'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🤖 快速右移")
        .appendField(new Blockly.FieldNumber(3, 0.1, 600, 0.1), "DURATION")
        .appendField("秒");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.movement);
    this.setTooltip("讓機器人快速向右移動（3秒）");
  }
};

// ============================================
// 積木定義：姿態類
// ============================================
Blockly.Blocks['robot_stand'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🧍 站立");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.gesture);
    this.setTooltip("讓機器人站立（1秒）");
  }
};

Blockly.Blocks['robot_bow'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🙇 鞠躬");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.gesture);
    this.setTooltip("讓機器人鞠躬（4秒）");
  }
};

Blockly.Blocks['robot_squat'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🧘 蹲下");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.gesture);
    this.setTooltip("讓機器人蹲下（1秒）");
  }
};

Blockly.Blocks['robot_stand_up_front'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🤸 從前方起身");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.gesture);
    this.setTooltip("讓機器人從前方姿勢起身（5秒）");
  }
};

Blockly.Blocks['robot_stand_up_back'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🤸 從後方起身");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.gesture);
    this.setTooltip("讓機器人從後方姿勢起身（5秒）");
  }
};

Blockly.Blocks['robot_wave'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("👋 揮手");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.gesture);
    this.setTooltip("讓機器人揮手（3.5秒）");
  }
};

// ============================================
// 積木定義：戰鬥類
// ============================================
Blockly.Blocks['robot_left_kick'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🦵 左踢");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.combat);
    this.setTooltip("讓機器人左腳踢擊（2秒）");
  }
};

Blockly.Blocks['robot_right_kick'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🦵 右踢");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.combat);
    this.setTooltip("讓機器人右腳踢擊（2秒）");
  }
};

Blockly.Blocks['robot_kung_fu'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🥋 功夫");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.combat);
    this.setTooltip("讓機器人執行功夫動作（2秒）");
  }
};

Blockly.Blocks['robot_wing_chun'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🥋 詠春");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.combat);
    this.setTooltip("讓機器人執行詠春動作（2秒）");
  }
};

Blockly.Blocks['robot_left_uppercut'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("👊 左上勾拳");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.combat);
    this.setTooltip("讓機器人左上勾拳（2秒）");
  }
};

Blockly.Blocks['robot_right_uppercut'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("👊 右上勾拳");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.combat);
    this.setTooltip("讓機器人右上勾拳（2秒）");
  }
};

Blockly.Blocks['robot_left_shot_fast'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("👊 快速左拳");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.combat);
    this.setTooltip("讓機器人快速左拳（4秒）");
  }
};

Blockly.Blocks['robot_right_shot_fast'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("👊 快速右拳");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.combat);
    this.setTooltip("讓機器人快速右拳（4秒）");
  }
};

// ============================================
// 積木定義：舞蹈類
// ============================================
Blockly.Blocks['robot_dance'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("💃 跳舞")
        .appendField(new Blockly.FieldDropdown([
          ["舞蹈二", "dance_two"],
          ["舞蹈三", "dance_three"],
          ["舞蹈四", "dance_four"],
          ["舞蹈五", "dance_five"],
          ["舞蹈六", "dance_six"],
          ["舞蹈七", "dance_seven"],
          ["舞蹈八", "dance_eight"],
          ["舞蹈九", "dance_nine"],
          ["舞蹈十", "dance_ten"]
        ]), "DANCE_TYPE");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.dance);
    this.setTooltip("讓機器人跳指定舞蹈（52-85秒）");
  }
};

// ============================================
// 積木定義：運動類
// ============================================
Blockly.Blocks['robot_push_ups'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("💪 伏地挺身");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.exercise);
    this.setTooltip("讓機器人做伏地挺身（9秒）");
  }
};

Blockly.Blocks['robot_sit_ups'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("💪 仰臥起坐");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.exercise);
    this.setTooltip("讓機器人做仰臥起坐（12秒）");
  }
};

Blockly.Blocks['robot_chest'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("💪 胸部運動");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.exercise);
    this.setTooltip("讓機器人做胸部運動（9秒）");
  }
};

Blockly.Blocks['robot_weightlifting'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🏋️ 舉重");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.exercise);
    this.setTooltip("讓機器人做舉重動作（9秒）");
  }
};

Blockly.Blocks['robot_squat_up'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("💪 深蹲起立");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.exercise);
    this.setTooltip("讓機器人深蹲起立（6秒）");
  }
};

Blockly.Blocks['robot_twist'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("💪 扭轉");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.exercise);
    this.setTooltip("讓機器人扭轉身體（4秒）");
  }
};

Blockly.Blocks['robot_stepping'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("💪 踏步");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.exercise);
    this.setTooltip("讓機器人原地踏步（3秒）");
  }
};

// ============================================
// 積木定義：控制流程類
// ============================================
// 起始 (Starter) 積木：工作區預設放置，包裹其他動作
Blockly.Blocks['robot_start'] = {
  init: function() {
    this.appendStatementInput('DO')
        .setCheck(null)
        .appendField('\u25B6\uFE0F 開始');
    // 使用控制色系，使其與流程積木一致
    this.setColour(BLOCK_COLORS.control);
    this.setTooltip('程式的起始區塊，將動作放入此區塊內');
    this.setHelpUrl('');
    // 預設允許拖曳與刪除，使用者可從工具箱新增或移動至工作區
  }
};

Blockly.Blocks['robot_loop'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🔁 重複")
        .appendField(new Blockly.FieldNumber(2, 1, 10), "TIMES")
        .appendField("次");
    this.appendStatementInput("DO")
        .setCheck(null)
        .appendField("執行");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.control);
    this.setTooltip("重複執行指定次數的動作");
  }
};

Blockly.Blocks['robot_wait'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("⏱️ 等待")
        .appendField(new Blockly.FieldNumber(1000, 100, 10000, 100), "DURATION")
        .appendField("毫秒");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.control);
    this.setTooltip("暫停指定時間（毫秒）");
  }
};

Blockly.Blocks['robot_stop'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🛑 停止");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.control);
    this.setTooltip("停止所有動作");
  }
};

// ============================================
// 積木定義：擴充 / 進階指令（可從工具箱拖入）
// ============================================
Blockly.Blocks['advanced_command'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("🧩 進階指令")
        .appendField(new Blockly.FieldTextInput("command_name"), "CMD")
        .appendField(" 已驗證 ")
        .appendField(new Blockly.FieldCheckbox("0"), "VERIFIED");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(BLOCK_COLORS.control);
    this.setTooltip("引用一個已存在的進階指令（必須驗證）");
  }
};

// 進階指令的程式碼產生器
Blockly.JavaScript['advanced_command'] = function(block) {
  var name = block.getFieldValue('CMD') || '';
  var verified = block.getFieldValue('VERIFIED') === '1';
  return `{"command": "advanced_command", "name": "${name}", "advanced": true, "verified": ${verified}},\n`;
};

// ============================================
// 程式碼產生器：將積木轉換為 JSON 指令序列
// ============================================
Blockly.JavaScript = new Blockly.Generator('JavaScript');

// 簡單動作積木的產生器（通用模板）
const generateSimpleAction = (blockName, commandName) => {
  Blockly.JavaScript[blockName] = function(block) {
    return `{"command": "${commandName}"},\n`;
  };
};

// 帶有持續時間 (秒) 的動作產生器
const generateActionWithDuration = (blockName, commandName, defaultSeconds) => {
  Blockly.JavaScript[blockName] = function(block) {
    var duration = parseFloat(block.getFieldValue('DURATION')) || defaultSeconds || 0;
    // 決定輸出的時間單位：優先使用全域變數，其次檢查 localStorage，否則預設為秒(s)
    var unit = 's';
    if (typeof window !== 'undefined' && window.DURATION_UNIT) {
      unit = window.DURATION_UNIT;
    } else if (typeof localStorage !== 'undefined' && localStorage.getItem('durationUnit')) {
      unit = localStorage.getItem('durationUnit');
    }
    if (unit === 'ms') {
      var ms = Math.round(duration * 1000);
      return `{"command": "${commandName}", "duration_ms": ${ms}},\n`;
    }
    // default: seconds
    return `{"command": "${commandName}", "duration_s": ${duration}},\n`;
  };
};

// 移動類（包含可設定的持續時間）
generateActionWithDuration('robot_go_forward', 'go_forward', 3.5);
generateActionWithDuration('robot_back_fast', 'back_fast', 4.5);
generateActionWithDuration('robot_turn_left', 'turn_left', 4);
generateActionWithDuration('robot_turn_right', 'turn_right', 4);
generateActionWithDuration('robot_left_move_fast', 'left_move_fast', 3);
generateActionWithDuration('robot_right_move_fast', 'right_move_fast', 3);

// 姿態類
generateSimpleAction('robot_stand', 'stand');
generateSimpleAction('robot_bow', 'bow');
generateSimpleAction('robot_squat', 'squat');
generateSimpleAction('robot_stand_up_front', 'stand_up_front');
generateSimpleAction('robot_stand_up_back', 'stand_up_back');
generateSimpleAction('robot_wave', 'wave');

// 戰鬥類
generateSimpleAction('robot_left_kick', 'left_kick');
generateSimpleAction('robot_right_kick', 'right_kick');
generateSimpleAction('robot_kung_fu', 'kung_fu');
generateSimpleAction('robot_wing_chun', 'wing_chun');
generateSimpleAction('robot_left_uppercut', 'left_uppercut');
generateSimpleAction('robot_right_uppercut', 'right_uppercut');
generateSimpleAction('robot_left_shot_fast', 'left_shot_fast');
generateSimpleAction('robot_right_shot_fast', 'right_shot_fast');

// 舞蹈類（下拉選單）
Blockly.JavaScript['robot_dance'] = function(block) {
  var danceType = block.getFieldValue('DANCE_TYPE');
  return `{"command": "${danceType}"},\n`;
};

// 運動類
generateSimpleAction('robot_push_ups', 'push_ups');
generateSimpleAction('robot_sit_ups', 'sit_ups');
generateSimpleAction('robot_chest', 'chest');
generateSimpleAction('robot_weightlifting', 'weightlifting');
generateSimpleAction('robot_squat_up', 'squat_up');
generateSimpleAction('robot_twist', 'twist');
generateSimpleAction('robot_stepping', 'stepping');

// 控制流程類
Blockly.JavaScript['robot_loop'] = function(block) {
  var times = block.getFieldValue('TIMES');
  var branch = Blockly.JavaScript.statementToCode(block, 'DO');
  
  // 將內部指令重複 times 次
  var repeated = '';
  for (var i = 0; i < times; i++) {
    repeated += branch;
  }
  return repeated;
};

Blockly.JavaScript['robot_wait'] = function(block) {
  var duration = block.getFieldValue('DURATION');
  return `{"command": "wait", "duration_ms": ${duration}},\n`;
};

Blockly.JavaScript['robot_stop'] = function(block) {
  return `{"command": "stop"},\n`;
};

// ============================================
// 工具箱（Toolbox）定義
// ============================================
const ROBOT_TOOLBOX = {
  "kind": "categoryToolbox",
  "contents": [
    {
      "kind": "category",
      "name": "移動 🤖",
      "colour": BLOCK_COLORS.movement,
      "contents": [
        {"kind": "block", "type": "robot_go_forward"},
        {"kind": "block", "type": "robot_back_fast"},
        {"kind": "block", "type": "robot_turn_left"},
        {"kind": "block", "type": "robot_turn_right"},
        {"kind": "block", "type": "robot_left_move_fast"},
        {"kind": "block", "type": "robot_right_move_fast"}
      ]
    },
    {
      "kind": "category",
      "name": "姿態 🧍",
      "colour": BLOCK_COLORS.gesture,
      "contents": [
        {"kind": "block", "type": "robot_stand"},
        {"kind": "block", "type": "robot_bow"},
        {"kind": "block", "type": "robot_squat"},
        {"kind": "block", "type": "robot_stand_up_front"},
        {"kind": "block", "type": "robot_stand_up_back"},
        {"kind": "block", "type": "robot_wave"}
      ]
    },
    {
      "kind": "category",
      "name": "戰鬥 🥋",
      "colour": BLOCK_COLORS.combat,
      "contents": [
        {"kind": "block", "type": "robot_left_kick"},
        {"kind": "block", "type": "robot_right_kick"},
        {"kind": "block", "type": "robot_kung_fu"},
        {"kind": "block", "type": "robot_wing_chun"},
        {"kind": "block", "type": "robot_left_uppercut"},
        {"kind": "block", "type": "robot_right_uppercut"},
        {"kind": "block", "type": "robot_left_shot_fast"},
        {"kind": "block", "type": "robot_right_shot_fast"}
      ]
    },
    {
      "kind": "category",
      "name": "舞蹈 💃",
      "colour": BLOCK_COLORS.dance,
      "contents": [
        {
          "kind": "block",
          "type": "robot_dance",
          "fields": {"DANCE_TYPE": "dance_two"}
        }
      ]
    },
    {
      "kind": "category",
      "name": "運動 💪",
      "colour": BLOCK_COLORS.exercise,
      "contents": [
        {"kind": "block", "type": "robot_push_ups"},
        {"kind": "block", "type": "robot_sit_ups"},
        {"kind": "block", "type": "robot_chest"},
        {"kind": "block", "type": "robot_weightlifting"},
        {"kind": "block", "type": "robot_squat_up"},
        {"kind": "block", "type": "robot_twist"},
        {"kind": "block", "type": "robot_stepping"}
      ]
    },
    {
      "kind": "category",
      "name": "擴充 🔌",
      "colour": 45,
      "contents": [
        {"kind": "block", "type": "advanced_command"}
      ]
    },
    {
      "kind": "category",
      "name": "控制 🔁",
      "colour": BLOCK_COLORS.control,
      "contents": [
        {"kind": "block", "type": "robot_start"},
        {
          "kind": "block",
          "type": "robot_loop",
          "fields": {"TIMES": 2}
        },
        {
          "kind": "block",
          "type": "robot_wait",
          "fields": {"DURATION": 1000}
        },
        {"kind": "block", "type": "robot_stop"}
      ]
    }
  ]
};

// ============================================
// 輔助函數：產生 JSON 指令序列
// ============================================
function generateCommandJSON(workspace) {
  var code = Blockly.JavaScript.workspaceToCode(workspace);
  
  // 移除最後的逗號與換行
  code = code.trim();
  if (code.endsWith(',')) {
    code = code.slice(0, -1);
  }
  
  // 包裝成 JSON 陣列
  var json = '[\n  ' + code.replace(/\},\n/g, '},\n  ') + '\n]';
  
  try {
    // 驗證 JSON 格式
    JSON.parse(json);
    return json;
  } catch (e) {
    console.error('JSON 產生錯誤:', e);
    return '[]';
  }
}

// ============================================
// 輔助函數：從 JSON 載入積木
// ============================================
function loadBlocksFromJSON(workspace, jsonString) {
  try {
    var commands = JSON.parse(jsonString);
    workspace.clear();
    
    // TODO: 實作從 JSON 反向產生積木的邏輯
    // 這需要更複雜的解析器來將 JSON 指令轉回積木結構
    
    console.log('從 JSON 載入積木（功能開發中）', commands);
  } catch (e) {
    console.error('JSON 解析錯誤:', e);
    alert('無效的 JSON 格式');
  }
}
