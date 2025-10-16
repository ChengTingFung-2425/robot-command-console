# Python version of the robot actions and tool list

# Dictionary of robot actions with sleep time, action commands, and name
ACTIONS = {
    "back_fast": {"sleep_time": 4.5, "action": ["2", "4"], "name": "back_fast"},
    "bow": {"sleep_time": 4, "action": ["10", "1"], "name": "bow"},
    "chest": {"sleep_time": 9, "action": ["12", "1"], "name": "chest"},
    "dance_eight": {"sleep_time": 85, "action": ["42", "1"], "name": "dance_eight"},
    "dance_five": {"sleep_time": 59, "action": ["39", "1"], "name": "dance_five"},
    "dance_four": {"sleep_time": 59, "action": ["38", "1"], "name": "dance_four"},
    "dance_nine": {"sleep_time": 84, "action": ["43", "1"], "name": "dance_nine"},
    "dance_seven": {"sleep_time": 67, "action": ["41", "1"], "name": "dance_seven"},
    "dance_six": {"sleep_time": 69, "action": ["40", "1"], "name": "dance_six"},
    "dance_ten": {"sleep_time": 85, "action": ["44", "1"], "name": "dance_ten"},
    "dance_three": {"sleep_time": 70, "action": ["37", "1"], "name": "dance_three"},
    "dance_two": {"sleep_time": 52, "action": ["36", "1"], "name": "dance_two"},
    "go_forward": {"sleep_time": 3.5, "action": ["1", "4"], "name": "go_forward"},
    "kung_fu": {"sleep_time": 2, "action": ["46", "2"], "name": "kung_fu"},
    "left_kick": {"sleep_time": 2, "action": ["18", "1"], "name": "left_kick"},
    "left_move_fast": {"sleep_time": 3, "action": ["3", "4"], "name": "left_move_fast"},
    "left_shot_fast": {
        "sleep_time": 4,
        "action": ["13", "1"],
        "name": "left_shot_fast",
    },
    "left_uppercut": {"sleep_time": 2, "action": ["16", "1"], "name": "left_uppercut"},
    "push_ups": {"sleep_time": 9, "action": ["5", "1"], "name": "push_ups"},
    "right_kick": {"sleep_time": 2, "action": ["19", "1"], "name": "right_kick"},
    "right_move_fast": {
        "sleep_time": 3,
        "action": ["4", "4"],
        "name": "right_move_fast",
    },
    "right_shot_fast": {
        "sleep_time": 4,
        "action": ["14", "1"],
        "name": "right_shot_fast",
    },
    "right_uppercut": {
        "sleep_time": 2,
        "action": ["17", "1"],
        "name": "right_uppercut",
    },
    "sit_ups": {"sleep_time": 12, "action": ["6", "1"], "name": "sit_ups"},
    "squat": {"sleep_time": 1, "action": ["11", "1"], "name": "squat"},
    "squat_up": {"sleep_time": 6, "action": ["45", "1"], "name": "squat_up"},
    "stand": {"sleep_time": 1, "action": ["0", "1"], "name": "站立"},
    "stand_up_back": {"sleep_time": 5, "action": ["21", "1"], "name": "stand_up_back"},
    "stand_up_front": {
        "sleep_time": 5,
        "action": ["20", "1"],
        "name": "stand_up_front",
    },
    "stepping": {"sleep_time": 3, "action": ["24", "2"], "name": "stepping"},
    "stop": {"sleep_time": 3, "action": ["24", "2"], "name": "stop"},
    "turn_left": {"sleep_time": 4, "action": ["7", "4"], "name": "turn_left"},
    "turn_right": {"sleep_time": 4, "action": ["8", "4"], "name": "turn_right"},
    "twist": {"sleep_time": 4, "action": ["22", "1"], "name": "twist"},
    "wave": {"sleep_time": 3.5, "action": ["9", "1"], "name": "wave"},
    "weightlifting": {"sleep_time": 9, "action": ["35", "1"], "name": "weightlifting"},
    "wing_chun": {"sleep_time": 2, "action": ["15", "1"], "name": "wing_chun"},
}

