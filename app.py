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

# --- Extract 2-letter State codes ---
if not fmr_df.empty and "State" not in fmr_df.columns:
    fmr_df["State"] = (
        fmr_df["HUD Fair Market Rent Area Name"]
        .apply(lambda x: x.split(",")[-1].strip()[:2])
    )
valid_states = sorted(fmr_df["State"].dropna().unique().tolist()) if not fmr_df.empty else []

# --- App title + navigation buttons ---
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

# --- Common helpers ---
def parse_input(text):
    try:
        return float(text)
    except:
        return 0.0

def calculate_rent_cost(rent, rent_increase, insurance, years):
    total_rent = 0
    current_rent = rent
    for _ in range(years):
        total_rent += current_rent * 12
        current_rent *= 1 + rent_increase / 100
    total_insurance = insurance * years
    return total_rent + total_insurance, total_rent, total_insurance

def calculate_buy_cost(price, down_payment_pct, mortgage_rate, loan_term,
                       tax, insurance, maintenance, appreciation,
                       years, sell_cost_pct):
    down_payment = price * (down_payment_pct / 100)
    loan = price - down_payment
    monthly_rate = mortgage_rate / 100 / 12
    n_payments = loan_term * 12
    if monthly_rate > 0:
        monthly_payment = loan * (
            monthly_rate * (1 + monthly_rate) ** n_payments
        ) / ((1 + monthly_rate) ** n_payments - 1)
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

    total_out_of_pocket = (
        total_mortgage_paid
        + property_tax
        + home_insurance
        + maintenance_total
        + selling_cost
        - net_proceeds
    )
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

# --- 1) FMR Rental Data Mode ---
if st.session_state["mode"] == "FMR Rental Data":
    st.subheader("FMR Rental Data Finder")
    zip_code = st.text_input(
        "Enter ZIP Code (5 digits):",
        help="Provide a 5-digit ZIP code to look up HUD FMR."
    )
    bedrooms = st.selectbox(
        "Select Number of Bedrooms:",
        options=[0,1,2,3,4],
        format_func=lambda x: "Efficiency" if x==0 else f"{x} Bedroom(s)",
        help="Choose the bedroom count for the rent lookup."
    )
    if st.button("Find Rent"):
        if not zip_code:
            st.warning("Please enter a valid ZIP code.")
        else:
            z = str(zip_code).zfill(5)
            rec = fmr_df[fmr_df['ZIP Code'].astype(str).str.zfill(5) == z]
            if rec.empty:
                st.error("❌ ZIP code not found.")
            else:
                m0, m90, m110 = [
                    rec.iloc[0].get(col) for col in (
                        f"SAFMR {bedrooms}BR",
                        f"SAFMR {bedrooms}BR - 90% Payment Standard",
                        f"SAFMR {bedrooms}BR - 110% Payment Standard"
                    )
                ]
                df = pd.DataFrame({
                    "Standard FMR": [f"${int(m0):,}"] if pd.notna(m0) else ["N/A"],
                    "90% Payment": [f"${int(m90):,}"] if pd.notna(m90) else ["N/A"],
                    "110% Payment": [f"${int(m110):,}"] if pd.notna(m110) else ["N/A"]
                })
                st.success("✅ Estimated FMR Found:")
                st.table(df)

