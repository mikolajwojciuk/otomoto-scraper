# pylint: disable=C0301
# pylint: disable=C0103
import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_utils.utils import (
    process_data,
    smoothen_plot,
    get_maker_data,
    get_session_state,
    estimate_price,
    get_polish_age,
)


pd.options.mode.chained_assignment = None  # Disable Pandas SettingWithCopyWarning

st.set_page_config(
    page_title="Otomoto analytics",
    page_icon="🚗",
    layout="wide",
    menu_items={
        "About": """
App for providing insights about cars listed on otomoto.pl.
The aim on this app is to enable users to get insights about cars without
having to manually search through original web page.

It was mainly created to get familiar with data scraping and AWS processing and storage.
Implementation details can be found at https://github.com/mikolajwojciuk/otomoto-scraper.
"""
    },
)


st.title("Otomoto analytics")
st.caption("Dowiedz się więcej o samochodach z Otomoto!")


st.caption(
    "Uwaga: Liczba obsługiwanych marek i modeli zależy od dostępności danych. Aby umożliwić analizę, wybrano modele z co najmniej 30 ogłoszeniami."
)


st.divider()
col1, col2 = st.columns([0.35, 0.65])

col1.text(
    """Wybierz markę by zobaczyć jej podsumowanie.

Możesz także wybrać model,
by poznać więcej szczegółów.

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
    label="Wybierz markę",
    options=st.session_state.car_makes,
    index=None,
    placeholder="Wybierz markę",
    label_visibility="collapsed",
)

if selected_make:
    if selected_make not in st.session_state.car_data.keys():
        maker_data = get_maker_data(st.session_state.s3, selected_make)
        if maker_data.empty:
            st.warning(f"Marka, {selected_make} nie jest wspierana. Proszę wybrać inną.", icon="⚠️")
        else:
            st.session_state.car_data[selected_make] = maker_data

    if selected_make in st.session_state.car_data.keys():
        selected_model = col2.selectbox(
            label="Wybierz model",
            options=["Wszystkie modele"] + st.session_state.car_data[selected_make]["Model pojazdu"].unique().tolist(),
            index=0,
            placeholder="Wybierz model",
            label_visibility="collapsed",
        )


if selected_make in st.session_state.car_data.keys():
    data = st.session_state.car_data[selected_make]
    if selected_model != "Wszystkie modele":
        data = data[data["Model pojazdu"] == selected_model]

    st.divider()

    data = process_data(data)
    avg_price = str(int(data["Cena"].mean())) + " PLN"
    st.subheader("Średnia cena:   " + f":blue[{avg_price}]")
    avg_age = datetime.date.today().year - int(data["Rok produkcji"].astype(int).mean())
    st.subheader("Średni wiek:   " + f":blue[{str(avg_age)}]" + " " + f":blue[{get_polish_age(avg_age)}]")
    avg_mileage = str(int(data["Przebieg"].mean())) + " km"
    st.subheader("Średni przebieg:   " + f":blue[{avg_mileage}]")
    countries_origin = " ".join(data["Kraj pochodzenia"].value_counts()[:3].index.to_list())
    st.subheader("Najpopularniejsze kraje pochodzenia:   " + f":blue[{countries_origin}]")
    common_color = " ".join(data["Kolor"].value_counts()[:3].index.to_list())
    st.subheader("Najpopularniejsze kolory:   " + f":blue[{common_color}]")

    left_column, right_column = st.columns(2)
    left_column.subheader("Rodzaje paliwa")
    left_column.bar_chart(data=data["Rodzaj paliwa"].value_counts().to_dict())

    right_column.subheader("Rodzaje nadwozi")
    right_column.bar_chart(data=data["Typ nadwozia"].value_counts().to_dict())

    left_column, right_column = st.columns(2)

    left_column.subheader("Rodzaje napędów")
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

    right_column.subheader("Rodzaje skrzyń biegów")
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

    left_column.subheader("Rok produkcji / Przebieg")
    left_column.caption("Wykres przedstawia uśrednione przebiegi ze wszyskich lat produkcji")
    left_column.caption(
        "Luki na wykresach spowodowane mogą być brakiem ezgemplarzy z danego rocznika i z danym rodzajem paliwa"
    )
    data["Rok produkcji"] = data["Rok produkcji"].astype(str)
    year_mileage = data.groupby(["Rok produkcji", "Rodzaj paliwa"])["Przebieg"].mean().astype(int).reset_index()
    year_mileage = year_mileage.pivot(index="Rok produkcji", columns="Rodzaj paliwa", values="Przebieg")
    left_column.line_chart(year_mileage)

    right_column.subheader("Rok produkcji/ Cena")
    right_column.caption("Wykres przedstawia uśrednione ceny egzemplarzy ze wszyskich lat produkcji")
    right_column.caption(
        "Luki na wykresach spowodowane mogą być brakiem ezgemplarzy z danego rocznika i z danym rodzajem paliwa"
    )
    year_price = data.groupby(["Rok produkcji", "Rodzaj paliwa"])["Cena"].mean().astype(int).reset_index()
    year_price = year_price.pivot(index="Rok produkcji", columns="Rodzaj paliwa", values="Cena")
    right_column.line_chart(year_price)

    st.subheader("Przebieg / Cena")
    st.caption("Wykres przedstawia uśrednione ceny egzemplarzy z danym przebiegiem")
    st.caption(
        "Uwaga: wygładzanie wykresu dokonane jest poprzez dopasowanie funkcji wykładniczej i moze nie być reprezentatywne we wszystkich przypadkach."
    )
    smoothen_toggle = st.toggle("Wygładź wykres", value=True)
    mileage_price = data.groupby(["Przebieg", "Rodzaj paliwa"])["Cena"].mean().astype(int).reset_index()
    mileage_price = mileage_price.pivot(index="Przebieg", columns="Rodzaj paliwa", values="Cena")

    if smoothen_toggle:
        mileage_price = smoothen_plot(data=mileage_price.reset_index(), columns=mileage_price.columns.to_list())
        mileage_price = mileage_price.set_index("Przebieg")
    st.line_chart(mileage_price)


if (selected_make in st.session_state.car_data.keys()) and selected_model != "Wszystkie modele":
    data = st.session_state.car_data[selected_make]
    data = data[data["Model pojazdu"] == selected_model]
    data = process_data(data)
    st.subheader("Estymacja ceny")
    st.caption(
        """Aby oszacować wartość pojazdu, proszę uzupełnić ponizsze pola.
        Do oszacowania ceny wykorzystywany jest model oparty o lasy losowe."""
    )

    if data is not None:
        left_column, right_column = st.columns(2)
        year = left_column.number_input(
            min_value=int(data["Rok produkcji"].min()),
            max_value=int(data["Rok produkcji"].max()),
            value=int(data["Rok produkcji"].min()),
            label="Rok produkcji",
            key="price_estimation_year",
        )
        mileage = right_column.text_input(label="Przebieg (km)", value="180000", key="price_estimation_mileage")
        fuel_type = left_column.selectbox(
            label="Rodzaj paliwa",
            options=data["Rodzaj paliwa"].unique().tolist(),
            index=0,
            key="price_estimation_fuel_type",
        )
        power = right_column.text_input(label="Moc silnika (KM)", value="100", key="price_estimation_power")
        gearbox_type = left_column.selectbox(
            label="Rodzaj skrzyni biegów",
            options=data["Skrzynia biegów"].unique().tolist(),
            index=0,
            key="price_estimation_gearbox_type",
        )
        drive_type = right_column.selectbox(
            label="Rodzaj napędu",
            options=data["Napęd"].dropna().unique().tolist(),
            index=0,
            key="price_estimation_drive_type",
        )
        body_type = left_column.selectbox(
            label="Rodzaj nadwozia",
            options=data["Typ nadwozia"].unique().tolist(),
            index=0,
            key="price_estimation_body_type",
        )
        color = right_column.selectbox(
            label="Kolor", options=data["Kolor"].unique().tolist(), index=0, key="price_estimation_color"
        )
        clean_title = left_column.toggle(label="Bezwypadkowy", value=False)
        tow_hitch = right_column.toggle(label="Hak", value=False)

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

        if st.button("Oszacuj wartość", use_container_width=True):
            with st.spinner("Obliczanie wartości pojazdu..."):
                prediction = estimate_price(prediction_features, data)
                st.subheader(f"Oszacowana wartość :blue[{prediction}]")


st.markdown(
    """<div style="width:100%;text-align:center;">
    Wykonał Mikołaj Wojciuk
    <a href="https://www.linkedin.com/in/mikołaj-wojciuk-72956a20b" style="float:center">
    <img src="https://content.linkedin.com/content/dam/me/business/en-us/amp/brand-site/v2/bg/LI-Bug.svg.original.svg" width="22px"></img></a>
    </div>""",
    unsafe_allow_html=True,
)
