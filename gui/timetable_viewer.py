"""
Timetable viewer widget for displaying schedules
"""
import json
from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont


class TimetableViewer(QWidget):    
    def __init__(self):
        super().__init__()
        self.timetable_data = None
        self.days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
        self.time_slots = [] 
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title_label = QLabel("Timetable Viewer")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        self.table_scroll = QScrollArea()
        self.table_scroll.setWidgetResizable(True)
        self.table_scroll.setFrameShape(QFrame.Shape.StyledPanel)
        
        self.table_widget = QTableWidget()
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.setAlternatingRowColors(True)
        self.setup_table_style()
        
        self.table_scroll.setWidget(self.table_widget)
        layout.addWidget(self.table_scroll)
        
        self.status_label = QLabel("Load a timetable.json file to view the schedule")
        self.status_label.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(self.status_label)
    
    def create_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        
        self.load_btn = QPushButton("Load Timetable")
        self.load_btn.clicked.connect(self.load_timetable)
        layout.addWidget(self.load_btn)
        
        layout.addWidget(QLabel("Year:"))
        self.year_combo = QComboBox()
        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        layout.addWidget(self.year_combo)
        
        layout.addWidget(QLabel("Group:"))
        self.group_combo = QComboBox()
        self.group_combo.currentIndexChanged.connect(self.refresh_table)
        layout.addWidget(self.group_combo)
        
        layout.addStretch()
        
        self.year_combo.setEnabled(False)
        self.group_combo.setEnabled(False)
        
        return panel
    
    def setup_table_style(self):
        self.table_widget.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 5px;
                border: 1px solid #e0e0e0;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: 1px solid #1976D2;
            }
        """)
    
    def load_timetable(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Timetable",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if not data.get('success', False):
                QMessageBox.warning(
                    self,
                    "Invalid Timetable",
                    "The timetable file indicates no valid schedule was found."
                )
                return
            
            self.timetable_data = data
            self.extract_time_slots()
            self.populate_filters()
            self.refresh_table()
            
            stats = data.get('stats', {})
            self.status_label.setText(
                f"Loaded: {stats.get('totalCourses', 0)} courses, "
                f"{stats.get('totalSessions', 0)} sessions, "
                f"Solved in {stats.get('solveTime', 0):.2f}s"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load timetable:\n{str(e)}"
            )
    
    def extract_time_slots(self):
        time_slots_set = set()        
        schedule = self.timetable_data.get('schedule', {})
        for year_data in schedule.values():
            for group_data in year_data.values():
                for session in group_data:
                    time_slots_set.add(session.get('time', ''))
        
        self.time_slots = sorted(list(time_slots_set), key=self.parse_time)
    
    def parse_time(self, time_str: str) -> int:
        try:
            start = time_str.split(' - ')[0].strip()
            time_part = start[:-2]
            period = start[-2:]
            
            hours, mins = map(int, time_part.split(':'))
            if period == 'PM' and hours != 12:
                hours += 12
            elif period == 'AM' and hours == 12:
                hours = 0
            
            return hours * 60 + mins
        except:
            return 0
    
    def populate_filters(self):
        if not self.timetable_data:
            return
        
        schedule = self.timetable_data.get('schedule', {})
        
        self.year_combo.clear()
        years = sorted([int(y) for y in schedule.keys()])
        for year in years:
            self.year_combo.addItem(f"Year {year}", year)
        
        self.year_combo.setEnabled(True)
        self.on_year_changed()
    
    def on_year_changed(self):
        if not self.timetable_data:
            return
        
        year = self.year_combo.currentData()
        if year is None:
            return

        schedule = self.timetable_data.get('schedule', {})
        year_data = schedule.get(str(year), {})
        
        self.group_combo.clear()
        groups = sorted(year_data.keys(), key=self.sort_group_key)
        for group in groups:
            self.group_combo.addItem(group, group)
        
        self.group_combo.setEnabled(True)
        self.refresh_table()

    def sort_group_key(self, group: str):
        if group.startswith('G') and len(group) == 2:
            return (0, int(group[1]))
        else:
            return (1, group)
    
    def refresh_table(self):
        if not self.timetable_data:
            return
        
        year = self.year_combo.currentData()
        group = self.group_combo.currentData()
        
        if year is None or group is None:
            return
        
        schedule = self.timetable_data.get('schedule', {})
        year_data = schedule.get(str(year), {})
        sessions = year_data.get(group, [])
        
        self.display_timetable(sessions)
    
    def display_timetable(self, sessions: List[Dict]):
        num_rows = len(self.time_slots)
        num_cols = len(self.days)
        
        self.table_widget.setRowCount(num_rows)
        self.table_widget.setColumnCount(num_cols)
        
        self.table_widget.setHorizontalHeaderLabels(self.days)
        self.table_widget.setVerticalHeaderLabels(self.time_slots)
        
        self.table_widget.clearContents()
        
        schedule_grid = {}
        for session in sessions:
            day = session.get('day', '')
            time = session.get('time', '')
            
            key = (day, time)
            if key not in schedule_grid:
                schedule_grid[key] = []
            schedule_grid[key].append(session)
        
        for row, time_slot in enumerate(self.time_slots):
            for col, day in enumerate(self.days):
                key = (day, time_slot)
                
                if key in schedule_grid:
                    cell_text = self.format_cell(schedule_grid[key])
                    item = QTableWidgetItem(cell_text)
                    
                    if any('Lab' in s.get('type', '') for s in schedule_grid[key]):
                        item.setBackground(QColor(255, 243, 205)) 
                    else:
                        item.setBackground(QColor(232, 245, 233)) 
                    
                    if any('Full Day' in s.get('type', '') for s in schedule_grid[key]):
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    
                    item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                    self.table_widget.setItem(row, col, item)
                else:
                    item = QTableWidgetItem("")
                    item.setBackground(QColor(250, 250, 250))
                    self.table_widget.setItem(row, col, item)
        
        header = self.table_widget.horizontalHeader()
        for i in range(num_cols):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        v_header = self.table_widget.verticalHeader()
        for i in range(num_rows):
            v_header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
    
    def format_cell(self, sessions: List[Dict]) -> str:
        lines = []
        
        for session in sessions:
            code = session.get('code', '')
            name = session.get('name', '')
            session_type = session.get('type', '')
            instructor = session.get('instructor', '')
            room = session.get('room', '')
            cell_lines = [
                f"{code} - {name}",
                f"  {session_type}",
                f"  👤 {instructor}",
                f"  🚪 {room}"
            ]
            
            lines.extend(cell_lines)
            
            if len(sessions) > 1 and session != sessions[-1]:
                lines.append("─" * 30)
        
        return "\n".join(lines)
    
    def load_from_result(self, json_data: dict):
        if not json_data.get('success', False):
            self.status_label.setText("No valid schedule to display")
            return
        
        self.timetable_data = json_data
        self.extract_time_slots()
        self.populate_filters()
        self.refresh_table()
        
        stats = json_data.get('stats', {})
        self.status_label.setText(
            f"Displaying: {stats.get('totalCourses', 0)} courses, "
            f"{stats.get('totalSessions', 0)} sessions"
        )