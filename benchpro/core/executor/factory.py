def create_executor(settings: Settings) -> Executor:
    """Create an executor based on settings.

    Args:
        settings: Settings instance

    Returns:
        Executor: Created executor instance

    Raises:
        ExecutorError: If executor type is invalid
    """
    # Get executor config from settings
    executor_config = settings.get("executor", {})
    executor_type = executor_config.get("type", "local")

    # Create executor based on type
    if executor_type == "local":
        return LocalExecutor(settings)
    elif executor_type == "slurm":
        raise ExecutorError("Slurm executor not yet implemented")
    else:
        raise ExecutorError(f"Invalid executor type: {executor_type}")

def create_local_executor(settings: Settings) -> LocalExecutor:
    """Create a local executor.

    Args:
        settings: Settings instance

    Returns:
        LocalExecutor: Created local executor instance
    """
    return LocalExecutor(settings) 