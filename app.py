# pylint: disable=C0301
# pylint: disable=C0103
import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_utils.utils import process_data, smoothen_plot, get_maker_data, get_session_state, estimate_price


pd.options.mode.chained_assignment = None  # Disable Pandas SettingWithCopyWarning

st.set_page_config(
    page_title="Otomoto analytics",
    page_icon="🚗",
    layout="wide",
    menu_items={
        "About": """
App for providing insights about cars listed on otomoto.pl.
The aim on this app is to enable users to get insights about cars without having to manually search through original web page.

It was mainly created to get familiar with data scraping and AWS processing and storage.
Implementation details can be found at https://github.com/mikolajwojciuk/otomoto-scraper.
"""
    },
)


st.title("Otomoto analytics")
st.caption("Get insights from Otomoto")


st.caption(
    "Note: Number of supported makes and models depends on data availability. To make the analysis possible, models with at least 30 advertisements were selected."
)


st.divider()
col1, col2 = st.columns([0.35, 0.65])

col1.text(
    """Select car brand to see
insights about it

You can also specify model
to get insights about it as well
          """
)

s3, car_makes, car_models = get_session_state()
if "s3" not in st.session_state:
    st.session_state.s3 = s3
if "car_makes" not in st.session_state:
    st.session_state.car_makes = car_makes
if "car_models" not in st.session_state:
    st.session_state.car_models = car_models
if "car_data" not in st.session_state:
    st.session_state.car_data = {}

selected_make = col2.selectbox(
    label="Choose brand",
    options=st.session_state.car_makes,
    index=None,
    placeholder="Choose brand",
    label_visibility="collapsed",
)

if selected_make:
    if selected_make not in st.session_state.car_data.keys():
        maker_data = get_maker_data(st.session_state.s3, selected_make)
        if maker_data.empty:
            st.warning(f"Sorry, {selected_make} is not supported yet. Please try another one.", icon="⚠️")
        else:
            st.session_state.car_data[selected_make] = maker_data

    if selected_make in st.session_state.car_data.keys():
        selected_model = col2.selectbox(
            label="Choose model",
            options=["All models"] + st.session_state.car_data[selected_make]["Model pojazdu"].unique().tolist(),
            index=0,
            placeholder="Choose model",
            label_visibility="collapsed",
        )


if selected_make in st.session_state.car_data.keys():
    data = st.session_state.car_data[selected_make]
    if selected_model != "All models":
        data = data[data["Model pojazdu"] == selected_model]

    st.divider()

    data = process_data(data)
    avg_price = str(int(data["Cena"].mean())) + " PLN"
    st.subheader("Average price:   " + f":blue[{avg_price}]")
    avg_age = str(datetime.date.today().year - int(data["Rok produkcji"].astype(int).mean())) + " years"
    st.subheader("Average age:   " + f":blue[{avg_age}]")
    avg_mileage = str(int(data["Przebieg"].mean())) + " km"
    st.subheader("Average mileage:   " + f":blue[{avg_mileage}]")
    countries_origin = " ".join(data["Kraj pochodzenia"].value_counts()[:3].index.to_list())
    st.subheader("Most common countries of origin:   " + f":blue[{countries_origin}]")
    common_color = " ".join(data["Kolor"].value_counts()[:3].index.to_list())
    st.subheader("Most common colours:   " + f":blue[{common_color}]")

    left_column, right_column = st.columns(2)
    left_column.subheader("Fuel types")
    left_column.bar_chart(data=data["Rodzaj paliwa"].value_counts().to_dict())

    right_column.subheader("Body types")
    right_column.bar_chart(data=data["Typ nadwozia"].value_counts().to_dict())

    left_column, right_column = st.columns(2)

    left_column.subheader("Drivetrain types")
    drivetrain_type_percentage = []
    data_size = len(data)
    for drivetrain in data["Napęd"].dropna().unique().tolist():
        drivetrain_dict = {}
        drivetrain_dict["Type of drivetrain"] = drivetrain
        drivetrain_dict["Percentage"] = round(data["Napęd"].value_counts()[drivetrain] / data_size, 2)
        drivetrain_type_percentage.append(drivetrain_dict)
    drivetrain_type_percentage = pd.DataFrame(drivetrain_type_percentage)
    drivetrain_type_plot = px.pie(drivetrain_type_percentage, names="Type of drivetrain", values="Percentage")
    left_column.plotly_chart(drivetrain_type_plot, theme="streamlit", use_container_width=True)

    right_column.subheader("Gearboxes types")
    gearbox_type_percentage = []
    data_size = len(data)
    for gearbox in data["Skrzynia biegów"].dropna().unique().tolist():
        gearbox_dict = {}
        gearbox_dict["Type of gearbox"] = gearbox
        gearbox_dict["Percentage"] = round(data["Skrzynia biegów"].value_counts()[gearbox] / data_size, 2)
        gearbox_type_percentage.append(gearbox_dict)
    gearbox_type_percentage = pd.DataFrame(gearbox_type_percentage)
    gearbox_type_plot = px.pie(gearbox_type_percentage, names="Type of gearbox", values="Percentage")
    right_column.plotly_chart(gearbox_type_plot, theme="streamlit", use_container_width=True)

    left_column.subheader("Year / Mileage")
    left_column.caption("Ratio calculated by averaging all cars mileages over manufacturing years")
    left_column.caption(
        "Possible gaps in the charts are due to a lack of cars from a specific model year with a specific type of power source."
    )
    data["Rok produkcji"] = data["Rok produkcji"].astype(str)
    year_mileage = data.groupby(["Rok produkcji", "Rodzaj paliwa"])["Przebieg"].mean().astype(int).reset_index()
    year_mileage = year_mileage.pivot(index="Rok produkcji", columns="Rodzaj paliwa", values="Przebieg")
    left_column.line_chart(year_mileage)

    right_column.subheader("Year / Price")
    right_column.caption("Ratio calculated by averaging all cars mileages over manufacturing years")
    right_column.caption(
        "Possible gaps in the charts are due to a lack of cars from a specific model year with a specific type of power source."
    )
    year_price = data.groupby(["Rok produkcji", "Rodzaj paliwa"])["Cena"].mean().astype(int).reset_index()
    year_price = year_price.pivot(index="Rok produkcji", columns="Rodzaj paliwa", values="Cena")
    right_column.line_chart(year_price)

    st.subheader("Mileage / Price")
    st.caption("Ratio calculated by averaging all cars prices over mileages")
    st.caption(
        "Note: Smoothening is performed by fitting exponential decay model and might not be indicative in all cases"
    )
    smoothen_toggle = st.toggle("Smoothen plot", value=True)
    mileage_price = data.groupby(["Przebieg", "Rodzaj paliwa"])["Cena"].mean().astype(int).reset_index()
    mileage_price = mileage_price.pivot(index="Przebieg", columns="Rodzaj paliwa", values="Cena")

    if smoothen_toggle:
        mileage_price = smoothen_plot(data=mileage_price.reset_index(), columns=mileage_price.columns.to_list())
        mileage_price = mileage_price.set_index("Przebieg")
    st.line_chart(mileage_price)


