import pandas as pd
import sqlitecloud
import streamlit as st
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="LOL Prediction",
    layout="wide",
    page_icon="https://www.rw-designer.com/icon-image/21516-256x256x32.png",
)

st.subheader("📊 Indicadores Gerais - LOL Prediction")

# String de conexão padronizada
CONNECTION_STRING = "sqlitecloud://cw1kibdpdk.g4.sqlite.cloud:8860/dados_lol?apikey=kGwXx2fOHa43yDXhBsdeyAGbJBQXK0ljXRDtBEbieFs"

def get_dados_hist():
    conn = sqlitecloud.connect(CONNECTION_STRING)
    df_sql = pd.read_sql_query("SELECT * FROM dados_partidas", conn)
    conn.close()
    
    # Ajusta o df
    df_sql.columns = ['Data', 'Time1', 'Time2', 'Win1', 'Win2', 'Winner', 'origem']
    df_sql['Data'] = pd.to_datetime(df_sql['Data'], dayfirst=True)

    # Tratamento de nomenclaturas
    subs = {
        'KRX': 'DRX',
        'OKSavingsBank Brion': 'Hanjin Brion'
    }
    df_sql['Time1'] = df_sql['Time1'].replace(subs)
    df_sql['Time2'] = df_sql['Time2'].replace(subs)

    return df_sql

# 1. Carregar os dados
@st.cache_data(ttl=600) 
def carregar_dados():
    conn = sqlitecloud.connect(CONNECTION_STRING)

    df_sql = pd.read_sql_query("SELECT * FROM base_pred", conn)
    df_status = pd.read_sql_query("SELECT * FROM status_jogo where status = 'Feito'", conn)

    df_sql = df_sql.merge(df_status, on=["data", "time_a", "time_b"], how="left")
    df_sql["status"] = df_sql["status"].fillna("Pendente")

    df_novo = pd.read_sql_query("SELECT * FROM palpites_hist", conn)
    conn.close()

    df_novo["data"] = pd.to_datetime(df_novo["data"], format="%d/%m/%Y")
    df_novo = df_novo.rename(columns={"data": "Data"})

    return df_sql, df_novo

# Alterado para agrupar também por Data e manter os valores como numéricos para o gráfico
def processa_performance_acumulada(df_hist, df_palpites, data_ini, data_fim):
    df_palpites = df_palpites.rename(columns={"time_a": "Time1", "time_b": "Time2", 'ganhador': 'ganhador_predito'})
    
    # Filtra as datas usando dt.date para corresponder aos objetos retornados pelo slider
    mask = (df_palpites['Data'].dt.date >= data_ini) & (df_palpites['Data'].dt.date <= data_fim)
    df_palpites = df_palpites[mask]
    
    df_final = df_palpites.merge(df_hist, on=['Data', 'Time1', 'Time2'], how='left')
    df_final['ganhador_real'] = np.where(df_final['Winner'] >= 0.5, df_final['Time1'], df_final['Time2'])

    df_final = df_final.dropna(subset=['Win1'])

    if df_final.empty:
        return pd.DataFrame(columns=['Data', 'liga', 'resultado'])

    # Cria a coluna 'resultado' (1 se acertou, 0 se errou)
    df_final['resultado'] = (df_final['ganhador_real'] == df_final['ganhador_predito']).astype(int)

    # 1. Agrupa por Data e Liga pegando a SOMA dos acertos e o TOTAL de jogos no dia
    df_performance = df_final.groupby(['Data', 'liga'])['resultado'].agg(
        acertos='sum', 
        total='count'
    ).reset_index()

    # 2. Ordena por liga e data para garantir que a acumulação ocorra na ordem cronológica
    df_performance = df_performance.sort_values(by=['liga', 'Data'])

    # 3. Calcula a soma acumulada de acertos e de total de jogos, por liga
    df_performance['acertos_acum'] = df_performance.groupby('liga')['acertos'].cumsum()
    df_performance['total_acum'] = df_performance.groupby('liga')['total'].cumsum()

    # 4. A performance (resultado) será o total de acertos acumulados dividido pelo total de jogos até o dia
    df_performance['resultado'] = df_performance['acertos_acum'] / df_performance['total_acum']

    df_performance['liga'] = df_performance['liga'].str.upper()

    # Mantém apenas as colunas originais esperadas para não quebrar o resto do seu código
    df_performance = df_performance[['Data', 'liga', 'resultado']]

    return df_performance


# Inicializa o estado dos dados na sessão do usuário
if "df_jogos" not in st.session_state or "df_novo" not in st.session_state:
    st.session_state.df_jogos, st.session_state.df_novo = carregar_dados()
    st.session_state.df_hist = get_dados_hist()

