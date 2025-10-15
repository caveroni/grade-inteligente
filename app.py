# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ======================================================
# CONFIGURAÇÃO DO GOOGLE SHEETS
# ======================================================
SHEET_NAME = "tabela_dados_limpos"
LOG_SHEET = "log_execucao"

scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(credentials)
sheet = client.open("planilha_tcc").worksheet(SHEET_NAME)

# ======================================================
# FUNÇÕES
# ======================================================
def carregar_dados():
    """Lê os dados da planilha Google Sheets."""
    return pd.DataFrame(sheet.get_all_records())

def registrar_log(tempo_exec, status):
    """Registra o tempo e status da execução no log."""
    log_sheet = client.open("planilha_tcc").worksheet(LOG_SHEET)
    log_sheet.append_row([str(datetime.now()), tempo_exec, status])

def executar_otimizacao(df):
    """Simula a otimização (substituir depois pelo seu modelo Gurobi real)."""
    pendentes = df[df["COMPLETOU"] == False]
    selecionadas = pendentes.head(5)  # Exemplo: pega 5 matérias pendentes
    return selecionadas

# ======================================================
# INTERFACE WEB
# ======================================================
st.set_page_config(page_title="Grade Inteligente", layout="wide")

st.title("🎓 Gerador de Grade Horária Inteligente")
st.write("Marque abaixo as disciplinas que você já concluiu:")

# Carregar dados do Sheets
df = carregar_dados()

# Exibir checkboxes organizados por período
for periodo in sorted(df["Periodo"].unique()):
    st.subheader(f"📘 Período {periodo}")
    subset = df[df["Periodo"] == periodo]
    for i, row in subset.iterrows():
        df.at[i, "COMPLETOU"] = st.checkbox(
            row["TÍTULO"],
            value=row["COMPLETOU"],
            key=row["x"]
        )

# Botão principal
if st.button("Gerar Grade Otimizada"):
    start_time = datetime.now()
    try:
        resultado = executar_otimizacao(df)
        tempo_total = (datetime.now() - start_time).total_seconds()
        registrar_log(tempo_total, "OK")

        st.success(f"Grade gerada em {tempo_total:.2f} segundos!")
        st.dataframe(resultado[["TÍTULO", "Periodo"]])

        # Download CSV
        st.download_button(
            "⬇️ Baixar resultado (CSV)",
            data=resultado.to_csv(index=False).encode("utf-8"),
            file_name="grade_otimizada.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Erro: {e}")
        registrar_log(0, f"ERRO: {e}")
