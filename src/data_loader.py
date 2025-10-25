import pandas as pd
from typing import Dict, List, Tuple, Optional
import os
import sys


class DataLoader:
    """
    Loads and processes CSV data files for timetable generation.
    Provides clean, structured data with validation and error checking.
    """
    
    def __init__(self, data_path: str = None):
        """
        Initialize the data loader.
        
        Args:
            data_path (str): Path to directory containing CSV files 
                           (default: None - auto-detects from src/)
        """
        # Auto-detect path if not provided
        if data_path is None:
            # Get the directory where this script is located (src/)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to project_root/, then to data/
            self.data_path = os.path.normpath(os.path.join(script_dir, '..', 'data'))
        elif not os.path.isabs(data_path):
            # Handle relative paths
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_path = os.path.normpath(os.path.join(script_dir, data_path))
        else:
            # Handle absolute paths
            self.data_path = data_path
        
        # Raw dataframes
        self.courses_df = None
        self.sections_df = None
        self.instructors_df = None
        self.rooms_df = None
        self.timeslots_df = None
        
        # Processed data structures
        self.courses = {}
        self.sections = {}
        self.instructors = {}
        self.rooms = {}
        self.timeslots = []
        
        # Lookup dictionaries
        self.courses_by_year = {}
        self.sections_by_year = {}
        self.sections_by_specialization = {}
        self.rooms_by_type = {}
        self.instructor_qualifications = {}
        
        # Statistics
        self.stats = {
            'total_courses': 0,
            'total_sections': 0,
            'total_instructors': 0,
            'total_rooms': 0,
            'total_timeslots': 0
        }    
        """
        Initialize the data loader.
        
        Args:
            data_path (str): Path to directory containing CSV files 
                        (default: None - auto-detects ../data from src/)
        """
        if data_path is None:
            # Auto-detect: go up one level from src/ to project_root/, then to data/
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_path = os.path.normpath(os.path.join(script_dir, '..', 'data'))
        elif not os.path.isabs(data_path):
            # Handle relative paths
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_path = os.path.normpath(os.path.join(script_dir, data_path))
        else:
            self.data_path = data_path
            
            # Raw dataframes
            self.courses_df = None
            self.sections_df = None
            self.instructors_df = None
            self.rooms_df = None
            self.timeslots_df = None
            
            # Processed data structures
            self.courses = {}
            self.sections = {}
            self.instructors = {}
            self.rooms = {}
            self.timeslots = []
            
            # Lookup dictionaries for efficient queries
            self.courses_by_year = {}
            self.sections_by_year = {}
            self.sections_by_specialization = {}
            self.rooms_by_type = {}
            self.instructor_qualifications = {}
            
            # Statistics
            self.stats = {
                'total_courses': 0,
                'total_sections': 0,
                'total_instructors': 0,
                'total_rooms': 0,
                'total_timeslots': 0
            }
        
    def load_all(self) -> bool:
        """
        Load all data files and process them.
        
        Returns:
            bool: True if all files loaded successfully, False otherwise
        """
        try:
            print("=" * 70)
            print("CSIT TIMETABLE DATA LOADER")
            print("=" * 70)
            print(f"Data path: {self.data_path}")
            
            # Check if data directory exists
            if not os.path.exists(self.data_path):
                raise FileNotFoundError(f"Data directory not found: {self.data_path}")
            
            # Load all data files
            self.load_courses()
            self.load_sections()
            self.load_instructors()
            self.load_rooms()
            self.load_timeslots()
            
            # Build lookup indices
            self._build_lookups()
            
            # Validate data
            self._validate_data()
            
            # Update statistics
            self.stats['total_courses'] = len(self.courses)
            self.stats['total_sections'] = len(self.sections)
            self.stats['total_instructors'] = len(self.instructors)
            self.stats['total_rooms'] = len(self.rooms)
            self.stats['total_timeslots'] = len(self.timeslots)
            
            print("\n" + "=" * 70)
            print("✓ ALL DATA LOADED SUCCESSFULLY")
            print("=" * 70)
            
            self.print_summary()
            return True
            
        except Exception as e:
            print(f"\n✗ ERROR LOADING DATA: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_courses(self):
        """Load and process courses.csv"""
        print("\n[1/5] Loading courses.csv...")
        
        file_path = os.path.join(self.data_path, "courses.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.courses_df = pd.read_csv(file_path)
        
        for _, row in self.courses_df.iterrows():
            course_id = str(row['CourseID']).strip()
            
            # Parse course type to determine session requirements
            course_type = str(row['Type']).lower()
            has_lecture = 'lecture' in course_type
            has_lab = 'lab' in course_type
            has_tutorial = 'tut' in course_type
            
            self.courses[course_id] = {
                'id': course_id,
                'name': str(row['CourseName']),
                'credits': int(row['Credits']),
                'year': int(row['Year']),
                'type': str(row['Type']),
                'shared': str(row['Shared']).lower() == 'yes' if pd.notna(row['Shared']) else False,
                'has_lecture': has_lecture,
                'has_lab': has_lab,
                'has_tutorial': has_tutorial,
                # Session counts based on credits
                'lecture_sessions': int(row['Credits']) if has_lecture else 0,
                'lab_sessions': int(row['Credits']) if has_lab else 0,
                'tutorial_sessions': int(row['Credits']) if has_tutorial else 0
            }
        
        print(f"  ✓ Loaded {len(self.courses)} courses")
    
    def load_sections(self):
        """Load and process sections.csv"""
        print("\n[2/5] Loading sections.csv...")
        
        file_path = os.path.join(self.data_path, "sections.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.sections_df = pd.read_csv(file_path)
        
        for _, row in self.sections_df.iterrows():
            section_id = str(row['SectionID']).strip()
            
            # Parse section ID to extract year and specialization
            # Format: "Year/Group" or "Year/Specialization/Group"
            parts = section_id.split('/')
            
            if len(parts) == 2:
                # Format: "1/1" -> Year 1, General, Group 1
                year = int(parts[0])
                group = parts[1]
                specialization = 'General'
            elif len(parts) == 3:
                # Format: "3/CNC/1" -> Year 3, CNC, Group 1
                year = int(parts[0])
                specialization = parts[1]
                group = parts[2]
            else:
                raise ValueError(f"Invalid section ID format: {section_id}")
            
            self.sections[section_id] = {
                'id': section_id,
                'year': year,
                'specialization': specialization,
                'group': group,
                'capacity': int(row['Capacity'])
            }
        
        print(f"  ✓ Loaded {len(self.sections)} sections")
    
    def load_instructors(self):
        """Load and process instructors.csv"""
        print("\n[3/5] Loading instructors.csv...")
        
        file_path = os.path.join(self.data_path, "instructors.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.instructors_df = pd.read_csv(file_path)
        
        for _, row in self.instructors_df.iterrows():
            instructor_id = str(row['InstructorID']).strip()
            
            # Parse qualified courses (comma-separated list)
            qualified_courses = []
            if pd.notna(row['QualifiedCourses']):
                qualified_str = str(row['QualifiedCourses'])
                qualified_courses = [c.strip() for c in qualified_str.split(',')]
            
            # Parse preferred slots
            preferred_slots = None
            unavailable_day = None
            if pd.notna(row['PreferredSlots']):
                pref_str = str(row['PreferredSlots']).lower()
                # Extract unavailable day (e.g., "Not on Tuesday")
                if 'not on' in pref_str:
                    for day in ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday']:
                        if day in pref_str:
                            unavailable_day = day.capitalize()
                            break
            
            self.instructors[instructor_id] = {
                'id': instructor_id,
                'name': str(row['Name']),
                'role': str(row['Role']),
                'preferred_slots': preferred_slots,
                'unavailable_day': unavailable_day,
                'qualified_courses': qualified_courses
            }
        
        print(f"  ✓ Loaded {len(self.instructors)} instructors")
    
    def load_rooms(self):
        """Load and process rooms.csv"""
        print("\n[4/5] Loading rooms.csv...")
        
        file_path = os.path.join(self.data_path, "rooms.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.rooms_df = pd.read_csv(file_path)
        
        for _, row in self.rooms_df.iterrows():
            room_id = str(row['RoomID']).strip()
            
            self.rooms[room_id] = {
                'id': room_id,
                'type': str(row['Type']),
                'capacity': int(row['Capacity'])
            }
        
        print(f"  ✓ Loaded {len(self.rooms)} rooms")
    
    def load_timeslots(self):
        """Load and process timeslots.csv"""
        print("\n[5/5] Loading timeslots.csv...")
        
        file_path = os.path.join(self.data_path, "timeslots.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.timeslots_df = pd.read_csv(file_path)
        
        for idx, row in self.timeslots_df.iterrows():
            self.timeslots.append({
                'id': idx,
                'day': str(row['Day']),
                'start_time': str(row['StartTime']),
                'end_time': str(row['EndTime']),
                'duration': int(row['Duration'])
            })
        
        print(f"  ✓ Loaded {len(self.timeslots)} time slots")
    
    def _build_lookups(self):
        """Build lookup dictionaries for efficient querying"""
        print("\nBuilding lookup indices...")
        
        # Courses by year
        for course_id, course in self.courses.items():
            year = course['year']
            if year not in self.courses_by_year:
                self.courses_by_year[year] = []
            self.courses_by_year[year].append(course_id)
        
        # Sections by year and specialization
        for section_id, section in self.sections.items():
            year = section['year']
            spec = section['specialization']
            
            # By year
            if year not in self.sections_by_year:
                self.sections_by_year[year] = []
            self.sections_by_year[year].append(section_id)
            
            # By specialization
            if spec not in self.sections_by_specialization:
                self.sections_by_specialization[spec] = []
            self.sections_by_specialization[spec].append(section_id)
        
        # Rooms by type
        for room_id, room in self.rooms.items():
            room_type = room['type']
            if room_type not in self.rooms_by_type:
                self.rooms_by_type[room_type] = []
            self.rooms_by_type[room_type].append(room_id)
        
        # Instructor qualifications (reverse mapping: course -> instructors)
        for instructor_id, instructor in self.instructors.items():
            for course_id in instructor['qualified_courses']:
                if course_id not in self.instructor_qualifications:
                    self.instructor_qualifications[course_id] = []
                self.instructor_qualifications[course_id].append(instructor_id)
        
        print("  ✓ Lookups built")
    
    def _validate_data(self):
        """Validate loaded data for consistency"""
        print("\nValidating data consistency...")
        
        errors = []
        warnings = []
        
        # Check that all courses have at least one qualified instructor
        for course_id in self.courses.keys():
            if course_id not in self.instructor_qualifications:
                warnings.append(f"Course {course_id} has no qualified instructors")
            elif len(self.instructor_qualifications[course_id]) < 2:
                warnings.append(f"Course {course_id} has only 1 qualified instructor")
        
        # Check room availability
        lecture_rooms = self.rooms_by_type.get('Lecture', [])
        lab_rooms = self.rooms_by_type.get('Lab', [])
        
        if len(lecture_rooms) == 0:
            errors.append("No lecture rooms available")
        if len(lab_rooms) == 0:
            warnings.append("No lab rooms available")
        
        # Check timeslot coverage
        days = set(slot['day'] for slot in self.timeslots)
        if len(days) < 5:
            warnings.append(f"Only {len(days)} days have time slots")
        
        # Report validation results
        if errors:
            print("\n  ✗ VALIDATION ERRORS:")
            for error in errors:
                print(f"    - {error}")
            raise ValueError("Data validation failed")
        
        if warnings:
            print("\n  ⚠ WARNINGS:")
            for warning in warnings[:10]:  # Show first 10
                print(f"    - {warning}")
            if len(warnings) > 10:
                print(f"    ... and {len(warnings) - 10} more")
        
        if not errors and not warnings:
            print("  ✓ All validations passed")
    
    def print_summary(self):
        """Print summary of loaded data"""
        print("\n" + "=" * 70)
        print("DATA SUMMARY")
        print("=" * 70)
        
        print(f"\nCourses: {len(self.courses)}")
        for year in sorted(self.courses_by_year.keys()):
            count = len(self.courses_by_year[year])
            print(f"  - Year {year}: {count} courses")
        
        print(f"\nSections: {len(self.sections)}")
        for year in sorted(self.sections_by_year.keys()):
            sections = [self.sections[s] for s in self.sections_by_year[year]]
            specializations = set(s['specialization'] for s in sections)
            print(f"  - Year {year}: {len(sections)} sections ({', '.join(sorted(specializations))})")
        
        print(f"\nInstructors: {len(self.instructors)}")
        roles = {}
        for inst in self.instructors.values():
            role = inst['role']
            roles[role] = roles.get(role, 0) + 1
        for role, count in sorted(roles.items()):
            print(f"  - {role}: {count}")
        
        print(f"\nRooms: {len(self.rooms)}")
        for room_type, room_list in sorted(self.rooms_by_type.items()):
            print(f"  - {room_type}: {len(room_list)} rooms")
        
        print(f"\nTime Slots: {len(self.timeslots)}")
        duration_groups = {}
        for slot in self.timeslots:
            dur = slot['duration']
            duration_groups[dur] = duration_groups.get(dur, 0) + 1
        for duration, count in sorted(duration_groups.items()):
            print(f"  - {duration} min slots: {count}")
    
    # ========================================================================
    # QUERY METHODS - Used by CSP Solver
    # ========================================================================
    
    def get_courses_for_year(self, year: int) -> List[str]:
        """Get all course IDs for a specific year"""
        return self.courses_by_year.get(year, [])
    
    def get_sections_for_year(self, year: int) -> List[str]:
        """Get all section IDs for a specific year"""
        return self.sections_by_year.get(year, [])
    
    def get_sections_for_course(self, course_id: str) -> List[str]:
        """
        Get sections that should take a specific course.
        
        Logic:
        - If course is shared (marked as "Yes"), all sections in that year take it
        - If course is not shared, only General sections or matching specialization sections take it
        """
        course = self.courses.get(course_id)
        if not course:
            return []
        
        year = course['year']
        is_shared = course['shared']
        
        matching_sections = []
        for section_id in self.get_sections_for_year(year):
            section = self.sections[section_id]
            
            # If shared course, all sections in that year take it
            if is_shared:
                matching_sections.append(section_id)
            # If not shared, only General sections take it
            elif section['specialization'] == 'General':
                matching_sections.append(section_id)
        
        return matching_sections
    
    def get_qualified_instructors(self, course_id: str) -> List[str]:
        """Get instructors qualified to teach a course"""
        return self.instructor_qualifications.get(course_id, [])
    
    def get_suitable_rooms(self, room_type: str, min_capacity: int = 0) -> List[str]:
        """Get rooms of specific type with minimum capacity"""
        rooms = self.rooms_by_type.get(room_type, [])
        return [r for r in rooms if self.rooms[r]['capacity'] >= min_capacity]
    
    def get_timeslots_by_duration(self, duration: int) -> List[int]:
        """Get time slot IDs with specific duration (45 or 90 minutes)"""
        return [slot['id'] for slot in self.timeslots if slot['duration'] == duration]
    
    def get_timeslots_by_day(self, day: str) -> List[int]:
        """Get time slot IDs for a specific day"""
        return [slot['id'] for slot in self.timeslots if slot['day'] == day]
    
    def is_instructor_available(self, instructor_id: str, timeslot_id: int) -> bool:
        """Check if instructor is available during a time slot"""
        instructor = self.instructors.get(instructor_id)
        if not instructor:
            return False
        
        # Check unavailable day
        if instructor['unavailable_day']:
            slot = self.timeslots[timeslot_id]
            if slot['day'] == instructor['unavailable_day']:
                return False
        
        return True
    
    def find_consecutive_slots(self, day: Optional[str] = None, duration: int = 45) -> List[Tuple[int, int]]:
        """
        Find pairs of consecutive time slots for labs (need 90 minutes).
        
        Args:
            day: Day of the week (optional, if None finds for all days)
            duration: Duration per slot (default: 45 minutes)
        
        Returns:
            List of (slot1_id, slot2_id) tuples
        """
        # Filter slots
        if day:
            day_slots = [(slot['id'], slot) for slot in self.timeslots 
                         if slot['day'] == day and slot['duration'] == duration]
        else:
            day_slots = [(slot['id'], slot) for slot in self.timeslots 
                         if slot['duration'] == duration]
        
        # Sort by day and start time
        day_slots.sort(key=lambda x: (x[1]['day'], x[1]['start_time']))
        
        consecutive_pairs = []
        for i in range(len(day_slots) - 1):
            slot1_id, slot1 = day_slots[i]
            slot2_id, slot2 = day_slots[i + 1]
            
            # Check if same day and slot2 starts when slot1 ends
            if (slot1['day'] == slot2['day'] and 
                slot1['end_time'] == slot2['start_time']):
                consecutive_pairs.append((slot1_id, slot2_id))
        
        return consecutive_pairs
    
    def get_statistics(self) -> Dict:
        """Get statistics about loaded data"""
        return self.stats.copy()


# # ============================================================================
# # USAGE EXAMPLE & TESTING
# # ============================================================================

# def test_data_loader():
#     """Test function to verify data loader works correctly"""
#     print("\n" + "=" * 70)
#     print("TESTING DATA LOADER")
#     print("=" * 70)
    
#     # Initialize loader
#     loader = DataLoader()
    
#     # Load all data
#     if not loader.load_all():
#         print("\n✗ Data loading failed!")
#         return False
    
#     print("\n" + "=" * 70)
#     print("RUNNING QUERY TESTS")
#     print("=" * 70)
    
#     # Test 1: Get courses for Year 1
#     print("\n[Test 1] Get courses for Year 1:")
#     year1_courses = loader.get_courses_for_year(1)
#     print(f"  Found {len(year1_courses)} courses")
#     for course_id in year1_courses[:3]:
#         course = loader.courses[course_id]
#         print(f"  - {course_id}: {course['name']} ({course['credits']} credits)")
    
#     # Test 2: Get sections for a course
#     if year1_courses:
#         print("\n[Test 2] Get sections for course:", year1_courses[0])
#         sections = loader.get_sections_for_course(year1_courses[0])
#         print(f"  Found {len(sections)} sections:")
#         for section_id in sections[:3]:
#             section = loader.sections[section_id]
#             print(f"  - {section_id}: {section['specialization']}, Capacity: {section['capacity']}")
    
#     # Test 3: Get qualified instructors
#     if year1_courses:
#         print("\n[Test 3] Get qualified instructors for:", year1_courses[0])
#         instructors = loader.get_qualified_instructors(year1_courses[0])
#         print(f"  Found {len(instructors)} qualified instructors:")
#         for inst_id in instructors[:3]:
#             instructor = loader.instructors[inst_id]
#             print(f"  - {inst_id}: {instructor['name']} ({instructor['role']})")
    
#     # Test 4: Get lecture rooms
#     print("\n[Test 4] Get lecture rooms (capacity >= 30):")
#     lecture_rooms = loader.get_suitable_rooms('Lecture', min_capacity=30)
#     print(f"  Found {len(lecture_rooms)} suitable rooms:")
#     for room_id in lecture_rooms[:5]:
#         room = loader.rooms[room_id]
#         print(f"  - {room_id}: Capacity {room['capacity']}")
    
#     # Test 5: Find consecutive slots
#     print("\n[Test 5] Find consecutive 45-min slots:")
#     consecutive = loader.find_consecutive_slots(duration=45)
#     print(f"  Found {len(consecutive)} consecutive slot pairs")
#     if consecutive:
#         for slot1_id, slot2_id in consecutive[:3]:
#             slot1 = loader.timeslots[slot1_id]
#             slot2 = loader.timeslots[slot2_id]
#             print(f"  - {slot1['day']}: {slot1['start_time']}-{slot1['end_time']} + {slot2['start_time']}-{slot2['end_time']}")
    
#     # Test 6: Check instructor availability
#     if year1_courses and instructors:
#         print("\n[Test 6] Check instructor availability:")
#         test_instructor = instructors[0]
#         instructor = loader.instructors[test_instructor]
#         print(f"  Instructor: {instructor['name']}")
#         print(f"  Unavailable day: {instructor['unavailable_day']}")
        
#         # Check a few timeslots
#         for slot_id in range(min(3, len(loader.timeslots))):
#             slot = loader.timeslots[slot_id]
#             available = loader.is_instructor_available(test_instructor, slot_id)
#             status = "✓ Available" if available else "✗ Unavailable"
#             print(f"  - {slot['day']} {slot['start_time']}: {status}")
    
#     print("\n" + "=" * 70)
#     print("✓ ALL TESTS PASSED")
#     print("=" * 70)
#     return True


# if __name__ == "__main__":
#     test_data_loader()