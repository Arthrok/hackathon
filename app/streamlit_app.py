import sys
import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go

# Adicionar o diretório pai ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar a página
st.set_page_config(
    page_title="Mapa de Análise de Risco Urbano",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar variáveis de ambiente
load_dotenv()

@st.cache_resource
def init_database():
    """Inicializa conexão com o banco de dados"""
    db_url = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:"
        f"{os.getenv('POSTGRES_PASSWORD')}@"
        f"{os.getenv('POSTGRES_HOST')}:"
        f"{os.getenv('POSTGRES_PORT')}/"
        f"{os.getenv('POSTGRES_DB')}"
    )
    return create_engine(db_url)

@st.cache_data
def load_safety_data():
    """Carrega dados de segurança do banco de dados"""
    engine = init_database()
    query = """
    SELECT 
        ui.place_id,
        ui.place_name,
        ui.latitude,
        ui.longitude,
        s.safety_total_score
    FROM urban_images ui
    INNER JOIN score s ON ui.place_id = s.img_path
    WHERE ui.latitude IS NOT NULL 
      AND ui.longitude IS NOT NULL 
      AND s.safety_total_score IS NOT NULL
      AND ui.latitude != 'NaN' 
      AND ui.longitude != 'NaN'
      AND s.safety_total_score != 'NaN'
    ORDER BY s.safety_total_score DESC
    """
    try:
        with engine.begin() as conn:
            df = pd.read_sql(query, conn)
        # Limpeza e validação
        df = df.dropna(subset=['latitude','longitude','safety_total_score'])
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['safety_total_score'] = pd.to_numeric(df['safety_total_score'], errors='coerce')
        df = df.dropna(subset=['latitude','longitude','safety_total_score'])
        df = df[
            (df['latitude'].between(-90, 90)) &
            (df['longitude'].between(-180, 180)) &
            (df['safety_total_score'] >= 0)
        ]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def create_heatmap(df, zoom_level=10):
    """Cria o mapa de calor usando PyDeck"""
    if df.empty:
        return None

    df_clean = df.copy()
    df_clean['latitude'] = pd.to_numeric(df_clean['latitude'], errors='coerce')
    df_clean['longitude'] = pd.to_numeric(df_clean['longitude'], errors='coerce')
    df_clean['safety_total_score'] = pd.to_numeric(df_clean['safety_total_score'], errors='coerce')
    df_clean = df_clean.dropna(subset=['latitude','longitude','safety_total_score'])
    df_clean = df_clean[
        np.isfinite(df_clean['latitude']) &
        np.isfinite(df_clean['longitude']) &
        np.isfinite(df_clean['safety_total_score'])
    ]
    if df_clean.empty:
        return None

    # calcular centro
    center_lat = float(df_clean['latitude'].mean())
    center_lon = float(df_clean['longitude'].mean())

    # montar lista de dicionários, incluindo campos pré-formatados para tooltip
    data_list = []
    for _, row in df_clean.iterrows():
        lat = float(row['latitude'])
        lon = float(row['longitude'])
        score = float(row['safety_total_score'])
        data_list.append({
            'latitude': lat,
            'longitude': lon,
            'safety_total_score': score,
            'place_name': str(row['place_name']) if pd.notna(row['place_name']) else 'Local desconhecido',
            'place_id': str(row['place_id']) if pd.notna(row['place_id']) else '',
            # campos pré-formatados (ATENÇÃO: use estes no tooltip, não {latitude:.4f})
            'lat_formatted': f"{lat:.4f}",
            'lon_formatted': f"{lon:.4f}",
            'score_formatted': f"{score:.2f}"
        })

    # peso invertido para o heatmap
    for item in data_list:
        item['risk_weight'] = 10 - item['safety_total_score']

    # cor dos pontos
    for item in data_list:
        sc = item['safety_total_score']
        if sc <= 2:
            item['color'] = [139, 0, 0, 200]
        elif sc <= 4:
            item['color'] = [255, 0, 0, 180]
        elif sc <= 6:
            item['color'] = [255, 165, 0, 160]
        elif sc <= 8:
            item['color'] = [255, 255, 0, 140]
        else:
            item['color'] = [0, 255, 0, 120]

    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=data_list,
        get_position=["longitude","latitude"],
        get_weight="risk_weight",
        radius_pixels=100,
        intensity=1,
        threshold=0.03,
        color_range=[
            [0,255,0,50],
            [255,255,0,100],
            [255,165,0,150],
            [255,0,0,200],
            [139,0,0,255]
        ]
    )

    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=data_list,
        get_position=["longitude","latitude"],
        get_color="color",
        get_radius="risk_weight * 3",
        radius_scale=6,
        radius_min_pixels=3,
        radius_max_pixels=30,
        pickable=True,
        auto_highlight=True
    )

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_level,
        pitch=45,
        bearing=0
    )

    # Tooltip corrigido: usa apenas os campos formatados, sem specifiers dentro das chaves
    tooltip = {
        "html":
            "<b>Local:</b> {place_name}<br/>"
            "<b>Score de Segurança:</b> {score_formatted}<br/>"
            "<b>Coordenadas:</b> ({lat_formatted}, {lon_formatted})",
        "style": {"color":"white","backgroundColor":"rgba(0,0,0,0.8)"}
    }

    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=[heatmap_layer, scatter_layer],
        tooltip=tooltip
    )

    return deck

