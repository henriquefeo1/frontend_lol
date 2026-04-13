import gradio as gr
import pandas as pd
import sqlitecloud

pd.options.mode.chained_assignment = None

def get_projecoes(liga):

    if liga == "LEC":
        liga = "lec"
    elif liga == "LCK":
        liga = 'lck'

    connection_string = "sqlitecloud://cw1kibdpdk.g4.sqlite.cloud:8860/dados_lol?apikey=kGwXx2fOHa43yDXhBsdeyAGbJBQXK0ljXRDtBEbieFs"

    conn = sqlitecloud.connect(connection_string)
    cursor = conn.cursor()

    df_sql = pd.read_sql_query(f"SELECT * FROM base_pred where liga = '{liga}'", conn)

    return df_sql


with gr.Blocks(title="Data LOL Prediction") as demo:
    
    # --- Seção do Dashboard (Inicia oculta) ---
    with gr.Column() as main_layout:
        gr.Markdown("# 📊 Indicadores Gerais")
        
        with gr.Row():
            liga = gr.Dropdown(label="Selecione a liga", choices=["LCK", "LEC"])
            btn_processa = gr.Button("🚀 Prediction")

        with gr.Row():
            df_final = gr.DataFrame(label="Base Consolidada")

    btn_processa.click(
        fn=get_projecoes,
        inputs=[liga],
        outputs=[df_final]
    )

demo.launch()
