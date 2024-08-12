import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import pandas as pd
from io import StringIO
import streamlit as st
import datetime

def airtable_access():
    access_url = "https://airtable.com/appP16yvFUfongopF/shre0mftKFPTjM7BG/tblJAj9wQaZq7o5CS"
    access_headers = {
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
    }

    access_response = requests.get(access_url, headers=access_headers)
    html_content = access_response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    script_tag = soup.find(string=re.compile(r'window\.__stashedPrefetch'))
    script_content = script_tag if script_tag else ''

    application_id_pattern = re.compile(r'x-airtable-application-id":"(.*?)"')
    application_id_match = application_id_pattern.search(script_content)
    application_id = application_id_match.group(1) if application_id_match else None

    page_load_id_pattern = re.compile(r'x-airtable-page-load-id":"(.*?)"')
    page_load_id_match = page_load_id_pattern.search(script_content)
    page_load_id = page_load_id_match.group(1) if page_load_id_match else None

    request_id_pattern = re.compile(r'requestId:\s*"(.*?)"')
    request_id_match = request_id_pattern.search(script_content)
    request_id = request_id_match.group(1) if request_id_match else None

    url_with_params_pattern = re.compile(r'urlWithParams:\s*"(.*?)"')
    url_with_params_match = url_with_params_pattern.search(script_content)
    url_with_params = url_with_params_match.group(1) if url_with_params_match else None

    access_policy = None
    if url_with_params:
        parsed_url = urllib.parse.unquote(url_with_params)
        start = parsed_url.find('accessPolicy=') + len('accessPolicy=')
        end = parsed_url.find('&', start)
        if end == -1:
            end = len(parsed_url)
        access_policy = parsed_url[start:end]
        
    return request_id, access_policy, application_id, page_load_id

def airtable_format_amount(value):
    if isinstance(value, str) and value.startswith('$'):
        return '${:,.0f}'.format(float(value.replace('$', '').replace(',', '')))
    return value

def airtable_dataset(request_id, access_policy, application_id, page_load_id):
    data_url = f"https://airtable.com/v0.3/view/viwbD1NkdENbkpbVI/downloadCsv?stringifiedObjectParams=%7B%22shouldUseNestedResponseFormat%22%3Atrue%7D&requestId={request_id}&accessPolicy={access_policy}"
    data_headers = {
        'Accept-Language': 'en-US,en;q=0.9',
        'x-airtable-inter-service-client': 'webClient',
        'x-airtable-application-id': f'{application_id}',
        'x-airtable-accept-msgpack': 'true',
        'x-airtable-page-load-id': f'{page_load_id}',
        'x-early-prefetch': 'true',
        'x-requested-with': 'XMLHttpRequest',
        'x-time-zone': 'America/New_York',
        'x-user-locale': 'en'
    }

    data_response = requests.get(data_url, headers=data_headers)
    data_csv = data_response.content
    if data_csv.startswith(b'\xef\xbb\xbf'):
        data_csv = data_csv[3:]

    data_csv = data_csv.decode('utf-8')
    data_df = pd.read_csv(StringIO(data_csv))
    data_df.columns = [col.upper().replace(' ', '_') for col in data_df.columns]
    data_df = data_df.rename(columns={"MAXIMUM_AMOUNT": "AMOUNT", "MAXIMUM_DURATION": "DURATION"})
    data_df.loc[:, 'DEADLINE'] = pd.to_datetime(data_df['DEADLINE'], format='%m/%d/%Y', errors='coerce')
    
    data_df['AMOUNT'] = data_df['AMOUNT'].apply(airtable_format_amount)
    data_df['TAGS'] = data_df['TAGS'].fillna('')
    tags_list = data_df['TAGS'].str.split(',')
    all_tags = [tag for sublist in tags_list for tag in sublist]
    all_unique_tags = list(set(all_tags))
    all_unique_tags = [tag for tag in all_unique_tags if tag]

    return data_df, all_unique_tags

def airtable_filters(df, unique_tags):
    filter_columns = st.sidebar.multiselect("Select columns to filter", df.columns)
    
    for col in filter_columns:
        if col == "TAGS":
            selected_tags = st.sidebar.multiselect("Select tags to filter", unique_tags)
            if selected_tags:
                df = df[df['TAGS'].apply(lambda x: any(tag in x for tag in selected_tags))]
        elif col == "DEADLINE":
            today = datetime.datetime.today()
            min_date = st.sidebar.date_input("Start date", value=today.date(), key=f"{col}_start_date")
            max_date = st.sidebar.date_input("End date", value=today.date(), key=f"{col}_end_date")
            
            df['DEADLINE'] = pd.to_datetime(df['DEADLINE'], format='%m/%d/%Y', errors='coerce')
            df = df[df['DEADLINE'].notna() & (df[col] >= pd.to_datetime(min_date)) & (df[col] <= pd.to_datetime(max_date))]
            df.loc[:, 'DEADLINE'] = df['DEADLINE'].dt.strftime('%m/%d/%Y')
        else:
            search_type = st.sidebar.selectbox(f"Filter type for {col}", ["contains", "exact"], key=f"{col}_search_type")
            
            if search_type == "contains":
                search_term = st.sidebar.text_input(f"Search term for {col}")
                if search_term:
                    df = df[df[col].astype(str).str.contains(search_term, case=False, na=False)]
            else:
                unique_values = df[col].dropna().unique()
                if df[col].dtype == 'datetime64[ns]':
                    filter_values = st.sidebar.multiselect(f"Filter values for {col}", pd.to_datetime(unique_values, errors='coerce'))
                    filter_values = pd.to_datetime(filter_values, errors='coerce')
                    df = df[df[col].isin(filter_values)]
                else:
                    filter_values = st.sidebar.multiselect(f"Filter values for {col}", unique_values)
                    df = df[df[col].isin(filter_values)]

    return df


