import numpy as np
import streamlit as st
import requests
import pandas as pd
import pandas_profiling
from streamlit_pandas_profiling import st_profile_report
from cleaner.file_cleaner import file_cleaner, int_to_month
import re


def offset_label(start, end):
    end = end - pd.DateOffset(months=1)
    if start.month == end.month:
        return f'{int_to_month(start.month)} {start.year}'
    return f'{int_to_month(start.month)} {start.year} - {int_to_month(end.month)} {end.year}'


@st.cache_data
def download_file_from_google_drive(id, destination):
    URL = "https://docs.google.com/uc?export=download&confirm=1"

    session = requests.Session()

    response = session.get(URL, params={"id": id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {"id": id, "confirm": token}
        response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)


def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value

    return None


def save_response_content(response, destination):
    CHUNK_SIZE = 32768
    with st.spinner("Descargando archivo"):
        with open(destination, "wb") as f:
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
    st.success("Archivo descargado")


@st.cache_data
def df_to_csv(df: pd.DataFrame):
    return df.to_csv(index=False)


@st.cache_data
def get_report(df: pd.DataFrame):
    # duplicate rows using the 'N' column, remove the rows with N = 0 and then drop the 'N' column
    df = df.loc[df.index.repeat(df['Total'])].drop('Total', axis=1)
    return df.profile_report(title="Análisis exploratorio de datos")


sidebar = st.sidebar
sidebar.title("Instrucciones:")

sidebar.markdown("""
                 Entre a la siguiente liga para descargar los archivos del secretariado:
                 [Descarga de datos](https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva)
                 
                 Copia la liga de uno de los siguientes archivos de la nueva metodología: 
                 * Cifras de Incidencia Delictiva Municipal
                 * Cifras de Víctimas del Fuero Común
                    """)


def idm():
    st.title("Cifras de Incidencia Delictiva Municipal")
    st.session_state["gt_only"] = True
    gto_only = st.checkbox("Procesar sólo Guanajuato", key="gt_only")
    st.warning("Advertencia: Procesar todos los estados puede tardar mucho tiempo")
    fileurl = st.text_input("Ingresa la URL del archivo en drive")
    if fileurl:
        file_id = fileurl.split("/")[-2]
        destination = "idm.csv"
        download_file_from_google_drive(file_id, destination)
        df = pd.read_csv(destination, encoding="latin")
        if gto_only:
            df = df[df['Clave_Ent'] == 11]
        st.success("Archivo cargado")
        df = file_cleaner(df)
        # descarga de datos
        """## Filtrado de datos"""
        """### Filtrado por tipo de delito"""
        should_filter_by_crime_type = st.checkbox("Filtrar por tipo de delito")
        if should_filter_by_crime_type:
            tipos_de_delito = df['Tipo de delito'].unique()
            # haz una lista de selección para los tipos de delito
            tipos_de_delito_seleccionados = st.multiselect("Selecciona los tipos de delito a procesar", tipos_de_delito)

            # filtra el dataframe por los tipos de delito seleccionados
            df = df[df['Tipo de delito'].isin(tipos_de_delito_seleccionados)]

            subtipos_de_delito = df['Subtipo de delito'].unique()
            # haz una lista de selección para los subtipos de delito
            subtipos_de_delito_seleccionados = st.multiselect("Selecciona los subtipos de delito a procesar",
                                                              subtipos_de_delito)

            # filtra el dataframe por los subtipos de delito seleccionados
            df = df[df['Subtipo de delito'].isin(subtipos_de_delito_seleccionados)]

        """### Filtrado por municipio"""

        should_filter_by_municipality = st.checkbox("Filtrar por municipio")

        if should_filter_by_municipality:
            municipios = df['Municipio'].unique()
            municipios_seleccionados = st.multiselect("Selecciona los municipios a procesar", municipios)
            df = df[df['Municipio'].isin(municipios_seleccionados)]

        # periodo de tiempo
        """### Filtrado por periodo de tiempo"""

        should_filter_by_time = st.checkbox("Filtrar por periodo de tiempo")
        # haz una lista de selección para los años
        if should_filter_by_time:
            min_date = df['Fecha'].min()
            min_date = pd.to_datetime(min_date).date()
            max_date = df['Fecha'].max()
            max_date = pd.to_datetime(max_date).date()

            st.write("Elige el periodo de tiempo a procesar")
            start_date = st.date_input("Fecha de inicio", min_date)
            end_date = st.date_input("Fecha de fin", max_date)

            st.write(df.head())
            st.write(df['Fecha'].min())

            if start_date > end_date:
                st.error("La fecha de inicio debe ser menor a la fecha de fin")
            else:
                # create timestamp objects from the dates
                start_date_timestamp = pd.to_datetime(start_date)
                end_date_timestamp = pd.to_datetime(end_date)
                st.write(start_date_timestamp)
                df = df[(df['Fecha-dt'] >= start_date) & (df['Fecha-dt'] <= end_date)]

        # descarga de datos
        """## Descarga de datos filtrados"""
        st.download_button("Descargar datos filtrados", data=df_to_csv(df), file_name="idm.csv", mime="text/csv")

        """## Análisis de datos"""
        """### Análisis exploratorio de datos"""
        show_report = st.checkbox("Mostrar reporte")
        if show_report:
            st_profile_report(get_report(df))

        """### Gráficas"""
        df.columns
        should_show_graphs = st.checkbox("Mostrar gráficas")
        if should_show_graphs:
            dfg = df.copy()
            dfg = dfg.loc[dfg.index.repeat(df['Total'])].drop('Total', axis=1)

            # agrupación de tiempo
            """#### Agrupación de tiempo"""
            time_grouping = st.selectbox("Selecciona el tipo de agrupación de tiempo",
                                         ["1M", "3M", "6M", "12M", "1Y", "2Y", "3Y", "5Y"])

            time_offset_amount = int(re.search(r'\d+', time_grouping).group())
            time_offset_unit = re.search(r'[A-Z]', time_grouping).group()

            if time_offset_unit == 'M':
                offset = pd.DateOffset(months=time_offset_amount)
            elif time_offset_unit == 'Y':
                offset = pd.DateOffset(years=time_offset_amount)

            st.write(offset)

            if time_grouping:
                cm = pd.DataFrame()
                cm['Cve. Municipio'] = df['Cve. Municipio']
                cm['Municipio'] = df['Municipio']
                cm.drop_duplicates(inplace=True)
                cm.set_index('Municipio', inplace=True)
                if not should_filter_by_time:
                    min_date = df['Fecha'].min()
                    start_date = pd.to_datetime(min_date).date()
                    max_date = df['Fecha'].max()
                    end_date = pd.to_datetime(max_date).date()
                f"""Fecha de inicio: {start_date}
                Fecha de fin: {end_date}"""
                end_date = end_date + pd.DateOffset(months=1)
                f"""Fecha de inicio: {start_date}
                Fecha de fin: {end_date}"""
                ranges = []
                masks = []
                date_range = list(pd.date_range(start=start_date, end=end_date, freq=time_grouping))
                for i in range(len(date_range)):
                    if i == 0:
                        continue
                    previous_date = date_range[i - 1]
                    current_date = date_range[i]

                    ranges.append((previous_date, current_date))

                    mask = (df['Fecha'] >= previous_date) & (df['Fecha'] < current_date)
                    masks.append(mask)

                di = {}
                maxes = []
                start = ranges[0][0]
                end = start + offset
                first_period = offset_label(start, end)
                st.write(first_period)
                for mask in masks:
                    df_mask = df.loc[mask]
                    d = df_mask.groupby('Municipio').sum('Total').reset_index()
                    d.drop(['Cve. Municipio'], axis=1, inplace=True)

                    d['Cve. Municipio'] = d['Municipio'].map(cm.to_dict()['Cve. Municipio'])

                    d.sort_values(by='Cve. Municipio', inplace=True)
                    # end should be the start + the time grouping

                    end = start + offset

                    period = offset_label(start, end)

                    di[period] = []
                    municipality_added = False

                    for row in d.to_dict('records'):
                        if period == first_period:
                            di[period].append({
                                'Municipio': row['Municipio'],
                                period: row['Total'],
                            })

                        else:
                            di[period].append({
                                period: row['Total'],
                            })

                    # d.to_csv('output/municipios/municipios_' + str(y) + '.csv', index=False)

                    m = d.groupby('Municipio').sum()['Total'].max()
                    maxes.append(m)
                    start = end

                # db6.loc[masks[0]].groupby('Municipio').sum().to_csv('municipios_2018.csv', index=False)
                for y in di.keys():
                    df1 = pd.DataFrame(di[y])
                    di[y] = df1

                # join all the dataframes
                start = ranges[0][0]
                # end should be the start + the time grouping
                end = start + offset
                period = offset_label(start, end)

                dfj = di[period]
                for y in di.keys():
                    if y == period:
                        continue
                    dfj = dfj.join(di[y])
                dfj['Total'] = dfj.sum(axis=1, numeric_only=True)
                dfj = dfj.sort_values(by=['Total'], ascending=False)
                dfj


def idfc():
    st.title("Cifras de Víctimas del Fuero Común")


pages_names_to_functions = {
    "Cifras de Incidencia Delictiva Municipal": idm,
    "Cifras de Víctimas del Fuero Común": idfc
}

page = sidebar.selectbox("Selecciona el tipo de datos a procesar", tuple(pages_names_to_functions.keys()))

pages_names_to_functions[page]()
