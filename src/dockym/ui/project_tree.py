from __future__ import annotations

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Signal, Qt

from dockym.models.project import Project


class ProjectTree(QTreeWidget):
    project_selected = Signal(object)
    service_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Proyectos")
        self.setMinimumWidth(220)
        self.setIndentation(14)
        self._project_map: dict[str, QTreeWidgetItem] = {}
        self.itemClicked.connect(self._on_item_clicked)

    def load_projects(self, projects: list[Project]) -> None:
        self.clear()
        self._project_map.clear()

        for proj in projects:
            status_char = "·"
            if proj.running_count == proj.total_count and proj.total_count > 0:
                status_char = "●"
            elif proj.running_count > 0:
                status_char = "◐"
            elif proj.total_count > 0:
                status_char = "○"

            label = f"{status_char}  {proj.name}  ·  {proj.running_count}/{proj.total_count}"
            proj_item = QTreeWidgetItem(self, [label])
            proj_item.setData(0, Qt.ItemDataRole.UserRole, ("project", proj.name))
            self._project_map[proj.name] = proj_item

            for svc in proj.services:
                svc_status = "●" if svc.status == "running" else "○" if svc.status == "exited" else "◌"
                svc_label = f"   {svc_status}  {svc.name}"
                svc_item = QTreeWidgetItem(proj_item, [svc_label])
                svc_item.setData(0, Qt.ItemDataRole.UserRole,
                                 ("service", proj.name, svc.name))

            proj_item.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind = data[0]
        screen = self.window()
        if not hasattr(screen, 'projects'):
            return

        projects = screen.projects
        if kind == "project":
            for p in projects:
                if p.name == data[1]:
                    self.project_selected.emit(p)
                    break
        elif kind == "service":
            for p in projects:
                if p.name == data[1]:
                    self.project_selected.emit(p)
                    for s in p.services:
                        if s.name == data[2]:
                            self.service_selected.emit(s)
                            break
                    break
