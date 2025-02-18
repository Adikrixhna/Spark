import streamlit as st
import pandas as pd
import logging
import tempfile
import os
from database import Database
import re

class SparkSearchApp:
    def __init__(self):
        """Initialize the Spark Search Application."""
        self.setup_logging()
        self.initialize_session_state()

    def setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="spark_search.log"
        )
        self.logger = logging.getLogger(__name__)

    def initialize_session_state(self):
        """Initialize session state variables."""
        if "db" not in st.session_state:
            st.session_state.db = Database()
        if "search_performed" not in st.session_state:
            st.session_state.search_performed = False
        if "columns" not in st.session_state:
            st.session_state.columns = []

    def handle_file_upload(self, uploaded_file):
        """Handle file upload and processing."""
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.session_state.columns = df.columns.tolist()

            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_path = temp_file.name

            try:
                success, message = st.session_state.db.insert_data(temp_path)
                if success:
                    st.success(message, icon="✅")
                else:
                    st.error(message, icon="❌")
            finally:
                # Ensure temp file is deleted
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception as e:
                    self.logger.error(f"Error deleting temporary file: {e}")

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            self.logger.error(f"Error processing file: {e}")

    def render_sidebar(self):
        """Render sidebar with file upload and basic info."""
        with st.sidebar:
            st.image("https://your-image-url.com/logo.png", width=150)  # Add your logo
            st.header("Data Management")
            uploaded_file = st.file_uploader(
                "Upload Data (CSV/Excel)",
                type=["csv", "xlsx", "xls"],
                label_visibility="collapsed"
            )

            if uploaded_file:
                self.handle_file_upload(uploaded_file)

            st.markdown("### Quick Stats")
            st.markdown(
                """
                - Use the filters above to search data
                - Export results in CSV/Excel/JSON format
                """
            )

    def create_search_filters(self):
        """Create and return search filters based on user input."""
        if not st.session_state.columns:
            st.warning("Please upload a file first to see search options.", icon="⚠️")
            return {}

        st.subheader("Search Criteria", anchor="search-criteria")
        filters = {}

        selected_columns = st.multiselect(
            "Select Columns to Filter",
            st.session_state.columns,
            help="Choose columns you want to filter on"
        )

        for column in selected_columns:
            filter_type = st.radio(
                f"Select filter type for '{column}'",
                ["Text Search", "Range Search"],
                key=column,
                help="Choose filter type for each column"
            )

            if filter_type == "Text Search":
                text_value = st.text_input(f"Search by {column}", key=f"text_{column}")
                if text_value:
                    filters[column] = text_value

            elif filter_type == "Range Search":
                stats = st.session_state.db.get_column_stats(column)
                if stats["max"] > 0:  # Numeric column
                    range_val = st.slider(
                        f"{column} Range",
                        min_value=float(stats["min"]),
                        max_value=float(stats["max"]),
                        value=(float(stats["min"]), float(stats["max"])),
                        step=0.1,
                        key=f"range_{column}"
                    )
                    filters[column] = range_val

        return filters

    def run(self):
        """Run the application."""
        st.set_page_config(
            page_title="Spark Search Platform",
            layout="wide",
            initial_sidebar_state="expanded",
            page_icon="🔍"
        )

        # Apply new Light Background Theme with slightly darker background
        st.markdown(
            """
            <style>
                /* Set the background color to a slightly darker light gray */
                body, .stApp {
                    background-color: #E8E8E8 !important; /* Slightly darker gray background */
                    color: #2196F3 !important; /* Blue text */
                }

                /* Sidebar customization */
                .sidebar .sidebar-content {
                    background-color: white !important;
                    border-radius: 10px;
                    padding: 20px;
                }

                /* Text color */
                h1, h2, h3, h4, h5, h6, label, .stTextInput, .stTextInput label, 
                .stRadio label, .stCheckbox label, .stSelectbox label, .stMultiselect label {
                    color: #2196F3 !important; /* Blue */
                }

                /* Buttons */
                .stButton > button {
                    background-color: #2196F3 !important;
                    color: white !important;
                    border-radius: 5px;
                }

                /* Input fields */
                .stTextInput > div > input, .stSelectbox div, .stMultiselect div {
                    background-color: white !important;
                    border: 1px solid #2196F3 !important;
                    color: #2196F3 !important;
                }

                /* Slider */
                .stSlider .st-bp {
                    color: #2196F3 !important;
                }

                /* Alert box */
                .stAlert {
                    color: #2196F3 !important;
                }
            </style>
            """,
            unsafe_allow_html=True
        )

        if "logged_in" not in st.session_state or not st.session_state.logged_in:
            self.render_login_page()
        else:
            self.render_dashboard()

    def render_login_page(self):
        """Render the login page."""
        st.title("Login to Spark Search Platform")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        login_button = st.button("Login")

        if login_button:
            if username == "Admin" and password == "Admin@123":
                st.session_state.logged_in = True
                st.success("Login successful! Redirecting to the dashboard...", icon="✅")
                st.rerun()
            else:
                st.error("Invalid username or password. Please try again.", icon="❌")

    def render_dashboard(self):
        """Render the main dashboard of the application."""
        st.title("Spark Search Platform")
        self.render_sidebar()
        filters = self.create_search_filters()

        if st.button("Search Data", use_container_width=True):
            if filters:
                results = st.session_state.db.search_resumes(filters)
                st.session_state.search_performed = True
                st.session_state.results = results
            else:
                st.warning("Please upload a file and set some search criteria first.", icon="⚠️")

        if st.session_state.search_performed:
            st.subheader(f"Search Results ({len(st.session_state.results)} records)", anchor="results")
            if not st.session_state.results.empty:
                st.dataframe(st.session_state.results, use_container_width=True)
            else:
                st.warning("No results found matching your criteria.", icon="⚠️")

if __name__ == "__main__":
    app = SparkSearchApp()
    app.run()
