from ortools.sat.python import cp_model
from src.data_loader import DataLoader
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import pandas as pd
import time
import os


class TimetableSession:
    """Represents a single timetable session (lecture/lab/tutorial)"""
    
    def __init__(self, course_id: str, section_id: str, session_type: str, 
                 session_num: int, timeslot_id: int, room_id: str, 
                 instructor_id: str, is_double: bool = False):
        self.course_id = course_id
        self.section_id = section_id
        self.session_type = session_type  # 'LECTURE', 'LAB', 'TUTORIAL'
        self.session_num = session_num
        self.timeslot_id = timeslot_id
        self.timeslot_id_2 = timeslot_id + 1 if is_double else None  # For labs
        self.room_id = room_id
        self.instructor_id = instructor_id
        self.is_double = is_double


class CSPTimetableSolver:
    """
    Constraint Satisfaction Problem solver for timetable generation.
    Uses Google OR-Tools CP-SAT solver.
    """
    
    def __init__(self, data_loader: DataLoader, target_year: int):
        """
        Initialize the CSP solver.
        
        Args:
            data_loader: Loaded data from DataLoader
            target_year: Year to generate timetable for (1, 2, 3, or 4)
        """
        self.loader = data_loader
        self.target_year = target_year
        
        # OR-Tools model and solver
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Configure solver parameters
        self.solver.parameters.num_search_workers = 8  # Parallel solving
        self.solver.parameters.max_time_in_seconds = 600  # 10 minutes timeout
        self.solver.parameters.log_search_progress = True
        
        # Decision variables
        self.session_vars = []  # List of (var, session_info) tuples
        
        # Penalty variables for soft constraints
        self.penalty_vars = []
        
        # Results
        self.solution = []  # List of TimetableSession objects
        self.solve_time = 0
        self.status = None
    
    def create_variables(self):
        """Create decision variables for all possible session assignments"""
        print(f"\n[Year {self.target_year}] Creating decision variables...")
        
        courses = self.loader.get_courses_for_year(self.target_year)
        var_count = 0
        skipped = []
        
        for course_id in courses:
            course = self.loader.courses[course_id]
            instructors = self.loader.get_qualified_instructors(course_id)
            
            if not instructors:
                skipped.append(f"{course_id} (no instructors)")
                continue
            
            sections = self.loader.get_sections_for_course(course_id)
            if not sections:
                skipped.append(f"{course_id} (no sections)")
                continue
            
            # Create variables for LECTURES (90 min slots)
            if course['has_lecture']:
                var_count += self._create_lecture_vars(course_id, course, sections, instructors)
            
            # Create variables for TUTORIALS (45 min slots)
            if course['has_tutorial']:
                var_count += self._create_tutorial_vars(course_id, course, sections, instructors)
            
            # Create variables for LABS (consecutive 45 min slots = 90 min)
            if course['has_lab']:
                var_count += self._create_lab_vars(course_id, course, sections, instructors)
        
        print(f"  ✓ Created {var_count} decision variables")
        if skipped:
            print(f"  ⚠ Skipped: {', '.join(skipped[:5])}")
            if len(skipped) > 5:
                print(f"    ... and {len(skipped) - 5} more")
    
    def _create_lecture_vars(self, course_id: str, course: dict, 
                            sections: List[str], instructors: List[str]) -> int:
        """Create variables for lecture sessions (90 min slots)"""
        var_count = 0
        
        # Lectures use 90-minute slots
        lecture_slots = self.loader.get_timeslots_by_duration(90)
        
        # Get suitable rooms - lectures need large rooms
        max_capacity = max(self.loader.sections[s]['capacity'] for s in sections)
        suitable_rooms = self.loader.get_suitable_rooms('Lecture', min_capacity=int(max_capacity * 0.7))
        
        if not suitable_rooms:
            return 0
        
        # Create variables for each lecture session
        for session_num in range(course['lecture_sessions']):
            for slot_id in lecture_slots:
                for room_id in suitable_rooms[:75]:  # Limit to reduce complexity
                    for instructor_id in instructors:
                        # Check instructor availability
                        if not self.loader.is_instructor_available(instructor_id, slot_id):
                            continue
                        
                        var_name = f"L_{course_id}_S{session_num}_T{slot_id}_R{room_id}_I{instructor_id}"
                        var = self.model.NewBoolVar(var_name)
                        
                        session_info = {
                            'course_id': course_id,
                            'sections': sections,  # All sections attend together
                            'session_type': 'LECTURE',
                            'session_num': session_num,
                            'slot_id': slot_id,
                            'room_id': room_id,
                            'instructor_id': instructor_id,
                            'is_double': False
                        }
                        
                        self.session_vars.append((var, session_info))
                        var_count += 1
        
        return var_count
    
    def _create_tutorial_vars(self, course_id: str, course: dict,
                             sections: List[str], instructors: List[str]) -> int:
        """Create variables for tutorial sessions (45 min slots)"""
        var_count = 0
        
        # Tutorials use 45-minute slots
        tutorial_slots = self.loader.get_timeslots_by_duration(45)
        
        # Each section has separate tutorial
        for section_id in sections:
            section = self.loader.sections[section_id]
            suitable_rooms = self.loader.get_suitable_rooms('Lecture', min_capacity=section['capacity'])
            
            if not suitable_rooms:
                continue
            
            for session_num in range(course['tutorial_sessions']):
                for slot_id in tutorial_slots:
                    for room_id in suitable_rooms[:25]:  # Limit rooms
                        for instructor_id in instructors:
                            if not self.loader.is_instructor_available(instructor_id, slot_id):
                                continue
                            
                            var_name = f"T_{course_id}_{section_id}_S{session_num}_T{slot_id}_R{room_id}_I{instructor_id}"
                            var = self.model.NewBoolVar(var_name)
                            
                            session_info = {
                                'course_id': course_id,
                                'section_id': section_id,
                                'session_type': 'TUTORIAL',
                                'session_num': session_num,
                                'slot_id': slot_id,
                                'room_id': room_id,
                                'instructor_id': instructor_id,
                                'is_double': False
                            }
                            
                            self.session_vars.append((var, session_info))
                            var_count += 1
        
        return var_count
    
    def _create_lab_vars(self, course_id: str, course: dict,
                    sections: List[str], instructors: List[str]) -> int:
        """Create variables for lab sessions (90 min slots OR consecutive 45 min)"""
        var_count = 0
        
        # Try to use 90-minute slots first (easier to schedule)
        lab_slots_90 = self.loader.get_timeslots_by_duration(90)
        
        # Also get consecutive 45-min pairs as backup
        consecutive_pairs = self.loader.find_consecutive_slots(duration=45)

        
        if not consecutive_pairs:
            return 0
        
        # Each section has separate lab
        for section_id in sections:
            section = self.loader.sections[section_id]
            suitable_rooms = self.loader.get_suitable_rooms('Lab', min_capacity=section['capacity'])
        
            if not suitable_rooms:
                continue
        
        for session_num in range(course['lab_sessions']):
            # OPTION 1: Use 90-minute slots
            for slot_id in lab_slots_90:
                for room_id in suitable_rooms[:25]:
                    for instructor_id in instructors:
                        if not self.loader.is_instructor_available(instructor_id, slot_id):
                            continue
                        
                        var_name = f"B_{course_id}_{section_id}_S{session_num}_T{slot_id}_R{room_id}_I{instructor_id}"
                        var = self.model.NewBoolVar(var_name)
                        
                        session_info = {
                            'course_id': course_id,
                            'section_id': section_id,
                            'session_type': 'LAB',
                            'session_num': session_num,
                            'slot_id': slot_id,
                            'room_id': room_id,
                            'instructor_id': instructor_id,
                            'is_double': False  # Single 90-min slot
                        }
                        
                        self.session_vars.append((var, session_info))
                        var_count += 1
            
            # OPTION 2: Use consecutive 45-min pairs (keep existing code)
            for slot1_id, slot2_id in consecutive_pairs:
                    for room_id in suitable_rooms[:10]:  # Fewer lab rooms
                        for instructor_id in instructors:
                            # Check instructor available for both slots
                            if not (self.loader.is_instructor_available(instructor_id, slot1_id) and
                                   self.loader.is_instructor_available(instructor_id, slot2_id)):
                                continue
                            
                            var_name = f"B_{course_id}_{section_id}_S{session_num}_T{slot1_id}-{slot2_id}_R{room_id}_I{instructor_id}"
                            var = self.model.NewBoolVar(var_name)
                            
                            session_info = {
                                'course_id': course_id,
                                'section_id': section_id,
                                'session_type': 'LAB',
                                'session_num': session_num,
                                'slot_id': slot1_id,
                                'slot_id_2': slot2_id,
                                'room_id': room_id,
                                'instructor_id': instructor_id,
                                'is_double': True
                            }
                            
                            self.session_vars.append((var, session_info))
                            var_count += 1
        
        return var_count
    
    def add_hard_constraints(self):
        """Add hard constraints that MUST be satisfied"""
        print(f"\n[Year {self.target_year}] Adding hard constraints...")
        
        constraint_count = 0
        
        # Constraint 1: Each session must be scheduled exactly once
        constraint_count += self._add_session_assignment_constraints()
        
        # Constraint 2: Room conflicts - no room used twice at same time
        constraint_count += self._add_room_conflict_constraints()
        
        # Constraint 3: Instructor conflicts - no instructor teaches twice at same time
        constraint_count += self._add_instructor_conflict_constraints()
        
        # Constraint 4: Section conflicts - students can't be in two places at once
        constraint_count += self._add_section_conflict_constraints()
        
        print(f"  ✓ Added {constraint_count} hard constraints")
    
    def _add_session_assignment_constraints(self) -> int:
        """Each session must be assigned exactly once"""
        count = 0
        
        # Group variables by (course, section/sections, type, session_num)
        session_groups = defaultdict(list)
        
        for var, info in self.session_vars:
            if info['session_type'] == 'LECTURE':
                # Lectures: group by course and session number
                key = (info['course_id'], 'ALL', info['session_type'], info['session_num'])
            else:
                # Labs/Tutorials: group by course, section, and session number
                key = (info['course_id'], info['section_id'], info['session_type'], info['session_num'])
            
            session_groups[key].append(var)
        
        # Each group must have exactly one assignment
        for key, vars_list in session_groups.items():
            self.model.Add(sum(vars_list) == 1)
            count += 1
        
        return count
    
    def _add_room_conflict_constraints(self) -> int:
        """No room can be used by multiple sessions at the same time"""
        count = 0
        
        # Group by (room, timeslot)
        room_slot_usage = defaultdict(list)
        
        for var, info in self.session_vars:
            room_slot_usage[(info['room_id'], info['slot_id'])].append(var)
            
            # For labs (double slots), also block the second slot
            if info['is_double']:
                room_slot_usage[(info['room_id'], info['slot_id_2'])].append(var)
        
        # At most one session per room per slot
        for key, vars_list in room_slot_usage.items():
            if len(vars_list) > 1:
                self.model.Add(sum(vars_list) <= 1)
                count += 1
        
        return count
    
    def _add_instructor_conflict_constraints(self) -> int:
        """No instructor can teach multiple sessions at the same time"""
        count = 0
        
        # Group by (instructor, timeslot)
        instructor_slot_usage = defaultdict(list)
        
        for var, info in self.session_vars:
            instructor_slot_usage[(info['instructor_id'], info['slot_id'])].append(var)
            
            # For labs, also block the second slot
            if info['is_double']:
                instructor_slot_usage[(info['instructor_id'], info['slot_id_2'])].append(var)
        
        # At most one session per instructor per slot
        for key, vars_list in instructor_slot_usage.items():
            if len(vars_list) > 1:
                self.model.Add(sum(vars_list) <= 1)
                count += 1
        
        return count
    
    def _add_section_conflict_constraints(self) -> int:
        """Students in a section cannot have overlapping classes"""
        count = 0
        
        sections = self.loader.get_sections_for_year(self.target_year)
        
        for section_id in sections:
            # Group by timeslot for this section
            section_slot_usage = defaultdict(list)
            
            for var, info in self.session_vars:
                # Check if this session involves this section
                section_affected = False
                
                if info['session_type'] == 'LECTURE':
                    # Lectures affect all sections taking the course
                    if section_id in info['sections']:
                        section_affected = True
                else:
                    # Labs/Tutorials are section-specific
                    if info.get('section_id') == section_id:
                        section_affected = True
                
                if section_affected:
                    section_slot_usage[info['slot_id']].append(var)
                    
                    if info['is_double']:
                        section_slot_usage[info['slot_id_2']].append(var)
            
            # At most one session per slot for this section
            for slot_id, vars_list in section_slot_usage.items():
                if len(vars_list) > 1:
                    self.model.Add(sum(vars_list) <= 1)
                    count += 1
        
        return count
    
    def add_soft_constraints(self):
        """Add soft constraints for optimization (preferences)"""
        print(f"\n[Year {self.target_year}] Adding soft constraints...")
        
        penalty_count = 0
        
        # Penalize early morning slots (before 10:30 AM)
        for var, info in self.session_vars:
            slot = self.loader.timeslots[info['slot_id']]
            
            # Check if early morning
            if '9:00' in slot['start_time']:
                penalty = self.model.NewBoolVar(f"penalty_early_{var.Name()}")
                self.model.Add(var == 1).OnlyEnforceIf(penalty)
                self.model.Add(var == 0).OnlyEnforceIf(penalty.Not())
                self.penalty_vars.append(penalty)
                penalty_count += 1
        
        # Minimize penalties
        if self.penalty_vars:
            self.model.Minimize(sum(self.penalty_vars))
        
        print(f"  ✓ Added {penalty_count} soft constraint penalties")
    
    def solve(self) -> bool:
        """
        Solve the CSP problem.
        
        Returns:
            bool: True if solution found, False otherwise
        """
        print(f"\n[Year {self.target_year}] Solving CSP...")
        print("=" * 70)
        
        start_time = time.time()
        self.status = self.solver.Solve(self.model)
        self.solve_time = time.time() - start_time
        
        print(f"\n  Solver finished in {self.solve_time:.2f} seconds")
        print(f"  Status: {self.solver.StatusName(self.status)}")
        
        if self.status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            print(f"  ✓ Solution found!")
            print(f"    Objective value: {self.solver.ObjectiveValue()}")
            print(f"    Branches: {self.solver.NumBranches()}")
            print(f"    Conflicts: {self.solver.NumConflicts()}")
            
            self._extract_solution()
            return True
        else:
            print(f"  ✗ No feasible solution found")
            return False
    
    def _extract_solution(self):
        """Extract the solution from the solver"""
        self.solution = []
        
        for var, info in self.session_vars:
            if self.solver.BooleanValue(var):
                session = TimetableSession(
                    course_id=info['course_id'],
                    section_id=info.get('section_id', 'ALL'),
                    session_type=info['session_type'],
                    session_num=info['session_num'],
                    timeslot_id=info['slot_id'],
                    room_id=info['room_id'],
                    instructor_id=info['instructor_id'],
                    is_double=info['is_double']
                )
                self.solution.append(session)
        
        print(f"    Total sessions scheduled: {len(self.solution)}")
    
    def export_to_csv(self, output_dir: str = "../output") -> str:
        """
        Export timetable to CSV file.
        
        Args:
            output_dir: Directory to save the file
            
        Returns:
            str: Path to the saved file
        """
        if not self.solution:
            raise ValueError("No solution to export")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare data
        rows = []
        for session in self.solution:
            slot = self.loader.timeslots[session.timeslot_id]
            course = self.loader.courses[session.course_id]
            instructor = self.loader.instructors[session.instructor_id]
            room = self.loader.rooms[session.room_id]
            
            row = {
                'Course ID': session.course_id,
                'Course Name': course['name'],
                'Section': session.section_id,
                'Type': session.session_type,
                'Session': session.session_num + 1,
                'Day': slot['day'],
                'Start Time': slot['start_time'],
                'End Time': slot['end_time'],
                'Duration': f"{slot['duration']} min" if not session.is_double else "90 min",
                'Room': session.room_id,
                'Room Type': room['type'],
                'Instructor': instructor['name'],
                'Instructor ID': session.instructor_id
            }
            
            rows.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Sort by day, start time, section
        day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
        df['Day_Order'] = df['Day'].apply(lambda x: day_order.index(x) if x in day_order else 999)
        df = df.sort_values(['Section', 'Day_Order', 'Start Time'])
        df = df.drop('Day_Order', axis=1)
        
        # Save to CSV
        filename = f"timetable_year{self.target_year}.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False)
        
        print(f"\n  ✓ Timetable exported to: {filepath}")
        return filepath


