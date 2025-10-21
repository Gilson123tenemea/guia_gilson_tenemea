import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from urllib.parse import quote
import numpy as np

# ================== Configuración ==================
st.set_page_config(
    page_title="Dashboard Contrataciones Públicas Ecuador",
    layout="wide",
    page_icon="🏛️"
)

# ================== Estilos CSS personalizados ==================
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 800;
    }
    .metric-card {
        background: linear-gradient(135deg, #ecf0f1 0%, #d5dbdb 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #34495e;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .section-header {
        font-size: 1.8rem;
        color: #2c3e50;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #34495e;
        font-weight: 600;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #34495e 0%, #5d6d7b 100%);
    }
    .stButton button {
        background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        width: 100%;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .interpretation-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #34495e;
        margin-top: 1rem;
        font-size: 0.9rem;
        color: #2c3e50;
    }

</style>
""", unsafe_allow_html=True)

# ================== Header Principal ==================
st.markdown('<h1 class="main-header">🏛️ Dashboard de Contrataciones Públicas Ecuador</h1>', unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #7f8c8d; font-size: 1.2rem; margin-bottom: 2rem;'>
    Visualización avanzada de procesos de contratación pública - Datos abiertos del Ecuador
</div>
""", unsafe_allow_html=True)

# ================== 1. DEFINICIÓN DEL PROBLEMA ==================
with st.expander("🎯 **1. Definición del Problema y Objetivos**", expanded=True):
    st.markdown("""
    ### Objetivo General
    Analizar los datos de compras públicas en Ecuador para identificar patrones, tendencias y relaciones entre variables relevantes.
    
    ### Preguntas Guía
    - **¿Cuáles son los tipos de contratación más frecuentes en los diferentes años?**
    - **¿Cómo se distribuyen los montos de contratación por provincia y tipo de compra?**
    - **¿Existen tendencias crecientes o decrecientes en el tiempo respecto a los montos contratados?**
    - **¿Qué variables presentan correlación significativa con el monto total?**
    """)

# ================== Sidebar con diseño mejorado ==================
with st.sidebar:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%); padding: 2rem; border-radius: 10px; color: white; text-align: center;'>
        <h2 style='margin: 0; color: white;'>🔍 Filtros</h2>
        <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>Personaliza tu análisis</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ================== 2. CARGA DE DATOS - Filtros ==================
    year_selected = st.selectbox(
        "📅 **Año de análisis**",
        ["Todos"] + list(range(2015, 2026)),
        help="Selecciona el año específico o 'Todos' para análisis histórico"
    )
    
    search_keyword = st.text_input(
        "🔎 **Palabra clave**",
        value="agua",
        help="Término de búsqueda (mínimo 3 caracteres)"
    )
    
    buyer_filter = st.text_input(
        "🏙️ **Provincia / Entidad**",
        help="Filtrar por provincia o entidad contratante específica"
    )
    
    type_filter = st.text_input(
        "📑 **Tipo de contratación**",
        help="Filtrar por tipo específico de proceso de contratación"
    )
    
    # Botón con diseño mejorado
    apply_filters = st.button("🚀 Aplicar Filtros y Generar Dashboard")

# ================== 2. CARGA DE DATOS - Función ==================
@st.cache_data(ttl=3600)
def load_data(year, search, buyer=None, max_pages=10):
    """
    Carga datos de la API search_ocds con paginación, control de pausas y reintentos.
    Limita a 'max_pages' páginas para evitar 429 Too Many Requests.
    """
    all_data = []
    page = 1
    base_url = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/search_ocds"

    while page <= max_pages:
        params = {"year": year, "search": search, "page": page}
        if buyer:
            params["buyer"] = buyer

        for intento in range(3):  # hasta 3 reintentos
            try:
                response = requests.get(base_url, params={k: v for k, v in params.items() if v})
                if response.status_code == 429:
                    st.warning("⚠️ Límite de solicitudes alcanzado. Esperando 5 segundos antes de reintentar...")
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
                "Tipo de Contratación": item.get("internal_type"),
                "Provincia / Buyer": item.get("buyer"),
                "Localidad": item.get("locality"),
                "Región": item.get("region"),
                "Proveedor(s)": item.get("suppliers"),
                "Monto": item.get("amount"),
                "Título": item.get("title"),
                "Descripción": item.get("description"),
                "Presupuesto": item.get("budget")
            }
            all_data.append(row)

        if page >= data_json.get("pages", 1):
            break
        page += 1
        time.sleep(1.5)  # Esperar entre peticiones para evitar 429

    df = pd.DataFrame(all_data)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Tipo de Contratación"] = df["Tipo de Contratación"].str.title()
        df["Provincia / Buyer"] = df["Provincia / Buyer"].str.upper()
    return df

