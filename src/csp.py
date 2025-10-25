import pandas as pd
from itertools import product
from collections import deque
import re

# ---------- Helpers for flexible column names ----------

def _get(df_row, *candidates, default=None):
    """
    Return first available column value from candidates for a given pandas Series (row).
    """
    for c in candidates:
        if c in df_row.index:
            return df_row[c]
    return default

def _col(df, *candidates, default=None):
    """
    Return first existing column name in a DataFrame from candidates; otherwise default.
    """
    for c in candidates:
        if c in df.columns:
            return c
    return default

# ---------- CSP SETUP ----------

def create_day_to_slots_map(timeslots_df):
    """Maps each day to a list of its TimeSlotIDs."""
    if 'TimeSlotID' not in timeslots_df.columns:
        timeslots_df['TimeSlotID'] = [f"TS{i}" for i in range(len(timeslots_df))]
    return timeslots_df.groupby('Day')['TimeSlotID'].apply(list).to_dict()

def infer_courses_for_section(section, courses_df):
    """
    If 'Courses' column is not present in sections, infer the course list for a
    section by matching Year/Semester/Specialization (best-effort).
    """
    year = _get(section, 'Year')
    semester = _get(section, 'Semester')
    specialization = _get(section, 'Specialization') or _get(section, 'DepartmentName')

    candidates = courses_df.copy()
    if year is not None and 'Year' in candidates.columns:
        candidates = candidates[candidates['Year'].astype(str) == str(year)]
    if semester is not None and 'Semester' in candidates.columns:
        candidates = candidates[candidates['Semester'].astype(str) == str(semester)]
    if specialization is not None and 'Specialization' in candidates.columns:
        # match specialization or department loosely
        candidates = candidates[candidates['Specialization'].astype(str).str.contains(str(specialization), case=False, na=False)]

    # Collect CourseCode column values
    ccol = _col(candidates, 'CourseCode', 'CourseID')
    if ccol is None:
        return []
    return list(candidates[ccol].astype(str).str.strip().unique())

def normalize_course_type(course_row):
    """
    Determine course Type string (Lecture / Lab / Lecture and Lab) using explicit Type
    if present, otherwise infer from LecSlots/LabSlots columns.
    """
    if 'Type' in course_row.index and pd.notna(course_row['Type']):
        return str(course_row['Type']).strip()
    lec = _get(course_row, 'LecSlots', 'LecSlot', default=0)
    lab = _get(course_row, 'LabSlots', 'LabSlot', default=0)
    try:
        lec_n = int(lec) if pd.notna(lec) and str(lec).strip() != '' else 0
    except Exception:
        lec_n = 0
    try:
        lab_n = int(lab) if pd.notna(lab) and str(lab).strip() != '' else 0
    except Exception:
        lab_n = 0

    if lec_n > 0 and lab_n > 0:
        return "Lecture and Lab"
    elif lab_n > 0:
        return "Lab"
    else:
        return "Lecture"

def make_room_id(room_row):
    """
    Construct a RoomID from available columns (prefer 'Space', else 'Building_Space').
    """
    space = _get(room_row, 'Space', 'RoomID')
    building = _get(room_row, 'Building')
    if pd.notna(space) and str(space).strip() != '':
        return str(space).strip()
    if pd.notna(building) and pd.notna(space):
        return f"{str(building).strip()}_{str(space).strip()}"
    # fallback to index
    return f"ROOM_{room_row.name}"

def get_room_capacity(room_row):
    cap = _get(room_row, 'Capacity', 'Capacity (Seats)', 'Seats')
    try:
        return int(cap)
    except Exception:
        try:
            return int(float(cap))
        except Exception:
            return 0

