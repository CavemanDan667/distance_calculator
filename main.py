import streamlit as st
import pandas as pd
import requests
import time

st.title("Driving Distance Calculator with Google Routes API")

# API Key input
API_KEY = st.text_input("Enter your Google API Key", type="password")

# Initialize session state variables
if "pasted_data" not in st.session_state:
    st.session_state.pasted_data = "SW1A 1AA,EC1A 1BB\nM1 1AE,L1 8JQ\nBS1 4ST,BT1 5GS"
if "results" not in st.session_state:
    st.session_state.results = None

API_COST_PER_REQUEST = 0.005  # USD
MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds

# Text area for postcode pairs
if API_KEY:
    pasted_data = st.text_area(
        "Paste your postcode pairs (one pair per line, comma-separated):",
        st.session_state.pasted_data,
    )

    # Buttons for Calculate and Clear
    col1, col2 = st.columns([1, 1])
    calculate = col1.button("Calculate Distances")
    clear = col2.button("Clear")

    # Handle clearing data
    if clear:
        st.session_state.pasted_data = ""
        st.session_state.results = None
        st.rerun()  

    if calculate:
        rows = []
        for line in pasted_data.strip().split("\n"):
            try:
                origin, destination = [x.strip() for x in line.split(",")]
                rows.append({"Origin": origin, "Destination": destination})
            except ValueError:
                st.error(f"Invalid line format: '{line}' (should be 'Origin,Destination')")

        df = pd.DataFrame(rows)
        progress_bar = st.progress(0)
        api_usage = 0
        total_cost = 0
        results = []

        for index, row in df.iterrows():
            origin = row["Origin"]
            destination = row["Destination"]

            url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": API_KEY,
                "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status",
            }
            body = {
                "origins": [{"waypoint": {"address": origin}}],
                "destinations": [{"waypoint": {"address": destination}}],
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_UNAWARE",
            }

            success = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = requests.post(
                        url, headers=headers, json=body, timeout=10
                    )
                    data = response.json()

                    if response.status_code == 200 and isinstance(data, list) and len(data) > 0:
                        element = data[0]
                        status = element.get("status")

                        if status in (None, {}, "OK"):
                            distance_meters = element.get("distanceMeters")
                            duration_seconds = element.get("duration")

                            distance_km = (
                                round(distance_meters / 1000, 2)
                                if distance_meters
                                else "N/A"
                            )
                            duration_minutes = (
                                round(int(duration_seconds.rstrip("s")) / 60, 1)
                                if duration_seconds
                                else "N/A"
                            )
                            success = True
                            break
                        else:
                            error_message = f"API Error: {status}"
                    elif response.status_code == 400:
                        st.error("❌ Invalid API Key. Please check your API Key.")
                        st.stop()  # Stop further execution if the key is invalid.
                    else:
                        error_message = "Invalid response structure"
                except requests.exceptions.RequestException as e:
                    error_message = f"Request Exception: {e}"

                st.warning(f"Attempt {attempt}/{MAX_RETRIES} failed ({response.status_code}): {response.text}")
                time.sleep(RETRY_DELAY)

            if not success:
                distance_km = "Error"
                duration_minutes = "Error"

            results.append(
                {
                    "Origin": origin,
                    "Destination": destination,
                    "Distance (km)": distance_km,
                    "Duration (mins)": duration_minutes,
                }
            )

            api_usage += 1
            total_cost += API_COST_PER_REQUEST
            progress_bar.progress((index + 1) / len(df))

        st.success(f"✅ Completed {api_usage} requests.")
        st.info(f"💰 Estimated API cost: ${total_cost:.2f} USD")

        result_df = pd.DataFrame(results)
        st.session_state.results = result_df

        # Display results if available
        st.dataframe(st.session_state.results)

        csv = st.session_state.results.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Results as CSV",
            csv,
            "distances.csv",
            "text/csv",
            key="download-csv",
        )

else:
    st.warning("Please enter your Google API Key.")
