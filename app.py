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

if "mode" not in st.session_state:
    st.session_state["mode"] = "FMR Rental Data"

if "State" not in fmr_df.columns and not fmr_df.empty:
    fmr_df["State"] = fmr_df["HUD Fair Market Rent Area Name"].apply(lambda x: x.split(",")[-1].strip()[:2])

valid_states = sorted(fmr_df["State"].dropna().unique().tolist()) if not fmr_df.empty else []

st.title("🏠 Housing Tools App")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏡 FMR Rental Data"):
        st.session_state["mode"] = "FMR Rental Data"

with col2:
    if st.button("💰 Highest Paying ZIPs"):
        st.session_state["mode"] = "Highest Paying ZIPs"

with col3:
    if st.button("📈 Rent vs Buy Calculator"):
        st.session_state["mode"] = "Rent vs Buy Calculator"

st.divider()

# --- Helper ---
def parse_input(text):
    try:
        return float(text)
    except:
        return 0.0

def calculate_rent_cost(rent, rent_increase, insurance, years):
    total_rent = 0
    current_rent = rent
    for year in range(1, years + 1):
        total_rent += current_rent * 12
        current_rent *= (1 + rent_increase / 100)
    total_insurance = insurance * years
    return total_rent + total_insurance, total_rent, total_insurance

def calculate_buy_cost(price, down_payment_pct, mortgage_rate, loan_term, tax, insurance, maintenance, appreciation, years, sell_cost_pct):
    down_payment = price * (down_payment_pct / 100)
    loan = price - down_payment
    monthly_rate = mortgage_rate / 100 / 12
    n_payments = loan_term * 12
    if monthly_rate > 0:
        monthly_payment = loan * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
    else:
        monthly_payment = loan / n_payments
    
    total_mortgage_paid = monthly_payment * 12 * years
    balance = loan
    
    for _ in range(years * 12):
        interest = balance * monthly_rate
        principal = monthly_payment - interest
        balance -= principal

    property_tax = tax * years
    home_insurance = insurance * years
    maintenance_total = maintenance * years
    
    home_value = price * (1 + appreciation / 100) ** years
    selling_cost = sell_cost_pct / 100 * home_value
    net_proceeds = home_value - balance - selling_cost

    total_out_of_pocket = total_mortgage_paid + property_tax + home_insurance + maintenance_total + selling_cost - net_proceeds
    return {
        'down_payment': down_payment,
        'total_mortgage_paid': total_mortgage_paid,
        'property_tax': property_tax,
        'home_insurance': home_insurance,
        'maintenance_total': maintenance_total,
        'selling_cost': selling_cost,
        'net_proceeds': net_proceeds,
        'total_out_of_pocket': total_out_of_pocket,
        'monthly_payment': monthly_payment
    }

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

                if pd.isna(standard_rent):
                    st.error("❌ Rent data not available for this ZIP/bedroom combo.")
                else:
                    st.table(pd.DataFrame({
                        "Standard FMR": [f"${int(standard_rent):,}"],
                        "90% Payment": [f"${int(rent_90):,}"] if not pd.isna(rent_90) else ["N/A"],
                        "110% Payment": [f"${int(rent_110):,}"] if not pd.isna(rent_110) else ["N/A"]
                    }))

# --- Highest Paying ZIPs ---
elif st.session_state["mode"] == "Highest Paying ZIPs":
    st.subheader("Highest Paying ZIPs")
    if not fmr_df.empty:
        selected_state = st.selectbox("Select State:", valid_states)
        bedrooms = st.selectbox("Select Bedroom Size:", options=[0,1,2,3,4], format_func=lambda x: f"{x} Bedroom(s)" if x > 0 else "Efficiency")
        rent_type = st.selectbox("Select Rent Type:", ["Standard FMR", "90% Payment", "110% Payment"])
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

        rent_col = bedroom_map[bedrooms][rent_column_map[rent_type]]

        filtered = fmr_df[(fmr_df["State"] == selected_state) & fmr_df[rent_col].notna()]
        filtered = filtered[(filtered[rent_col] >= min_rent) & (filtered[rent_col] <= max_rent)]

        sort_order = st.selectbox("Sort order:", ["Ascending", "Descending"])
        filtered = filtered.sort_values(by=rent_col, ascending=(sort_order == "Ascending"))

        if not filtered.empty:
            result_df = filtered[["ZIP Code", rent_col]].copy()
            result_df["Rent"] = result_df[rent_col].apply(lambda x: f"${int(x):,}")
            result_df = result_df[["ZIP Code", "Rent"]]
            st.table(result_df)
        else:
            st.warning("No ZIP codes found matching your criteria.")
    else:
        st.warning("FMR data not loaded.")