# List of tools with names and descriptions
TOOL_LIST = [
    {
        "name": "back_fast",
        "description": "Command the robot to move backward quickly.",
    },
    {
        "name": "bow",
        "description": "Command the robot to bow.",
    },
    {
        "name": "chest",
        "description": "Command the robot to perform chest exercises.",
    },
    {
        "name": "dance_eight",
        "description": "Command the robot to perform dance eight.",
    },
    {
        "name": "dance_five",
        "description": "Command the robot to perform dance five.",
    },
    {
        "name": "dance_four",
        "description": "Command the robot to perform dance four.",
    },
    {
        "name": "dance_nine",
        "description": "Command the robot to perform dance nine.",
    },
    {
        "name": "dance_seven",
        "description": "Command the robot to perform dance seven.",
    },
    {
        "name": "dance_six",
        "description": "Command the robot to perform dance six.",
    },
    {
        "name": "dance_ten",
        "description": "Command the robot to perform dance ten.",
    },
    {
        "name": "dance_three",
        "description": "Command the robot to perform dance three.",
    },
    {
        "name": "dance_two",
        "description": "Command the robot to perform dance two.",
    },
    {
        "name": "go_forward",
        "description": "Command the robot to move forward in the direction it is currently facing.",
    },
    {
        "name": "kung_fu",
        "description": "Command the robot to perform kung fu moves.",
    },
    {
        "name": "left_kick",
        "description": "Command the robot to perform a left kick.",
    },
    {
        "name": "left_move_fast",
        "description": "Command the robot to move left quickly.",
    },
    {
        "name": "left_shot_fast",
        "description": "Command the robot to perform a fast left punch.",
    },
    {
        "name": "left_uppercut",
        "description": "Command the robot to perform a left uppercut.",
    },
    {"name": "push_ups", "description": "Command the robot to perform push-ups."},
    {
        "name": "right_kick",
        "description": "Command the robot to perform a right kick.",
    },
    {
        "name": "right_move_fast",
        "description": "Command the robot to move right quickly.",
    },
    {
        "name": "right_shot_fast",
        "description": "Command the robot to perform a fast right punch.",
    },
    {
        "name": "right_uppercut",
        "description": "Command the robot to perform a right uppercut.",
    },
    {
        "name": "sit_ups",
        "description": "Command the robot to perform sit-ups.",
    },
    {
        "name": "squat",
        "description": "Command the robot to squat down.",
    },
    {
        "name": "squat_up",
        "description": "Command the robot to stand up from a squat.",
    },
    {
        "name": "stand",
        "description": "Command the robot to stand up and maintain a standing position.",
    },
    {
        "name": "stand_up_back",
        "description": "Command the robot to stand up from the back.",
    },
    {
        "name": "stand_up_front",
        "description": "Command the robot to stand up from the front.",
    },
    {
        "name": "stepping",
        "description": "Command the robot to perform stepping motions.",
    },
    {
        "name": "stop",
        "description": "Command the robot to perform stepping motions.",
    },
    {
        "name": "turn_left", 
        "description": "Command the robot to turn left."
    },
    {
        "name": "turn_right", 
        "description": "Command the robot to turn right."
    },
    {
        "name": "twist",
        "description": "Command the robot to twist its body."
    },
    {
        "name": "wave",
        "description": "Command the robot to wave its hand."
    },
    {
        "name": "weightlifting",
        "description": "Command the robot to perform weightlifting.",
    },
    {
        "name": "wing_chun",
        "description": "Command the robot to perform Wing Chun moves.",
    },
]

# Default tool schema for input validation
DEFAULT_TOOL_SCHEMA = {
    "type": "object",
    "properties": {},
    "required": [],
}  # Python equivalent of DefaultToolSchema

# Convert tool list to toolSpec format
TOOLS = [
    {
        "toolSpec": {
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": {"json": DEFAULT_TOOL_SCHEMA},
        }
    }
    for tool in TOOL_LIST
]
