def run_workflow_plan(workflow_key, db_path=None):
    """Create and execute a persisted workflow track for a known workflow key."""
    from modules.task_catalog import TaskCatalog
    from modules.task_orchestration import TaskExecutor
    from modules.workflow_handlers import WORKFLOW_HANDLERS

    track = TaskCatalog(db_path=db_path).plan(workflow_key)

    if workflow_key in WORKFLOW_HANDLERS:
        handler = WORKFLOW_HANDLERS[workflow_key]
        executor = TaskExecutor(db_path=db_path)

        last_result = ""
        planned_tasks = track["tasks"]
        for task_index, task in enumerate(planned_tasks):
            from modules import hud

            steps_state = [
                {
                    "title": planned_task["title"],
                    "status": (
                        "done"
                        if index < task_index
                        else "running"
                        if index == task_index
                        else "pending"
                    ),
                }
                for index, planned_task in enumerate(planned_tasks)
            ]
            hud.update_task_progress(track["name"], steps_state)
            res = executor.execute_task(
                track["track_id"],
                task["task_id"],
                task_handler=lambda t, c: handler(t, c),
            )
            if not res or res.get("status") != "COMPLETED":
                raise RuntimeError(
                    (res.get("error") if res else None)
                    or f"Workflow task '{task['title']}' did not complete."
                )
            steps_state[task_index]["status"] = "done"
            hud.update_task_progress(track["name"], steps_state)
            last_result = res.get("result") or "Completed"

        return {
            "message": f"Executed {track['name']} successfully. Final result: {last_result}",
            "track_name": track["name"],
            "track_id": track["track_id"],
        }

    return {
        "message": (
            f"Planned {track['name']} with {len(track['tasks'])} tasks. "
            f"Track ID: {track['track_id']}."
        ),
        "track_name": track["name"],
        "track_id": track["track_id"],
    }