# Define limites de data independente do recarregamento do layout
min_data = st.session_state.df_novo['Data'].min().date()
max_data = st.session_state.df_novo['Data'].max().date()


# 2. Criando as Janelas (Abas)
tab1, tab2 = st.tabs(["🎮 Gerenciador de Apostas", "📈 Visualizador de Dados"])

# ==========================================
# JANELA 1: GERENCIADOR DE APOSTAS
# ==========================================
with tab1:
    st.sidebar.header("Filtros - Gerenciador")

    ligas_disponiveis = [liga.upper() for liga in st.session_state.df_jogos["liga"].unique().tolist()]
    liga_selecionada = st.sidebar.selectbox("Selecione a Liga", ["Todas"] + ligas_disponiveis)

    status_selecionado = st.sidebar.multiselect(
        "Status do Jogo",
        options=["Pendente", "Feito"],
        default=["Pendente", "Feito"],
    )

    df_filtrado = st.session_state.df_jogos.copy()

    if liga_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["liga"] == liga_selecionada.lower()]

    df_filtrado = df_filtrado[df_filtrado["status"].isin(status_selecionado)]

    st.write(f"Exibindo {len(df_filtrado)} jogos encontrados:")

    df_editado = st.data_editor(
        df_filtrado,
        column_config={
            "status": st.column_config.SelectboxColumn(
                "Sua Aposta",
                help="Marque se o jogo já foi feito ou está pendente",
                width="medium",
                options=["Pendente", "Feito"],
                required=True,
            )
        },
        disabled=[
            "data", "time_a", "time_b", "prob_0_cont", "prob_1_cont",
            "prob_0_parc", "prob_1_parc", "prob_0_compl", "prob_1_compl",
            "prob_0", "prob_1", "ganhador", "liga", "dt_atualizacao",
        ],
        hide_index=True,
        width="content",
    )

    if st.button("Salvar Alterações de Status"):
        st.session_state.df_jogos.update(df_editado)
        
        conn = sqlitecloud.connect(CONNECTION_STRING)
        df_status_2 = pd.read_sql_query("SELECT * FROM status_jogo", conn)

        df_status_2 = pd.concat([
            df_status_2,
            df_editado.query("status == 'Feito'")[["data", "time_a", "time_b", "status"]]
        ]).drop_duplicates(subset=["data", "time_a", "time_b"], keep="last")

        cursor = conn.cursor()
        cursor.execute("DELETE FROM status_jogo;")

        for index, row in df_status_2.iterrows():
            insert_sql = """
            INSERT INTO status_jogo (data, time_a, time_b, status)
            VALUES (?, ?, ?, ?);
            """
            values = (row["data"], row["time_a"], row["time_b"], row["status"])
            cursor.execute(insert_sql, values)

        conn.commit()
        conn.close()
        st.success("Status dos jogos atualizado com sucesso!")
        
        carregar_dados.clear() 

# ==========================================
# JANELA 2: GRÁFICO DE PERFORMANCE
# ==========================================
with tab2:
    st.markdown("### 📈 Histórico de Precisão por Liga")

    datas_selecionadas = st.slider(
        "Selecione o intervalo de datas:",
        min_value=min_data,
        max_value=max_data,
        value=(min_data, max_data),
        key="intervalo_datas"
    )

    # Processa os dados reativamente baseando-se no slider
    df_performance_atual = processa_performance_acumulada(
        st.session_state.df_hist, 
        st.session_state.df_novo,
        data_ini=datas_selecionadas[0],
        data_fim=datas_selecionadas[1]
    )

    if not df_performance_atual.empty:
        # Prepara a tabela para o gráfico de linhas: X = Data, Y = Resultado, Linhas = Liga
        df_grafico = df_performance_atual.pivot(index="Data", columns="liga", values="resultado")
        
        # 1. Cria um intervalo contínuo de datas, do primeiro ao último dia do gráfico
        data_inicial_grafico = df_grafico.index.min()
        data_final_grafico = df_grafico.index.max()
        dias_completos = pd.date_range(start=data_inicial_grafico, end=data_final_grafico)
        
        # 2. Reindexa o DataFrame para ter todos os dias. 
        # O método ffill() (forward fill) carrega o último valor conhecido para os dias vazios.
        df_grafico = df_grafico.reindex(dias_completos).ffill()
        
        # Multiplica por 100 para visualizar a performance em base percentual (ex: 85%)
        df_grafico = df_grafico * 100
        
        # Exibe o gráfico 
        st.line_chart(
            df_grafico, 
            y_label="Precisão Média (%)",
            x_label="Data"
        )
    else:
        st.warning("Sem dados suficientes para gerar o gráfico neste período.")
