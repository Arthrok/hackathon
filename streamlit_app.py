import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import plotly.express as px
import plotly.graph_objects as go

# Configurar a página
st.set_page_config(
    page_title="Mapa de Análise de Risco Urbano",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do banco de dados
@st.cache_resource
def init_database():
    """Inicializa conexão com o banco de dados"""
    db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@" \
             f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
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
        
        # Limpar e validar dados
        df = df.dropna(subset=['latitude', 'longitude', 'safety_total_score'])
        
        # Converter para tipos numéricos e remover valores inválidos
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['safety_total_score'] = pd.to_numeric(df['safety_total_score'], errors='coerce')
        
        # Remover linhas com valores NaN após conversão
        df = df.dropna(subset=['latitude', 'longitude', 'safety_total_score'])
        
        # Validar ranges de coordenadas
        df = df[(df['latitude'].between(-90, 90)) & (df['longitude'].between(-180, 180))]
        
        # Garantir que safety_total_score seja positivo
        df = df[df['safety_total_score'] >= 0]
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def create_heatmap(df, zoom_level=10):
    """Cria o mapa de calor usando PyDeck"""
    if df.empty:
        return None
    
    # Validar dados antes de criar o mapa
    df_clean = df.copy()
    
    # Garantir que os dados são numéricos e finitos
    df_clean['latitude'] = pd.to_numeric(df_clean['latitude'], errors='coerce')
    df_clean['longitude'] = pd.to_numeric(df_clean['longitude'], errors='coerce')
    df_clean['safety_total_score'] = pd.to_numeric(df_clean['safety_total_score'], errors='coerce')
    
    # Remover valores NaN ou infinitos
    df_clean = df_clean.dropna(subset=['latitude', 'longitude', 'safety_total_score'])
    df_clean = df_clean[np.isfinite(df_clean['latitude']) & 
                        np.isfinite(df_clean['longitude']) & 
                        np.isfinite(df_clean['safety_total_score'])]
    
    if df_clean.empty:
        return None
    
    # Calcular centro do mapa
    center_lat = float(df_clean['latitude'].mean())
    center_lon = float(df_clean['longitude'].mean())
    
    # Converter DataFrame para lista de dicionários com tipos Python nativos
    data_list = []
    for _, row in df_clean.iterrows():
        data_list.append({
            'latitude': float(row['latitude']),
            'longitude': float(row['longitude']),
            'safety_total_score': float(row['safety_total_score']),
            'place_name': str(row['place_name']) if pd.notna(row['place_name']) else 'Local desconhecido',
            'place_id': str(row['place_id']) if pd.notna(row['place_id']) else ''
        })
    
    # Adicionar peso invertido para o heatmap (score baixo = maior risco = mais vermelho)
    for item in data_list:
        # Inverter o score para que valores baixos fiquem mais "quentes" no heatmap
        item['risk_weight'] = 10 - item['safety_total_score']
    
    # Configurar a camada de heatmap
    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=data_list,
        get_position=["longitude", "latitude"],
        get_weight="risk_weight",  # Usar peso invertido
        radius_pixels=100,
        intensity=1,
        threshold=0.03,
        color_range=[
            [0, 255, 0, 50],      # Verde (baixo risco - score alto)
            [255, 255, 0, 100],   # Amarelo
            [255, 165, 0, 150],   # Laranja
            [255, 0, 0, 200],     # Vermelho (alto risco)
            [139, 0, 0, 255]      # Vermelho escuro (maior risco - score baixo)
        ]
    )
    
    # Adicionar cores baseadas no risco para os pontos
    for item in data_list:
        score = item['safety_total_score']
        # Definir cor baseada no score (baixo = vermelho, alto = verde)
        if score <= 2:
            item['color'] = [139, 0, 0, 200]      # Vermelho escuro (maior risco)
        elif score <= 4:
            item['color'] = [255, 0, 0, 180]      # Vermelho
        elif score <= 6:
            item['color'] = [255, 165, 0, 160]    # Laranja
        elif score <= 8:
            item['color'] = [255, 255, 0, 140]    # Amarelo
        else:
            item['color'] = [0, 255, 0, 120]      # Verde (menor risco)
    
    # Camada de pontos para mostrar localizações específicas
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=data_list,
        get_position=["longitude", "latitude"],
        get_color="color",
        get_radius="risk_weight * 3",  # Usar peso de risco para tamanho
        radius_scale=6,
        radius_min_pixels=3,
        radius_max_pixels=30,
        pickable=True,
        auto_highlight=True
    )
    
    # Configurar visualização
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_level,
        pitch=45,
        bearing=0
    )
    
    # Criar deck
    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=[heatmap_layer, scatter_layer],
        tooltip={
            "html": "<b>Local:</b> {place_name}<br/>"
                   "<b>Score de Segurança:</b> {safety_total_score}<br/>"
                   "<b>Coordenadas:</b> ({latitude:.4f}, {longitude:.4f})",
            "style": {"color": "white", "backgroundColor": "rgba(0,0,0,0.8)"}
        }
    )
    
    return deck

