"""
Audit logging helper module

Provides utilities for creating and managing audit log entries
for security-sensitive operations.
"""

from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
from flask import request
from flask_login import current_user

from WebUI.app import db
from WebUI.app.models import AuditLog


# Severity levels (aligned with EventLog schema)
class AuditSeverity:
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


# Categories (aligned with EventLog schema)
class AuditCategory:
    AUTH = "auth"
    COMMAND = "command"
    AUDIT = "audit"
    ROBOT = "robot"
    PROTOCOL = "protocol"


# Action types for audit logging
class AuditAction:
    # Authentication actions
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    TOKEN_ROTATION = "token_rotation"

    # Authorization actions
    PERMISSION_DENIED = "permission_denied"
    ROLE_CHANGE = "role_change"

    # Command actions
    COMMAND_CREATE = "command_create"
    COMMAND_EXECUTE = "command_execute"
    COMMAND_CANCEL = "command_cancel"

    # Advanced command actions
    ADVANCED_COMMAND_CREATE = "advanced_command_create"
    ADVANCED_COMMAND_APPROVE = "advanced_command_approve"
    ADVANCED_COMMAND_REJECT = "advanced_command_reject"
    ADVANCED_COMMAND_DELETE = "advanced_command_delete"

    # Robot actions
    ROBOT_REGISTER = "robot_register"
    ROBOT_UPDATE = "robot_update"
    ROBOT_DELETE = "robot_delete"
    ROBOT_FIRMWARE_UPDATE = "robot_firmware_update"

    # System actions
    CONFIG_CHANGE = "config_change"
    EMERGENCY_STOP = "emergency_stop"


# Status values
class AuditStatus:
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


