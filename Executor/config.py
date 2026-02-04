# Standard configuration for Executor

class ExecutorConfig:
    LOG_LEVEL = "INFO"
    EXECUTION_TIMEOUT = 300  # Timeout in seconds for command execution
    RETRY_ATTEMPTS = 3       # Number of retry attempts for failed commands
    LOG_DIR = "/var/log/executor"

    @staticmethod
    def display():
        return {
            "LOG_LEVEL": ExecutorConfig.LOG_LEVEL,
            "EXECUTION_TIMEOUT": ExecutorConfig.EXECUTION_TIMEOUT,
            "RETRY_ATTEMPTS": ExecutorConfig.RETRY_ATTEMPTS,
            "LOG_DIR": ExecutorConfig.LOG_DIR,
        }