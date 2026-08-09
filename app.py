import streamlit as st
import pandas as pd
import sqlitecloud

# Configuração da página
st.set_page_config(page_title="LOL Prediction", layout="wide", page_icon= 'https://www.rw-designer.com/icon-image/21516-256x256x32.png')

st.subheader("📊 Indicadores Gerais - LOL Prediction")

# 1. Carregar os dados
def carregar_dados():

    connection_string = "sqlitecloud://cw1kibdpdk.g4.sqlite.cloud:8860/dados_lol?apikey=kGwXx2fOHa43yDXhBsdeyAGbJBQXK0ljXRDtBEbieFs"

    conn = sqlitecloud.connect(connection_string)

    df_sql = pd.read_sql_query(f"SELECT * FROM base_pred", conn)
    df_status = pd.read_sql_query(f"SELECT * FROM status_jogo where status = 'Feito'", conn)

    df_sql = df_sql.merge(df_status, on = ['data', 'time_a', 'time_b'], how='left')

    df_sql['status'] = df_sql['status'].fillna('Pendente')
    
    conn.commit()
    conn.close()    

    return df_sql

# Inicializa o estado dos dados na sessão do usuário
if 'df_jogos' not in st.session_state:
    st.session_state.df_jogos = carregar_dados()

# 2. Barra Lateral - Filtros
st.sidebar.header("Filtros")

# Filtro de Liga
ligas_disponiveis = [liga.upper() for liga in st.session_state.df_jogos['liga'].unique().tolist()]
liga_selecionada = st.sidebar.selectbox("Selecione a Liga", ["Todas"] + ligas_disponiveis)

# Filtro de Status (Feito / Pendente)
status_selecionado = st.sidebar.multiselect(
    "Status do Jogo", 
    options=["Pendente", "Feito"], 
    default=["Pendente", "Feito"]
)

# Aplicar filtros ao DataFrame de exibição
df_filtrado = st.session_state.df_jogos.copy()

if liga_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['liga'] == liga_selecionada.lower()]

df_filtrado = df_filtrado[df_filtrado['status'].isin(status_selecionado)]

# 3. Exibição e Edição da Tabela
st.write(f"Exibindo {len(df_filtrado)} jogos encontrados:")

# Usamos o st.data_editor para permitir marcar os jogos como Feito/Pendente
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
    disabled=["data", "time_a", "time_b", "prob_0_cont", "prob_1_cont", "prob_0_parc", "prob_1_parc", "prob_0_compl", "prob_1_compl", "prob_0", "prob_1", "ganhador", "liga", "dt_atualizacao"], # Trava as outras colunas para não serem alteradas sem querer
    hide_index=True,
    width='content'
)

# Salvar as alterações feitas de volta para o estado da sessão
if st.button("Salvar Alterações de Status"):
    print("Botão clicado inicio")
    st.session_state.df_jogos.update(df_editado)
    connection_string = "sqlitecloud://cw1kibdpdk.g4.sqlite.cloud:8860/dados_lol?apikey=kGwXx2fOHa43yDXhBsdeyAGbJBQXK0ljXRDtBEbieFs"
    conn = sqlitecloud.connect(connection_string)
    df_status_2 = pd.read_sql_query(f"SELECT * FROM status_jogo", conn)

    print("Leu base de status_jogos clicado inicio")

    # print(df_editado.query("status == 'Feito'")[['data', 'time_a', 'time_b']])

    df_status_2 = pd.concat((df_status_2, df_editado.query("status == 'Feito'")[['data', 'time_a', 'time_b', 'status']])).drop_duplicates()

    print("Deletando a base de status_jogos clicado inicio")
    sql = """
    Delete from status_jogo;
    """

    cursor = conn.cursor()
    cursor.execute(sql)
    print("Dados deletados com sucesso")

    for index, row in df_status_2.iterrows():
    # Forma segura de inserir dados, evitando injeção de SQL
        insert_sql = """
        INSERT INTO status_jogo (data, time_a, time_b, status)
        VALUES (?, ?, ?, ?);
        """
        values = (row['data'], row['time_a'], row['time_b'], 
                row['status'])
        cursor.execute(insert_sql, values)

    print("Linhas ajustadas com sucesso")

    conn.commit()
    conn.close()
    st.success("Status dos jogos atualizado com sucesso!")
