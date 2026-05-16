from app.models.task import Task

class TaskManager:
    def __init__(self):
        raise NotImplementedError
    
    def create_task(self, data: dict) -> int:
        raise NotImplementedError

    def update_task(self, task_id: int, data: dict) -> None:
        raise NotImplementedError

    def delete_task(self, task_id: int) -> None:
        raise NotImplementedError
    
    def get_task(self, task_id: int) -> Task | None:
        raise NotImplementedError
    
    def list_tasks(self, filters: dict | None = None) -> list[Task]:
        raise NotImplementedError
    
    def mark_done(self, task_id: int) -> None:
        raise NotImplementedError
    
    def list_by_course(self, course_id: int) -> list[Task]:
        raise NotImplementedError
    
    def list_by_status(self, status: str) -> list[Task]:
        raise NotImplementedError
