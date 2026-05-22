import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import time

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("task_management.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Task (
                    task_id TEXT PRIMARY KEY,
                    date_recorded TEXT,
                    time_recorded TEXT,
                    description TEXT,
                    instructed_by TEXT,
                    task_assigned_to TEXT,
                    school TEXT,
                    other_description TEXT,
                    additional_note TEXT,
                    completed TEXT DEFAULT 'No',
                    entered_by TEXT)''')
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

# --- APP BRANDING CONFIG ---
LOGO_URL = "https://twuvisionschool.edu.my/wp-content/uploads/2021/04/vision-school-logo.png"
FAVICON_URL = "https://twuvisionschool.edu.my/wp-content/uploads/2021/04/cropped-vision-school-logo-32x32.png"

st.set_page_config(
    page_title="Task & Follow-Up Manager - Vision School", 
    page_icon=FAVICON_URL, 
    layout="wide"
)

# --- HEADER WITH LOGO (FIXED) ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        # Removed the unexpected 'fallback' keyword argument
        st.image(LOGO_URL, width=180)
    except Exception:
        # Backup display if the website host blocks Streamlit Cloud from reading the image url
        st.title("🏫")

with col_title:
    st.markdown("<h1 style='margin-top: 10px;'>Task & Follow-Up Management System</h1>", unsafe_allow_html=True)
st.markdown("---")

tabs = st.tabs(["➕ Record New Task", "🔄 Update Task (Follow-Up)", "📊 Reports & Preview"])

# --- TAB 1: RECORD NEW TASK ---
with tabs[0]:
    st.header("Create a New Task")
    
    now_ts = datetime.now()
    generated_task_id = now_ts.strftime("%Y%m%d_%H%M%S")
    
    with st.form("task_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Generated Task ID (Auto)", value=generated_task_id, disabled=True)
            instructed_by = st.text_input("Instructed By *")
            task_assigned_to = st.text_input("Task Assigned To *")
            school = st.selectbox("School", ["SRV", "SMV", "VIS", "Dormitory", "other"])
            
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
            if not description or not instructed_by or not task_assigned_to or not entered_by or (school == "other" and not other_description):
                st.error("Please fill in all required (*) fields.")
            else:
                conn = get_db_connection()
                c = conn.cursor()
                try:
                    date_str = now_ts.strftime("%Y-%m-%d")
                    time_str = now_ts.strftime("%H:%M:%S")
                    
                    c.execute('''INSERT INTO Task VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (generated_task_id, date_str, time_str, description, 
                               instructed_by, task_assigned_to, school, other_description, additional_note, completed, entered_by))
                    conn.commit()
                    st.success(f"Task {generated_task_id} successfully saved!")
                    time.sleep(1)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("System collision error. Please wait a second and submit again.")
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
                    c.execute('''INSERT INTO FollowUp (task_id, date_recorded, time_recorded, description, mark_as_completed, entered_by) 
                                 VALUES (?, ?, ?, ?, ?, ?)''',
                              (selected_task_id, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), fu_description, fu_completed, fu_entered_by))
                    if fu_completed == "Yes":
                        c.execute("UPDATE Task SET completed = 'Yes' WHERE task_id = ?", (selected_task_id,))
                    conn.commit()
                    conn.close()
                    st.success(f"Follow-up logged for Task {selected_task_id}!")

# --- TAB 3: REPORTS & PREVIEW ---
with tabs[2]:
    st.header("Generate & Retrieve Reports")
    
    conn = get_db_connection()
    tasks = pd.read_sql_query("SELECT * FROM Task", conn)
    followups = pd.read_sql_query("SELECT * FROM FollowUp", conn)
    conn.close()
    
    if tasks.empty:
        st.info("No records to report.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_type = st.radio("1. Filter Report By Time:", ["All Records", "Date", "Month", "Year"], horizontal=True)
        with col_f2:
            unique_assignees = ["All Persons"] + sorted(tasks['task_assigned_to'].dropna().unique().tolist())
            selected_assignee = st.selectbox("2. Retrieve By Assigned Person:", unique_assignees)

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
            
        if selected_assignee != "All Persons":
            filtered_tasks = filtered_tasks[filtered_tasks['task_assigned_to'] == selected_assignee]
            
        filtered_tasks = filtered_tasks.drop(columns=['datetime_obj'])
        
        st.subheader(f"Primary Tasks Summary ({selected_assignee})")
        st.dataframe(filtered_tasks, use_container_width=True)
        
        st.subheader("Associated Follow-Up History")
        visible_task_ids = filtered_tasks['task_id'].tolist()
        filtered_fu = followups[followups['task_id'].isin(visible_task_ids)]
        
        if not filtered_fu.
