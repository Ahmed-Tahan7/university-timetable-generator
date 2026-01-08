"""
Data models for the timetable scheduling system
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Course:
    id: str
    name: str
    credits: int
    type: str
    year: int
    specialization: str
    has_lecture: bool
    has_lab: bool
    is_grad_project: bool


@dataclass
class Instructor:
    id: str
    name: str
    role: str
    preferred_slots: str
    qualified_courses: str


@dataclass
class InstructorCourse:
    instructor_id: str
    course_id: str


@dataclass
class Room:
    id: str
    building: str
    room_name: str
    capacity: int
    room_type: str


@dataclass
class TimeSlot:
    id: int
    day: str
    start_txt: str
    end_txt: str
    start_min: int
    end_min: int


@dataclass
class LectureVar:
    var_id: str
    course_id: str
    year: int
    group_id: int
    section_id: int
    specialization: str
    session_type: str
    length_min: int
    is_full_day: bool


@dataclass
class AssignmentValue:
    timeslot_index: int
    room_id: str
    instructor_id: str


@dataclass
class CSPResult:
    success: bool
    assignments: Dict[str, AssignmentValue]
    hard_violations: int
    soft_cost: int
    solve_seconds: float