def create_statistics_charts(df):
    """Cria gráficos estatísticos dos dados"""
    if df.empty:
        return None, None
    
    # Histograma de scores
    fig_hist = px.histogram(
        df, 
        x='safety_total_score',
        nbins=20,
        title='Distribuição dos Scores de Segurança',
        labels={'safety_total_score': 'Score de Segurança', 'count': 'Quantidade'},
        color_discrete_sequence=['#2E8B57']
    )
    fig_hist.update_layout(showlegend=False)
    
    # Top 10 locais de maior risco (scores mais baixos)
    top_risk = df.nsmallest(10, 'safety_total_score')
    fig_bar = px.bar(
        top_risk,
        x='safety_total_score',
        y='place_name',
        orientation='h',
        title='Top 10 Áreas de Maior Risco',
        labels={'safety_total_score': 'Score de Segurança', 'place_name': 'Local'},
        color='safety_total_score',
        color_continuous_scale='Reds'
    )
    fig_bar.update_layout(height=400)
    
    return fig_hist, fig_bar

def main():
    """Função principal da aplicação"""
    
    # Título da aplicação
    st.title("Análise de Áreas de Risco Urbano")
    st.markdown("### Identificação de Locais com Potencial de Risco com Base em Análise Visual")
    st.markdown("---")
    
    # Sidebar para controles
    st.sidebar.header("Controles")
    
    # Carregar dados
    with st.spinner("Carregando dados do banco de dados..."):
        df = load_safety_data()
    
    if df.empty:
        st.error("Nenhum dado encontrado. Verifique se as tabelas 'urban_images' e 'score' existem e contêm dados.")
        st.stop()
    
    # Informações sobre os dados
    st.sidebar.markdown("### Informações dos Dados")
    st.sidebar.metric("Total de Locais", len(df))
    
    if len(df) > 0:
        st.sidebar.metric("Score Máximo", f"{df['safety_total_score'].max():.2f}")
        st.sidebar.metric("Score Médio", f"{df['safety_total_score'].mean():.2f}")
        st.sidebar.metric("Score Mínimo", f"{df['safety_total_score'].min():.2f}")
    else:
        st.sidebar.metric("Score Máximo", "N/A")
        st.sidebar.metric("Score Médio", "N/A")
        st.sidebar.metric("Score Mínimo", "N/A")
    
    # Controles do mapa
    st.sidebar.markdown("### Controles do Mapa")
    zoom_level = st.sidebar.slider("Nível de Zoom", 8, 15, 10)
    
    # Filtro por score
    if len(df) > 0:
        show_risk_only = st.sidebar.checkbox("Mostrar apenas áreas de risco (score < 5)", value=False)
        
        if show_risk_only:
            df_filtered = df[df['safety_total_score'] < 5.0]
        else:
            max_score = st.sidebar.slider(
                "Mostrar áreas com score até:", 
                float(df['safety_total_score'].min()), 
                float(df['safety_total_score'].max()), 
                float(df['safety_total_score'].max())
            )
            df_filtered = df[df['safety_total_score'] <= max_score]
    else:
        max_score = 10.0
        df_filtered = df
    
    # Layout principal
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Mapa de Áreas de Risco")
        st.markdown("""
        **Interpretação das cores:**
        - **Verde**: Áreas de baixo risco (scores altos de segurança)
        - **Amarelo**: Áreas de risco moderado
        - **Laranja**: Áreas de alto risco
        - **Vermelho**: Áreas de risco elevado
        - **Vermelho escuro**: Áreas de maior risco (scores baixos de segurança)
        
        *Quanto mais vermelha a área, maior o risco identificado.*
        """)
        
        # Criar e exibir mapa
        if len(df_filtered) > 0:
            try:
                deck = create_heatmap(df_filtered, zoom_level)
                if deck:
                    st.pydeck_chart(deck)
                else:
                    st.warning("Não foi possível criar o mapa com os dados filtrados.")
            except Exception as e:
                st.error(f"Erro ao criar o mapa: {str(e)}")
                st.info("Tentando exibir dados em formato de tabela...")
        else:
            st.warning("Nenhum dado disponível para exibir no mapa com os filtros aplicados.")
    
    with col2:
        st.subheader("Áreas de Maior Risco")
        if len(df_filtered) > 0:
            top_5_risk = df_filtered.nsmallest(5, 'safety_total_score')[['place_name', 'safety_total_score']]
            for idx, row in top_5_risk.iterrows():
                place_name = str(row['place_name']) if pd.notna(row['place_name']) else 'Local desconhecido'
                display_name = place_name[:20] + "..." if len(place_name) > 20 else place_name
                st.metric(
                    label=display_name,
                    value=f"{row['safety_total_score']:.2f}"
                )
        else:
            st.info("Nenhum dado disponível")
    
    # Seção de estatísticas
    st.markdown("---")
    st.subheader("Análise Estatística")
    
    if len(df_filtered) > 0:
        # Criar gráficos
        fig_hist, fig_bar = create_statistics_charts(df_filtered)
        
        if fig_hist and fig_bar:
            col3, col4 = st.columns(2)
            
            with col3:
                st.plotly_chart(fig_hist, use_container_width=True)
            
            with col4:
                st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Nenhum dado disponível para análise estatística com os filtros aplicados.")
    
    # Tabela de dados
    st.markdown("---")
    st.subheader("Dados Detalhados")
    
    if len(df_filtered) > 0:
        # Ordenar por score
        df_display = df_filtered.sort_values('safety_total_score', ascending=False)
        df_display = df_display.rename(columns={
            'place_name': 'Local',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'safety_total_score': 'Score de Segurança'
        })
        
        st.dataframe(
            df_display[['Local', 'Score de Segurança', 'Latitude', 'Longitude']],
            use_container_width=True
        )
    else:
        st.info("Nenhum dado disponível para exibir na tabela com os filtros aplicados.")
    
    # Informações técnicas
    with st.expander("Informações Técnicas"):
        st.markdown("""
        ### Como funciona o Mapa de Análise de Risco
        
        1. **Fonte dos Dados**: Os dados são obtidos através de um JOIN entre as tabelas `urban_images` e `score`.
        2. **Score de Segurança**: Valores mais baixos indicam áreas de maior risco potencial.
        3. **Visualização**: O mapa de calor usa cores vermelhas para destacar áreas de maior risco (scores baixos).
        4. **Interpretação**: Áreas vermelhas requerem mais atenção, áreas verdes são consideradas de menor risco.
        5. **Interatividade**: Passe o mouse sobre os pontos para ver detalhes específicos.
        
        ### Tecnologias Utilizadas
        - **Streamlit**: Interface web
        - **PyDeck**: Renderização do mapa 3D
        - **PostgreSQL**: Banco de dados
        - **Plotly**: Gráficos estatísticos
        """)

if __name__ == "__main__":
    main()
