import json
import os
import unittest

try:
    import jsonschema
    from jsonschema.exceptions import ValidationError
    HAS_JSONSCHEMA = True
except Exception:
    jsonschema = None  # type: ignore
    ValidationError = Exception  # type: ignore
    HAS_JSONSCHEMA = False


SCHEMA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs', 'contract'))


def _load_schema(name: str):
    path = os.path.join(SCHEMA_DIR, name)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


class TestContractSchemas(unittest.TestCase):
    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed")
    def test_command_request_schema_valid(self):
        schema = _load_schema('command_request.schema.json')
        doc = {
            "trace_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": "2025-10-15T08:30:00Z",
            "actor": {"type": "human", "id": "user_1"},
            "source": "webui",
            "command": {
                "id": "cmd-1",
                "type": "robot.move",
                "target": {"robot_id": "rbx-01"},
                "params": {"x": 1, "y": 2},
                "timeout_ms": 1000,
                "priority": "normal"
            },
            "labels": {"env": "dev"}
        }
        jsonschema.validate(instance=doc, schema=schema)

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed")
    def test_command_request_schema_invalid(self):
        schema = _load_schema('command_request.schema.json')
        bad = {
            # missing trace_id, timestamp
            "actor": {"type": "human", "id": "user_1"},
            "source": "webui",
            "command": {
                "id": "cmd-1",
                "type": "robot.move",
                "target": {"robot_id": "rbx-01"}
            }
        }
        with self.assertRaises(ValidationError):
            jsonschema.validate(instance=bad, schema=schema)

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed")
    def test_command_response_schema_valid(self):
        schema = _load_schema('command_response.schema.json')
        doc = {
            "trace_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": "2025-10-15T08:30:01Z",
            "command": {"id": "cmd-1", "status": "accepted"},
            "result": {"summary": "ok"}
        }
        jsonschema.validate(instance=doc, schema=schema)

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed")
    def test_status_response_schema_valid(self):
        schema = _load_schema('status_response.schema.json')
        doc = {
            "trace_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": "2025-10-15T08:31:01Z",
            "command": {"id": "cmd-1", "status": "running"},
            "progress": {"percent": 50, "stage": "moving"}
        }
        jsonschema.validate(instance=doc, schema=schema)

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed")
    def test_event_log_schema_valid(self):
        schema = _load_schema('event_log.schema.json')
        doc = {
            "trace_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": "2025-10-15T08:30:00Z",
            "severity": "INFO",
            "category": "command",
            "message": "accepted"
        }
        jsonschema.validate(instance=doc, schema=schema)

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed")
    def test_error_schema_valid(self):
        schema = _load_schema('error.schema.json')
        bad_code = {
            "code": "ERR_NOT_DEFINED",
            "message": "oops"
        }
        with self.assertRaises(ValidationError):
            jsonschema.validate(instance=bad_code, schema=schema)
        good = {"code": "ERR_TIMEOUT", "message": "timeout"}
        jsonschema.validate(instance=good, schema=schema)


if __name__ == '__main__':
    unittest.main()