def setup_csp(data):
    """
    Builds the CSP model: variables, domains, and constraints.
    This version is robust to the sheet columns you provided.
    """
    variables, domains, empty_domain_reasons = [], {}, {}
    timeslots_df = data['timeslots']
    day_to_slots = create_day_to_slots_map(timeslots_df)

    print("--- Setting up CSP ---")

    # Pre-normalize courses DataFrame: ensure CourseID and CourseName exist
    courses_df = data['courses']
    course_id_col = _col(courses_df, 'CourseCode', 'CourseID')
    course_name_col = _col(courses_df, 'Title', 'CourseName')
    # create normalized columns for easier lookup
    courses_df = courses_df.copy()
    courses_df['CourseID'] = courses_df[course_id_col].astype(str).str.strip() if course_id_col else courses_df.index.astype(str)
    courses_df['CourseName'] = courses_df[course_name_col].astype(str).str.strip() if course_name_col else courses_df['CourseID']
    # keep original columns for lec/lab inference
    data['courses'] = courses_df

    # Pre-normalize rooms: create RoomID, Capacity, Type
    rooms_df = data['rooms'].copy()
    rooms_df['RoomID'] = rooms_df.apply(make_room_id, axis=1)
    rooms_df['Capacity'] = rooms_df.apply(get_room_capacity, axis=1)
    # Type may be 'Type', or 'Type of Space'
    type_col_room = _col(rooms_df, 'Type', 'Type of Space')
    if type_col_room:
        rooms_df['Type'] = rooms_df[type_col_room].astype(str).str.strip()
    data['rooms'] = rooms_df

    # Prepare instructors DataFrame
    instructors_df = data['instructors']
    # ensure QualifiedCourses column exists as string lists
    if 'QualifiedCourses' in instructors_df.columns:
        instructors_df['QualifiedCourses'] = instructors_df['QualifiedCourses'].astype(str)
    else:
        instructors_df['QualifiedCourses'] = ''

    data['instructors'] = instructors_df

    # iterate sections
    sections_df = data['sections']
    for _, section in sections_df.iterrows():
        # derive a SectionID if missing
        section_id = _get(section, 'SectionID')
        if pd.isna(section_id) or section_id is None:
            # build from Year, DepartmentName, GroupNumber, SectionNumber
            year = _get(section, 'Year', default='')
            dept = _get(section, 'DepartmentName', 'Specialization', default='')
            group = _get(section, 'GroupNumber', default='')
            s_num = _get(section, 'SectionNumber', default='')
            # sanitize pieces
            pieces = [str(x).strip() for x in (year, dept, group, s_num) if pd.notna(x) and str(x).strip() != '']
            section_id = "_".join(pieces) if pieces else f"SECTION_{_}"
        # get student count
        student_count = _get(section, 'StudentCount', 'StudentNumber', default=0)
        try:
            student_count = int(student_count)
        except Exception:
            try:
                student_count = int(float(student_count))
            except Exception:
                student_count = 0

        # get courses list: prefer explicit 'Courses' column, else infer from courses.xlsx
        courses_list = []
        if 'Courses' in section.index and pd.notna(section['Courses']) and str(section['Courses']).strip() != '':
            courses_list = [c.strip() for c in str(section['Courses']).split(',') if c.strip()]
        else:
            # attempt inference using Year/Semester/Specialization
            inferred = infer_courses_for_section(section, data['courses'])
            if inferred:
                courses_list = inferred
            else:
                print(f"⚠️ Couldn't find Courses for section '{section_id}'. Skipping this section.")
                continue

        # For each course, create variable(s) according to course type
        for course_id in courses_list:
            course_rows = data['courses'][data['courses']['CourseID'].astype(str) == str(course_id)]
            if course_rows.empty:
                print(f"⚠️ Course '{course_id}' referenced by section '{section_id}' not found in courses sheet. Skipping.")
                continue
            course_row = course_rows.iloc[0]
            course_type = normalize_course_type(course_row)

            # Determine qualified instructors (any instructor whose QualifiedCourses contains the course)
            qualified_instructors = data['instructors'][data['instructors']['QualifiedCourses'].apply(lambda x: str(course_id) in str(x))]

            def make_domain_for_type(vtype):
                domain = []
                if vtype == "Lecture":
                    room_candidates = data['rooms'][(data['rooms']['Type'].str.contains('Lecture', case=False, na=False)) & (data['rooms']['Capacity'] >= student_count)] if 'Type' in data['rooms'].columns else data['rooms']
                else:
                    room_candidates = data['rooms'][(data['rooms']['Type'].str.contains('Lab', case=False, na=False)) & (data['rooms']['Capacity'] >= student_count)] if 'Type' in data['rooms'].columns else data['rooms']
                if room_candidates.empty or qualified_instructors.empty:
                    return []
                domain = list(product(data['timeslots']['TimeSlotID'], room_candidates['RoomID'], qualified_instructors['InstructorID']))
                return domain

            var_types = ["Lecture", "Lab"] if course_type == "Lecture and Lab" else [course_type]

            for vtype in var_types:
                var_name = f"{course_id}_{vtype}_{section_id}"
                variables.append(var_name)

                initial_domain = make_domain_for_type(vtype)
                filtered = []
                for ts, room, inst in initial_domain:
                    # instructor preference: Skip forbidden days like "Not on Monday"
                    pref = _get(data['instructors'].loc[data['instructors']['InstructorID'] == inst].squeeze(), 'PreferredSlots', default=None)
                    if pref and "Not on" in str(pref):
                        forbidden = str(pref).split("Not on")[-1].strip()
                        # if forbidden matches a day string or contains it, remove those timeslots
                        if ts in day_to_slots.get(forbidden, []):
                            continue
                    filtered.append((ts, room, inst))

                domains[var_name] = filtered
                if not filtered:
                    empty_domain_reasons[var_name] = f"No valid assignments found for {var_name}"

    constraints = [(v1, v2) for i, v1 in enumerate(variables) for v2 in variables[i+1:]]
    print("✅ CSP formulation complete.\n")
    return variables, domains, constraints, empty_domain_reasons

