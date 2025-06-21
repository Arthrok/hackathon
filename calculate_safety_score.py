#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para calcular score de segurança baseado nas classificações de percepção urbana.

O score é calculado usando média ponderada com foco em segurança:
- safety: 0.40 (peso alto)
- beautiful: 0.15
- lively: 0.15
- wealthy: 0.05
- boring: -0.10 (peso negativo)
- depressing: -0.15 (peso negativo)

O resultado final é normalizado para escala 0-10.
"""

import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, Column, MetaData, String, Float, text
from sqlalchemy.dialects.postgresql import insert

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do banco de dados
db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@" \
         f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

print(f"Conectando ao banco: {db_url}")
engine = create_engine(db_url)
metadata = MetaData()

# Definir a tabela score
score_table = Table(
    "score", metadata,
    Column("img_path", String, primary_key=True),
    Column("safety_total_score", Float),
    schema="public"
)

# Pesos para o cálculo da média ponderada
WEIGHTS = {
    'safety': 0.40,
    'beautiful': 0.15,
    'lively': 0.15,
    'wealthy': 0.05,
    'boring': -0.10,    # Peso negativo
    'depressing': -0.15  # Peso negativo
}

def create_score_table():
    """Criar a tabela score se ela não existir"""
    try:
        metadata.create_all(engine)
        print("✅ Tabela 'score' criada/verificada com sucesso")
    except Exception as e:
        print(f"❌ Erro ao criar tabela 'score': {e}")
        return False
    return True

def load_classification_data():
    """Carregar dados da tabela classification"""
    try:
        query = """
        SELECT img_path, safety, lively, wealthy, beautiful, boring, depressing
        FROM public.classification
        WHERE safety IS NOT NULL 
          AND lively IS NOT NULL 
          AND wealthy IS NOT NULL 
          AND beautiful IS NOT NULL 
          AND boring IS NOT NULL 
          AND depressing IS NOT NULL
        """
        
        df = pd.read_sql(query, engine)
        print(f"📊 Carregados {len(df)} registros da tabela classification")
        return df
        
    except Exception as e:
        print(f"❌ Erro ao carregar dados da tabela classification: {e}")
        return None

def calculate_safety_score(row):
    """
    Calcular o score de segurança para uma linha de dados
    
    Args:
        row: pandas Series com as colunas de percepção
        
    Returns:
        float: Score normalizado entre 0 e 10
    """
    # Calcular média ponderada bruta
    nota_raw = (
        row['safety'] * WEIGHTS['safety'] +
        row['beautiful'] * WEIGHTS['beautiful'] +
        row['lively'] * WEIGHTS['lively'] +
        row['wealthy'] * WEIGHTS['wealthy'] +
        row['boring'] * WEIGHTS['boring'] +
        row['depressing'] * WEIGHTS['depressing']
    )
    
    # Valores teóricos mínimo e máximo
    peso_positivo = sum(w for w in WEIGHTS.values() if w > 0)  # 0.75
    peso_negativo = abs(sum(w for w in WEIGHTS.values() if w < 0))  # 0.25
    
    nota_min = (0 * peso_positivo) - (10 * peso_negativo)  # -2.5
    nota_max = (10 * peso_positivo) - (0 * peso_negativo)  # 7.5
    
    # Normalizar para escala 0-10
    nota_normalizada = 10 * (nota_raw - nota_min) / (nota_max - nota_min)
    
    # Garantir que está entre 0 e 10
    nota_normalizada = max(0, min(10, nota_normalizada))
    
    return round(nota_normalizada, 2)

def clean_img_path(img_path):
    """
    Remover a extensão .jpg do final do img_path
    
    Args:
        img_path: string com o caminho da imagem
        
    Returns:
        string: caminho sem a extensão .jpg
    """
    if img_path.endswith('.jpg'):
        return img_path[:-4]
    return img_path

def save_scores_to_db(scores_df):
    """
    Salvar os scores calculados na tabela score
    
    Args:
        scores_df: DataFrame com img_path e safety_total_score
    """
    try:
        saved_count = 0
        
        with engine.begin() as conn:
            for _, row in scores_df.iterrows():
                # Usar upsert (INSERT ... ON CONFLICT DO UPDATE)
                stmt = insert(score_table).values(
                    img_path=row['img_path'],
                    safety_total_score=row['safety_total_score']
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['img_path'],
                    set_={'safety_total_score': stmt.excluded.safety_total_score}
                )
                conn.execute(stmt)
                saved_count += 1
        
        print(f"✅ {saved_count} scores salvos na tabela 'score' com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar scores no banco: {e}")
        return False

def main():
    """Função principal do script"""
    print("🚀 Iniciando cálculo de safety scores...")
    
    # 1. Criar tabela score se necessário
    if not create_score_table():
        return
    
    # 2. Carregar dados da tabela classification
    df = load_classification_data()
    if df is None or len(df) == 0:
        print("❌ Nenhum dado encontrado na tabela classification")
        return
    
    print(f"📋 Dados carregados:")
    print(f"   - Total de registros: {len(df)}")
    print(f"   - Colunas: {list(df.columns)}")
    
    # 3. Calcular scores para cada imagem
    print("🔢 Calculando safety scores...")
    
    scores_list = []
    for idx, row in df.iterrows():
        # Calcular score
        safety_score = calculate_safety_score(row)
        
        # Limpar img_path (remover .jpg)
        clean_path = clean_img_path(row['img_path'])
        
        scores_list.append({
            'img_path': clean_path,
            'safety_total_score': safety_score
        })
        
        if (idx + 1) % 100 == 0:
            print(f"   Processados {idx + 1}/{len(df)} registros...")
    
    # 4. Criar DataFrame com os scores
    scores_df = pd.DataFrame(scores_list)
    
    print(f"📊 Estatísticas dos scores calculados:")
    print(f"   - Média: {scores_df['safety_total_score'].mean():.2f}")
    print(f"   - Mediana: {scores_df['safety_total_score'].median():.2f}")
    print(f"   - Mínimo: {scores_df['safety_total_score'].min():.2f}")
    print(f"   - Máximo: {scores_df['safety_total_score'].max():.2f}")
    
    # 5. Salvar no banco de dados
    print("💾 Salvando scores no banco de dados...")
    if save_scores_to_db(scores_df):
        print("🎉 Processo concluído com sucesso!")
        
        # Verificar resultados
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM public.score"))
                total_scores = result.scalar()
                print(f"✅ Total de scores na tabela: {total_scores}")
        except Exception as e:
            print(f"⚠️ Erro ao verificar resultados: {e}")
    else:
        print("❌ Erro ao salvar scores no banco")

if __name__ == "__main__":
    main()
