import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import numpy as np

# ================== Configuración ==================
st.set_page_config(
    page_title="Dashboard Contrataciones Públicas Ecuador",
    layout="wide",
    page_icon="🏛️"
)

# ================== Header Principal ==================
st.title("🏛️ Dashboard de Contrataciones Públicas Ecuador")
st.markdown("Visualización de procesos de contratación pública - Datos abiertos del Ecuador")

# ================== Sidebar con filtros ==================
with st.sidebar:
    st.header("🔍 Filtros")
    
    year_selected = st.selectbox(
        "Año de análisis",
        ["Todos"] + list(range(2015, 2026)),
        help="Selecciona el año específico o 'Todos' para análisis histórico"
    )
    
    search_keyword = st.text_input(
        "Palabra clave",
        value="agua",
        help="Término de búsqueda (mínimo 3 caracteres)"
    )
    
    buyer_filter = st.text_input(
        "Provincia / Entidad",
        help="Filtrar por provincia o entidad contratante específica"
    )
    
    type_filter = st.text_input(
        "Tipo de contratación",
        help="Filtrar por tipo específico de proceso de contratación"
    )
    
    apply_filters = st.button("Aplicar Filtros y Generar Dashboard", use_container_width=True)

# ================== CARGA DE DATOS - Función ==================
@st.cache_data(ttl=3600)
def load_data(year, search, buyer=None, max_pages=10):
    """
    Carga datos de la API search_ocds con paginación y reintentos.
    """
    all_data = []
    page = 1
    base_url = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/search_ocds"

    while page <= max_pages:
        params = {"year": year, "search": search, "page": page}
        if buyer:
            params["buyer"] = buyer

        for intento in range(3):
            try:
                response = requests.get(base_url, params={k: v for k, v in params.items() if v})
                if response.status_code == 429:
                    time.sleep(5)
                    continue
                response.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    time.sleep(5)
                    continue
                else:
                    st.error(f"Error HTTP {response.status_code}: {e}")
                    return pd.DataFrame()
            except Exception as e:
                st.error(f"Error al conectar con la API: {e}")
                return pd.DataFrame()

        data_json = response.json()
        data_page = data_json.get("data", [])
        if not data_page:
            break

        for item in data_page:
            row = {
                "ID": item.get("id"),
                "OCID": item.get("ocid"),
                "Date": item.get("date"),
                "Year": item.get("year"),
                "Month": item.get("month"),
                "Method": item.get("method"),
                "Tipo_Contratacion": item.get("internal_type"),
                "Provincia": item.get("buyer"),
                "Localidad": item.get("locality"),
                "Region": item.get("region"),
                "Proveedores": item.get("suppliers"),
                "Monto": item.get("amount"),
                "Titulo": item.get("title"),
                "Descripcion": item.get("description"),
                "Presupuesto": item.get("budget")
            }
            all_data.append(row)

        if page >= data_json.get("pages", 1):
            break
        page += 1
        time.sleep(1.5)

    df = pd.DataFrame(all_data)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Tipo_Contratacion"] = df["Tipo_Contratacion"].fillna("No especificado").str.title()
        df["Provincia"] = df["Provincia"].fillna("No especificado").str.upper()
    return df

