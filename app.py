import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fair Market Rent Finder", layout="centered")

# --- Load your FMR data ---
@st.cache_data
def load_fmr_data():
    try:
        df = pd.read_excel('FY25_FMRs_revised.xlsx', engine='openpyxl')
        df.columns = df.columns.str.replace('\n', ' ').str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame()

fmr_df = load_fmr_data()

# --- Session State Initialization ---
if "mode" not in st.session_state:
    st.session_state["mode"] = "FMR Rental Data"
if "num_results" not in st.session_state:
    st.session_state["num_results"] = 10  # Default top 10

# --- Extract clean 2-letter State Codes ---
if "State" not in fmr_df.columns:
    fmr_df["State"] = fmr_df["HUD Fair Market Rent Area Name"].apply(lambda x: x.split(",")[-1].strip()[:2])

valid_states = sorted(fmr_df["State"].dropna().unique().tolist())

# --- Streamlit App UI ---
st.title("🏠 Fair Market Rent (FMR) Finder")
st.write("Find the HUD 2025 FMR Rent by ZIP Code and Bedroom Size.")

# --- Mode Buttons ---
col1, col2 = st.columns(2)

with col1:
    if st.button("🏡 FMR Rental Data"):
        st.session_state["mode"] = "FMR Rental Data"
        st.session_state["num_results"] = 10

with col2:
    if st.button("💰 Highest Paying ZIPs"):
        st.session_state["mode"] = "Highest Paying ZIPs"
        st.session_state["num_results"] = 10

st.divider()

# --- Highest Paying ZIPs Mode ---
if st.session_state["mode"] == "Highest Paying ZIPs":
    selected_state = st.selectbox("Select State:", valid_states, key="state_select")
    bedrooms = st.selectbox("Select Bedroom Size:", options=[0,1,2,3,4], format_func=lambda x: f"{x} Bedroom(s)" if x > 0 else "Efficiency", key="high_bedroom_select")

    rent_type = st.selectbox("Select Rent Type:", options=["Standard FMR", "90% Payment", "110% Payment"], key="rent_type_select")

    # Minimum and Maximum Rent Input Fields
    min_rent = st.number_input("Minimum Rent ($)", min_value=0, value=0, step=500)
    max_rent = st.number_input("Maximum Rent ($)", min_value=0, value=10000, step=500)

    bedroom_map = {
        0: ('SAFMR 0BR', 'SAFMR 0BR - 90% Payment Standard', 'SAFMR 0BR - 110% Payment Standard'),
        1: ('SAFMR 1BR', 'SAFMR 1BR - 90% Payment Standard', 'SAFMR 1BR - 110% Payment Standard'),
        2: ('SAFMR 2BR', 'SAFMR 2BR - 90% Payment Standard', 'SAFMR 2BR - 110% Payment Standard'),
        3: ('SAFMR 3BR', 'SAFMR 3BR - 90% Payment Standard', 'SAFMR 3BR - 110% Payment Standard'),
        4: ('SAFMR 4BR', 'SAFMR 4BR - 90% Payment Standard', 'SAFMR 4BR - 110% Payment Standard')
    }

    rent_column_map = {
        "Standard FMR": 0,
        "90% Payment": 1,
        "110% Payment": 2
    }

    selected_rent_col = bedroom_map.get(bedrooms)[rent_column_map[rent_type]]

    # Filter the DataFrame based on the selected state and rent range
    filtered = fmr_df[fmr_df["State"] == selected_state]
    filtered = filtered[filtered[selected_rent_col].notna()]

    # Apply rent range filter
    filtered = filtered[(filtered[selected_rent_col] >= min_rent) & (filtered[selected_rent_col] <= max_rent)]

    # Add sorting functionality
    sort_order = st.selectbox("Sort by:", ["Ascending", "Descending"], key="sort_order")

    if sort_order == "Ascending":
        top_results = filtered[['ZIP Code', selected_rent_col]].sort_values(by=selected_rent_col, ascending=True)
    else:
        top_results = filtered[['ZIP Code', selected_rent_col]].sort_values(by=selected_rent_col, ascending=False)

    top_display = pd.DataFrame({
        "ZIP Code": top_results['ZIP Code'].astype(str),
        "Rent Amount": top_results[selected_rent_col].apply(lambda x: f"${int(x):,}")
    }).reset_index(drop=True)

    if top_display.empty:
        st.warning("No ZIP codes found in the selected rent range.")
    else:
        st.success(f"✅ Top ZIP Codes with Rent between ${min_rent:,} and ${max_rent:,} in {selected_state}:")
        st.table(top_display)

    if len(filtered) > len(top_display):
        if st.button("Show more"):
            st.session_state["num_results"] += 10
