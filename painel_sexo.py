
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from etl_sexo import ARQUIVO_LIMPO, executar, limpar
from medidas_sexo import panorama, resumo_estatistico

st.set_page_config(page_title="Caderno 03 | População por sexo", layout="wide")

FUNDO = "#F6F1E6"
TINTA = "#262626"
LARANJA = "#C65D33"
AZUL = "#4B6073"

st.markdown("""
<style>
.stApp {background: #F6F1E6; color: #262626;}
[data-testid="stSidebar"] {background: #E9E1D3; border-right: 2px solid #262626;}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label {color: #262626;}
h1, h2, h3 {font-family: Georgia, 'Times New Roman', serif !important; color: #262626 !important;}
h1 {letter-spacing: -1.8px; font-weight: 600 !important;}
[data-testid="stMetric"] {border-top: 3px solid #262626; padding-top: 11px;}
[data-testid="stMetricLabel"] {font-size: 12px; letter-spacing: 1px; text-transform: uppercase;}
[data-testid="stMetricValue"] {font-family: Georgia, serif;}
[data-baseweb="tab-list"] {border-bottom: 2px solid #262626; gap: 18px;}
[data-baseweb="tab"] {font-weight: 650;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def formato_inteiro(numero):
    return f"{int(numero):,}".replace(",", ".")


def formato_percentual(numero):
    return f"{numero:.2f}".replace(".", ",") + "%"


def aparencia_grafico(figura, altura=480):
    figura.update_layout(
        font=dict(family="Arial", color=TINTA, size=12),
        height=altura,
        margin=dict(l=8, r=12, t=22, b=35),
        paper_bgcolor=FUNDO,
        plot_bgcolor=FUNDO,
        legend=dict(orientation="h", y=1.1, x=0),
        hoverlabel=dict(bgcolor="#FFFFFF", font_color=TINTA),
    )
    figura.update_xaxes(showgrid=True, gridcolor="#D7CFC1", zeroline=False, title_text="Percentual da população (%)")
    figura.update_yaxes(showgrid=False, zeroline=False)
    return figura


def grafico_composicao(base):
    ordem = base.sort_values("Pct_Mulheres", ascending=False)
    grafico = go.Figure()
    for sexo, coluna, cor in (
        ("Mulheres", "Pct_Mulheres", LARANJA),
        ("Homens", "Pct_Homens", AZUL),
    ):
        grafico.add_trace(go.Bar(
            x=ordem[coluna], y=ordem["UF"], name=sexo,
            orientation="h", marker_color=cor,
            text=[formato_percentual(v) for v in ordem[coluna]],
            textposition="inside", textfont=dict(color="#FFFFFF", size=10),
            customdata=ordem["UF"],
            hovertemplate="%{customdata}<br>" + sexo + ": %{x:.2f}%<extra></extra>",
        ))
    grafico.update_layout(barmode="stack")
    grafico.update_yaxes(autorange="reversed", title_text="")
    grafico.update_xaxes(range=[0, 100], ticksuffix="%")
    return aparencia_grafico(grafico, max(320, len(base) * 30 + 110))


def grafico_boxplot(base):
    figura = go.Figure()
    for rotulo, coluna, cor in (
        ("Mulheres", "Pct_Mulheres", LARANJA),
        ("Homens", "Pct_Homens", AZUL),
    ):
        figura.add_trace(go.Box(
            y=base[coluna], name=rotulo,
            boxpoints="outliers", boxmean=False,
            marker_color=cor, line_color=cor,
            fillcolor="rgba(0,0,0,0)",
            hovertemplate=rotulo + ": %{y:.2f}%<extra></extra>",
        ))
    aparencia_grafico(figura, 420)
    figura.update_yaxes(title_text="Participação dentro de cada UF (%)", showgrid=True, gridcolor="#D7CFC1")
    figura.update_xaxes(title_text="", showgrid=False)
    return figura


@st.cache_data

def base_inicial():
    if not ARQUIVO_LIMPO.exists():
        return executar()
    return limpar(pd.read_csv(ARQUIVO_LIMPO, encoding="utf-8-sig"))


st.sidebar.markdown("### CENSO / 2022")
st.sidebar.caption("EDIÇÃO 03 — COMPOSIÇÃO DA POPULAÇÃO")
st.sidebar.divider()

arquivo = st.sidebar.file_uploader("Importar CSV ou XLSX", type=["csv", "xlsx"])
try:
    if arquivo is None:
        dados = base_inicial()
    elif arquivo.name.lower().endswith(".xlsx"):
        dados = limpar(pd.read_excel(arquivo), exigir_27=False)
    else:
        dados = limpar(pd.read_csv(arquivo, encoding="utf-8-sig"), exigir_27=False)
except Exception as erro:
    st.error(f"Não consegui carregar os dados: {erro}")
    st.info("Confira as colunas UF, Mulheres e Homens. Também é possível executar: python etl_sexo.py")
    st.stop()

regiao = st.sidebar.selectbox("Região", ["Brasil"] + sorted(dados["Regiao"].unique()))
regioes = dados if regiao == "Brasil" else dados.loc[dados["Regiao"] == regiao]
estado = st.sidebar.selectbox("Unidade federativa", ["Todas"] + sorted(regioes["UF"].unique()))
recorte = regioes if estado == "Todas" else regioes.loc[regioes["UF"] == estado]
if recorte.empty:
    st.warning("Não há dados disponíveis para este recorte.")
    st.stop()

medidas = panorama(recorte)
local = estado if estado != "Todas" else ("Brasil" if regiao == "Brasil" else "Região " + regiao)

st.markdown('<div style="font-family:monospace;letter-spacing:2px;font-size:12px;border-bottom:3px solid #262626;padding-bottom:12px">CADERNO DE DADOS &nbsp;/&nbsp; 03 &nbsp;&nbsp; • &nbsp;&nbsp; BRASIL 2022</div>', unsafe_allow_html=True)
st.title("Quem vive no Brasil?")
st.write("Uma leitura da população por sexo, de acordo com o Censo Demográfico 2022.")
st.caption(f"RECORTE ATUAL: {local}  ·  {recorte['UF'].nunique()} UF(s)  ·  ano 2022")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de habitantes", formato_inteiro(medidas["total"]))
col2.metric("Mulheres", formato_percentual(medidas["pct_mulheres"]))
col3.metric("Homens", formato_percentual(medidas["pct_homens"]))
col4.metric("Homens / 100 mulheres", f"{medidas['razao']:.1f}".replace(".", ","))

aba1, aba2, aba3 = st.tabs(["01  COMPOSIÇÃO", "02  ESTATÍSTICAS", "03  DADOS E FONTES"])

with aba1:
    st.subheader("Mulheres e homens em cada estado")
    st.caption("Cada barra soma 100% da população do estado. Os estados estão ordenados pela participação feminina.")
    st.plotly_chart(grafico_composicao(recorte), use_container_width=True)
    if estado != "Todas":
        st.caption("Neste recorte foi selecionado um único estado.")

with aba2:
    st.subheader("Como os percentuais variam entre estados?")
    n = recorte["UF"].nunique()
    st.caption(f"As medidas abaixo usam apenas as {n} UF(s) presentes no filtro atual.")
    if n == 1:
        st.info("Com apenas um estado, não há distribuição entre UFs para calcular quartis e identificar outliers.")
        st.dataframe(pd.DataFrame({
            "Grupo": ["Mulheres", "Homens"],
            "Participação": [formato_percentual(medidas["pct_mulheres"]), formato_percentual(medidas["pct_homens"])],
        }), hide_index=True, use_container_width=True)
    else:
        st.plotly_chart(grafico_boxplot(recorte), use_container_width=True)
        st.write("**Tabela de estatísticas descritivas**")
        tabela = resumo_estatistico(recorte)
        numero_cols = tabela.select_dtypes(include="number").columns
        tabela[numero_cols] = tabela[numero_cols].round(2)
        st.dataframe(tabela, hide_index=True, use_container_width=True)
        st.caption("IQR = Q3 - Q1. Outliers seguem a regra de 1,5 × IQR. Moda calculada com percentuais arredondados a duas casas decimais. Desvio padrão populacional.")

with aba3:
    st.subheader("Planilha usada")
    colunas = ["UF", "Regiao", "Mulheres", "Homens", "Total", "Pct_Mulheres", "Pct_Homens", "Razao_Sexo"]
    visivel = recorte[colunas].rename(columns={
        "Regiao": "Região", "Pct_Mulheres": "% mulheres", "Pct_Homens": "% homens",
        "Razao_Sexo": "Homens/100 mulheres",
    }).copy()
    st.dataframe(visivel.round(2), hide_index=True, use_container_width=True)
    st.download_button("Salvar dados filtrados em CSV", recorte.to_csv(index=False).encode("utf-8-sig"),
                       file_name="sexo_censo2022_filtrado.csv", mime="text/csv")
    st.subheader("Leitura dos resultados")
    if medidas["pct_mulheres"] > medidas["pct_homens"]:
        st.write(f"No recorte de {local}, as mulheres são maioria: {formato_percentual(medidas['pct_mulheres'])} da população.")
    else:
        st.write(f"No recorte de {local}, os homens representam {formato_percentual(medidas['pct_homens'])} da população.")
    st.write("Esses percentuais mostram a composição da população, não a densidade demográfica. "
             "Podem complementar análises sobre necessidades de saúde e políticas públicas, "
             "mas não comprovam, por si só, desigualdade de acesso a serviços.")
    st.caption("O quesito 'sexo' segue a classificação divulgada no Censo 2022; não é uma pesquisa sobre identidade de gênero.")
    st.markdown("**Fonte:** [IBGE — SIDRA, tabela 9514](https://sidra.ibge.gov.br/tabela/9514)  ·  "
                "[IBGE Educa — quantidade de homens e mulheres](https://educa.ibge.gov.br/jovens/conheca-o-brasil/populacao/18320-quantidade-de-homens-e-mulheres)")