# ================== PROCESAMIENTO DE DATOS ==================
if apply_filters:
    if len(search_keyword) < 3:
        st.error("La palabra clave debe tener al menos 3 caracteres.")
    else:
        year_param = None if year_selected == "Todos" else year_selected
        
        with st.spinner("Cargando datos..."):
            df = load_data(year_param, search_keyword, buyer_filter if buyer_filter else None)

        if df.empty:
            st.warning("No se encontraron registros con los filtros aplicados.")
        else:
            # Limpieza de datos
            df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            
            # Filtros adicionales
            if buyer_filter.strip():
                df = df[df["Provincia"].str.contains(buyer_filter.upper(), na=False)]
            if type_filter.strip():
                df = df[df["Tipo_Contratacion"].str.contains(type_filter, case=False, na=False)]
            
            # Eliminar filas sin monto o tipo
            df = df.dropna(subset=["Monto", "Tipo_Contratacion"])
            df = df[df["Monto"] > 0]
            df = df.drop_duplicates(subset=["ID"], keep="first")

            if df.empty:
                st.warning("No hay datos válidos después de la limpieza.")
            else:
                # ================== RESUMEN EJECUTIVO ==================
                st.header("Resumen Ejecutivo")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total de Contratos", f"{len(df):,}")
                col2.metric("Proveedores Únicos", f"{df['Proveedores'].nunique():,}")
                col3.metric("Tipos de Contratación", f"{df['Tipo_Contratacion'].nunique()}")
                col4.metric("Provincias/Entidades", f"{df['Provincia'].nunique()}")

                col1, col2, col3 = st.columns(3)
                col1.metric("Monto Total", f"${df['Monto'].sum():,.0f}")
                col2.metric("Monto Promedio", f"${df['Monto'].mean():,.0f}")
                col3.metric("Monto Mediano", f"${df['Monto'].median():,.0f}")

                # ================== VISUALIZACIONES ==================
                st.header("Análisis de Datos")

                # Tab 1: Distribuciones
                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                    "Tipos de Contratación",
                    "Evolución Temporal",
                    "Distribución Mensual",
                    "Proporción",
                    "Relación Monto-Cantidad",
                    "Análisis por Año"
                ])

                # TAB 1: Tipos de Contratación
                with tab1:
                    montos_por_tipo = df["Tipo_Contratacion"].value_counts().head(15).reset_index()
                    montos_por_tipo.columns = ["Tipo_Contratacion", "Cantidad"]
                    
                    fig1 = px.bar(
                        montos_por_tipo,
                        x="Tipo_Contratacion",
                        y="Cantidad",
                        text="Cantidad",
                        title="Tipos de Contratación Más Utilizados",
                        labels={"Cantidad": "Cantidad de Contratos"}
                    )
                    fig1.update_traces(textposition='outside')
                    st.plotly_chart(fig1, use_container_width=True)

                # TAB 2: Evolución Temporal
                with tab2:
                    df_monthly = df.groupby(pd.Grouper(key='Date', freq='M')).size().reset_index(name='count')
                    
                    fig2 = px.line(
                        df_monthly,
                        x="Date",
                        y="count",
                        markers=True,
                        title="Evolución Mensual de Contratos",
                        labels={"Date": "Mes", "count": "Cantidad de Contratos"}
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                # TAB 3: Distribución Mensual por Tipo
                with tab3:
                    df_stack = df.groupby([df["Month"], "Tipo_Contratacion"]).size().reset_index(name='count')
                    
                    fig3 = px.bar(
                        df_stack,
                        x="Month",
                        y="count",
                        color="Tipo_Contratacion",
                        barmode='stack',
                        title="Distribución Mensual por Tipo de Contratación",
                        labels={"Month": "Mes", "count": "Cantidad"}
                    )
                    st.plotly_chart(fig3, use_container_width=True)

                # TAB 4: Proporción
                with tab4:
                    montos_pie = df["Tipo_Contratacion"].value_counts().head(10).reset_index()
                    montos_pie.columns = ["Tipo_Contratacion", "Cantidad"]
                    
                    fig4 = px.pie(
                        montos_pie,
                        names="Tipo_Contratacion",
                        values="Cantidad",
                        title="Proporción de Contratos por Tipo (Top 10)"
                    )
                    st.plotly_chart(fig4, use_container_width=True)

                # TAB 5: Relación Monto-Cantidad
                with tab5:
                    df_scatter = df.groupby("Tipo_Contratacion").agg(
                        Cantidad=("ID", "count"),
                        Monto_Total=("Monto", "sum")
                    ).reset_index()
                    df_scatter = df_scatter[df_scatter["Monto_Total"] > 0]

                    if not df_scatter.empty:
                        corr = df_scatter["Cantidad"].corr(df_scatter["Monto_Total"])
                        
                        fig5 = px.scatter(
                            df_scatter,
                            x="Cantidad",
                            y="Monto_Total",
                            size="Monto_Total",
                            hover_name="Tipo_Contratacion",
                            title=f"Relación: Cantidad vs Monto Total (Correlación: {corr:.2f})",
                            labels={"Cantidad": "Cantidad de Contratos", "Monto_Total": "Monto Total"}
                        )
                        st.plotly_chart(fig5, use_container_width=True)

                # TAB 6: Análisis por Año
                with tab6:
                    col_year1, col_year2 = st.columns(2)
                    
                    with col_year1:
                        df_tipo_year = df.groupby(["Year", "Tipo_Contratacion"]).size().reset_index(name="Cantidad")
                        fig6a = px.bar(
                            df_tipo_year,
                            x="Year",
                            y="Cantidad",
                            color="Tipo_Contratacion",
                            barmode="stack",
                            title="Distribución de Tipos por Año"
                        )
                        st.plotly_chart(fig6a, use_container_width=True)
                    
                    with col_year2:
                        df_monto_year = df.groupby("Year")["Monto"].sum().reset_index()
                        fig6b = px.line(
                            df_monto_year,
                            x="Year",
                            y="Monto",
                            markers=True,
                            title="Evolución del Monto Total por Año",
                            labels={"Monto": "Monto Total"}
                        )
                        st.plotly_chart(fig6b, use_container_width=True)

                    # Heatmap
                    df_heatmap = df.groupby(["Year", "Month"]).size().reset_index(name='Cantidad')
                    pivot_heatmap = df_heatmap.pivot(index="Year", columns="Month", values="Cantidad").fillna(0)
                    
                    fig6c = px.imshow(
                        pivot_heatmap,
                        labels=dict(x="Mes", y="Año", color="Contratos"),
                        title="Mapa de Calor: Actividad por Año y Mes",
                        aspect="auto"
                    )
                    st.plotly_chart(fig6c, use_container_width=True)

                # ================== TABLA DE DATOS ==================
                st.header("Vista de Datos")
                
                with st.expander("Ver datos detallados"):
                    st.dataframe(
                        df[["ID", "Date", "Tipo_Contratacion", "Provincia", "Monto", "Titulo"]],
                        use_container_width=True,
                        hide_index=True
                    )

                # ================== DESCARGA ==================
                st.header("Descargar Resultados")
                
                col_exp1, col_exp2, col_exp3 = st.columns(3)
                
                with col_exp1:
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Descargar Datos Procesados",
                        data=csv_data,
                        file_name=f"contrataciones_{search_keyword}_{year_selected}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_exp2:
                    resumen = df.groupby("Tipo_Contratacion").agg({
                        "Monto": ["sum", "mean", "count"]
                    }).round(2)
                    resumen_csv = resumen.to_csv()
                    st.download_button(
                        label="Resumen por Tipo",
                        data=resumen_csv,
                        file_name=f"resumen_{search_keyword}_{year_selected}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_exp3:
                    por_provincia = df.groupby("Provincia").agg({
                        "Monto": ["sum", "count"]
                    }).round(2)
                    provincia_csv = por_provincia.to_csv()
                    st.download_button(
                        label="Datos por Provincia",
                        data=provincia_csv,
                        file_name=f"provincia_{search_keyword}_{year_selected}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

else:
    st.info("Configure los filtros en la barra lateral y haga clic en 'Aplicar Filtros y Generar Dashboard' para comenzar.")