# --- Rent vs Buy Calculator ---
elif st.session_state["mode"] == "Rent vs Buy Calculator":
    st.title("🏠 Rent vs Buy Calculator")

    st.markdown("Enter your details below. Fields marked with * are required.")

    st.header("📌 Rent Info")
    rent = parse_input(st.text_input("Monthly rent ($)*", placeholder="e.g. 2500"))
    rent_increase = parse_input(st.text_input("Annual rent increase (%)", placeholder="e.g. 3"))
    rent_insurance = parse_input(st.text_input("Renters insurance per year ($)", placeholder="e.g. 200"))

    st.header("📌 Buy Info")
    price = parse_input(st.text_input("Home price ($)*", placeholder="e.g. 600000"))
    down_payment_pct = parse_input(st.text_input("Down payment (%)*", placeholder="e.g. 20"))
    mortgage_rate = parse_input(st.text_input("Mortgage rate (%)*", placeholder="e.g. 6.5"))
    loan_term = parse_input(st.text_input("Loan term (years)*", placeholder="e.g. 30"))
    property_tax = parse_input(st.text_input("Property tax per year ($)*", placeholder="e.g. 6000"))
    home_insurance = parse_input(st.text_input("Homeowners insurance per year ($)", placeholder="e.g. 1500"))
    maintenance = parse_input(st.text_input("Annual maintenance ($)", placeholder="e.g. 6000"))
    appreciation = parse_input(st.text_input("Home appreciation (%)", placeholder="e.g. 3"))
    sell_cost_pct = parse_input(st.text_input("Selling cost (% of final home price)", placeholder="e.g. 7"))

    st.header("⏳ Time")
    years = st.slider("Years you plan to stay", 1, 30, 7)

    if st.button("Check Rent or Buy"):
        missing_fields = []
        if rent == 0: missing_fields.append("Monthly rent ($)")
        if price == 0: missing_fields.append("Home price ($)")
        if down_payment_pct == 0: missing_fields.append("Down payment (%)")
        if mortgage_rate == 0: missing_fields.append("Mortgage rate (%)")
        if loan_term == 0: missing_fields.append("Loan term (years)")
        if property_tax == 0: missing_fields.append("Property tax per year ($)")

        if missing_fields:
            st.warning(f"Please provide valid values for: {', '.join(missing_fields)}")
        else:
            rent_cost, rent_only, rent_ins = calculate_rent_cost(rent, rent_increase, rent_insurance, years)
            buy_result = calculate_buy_cost(price, down_payment_pct, mortgage_rate, loan_term, property_tax, home_insurance, maintenance, appreciation, years, sell_cost_pct)

            if rent_cost < buy_result['total_out_of_pocket']:
                st.success("✅ Renting is likely cheaper over this period based on your inputs.")
            else:
                st.success("✅ Buying is likely cheaper over this period based on your inputs.")

            with st.expander("See detailed calculation"):
                st.markdown("### Rent Summary")
                st.write(f"Total rent paid: ${rent_only:,.0f}")
                st.write(f"Total renters insurance: ${rent_ins:,.0f}")
                st.write(f"**Total cost of renting:** ${rent_cost:,.0f}")

                st.markdown("### Buy Summary")
                st.write(f"Down payment: ${buy_result['down_payment']:,.0f}")
                st.write(f"Monthly mortgage payment: ${buy_result['monthly_payment']:,.0f}")
                st.write(f"Total mortgage payments: ${buy_result['total_mortgage_paid']:,.0f}")
                st.write(f"Property taxes: ${buy_result['property_tax']:,.0f}")
                st.write(f"Home insurance: ${buy_result['home_insurance']:,.0f}")
                st.write(f"Maintenance cost (total): ${buy_result['maintenance_total']:,.0f}")
                st.write(f"Selling cost: ${buy_result['selling_cost']:,.0f}")
                st.write(f"Net proceeds from sale: ${buy_result['net_proceeds']:,.0f}")
                st.write(f"**Total out-of-pocket cost of buying:** ${buy_result['total_out_of_pocket']:,.0f}")

                st.markdown("### Pros of Renting")
                st.write("- Flexibility to move without selling")
                st.write("- No maintenance headaches")
                st.write("- Lower upfront cost")

                st.markdown("### Pros of Buying")
                st.write("- Build equity over time")
                st.write("- Potential property appreciation")
                st.write("- More stable housing costs long-term")
