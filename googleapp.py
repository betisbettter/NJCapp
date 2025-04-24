import streamlit as st
import psycopg2
import pandas as pd
import os
from datetime import datetime, time, timedelta
import re



# === 📌 Database Connection & Utility Functions ===

# User passwords
user_passwords = {
    "Emily": "Kali",
    "Anthony": "TuaTime",
    "Greg": "GoJets",
    "Jeff": "Champion",
    "Dave": "BlackBird",
    "Sean": "BlueCat",
    "Cam": "YellowDog",
    "Joanna": "PinkPirate",
    "Brandon": "RedDog",
    "Jarren": "BlueJay",
    "Ingy": "Siberia",
    "Claire": "GoodDay",
    "Aimee": "HappyKid",
    "Manu": "GoDolphins"
}

# Load database credentials from Streamlit Secrets
DB_URL = st.secrets["database"]["url"]

# Function to connect to the PostgreSQL database
def get_connection():
    return psycopg2.connect(DB_URL, sslmode="require")
#Punch clock integration functions
def extract_date_from_filename(filename):
    """Extracts YYYYMMDD date from filename and converts it to a date object."""
    match = re.search(r"(\d{8})", filename)  # Looks for an 8-digit number in filename
    if match:
        return datetime.strptime(match.group(1), "%Y%m%d").date()  # Convert to date
    return None  # Return None if no date found 

def extract_punch_clock_data(file_path, filename):
    """
    Extracts the employee name, total hours worked, and week start date from the punch clock CSV.
    """
    df = pd.read_csv(file_path, header=None, encoding="latin1")
    raw_name = df.iloc[2, 3] if pd.notna(df.iloc[2, 3]) else None
  # name = re.sub(r"\s*\(\d+\)", "", raw_name).strip() if raw_name else None
  # first name extract
    name = re.sub(r"\s*\(\d+\)", "", raw_name).strip().split()[0] if raw_name else None 

    # Extract total hours from row 11, column 5
    total_hours = df.iloc[11, 5] if pd.notna(df.iloc[11, 5]) else None

    # Extract week start date from filename
    week_start_date = extract_date_from_filename(filename)

    return {"name": name, "total_hours": total_hours, "week_start_date": week_start_date}

def insert_punch_clock_data(name, total_hours, week_start):
    """
    Inserts or updates punch clock data into the PunchClockData table.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO PunchClockData (name, week_start, total_hours)
                VALUES (%s, %s, %s)
                ON CONFLICT (name, week_start) DO UPDATE
                SET total_hours = EXCLUDED.total_hours;
                """,
                (name, week_start, total_hours)
            )
        conn.commit()

def get_punch_clock_hours(name, week_start):
    """Retrieve total hours worked from PunchClockData for a given week."""
    with get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT total_hours FROM PunchClockData WHERE name = %s AND week_start = %s",
            conn,
            params=(name, week_start)
        )
        if not df.empty:
            return df.iloc[0]["total_hours"]  # Return first match
        return None  # If no data found, return None
    
def get_available_weeks():
    """Fetch distinct week start dates from the PunchClockData table."""
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT DISTINCT week_start FROM PunchClockData ORDER BY week_start DESC", conn)
    return df["week_start"].tolist() if not df.empty else []
    
