"""Data models package"""
from .data_models import (
    Course, Instructor, InstructorCourse, Room, TimeSlot,
    LectureVar, AssignmentValue, CSPResult
)

__all__ = [
    'Course', 'Instructor', 'InstructorCourse', 'Room', 'TimeSlot',
    'LectureVar', 'AssignmentValue', 'CSPResult'
]