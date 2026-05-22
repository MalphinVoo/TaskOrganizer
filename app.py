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

# --- APP LAYOUT CONFIG ---
st.set_page_config(
    page_title="Task & Follow-Up Manager", 
    layout="wide"
)

# --- HEADER ---
st.title("📋 Task & Follow-Up Management System")
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
                    st.error("System collision error. Please wait a second
