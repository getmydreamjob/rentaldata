import streamlit as st
import pandas as pd

st.set_page_config(page_title="Housing Tools App", layout="centered")

# --- Load FMR data ---
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

if "State" not in fmr_df.columns:
    fmr_df["State"] = fmr_df["HUD Fair Market Rent Area Name"].apply(lambda x: x.split(",")[-1].strip()[:2])

valid_states = sorted(fmr_df["State"].dropna().unique().tolist())

# --- Main title ---
st.title("🏠 Housing Tools App")

# --- Mode Buttons ---
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏡 FMR Rental Data"):
        st.session_state["mode"] = "FMR Rental Data"
        st.session_state["num_results"] = 10

with col2:
    if st.button("💰 Highest Paying ZIPs"):
        st.session_state["mode"] = "Highest Paying ZIPs"
        st.session_state["num_results"] = 10

with col3:
    if st.button("📈 Rent vs Buy Calculator"):
        st.session_state["mode"] = "Rent vs Buy Calculator"

st.divider()

# --- FMR Rental Data ---
if st.session_state["mode"] == "FMR Rental Data":
    st.subheader("FMR Rental Data Finder")
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

# --- Highest Paying ZIPs ---
elif st.session_state["mode"] == "Highest Paying ZIPs":
    st.subheader("Highest Paying ZIPs")
    selected_state = st.selectbox("Select State:", valid_states)
    bedrooms = st.selectbox("Select Bedroom Size:", options=[0,1,2,3,4], format_func=lambda x: f"{x} Bedroom(s)" if x > 0 else "Efficiency")
    rent_type = st.selectbox("Select Rent Type:", options=["Standard FMR", "90% Payment", "110% Payment"])
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
    filtered = fmr_df[(fmr_df["State"] == selected_state) & fmr_df[selected_rent_col].notna()]
    filtered = filtered[(filtered[selected_rent_col] >= min_rent) & (filtered[selected_rent_col] <= max_rent)]

    sort_order = st.selectbox("Sort by:", ["Ascending", "Descending"])
    top_results = filtered[['ZIP Code', selected_rent_col]].sort_values(
        by=selected_rent_col, ascending=(sort_order == "Ascending"))

    top_display = pd.DataFrame({
        "ZIP Code": top_results['ZIP Code'].astype(str),
        "Rent Amount": top_results[selected_rent_col].apply(lambda x: f"${int(x):,}")
    }).reset_index(drop=True)

    if top_display.empty:
        st.warning("No ZIP codes found in the selected rent range.")
    else:
        st.success(f"✅ Top ZIP Codes with Rent between ${min_rent:,} and ${max_rent:,} in {selected_state}:")
        st.table(top_display)

# --- Rent vs Buy Calculator ---
elif st.session_state["mode"] == "Rent vs Buy Calculator":
    st.subheader("Rent vs Buy Calculator")

    def parse_input(text):
        try:
            return float(text)
        except:
            return 0.0

    rent = parse_input(st.text_input("Monthly rent ($)*", placeholder="e.g. 2500"))
    price = parse_input(st.text_input("Home price ($)*", placeholder="e.g. 600000"))
    down_payment_pct = parse_input(st.text_input("Down payment (%)*", placeholder="e.g. 20"))
    mortgage_rate = parse_input(st.text_input("Mortgage rate (%)*", placeholder="e.g. 6.5"))
    loan_term = parse_input(st.text_input("Loan term (years)*", placeholder="e.g. 30"))
    property_tax = parse_input(st.text_input("Property tax per year ($)*", placeholder="e.g. 6000"))
    rent_increase = parse_input(st.text_input("Annual rent increase (%)", placeholder="e.g. 3"))
    rent_insurance = parse_input(st.text_input("Renters insurance per year ($)", placeholder="e.g. 200"))
    home_insurance = parse_input(st.text_input("Homeowners insurance per year ($)", placeholder="e.g. 1500"))
    maintenance = parse_input(st.text_input("Annual maintenance ($)", placeholder="e.g. 6000"))
    appreciation = parse_input(st.text_input("Home appreciation (%)", placeholder="e.g. 3"))
    sell_cost_pct = parse_input(st.text_input("Selling cost (% of final home price)", placeholder="e.g. 7"))
    years = st.slider("Years you plan to stay", 1, 30, 7)

    if st.button("Check Rent or Buy"):
        missing = []
        if rent == 0: missing.append("Monthly rent ($)")
        if price == 0: missing.append("Home price ($)")
        if down_payment_pct == 0: missing.append("Down payment (%)")
        if mortgage_rate == 0: missing.append("Mortgage rate (%)")
        if loan_term == 0: missing.append("Loan term (years)")
        if property_tax == 0: missing.append("Property tax per year ($)")
        
        if missing:
            st.warning(f"Please provide valid values for: {', '.join(missing)}")
        else:
            # You can paste the Rent vs Buy calculation logic here
            st.success("✅ Example result — insert Rent vs Buy logic here!")
