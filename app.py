'''
Streamlit app to download recent job offers from linkedin based on keyword given by the user

Usage: 
streamlit run app.py
'''

import json
import pandas as pd
import streamlit as st
import requests as req
from requests.adapters import HTTPAdapter, Retry


@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')


@st.cache_data
def query_api(url):
    s = req.Session()

    retries = Retry(total=5,
                    backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504])

    s.mount('http://', HTTPAdapter(max_retries=retries))

    resp = s.get(url)
    if (resp.status_code == 200):
        dict = json.loads(resp.text)
        return dict
    else:
        print(f"Response code:{resp.status_code}")
        raise Exception("Request not successful")


def get_network_metadata(network):
    city = network['location']['city']
    country = network['location']['country']
    company = network['company']
    id = network['id']
    name = network['name']
    api_endpoint = "http://api.citybik.es" + network['href']
    return country, city, company, name, id, api_endpoint


def get_network_information(network):
    stations = network['network']['stations']
    n_stations = len(stations)

    n_empty_slots = 0
    n_bikes = 0
    for station in stations:
        try:
            n_empty_slots += int(station['empty_slots'])
        except:
            pass
        try:
            n_bikes += int(station['free_bikes'])
        except:
            pass

    return n_stations, n_empty_slots, n_bikes


@st.cache_data
def get_country_codes():
    dict = query_api("http://api.citybik.es/v2/networks")
    countries = set()

    for network in dict['networks']:
        countries.add(network['location']['country'])

    return list(countries)


def display_placeholder(placeholder, df, progress, total):
    with placeholder.container():
        spacer1, row_1, spacer_2 = st.columns((.1, ROW, .1))
        with row_1:
            if (progress == total):
                st.write("Web scraping complete")
            else:
                st.write("Web scraper is running...")
            st.progress(progress/total)

            st.write("")
            st.write(df)

            if (progress == total):
                st.write("")
                csv = convert_df(df)

                st.download_button(
                    label="Download data as CSV",
                    data=csv,
                    file_name='city_bike.csv',
                    mime='text/csv',
                )


# configuration of the page
st.set_page_config(layout="wide")
SPACER = .2
ROW = 1

title_spacer1, title, title_spacer_2 = st.columns((.1, ROW, .1))
with title:
    st.title('City bike web-scraper')
    st.markdown("""
            This app allows you scrape city bike information from https://api.citybik.es/v2/
            * The code can be accessed at [code](https://github.com/max-lutz/citybike_web_scraper).
            * You can select a country in the sidebar and download the data as csv once all the information have been retireved.
            """)


country_codes = get_country_codes()
country_codes.sort()

run_web_scraper = False

if (country_codes):
    st.sidebar.header('Web scraper input')
    country_code = st.sidebar.selectbox('Country code', country_codes)
    st.sidebar.write("")
    run_web_scraper = st.sidebar.button("Run web scraper")


placeholder = st.empty()
if (run_web_scraper):
    dict = query_api("http://api.citybik.es/v2/networks")
    rows = []

    for progress, network in enumerate(dict['networks']):
        if (network['location']['country'] == country_code):
            country, city, company, name, id, api_endpoint = get_network_metadata(network)
            n_stations, n_empty_slots, n_bikes = get_network_information(query_api(api_endpoint))
            rows.append([country, city, company, name, id, api_endpoint, n_stations, n_empty_slots, n_bikes])
            df = pd.DataFrame(rows, columns=['country', 'city', 'company', 'name', 'id',
                                             'api_endpoint', 'n_stations', 'n_empty_slots', 'n_bikes'])
            df['total_slots'] = df['n_empty_slots'] + df['n_bikes']

            display_placeholder(placeholder, df, progress, len(dict['networks']))

    placeholder.empty()
    display_placeholder(placeholder, progress+1, len(dict['networks']))
