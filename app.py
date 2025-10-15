import streamlit as st
import pandas as pd
from collections import defaultdict
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpBinary, PulpSolverError
import matplotlib.pyplot as plt
from textwrap import wrap
from datetime import datetime

st.set_page_config(page_title="Grade Inteligente", layout="wide")

st.title("🎓 Grade Inteligente — Otimização de Disciplinas")

# ================================================================
# CARREGAR PLANILHA
# ================================================================
uploaded_file = st.file_uploader("📂 Envie sua planilha Excel (restricao_grade.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Planilha carregada com sucesso!")
else:
    st.info("Carregando planilha padrão (restricao_grade.xlsx)...")
    df = pd.read_excel("restricao_grade.xlsx")

# ================================================================
# FUNÇÃO PARA FILTRAR MATÉRIAS VIÁVEIS
# ================================================================
def filtrar_materias_viaveis(df):
    materias_cursadas = set(df[df["COMPLETOU"] == True]["TÍTULO"])
    creditos_cursados = df[df["COMPLETOU"] == True]["CRÉDITOS"].sum()
    viaveis = []

    for i, row in df.iterrows():
        if row["COMPLETOU"]:
            continue

        pre_requisitos = str(row["TÍTULO PRE REQUISITO"])
        if pre_requisitos in ["", "NaN", "nan", "None"]:
            viaveis.append(i)
            continue

        titulo = row["TÍTULO"]

        # Casos especiais
        if titulo == "Projeto Final I" and creditos_cursados >= 140:
            viaveis.append(i)
            continue
        if titulo == "Estágio Supervisionado" and creditos_cursados >= 120:
            viaveis.append(i)
            continue

        pre_req_lista = [p.strip() for p in pre_requisitos.split("/") if p.strip()]
        if all(pr in materias_cursadas for pr in pre_req_lista):
            viaveis.append(i)

    return df.loc[viaveis].reset_index(drop=True)

# ================================================================
# SELEÇÃO DE DISCIPLINAS CONCLUÍDAS
# ================================================================
st.header("✅ Selecione as disciplinas já concluídas:")

for periodo in sorted(df["Periodo"].unique()):
    st.subheader(f"📘 Período {periodo}")
    subset = df[df["Periodo"] == periodo]
    for i, row in subset.iterrows():
        df.at[i, "COMPLETOU"] = st.checkbox(row["TÍTULO"], value=row["COMPLETOU"], key=row["x"])

# ================================================================
# EXECUTAR OTIMIZAÇÃO COM PULP
# ================================================================
def executar_otimizacao(df):
    model = LpProblem("grade_otimizada", LpMaximize)
    xvars = {i: LpVariable(f"x_{i}", cat=LpBinary) for i in df.index}

    pesos = pd.to_numeric(df["funcao_obj"], errors="coerce").fillna(0.0)
    model += lpSum(pesos[i] * xvars[i] for i in df.index)

    model += lpSum(xvars[i] for i in df.index) >= 2
    model += lpSum(xvars[i] for i in df.index) <= 10

    def parse_slots(codigo):
        slots = []
        for token in str(codigo).replace(" ", "").split("-"):
            if not token:
                continue
            hora = "".join(ch for ch in token if ch.isdigit())
            dia = "".join(ch for ch in token if ch.isalpha()).lower()
            if hora and dia:
                slots.append((dia, int(hora)))
        return set(slots)

    idx_to_slots = {i: parse_slots(df.loc[i, "codigo de horario"]) for i in df.index}
    timeslot_to_courses = defaultdict(list)
    for i in df.index:
        for slot in idx_to_slots[i]:
            timeslot_to_courses[slot].append(i)

    for slot, courses in timeslot_to_courses.items():
        if len(courses) > 1:
            model += lpSum(xvars[i] for i in courses) <= 1

    model.solve()

    selecionadas = [i for i in df.index if xvars[i].value() > 0.5]
    return selecionadas, idx_to_slots

# ================================================================
# BOTÃO PRINCIPAL
# ================================================================
if st.button("🚀 Gerar Grade Otimizada"):
    start_time = datetime.now()
    try:
        selecionadas, idx_to_slots = executar_otimizacao(filtrar_materias_viaveis(df))
        tempo_exec = (datetime.now() - start_time).total_seconds()

        if not selecionadas:
            st.error("Nenhuma solução encontrada.")
        else:
            st.success(f"✅ Grade gerada em {tempo_exec:.2f} segundos!")

            resultado = df.loc[selecionadas, ["TÍTULO", "Periodo", "funcao_obj", "codigo de horario"]]
            resultado = resultado.sort_values(by="Periodo")

            st.dataframe(resultado)

            csv = resultado.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Baixar resultado (CSV)", data=csv, file_name="grade_otimizada.csv", mime="text/csv")

    except PulpSolverError:
        st.error("Erro ao resolver a otimização.")
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")

# ================================================================
# RODAPÉ
# ================================================================
st.markdown("---")
st.caption("Desenvolvido por Sávio • Projeto Grade Inteligente")
