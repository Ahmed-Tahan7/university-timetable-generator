import pandas as pd
import os

def load_data_from_excel(folder_path):
    """
    Reads all required Excel files from the 'data' folder into a dictionary of DataFrames,
    and automatically renames columns to match what the CSP solver expects.
    """

    file_names = {
        'courses': 'Courses.xlsx',
        'instructors': 'Instructor.xlsx',
        'rooms': 'Halls.xlsx',
        'timeslots': 'TimeSlots.xlsx',
        'sections': 'Sections.xlsx'
    }

    # Column name mappings for compatibility
    COLUMN_MAP = {
        'courses': {
            'CourseCode': 'CourseID',
            'Title': 'CourseName',
            'Year': 'Year',
            'Semester': 'Semester'
        },
        'instructors': {
            'InstructorID': 'InstructorID',
            'Name': 'Name',
            'PreferredSlots': 'PreferredSlots',
            'QualifiedCourses': 'QualifiedCourses'
        },
        'rooms': {
            'Space': 'RoomID',
            'Capacity (Seats)': 'Capacity',
            'Type of Space': 'Type'
        },
        'timeslots': {
            'Day': 'Day',
            'StartTime': 'StartTime',
            'EndTime': 'EndTime',
            'TimeSlotID': 'TimeSlotID'
        },
        'sections': {
            'SectionNumber': 'SectionID',
            'StudentNumber': 'StudentCount'
        }
    }

    data = {}
    print("\n--- Loading Excel Data ---")

    for key, name in file_names.items():
        file_path = os.path.join(folder_path, name)
        if not os.path.exists(file_path):
            print(f"⚠️ File missing: {name}")
            continue

        df = pd.read_excel(file_path)
        df.rename(columns=COLUMN_MAP.get(key, {}), inplace=True)
        data[key] = df
        print(f"  -> Loaded {name} ({len(df)} rows)")

    # ✅ Generate missing TimeSlotID if not present
    if 'timeslots' in data and 'TimeSlotID' not in data['timeslots'].columns:
        data['timeslots']['TimeSlotID'] = [f"TS{i}" for i in range(len(data['timeslots']))]
        print("  -> Added TimeSlotID column to TimeSlots.xlsx")

    # ✅ Ensure 'Courses' column exists in Sections (if not, warn)
    if 'sections' in data and 'Courses' not in data['sections'].columns:
        print("⚠️ WARNING: 'Courses' column missing in Sections.xlsx — add one like 'CS101, CS102'.")

    # ✅ Clean up text fields
    for key, df in data.items():
        data[key] = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)

    print("✅ Data loaded and standardized successfully!\n")
    return data