def generate_timetable_for_year(year: int, data_path: str = None, 
                                 output_dir: str = None) -> Optional[str]:
    """
    Generate timetable for a specific year.
    
    Args:
        year: Year to generate (1, 2, 3, or 4)
        data_path: Path to data folder (default: auto-detect)
        output_dir: Path to output folder (default: auto-detect)
        
    Returns:
        str: Path to generated file, or None if failed
    """
    # Auto-detect paths if not provided
    if data_path is None:
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data')
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
        
    print("\n" + "=" * 70)
    print(f"GENERATING TIMETABLE FOR YEAR {year}")
    print("=" * 70)
    
    # Load data
    loader = DataLoader(data_path)
    if not loader.load_all():
        return None
    
    # Create solver
    solver = CSPTimetableSolver(loader, year)
    
    # Create variables
    solver.create_variables()
    
    # Add constraints
    solver.add_hard_constraints()
    solver.add_soft_constraints()
    
    # Solve
    if solver.solve():
        return solver.export_to_csv(output_dir)
    else:
        return None


def generate_all_timetables(data_path: str = None, 
                            output_dir: str = None) -> Dict[int, Optional[str]]:
    """
    Generate timetables for all years (1-4).
    
    Args:
        data_path: Path to data folder (default: auto-detect)
        output_dir: Path to output folder (default: auto-detect)
        
    Returns:
        dict: Mapping of year -> filepath (None if failed)
    """
    # Auto-detect paths if not provided
    if data_path is None:
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data')
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
        
    print("\n" + "=" * 70)
    print("CSIT TIMETABLE GENERATOR - ALL YEARS")
    print("=" * 70)
    
    results = {}
    
    for year in [1, 2, 3, 4]:
        filepath = generate_timetable_for_year(year, data_path, output_dir)
        results[year] = filepath
        
        if filepath:
            print(f"\n✓ Year {year} completed successfully")
        else:
            print(f"\n✗ Year {year} failed")
        
        print("\n" + "-" * 70)
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    successful = sum(1 for path in results.values() if path is not None)
    print(f"\nSuccessfully generated: {successful}/4 timetables")
    
    for year, filepath in results.items():
        if filepath:
            print(f"  ✓ Year {year}: {filepath}")
        else:
            print(f"  ✗ Year {year}: FAILED")
    
    return results


# # ============================================================================
# # MAIN ENTRY POINT
# # ============================================================================

# if __name__ == "__main__":
#     # Generate timetables for all years
#     results = generate_all_timetables()
    
#     # Exit code based on success
#     if all(path is not None for path in results.values()):
#         print("\n✓ All timetables generated successfully!")
#         exit(0)
#     else:
#         print("\n⚠ Some timetables failed to generate")
#         exit(1)