def insert_payday_data(name, date, num_breaks):
    """Insert Payday data using ONLY punch clock hours. If no data is found, set hours to 0."""
    
    # Calculate week start date (Monday of that week)
    week_start = date - timedelta(days=date.weekday())  

    # Fetch official hours from PunchClockData
    official_hours = get_punch_clock_hours(name, week_start)

    # 🛑 If no punch clock data is found, set total hours to 0
    total_time = official_hours if official_hours is not None else 0  

    # Calculate total pay based on official punch clock time
    total_pay = calculate_total_pay(name, total_time, num_breaks)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Payday (name, date, num_breaks, total_pay)
                VALUES (%s, %s, %s, %s)
                """,
                (name, date, num_breaks, total_pay)  
            )
        conn.commit()

def calculate_total_pay(name, total_time, num_breaks):
    """Calculates the total pay based on hourly or break pay structure."""
    
    if name not in pay_rates:
        return 0  # Default to 0 if no pay rate is set

    pay_type = pay_rates[name]["type"]
    rate = pay_rates[name]["rate"]

    if pay_type == "hourly":
        return round((total_time or 0) * rate, 2)  # Multiply hours worked by hourly rate
    elif pay_type == "break":
        return round(num_breaks * rate, 2)  # Multiply breaks by break rate
    else:
        return 0

# Function to insert data into the Operations table
def insert_operations_data(name, sort_or_ship, whos_show, show_date, break_numbers):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Operations (name, sort_or_ship, whos_show, show_date, Break_Numbers)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (name, sort_or_ship, whos_show, show_date, break_numbers)  # ✅ Insert Break_Numbers
            )
        conn.commit()

# Function to archive and reset data
def archive_and_reset():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS Operations_Archive AS SELECT * FROM Operations WHERE 1=0;")
            cursor.execute("CREATE TABLE IF NOT EXISTS Payday_Archive AS SELECT * FROM Payday WHERE 1=0;")

            cursor.execute("INSERT INTO Operations_Archive SELECT * FROM Operations;")
            cursor.execute("INSERT INTO Payday_Archive SELECT * FROM Payday;")

            cursor.execute("DELETE FROM Operations;")
            cursor.execute("DELETE FROM Payday;")
        conn.commit()

# Function to retrieve archived data
def get_archived_data():
    with get_connection() as conn:
        df_operations_archive = pd.read_sql_query("SELECT * FROM Operations_Archive", conn)
        df_payday_archive = pd.read_sql_query("SELECT * FROM Payday_Archive", conn)
    return df_operations_archive, df_payday_archive


# Users List
all_names = ["Select your name"] + sorted([
    "Emily", "Anthony", "Greg", "Jeff", "Dave", "Sean", "Cameron",
    "Joanna", "Brandon", "Jarren", "Ingy", "Claire", "Aimee", "Manu", "Kylie", "Kaley"
])

pay_rates = {
    "Emily": {"type": "break", "rate": 15.00},  
    "Anthony": {"type": "break", "rate": 15.00},  
    "Greg": {"type": "hourly", "rate": 18.50},
    "Jeff": {"type": "hourly", "rate": 25.00},
    "Dave": {"type": "hourly", "rate": 25.00},
    "Sean": {"type": "hourly", "rate": 22.00},
    "Cameron": {"type": "hourly", "rate": 20.00},
    "Joanna": {"type": "break", "rate": 15.00},
    "Brandon": {"type": "hourly", "rate": 20.00},
    "Claire": {"type": "hourly", "rate": 22.00},
    "Aimee": {"type": "hourly", "rate": 22.00},
    "Kylie": {"type": "hourly", "rate": 21.00},
    "Kaley": {"type": "hourly", "rate": 20.00},

}

def calculate_total_pay(name, total_time, num_breaks):
    """Calculates the total pay based on hourly or break pay structure."""
    if name not in pay_rates:
        return 0  # Default to 0 if no pay rate is set

    pay_type = pay_rates[name]["type"]
    rate = pay_rates[name]["rate"]

    if pay_type == "hourly":
        return round(total_time * rate, 2)  # Multiply hours worked by hourly rate
    elif pay_type == "break":
        return round(num_breaks * rate, 2)  # Multiply breaks by break rate
    else:
        return 0  # Default case (should never happen)

def generate_weekly_payroll_report(week_start):
    """
    Generates a payroll report including all employees with either punch clock data or breaks submitted.
    """
    week_end = week_start + timedelta(days=6)  # Define the full week range

    with get_connection() as conn:
        # Fetch all unique employee names from both PunchClockData and Payday
        employee_df = pd.read_sql_query("""
            SELECT DISTINCT name FROM (
                SELECT name FROM PunchClockData
                UNION
                SELECT name FROM Payday
            ) AS all_names
        """, conn)

        # Fetch punch clock data for the selected week
        punch_clock_df = pd.read_sql_query(
            "SELECT name, total_hours FROM PunchClockData WHERE week_start = %s",
            conn,
            params=(week_start,)
        )

        # Fetch and sum `num_breaks` from `Payday` where the date is within the selected week
        breaks_df = pd.read_sql_query(
            """
            SELECT name, COALESCE(SUM(num_breaks), 0) AS total_breaks
            FROM Payday 
            WHERE date BETWEEN %s AND %s 
            GROUP BY name
            """,
            conn,
            params=(week_start, week_end)
        )

    # Merge punch clock and breaks data to ensure all employees are included
    payroll_df = pd.merge(employee_df, punch_clock_df, on="name", how="left")
    payroll_df = pd.merge(payroll_df, breaks_df, on="name", how="left")

    # Set missing hours and breaks to 0 if no data exists
    payroll_df["total_hours"] = payroll_df["total_hours"].fillna(0)
    payroll_df["total_breaks"] = payroll_df["total_breaks"].fillna(0)

    # Compute total pay based on hours and breaks
    payroll_df["total_pay"] = payroll_df.apply(
        lambda row: calculate_total_pay(row["name"], row["total_hours"], row["total_breaks"]),
        axis=1
    )

    # Select relevant columns
    payroll_df = payroll_df[["name", "total_hours", "total_breaks", "total_pay"]]

    # Insert the payroll data into the PayrollSummary table
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for _, row in payroll_df.iterrows():
                cursor.execute(
                    """
                    INSERT INTO PayrollSummary (week_start, name, total_hours, total_breaks, total_pay)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (week_start, name) DO UPDATE
                    SET total_hours = EXCLUDED.total_hours,
                        total_breaks = EXCLUDED.total_breaks,
                        total_pay = EXCLUDED.total_pay;
                    """,
                    (week_start, row["name"], row["total_hours"], row["total_breaks"], row["total_pay"])
                )
        conn.commit()

    return payroll_df




# === APP MAIN SECTION  ===


# Display Image (if available)
if os.path.exists("NJCimage2.png"):
    st.image("NJCimage2.png", use_container_width=True)  # Adjust width as needed
else:
    st.warning("⚠️ Image not found. Please upload `NJCimage.png`.")


# === 📌 User Authentication Section ===
with st.expander("🔐 User Authentication", expanded=True):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>Login to Access Your Work</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)

    # Login form
    selected_user = st.selectbox("Select Your Name", all_names)
    entered_password = st.text_input("Enter Password", type="password")

    # Authentication logic
    if entered_password:
        if selected_user in user_passwords and entered_password == user_passwords[selected_user]:
            st.success(f"✅ Welcome, {selected_user}!")
            st.session_state["authenticated_user"] = selected_user  # Store in session
        else:
            st.error("❌ Incorrect password.")
            st.session_state.pop("authenticated_user", None)  # Remove from session if incorrect

    # Logout button
    if "authenticated_user" in st.session_state:
        if st.button("🚪 Logout"):
            st.session_state.pop("authenticated_user")  # Remove user from session
            st.rerun()

# === 📌 Expander 2: Get Paid Section ===
with st.expander("💰 Get Paid (Click to Expand/Collapse)", expanded=False):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>Get Paid</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)

    if "authenticated_user" not in st.session_state:
        st.error("⚠️ Please log in first.")
    else:
        with st.form("base_data_form"):
            name = st.session_state["authenticated_user"]  # Use authenticated user
            date = st.date_input("📅 Date *", key="date")
            num_breaks = st.number_input("☕ Number of Breaks", min_value=0, step=1, key="num_breaks")

            submit_button = st.form_submit_button("💾 Save Pay Data", use_container_width=True)

        if submit_button:
            week_start = date - timedelta(days=date.weekday())
            official_hours = get_punch_clock_hours(name, week_start)

            if official_hours is None:
                st.warning(f"⚠️ No punch clock data found for {name}. Hours set to 0, but breaks are recorded.")
            
            insert_payday_data(name, date, num_breaks)
            st.success("✅ Data saved!")

# === 📌 Expander 3: Track Shows ===
with st.expander("🎬 Track Shows (Click to Expand/Collapse)", expanded=False):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>Track Shows</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)

    if "authenticated_user" not in st.session_state:
        st.error("⚠️ Please log in first.")
    else:
        name = st.session_state["authenticated_user"]  # Use the authenticated name

    
    num_entries = st.number_input("Number of entries *", min_value=1, step=1, key="num_shows")

    show_data = []
    for i in range(num_entries):
        st.markdown(f"### Entry {i+1}")
        col1, col2 = st.columns(2)

        with col1:
            sort_or_ship = st.selectbox(f"Sort or Ship", ["Sort", "Ship"], key=f"sort_or_ship_{i}")
            whos_show = st.text_input(f"Who's Show", key=f"whos_show_{i}")

        with col2:
            show_date = st.date_input(f"Show Date", key=f"show_date_{i}")
            break_numbers = st.text_input(f"Break Numbers Worked On", key=f"break_numbers_{i}")

        show_data.append({
            "sort_or_ship": sort_or_ship,
            "whos_show": whos_show,
            "show_date": show_date,
            "break_numbers": break_numbers  # ✅ New field added
        })

    show_submit = st.button("Submit Show Data")

    if show_submit:
        for show in show_data:
            insert_operations_data(
                name, 
                show["sort_or_ship"], 
                show["whos_show"], 
                show["show_date"], 
                show["break_numbers"]  # ✅ Pass new value to database function
            )
        st.success("✅ Show Data submitted successfully!")


    # === 📌 Expander 4: View Data ===
# === 📌 Expander 4: View Data ===
with st.expander("📊 View Your Data (Click to Expand/Collapse)", expanded=False):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>Your Work</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)

    if "authenticated_user" not in st.session_state:
        st.error("⚠️ Please log in first.")
    else:
        selected_user = st.session_state["authenticated_user"]
        st.subheader(f"📊 Your Work Log, {selected_user}")

        try:
            with st.spinner("🔄 Loading your work summary..."):
                df_operations = pd.read_sql_query(
                    "SELECT * FROM Operations WHERE name = %s",
                    get_connection(),
                    params=(selected_user,)
                )
                st.subheader("📋 Show Log")
                st.dataframe(df_operations)

            with st.spinner("🔄 Loading your Payroll report..."):
                df_payday = pd.read_sql_query(
                    "SELECT * FROM payrollsummary WHERE name = %s",
                    get_connection(),
                    params=(selected_user,)
                )
                st.subheader("💰 Payroll Summary")
                st.dataframe(df_payday)

        except Exception as e:
            st.error(f"❌ Failed to fetch data: {e}")


# === 📌 Admin View (Secure with Password) ===
with st.expander("Admin Access (Click to Expand/Collapse)", expanded=False):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>Admin View</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)
    admin_password = st.text_input("Enter Admin Password", type="password")

    if admin_password == "leroy":
        st.success("Access granted! Viewing all submissions.")

    #generate payroll report
        # Fetch available weeks from database
        available_weeks = get_available_weeks()

        if available_weeks:
            selected_week_start = st.selectbox("Select week start date for payroll report generation", available_weeks, format_func=lambda x: x.strftime("%Y-%m-%d"))
        else:
            st.warning("⚠️ No Punch Clock data available.")
            selected_week_start = None

        if selected_week_start and st.button("📊 Generate Payroll Report"):
            payroll_df = generate_weekly_payroll_report(selected_week_start)

            # Display the report in Streamlit
            st.subheader("📋 Payroll Summary")
            st.dataframe(payroll_df)

            # Offer CSV download
            csv = payroll_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Payroll Report as CSV",
                data=csv,
                file_name=f"Payroll_Report_{selected_week_start}.csv",
                mime="text/csv"
            )

        if st.button("View Operations Table"):
            try:
                with st.spinner("🔄 Loading Operations table..."):
                    df_operations = pd.read_sql_query("SELECT * FROM Operations", get_connection())
                    st.subheader("📋 Operations Table")
                    st.dataframe(df_operations)

            except Exception as e:
                st.error(f"❌ Failed to fetch data: {e}")

        if st.button("Archive & Reset Data"):
            archive_and_reset()
            st.success("✅ Data has been archived and reset!")
            st.rerun()

        
        df_operations_archive, _ = get_archived_data()  # Ignore the payroll archive

        # Convert Operations Archive to CSV
        operations_csv = df_operations_archive.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Archived Operations Data",
            data=operations_csv,
            file_name="Archived_Operations.csv",
            mime="text/csv"
        )


# === 📂 Expander: Upload Multiple Punch Clock CSVs ===
with st.expander("📂 Upload Weekly Punch Clock Data"):
    st.markdown("""
        <h2 style='text-align: center; font-size: 24px;'>Upload Punch Clock Data</h2>
        <hr style='border: 1px solid gray;'>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Upload Punch Clock CSVs", type=["csv"], accept_multiple_files=True)

    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Extract Data from Each CSV
            punch_clock_data = extract_punch_clock_data(uploaded_file, uploaded_file.name)

            # Display Extracted Data for Admin Review
            st.write(f"🧑 Employee: {punch_clock_data['name']}")
            st.write(f"⏳ Total Hours Worked: {punch_clock_data['total_hours']}")
            st.write(f"📆 Week Start Date: {punch_clock_data['week_start_date']}")  # ✅ Auto-detected!

            # Save to Database
            if punch_clock_data["week_start_date"]:
                insert_punch_clock_data(
                    punch_clock_data["name"], 
                    punch_clock_data["total_hours"], 
                    punch_clock_data["week_start_date"]
                )

        st.success("✅ All Punch Clock Data Successfully Saved to Database!")