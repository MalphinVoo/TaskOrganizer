import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("task_management.db")
    c = conn.cursor()
    # Create Task Table
    c.execute('''CREATE TABLE IF NOT EXISTS Task (
                    task_id TEXT PRIMARY KEY,
                    date_recorded TEXT,
                    time_recorded TEXT,
                    description TEXT,
                    instructed_by TEXT,
                    school TEXT,
                    other_description TEXT,
                    additional_note TEXT,
                    completed TEXT DEFAULT 'No',
                    entered_by TEXT)''')
    # Create Follow-Up Table
    c.execute('''CREATE TABLE IF NOT EXISTS FollowUp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    date_recorded TEXT,
                    time_recorded TEXT,
                    description TEXT,
                    mark_as_completed TEXT DEFAULT 'No',
                    entered_by TEXT,
                    FOREIGN KEY(task_id) REFERENCES Task(task_id))''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect("task_management.db")

# --- APP UI ---
st.set_page_config(page_title="Task & Follow-Up Manager", layout="wide")
st.title("📋 Task & Follow-Up Management System")

tabs = st.tabs(["➕ Record New Task", "🔄 Update Task (Follow-Up)", "📊 Reports & Preview"])

# --- TAB 1: RECORD NEW TASK ---
with tabs[0]:
    st.header("Create a New Task")
    
    with st.form("task_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            task_id = st.text_input("Task ID *").strip()
            instructed_by = st.text_input("Instructed By *")
            school = st.selectbox("School", ["SRV", "SMV", "VIS", "Dormitory", "other"])
            # Conditional input for 'other'
            other_description = ""
            if school == "other":
                other_description = st.text_input("Please specify 'Other' school *")
        
        with col2:
            entered_by = st.text_input("Entered By *")
            completed = st.selectbox("Completed", ["No", "Yes"], index=0)
            additional_note = st.text_area("Additional Note / Remark")
            
        description = st.text_area("Task / Description *")
        
        submit_task = st.form_submit_button("Save Task")
        
        if submit_task:
            if not task_id or not description or not instructed_by or not entered_by or (school == "other" and not other_description):
                st.error("Please fill in all required (*) fields.")
            else:
                conn = get_db_connection()
                c = conn.cursor()
                try:
                    now = datetime.now()
                    c.execute('''INSERT INTO Task VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (task_id, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), 
                               description, instructed_by, school, other_description, additional_note, completed, entered_by))
                    conn.commit()
                    st.success(f"Task {task_id} successfully saved!")
                except sqlite3.IntegrityError:
                    st.error(f"Error: Task ID '{task_id}' already exists. Use the Follow-Up tab to update it.")
                finally:
                    conn.close()

# --- TAB 2: FOLLOW-UP ---
with tabs[1]:
    st.header("Log a Task Follow-Up")
    
    conn = get_db_connection()
    tasks_df = pd.read_sql_query("SELECT task_id, description FROM Task", conn)
    conn.close()
    
    if tasks_df.empty:
        st.warning("No tasks available. Please create a task first.")
    else:
        # Create a dropdown labeled with ID and snippet of description
        task_options = tasks_df['task_id'].tolist()
        selected_task_id = st.selectbox("Select Task ID to Update", task_options)
        
        with st.form("follow_up_form", clear_on_submit=True):
            fu_description = st.text_area("Follow-Up Progress Description *")
            fu_completed = st.selectbox("Mark As Completed?", ["No", "Yes"], index=0)
            fu_entered_by = st.text_input("Follow-Up Entered By *")
            
            submit_fu = st.form_submit_button("Save Follow-Up")
            
            if submit_fu:
                if not fu_description or not fu_entered_by:
                    st.error("Please fill in all required fields.")
                else:
                    conn = get_db_connection()
                    c = conn.cursor()
                    now = datetime.now()
                    
                    # Insert into Follow-Up Table
                    c.execute('''INSERT INTO FollowUp (task_id, date_recorded, time_recorded, description, mark_as_completed, entered_by) 
                                 VALUES (?, ?, ?, ?, ?, ?)''',
                              (selected_task_id, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), fu_description, fu_completed, fu_entered_by))
                    
                    # If marked as completed in follow-up, optionally update the main Task status
                    if fu_completed == "Yes":
                        c.execute("UPDATE Task SET completed = 'Yes' WHERE task_id = ?", (selected_task_id,))
                        
                    conn.commit()
                    conn.close()
                    st.success(f"Follow-up logged for Task {selected_task_id}!")

# --- TAB 3: REPORTS & PREVIEW ---
with tabs[2]:
    st.header("Generate Reports")
    
    filter_type = st.radio("Filter Report By:", ["Date", "Month", "Year", "All Records"], horizontal=True)
    
    conn = get_db_connection()
    # Read fresh data
    tasks = pd.read_sql_query("SELECT * FROM Task", conn)
    followups = pd.read_sql_query("SELECT * FROM FollowUp", conn)
    conn.close()
    
    if tasks.empty:
        st.info("No records to report.")
    else:
        # Convert date string to datetime object for accurate filtering
        tasks['datetime_obj'] = pd.to_datetime(tasks['date_recorded'])
        
        if filter_type == "Date":
            target_date = st.date_input("Select Date", datetime.now())
            filtered_tasks = tasks[tasks['datetime_obj'].dt.date == target_date]
        elif filter_type == "Month":
            current_year = datetime.now().year
            target_month = st.slider("Select Month", 1, 12, int(datetime.now().month))
            filtered_tasks = tasks[(tasks['datetime_obj'].dt.month == target_month) & (tasks['datetime_obj'].dt.year == current_year)]
        elif filter_type == "Year":
            target_year = st.number_input("Select Year", min_value=2020, max_value=2030, value=int(datetime.now().year))
            filtered_tasks = tasks[tasks['datetime_obj'].dt.year == target_year]
        else:
            filtered_tasks = tasks.copy()
            
        # Drop the helper datetime column before displaying
        filtered_tasks = filtered_tasks.drop(columns=['datetime_obj'])
        
        st.subheader("Primary Tasks")
        st.dataframe(filtered_tasks, use_container_width=True)
        
        st.subheader("Associated Follow-Up History")
        # Filter follow ups belonging to the visible tasks
        visible_task_ids = filtered_tasks['task_id'].tolist()
        filtered_fu = followups[followups['task_id'].isin(visible_task_ids)]
        
        if not filtered_fu.empty:
            st.dataframe(filtered_fu, use_container_width=True)
        else:
            st.caption("No follow-up actions recorded for the filtered tasks.")
