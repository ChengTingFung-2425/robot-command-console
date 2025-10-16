import logging
import queue
import threading
import time
from typing import Any, Dict, Optional
from uuid import uuid4

import requests

logger = logging.getLogger(__name__)

# 動作配置字典 (Action configuration dictionary)
actions: Dict[str, Dict[str, Any]] = {
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

# 空閒動作 (Idle action)
idle_action: Dict[str, Any] = {"name": None, "sleep_time": 0}


class ActionExecutor:

    def __init__(
        self, robot_name: str, simulator_endpoint: str, session_key: str
    ) -> None:
        """Initialize the ActionExecutor with a queue and a consumer thread."""
        self.robot_name = robot_name
        self.simulator_endpoint = simulator_endpoint
        self.session_key = session_key
        self.logger = logging.getLogger(__name__)
        self.action_queue: queue.Queue = queue.Queue()
        self.current_action: Dict[str, Any] = idle_action.copy()
        self.is_running: bool = False
        self._immediate_stop_event = threading.Event()
        self.queue_lock = threading.Lock()
        self._stop_event = threading.Event()
        self.consumer_thread = threading.Thread(target=self._consumer, daemon=True)
        self.consumer_thread.start()

    def _run_action(
        self, action_name: str, p1: str, p2: str
    ) -> Optional[Dict[str, Any]]:
        """Send a request to execute an action."""

        self._send_to_simulator(
            action_name=action_name,
            log_success_msg=f"Action {action_name} sent to simulator.",
            log_error_msg=f"Error sending action {action_name} to simulator:",
        )

        return self._send_request(
            method="RunAction",
            params=[p1, p2],
            log_success_msg=f"Action run_action({p1}, {p2}) successful.",
            log_error_msg=f"Error running action run_action({p1}, {p2}):",
        )

    def _run_stop_action(self) -> Optional[Dict[str, Any]]:
        """Send a request to stop the current action group."""
        return self._send_request(
            method="StopBusServo",
            params=["stopAction"],
            log_success_msg="Action run_stop_action() successful.",
            log_error_msg="Error running action run_stop_action():",
        )

    def _send_request(
        self,
        method: str,
        params: Optional[list],
        log_success_msg: str,
        log_error_msg: str,
    ) -> Optional[Dict[str, Any]]:
        headers = {"deviceid": "1732853986186"}
        data = {
            "id": "1732853986186",
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            data["params"] = params
        try:
            response = requests.post(
                "http://localhost:9030/", headers=headers, json=data, timeout=0.5
            )
            response.raise_for_status()
            self.logger.info("%s Response: %s", log_success_msg, response.json())
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error("%s %s", log_error_msg, e)
            return None

    def _execute_action(self, action_item: Dict[str, Any]) -> None:
        """Execute a single action from the queue."""
        action_name = action_item["name"]
        action = actions[action_name]
        self.current_action = {
            "name": action["name"],
            "sleep_time": action["sleep_time"],
        }
        try:
            self._run_action(action_name, action["action"][0], action["action"][1])
            elapsed = 0.0
            while elapsed < action["sleep_time"]:
                if self._immediate_stop_event.is_set():
                    self.logger.info("Stopping action execution for %s", action_name)
                    self._immediate_stop_event.clear()
                    self._run_stop_action()
                    break
                time.sleep(0.1)
                elapsed += 0.1
        except Exception as e:
            self.logger.error("Error executing action %s: %s", action_name, e)
        finally:
            self._remove_action_by_id(action_item["id"])
            self.current_action = idle_action.copy()

    def _remove_action_by_id(self, action_id: str) -> None:
        """Remove an action from the queue by its ID."""
        with self.queue_lock:
            temp_list = list(self.action_queue.queue)
            filtered = [item for item in temp_list if item["id"] != action_id]
            self._replace_queue(filtered)

    def _replace_queue(self, items: list) -> None:
        """Replace the current queue with a new list of items."""
        self.action_queue.queue.clear()
        for item in items:
            self.action_queue.put(item)

    def _consumer(self) -> None:
        """Continuously consume actions from the queue and execute them."""
        time.sleep(5 - time.time() % 5)
        while not self._stop_event.is_set():
            try:
                if self._immediate_stop_event.is_set():
                    self.logger.info(
                        "Immediate stop triggered, clearing queue and setting to idle."
                    )
                    self.clear_action_queue()
                    self.current_action = idle_action.copy()
                    self.is_running = False
                    self._immediate_stop_event.clear()
                    time.sleep(0.5)
                    continue
                time.sleep(1 - time.time() % 1)
                action_item = self.action_queue.get(timeout=1)
                self.is_running = True
                self._execute_action(action_item)
                time.sleep(0.5)
            except queue.Empty:
                self.is_running = False
                time.sleep(0.5)

    def add_action_to_queue(self, action_name: str) -> None:
        """Add a new action to the queue."""
        action_id = str(uuid4())

        if action_name == "stop":
            self.stop()  # Use improved stop logic
            return

        if action_name not in actions:
            self.logger.error(
                "Action '%s' not found in actions dictionary.", action_name
            )
            return

        with self.queue_lock:
            self.action_queue.put({"id": action_id, "name": action_name})

    def remove_action_from_queue(self, action_id: str) -> None:
        """Remove an action from the queue by its ID."""
        self._remove_action_by_id(action_id)

    def clear_action_queue(self) -> None:
        """Clear all actions from the queue."""
        with self.queue_lock:
            self.action_queue.queue.clear()

    def get_queue_status(self) -> Dict[str, Any]:
        """Get the current status of the action queue."""
        with self.queue_lock:
            queue_items = list(self.action_queue.queue)
        return {
            "queue": queue_items,
            "current_action": self.current_action,
            "is_running": self.is_running,
        }

    def stop(self) -> None:
        """Stop all actions immediately and clear the queue."""
        self.logger.info(
            "Immediate stop requested: clearing queue and intserrupting current action."
        )
        self._immediate_stop_event.set()
        self.clear_action_queue()
        with self.queue_lock:
            stand_id = str(uuid4())
            self.action_queue.put({"id": stand_id, "name": "stand"})

    def shutdown(self) -> None:
        """Gracefully shutdown the consumer thread."""
        self._stop_event.set()
        self.consumer_thread.join()

    def _send_to_simulator(
        self,
        action_name: str,
        log_success_msg: str = None,
        log_error_msg: str = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Send an action command to the robot simulator.

        Args:
            action_name: The name of the action to execute
            robot_id: The ID of the robot to control
            session_key: The session key for authentication
            simulator_base_url: The base URL of the simulator (default: http://localhost:5000)
            log_success_msg: Message to log on successful API call
            log_error_msg: Message to log on failed API call

        Returns:
            Optional response data from the simulator API call
        """

        if log_success_msg is None:
            log_success_msg = f"Simulator action {action_name} for robot {self.robot_name} successful."
        if log_error_msg is None:
            log_error_msg = f"Error sending action {action_name} to simulator for robot {self.robot_name}:"

        # Construct the URL in the format:
        url = f"{self.simulator_endpoint}/run_action/{self.robot_name}?session_key={self.session_key}"

        # Prepare the payload in the expected format: {"action": "bow"}
        payload = {"action": action_name}

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=3.0,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            resp_json = response.json()
            self.logger.info(
                "%s - %s Response: %s", self.robot_name, log_success_msg, resp_json
            )
            return resp_json
        except requests.exceptions.RequestException as e:
            self.logger.error("%s %s", log_error_msg, e)
            return None
