import streamlit as st
import time
import datetime
import pandas as pd
import os

# File for persisting data
data_file = "lag_time_data.csv"

# Load existing data if available
def load_data():
    if os.path.exists(data_file):
        try:
            df = pd.read_csv(data_file)

            # Ensure at least one valid column exists before processing
            if df.empty or len(df.columns) == 0:
                st.warning("⚠️ CSV file is empty or corrupted. Initializing fresh data.")
                return {}

            if "sample_name" not in df.columns:
                df.insert(0, "sample_name", df.index.astype(str))  # Use index as sample names

            df['start_time'] = pd.to_datetime(df['start_time'])
            current_time = time.time()

            for idx, row in df.iterrows():
                if row['status'] == 'Running':
                    elapsed_time = current_time - row['start_time'].timestamp()
                    if row['initial_pump_speed'] > 0:
                        remaining_time = max(0, int(row['initial_lag_time'] * (row['initial_pump_speed'] / st.session_state.global_pump_speed) - elapsed_time))
                        df.at[idx, 'remaining_time'] = remaining_time
                    else:
                        df.at[idx, 'remaining_time'] = row['remaining_time']

                    if remaining_time == 0:
                        df.at[idx, 'status'] = 'Completed'

            return df.set_index("sample_name").to_dict(orient="index")

        except Exception as e:
            st.error(f"Error loading data: {e}")
            return {}

    return {}

# Save session state to file
def save_data():
    for sample, data in st.session_state.samples.items():
        if "start_time" in data:
            data["start_time_human_readable"] = datetime.datetime.fromtimestamp(data["start_time"]).strftime('%Y-%m-%d %H:%M:%S')
    
    df = pd.DataFrame.from_dict(st.session_state.samples, orient="index")
    df.to_csv(data_file)
    # Create the dataframe and save it
    df = pd.DataFrame.from_dict(st.session_state.samples, orient="index")
    df.to_csv(data_file)


# Function to generate a downloadable CSV file
def generate_csv():
    df = pd.DataFrame.from_dict(st.session_state.samples, orient="index")
    return df.to_csv(index=True).encode('utf-8')

# Initialize session state
if "samples" not in st.session_state or st.session_state.get('init', False) == False:
    # Reset session for new user or new session
    st.session_state.samples = {}
    st.session_state.paused = False  # Explicitly initialize paused
    st.session_state.init = True  # Mark that session has been initialized
    save_data()  # Initialize or reset the file data


# Initialize global_pump_speed if not already set
if "global_pump_speed" not in st.session_state:
    st.session_state.global_pump_speed = 1.0  # Set a default value, e.g., 1.0


# Function to update countdowns in real-time
def update_countdowns():
    current_time = time.time()
    for sample, data in st.session_state.samples.items():
        if data["status"] == "Running":
            elapsed_time = current_time - data["start_time"]
            
            # Adjust remaining time using updated pump speed
            if st.session_state.global_pump_speed > 0:
                remaining_time = max(0, int(data["initial_lag_time"] * (data["initial_pump_speed"] / st.session_state.global_pump_speed) - elapsed_time))
            else:
                remaining_time = data["remaining_time"]  # Keep last known value if pump speed is zero

            data["remaining_time"] = remaining_time
            
            if remaining_time == 0:
                data["status"] = "Completed"
                st.success(f"Sample {sample} has reached the surface!")
    
    save_data()
    st.rerun()

# Streamlit UI
st.title("Lag Time Calculator and Tracker")
st.sidebar.header("Global Controls")

# Global Pump Speed Control
new_pump_speed = st.sidebar.number_input("Global Pump Speed (spm)", min_value=0.1, step=0.1, value=st.session_state.global_pump_speed)
if new_pump_speed != st.session_state.global_pump_speed:
    st.session_state.global_pump_speed = new_pump_speed
    update_countdowns()

if st.sidebar.button("Pause" if not st.session_state.paused else "Resume"):
    st.session_state.paused = not st.session_state.paused

# Reset Button
if st.sidebar.button("Reset Session"):
    st.session_state.samples = {}  # Clear all sample data
    save_data()  # Overwrite the file with empty data
    st.rerun()  # Force re-run to reset everything


