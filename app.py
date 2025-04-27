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

# --- Streamlit App UI ---
st.title("🏠 Fair Market Rent (FMR) Finder")
st.write("Find the HUD 2025 FMR Rent by ZIP Code and Bedroom Size.")

# --- Button Selections ---
col1, col2 = st.columns(2)

app_mode = "FMR Rental Data"  # default mode

if col1.button("🏡 FMR Rental Data"):
    app_mode = "FMR Rental Data"

if col2.button("💰 Highest Paying ZIPs"):
    app_mode = "Highest Paying ZIPs"

st.divider()

# --- FMR Rental Data Mode ---
if app_mode == "FMR Rental Data":
    zip_code = st.text_input("Enter ZIP Code (5 digits):")
    bedrooms = st.selectbox("Select Number of Bedrooms:", options=[0,1,2,3,4], format_func=lambda x: f"{x} Bedroom(s)" if x > 0 else "Efficiency")

    if st.button("Find Rent"):
        if not zip_code:
            st.warning("Please enter a valid ZIP code.")
        else:
            zip_code = str(zip_code).zfill(5)
            record = fmr_df[fmr_df['ZIP Code'].astype(str).str.zfill(5) == zip_code]

            if record.empty:
                st.error("❌ ZIP code not found.")
            else:
                bedroom_map = {
                    0: ('SAFMR 0BR', 'SAFMR 0BR - 90% Payment Standard', 'SAFMR 0BR - 110% Payment Standard'),
                    1: ('SAFMR 1BR', 'SAFMR 1BR - 90% Payment Standard', 'SAFMR 1BR - 110% Payment Standard'),
                    2: ('SAFMR 2BR', 'SAFMR 2BR - 90% Payment Standard', 'SAFMR 2BR - 110% Payment Standard'),
                    3: ('SAFMR 3BR', 'SAFMR 3BR - 90% Payment Standard', 'SAFMR 3BR - 110% Payment Standard'),
                    4: ('SAFMR 4BR', 'SAFMR 4BR - 90% Payment Standard', 'SAFMR 4BR - 110% Payment Standard')
                }
                columns = bedroom_map.get(bedrooms)

                standard_rent = record.iloc[0].get(columns[0])
                rent_90 = record.iloc[0].get(columns[1])
                rent_110 = record.iloc[0].get(columns[2])

                if pd.isna(standard_rent) or pd.isna(rent_90) or pd.isna(rent_110):
                    st.error("❌ Rent information not available.")
                else:
                    bedroom_label = {
                        0: 'Efficiency',
                        1: '1 Bedroom',
                        2: '2 Bedrooms',
                        3: '3 Bedrooms',
                        4: '4 Bedrooms'
                    }.get(bedrooms, f'{bedrooms}BR')

                    result_df = pd.DataFrame({
                        "Bedroom Size": [bedroom_label],
                        "Standard FMR": [f"${int(standard_rent):,}"],
                        "90% Payment": [f"${int(rent_90):,}"],
                        "110% Payment": [f"${int(rent_110):,}"]
                    })

                    st.success("✅ Estimated FMR Found:")
                    st.table(result_df)

# --- Highest Paying ZIPs Mode ---
elif app_mode == "Highest Paying ZIPs":
    bedrooms = st.selectbox("Select Bedroom Size to Find Top 10 ZIPs:", options=[0,1,2,3,4], format_func=lambda x: f"{x} Bedroom(s)" if x > 0 else "Efficiency")

    bedroom_map = {
        0: 'SAFMR 0BR',
        1: 'SAFMR 1BR',
        2: 'SAFMR 2BR',
        3: 'SAFMR 3BR',
        4: 'SAFMR 4BR'
    }

    selected_col = bedroom_map.get(bedrooms)

    top10 = fmr_df[['ZIP Code', selected_col]].dropna().sort_values(by=selected_col, ascending=False).head(10)

    if top10.empty:
        st.warning("No data available for selected bedroom size.")
    else:
        top10_display = pd.DataFrame({
            "ZIP Code": top10['ZIP Code'].astype(str),
            "Rent Amount": top10[selected_col].apply(lambda x: f"${int(x):,}")
        }).reset_index(drop=True)

        st.success("✅ Top 10 Highest Paying ZIP Codes:")
        st.table(top10_display)