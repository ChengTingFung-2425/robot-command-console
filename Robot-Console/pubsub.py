# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import configparser
import json
import logging
import os
import threading
from concurrent.futures import Future
from typing import Any, Dict, Optional

import yaml
from action_executor import ActionExecutor
from advanced_decoder import AdvancedDecoder
from awscrt import auth, mqtt5
from awsiot import mqtt5_client_builder

TIMEOUT = 5

# Maximum recommended size for actions array to avoid performance issues
# Arrays larger than this will still be processed but may cause delays
MAX_RECOMMENDED_ACTIONS = 100

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def load_settings(settings_path: str) -> dict:
    try:
        with open(settings_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logging.error("Failed to load settings: %s", e)
        raise


def format_settings(
    settings: Dict[str, Any], robot_name: str, base_path: str
) -> Dict[str, Any]:
    # Format all relevant fields with robot_name and base_path
    for key in ["input_topic", "input_cert", "input_key", "input_ca", "input_clientId"]:
        if key in settings:
            settings[key] = settings[key].format(
                robot_name=robot_name, base_path=base_path
            )
    return settings


class PubSubClient:
    def __init__(self, settings: Dict[str, Any], executor: ActionExecutor):
        self.settings = settings
        self.executor = executor
        # Create decoder using MCP base URL if provided in settings (optional, for legacy support)
        mcp_base = settings.get("mcp_base_url") or settings.get("MCP_BASE_URL")
        self.decoder = AdvancedDecoder(mcp_base_url=mcp_base) if settings.get("enable_legacy_decoder", False) else None
        self.client: Optional[mqtt5.Client] = None
        self.future_stopped = Future()
        self.future_connection_success = Future()
        self.received_all_event = threading.Event()
        self.message_topic = settings["input_topic"]

    def on_publish_received(self, publish_packet_data):
        try:
            publish_packet = publish_packet_data.publish_packet
            assert isinstance(publish_packet, mqtt5.PublishPacket)
            logging.info(
                "Received message from topic '%s': %s",
                publish_packet.topic,
                publish_packet.payload,
            )
            try:
                payload = json.loads(publish_packet.payload)
                
                # Primary: Handle pre-decoded actions array from WebUI/upper layer
                if "actions" in payload:
                    actions = payload["actions"]
                    
                    # Validate actions is a list
                    if not isinstance(actions, list):
                        logging.error(
                            "Invalid 'actions' format in payload: expected list, got %s",
                            type(actions).__name__
                        )
                        return

                    # Warn if actions array is very large (may impact performance)
                    if len(actions) > MAX_RECOMMENDED_ACTIONS:
                        logging.warning(
                            "Actions array size (%d) exceeds recommended max (%d). "
                            "Consider breaking into smaller batches.",
                            len(actions), MAX_RECOMMENDED_ACTIONS
                        )
                    
                    # Validate all actions are strings (short-circuits on first non-string)
                    for i, action in enumerate(actions):
                        if not isinstance(action, str):
                            logging.error(
                                "Invalid action at index %d: expected string, got %s",
                                i, type(action).__name__
                            )
                            return
                    
                    logging.info("Processing pre-decoded actions list: %s", actions)
                    self.executor.add_actions_to_queue(actions)
                    return
                
                # Legacy: Try decoder if enabled (backward compatibility)
                if self.decoder:
                    try:
                        decoded = self.decoder.decode(payload)
                        if decoded:
                            logging.info("Using legacy decoder, decoded actions: %s", decoded)
                            self.executor.add_actions_to_queue(decoded)
                            return
                    except Exception as e:
                        logging.warning("Legacy decoder error: %s", e)
                
                # Fallback: legacy single toolName field
                action_name = payload.get("toolName")
                if action_name:
                    logging.info("Processing legacy toolName: %s", action_name)
                    self.executor.add_action_to_queue(action_name)
                else:
                    logging.warning("No actionable command found in payload: %s", payload)
                    
            except json.JSONDecodeError:
                logging.error("Invalid JSON payload received")
        except Exception as e:
            logging.error("Exception in on_publish_received: %s", e)

    def on_lifecycle_stopped(self, lifecycle_stopped_data: mqtt5.LifecycleStoppedData):
        logging.info("Lifecycle Stopped")
        if not self.future_stopped.done():
            self.future_stopped.set_result(lifecycle_stopped_data)

    def on_lifecycle_connection_success(
        self, lifecycle_connect_success_data: mqtt5.LifecycleConnectSuccessData
    ):
        logging.info("Lifecycle Connection Success")
        if not self.future_connection_success.done():
            self.future_connection_success.set_result(lifecycle_connect_success_data)

    def on_lifecycle_connection_failure(
        self, lifecycle_connection_failure: mqtt5.LifecycleConnectFailureData
    ):
        logging.error(
            "Lifecycle Connection Failure: %s", lifecycle_connection_failure.exception
        )

    def build_mqtt_client(self, use_websocket: bool = False) -> mqtt5.Client:
        client_args = dict(
            endpoint=self.settings["input_endpoint"],
            client_id=self.settings["input_clientId"],
            keep_alive_interval_sec=5,
            on_publish_received=self.on_publish_received,
            on_lifecycle_stopped=self.on_lifecycle_stopped,
            on_lifecycle_connection_success=self.on_lifecycle_connection_success,
            on_lifecycle_connection_failure=self.on_lifecycle_connection_failure,
        )
        if not use_websocket:
            return mqtt5_client_builder.mtls_from_path(
                port=8883,
                cert_filepath=self.settings["input_cert"],
                pri_key_filepath=self.settings["input_key"],
                ca_filepath=self.settings["input_ca"],
                **client_args
            )
        else:
            region = self.settings.get("region", "us-east-1")
            credentials_provider = auth.AwsCredentialsProvider.new_static(
                access_key_id=self.settings["aws_access_key_id"],
                secret_access_key=self.settings["aws_secret_access_key"],
            )
            return mqtt5_client_builder.websockets_with_default_aws_signing(
                region=region,
                credentials_provider=credentials_provider,
                ca_filepath=self.settings["input_ca"],
                port=443,
                **client_args
            )

    def connect(self) -> None:
        try:
            logging.info("Trying MQTT mTLS connection...")
            self.client = self.build_mqtt_client(use_websocket=False)
            self.client.start()
            lifecycle_connect_success_data = self.future_connection_success.result(
                TIMEOUT
            )
            connack_packet = lifecycle_connect_success_data.connack_packet
            logging.info(
                "Connected to endpoint: '%s' with Client ID: '%s' reason_code: %s",
                self.settings["input_endpoint"],
                self.settings["input_clientId"],
                repr(connack_packet.reason_code),
            )
        except Exception as e:
            logging.warning("MQTT mTLS failed: %s. Trying WebSocket...", e)
            # Reset the future for websocket attempt
            self.future_connection_success = Future()
            self.client = self.build_mqtt_client(use_websocket=True)
            self.client.start()
            lifecycle_connect_success_data = self.future_connection_success.result(
                TIMEOUT
            )
            connack_packet = lifecycle_connect_success_data.connack_packet
            logging.info(
                "Connected to endpoint: '%s' with Client ID: '%s' (WebSocket) reason_code: %s",
                self.settings["input_endpoint"],
                self.settings["input_clientId"],
                repr(connack_packet.reason_code),
            )

    def subscribe(self) -> None:
        logging.info("Subscribing to topic '%s'...", self.message_topic)
        subscribe_future = self.client.subscribe(
            subscribe_packet=mqtt5.SubscribePacket(
                subscriptions=[
                    mqtt5.Subscription(
                        topic_filter=self.message_topic, qos=mqtt5.QoS.AT_LEAST_ONCE
                    )
                ]
            )
        )
        suback = subscribe_future.result(TIMEOUT)
        logging.info("Subscribed with %s", suback.reason_codes)

    def unsubscribe(self) -> None:
        try:
            logging.info("Unsubscribing from topic '%s'", self.message_topic)
            unsubscribe_future = self.client.unsubscribe(
                unsubscribe_packet=mqtt5.UnsubscribePacket(
                    topic_filters=[self.message_topic]
                )
            )
            unsuback = unsubscribe_future.result(TIMEOUT)
            logging.info("Unsubscribed with %s", unsuback.reason_codes)
        except Exception as e:
            logging.warning("Exception during unsubscribe: %s", e)

    def stop(self) -> None:
        logging.info("Stopping Client")
        if self.client:
            self.client.stop()
        self.executor.stop()
        try:
            self.future_stopped.result(TIMEOUT)
        except Exception as e:
            logging.warning("Exception waiting for client stop: %s", e)
        logging.info("Client Stopped!")

    def run(self) -> None:
        self.connect()
        self.subscribe()
        logging.info("Sending messages until user inputs 's' to stop")
        try:
            while True:
                user_input = input("Type 's' and press Enter to stop the program: ")
                if user_input.strip().lower() == "s":
                    logging.info("'s' received, shutting down gracefully...")
                    self.received_all_event.set()
                    break
        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt received, shutting down...")
        finally:
            self.unsubscribe()
            self.stop()


def main():
    try:
        settings = load_settings("settings.yaml")
        robot_name = settings["robot_name"]
        base_path = settings["base_path"]
        settings = format_settings(settings, robot_name, base_path)
        if not settings.get("aws_access_key_id"):
            settings["aws_access_key_id"] = os.environ.get("IoTRobotAccessKeyId", "")
        if not settings["aws_access_key_id"]:
            settings["aws_access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID", "")
        if not settings["aws_access_key_id"]:
            # Try to read from AWS CLI config (~/.aws/credentials)
            aws_creds_path = os.path.expanduser("~/.aws/credentials")
            if os.path.exists(aws_creds_path):
                config = configparser.ConfigParser()
                config.read(aws_creds_path)
                profile = os.environ.get("AWS_PROFILE", "default")
                if config.has_section(profile):
                    settings["aws_access_key_id"] = config.get(
                        profile, "aws_access_key_id", fallback=""
                    )
                    settings["aws_secret_access_key"] = config.get(
                        profile, "aws_secret_access_key", fallback=""
                    )
        if not settings.get("aws_secret_access_key"):
            settings["aws_secret_access_key"] = os.environ.get(
                "IoTRobotSecretAccessKey", ""
            )
        if not settings["aws_secret_access_key"]:
            settings["aws_secret_access_key"] = os.environ.get(
                "AWS_SECRET_ACCESS_KEY", ""
            )
        print("Settings loaded successfully:", json.dumps(settings, indent=2))

        executor = ActionExecutor(
            robot_name,
            settings.get("simulator_endpoint", ""),
            settings.get("session_key", ""),
        )
        client = PubSubClient(settings, executor)
        client.run()
    except Exception as e:
        logging.error("Exception occurred in main loop: %s", e)


if __name__ == "__main__":
    main()
