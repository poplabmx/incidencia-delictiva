from datetime import datetime
import numpy as np
from pandas import DataFrame
import streamlit as st

months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre',
          'Noviembre',
          'Diciembre']


def int_to_month(n: int):
    return months[n - 1]


# un diccionario de mes a numero
month_to_num = {'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6, 'Julio': 7, 'Agosto': 8,
                'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12}


@st.cache_data
def file_cleaner(df: DataFrame):
    with st.spinner("Limpiando archivo"):
        l = []
        df = df.fillna(int(0))
        for year, df1 in df.groupby('Año'):
            for month in months:
                date = datetime(year, month_to_num[month], 15)
                for row in df1.to_dict('records'):
                    row['Fecha'] = date
                    row['Año-Mes'] = str(year) + '-' + month
                    n = row[month]
                    if n == '' or n == np.nan:
                        n = 0
                    for m in months:
                        del row[m]
                    try:
                        row['N'] = int(n)
                    except ValueError:
                        print(row, n)
                        row['N'] = 0
                    row['Mes'] = month
                    l.append(row)

        df = DataFrame(l)
        df = df.drop(['Modalidad'], axis=1)
        df['Total'] = df.groupby(['Año', 'Clave_Ent', 'Entidad',
                                  'Tipo de delito', 'Subtipo de delito', 'Municipio',
                                  'Año-Mes', 'Mes'])['N'].transform('sum')
        df.drop(['N'], axis=1, inplace=True)
        df = df.drop_duplicates()
        df['Fecha-dt'] = df['Fecha'].dt.date
    st.success("Archivo limpiado")
    return df