if (selected_make in st.session_state.car_data.keys()) and selected_model:
    data = st.session_state.car_data[selected_make]
    data = data[data["Model pojazdu"] == selected_model]
    data = process_data(data)
    st.subheader("Price estimation")

    if data is not None:
        left_column, right_column = st.columns(2)
        year = left_column.number_input(
            min_value=int(data["Rok produkcji"].min()),
            max_value=int(data["Rok produkcji"].max()),
            value=int(data["Rok produkcji"].min()),
            label="Year",
            key="price_estimation_year",
        )
        mileage = right_column.text_input(label="Mileage (km)", value="100000", key="price_estimation_mileage")
        fuel_type = left_column.selectbox(
            label="Fuel type",
            options=data["Rodzaj paliwa"].unique().tolist(),
            index=0,
            key="price_estimation_fuel_type",
        )
        power = right_column.text_input(label="Power (KM)", value="100", key="price_estimation_power")
        gearbox_type = left_column.selectbox(
            label="Gearbox type",
            options=data["Skrzynia biegów"].unique().tolist(),
            index=0,
            key="price_estimation_gearbox_type",
        )
        drive_type = right_column.selectbox(
            label="Drive type",
            options=data["Napęd"].dropna().unique().tolist(),
            index=0,
            key="price_estimation_drive_type",
        )
        body_type = left_column.selectbox(
            label="Body type", options=data["Typ nadwozia"].unique().tolist(), index=0, key="price_estimation_body_type"
        )
        color = right_column.selectbox(
            label="Color", options=data["Kolor"].unique().tolist(), index=0, key="price_estimation_color"
        )
        clean_title = left_column.toggle(label="Clean title", value=False)
        tow_hitch = right_column.toggle(label="Tow hitch", value=False)

        prediction_features = {
            "Rok produkcji": year,
            "Przebieg": mileage,
            "Rodzaj paliwa": fuel_type,
            "Moc": power,
            "Skrzynia biegów": gearbox_type,
            "Napęd": drive_type,
            "Typ nadwozia": body_type,
            "Kolor": color,
            "Bezwypadkowy": int(clean_title),
            "Hak": int(tow_hitch),
        }

        if st.button("Estimate price", use_container_width=True):
            with st.spinner("Calculating price estimate..."):
                prediction = estimate_price(prediction_features, data)
                st.subheader(f"Estimated price: :blue[{prediction}]")


st.markdown(
    """<div style="width:100%;text-align:center;">
    Developed by Mikołaj Wojciuk
    <a href="https://www.linkedin.com/in/mikołaj-wojciuk-72956a20b" style="float:center">
    <img src="https://content.linkedin.com/content/dam/me/business/en-us/amp/brand-site/v2/bg/LI-Bug.svg.original.svg" width="22px"></img></a>
    </div>""",
    unsafe_allow_html=True,
)
