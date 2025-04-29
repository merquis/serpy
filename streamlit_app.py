import streamlit as st
from scraping_module import render_scraping

st.set_page_config(page_title="TripToIslands Scraper", layout="wide")
render_scraping()
