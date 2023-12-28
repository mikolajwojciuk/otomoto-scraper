# pylint: disable=C0301
# pylint: disable=C0103
import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from streamlit_utils.utils import process_data, smoothen_plot


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

if "s3" not in st.session_state:
    load_dotenv()

    region_name = os.environ["REGION_NAME"]
    aws_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
    aws_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]

    st.session_state.s3 = boto3.resource(
        service_name="s3",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

if "car_makes" not in st.session_state:
    car_makes_data = st.session_state.s3.Bucket("otomoto-scrapper-car-makes").Object("car_makes.txt").get()
    st.session_state.car_makes = pd.read_csv(car_makes_data["Body"], header=None, low_memory=False)[0].to_list()


if "car_models" not in st.session_state:
    st.session_state.car_models = {}
    for make in st.session_state.car_makes:
        models_data = st.session_state.s3.Bucket("otomoto-scrapper-car-models").Object(f"car_models/{make}.txt").get()
        st.session_state.car_models[make] = pd.read_csv(models_data["Body"], header=None, low_memory=False)[0].to_list()

if "car_data" not in st.session_state:
    st.session_state.car_data = {}
    for make in st.session_state.car_makes:
        try:
            make_data = st.session_state.s3.Bucket("otomoto-scrapper").Object(f"{make}.txt").get()
            st.session_state.car_data[make] = pd.read_csv(make_data["Body"], low_memory=False)
        except ClientError as e:
            if not e.response["Error"]["Code"] == "NoSuchKey":
                raise

if "supported_vehicles" not in st.session_state:
    st.session_state.supported_vehicles = {}
    for make in list(st.session_state.car_data.keys()):
        st.session_state.supported_vehicles[make] = st.session_state.car_data[make]["Model pojazdu"].unique()


st.title("Otomoto analytics")
st.caption("Get insights from Otomoto")

st.divider()

n_makes_metric, n_models_metric = st.columns(2)

n_makes_metric.metric("Number of supported makes", str(len(list(st.session_state.supported_vehicles.keys()))))
n_models_metric.metric(
    "Number of supported models",
    str(sum((len(st.session_state.supported_vehicles[make]) for make in st.session_state.supported_vehicles))),
)
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

selected_make = col2.selectbox(
    label="Choose brand",
    options=st.session_state.supported_vehicles.keys(),
    index=None,
    placeholder="Choose brand",
    label_visibility="collapsed",
)
if selected_make:
    selected_model = col2.selectbox(
        label="Choose model",
        options=["All models"] + list(st.session_state.supported_vehicles[selected_make]),
        index=0,
        placeholder="Choose model",
        label_visibility="collapsed",
    )


if selected_make:
    data = st.session_state.car_data[selected_make]
    if selected_model != "All models":
        data = data[data["Model pojazdu"] == selected_model]


if selected_make:
    st.divider()

    data = process_data(data)
    left_column, right_column = st.columns(2)
    avg_price = str(int(data["Cena"].mean())) + " PLN"
    left_column.subheader("Average price:   ")
    right_column.subheader(f":blue[{avg_price}]")
    avg_age = str(datetime.date.today().year - int(data["Rok produkcji"].astype(int).mean())) + " years"
    left_column.subheader("Average age:   ")
    right_column.subheader(f":blue[{avg_age}]")
    avg_mileage = str(int(data["Przebieg"].mean())) + " km"
    left_column.subheader("Average mileage:   ")
    right_column.subheader(f":blue[{avg_mileage}]")
    countries_origin = " ".join(data["Kraj pochodzenia"].value_counts()[:3].index.to_list())
    left_column.subheader("Most common countries of origin:   ")
    right_column.subheader(f":blue[{countries_origin}]")
    common_color = " ".join(data["Kolor"].value_counts()[:3].index.to_list())
    left_column.subheader("Most common colours:   ")
    right_column.subheader(f":blue[{common_color}]")

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
        mileage_price = smoothen_plot(
            data=mileage_price.reset_index(), columns=mileage_price.columns.to_list()
        )  # TODO: Add columns filtering
        mileage_price = mileage_price.set_index("Przebieg")
    st.line_chart(mileage_price)

    x, y = st.columns(2)


st.markdown(
    """<div style="width:100%;text-align:center;">
    Developed by Mikołaj Wojciuk
    <a href="https://www.linkedin.com/in/mikołaj-wojciuk-72956a20b" style="float:center">
    <img src="https://content.linkedin.com/content/dam/me/business/en-us/amp/brand-site/v2/bg/LI-Bug.svg.original.svg" width="22px"></img></a>
    </div>""",
    unsafe_allow_html=True,
)
