import pandas as pd
import streamlit as st
import plotly.express as px
from PIL import Image
import base64
import io
from io import StringIO, BytesIO
import plotly.graph_objects as go
from plotly.subplots import make_subplots


st.set_page_config(page_title="Cost Comparison", layout="wide")
# # Function to create download link for DataFrame
def get_download_link(df, label):
    # Reset index if MultiIndex columns are present
    if isinstance(df.columns, pd.MultiIndex):
        df = df.reset_index()
    # Convert DataFrame to XLSX file in memory
    output = io.BytesIO()
    df.to_excel(output, engine='xlsxwriter')
    xlsx_data = output.getvalue()
    # Encode Excel data as base64 string
    b64 = base64.b64encode(xlsx_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="report_{label}.xlsx">{label}</a>'
    return href

def fill_messa7ma(df):
    for course in df['Course Name'].unique():
        course_df = df[df['Course Name'] == course]  # Get all rows for the current course
        not_null_value = course_df['مساهمة'].dropna().iloc[0]  # Get the non-null value of "مساهمة"
        course_df.loc[course_df['مساهمة'].isna(), 'مساهمة'] = not_null_value / (course_df['Number Of Participants'])
        df.update(course_df)  # Update the main DataFrame with filled values
    return df

# Fill null values in `مساهمة`
def fill_contribution(group):
    non_null_value = group['مساهمة'].dropna().values[0]
    participants = group['Number Of Participants'].iloc[0]
    group['مساهمة'] = group['مساهمة'].fillna(non_null_value / participants)
    return group

def map_course_name(row, reference_df):
    # Filter cbe_course based on matching start/end dates and participant count
    match = reference_df[
        (reference_df['Class Start Date'] == row['Class Start Date']) &
        (reference_df['Class End Date'] == row['Class End Date']) &
        (reference_df['Number Of Participants'] == row['Number Of Participants'])
    ]
    
    # Return the matched course name or the original course name
    if not match.empty:
        return match['Course Name'].iloc[0]  # Take the first match if multiple
    return row['Course Name']

#%% --- Authenticator
#
# Dummy credentials - replace with a more secure approach for production
USER_CREDENTIALS = {
    "admin": "14591",
    "203359": "gm123456",
    "206354": "body123456"

}


usermap = {'admin': 'Ahmed Nazih', '203359': 'Nahla', '206354': 'Body'}

# Function to authenticate users
def authenticate(username, password):
    if USER_CREDENTIALS.get(username) == password:
        return True
    else:
        return False

# Main app function
def main():
    st.title("CBE Dashboards")
    
    # Check if the user is already logged in
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    # If not authenticated, show login form
    if not st.session_state['authenticated']:
        login_section()
    else:
        app_content()

# Login section
def login_section():
    st.subheader("Login")
    global username
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate(username, password):
            st.session_state['authenticated'] = True
            st.success("Login successful!")
            st.experimental_rerun()  # Refresh to show app content
        else:
            st.error("Invalid username or password. Please try again.")

# Main content to display after login
def app_content():
    st.sidebar.title("Menu")
    
    # Provide a logout button in the sidebar
    if st.sidebar.button("Logout"):
        st.session_state['authenticated'] = False
        st.experimental_rerun()

    # Display actual app content after login
    username = st.text_input("Username")
    full_name = usermap.get(username, username)  # Default to username if not found
    st.write(f"Welcome {full_name} to the secured app!")
    st.write("You are successfully logged in.")

    st.markdown("<h1 style='text-align: center; font-size: 45px;'>Cost Comparison CBE - EBI</h1>", unsafe_allow_html=True)


    uploaded_file = st.file_uploader("Upload CBE Data", type=["xlsx"])
    uploaded_file2 = st.file_uploader("Upload EBI Data", type=["xlsx"])


    if uploaded_file is not None:
        try:
            ebi = pd.read_excel(uploaded_file2)
            cbe = pd.read_excel(uploaded_file)


            # EBI DATA PREPARATION
            ebi['Course Name'] = ebi['Course Name'].fillna(method='ffill')
            ebi['Number Of Participants'] = ebi['Number Of Participants'].fillna(method='ffill')
            ebi['Class Start Date'] = ebi['Class Start Date'].fillna(method='ffill')
            ebi['Class End Date'] = ebi['Class End Date'].fillna(method='ffill')
            ebi = ebi.groupby(['Course Name', 'Number Of Participants', 'Class Start Date', 'Class End Date'], as_index=False).apply(fill_contribution)
            ebi.dropna(subset=['National ID'], inplace=True)
            ebi_col = ['Course Name', 'Class Start Date', 'Class End Date', 'Number Of Participants', 'الاسم', 'National ID', 'مساهمة']
            ebi = ebi[ebi_col]
            ebi = ebi.rename(columns={'الاسم': 'Name'})
            ebi = ebi.rename(columns={'مساهمة': 'Cost'})

            
            
            
            # CBE DATA PREPARATION
            # Create a grouping key based on whether 'Class End Date' is null
            cbe['Grouping Key'] = cbe.apply(
                lambda row: (row['Course Name'], row['Class Start Date']) 
                if pd.isna(row['Class End Date']) 
                else (row['Course Name'], row['Class Start Date'], row['Class End Date']),
                axis=1
            )
            # Group by the generated key and calculate the count of participants
            cbe['Number of Participants'] = cbe.groupby('Grouping Key')['Full Name'].transform('count')
            # Drop the helper 'Grouping Key' column for clean output
            cbe.drop(columns=['Grouping Key'], inplace=True)
            cbe['Number Of Participants'] = cbe.groupby(['Course Name', 'Class Start Date', 'Class End Date'])['Full Name'].transform('count')
            cbe = cbe.rename(columns={'Id Number': 'National ID'})
            cbe = cbe.rename(columns={'Actual Cost': 'Cost'})
            cbe = cbe.rename(columns={'Full Name': 'Name'})
            cbe_col = ['Course Name', 'Class Start Date', 'Class End Date','Number Of Participants',  'Name', 'National ID', 'Cost']
            cbe = cbe[cbe_col]
            cbe = cbe.drop_duplicates()

            #-------------------------------#
            # Apply the mapping function to update ebi_course
            ebi['Course Name'] = ebi.apply(map_course_name, axis=1, reference_df=cbe)

            cbe_course_list = cbe[['Course Name', 'Class Start Date', 'Class End Date']].drop_duplicates()
            ebi_course_list = ebi[['Course Name', 'Class Start Date', 'Class End Date']].drop_duplicates()

            ebi_merged = pd.merge(ebi, cbe, on=['Course Name', 'Class Start Date', 'Class End Date', 'Number Of Participants'], how='left', indicator=True, suffixes=('_ebi', '_cbe'))
            cbe_merged = pd.merge(ebi, cbe, on=['Course Name', 'Class Start Date', 'Class End Date', 'Number Of Participants'], how='right', indicator=True, suffixes=('_ebi', '_cbe'))

            ebi_only = ebi_merged[ebi_merged['_merge'] == 'left_only']
            ebi_only = ebi_only[['Course Name', 'Class Start Date', 'Class End Date', 'Number Of Participants', 'Name_ebi', 'National ID_ebi', 'Cost_ebi']]

            cbe_only = cbe_merged[cbe_merged['_merge'] == 'right_only']
            cbe_only = cbe_only[['Course Name', 'Class Start Date', 'Class End Date', 'Number Of Participants', 'Name_cbe', 'National ID_cbe', 'Cost_cbe']]

            common_data1 = ebi_merged[ebi_merged['_merge'] == 'both']
            common_data1 = common_data1[['Course Name', 'Class Start Date', 'Class End Date', 'Number Of Participants',  'Cost_ebi', 'Cost_cbe']]

            cost_compare = common_data1.copy()
            cost_compare['Cost Difference'] = cost_compare['Cost_cbe'] - cost_compare['Cost_ebi']

            odd_cost = cost_compare[cost_compare['Cost Difference'] != 0]
            unique_odd_cost = odd_cost.drop_duplicates()




            st.write('**Courses found in EBI and not found in CBE**')
            st.dataframe(ebi_only)
            download_links1 = {
                'Download Report - Data Missed in CBE': ebi_only,
            }
            # Download button
            # Display download links
            for label1, data1 in download_links1.items():
                download_link1 = get_download_link(data1, label1)
                st.markdown(download_link1, unsafe_allow_html=True)



            st.write('**Courses found in CBE and not found in EBI**')
            st.dataframe(cbe_only)
            download_links2 = {
                'Download Report - Data Missed in EBI': cbe_only,
            }
            # Download button
            # Display download links
            for label2, data2 in download_links2.items():
                download_link2 = get_download_link(data2, label2)
                st.markdown(download_link2, unsafe_allow_html=True)

#---#

                        # st.dataframe(ebi_courses_disc)

            try:
                # some code
                if len(unique_odd_cost) == 0:
                    st.write("Successfully Compared: No discrepancies found.")
                else:
                    st.write("Discrepancies found:")
                    st.dataframe(odd_cost)
                    
                    download_links3 = {
                        'Download Report - Disc.': odd_cost,
                    }
                    # Download button
                    # Display download links
                    for label3, data3 in download_links3.items():
                        download_link3 = get_download_link(data3, label3)
                        st.markdown(download_link3, unsafe_allow_html=True)

                st.write("**Clean Identical Data**")
                st.dataframe(cost_compare[cost_compare['Cost Difference'] == 0])
                download_links4 = {
                        'Download Report - Identical.': (cost_compare[cost_compare['Cost Difference'] == 0]),
                    }
                # Display download links
                for label4, data4 in download_links4.items():
                    download_link4 = get_download_link(data4, label4)
                    st.markdown(download_link4, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"An error occurred: {e}")

        except Exception as e:
            st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()