# --- 2) Highest Paying ZIPs Mode ---
elif st.session_state["mode"] == "Highest Paying ZIPs":
    st.subheader("Highest Paying ZIPs")
    if fmr_df.empty:
        st.warning("FMR data not loaded.")
    else:
        selected_state = st.selectbox(
            "Select State:",
            valid_states,
            help="Filter to a specific state."
        )
        bedrooms = st.selectbox(
            "Select Bedroom Size:",
            [0,1,2,3,4],
            format_func=lambda x: "Efficiency" if x==0 else f"{x} Bedroom(s)",
            help="Choose bedroom count."
        )
        rent_type = st.selectbox(
            "Select Rent Type:",
            ["Standard FMR","90% Payment","110% Payment"],
            help="Which FMR column to use."
        )
        min_rent = st.number_input(
            "Minimum Rent ($)",
            min_value=0, value=0, step=500,
            help="Minimum rent filter."
        )
        max_rent = st.number_input(
            "Maximum Rent ($)",
            min_value=0, value=10000, step=500,
            help="Maximum rent filter."
        )
        sort_order = st.selectbox(
            "Sort order:",
            ["Ascending","Descending"],
            help="Sort by rent ascending or descending."
        )

        # map to column
        col_map = {
            0: ('SAFMR 0BR','SAFMR 0BR - 90% Payment Standard','SAFMR 0BR - 110% Payment Standard'),
            1: ('SAFMR 1BR','SAFMR 1BR - 90% Payment Standard','SAFMR 1BR - 110% Payment Standard'),
            2: ('SAFMR 2BR','SAFMR 2BR - 90% Payment Standard','SAFMR 2BR - 110% Payment Standard'),
            3: ('SAFMR 3BR','SAFMR 3BR - 90% Payment Standard','SAFMR 3BR - 110% Payment Standard'),
            4: ('SAFMR 4BR','SAFMR 4BR - 90% Payment Standard','SAFMR 4BR - 110% Payment Standard'),
        }
        rent_col = col_map[bedrooms][
            {"Standard FMR":0,"90% Payment":1,"110% Payment":2}[rent_type]
        ]

        df_filt = fmr_df[
            (fmr_df["State"]==selected_state) &
            fmr_df[rent_col].notna() &
            (fmr_df[rent_col]>=min_rent) &
            (fmr_df[rent_col]<=max_rent)
        ].sort_values(
            by=rent_col,
            ascending=(sort_order=="Ascending")
        )

        if df_filt.empty:
            st.warning("No ZIP codes found matching your criteria.")
        else:
            out = df_filt[["ZIP Code", rent_col]].copy()
            out["Rent"] = out[rent_col].apply(lambda x: f"${int(x):,}")
            st.table(out[["ZIP Code","Rent"]])

# --- 3) Rent vs Buy Calculator Mode ---
elif st.session_state["mode"] == "Rent vs Buy Calculator":
    st.title("🏠 Rent vs Buy Calculator")
    st.markdown("Enter your details below. Fields marked with * are required.")

    st.header("📌 Rent Info")
    rent = parse_input(st.text_input(
        "Monthly rent ($)*",
        placeholder="e.g. 2500",
        help="Your current monthly rent payment."
    ))
    rent_increase = parse_input(st.text_input(
        "Annual rent increase (%)",
        placeholder="e.g. 3",
        help="Expected annual rent increase (percent)."
    ))
    rent_insurance = parse_input(st.text_input(
        "Renters insurance per year ($)",
        placeholder="e.g. 200",
        help="Annual renters insurance cost."
    ))

    st.header("📌 Buy Info")
    price = parse_input(st.text_input(
        "Home price ($)*",
        placeholder="e.g. 600000",
        help="Purchase price of the home."
    ))
    down_payment_pct = parse_input(st.text_input(
        "Down payment (%)*",
        placeholder="e.g. 20",
        help="Down payment as a percentage of home price."
    ))
    mortgage_rate = parse_input(st.text_input(
        "Mortgage rate (%)*",
        placeholder="e.g. 6.5",
        help="Annual mortgage interest rate."
    ))
    loan_term = parse_input(st.text_input(
        "Loan term (years)*",
        placeholder="e.g. 30",
        help="Mortgage length in years."
    ))
    property_tax = parse_input(st.text_input(
        "Property tax per year ($)*",
        placeholder="e.g. 6000",
        help="Annual property tax cost."
    ))
    home_insurance = parse_input(st.text_input(
        "Homeowners insurance per year ($)",
        placeholder="e.g. 1500",
        help="Annual homeowners insurance cost."
    ))
    maintenance = parse_input(st.text_input(
        "Annual maintenance ($)",
        placeholder="e.g. 6000",
        help="Expected annual maintenance cost."
    ))
    appreciation = parse_input(st.text_input(
        "Home appreciation (%)",
        placeholder="e.g. 3",
        help="Expected annual home value appreciation."
    ))
    sell_cost_pct = parse_input(st.text_input(
        "Selling cost (% of final home price)",
        placeholder="e.g. 7",
        help="Percentage of final price paid in selling costs."
    ))

    st.header("⏳ Time")
    years = st.slider(
        "Years you plan to stay",
        min_value=1, max_value=30, value=7,
        help="How many years you plan to rent or occupy the home."
    )

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
            rent_cost, rent_only, rent_ins = calculate_rent_cost(
                rent, rent_increase, rent_insurance, years
            )
            buy_result = calculate_buy_cost(
                price, down_payment_pct, mortgage_rate, loan_term,
                property_tax, home_insurance, maintenance,
                appreciation, years, sell_cost_pct
            )
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

                st.markdown("#### Pros of Renting")
                st.write("- Flexibility to move without selling")
                st.write("- No maintenance headaches")
                st.write("- Lower upfront cost")

                st.markdown("#### Pros of Buying")
                st.write("- Build equity over time")
                st.write("- Potential property appreciation")
                st.write("- More stable housing costs long-term")