# ---------- CONSISTENCY ----------

def is_consistent(val1, val2, v1, v2):
    t1, r1, i1 = val1
    t2, r2, i2 = val2
    # same time slot conflicts (same room or same instructor)
    if t1 == t2 and (r1 == r2 or i1 == i2):
        return False
    # same section conflict: a section cannot have two classes at the same timeslot
    sec1 = '_'.join(v1.split('_')[2:])
    sec2 = '_'.join(v2.split('_')[2:])
    if t1 == t2 and sec1 == sec2:
        return False
    return True

def revise(domains, v1, v2):
    old_len = len(domains[v1])
    domains[v1] = [d1 for d1 in domains[v1] if any(is_consistent(d1, d2, v1, v2) for d2 in domains[v2])]
    return len(domains[v1]) < old_len

def ac3(variables, domains, constraints):
    queue = deque(constraints + [(b, a) for a, b in constraints])
    while queue:
        v1, v2 = queue.popleft()
        if revise(domains, v1, v2):
            if not domains[v1]:
                return False
            for neighbor in (x for x in variables if x not in (v1, v2)):
                queue.append((neighbor, v1))
    return True

# ---------- BACKTRACKING ----------

def select_mrv(variables, schedule, domains):
    unassigned = [v for v in variables if v not in schedule]
    return min(unassigned, key=lambda x: len(domains.get(x, []))) if unassigned else None

def solve_backtracking(variables, domains, schedule):
    if len(schedule) == len(variables):
        return schedule

    var = select_mrv(variables, schedule, domains)
    if var is None:
        return None
    for val in domains.get(var, []):
        if all(is_consistent(val, schedule[v], var, v) for v in schedule):
            schedule[var] = val
            result = solve_backtracking(variables, domains, schedule)
            if result:
                return result
            del schedule[var]
    return None

# ---------- OUTPUT ----------

def save_timetable(schedule, data, output_path):
    if not schedule:
        print("❌ No feasible timetable found.")
        return

    timetable = []
    for var, (ts, room, inst) in schedule.items():
        try:
            parts = var.split('_')
            course_id = parts[0]
            ctype = parts[1]
            section_id = '_'.join(parts[2:])
            course_row = data['courses'][data['courses']['CourseID'].astype(str) == str(course_id)].iloc[0]
            course_name = _get(course_row, 'CourseName', 'Title', default=course_id)
            ts_info = data['timeslots'].loc[data['timeslots']['TimeSlotID'] == ts].iloc[0]
            inst_name = data['instructors'].loc[data['instructors']['InstructorID'] == inst, 'Name'].iloc[0]
        except Exception:
            course_name = course_id
            ts_info = {'Day': '', 'StartTime': '', 'EndTime': ''}
            inst_name = inst

        timetable.append({
            'Day': ts_info.get('Day', ts_info['Day']) if isinstance(ts_info, dict) else ts_info['Day'],
            'Time': f"{ts_info.get('StartTime','') if isinstance(ts_info, dict) else ts_info['StartTime']} - {ts_info.get('EndTime','') if isinstance(ts_info, dict) else ts_info['EndTime']}",
            'Section': section_id,
            'Course': f"{course_name} ({ctype})",
            'Instructor': inst_name,
            'Room': room
        })

    df = pd.DataFrame(timetable)
    sort_cols = [c for c in ['Day', 'Time', 'Section'] if c in df.columns]
    if sort_cols:
        df.sort_values(by=sort_cols, inplace=True)
    df.to_excel(output_path, index=False)
    print(f"✅ Timetable saved to {output_path}")
