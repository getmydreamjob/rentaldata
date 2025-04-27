
import streamlit as st
import pandas as pd

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

# Load the data
fmr_df = load_fmr_data()

# --- Streamlit Page Settings ---
st.set_page_config(page_title="Fair Market Rent Finder", layout="centered")
st.title("🏠 Fair Market Rent (FMR) Finder")
st.write("Find the HUD 2025 FMR Rent by ZIP Code and Bedroom Size.")

# --- Input Fields ---
zip_code = st.text_input("Enter ZIP Code (5 digits):")
bedrooms = st.selectbox("Select Number of Bedrooms:", options=[0,1,2,3,4], format_func=lambda x: f"{x} Bedroom(s)" if x > 0 else "Efficiency")

# --- Search Button ---
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
                    0: 'Efficiency (0BR)',
                    1: '1BR',
                    2: '2BR (Standard)',
                    3: '3BR',
                    4: '4BR'
                }.get(bedrooms, f'{bedrooms}BR')

                result_df = pd.DataFrame({
                    "Bedroom Size": [bedroom_label],
                    "Standard FMR": [f"${int(standard_rent):,}"],
                    "90% Payment": [f"${int(rent_90):,}"],
                    "110% Payment": [f"${int(rent_110):,}"]
                })

                st.success("✅ Estimated FMR Found:")
                st.table(result_df)
