from data_loader import load_data_from_excel
from csp import setup_csp, ac3, solve_backtracking, save_timetable
import os

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_path = os.path.join(base_dir, "data")
    output_path = os.path.join(base_dir, "output", "timetable.xlsx")

    dataset = load_data_from_excel(data_path)
    if not dataset:
        exit("❌ Failed to load dataset.")

    vars, domains, constraints, empty = setup_csp(dataset)
    if any(not d for d in domains.values()):
        print("⚠️ Some variables have empty domains. Check your data files.")
        exit()

    print("--- Running AC-3 ---")
    if ac3(vars, domains, constraints):
        print("✅ AC-3 completed successfully.")
        print("--- Starting Backtracking Solver ---")
        result = solve_backtracking(vars, domains, {})
        save_timetable(result, dataset, output_path)
    else:
        print("❌ No consistent solution exists (AC-3 failed).")
