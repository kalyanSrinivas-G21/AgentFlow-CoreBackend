# backend/app/common/exceptions.py
class InvalidTaskStateTransition(Exception):
    def __init__(self, current_state: str, target_state: str, task_id: str):
        self.current_state = current_state
        self.target_state = target_state
        self.task_id = str(task_id)
        self.message = f"Invalid transition from {current_state} to {target_state} for task {task_id}"
        super().__init__(self.message)