# ================== Cargar y filtrar datos ==================
if apply_filters:
    if len(search_keyword) < 3:
        st.error("❌ La palabra clave debe tener al menos 3 caracteres.")
    else:
        year_param = None if year_selected == "Todos" else year_selected
        with st.spinner("🔍 Cargando datos, por favor espera... Esto puede tomar unos segundos."):
            df = load_data(year_param, search_keyword, buyer_filter if buyer_filter else None)

        if df.empty:
            st.warning("⚠️ No se encontraron registros con los filtros aplicados.")
        else:
            # ================== 3. LIMPIEZA Y PREPARACIÓN DE DATOS ==================
            with st.expander("🧹 **3. Limpieza y Preparación de Datos**", expanded=True):
                col_clean1, col_clean2 = st.columns(2)
                
                with col_clean1:
                    st.subheader("Estructura Inicial")
                    st.write(f"**Registros:** {len(df)}")
                    st.write(f"**Columnas:** {len(df.columns)}")
                    st.dataframe(df.head(3), use_container_width=True)
                
                with col_clean2:
                    st.subheader("Verificación de Datos")
                    st.write("**Tipos de datos:**")
                    st.write(df.dtypes.astype(str))
                    
                    st.write("**Valores nulos:**")
                    null_counts = df.isnull().sum()
                    st.write(null_counts[null_counts > 0])
            
            # Aplicar filtros locales
            if buyer_filter.strip():
                df = df[df["Provincia / Buyer"].str.contains(buyer_filter.upper(), na=False)]
            if type_filter.strip():
                df = df[df["Tipo de Contratación"].str.contains(type_filter, case=False, na=False)]

            # ================== 3. LIMPIEZA - Procesamiento adicional ==================
            # Convertir columnas a tipos correctos
            df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            
            # Estandarizar nombres
            df = df.rename(columns={
                "Provincia / Buyer": "Provincia",
                "Tipo de Contratación": "Tipo_Contratacion"
            })
            
            # Tratar valores nulos
            initial_count = len(df)
            df = df.dropna(subset=["Monto", "Tipo_Contratacion"])
            final_count = len(df)
            
            # Eliminar duplicados
            df = df.drop_duplicates(subset=["ID"], keep="first")
            
            with st.expander("📊 **Resumen de Limpieza**"):
                st.write(f"**Registros iniciales:** {initial_count}")
                st.write(f"**Registros después de limpieza:** {final_count}")
                st.write(f"**Registros eliminados por nulos:** {initial_count - final_count}")
                st.write(f"**Duplicados eliminados:** {initial_count - len(df)}")
                st.write("**Estructura final:**")
                st.write(df.info())

            # ================== 4. ANÁLISIS DESCRIPTIVO ==================
            st.markdown('<div class="section-header">📊 4. Análisis Descriptivo</div>', unsafe_allow_html=True)
            
            # Tarjetas de Métricas Principales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style='margin: 0; color: #2c3e50;'>📋 Total Contratos</h3>
                    <p style='font-size: 2rem; font-weight: bold; color: #34495e; margin: 0.5rem 0;'>{len(df)}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style='margin: 0; color: #2c3e50;'>🏢 Proveedores Únicos</h3>
                    <p style='font-size: 2rem; font-weight: bold; color: #34495e; margin: 0.5rem 0;'>{df["Proveedor(s)"].nunique()}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style='margin: 0; color: #2c3e50;'>📑 Tipos de Contratación</h3>
                    <p style='font-size: 2rem; font-weight: bold; color: #34495e; margin: 0.5rem 0;'>{df["Tipo_Contratacion"].nunique()}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style='margin: 0; color: #2c3e50;'>🏙️ Provincias/Buyers</h3>
                    <p style='font-size: 2rem; font-weight: bold; color: #34495e; margin: 0.5rem 0;'>{df['Provincia'].nunique()}</p>
                </div>
                """, unsafe_allow_html=True)

            # Estadísticas descriptivas de montos
            st.subheader("Estadísticas Descriptivas - Montos")
            col_stats1, col_stats2 = st.columns(2)
            
            with col_stats1:
                st.metric("Monto Total", f"${df['Monto'].sum():,.2f}")
                st.metric("Monto Promedio", f"${df['Monto'].mean():,.2f}")
                st.metric("Monto Máximo", f"${df['Monto'].max():,.2f}")
            
            with col_stats2:
                st.metric("Monto Mínimo", f"${df['Monto'].min():,.2f}")
                st.metric("Desviación Estándar", f"${df['Monto'].std():,.2f}")
                st.metric("Mediana", f"${df['Monto'].median():,.2f}")

            # DataFrame de estadísticas
            st.dataframe(df['Monto'].describe(), use_container_width=True)

            # ================== 5. VISUALIZACIÓN DE DATOS ==================
            st.markdown('<div class="section-header">📈 5. Visualización de Datos</div>', unsafe_allow_html=True)
            
            # Primera fila de gráficos
            row1_col1, row1_col2 = st.columns(2)

            # a) Barras por tipo de contratación
            with row1_col1:
                montos_por_tipo = df["Tipo_Contratacion"].value_counts().reset_index()
                montos_por_tipo.columns = ["Tipo_Contratacion", "Cantidad de Contratos"]
                
                fig_a = px.bar(
                    montos_por_tipo.head(10),
                    x="Tipo_Contratacion",
                    y="Cantidad de Contratos",
                    color="Tipo_Contratacion",
                    text="Cantidad de Contratos",
                    color_discrete_sequence=px.colors.sequential.Viridis,
                    title="<b>a) Top 10 Tipos de Contratación Más Utilizados</b>"
                )
                fig_a.update_layout(showlegend=False)
                fig_a.update_traces(texttemplate='%{text}', textposition='outside')
                st.plotly_chart(fig_a, use_container_width=True)
                
                st.markdown("""
                <div class="interpretation-box">
                <strong>Interpretación:</strong> Muestra los tipos de contratación más frecuentes. Los tipos con barras más altas 
                representan las modalidades más utilizadas, lo que puede indicar preferencias institucionales o requisitos normativos.
                </div>
                """, unsafe_allow_html=True)

            # b) Línea mensual total
            with row1_col2:
                df_monthly = df.groupby(pd.Grouper(key='Date', freq='M')).size().reset_index(name='count')
                fig_b = px.line(
                    df_monthly,
                    x="Date",
                    y="count",
                    markers=True,
                    labels={"Date": "Mes", "count": "Cantidad de Contratos"},
                    color_discrete_sequence=["#95a5a6"],
                    title="<b>b) Evolución Mensual de Contratos</b>",
                    line_shape="spline"
                )
                st.plotly_chart(fig_b, use_container_width=True)
                
                st.markdown("""
                <div class="interpretation-box">
                <strong>Interpretación:</strong> Muestra la evolución temporal de contratos. Los picos indican períodos de alta 
                actividad, mientras los valles corresponden a menor actividad administrativa o períodos vacacionales.
                </div>
                """, unsafe_allow_html=True)

            # Segunda fila de gráficos
            row2_col1, row2_col2 = st.columns(2)

            # c) Barras apiladas tipo x mes
            with row2_col1:
                df_stack = df.groupby([df["Month"], "Tipo_Contratacion"]).size().reset_index(name='count')
                fig_c = px.bar(
                    df_stack,
                    x="Month",
                    y="count",
                    color="Tipo_Contratacion",
                    barmode='stack',
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    title="<b>c) Distribución Mensual por Tipo de Contratación</b>"
                )
                st.plotly_chart(fig_c, use_container_width=True)
                
                st.markdown("""
                <div class="interpretation-box">
                <strong>Interpretación:</strong> Permite visualizar la distribución de tipos de contratación a lo largo del año. 
                Los colores representan cada tipo, facilitando identificar patrones estacionales y predominancia de modalidades.
                </div>
                """, unsafe_allow_html=True)

            # d) Pastel por proporción de contratos
            with row2_col2:
                fig_d = px.pie(
                    montos_por_tipo.head(8),
                    names="Tipo_Contratacion",
                    values="Cantidad de Contratos",
                    hole=0.6,
                    color_discrete_sequence=px.colors.sequential.Plasma,
                    title="<b>d) Proporción de Contratos por Tipo</b>"
                )
                st.plotly_chart(fig_d, use_container_width=True)
                
                st.markdown("""
                <div class="interpretation-box">
                <strong>Interpretación:</strong> Muestra la proporción porcentual de cada tipo de contratación. Permite identificar 
                rápidamente qué modalidades concentran la mayor parte de los contratos y su participación relativa.
                </div>
                """, unsafe_allow_html=True)

            # ================== 6. RELACIÓN ENTRE MONTO TOTAL Y CANTIDAD ==================
            st.markdown('<div class="section-header">📊 6. Relación entre Monto Total y Cantidad de Contratos</div>', unsafe_allow_html=True)
            
            df_scatter = df.groupby("Tipo_Contratacion").agg(
                Cantidad_Contratos=("ID", "count"),
                Monto_Total=("Monto", "sum")
            ).reset_index()

            df_scatter = df_scatter.dropna(subset=["Monto_Total"])
            df_scatter = df_scatter[df_scatter["Monto_Total"] > 0]

            if not df_scatter.empty:
                corr = df_scatter["Cantidad_Contratos"].corr(df_scatter["Monto_Total"])
                
                fig_scatter = px.scatter(
                    df_scatter,
                    x="Cantidad_Contratos",
                    y="Monto_Total",
                    color="Tipo_Contratacion",
                    size="Monto_Total",
                    hover_name="Tipo_Contratacion",
                    size_max=50,
                    labels={
                        "Cantidad_Contratos": "Cantidad de Contratos",
                        "Monto_Total": "Monto Total (USD)"
                    },
                    color_discrete_sequence=px.colors.qualitative.Vivid,
                    title=f"<b>Dispersión: Monto Total vs. Cantidad de Contratos (Correlación: {corr:.2f})</b>"
                )
                
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                st.markdown(f"""
                <div class="interpretation-box">
                <strong>Interpretación:</strong> 
                - <strong>Correlación: {corr:.2f}</strong> - {'Fuerte positiva' if corr > 0.7 else 'Moderada positiva' if corr > 0.3 else 'Débil positiva' if corr > 0 else 'Negativa'}
                - Cada punto representa un tipo de contratación
                - Cuanto más a la derecha → mayor número de contratos
                - Cuanto más arriba → mayor monto total adjudicado
                - Una correlación positiva indica que tipos con más contratos tienden a manejar montos mayores
                </div>
                """, unsafe_allow_html=True)

            # ================== 7. COMPARATIVA DE TIPOS POR MES ==================
            st.markdown('<div class="section-header">📈 7. Comparativa de Tipos de Contratación por Mes</div>', unsafe_allow_html=True)
            
            df_linea = df.groupby(["Month", "Tipo_Contratacion"], as_index=False).agg({"Monto": "sum"})
            df_linea = df_linea.sort_values(by="Month")

            fig_f = px.line(
                df_linea,
                x="Month",
                y="Monto",
                color="Tipo_Contratacion",
                markers=True,
                labels={
                    "Month": "Mes",
                    "Monto": "Monto Total (USD)",
                    "Tipo_Contratacion": "Tipo de Contratación"
                },
                color_discrete_sequence=px.colors.qualitative.Bold,
                title="<b>Comparativa de Tipos de Contratación por Mes</b>"
            )

            st.plotly_chart(fig_f, use_container_width=True)
            
            st.markdown("""
            <div class="interpretation-box">
            <strong>Interpretación:</strong> Permite comparar directamente el comportamiento de diferentes tipos de contratación 
            a lo largo del año. Las líneas que se mantienen elevadas indican tipos con montos consistentemente altos, mientras 
            que líneas con picos sugieren concentración de montos en meses específicos.
            </div>
            """, unsafe_allow_html=True)

            # ================== 8. ANÁLISIS POR AÑOS ==================
            st.markdown('<div class="section-header">📅 8. Análisis por Años</div>', unsafe_allow_html=True)
            
            # KPIs por año
            st.subheader("KPIs por Año")
            df_kpis_year = df.groupby("Year").agg({
                "ID": "count",
                "Monto": ["sum", "mean", "std"],
                "Proveedor(s)": "nunique",
                "Tipo_Contratacion": "nunique"
            }).round(2)
            
            df_kpis_year.columns = ['Total_Contratos', 'Monto_Total', 'Monto_Promedio', 'Monto_Desviacion', 'Proveedores_Unicos', 'Tipos_Contratacion']
            df_kpis_year = df_kpis_year.reset_index()
            
            st.dataframe(df_kpis_year, use_container_width=True)

            # Gráficos de análisis por año
            col_year1, col_year2 = st.columns(2)
            
            with col_year1:
                # Tipo × Año (Barras Apiladas)
                df_tipo_year = df.groupby(["Year", "Tipo_Contratacion"]).size().reset_index(name="Cantidad")
                fig_year1 = px.bar(
                    df_tipo_year,
                    x="Year",
                    y="Cantidad",
                    color="Tipo_Contratacion",
                    barmode="stack",
                    title="<b>Distribución de Tipos por Año</b>"
                )
                st.plotly_chart(fig_year1, use_container_width=True)
            
            with col_year2:
                # Evolución de montos por año
                df_monto_year = df.groupby("Year")["Monto"].sum().reset_index()
                fig_year2 = px.line(
                    df_monto_year,
                    x="Year",
                    y="Monto",
                    markers=True,
                    title="<b>Evolución del Monto Total por Año</b>"
                )
                st.plotly_chart(fig_year2, use_container_width=True)

            # Heatmap Año × Mes
            st.subheader("Mapa de Calor: Actividad por Año y Mes")
            df_heatmap = df.groupby(["Year", "Month"]).size().reset_index(name='Cantidad')
            pivot_heatmap = df_heatmap.pivot(index="Year", columns="Month", values="Cantidad").fillna(0)
            
            fig_heatmap = px.imshow(
                pivot_heatmap,
                labels=dict(x="Mes", y="Año", color="Contratos"),
                color_continuous_scale="Viridis",
                aspect="auto",
                title="<b>Actividad de Contratación por Año y Mes</b>"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

            # Descripción interpretativa
            st.subheader("Descripción Interpretativa de Resultados")
            
            # Calcular métricas para el análisis
            if len(df_kpis_year) > 1:
                year_max = df_kpis_year.loc[df_kpis_year['Monto_Total'].idxmax(), 'Year']
                year_min = df_kpis_year.loc[df_kpis_year['Monto_Total'].idxmin(), 'Year']
                crecimiento = ((df_kpis_year['Monto_Total'].iloc[-1] - df_kpis_year['Monto_Total'].iloc[0]) / df_kpis_year['Monto_Total'].iloc[0]) * 100
                
                st.markdown(f"""
                <div class="interpretation-box">
                <strong>Hallazgos Principales:</strong>
                - <strong>Tendencias:</strong> El año {year_max} registró el mayor monto total, mientras {year_min} el menor
                - <strong>Crecimiento:</strong> {'Crecimiento' if crecimiento > 0 else 'Decrecimiento'} del {abs(crecimiento):.1f}% en el período analizado
                - <strong>Variabilidad:</strong> Los mapas de calor muestran patrones estacionales recurrentes
                - <strong>Concentración:</strong> Ciertos tipos de contratación predominan consistentemente across años
                </div>
                """, unsafe_allow_html=True)

            # ================== 8. EXPORTACIÓN DE RESULTADOS ==================
            st.markdown('<div class="section-header">💾 8. Exportación de Resultados</div>', unsafe_allow_html=True)
            
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                # Exportar datos procesados
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar Datos Procesados (CSV)",
                    data=csv_data,
                    file_name=f"contrataciones_processed_{search_keyword}_{year_selected}.csv",
                    mime="text/csv"
                )
            
            with col_exp2:
                # Exportar resumen estadístico
                summary_data = df_kpis_year.to_csv(index=False)
                st.download_button(
                    label="📊 Descargar Resumen Estadístico",
                    data=summary_data,
                    file_name=f"resumen_estadistico_{search_keyword}_{year_selected}.csv",
                    mime="text/csv"
                )
            
            with col_exp3:
                # Exportar datos agrupados por tipo
                tipo_data = df.groupby("Tipo_Contratacion").agg({
                    "Monto": ["sum", "mean", "count"],
                    "Proveedor(s)": "nunique"
                }).round(2).to_csv()
                st.download_button(
                    label="📑 Datos por Tipo Contratación",
                    data=tipo_data,
                    file_name=f"datos_tipo_contratacion_{search_keyword}_{year_selected}.csv",
                    mime="text/csv"
                )

            # ================== 9. CONCLUSIONES ==================
            st.markdown('<div class="section-header">🎯 9. Conclusiones del Análisis</div>', unsafe_allow_html=True)
            
            col_conc1, col_conc2 = st.columns(2)
            
            with col_conc1:
                st.subheader("Principales Hallazgos")
                st.markdown("""
                - **Variables con mayor peso:** Tipo de contratación y temporalidad (mes/año)
                - **Tendencias identificadas:** Patrones estacionales recurrentes
                - **Distribución geográfica:** Concentración en ciertas provincias/entidades
                - **Comportamientos atípicos:** Picos específicos en meses particulares
                """)
            
            with col_conc2:
                st.subheader("Hipótesis para Estudios Futuros")
                st.markdown("""
                - **Análisis de causalidad:** Factores detrás de los picos estacionales
                - **Benchmarking:** Comparativa interprovincial e intertemporal
                - **Optimización:** Identificación de oportunidades de eficiencia
                - **Impacto:** Relación entre contrataciones y desarrollo regional
                """)

else:
    # Estado inicial - Pantalla de bienvenida
    st.markdown("""
    <div style='text-align: center; padding: 4rem 2rem; background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%); border-radius: 20px; color: white;'>
        <h1 style='color: white; font-size: 3rem; margin-bottom: 1rem;'>🏛️ Bienvenido</h1>
        <p style='font-size: 1.5rem; margin-bottom: 2rem; opacity: 0.9;'>
            Dashboard de Análisis de Contrataciones Públicas del Ecuador
        </p>
        <div style='display: inline-block; background: rgba(255,255,255,0.2); padding: 1rem 2rem; border-radius: 10px;'>
            <p style='margin: 0; font-size: 1.2rem;'>🚀 <strong>Para comenzar:</strong></p>
            <p style='margin: 0.5rem 0 0 0;'>1. Configura los filtros en la barra lateral</p>
            <p style='margin: 0;'>2. Haz clic en "Aplicar Filtros y Generar Dashboard"</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================== 10. INFORMACIÓN DE ENTREGABLE ==================
with st.sidebar:
    st.markdown("---")
    st.markdown("""
    <div style='background: #34495e; padding: 1rem; border-radius: 10px; color: white;'>
        <h4 style='color: white; margin: 0 0 1rem 0;'>📋 Entregable</h4>
        <p style='font-size: 0.8rem; margin: 0.2rem 0;'>• Notebook: guia_practica1_Nombres_Apellidos.ipynb</p>
        <p style='font-size: 0.8rem; margin: 0.2rem 0;'>• Código: guia_practica1_Nombres_Apellidos.py</p>
        <p style='font-size: 0.8rem; margin: 0.2rem 0;'>• App: Streamlit Cloud</p>
    </div>
    """, unsafe_allow_html=True)