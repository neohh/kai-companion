"""
core.storage — хранилище данных задач и проектов.
Владельцы: DataManager.
Зависимости: json, pathlib; datetime.
"""
import json
from pathlib import Path
from datetime import datetime


class DataManager:
    def __init__(self):
        self.data_dir = Path.home() / "AppData" / "Roaming" / "pixel"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "data.json"
        self.data = self._load()

    def _load(self):
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"projects": [], "next_project_id": 1, "next_task_id": 1}

    def save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Save error:", e)

    def get_projects(self):
        return self.data["projects"]

    def get_project(self, project_id):
        for p in self.data["projects"]:
            if p["id"] == project_id:
                return p
        return None

    def create_project(self, name):
        project = {"id": self.data["next_project_id"], "name": name,
                   "created_at": datetime.now().isoformat(), "tasks": []}
        self.data["projects"].append(project)
        self.data["next_project_id"] += 1
        self.save()
        return project

    def rename_project(self, project_id, name):
        p = self.get_project(project_id)
        if p:
            p["name"] = name
            self.save()

    def delete_project(self, project_id):
        self.data["projects"] = [p for p in self.data["projects"] if p["id"] != project_id]
        self.save()

    def get_task(self, project_id, task_id):
        p = self.get_project(project_id)
        if not p:
            return None
        for t in p["tasks"]:
            if t["id"] == task_id:
                return t
        return None

    def create_task(self, project_id, name, steps):
        p = self.get_project(project_id)
        if not p:
            return None
        task = {"id": self.data["next_task_id"], "name": name, "steps": steps,
                "done": False, "created_at": datetime.now().isoformat()}
        p["tasks"].append(task)
        self.data["next_task_id"] += 1
        self.save()
        return task

    def rename_task(self, project_id, task_id, name):
        t = self.get_task(project_id, task_id)
        if t:
            t["name"] = name
            self.save()

    def delete_task(self, project_id, task_id):
        p = self.get_project(project_id)
        if p:
            p["tasks"] = [t for t in p["tasks"] if t["id"] != task_id]
            self.save()

    def update_task_steps(self, project_id, task_id, steps):
        t = self.get_task(project_id, task_id)
        if t:
            t["steps"] = steps
            self.save()

    def toggle_task_done(self, project_id, task_id):
        t = self.get_task(project_id, task_id)
        if t:
            t["done"] = not t["done"]
            self.save()
            return t["done"]
        return False