def log_audit_event(
    action: str,
    message: str,
    severity: str = AuditSeverity.INFO,
    category: str = AuditCategory.AUDIT,
    trace_id: Optional[str] = None,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    status: str = AuditStatus.SUCCESS,
    context: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Create and save an audit log entry.

    Args:
        action: Action type (use AuditAction constants)
        message: Human-readable message
        severity: Severity level (INFO, WARN, ERROR)
        category: Event category (auth, command, audit, etc.)
        trace_id: Optional trace ID for request tracking
        user_id: Optional user ID (uses current_user if not provided)
        resource_type: Type of resource affected
        resource_id: ID of affected resource
        status: Operation status (success, failure, denied)
        context: Additional context data

    Returns:
        Created AuditLog instance
    """
    # Generate trace_id if not provided
    if trace_id is None:
        trace_id = str(uuid4())

    # Use current user if user_id not provided
    if user_id is None and current_user and current_user.is_authenticated:
        user_id = current_user.id

    # Get request details
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:512]  # Truncate to fit column

    # Create audit log entry
    audit_log = AuditLog(
        trace_id=trace_id,
        timestamp=datetime.utcnow(),
        severity=severity,
        category=category,
        message=message,
        context=context or {},
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status
    )

    db.session.add(audit_log)
    db.session.commit()

    return audit_log


def log_login_attempt(username: str, success: bool, user_id: Optional[int] = None):
    """Log a login attempt."""
    if success:
        log_audit_event(
            action=AuditAction.LOGIN_SUCCESS,
            message=f"User '{username}' logged in successfully",
            severity=AuditSeverity.INFO,
            category=AuditCategory.AUTH,
            user_id=user_id,
            status=AuditStatus.SUCCESS,
            context={'username': username}
        )
    else:
        log_audit_event(
            action=AuditAction.LOGIN_FAILURE,
            message=f"Failed login attempt for user '{username}'",
            severity=AuditSeverity.WARN,
            category=AuditCategory.AUTH,
            user_id=None,  # No user_id for failed login
            status=AuditStatus.FAILURE,
            context={'username': username}
        )


def log_logout(user_id: int, username: str):
    """Log a logout event."""
    log_audit_event(
        action=AuditAction.LOGOUT,
        message=f"User '{username}' logged out",
        severity=AuditSeverity.INFO,
        category=AuditCategory.AUTH,
        user_id=user_id,
        status=AuditStatus.SUCCESS,
        context={'username': username}
    )


def log_registration(username: str, email: str, user_id: int):
    """Log a new user registration."""
    log_audit_event(
        action=AuditAction.REGISTER,
        message=f"New user registered: '{username}'",
        severity=AuditSeverity.INFO,
        category=AuditCategory.AUTH,
        user_id=user_id,
        status=AuditStatus.SUCCESS,
        context={'username': username, 'email': email}
    )


def log_password_reset_request(email: str):
    """Log a password reset request."""
    log_audit_event(
        action=AuditAction.PASSWORD_RESET_REQUEST,
        message=f"Password reset requested for email: {email}",
        severity=AuditSeverity.INFO,
        category=AuditCategory.AUTH,
        status=AuditStatus.SUCCESS,
        context={'email': email}
    )


def log_password_reset_complete(user_id: int, username: str):
    """Log a completed password reset."""
    log_audit_event(
        action=AuditAction.PASSWORD_RESET_COMPLETE,
        message=f"Password reset completed for user '{username}'",
        severity=AuditSeverity.INFO,
        category=AuditCategory.AUTH,
        user_id=user_id,
        status=AuditStatus.SUCCESS,
        context={'username': username}
    )


def log_permission_denied(user_id: int, action: str, resource: str):
    """Log a permission denial."""
    log_audit_event(
        action=AuditAction.PERMISSION_DENIED,
        message=f"Permission denied: user attempted '{action}' on '{resource}'",
        severity=AuditSeverity.WARN,
        category=AuditCategory.AUTH,
        user_id=user_id,
        status=AuditStatus.DENIED,
        context={'attempted_action': action, 'resource': resource}
    )


def log_command_execution(
    user_id: int,
    robot_id: int,
    robot_name: str,
    command: str,
    success: bool
):
    """Log a robot command execution."""
    log_audit_event(
        action=AuditAction.COMMAND_EXECUTE,
        message=f"Command '{command}' executed on robot '{robot_name}'",
        severity=AuditSeverity.INFO if success else AuditSeverity.ERROR,
        category=AuditCategory.COMMAND,
        user_id=user_id,
        resource_type='robot',
        resource_id=str(robot_id),
        status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
        context={'robot_name': robot_name, 'command': command}
    )


def log_advanced_command_action(
    action: str,
    user_id: int,
    command_id: int,
    command_name: str,
    status: str = AuditStatus.SUCCESS
):
    """Log an advanced command action (create, approve, reject, delete)."""
    action_messages = {
        AuditAction.ADVANCED_COMMAND_CREATE: f"Advanced command '{command_name}' created",
        AuditAction.ADVANCED_COMMAND_APPROVE: f"Advanced command '{command_name}' approved",
        AuditAction.ADVANCED_COMMAND_REJECT: f"Advanced command '{command_name}' rejected",
        AuditAction.ADVANCED_COMMAND_DELETE: f"Advanced command '{command_name}' deleted",
    }

    log_audit_event(
        action=action,
        message=action_messages.get(action, f"Advanced command action: {action}"),
        severity=AuditSeverity.INFO,
        category=AuditCategory.AUDIT,
        user_id=user_id,
        resource_type='advanced_command',
        resource_id=str(command_id),
        status=status,
        context={'command_name': command_name}
    )


def log_robot_action(
    action: str,
    user_id: int,
    robot_id: int,
    robot_name: str,
    status: str = AuditStatus.SUCCESS,
    context: Optional[Dict[str, Any]] = None
):
    """Log a robot management action."""
    action_messages = {
        AuditAction.ROBOT_REGISTER: f"Robot '{robot_name}' registered",
        AuditAction.ROBOT_UPDATE: f"Robot '{robot_name}' updated",
        AuditAction.ROBOT_DELETE: f"Robot '{robot_name}' deleted",
        AuditAction.ROBOT_FIRMWARE_UPDATE: f"Firmware update initiated for robot '{robot_name}'",
    }

    log_audit_event(
        action=action,
        message=action_messages.get(action, f"Robot action: {action}"),
        severity=AuditSeverity.INFO,
        category=AuditCategory.ROBOT,
        user_id=user_id,
        resource_type='robot',
        resource_id=str(robot_id),
        status=status,
        context=context or {'robot_name': robot_name}
    )
