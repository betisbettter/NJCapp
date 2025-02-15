import streamlit as st
import pandas as pd

# Sample DataFrame
current_dataframe = pd.DataFrame({
    "Name": ["Alice", "Bob", "Charlie"],
    "Age": [25, 30, 35],
    "Role": ["Engineer", "Designer", "Manager"]
})

st.set_page_config(layout="wide")

# Main Section
st.title("No Job Cards Work Log")
st.subheader("Welcome to the NJC work log. Fill in the fields below so that you can get paid for the work that you do. Go Team!")

with st.sidebar:
    try:
        st.image("NJCimage.png", caption="Where the champions work", use_column_width=True)
    except Exception:
        st.warning("Image not found. Please upload NJCimage.png to the working directory.")

    
    # Initialize admin mode in session state
    if "admin_mode" not in st.session_state:
        st.session_state.admin_mode = False
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    # Admin Button
    if st.button("Admin"):
        st.session_state.admin_mode = True
        st.session_state.password_correct = False  # Reset access when Admin button is pressed

    # Admin Password Input
    if st.session_state.admin_mode:
        password = st.text_input("Enter Admin Password:", type="password")

        if password:
            if password == "leroy":
                st.session_state.password_correct = True
                st.success("Access Granted! Displaying Data:")
            else:
                st.session_state.password_correct = False
                st.error("Incorrect Password!")

    # Display DataFrame if access granted
    if st.session_state.password_correct:
        st.dataframe(current_dataframe)
