# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import warnings
warnings.filterwarnings('ignore')
import pandas as pd 
import numpy as np
pd.set_option('display.max_columns', 20)


import holidays

import os
from flask import Flask, render_template, request

app = Flask(__name__)
app.template_folder = os.path.abspath('templates')

# create a dataframe 

def make_holidays(year_s, year_f):
    holiday_ch = []
    for i in ['AG', 'AR', 'AI', 'BL', 'BS', 'BE', 'FR', 'GE', 'GL', 'GR',
              'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SZ', 'SO', 'TG',
              'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH']:
        temp = [[date, name, i] for date, name in sorted(holidays.CH(prov=i, years=range(year_s, year_f+1)).items())]
        holiday_ch.extend(temp)
    
    holiday_df = pd.DataFrame(holiday_ch, columns=['ds', 'holiday', 'kanton'])
    holiday_df['ds'] = pd.to_datetime(holiday_df['ds'])
    holiday_df['dayName'] = holiday_df['ds'].dt.day_name()
    day_filter = ["Sunday", "Saturday"]
    
    holiday_agg = holiday_df.groupby([holiday_df['ds'].dt.to_period('M'), 'kanton']).agg(
        holiday_includingWeekend=('dayName', 'count'),
        holiday=('holiday', lambda x: list(x.unique()))
    ).reset_index()
    
    holiday_df_filtered = holiday_df[~holiday_df['dayName'].isin(day_filter)]
    holiday_agg_filtered = holiday_df_filtered.groupby([holiday_df_filtered['ds'].dt.to_period('M'), 'kanton']).agg(
        holiday_excludingWeekend=('dayName', 'count')).reset_index()
    
    holiday_df = pd.merge(holiday_agg, holiday_agg_filtered, on=['ds', 'kanton'], how='outer').fillna(0)
    
    date_range = pd.date_range(start=str(year_s)+'-01-01', end=str(year_f)+'-12-31', freq='B')
    # Create a DataFrame with the date range
    df = pd.DataFrame({'Date': date_range})
    # Extract year and month from the date
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month

    # Calculate the number of business days per month
    df['BusinessDays'] = df.groupby(['Year', 'Month'])['Date'].transform(
        lambda x: np.busday_count(x.min().to_numpy().astype('datetime64[D]'), x.max().to_numpy().astype('datetime64[D]')+1)
    )

    # Drop duplicate rows
    df = df.drop_duplicates(subset=['Year', 'Month'])

    # Reset the index
    df = df.reset_index(drop=True)

    # Display the DataFrame
    df['ds']=df.Date.dt.to_period('M')

    df=pd.merge(df,holiday_df,how='outer')
    
    
    df['Corrected_BusinessDays']=df.BusinessDays-df.holiday_excludingWeekend.fillna(0)
    df['holiday']=df.holiday.fillna('No Holidays')
    df['holiday_excludingWeekend']=df.holiday_excludingWeekend.fillna(0)
    df['holiday_includingWeekend']=df.holiday_includingWeekend.fillna(0)
  
    
    coordinates = {
        'kanton': ['AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR', 'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH',
                   'SO', 'SZ', 'TG', 'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH'],  # Update with the canton abbreviations
        'latitude': [47.3917, 47.3167, 47.3833, 46.9480, 47.4671, 47.5686, 46.8064, 46.2044, 47.0408, 46.8523, 47.3687,
                     47.0502, 46.9938, 46.9232, 46.8987, 47.4316, 47.6981, 47.2065, 47.0519, 47.4803, 46.3723, 46.8249,
                     46.5591, 46.1920, 46.1919, 47.1736],  # Update with the latitude values
        'longitude': [8.0447, 9.4167, 9.3833, 7.4515, 7.7347, 7.5896, 7.1587, 6.1432, 9.0656, 9.5298, 7.3397, 8.3063,
                      6.9292, 8.4208, 8.2500, 9.3763, 8.6417, 7.5336, 8.8189, 9.0568, 8.8375, 8.6482, 6.6380, 6.6497,
                      6.6487, 8.1900]  # Update with the longitude values
    }

    coordinates_df = pd.DataFrame(coordinates)

    df = pd.merge(df, coordinates_df, left_on='kanton', right_on='kanton', how='outer')



   

    # Convert the 'kanton' column to string type
    df['kanton'] = df['kanton'].astype(str)
    #df=df[df.latitude.notnull()]
    
    df1=df[df.latitude.notna()]
    df2=df[df.latitude.isna()]
    
   
    
    df3=pd.concat([df2[~df2.Date.isin(df1.Date)]] * 26, ignore_index=True)
    
    df3.kanton=np.repeat(df1.kanton.unique(),df2[~df2.Date.isin(df1.Date)].shape[0])
    df=pd.concat([pd.merge(df3.drop(columns=['longitude','latitude']),df1[['kanton','longitude','latitude']].drop_duplicates(),on='kanton',how='left'),df1])
    
    df=df.sort_values(['Year','Month','kanton'])
    return df

df=make_holidays(2022, 2024)

@app.route('/')
def index():
    # Get unique kantons and years from the DataFrame
    kantons = sorted(df['kanton'].unique())
    years = sorted(df['Year'].dropna().unique().astype(int))

    # Get the selected kanton and year from the URL parameters
    selected_kanton = request.args.get('kanton', '')
    selected_year = request.args.get('year', '')

    # Apply filters to the DataFrame based on the selected kanton and year
    filtered_df = df
    if selected_kanton:
        filtered_df = filtered_df[filtered_df['kanton'] == selected_kanton]
        selected_latitude = filtered_df['latitude'].iloc[0]
        selected_longitude = filtered_df['longitude'].iloc[0]
    else:
        selected_latitude = None
        selected_longitude = None
    if selected_year:
        selected_year = int(selected_year)
        filtered_df = filtered_df[filtered_df['Year'] == selected_year]

    # Convert the filtered DataFrame to a list of dictionaries
    table_data = filtered_df.to_dict(orient='records')

    return render_template('index.html', kantons=kantons, years=years, selected_kanton=selected_kanton,
                           selected_year=selected_year, table_data=table_data, selected_latitude=selected_latitude,
                           selected_longitude=selected_longitude)

if __name__ == '__main__':
    app.run(debug=True)