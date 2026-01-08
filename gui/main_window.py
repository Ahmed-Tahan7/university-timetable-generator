import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QFileDialog, QMessageBox, 
    QProgressBar, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from database.database_manager import DatabaseManager
from solver.csp_solver import CSPSolver, min_to_12_hour
from gui.timetable_viewer import TimetableViewer


class SolverThread(QThread):
    finished = pyqtSignal(object)
    progress = pyqtSignal(str)
    
    def __init__(self, solver):
        super().__init__()
        self.solver = solver
    
    def run(self):
        try:
            self.progress.emit("Building variables")
            self.solver.build_lecture_variables()
            
            self.progress.emit("Building domains")
            self.solver.build_domains()
            
            self.progress.emit("Solving CSP...")
            result = self.solver.solve()
            
            self.finished.emit(result)
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
            self.finished.emit(None)


class SolverTab(QWidget):    
    def __init__(self):
        super().__init__()
        self.db_manager = None
        self.solver = None
        self.result = None
        self.solver_thread = None
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title_label = QLabel("Timetable Generation CSP Solver")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        button_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load Database")
        self.load_btn.clicked.connect(self.load_database)
        button_layout.addWidget(self.load_btn)
        
        self.solve_btn = QPushButton("Solve")
        self.solve_btn.clicked.connect(self.solve)
        self.solve_btn.setEnabled(False)
        button_layout.addWidget(self.solve_btn)
        
        self.export_btn = QPushButton("Export JSON")
        self.export_btn.clicked.connect(self.export_json)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self.status_label)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.output_text)
    
    def log(self, message: str):
        self.output_text.append(message)
    
    def load_database(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Database File",
            "",
            "Database Files (*.db);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            self.db_manager = DatabaseManager(file_path)
            
            courses = self.db_manager.get_courses()
            instructors = self.db_manager.get_instructors()
            rooms = self.db_manager.get_rooms()
            time_slots = self.db_manager.get_time_slots()
            
            self.log("Timetable Generation CSP Solver")
            self.log(f"Loaded:\n{len(courses)} courses, {len(instructors)} instructors, "
                    f"{len(rooms)} rooms, {len(time_slots)} time slots\n")
            
            filtered_courses = [c for c in courses if 1 <= c.year <= 4]
            self.log(f"Scheduling {len(filtered_courses)} courses (Years 1 - 4)\n")
            
            instructor_courses = self.db_manager.get_instructor_courses()
            
            self.solver = CSPSolver(
                filtered_courses,
                instructors,
                instructor_courses,
                rooms,
                time_slots
            )
            
            self.solve_btn.setEnabled(True)
            self.status_label.setText(f"Database loaded: {Path(file_path).name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load database:\n{str(e)}")
            self.log(f"Error loading database: {str(e)}")
    
    def solve(self):
        if not self.solver:
            return
        
        self.solve_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.solver_thread = SolverThread(self.solver)
        self.solver_thread.progress.connect(self.on_progress)
        self.solver_thread.finished.connect(self.on_solve_finished)
        self.solver_thread.start()
    
    def on_progress(self, message: str):
        self.status_label.setText(message)
        self.log(message)
    
    def on_solve_finished(self, result):
        self.progress_bar.setVisible(False)
        self.solve_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        
        if result is None:
            self.status_label.setText("Solving failed")
            return
        
        self.result = result
        
        if result.success:
            self.log("\n" + "="*50)
            self.log("SOLUTION FOUND!")
            self.log("="*50)
            self.solver.print_result(result)
            self.log(f"\nSUCCESS | Hard violations: {result.hard_violations}")
            self.status_label.setText(f"Solution found in {result.solve_seconds:.2f}s")
            self.export_btn.setEnabled(True)
        else:
            self.log("\n" + "="*50)
            self.log("NO SOLUTION FOUND")
            self.log("="*50)
            self.log(f"FAILED | No valid schedule found")
            self.status_label.setText("No solution found")
            QMessageBox.warning(self, "No Solution", "Could not find a valid schedule.")
    
    def export_json(self):
        """Export result to JSON"""
        if not self.result or not self.result.success:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Timetable",
            "timetable.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            json_data = self.generate_json()
            
            with open(file_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            self.log(f"\nJSON exported to: {file_path}")
            self.status_label.setText(f"Exported to: {Path(file_path).name}")
            QMessageBox.information(self, "Success", "Timetable exported successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export JSON:\n{str(e)}")
            self.log(f"Error exporting JSON: {str(e)}")
    
    def generate_json(self) -> dict:
        room_index = {r.id: r for r in self.solver.rooms}
        instructor_names = {ins.id: ins.name for ins in self.solver.instructors}
        course_names = {c.id: c.name for c in self.solver.courses}
        
        organized = {}
        
        for v in self.solver.get_variables():
            if v.var_id not in self.result.assignments:
                continue
            
            a = self.result.assignments[v.var_id]
            ts = self.solver.time_slots[a.timeslot_index]
            rm = room_index.get(a.room_id)
            
            cname = course_names.get(v.course_id, v.course_id)
            ins_name = instructor_names.get(a.instructor_id, a.instructor_id) if a.instructor_id else "null"
            
            if v.year <= 2:
                group_key = f"G{v.group_id}"
            else:
                group_key = v.specialization if v.specialization else "G1"
            
            if v.session_type == "LECTURE":
                if (v.year == 3 or v.year == 4) and v.specialization:
                    session_type = f"{v.specialization} Lecture"
                elif v.section_id > 0 and v.group_id > 0:
                    session_type = f"G{v.group_id} Section {v.section_id}"
                else:
                    session_type = f"G{v.group_id} Lecture"
            elif v.session_type == "LAB":
                if v.specialization and v.section_id > 0:
                    session_type = f"{v.specialization} Lab"
                elif v.group_id > 0 and v.section_id > 0:
                    session_type = f"G{v.group_id} S{v.section_id} Lab"
                else:
                    session_type = "Lab"
                if v.is_full_day:
                    session_type += " (Full Day)"
            else:
                session_type = v.session_type
            
            # Time strings
            if v.is_full_day:
                time_str = "09:00AM - 03:45PM"
                start_time = "09:00AM"
                end_time = "03:45PM"
            else:
                start_time = min_to_12_hour(ts.start_min)
                end_time = min_to_12_hour(ts.end_min)
                time_str = f"{start_time} - {end_time}"
            
            session_data = {
                "code": v.course_id,
                "name": cname,
                "type": session_type,
                "day": ts.day,
                "time": time_str,
                "startTime": start_time,
                "endTime": end_time,
                "instructor": ins_name,
                "room": f"{rm.room_name if rm else a.room_id} ({rm.building if rm else ''})"
            }
            
            # Organize by year and group
            if v.year not in organized:
                organized[v.year] = {}
            if group_key not in organized[v.year]:
                organized[v.year][group_key] = []
            
            organized[v.year][group_key].append(session_data)
        
        json_data = {
            "success": True,
            "stats": {
                "totalCourses": len([c for c in self.solver.courses if 1 <= c.year <= 4]),
                "totalSessions": len(self.solver.get_variables()),
                "violations": self.result.hard_violations,
                "solveTime": self.result.solve_seconds
            },
            "schedule": organized
        }
        
        return json_data
    
    def get_result_json(self) -> dict:
        """Get the generated JSON data"""
        if self.result and self.result.success:
            return self.generate_json()
        return None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Timetable Scheduler - CSP Solver")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        
        self.solver_tab = SolverTab()
        self.tabs.addTab(self.solver_tab, "Solver")
        
        self.viewer_tab = TimetableViewer()
        self.tabs.addTab(self.viewer_tab, "Timetable Viewer")
        
        button_layout = QHBoxLayout()
        self.view_result_btn = QPushButton("View Current Solution")
        self.view_result_btn.clicked.connect(self.view_current_solution)
        self.view_result_btn.setEnabled(False)
        button_layout.addStretch()
        button_layout.addWidget(self.view_result_btn)
        self.solver_tab.solver_thread = None  
        
        layout.addWidget(self.tabs)
        layout.addLayout(button_layout)
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
    
    def on_tab_changed(self, index):
        if hasattr(self.solver_tab, 'result') and self.solver_tab.result:
            if self.solver_tab.result.success:
                self.view_result_btn.setEnabled(True)
    
    def view_current_solution(self):
        json_data = self.solver_tab.get_result_json()
        if json_data:
            self.viewer_tab.load_from_result(json_data)
            self.tabs.setCurrentWidget(self.viewer_tab)
            QMessageBox.information(
                self,
                "Loaded",
                "Current solution loaded into timetable viewer!"
            )
        else:
            QMessageBox.warning(
                self,
                "No Solution",
                "Please solve a timetable first before viewing."
            )