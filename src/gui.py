import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import pandas as pd

# Import from src package
from src.data_loader import DataLoader
from src.csp_solver import generate_timetable_for_year, generate_all_timetables

class TimetableGeneratorGUI:
    """Main GUI application for timetable generation"""
    
    def __init__(self, root):
        """Initialize the GUI application"""
        self.root = root
        self.root.title("CSIT Timetable Generator")
        self.root.geometry("1000x700")
        
        # Data paths
        self.data_path = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.output_path = os.path.join(os.path.dirname(__file__), '..', 'output')
        
        # State
        self.loader = None
        self.is_generating = False
        self.current_timetable = None
        
        # Create UI
        self.create_widgets()
        
        # Load data on startup
        self.root.after(500, self.load_data_automatically)
        
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Title
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="CSIT Timetable Generator",
            font=('Arial', 24, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=20)
        
        # Main container
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Left panel - Controls
        control_frame = tk.Frame(main_frame, width=300)
        control_frame.pack(side='left', fill='y', padx=(0, 10))
        control_frame.pack_propagate(False)
        
        self.create_control_panel(control_frame)
        
        # Right panel - Display
        display_frame = tk.Frame(main_frame)
        display_frame.pack(side='left', fill='both', expand=True)
        
        self.create_display_panel(display_frame)
    
    def create_control_panel(self, parent):
        """Create control panel with buttons and options"""
        
        # Data status section
        status_label = tk.Label(
            parent,
            text="Data Status",
            font=('Arial', 12, 'bold')
        )
        status_label.pack(pady=(0, 10))
        
        self.status_text = tk.Text(
            parent,
            height=8,
            width=35,
            font=('Courier', 9),
            bg='#ecf0f1',
            relief='flat'
        )
        self.status_text.pack(pady=(0, 20))
        self.status_text.insert('1.0', 'Loading data...')
        self.status_text.config(state='disabled')
        
        # Year selection
        year_label = tk.Label(
            parent,
            text="Select Year",
            font=('Arial', 11, 'bold')
        )
        year_label.pack(pady=(0, 5))
        
        self.year_var = tk.StringVar(value="All Years")
        year_options = ["All Years", "Year 1", "Year 2", "Year 3", "Year 4"]
        
        year_dropdown = ttk.Combobox(
            parent,
            textvariable=self.year_var,
            values=year_options,
            state='readonly',
            width=30
        )
        year_dropdown.pack(pady=(0, 20))
        
        # Generate button
        self.generate_btn = tk.Button(
            parent,
            text="Generate Timetable",
            command=self.start_generation,
            font=('Arial', 12, 'bold'),
            bg='#27ae60',
            fg='white',
            activebackground='#229954',
            activeforeground='white',
            height=2,
            cursor='hand2',
            relief='flat'
        )
        self.generate_btn.pack(fill='x', pady=(0, 10))
        
        # View button
        self.view_btn = tk.Button(
            parent,
            text="View Generated Timetable",
            command=self.view_timetable,
            font=('Arial', 11),
            bg='#3498db',
            fg='white',
            activebackground='#2980b9',
            activeforeground='white',
            cursor='hand2',
            relief='flat'
        )
        self.view_btn.pack(fill='x', pady=(0, 10))
        
        # Open output folder button
        self.folder_btn = tk.Button(
            parent,
            text="Open Output Folder",
            command=self.open_output_folder,
            font=('Arial', 11),
            bg='#95a5a6',
            fg='white',
            activebackground='#7f8c8d',
            activeforeground='white',
            cursor='hand2',
            relief='flat'
        )
        self.folder_btn.pack(fill='x', pady=(0, 20))
        
        # Progress bar
        progress_label = tk.Label(
            parent,
            text="Progress",
            font=('Arial', 11, 'bold')
        )
        progress_label.pack()
        
        self.progress = ttk.Progressbar(
            parent,
            mode='indeterminate',
            length=280
        )
        self.progress.pack(pady=5)
        
        # Status message
        self.status_label = tk.Label(
            parent,
            text="Ready",
            font=('Arial', 9),
            fg='#7f8c8d'
        )
        self.status_label.pack(pady=(5, 0))
    
    def create_display_panel(self, parent):
        """Create display panel for logs and timetable view"""
        
        # Notebook for tabs
        notebook = ttk.Notebook(parent)
        notebook.pack(fill='both', expand=True)
        
        # Tab 1: Console/Logs
        log_frame = tk.Frame(notebook)
        notebook.add(log_frame, text="Console Output")
        
        # Console text area
        log_scroll = tk.Scrollbar(log_frame)
        log_scroll.pack(side='right', fill='y')
        
        self.log_text = tk.Text(
            log_frame,
            font=('Courier', 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            yscrollcommand=log_scroll.set,
            wrap='word'
        )
        self.log_text.pack(fill='both', expand=True)
        log_scroll.config(command=self.log_text.yview)
        
        self.log("Welcome to CSIT Timetable Generator!")
        self.log("=" * 60)
        
        # Tab 2: Timetable View
        table_frame = tk.Frame(notebook)
        notebook.add(table_frame, text="Timetable View")
        
        # Treeview for timetable
        tree_scroll_y = tk.Scrollbar(table_frame)
        tree_scroll_y.pack(side='right', fill='y')
        
        tree_scroll_x = tk.Scrollbar(table_frame, orient='horizontal')
        tree_scroll_x.pack(side='bottom', fill='x')
        
        self.timetable_tree = ttk.Treeview(
            table_frame,
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        self.timetable_tree.pack(fill='both', expand=True)
        
        tree_scroll_y.config(command=self.timetable_tree.yview)
        tree_scroll_x.config(command=self.timetable_tree.xview)
        
        # Info label
        info_label = tk.Label(
            table_frame,
            text="Generate a timetable to view it here",
            font=('Arial', 10),
            fg='#7f8c8d'
        )
        info_label.place(relx=0.5, rely=0.5, anchor='center')
    
    def log(self, message):
        """Add message to console log"""
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')
    
    def update_status_text(self, text):
        """Update the data status text box"""
        self.status_text.config(state='normal')
        self.status_text.delete('1.0', 'end')
        self.status_text.insert('1.0', text)
        self.status_text.config(state='disabled')
    
    def load_data_automatically(self):
        """Load data automatically on startup"""
        self.log("\nLoading data from CSV files...")
        
        try:
            self.loader = DataLoader(self.data_path)
            
            # Redirect loader output to our log
            import io
            import contextlib
            
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                success = self.loader.load_all()
            
            output = f.getvalue()
            for line in output.split('\n'):
                if line.strip():
                    self.log(line)
            
            if success:
                # Update status
                status_info = (
                    f"✓ Data Loaded\n"
                    f"──────────────────────\n"
                    f"Courses:     {len(self.loader.courses)}\n"
                    f"Sections:    {len(self.loader.sections)}\n"
                    f"Instructors: {len(self.loader.instructors)}\n"
                    f"Rooms:       {len(self.loader.rooms)}\n"
                    f"Timeslots:   {len(self.loader.timeslots)}"
                )
                self.update_status_text(status_info)
                self.status_label.config(text="Ready to generate", fg='#27ae60')
            else:
                self.update_status_text("✗ Data loading failed")
                self.status_label.config(text="Error loading data", fg='#e74c3c')
                messagebox.showerror("Error", "Failed to load data files. Check console for details.")
        
        except Exception as e:
            self.log(f"\nError loading data: {str(e)}")
            self.update_status_text("✗ Error")
            self.status_label.config(text="Error", fg='#e74c3c')
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
    
    def start_generation(self):
        """Start timetable generation in background thread"""
        if self.is_generating:
            messagebox.showwarning("Warning", "Generation already in progress!")
            return
        
        if not self.loader:
            messagebox.showerror("Error", "Data not loaded. Please restart the application.")
            return
        
        # Confirm action
        year_selection = self.year_var.get()
        confirm = messagebox.askyesno(
            "Confirm Generation",
            f"Generate timetable for: {year_selection}?\n\n"
            "This may take several minutes."
        )
        
        if not confirm:
            return
        
        # Disable buttons
        self.is_generating = True
        self.generate_btn.config(state='disabled', text="Generating...")
        self.view_btn.config(state='disabled')
        self.folder_btn.config(state='disabled')
        
        # Start progress bar
        self.progress.start(10)
        self.status_label.config(text="Generating timetable...", fg='#f39c12')
        
        # Clear log
        self.log("\n" + "=" * 60)
        self.log("STARTING TIMETABLE GENERATION")
        self.log("=" * 60)
        
        # Start generation in thread
        thread = threading.Thread(target=self.generate_timetable_thread)
        thread.daemon = True
        thread.start()
    
    def generate_timetable_thread(self):
        """Background thread for timetable generation"""
        try:
            year_selection = self.year_var.get()
            
            # Redirect output to log
            import io
            import contextlib
            
            f = io.StringIO()
            
            if year_selection == "All Years":
                with contextlib.redirect_stdout(f):
                    results = generate_all_timetables(self.data_path, self.output_path)
                
                output = f.getvalue()
                self.root.after(0, lambda: self.log_output(output))
                
                # Check success
                successful = sum(1 for path in results.values() if path is not None)
                
                self.root.after(0, lambda: self.generation_complete(
                    successful == 4,
                    f"Generated {successful}/4 timetables successfully!"
                ))
            else:
                # Single year
                year_num = int(year_selection.split()[1])
                
                with contextlib.redirect_stdout(f):
                    filepath = generate_timetable_for_year(year_num, self.data_path, self.output_path)
                
                output = f.getvalue()
                self.root.after(0, lambda: self.log_output(output))
                
                self.root.after(0, lambda: self.generation_complete(
                    filepath is not None,
                    f"Timetable for Year {year_num} generated successfully!" if filepath else "Generation failed!"
                ))
        
        except Exception as e:
            error_msg = f"Error during generation: {str(e)}"
            self.root.after(0, lambda: self.log(error_msg))
            self.root.after(0, lambda: self.generation_complete(False, error_msg))
    
    def log_output(self, output):
        """Log output from generation thread"""
        for line in output.split('\n'):
            if line.strip():
                self.log(line)
    
    def generation_complete(self, success, message):
        """Called when generation is complete"""
        self.is_generating = False
        
        # Stop progress bar
        self.progress.stop()
        
        # Re-enable buttons
        self.generate_btn.config(state='normal', text="Generate Timetable")
        self.view_btn.config(state='normal')
        self.folder_btn.config(state='normal')
        
        # Update status
        if success:
            self.status_label.config(text="Generation complete!", fg='#27ae60')
            messagebox.showinfo("Success", message)
        else:
            self.status_label.config(text="Generation failed", fg='#e74c3c')
            messagebox.showerror("Error", message)
    
    def view_timetable(self):
        """View a generated timetable"""
        # Check if output directory exists
        if not os.path.exists(self.output_path):
            messagebox.showinfo("No Files", "No timetable files found. Generate one first.")
            return
        
        # Ask which file to view
        output_files = [f for f in os.listdir(self.output_path) if f.endswith('.csv')]
        
        if not output_files:
            messagebox.showinfo("No Files", "No timetable files found. Generate one first.")
            return
        
        # Create file selection dialog
        file_dialog = tk.Toplevel(self.root)
        file_dialog.title("Select Timetable")
        file_dialog.geometry("400x300")
        file_dialog.transient(self.root)
        file_dialog.grab_set()
        
        tk.Label(
            file_dialog,
            text="Select a timetable to view:",
            font=('Arial', 12)
        ).pack(pady=10)
        
        listbox = tk.Listbox(file_dialog, font=('Arial', 10))
        listbox.pack(fill='both', expand=True, padx=20, pady=10)
        
        for file in sorted(output_files):
            listbox.insert('end', file)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                filename = listbox.get(selection[0])
                file_dialog.destroy()
                self.load_and_display_timetable(filename)
        
        tk.Button(
            file_dialog,
            text="View",
            command=on_select,
            bg='#3498db',
            fg='white',
            font=('Arial', 11),
            cursor='hand2'
        ).pack(pady=10)
    
    def load_and_display_timetable(self, filename):
        """Load and display a timetable CSV file"""
        try:
            filepath = os.path.join(self.output_path, filename)
            df = pd.read_csv(filepath)
            
            # Clear existing tree
            self.timetable_tree.delete(*self.timetable_tree.get_children())
            
            # Configure columns
            self.timetable_tree['columns'] = list(df.columns)
            self.timetable_tree['show'] = 'headings'
            
            # Set column headings
            for col in df.columns:
                self.timetable_tree.heading(col, text=col)
                self.timetable_tree.column(col, width=100)
            
            # Insert data
            for _, row in df.iterrows():
                self.timetable_tree.insert('', 'end', values=list(row))
            
            self.log(f"\nLoaded timetable: {filename}")
            self.log(f"Total sessions: {len(df)}")
            
            messagebox.showinfo("Success", f"Loaded {filename}\n{len(df)} sessions")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load timetable: {str(e)}")
    
    def open_output_folder(self):
        """Open the output folder in file explorer"""
        try:
            if not os.path.exists(self.output_path):
                os.makedirs(self.output_path)
            
            # Platform-specific folder opening
            import platform
            if platform.system() == 'Windows':
                os.startfile(self.output_path)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{self.output_path}"')
            else:  # Linux
                os.system(f'xdg-open "{self.output_path}"')
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {str(e)}")


def run_gui():
    """Initialize and run the GUI application"""
    root = tk.Tk()
    app = TimetableGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()