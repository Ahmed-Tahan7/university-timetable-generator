# Timetable Scheduler - Python Port

A complete Python CSP (Constraint Satisfaction Problem) solver for university timetable generation.

## Project Structure

```
timetable_scheduler/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── README.md                  # This file
├── data/
│   └── database.db           # SQLite database (your existing DB)
├── models/
│   ├── __init__.py
│   └── data_models.py        # Data classes (Course, Instructor, etc.)
├── database/
│   ├── __init__.py
│   └── database_manager.py   # Database access layer
├── solver/
│   ├── __init__.py
│   └── csp_solver.py         # CSP solver implementation
└── gui/
    ├── __init__.py
    └── main_window.py        # PyQt6 main window
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Create a virtual environment (recommended)**:
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Place your database**:
   - Copy your `database.db` file to the `data/` directory
   - Or use the file dialog in the application to select any location

## Running the Application

### GUI Mode
```bash
python main.py
```

This opens the PyQt6 graphical interface where you can:
1. Load a database file
2. Solve the timetable scheduling problem
3. View the results
4. Export to JSON

### Core Functionality
- ✅ Complete CSP solver with backtracking
- ✅ Minimum Remaining Values (MRV) heuristic
- ✅ Forward checking for domain reduction
- ✅ Hard constraint enforcement
- ✅ Soft constraint cost calculation
- ✅ Multi-threaded solving (doesn't freeze GUI)

### Constraints Handled
- **Hard Constraints**:
  - No instructor conflicts
  - No room conflicts
  - No group conflicts (same year/group/time)
  - No specialization conflicts
  - Course consistency (same professor for all lecture groups)

- **Soft Constraints**:
  - Minimize early morning classes
  - Minimize multiple sessions per day for same course

### GUI Features
- Load database from file dialog
- Real-time progress updates
- View complete solution
- Export to JSON format
- Monospace output for readability