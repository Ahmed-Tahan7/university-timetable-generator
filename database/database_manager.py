import sqlite3
from typing import List
from models.data_models import (
    Course, Instructor, InstructorCourse, Room, TimeSlot
)

class DatabaseManager:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.connection = None
        try:
            self.connection = sqlite3.connect(db_file)
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            self.connection = None

    def __del__(self):
        if self.connection:
            self.connection.close()

    def get_courses(self) -> List[Course]:
        courses = []
        if not self.connection:
            return courses

        sql = """
            SELECT CourseID, CourseName, Credits, Type, Year, Specialization, 
                   HasLecture, HasLab, IsGradProject 
            FROM Courses;
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            
            for row in cursor.fetchall():
                course = Course(
                    id=row[0] if row[0] else "",
                    name=row[1] if row[1] else "",
                    credits=row[2],
                    type=row[3] if row[3] else "",
                    year=row[4],
                    specialization=row[5] if row[5] else "",
                    has_lecture=bool(row[6]),
                    has_lab=bool(row[7]),
                    is_grad_project=bool(row[8])
                )
                courses.append(course)
                
        except sqlite3.Error as e:
            print(f"Error while fetching courses: {e}")
        
        return courses

    def get_instructors(self) -> List[Instructor]:
        instructors = []
        if not self.connection:
            return instructors

        sql = """
            SELECT InstructorID, Name, Role, PreferredSlots, QualifiedCourses 
            FROM Instructor;
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            
            for row in cursor.fetchall():
                instructor = Instructor(
                    id=row[0] if row[0] else "",
                    name=row[1] if row[1] else "",
                    role=row[2] if row[2] else "",
                    preferred_slots=row[3] if row[3] else "",
                    qualified_courses=row[4] if row[4] else ""
                )
                instructors.append(instructor)
                
        except sqlite3.Error as e:
            print(f"Error while fetching instructors: {e}")
        
        return instructors

    def get_instructor_courses(self) -> List[InstructorCourse]:
        instructor_courses = []
        if not self.connection:
            return instructor_courses

        sql = "SELECT InstructorID, CourseID FROM InstructorCourses;"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            
            for row in cursor.fetchall():
                ic = InstructorCourse(
                    instructor_id=row[0] if row[0] else "",
                    course_id=row[1] if row[1] else ""
                )
                instructor_courses.append(ic)
                
        except sqlite3.Error as e:
            print(f"Error while fetching instructor-courses: {e}")
        
        return instructor_courses

    def get_rooms(self) -> List[Room]:
        rooms = []
        if not self.connection:
            return rooms

        sql = """
            SELECT RoomID, Building, RoomName, Capacity, RoomType 
            FROM Rooms;
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            
            for row in cursor.fetchall():
                room = Room(
                    id=row[0] if row[0] else "",
                    building=row[1] if row[1] else "",
                    room_name=row[2] if row[2] else "",
                    capacity=row[3],
                    room_type=row[4] if row[4] else ""
                )
                rooms.append(room)
                
        except sqlite3.Error as e:
            print(f"Error while fetching rooms: {e}")
        
        return rooms

    def get_time_slots(self) -> List[TimeSlot]:
        time_slots = []
        if not self.connection:
            return time_slots

        sql = """
            SELECT TimeSlotID, Day, StartTimeTxt, EndTimeTxt, StartMin, EndMin 
            FROM TimeSlots;
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            
            for row in cursor.fetchall():
                ts = TimeSlot(
                    id=row[0],
                    day=row[1] if row[1] else "",
                    start_txt=row[2] if row[2] else "",
                    end_txt=row[3] if row[3] else "",
                    start_min=row[4],
                    end_min=row[5]
                )
                time_slots.append(ts)
                
        except sqlite3.Error as e:
            print(f"Error while fetching time slots: {e}")
        
        return time_slots

    def get_instructors_for_course(self, course_id: str) -> List[Instructor]:
        instructors = []
        if not self.connection:
            return instructors

        sql = """
            SELECT I.InstructorID, I.Name, I.Role, I.PreferredSlots, I.QualifiedCourses
            FROM Instructor I
            INNER JOIN InstructorCourses IC ON I.InstructorID = IC.InstructorID
            WHERE IC.CourseID = ?;
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, (course_id,))
            
            for row in cursor.fetchall():
                instructor = Instructor(
                    id=row[0] if row[0] else "",
                    name=row[1] if row[1] else "",
                    role=row[2] if row[2] else "",
                    preferred_slots=row[3] if row[3] else "",
                    qualified_courses=row[4] if row[4] else ""
                )
                instructors.append(instructor)
                
        except sqlite3.Error as e:
            print(f"Error while fetching instructors for course: {e}")
        
        return instructors