def airtable_apply_filters(df, filters):
    for col, filter_values in filters.items():
        if isinstance(filter_values, tuple):
            min_value, max_value = filter_values
            df = df[(df[col] >= min_value) & (df[col] <= max_value)]
        else:
            df = df[df[col].isin(filter_values)]
    return df

def main():
    st.set_page_config(layout="wide", page_title="Opportunities")
    st.header("Opportunities")
    st.markdown("<br>", unsafe_allow_html=True)

    if 'original_df' not in st.session_state:
        request_id, access_policy, application_id, page_load_id = airtable_access()
        data_df, all_unique_tags = airtable_dataset(request_id, access_policy, application_id, page_load_id)
        st.session_state.original_df = data_df
        st.session_state.filtered_df = data_df.copy()
        st.session_state.all_unique_tags = all_unique_tags
    
    if 'all_unique_tags' not in st.session_state:
        st.session_state.all_unique_tags = []

    filters = airtable_filters(st.session_state.original_df, st.session_state.all_unique_tags)

    col1, col2 = st.sidebar.columns([1, 1])
    apply_filters = col1.button("Apply Filters")
    remove_filters = col2.button("Remove Filters")

    if apply_filters:
        st.session_state.filtered_df = airtable_apply_filters(st.session_state.original_df.copy(), filters)
        st.session_state.filtered_df['DEADLINE'] = st.session_state.filtered_df['DEADLINE'].dt.strftime('%m/%d/%Y')
    
    if remove_filters:
        st.session_state.filtered_df = st.session_state.original_df.copy()

    if 'select' not in st.session_state.filtered_df.columns:
        st.session_state.filtered_df.insert(0, 'select', False)

    st.session_state.filtered_df = st.session_state.filtered_df.reset_index(drop=True)
    selected_columns = [col for col in st.session_state.filtered_df.columns if col != "select"]
    
    st.data_editor(st.session_state.filtered_df,
                   hide_index=True,
                   disabled=selected_columns,
                   use_container_width=True,
                   key="filtered_data")
    
    selected_index = [key for key, value in st.session_state.filtered_data["edited_rows"].items() if value["select"]]
    selected_item = st.session_state.filtered_df.loc[selected_index]
    selected_item = selected_item.reset_index(drop=True)

    if not selected_item.empty:
        for idx, row in selected_item.iterrows():
            sponsor_opportunity = ''
            if pd.notnull(row["SPONSOR"]) and pd.notnull(row["OPPORTUNITY_NAME"]):
                sponsor_opportunity = f"{row['SPONSOR']} {row['OPPORTUNITY_NAME']}"
            elif pd.notnull(row["SPONSOR"]):
                sponsor_opportunity = f"{row['SPONSOR']}"
            elif pd.notnull(row["OPPORTUNITY_NAME"]):
                sponsor_opportunity = f"{row['OPPORTUNITY_NAME']}"
            
            if sponsor_opportunity and pd.notnull(row["URL"]):
                sponsor_opportunity = f"<a href='{row['URL']}'><b>{sponsor_opportunity}</b></a>"
            elif sponsor_opportunity:
                sponsor_opportunity = f"<b>{sponsor_opportunity}</b>"
            
            if sponsor_opportunity:
                st.markdown(sponsor_opportunity, unsafe_allow_html=True)

            if pd.notnull(row["AMOUNT"]):
                st.markdown(f"<b>AMOUNT:</b> {row['AMOUNT']}", unsafe_allow_html=True)

            if pd.notnull(row["DEADLINE"]):
                st.markdown(f"<b>DEADLINE:</b> {row['DEADLINE_TYPE']} due {row['DEADLINE']}", unsafe_allow_html=True)
            else:
                st.markdown(f"<b>DEADLINE:</b> Rolling", unsafe_allow_html=True)

            if pd.notnull(row["ELIGIBILITY_REQUIREMENTS"]):
                st.markdown(f"<b>ELIGIBILITY REQUIREMENTS:</b> {row['ELIGIBILITY_REQUIREMENTS']}", unsafe_allow_html=True)

            for col in selected_item.columns:
                if col not in ["select", "ID_NUMBER", "SPONSOR", "OPPORTUNITY_NAME", "URL", "TAGS", "DESCRIPTION", "DEADLINE_STATUS", "DEADLINE", "AMOUNT", "DEADLINE_TYPE", "CAREER_LEVEL", "DURATION", "ELIGIBILITY_REQUIREMENTS", "LIMITED_SUBMISSION"] and pd.notnull(row[col]):
                    st.markdown(f"<b>{col}:</b> {row[col]}", unsafe_allow_html=True)
                    
            if pd.notnull(row["DESCRIPTION"]):
                st.markdown(f"<b>DESCRIPTION:</b> {row['DESCRIPTION']}", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()

