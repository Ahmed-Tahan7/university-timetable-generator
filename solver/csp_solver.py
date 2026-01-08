import time
from typing import List, Dict, Tuple, Optional
from models.data_models import (
    Course, Instructor, InstructorCourse, Room, TimeSlot,
    LectureVar, AssignmentValue, CSPResult
)


def min_to_12_hour(mins: int) -> str:
    h = mins // 60
    m = mins % 60
    pm = h >= 12
    hh = 12 if h % 12 == 0 else h % 12
    return f"{hh:02d}:{m:02d}{'PM' if pm else 'AM'}"


class CSPSolver:
    def __init__(self, courses: List[Course], instructors: List[Instructor],
                 instructor_courses: List[InstructorCourse], rooms: List[Room],
                 time_slots: List[TimeSlot]):
        self.courses = courses
        self.instructors = instructors
        self.instructor_courses = instructor_courses
        self.rooms = rooms
        self.time_slots = time_slots
        
        self.variables: List[LectureVar] = []
        self.domains: List[List[AssignmentValue]] = []
        
        self.course_index: Dict[str, Course] = {c.id: c for c in courses}
        self.course_to_instructors: Dict[str, List[str]] = {}
        
        for ic in instructor_courses:
            if ic.course_id not in self.course_to_instructors:
                self.course_to_instructors[ic.course_id] = []
            self.course_to_instructors[ic.course_id].append(ic.instructor_id)
        
        if not self.course_to_instructors:
            for ins in instructors:
                q = ins.qualified_courses
                pos = 0
                while pos < len(q):
                    comma = q.find(',', pos)
                    token = q[pos:comma] if comma != -1 else q[pos:]
                    token = token.strip()
                    if token:
                        if token not in self.course_to_instructors:
                            self.course_to_instructors[token] = []
                        self.course_to_instructors[token].append(ins.id)
                    if comma == -1:
                        break
                    pos = comma + 1

    def build_lecture_variables(self):
        self.variables.clear()
        
        year1 = ["LRA401", "CSC111", "MTH111", "PHY113", "ECE111", "LRA101", "LRA104", "LRA105"]
        year2 = ["MTH212", "ACM215", "LRA403", "CSC211", "CNC111", "CSC114", "CSE214", "LRA306"]
        year3 = ["AID311", "AID312", "BIF311", "CNC311", "CNC312", "CNC314", "CSC314", "CSC317", "ECE324"]
        japanese_languages = ["LRA401", "LRA403"]
        specializations = ["AID", "BIF", "CSC", "CNC"]
        
        #lecture variables
        for c in self.courses:
            yr = c.year
            if yr < 1 or yr > 4:
                continue
            
            if c.is_grad_project:
                continue
            
            if yr == 1 and c.id not in year1:
                continue
            if yr == 2 and c.id not in year2:
                continue
            if yr == 3 and c.id not in year3:
                continue
            
            is_japanese = c.id in japanese_languages
            
            if yr == 3 or yr == 4:
                is_common = c.specialization == "Common" or not c.specialization
                if is_common:
                    for s in specializations:
                        v = LectureVar(
                            var_id=f"{c.id}_Y{yr}_{s}_LEC",
                            course_id=c.id,
                            year=yr,
                            group_id=0,
                            section_id=0,
                            specialization=s,
                            session_type="LECTURE",
                            length_min=90,
                            is_full_day=False
                        )
                        self.variables.append(v)
                else:
                    v = LectureVar(
                        var_id=f"{c.id}_Y{yr}_{c.specialization}_LEC",
                        course_id=c.id,
                        year=yr,
                        group_id=0,
                        section_id=0,
                        specialization=c.specialization,
                        session_type="LECTURE",
                        length_min=90,
                        is_full_day=False
                    )
                    self.variables.append(v)
            elif is_japanese:
                for grp in range(1, 4):
                    for sec in range(1, 4):
                        v = LectureVar(
                            var_id=f"{c.id}_Y{yr}_G{grp}_S{sec}",
                            course_id=c.id,
                            year=yr,
                            group_id=grp,
                            section_id=sec,
                            specialization="",
                            session_type="LECTURE",
                            length_min=90,
                            is_full_day=False
                        )
                        self.variables.append(v)
            else:
                for grp in range(1, 4):
                    v = LectureVar(
                        var_id=f"{c.id}_Y{yr}_G{grp}_LEC",
                        course_id=c.id,
                        year=yr,
                        group_id=grp,
                        section_id=0,
                        specialization="",
                        session_type="LECTURE",
                        length_min=90,
                        is_full_day=False
                    )
                    self.variables.append(v)
        
        #lab variables
        for c in self.courses:
            yr = c.year
            if yr < 1 or yr > 4:
                continue
            
            if not c.has_lab and not c.is_grad_project:
                continue
            
            if yr == 1 or yr == 2:
                for grp in range(1, 4):
                    for sec in range(1, 4):
                        v = LectureVar(
                            var_id=f"{c.id}_Y{yr}_G{grp}_S{sec}_LAB",
                            course_id=c.id,
                            year=yr,
                            group_id=grp,
                            section_id=sec,
                            specialization="",
                            session_type="LAB",
                            length_min=90,
                            is_full_day=c.is_grad_project
                        )
                        self.variables.append(v)
            else:
                is_common = c.specialization == "Common" or not c.specialization
                if is_common:
                    for s in specializations:
                        v = LectureVar(
                            var_id=f"{c.id}_Y{yr}_{s}_S1_LAB",
                            course_id=c.id,
                            year=yr,
                            group_id=0,
                            section_id=1,
                            specialization=s,
                            session_type="LAB",
                            length_min=90,
                            is_full_day=c.is_grad_project
                        )
                        self.variables.append(v)
                else:
                    v = LectureVar(
                        var_id=f"{c.id}_Y{yr}_{c.specialization}_S1_LAB",
                        course_id=c.id,
                        year=yr,
                        group_id=0,
                        section_id=1,
                        specialization=c.specialization,
                        session_type="LAB",
                        length_min=90,
                        is_full_day=c.is_grad_project
                    )
                    self.variables.append(v)
        
        print(f"Total variables created: {len(self.variables)}")

    def build_domains(self):
        self.domains = [[] for _ in self.variables]
        
        room_index = {r.id: r for r in self.rooms}
        instructor_index = {ins.id: ins for ins in self.instructors}
        
        for vi, v in enumerate(self.variables):
            course = self.course_index.get(v.course_id)
            if not course:
                continue
            
            qualified_instructors = []
            
            if v.session_type == "LECTURE":
                if course.id in self.course_to_instructors:
                    for ins_id in self.course_to_instructors[course.id]:
                        if ins_id in instructor_index and instructor_index[ins_id].role == "Professor":
                            qualified_instructors.append(ins_id)
                
                if not qualified_instructors:
                    qualified_instructors = [ins.id for ins in self.instructors if ins.role == "Professor"]
                
                for ts_idx, ts in enumerate(self.time_slots):
                    if (ts.end_min - ts.start_min) < v.length_min:
                        continue
                    
                    for r in self.rooms:
                        if r.room_type not in ["Classroom", "Theater", "Hall"]:
                            continue
                        for ins_id in qualified_instructors:
                            self.domains[vi].append(AssignmentValue(ts_idx, r.id, ins_id))
            
            elif v.session_type == "LAB":
                if course.id in self.course_to_instructors:
                    for ins_id in self.course_to_instructors[course.id]:
                        if ins_id in instructor_index and instructor_index[ins_id].role == "Assistant Professor":
                            qualified_instructors.append(ins_id)
                
                if not qualified_instructors:
                    qualified_instructors = [ins.id for ins in self.instructors if ins.role == "Assistant Professor"]
                
                if not qualified_instructors:
                    qualified_instructors = [ins.id for ins in self.instructors]
                
                for ts_idx, ts in enumerate(self.time_slots):
                    if (ts.end_min - ts.start_min) < v.length_min:
                        continue
                    
                    for r in self.rooms:
                        if r.room_type not in ["Lab", "Classroom"]:
                            continue
                        for ins_id in qualified_instructors:
                            self.domains[vi].append(AssignmentValue(ts_idx, r.id, ins_id))

    def is_hard_conflict(self, a: AssignmentValue, b: AssignmentValue,
                        va: LectureVar, vb: LectureVar) -> bool:
        ts_a = self.time_slots[a.timeslot_index]
        ts_b = self.time_slots[b.timeslot_index]
        
        if ts_a.day != ts_b.day:
            return False
        
        time_overlap = (va.is_full_day or vb.is_full_day) or \
                      not (ts_a.end_min <= ts_b.start_min or ts_b.end_min <= ts_a.start_min)
        
        if not time_overlap:
            return False
        
        if a.instructor_id and b.instructor_id and a.instructor_id == b.instructor_id:
            return True
        
        if a.room_id == b.room_id:
            return True
        
        if va.group_id > 0 and vb.group_id > 0 and va.year == vb.year and va.group_id == vb.group_id:
            if va.session_type == "LAB" and vb.session_type == "LAB" and va.section_id != vb.section_id:
                pass
            else:
                return True
        
        if va.specialization and vb.specialization and va.year == vb.year and va.specialization == vb.specialization:
            return True
        
        if (va.course_id == vb.course_id and va.session_type == "LECTURE" and
            vb.session_type == "LECTURE" and a.instructor_id and b.instructor_id and
            a.instructor_id != b.instructor_id):
            return True
        
        return False

    def compute_soft_cost(self, assignments: Dict[str, AssignmentValue]) -> int:
        cost = 0
        if not self.time_slots:
            return cost
        
        earliest_start_min = min(ts.start_min for ts in self.time_slots)
        
        for var_id, val in assignments.items():
            ts = self.time_slots[val.timeslot_index]
            if ts.start_min == earliest_start_min:
                cost += 5
        
        course_day_count = {}
        for var_id, val in assignments.items():
            pos = var_id.find("_Y")
            course_id = var_id[:pos] if pos != -1 else var_id
            ts = self.time_slots[val.timeslot_index]
            
            if course_id not in course_day_count:
                course_day_count[course_id] = {}
            if ts.day not in course_day_count[course_id]:
                course_day_count[course_id][ts.day] = 0
            course_day_count[course_id][ts.day] += 1
        
        for course_id, days in course_day_count.items():
            for day, count in days.items():
                if count > 1:
                    cost += (count - 1) * 2
        
        return cost

    def backtrack_search(self) -> CSPResult:
        print("Starting backtrack search (MRV + Forward Checking)")
        start_time = time.time()
        
        result = CSPResult(
            success=False,
            assignments={},
            hard_violations=0,
            soft_cost=0,
            solve_seconds=0.0
        )
        
        for i, v in enumerate(self.variables):
            if not self.domains[i]:
                print(f"Variable {v.var_id} has empty domain")
                result.hard_violations = 1
                result.solve_seconds = 0.0
                return result
        
        doms = [list(d) for d in self.domains]
        assignments = {}
        course_professor = {}
        
        def dfs() -> bool:
            if len(assignments) == len(self.variables):
                result.success = True
                result.assignments = dict(assignments)
                result.hard_violations = 0
                result.soft_cost = self.compute_soft_cost(assignments)
                return True
            
            chosen = -1
            min_domain_size = float('inf')
            for i, v in enumerate(self.variables):
                if v.var_id not in assignments:
                    if len(doms[i]) < min_domain_size:
                        min_domain_size = len(doms[i])
                        chosen = i
            
            if chosen == -1:
                return False
            
            chosen_var = self.variables[chosen]
            domain_copy = list(doms[chosen])
            
            for val in domain_copy:
                if (chosen_var.session_type == "LECTURE" and 
                    chosen_var.course_id in course_professor):
                    if course_professor[chosen_var.course_id] != val.instructor_id:
                        continue
                
                conflict = False
                for var_id, assigned_val in assignments.items():
                    other_idx = next((i for i, v in enumerate(self.variables) if v.var_id == var_id), None)
                    if other_idx is not None:
                        if self.is_hard_conflict(val, assigned_val, chosen_var, self.variables[other_idx]):
                            conflict = True
                            break
                
                if conflict:
                    continue
                
                assignments[chosen_var.var_id] = val
                if chosen_var.session_type == "LECTURE":
                    course_professor[chosen_var.course_id] = val.instructor_id
                
                changed = []
                for j in range(len(doms)):
                    if self.variables[j].var_id in assignments:
                        continue
                    
                    new_dom = []
                    for cand in doms[j]:
                        valid = True
                        
                        if self.is_hard_conflict(val, cand, chosen_var, self.variables[j]):
                            valid = False
                        
                        if (valid and self.variables[j].session_type == "LECTURE" and
                            self.variables[j].course_id in course_professor):
                            if course_professor[self.variables[j].course_id] != cand.instructor_id:
                                valid = False
                        
                        if valid:
                            new_dom.append(cand)
                    
                    if len(new_dom) != len(doms[j]):
                        changed.append((j, list(doms[j])))
                        doms[j] = new_dom
                
                any_empty = any(not doms[j] for j in range(len(doms)) 
                               if self.variables[j].var_id not in assignments)
                
                if not any_empty and dfs():
                    return True
                
                for j, old_dom in changed:
                    doms[j] = old_dom
                
                del assignments[chosen_var.var_id]
                
                if chosen_var.session_type == "LECTURE":
                    other_assigned = any(
                        v.course_id == chosen_var.course_id and v.session_type == "LECTURE"
                        for var_id in assignments.keys()
                        for v in self.variables if v.var_id == var_id
                    )
                    if not other_assigned:
                        course_professor.pop(chosen_var.course_id, None)
            
            return False
        
        found = dfs()
        end_time = time.time()
        result.solve_seconds = end_time - start_time
        
        if not found:
            result.success = False
            print(f"No solution found after {result.solve_seconds:.2f} seconds")
        
        return result

    def solve(self, max_solutions: int = 1) -> CSPResult:
        return self.backtrack_search()

    def print_result(self, result: CSPResult):
        if not result.success:
            print(f"\nNo solution found. Hard violations: {result.hard_violations}, "
                  f"time: {result.solve_seconds:.2f}s")
            return
        
        room_index = {r.id: r for r in self.rooms}
        instructor_names = {ins.id: ins.name for ins in self.instructors}
        course_names = {c.id: c.name for c in self.courses}
        
        for v in self.variables:
            if v.var_id not in result.assignments:
                continue
            
            a = result.assignments[v.var_id]
            ts = self.time_slots[a.timeslot_index]
            rm = room_index.get(a.room_id)
            
            cname = course_names.get(v.course_id, v.course_id)
            ins_name = instructor_names.get(a.instructor_id, a.instructor_id) if a.instructor_id else "null"
            
            print(f"{v.course_id} | {cname} (Y{v.year})", end="")
            
            if v.session_type == "LECTURE":
                if (v.year == 3 or v.year == 4) and v.specialization:
                    print(f" | {v.specialization} Lecture", end="")
                elif v.section_id > 0 and v.group_id > 0:
                    print(f" | G{v.group_id} Section {v.section_id}", end="")
                else:
                    print(f" | G{v.group_id} Lecture", end="")
            elif v.session_type == "LAB":
                if v.specialization and v.section_id > 0:
                    print(f" | {v.specialization} S{v.section_id} Lab", end="")
                elif v.group_id > 0 and v.section_id > 0:
                    print(f" | G{v.group_id} S{v.section_id} Lab", end="")
                else:
                    print(" | Lab", end="")
                if v.is_full_day:
                    print(" (Full Day)", end="")
            
            # Time and room line
            if v.is_full_day:
                print(f"\n  {ts.day} 9:00 AM - 3:45 PM (Full Day)", end="")
            else:
                print(f"\n  {ts.day} {min_to_12_hour(ts.start_min)} - {min_to_12_hour(ts.end_min)}", end="")
            
            print(f" | {rm.room_name if rm else a.room_id} ({rm.building if rm else ''})"
                  f" | {ins_name}\n")
        
        print(f"Solution found in {result.solve_seconds:.2f}s")
        print("=========================================")

    def get_variables(self) -> List[LectureVar]:
        """Get the list of variables"""
        return self.variables