# Sidebar for Active Samples
st.sidebar.header("Active Samples")
for sample, data in st.session_state.samples.items():
    time_display = str(datetime.timedelta(seconds=int(data.get("remaining_time", 0))))

    # Make sure progress value is between 0 and 100
    if data["status"] == "Running":
        remaining_ratio = data["remaining_time"] / data["initial_lag_time"]
        progress = int(100 * (1 - min(max(remaining_ratio, 0), 1)))  # Ensure progress is between 0 and 100
        
        # Display progress bar
        st.sidebar.progress(progress, text=f"Sample {sample} Progress: {time_display} ({data['status']})")

        # Color-coded Status Indicator
        st.sidebar.markdown(f'<p style="color:red;">Sample {sample}: Running</p>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown(f'<p style="color:green;">Sample {sample}: Completed</p>', unsafe_allow_html=True)

# Input Form for Calculator
st.header("Lag Time Calculator")

# User Inputs for Diameters (in inches)
ext_diameter_hwdp = st.number_input("External Diameter of HWDP/Drill Pipe (in)", min_value=0.0, step=0.1)
ext_diameter_drill_collar = st.number_input("External Diameter of Drill Collar (in)", min_value=0.0, step=0.1)
int_diameter_riser = st.number_input("Internal Diameter of Riser (in)", min_value=0.0, step=0.1)
int_diameter_casing = st.number_input("Internal Diameter of Casing (in)", min_value=0.0, step=0.1)
diameter_open_hole = st.number_input("Diameter of Open Hole (in)", min_value=0.0, step=0.1)

# User Inputs for Lengths (in feet)
last_casing_shoe_depth = st.number_input("Last Casing Shoe Depth (ft)", min_value=0.0, step=1.0)
current_hole_depth = st.number_input("Current Hole Depth (ft)", min_value=0.0, step=1.0)
end_of_drill_collar = st.number_input("End of Drill Collar (ft)", min_value=0.0, step=1.0)
length_surface = st.number_input("Length of Surface (ft)", min_value=0.0, step=1.0)

# Derived Lengths
last_casing_depth = last_casing_shoe_depth - length_surface
length_open_hole = max(0, current_hole_depth - (last_casing_depth + length_surface))
length_drill_collar_in_casing = max(0, end_of_drill_collar - length_open_hole)
length_drill_collar_in_open_hole = end_of_drill_collar - length_drill_collar_in_casing
length_drill_pipe_in_casing = last_casing_depth - length_drill_collar_in_casing
length_drill_pipe_in_open_hole = max(0, length_open_hole - end_of_drill_collar)

# Annular Volume Calculations
av_open_hole = ((diameter_open_hole**2 - ext_diameter_drill_collar**2) * 0.000971 * length_drill_collar_in_open_hole) +                ((diameter_open_hole**2 - ext_diameter_hwdp**2) * 0.000971 * length_drill_pipe_in_open_hole)
av_cased_hole = ((int_diameter_casing**2 - ext_diameter_drill_collar**2) * 0.000971 * length_drill_collar_in_casing) +                 ((int_diameter_casing**2 - ext_diameter_hwdp**2) * 0.000971 * length_drill_pipe_in_casing)
av_surface = ((int_diameter_riser**2 - ext_diameter_hwdp**2) * 0.000971 * length_surface)

# Pump Output and Lag Time Calculation
pump_rating = st.number_input("Pump Rating (bbl/stroke)", min_value=0.01, step=0.01)

pump_output = st.session_state.global_pump_speed * pump_rating
st.write(f"Pump Output: {pump_output:.2f} bbls/min")

if pump_output > 0:
    lag_time = (av_open_hole + av_cased_hole + av_surface) / pump_output
    lag_time_seconds = int(lag_time * 60)  # Convert minutes to seconds
    st.success(f"Lag Time: {lag_time:.2f} minutes ({lag_time_seconds} seconds)")
else:
    st.warning("Pump output must be greater than 0 to calculate lag time.")
    lag_time_seconds = None



# Start Tracking Samples
# Start Tracking Samples
st.header("Start a New Sample Tracking")
sample_name = st.text_input("Sample Name (e.g., Sample_3000ft)")
if lag_time_seconds and st.button("Start Tracking"):
    if sample_name and sample_name not in st.session_state.samples:
        # Convert start_time to a human-readable format
        start_time_human_readable = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

        st.session_state.samples[sample_name] = {
            "initial_lag_time": lag_time_seconds,
            "status": "Running",
            "start_time": time.time(),
            "start_time_human_readable": start_time_human_readable,  # Save the human-readable start time
            "remaining_time": lag_time_seconds,
            "initial_pump_speed": st.session_state.global_pump_speed,
            "ext_diameter_hwdp": ext_diameter_hwdp,
            "int_diameter_casing": int_diameter_casing,
            "diameter_open_hole": diameter_open_hole,
            "current_hole_depth": current_hole_depth,
            "pump_rating": pump_rating,
            "pump_output": pump_output,
        }
        save_data()
    elif sample_name in st.session_state.samples:
        st.warning("Sample name must be unique!")
    else:
        st.warning("Please provide a sample name.")

# Download CSV Button
st.sidebar.header("Download Session Data")
st.sidebar.download_button(
    label="Download CSV", 
    data=generate_csv(),
    file_name="session_data.csv", 
    mime="text/csv")

# Auto-update countdown every second
if len(st.session_state.samples) > 0:
    time.sleep(1)
    update_countdowns()
