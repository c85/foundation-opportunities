# Foundation Opportunities Finder

A Streamlit app that allows users to explore and filter foundation opportunities from Airtable. The app pulls data from an Airtable base, formats it, and presents it with various filtering options to help users find relevant foundation opportunities.

## Features

- **Real-Time Data**: Fetches and displays the latest foundation opportunities from Airtable.
- **Custom Filters**: Allows users to filter foundation opportunities based on tags, deadlines, and other fields.
- **Interactive Interface**: Provides an intuitive and interactive way to explore foundation opportunities.

## Demo

[Link to live app](https://foundation-opportunities.streamlit.app/)

## Getting Started

### Prerequisites

Ensure you have the following installed:

- Python 3.9 or later
- pip (Python package installer)

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/c85/foundation-opportunities.git
    cd foundation-opportunities
    ```

2. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

### Running the App Locally

1. Navigate to the project directory.

2. Run the Streamlit app:

    ```bash
    streamlit run app.py
    ```

3. The app should open in your default web browser. If not, open your browser and go to `http://localhost:8501`.

## Usage

- **Filters**: Use the sidebar to select columns and apply filters.
- **Data Exploration**: View the filtered results in an editable table. Select specific foundation opportunities to view detailed information.
- **Links**: Click on opportunity names to visit their respective URLs.

## Code Structure

- `app.py`: Main Streamlit app file that handles data fetching, filtering, and display.
- `requirements.txt`: Lists all dependencies required to run the app.
- `README.md`: This file, providing an overview of the project.

## Acknowledgments

- [Streamlit](https://www.streamlit.io/) for the web app framework.
- [Airtable](https://airtable.com/) for providing the data.