def create_statistics_charts(df):
    """Cria gráficos estatísticos dos dados"""
    if df.empty:
        return None, None

    fig_hist = px.histogram(
        df,
        x='safety_total_score',
        nbins=20,
        title='Distribuição dos Scores de Segurança',
        labels={'safety_total_score':'Score de Segurança','count':'Quantidade'},
        color_discrete_sequence=['#2E8B57']
    )
    fig_hist.update_layout(showlegend=False)

    top_risk = df.nsmallest(10,'safety_total_score')
    fig_bar = px.bar(
        top_risk,
        x='safety_total_score',
        y='place_name',
        orientation='h',
        title='Top 10 Áreas de Maior Risco',
        labels={'safety_total_score':'Score de Segurança','place_name':'Local'},
        color='safety_total_score',
        color_continuous_scale='Reds'
    )
    fig_bar.update_layout(height=400)
    return fig_hist, fig_bar

def main():
    """Função principal da aplicação"""
    st.title("Análise de Áreas de Risco Urbano")
    st.markdown("### Identificação de Locais com Potencial de Risco com Base em Análise Visual")
    st.markdown("---")

    st.sidebar.header("Controles")
    with st.spinner("Carregando dados do banco de dados..."):
        df = load_safety_data()
    if df.empty:
        st.error("Nenhum dado encontrado. Verifique se as tabelas existem.")
        st.stop()

    st.sidebar.markdown("### Informações dos Dados")
    st.sidebar.metric("Total de Locais", len(df))
    if len(df)>0:
        st.sidebar.metric("Score Máximo", f"{df['safety_total_score'].max():.2f}")
        st.sidebar.metric("Score Médio", f"{df['safety_total_score'].mean():.2f}")
        st.sidebar.metric("Score Mínimo", f"{df['safety_total_score'].min():.2f}")

    st.sidebar.markdown("### Controles do Mapa")
    zoom_level = st.sidebar.slider("Nível de Zoom",8,15,10)

    if len(df)>0:
        show_risk_only = st.sidebar.checkbox("Mostrar apenas áreas de risco (score < 5)", value=False)
        if show_risk_only:
            df_filtered = df[df['safety_total_score']<5.0]
        else:
            max_score = st.sidebar.slider(
                "Mostrar áreas com score até:",
                float(df['safety_total_score'].min()),
                float(df['safety_total_score'].max()),
                float(df['safety_total_score'].max())
            )
            df_filtered = df[df['safety_total_score']<=max_score]
    else:
        df_filtered = df

    col1, col2 = st.columns([3,1])
    with col1:
        st.subheader("Mapa de Áreas de Risco")
        if not df_filtered.empty:
            deck = create_heatmap(df_filtered, zoom_level)
            if deck:
                st.pydeck_chart(deck)
            else:
                st.warning("Não foi possível criar o mapa.")
        else:
            st.warning("Nenhum dado disponível para o mapa.")

    with col2:
        st.subheader("Áreas de Maior Risco")
        if not df_filtered.empty:
            top5 = df_filtered.nsmallest(5,'safety_total_score')[['place_name','safety_total_score']]
            for _, row in top5.iterrows():
                name = str(row['place_name'])
                st.metric(label=name[:20]+"...", value=f"{row['safety_total_score']:.2f}")

    st.markdown("---")
    st.subheader("Análise Estatística")
    if not df_filtered.empty:
        fig_hist, fig_bar = create_statistics_charts(df_filtered)
        if fig_hist and fig_bar:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(fig_hist, use_container_width=True)
            with c2:
                st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    st.subheader("Dados Detalhados")
    if not df_filtered.empty:
        df_display = df_filtered.rename(columns={
            'place_name':'Local','latitude':'Latitude',
            'longitude':'Longitude','safety_total_score':'Score de Segurança'
        })
        st.dataframe(df_display[['Local','Score de Segurança','Latitude','Longitude']], use_container_width=True)

    with st.expander("Informações Técnicas"):
        st.markdown("""
        **Como funciona o Mapa de Análise de Risco**
        1. Fonte: JOIN entre `urban_images` e `score`.
        2. Score: valores baixos = maior risco.
        3. Mapa: heatmap + scatter.
        4. Tooltip: lat/long com 4 casas, score com 2 casas.
        """)

if __name__ == "__main__":
    main()

