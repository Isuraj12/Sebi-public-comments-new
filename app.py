import streamlit as st
import db
import scraper
import summarizer
import time
from datetime import datetime

# Ensure DB is initialized and schemas are up to date
db.init_db()

st.set_page_config(page_title="SEBI Circulars Extractor & Summarizer", page_icon="📜", layout="wide")

st.title("SEBI Circular Extractor & AI Summarizer")
st.markdown("Easily extract, view, and analyze SEBI Consultation Papers and Circulars.")

# Sidebar Configuration
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("API Key", type="password", help="Required to generate summarization using Gemini 2.5 Flash")

# Service Selection
selected_service = st.sidebar.selectbox("Select Service:", ["Public Comments", "SEBI Circulars"], help="Choose the SEBI section to manage or view")

st.sidebar.markdown("---")
st.sidebar.header(f"Manage {selected_service}")

# Check new circulars button
if st.sidebar.button(f"Check New {selected_service}", help="Checks maximum 5 pages and stops instantly on duplicates.", use_container_width=True):
    with st.spinner(f"Checking for new items on SEBI {selected_service}..."):
        added = scraper.check_new(category=selected_service)
        if added > 0:
            st.sidebar.success(f"{added} new {selected_service} found and added!")
            time.sleep(2)
            st.rerun()
        else:
            st.sidebar.info("No new items found.")

circs = db.get_all_circulars()
# Filter by selected service
circs = [c for c in circs if c.get('category', 'Public Comments') == selected_service]

st.sidebar.markdown("---")
with st.sidebar.expander("Admin: Delete Summary", expanded=False):
    summarized_circs = [c for c in circs if c['summary']]
    if not summarized_circs:
        st.info("No summaries generated yet.")
    else:
        del_options = {f"{c['date']} - {c['title']}": c for c in summarized_circs}
        del_selected_key = st.selectbox("Select Summary to Delete", list(del_options.keys()))
        del_password = st.text_input("Admin Password", type="password", help="Default is 'admin123'")
        if st.button("Delete Selected Summary", use_container_width=True):
            if del_password == "admin123":
                db.delete_summary(del_options[del_selected_key]['id'])
                st.success("Summary deleted.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Incorrect password.")

if not circs:
    st.info(f"There are no {selected_service} in the database yet. Click Check New {selected_service} to fetch data!")
    st.stop()

# Circular selection - sorting by date descending
def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%b %d, %Y')
    except:
        return datetime.min # fallback

circs.sort(key=lambda x: parse_date(x['date']), reverse=True)
options = {f"{c['date']} - {c['title']}": c for c in circs}
selected_key = st.selectbox("Select a Circular to analyze:", list(options.keys()))

if selected_key:
    selected_circ = options[selected_key]
    
    st.markdown("### Circular Details")
    st.markdown(f"**Title:** {selected_circ['title']}")
    st.markdown(f"**Date:** {selected_circ['date']}")
    st.markdown(f"**Direct PDF Link:** [View PDF Document]({selected_circ['pdf_url']})")

    st.markdown("---")
    
    # Check if summarized already
    if selected_circ['summary']:
        st.success("Summary Already Generated")
        with st.expander("View Summary", expanded=True):
            st.markdown(selected_circ['summary'])
    else:
        if st.button("Generate Summary "):
            if not api_key:
                st.error("Please enter a valid API Key in the sidebar.")
            else:
                with st.spinner("Extracting PDF and generating summary"):
                    # Process & Gen
                    result_summary = summarizer.generate_summary(selected_circ['id'], api_key)
                    if "Error" in result_summary or "Could not extract text" in result_summary:
                        st.error(result_summary)
                    else:
                        st.success("Summary Generated Successfully!")
                        st.rerun()
