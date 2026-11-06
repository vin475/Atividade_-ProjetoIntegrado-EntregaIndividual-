
from pathlib import Path
import argparse

import pandas as pd
import requests

PASTA = Path(__file__).resolve().parent
ARQUIVO_BRUTO = PASTA / "base_original_sexo_2022.csv"
ARQUIVO_LIMPO = PASTA / "dados_sexo_2022.csv"


API_IBGE = (
    "https://apisidra.ibge.gov.br/values/t/9514/n3/all/v/93/p/2022/"
    "c2/all/c287/100362/c286/113635"
)

ESTADOS_POR_REGIAO = {
    "Norte": ["Acre", "Amapá", "Amazonas", "Pará", "Rondônia", "Roraima", "Tocantins"],
    "Nordeste": ["Alagoas", "Bahia", "Ceará", "Maranhão", "Paraíba", "Pernambuco", "Piauí", "Rio Grande do Norte", "Sergipe"],
    "Centro-Oeste": ["Distrito Federal", "Goiás", "Mato Grosso", "Mato Grosso do Sul"],
    "Sudeste": ["Espírito Santo", "Minas Gerais", "Rio de Janeiro", "São Paulo"],
    "Sul": ["Paraná", "Rio Grande do Sul", "Santa Catarina"],
}

REGIAO_DA_UF = {uf: regiao for regiao, ufs in ESTADOS_POR_REGIAO.items() for uf in ufs}
IBGE_UF_POR_CODIGO = dict(zip(
    ["12", "27", "16", "13", "29", "23", "53", "32", "52", "21", "51", "50", "31", "15",
     "25", "41", "26", "22", "33", "24", "43", "11", "14", "42", "35", "28", "17"],
    ["Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará", "Distrito Federal", "Espírito Santo",
     "Goiás", "Maranhão", "Mato Grosso", "Mato Grosso do Sul", "Minas Gerais", "Pará", "Paraíba",
     "Paraná", "Pernambuco", "Piauí", "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul",
     "Rondônia", "Roraima", "Santa Catarina", "São Paulo", "Sergipe", "Tocantins"]
))


def limpar(dados: pd.DataFrame, exigir_27: bool = True) -> pd.DataFrame:
    """Valida a base, cria a região e calcula porcentagens SEM arredondar."""
    obrigatorias = {"UF", "Mulheres", "Homens"}
    if not obrigatorias.issubset(dados.columns):
        faltam = ", ".join(sorted(obrigatorias - set(dados.columns)))
        raise ValueError(f"Faltam as colunas: {faltam}")

    tabela = dados[["UF", "Mulheres", "Homens"]].copy()
    tabela["UF"] = tabela["UF"].astype(str).str.strip()
    if tabela.empty or tabela["UF"].duplicated().any():
        raise ValueError("A tabela está vazia ou contém estados repetidos.")
    if not set(tabela["UF"]).issubset(REGIAO_DA_UF):
        raise ValueError("Há UFs desconhecidas na base.")

    for coluna in ["Mulheres", "Homens"]:
        tabela[coluna] = pd.to_numeric(tabela[coluna], errors="raise")
        if tabela[coluna].isna().any() or (tabela[coluna] < 0).any():
            raise ValueError(f"Contagens inválidas em: {coluna}.")
        if ((tabela[coluna] % 1) != 0).any():
            raise ValueError(f"{coluna} deve conter quantidade inteira de pessoas.")
        tabela[coluna] = tabela[coluna].astype("int64")

    if exigir_27 and set(tabela["UF"]) != set(REGIAO_DA_UF):
        raise ValueError("A base original deve conter as 27 unidades federativas.")

    tabela["Total"] = tabela["Mulheres"] + tabela["Homens"]
    if (tabela["Total"] <= 0).any():
        raise ValueError("O total de residentes precisa ser positivo.")
    tabela.insert(1, "Regiao", tabela["UF"].map(REGIAO_DA_UF))
    tabela["Pct_Mulheres"] = 100 * tabela["Mulheres"] / tabela["Total"]
    tabela["Pct_Homens"] = 100 * tabela["Homens"] / tabela["Total"]
    tabela["Razao_Sexo"] = 100 * tabela["Homens"] / tabela["Mulheres"].replace(0, float("nan"))
    return tabela.sort_values("UF").reset_index(drop=True)


def baixar_do_ibge() -> pd.DataFrame:
    """Atualiza a base bruta consultando a tabela 9514 do SIDRA/IBGE."""
    resposta = requests.get(API_IBGE, headers={"Accept": "application/json"}, timeout=70)
    resposta.raise_for_status()
    registros = resposta.json()
    if not isinstance(registros, list) or len(registros) < 2:
        raise ValueError("A API do IBGE não devolveu dados.")

    encontrados = {}
    for item in registros[1:]:
        uf = str(item.get("D1N", "")).strip()
        if uf not in REGIAO_DA_UF:
            uf = IBGE_UF_POR_CODIGO.get(str(item.get("D1C", "")), "")
        if not uf:
            continue
        sexo = next((str(v).strip() for k, v in item.items()
                     if k.startswith("D") and k.endswith("N")
                     and str(v).strip() in ("Homens", "Mulheres")), "")
        if not sexo:
            continue
        bruto = str(item.get("V", "")).strip()
        try:
            valor = int(bruto)
        except ValueError:
            continue
        if (uf, sexo) in encontrados:
            raise ValueError("Consulta ambígua: estado/sexo duplicado. Verifique a API.")
        encontrados[(uf, sexo)] = valor

    linhas = []
    for uf in REGIAO_DA_UF:
        if (uf, "Mulheres") in encontrados and (uf, "Homens") in encontrados:
            linhas.append({"UF": uf, "Mulheres": encontrados[(uf, "Mulheres")],
                           "Homens": encontrados[(uf, "Homens")]})
    bruto = pd.DataFrame(linhas, columns=["UF", "Mulheres", "Homens"])
    tratar = limpar(bruto)
    if tratar["Total"].sum() != 203080756:
        raise ValueError("O total não corresponde aos 203.080.756 habitantes do Censo 2022.")
    bruto.to_csv(ARQUIVO_BRUTO, index=False, encoding="utf-8-sig")
    return bruto


def executar(atualizar=False) -> pd.DataFrame:
    bruto = baixar_do_ibge() if atualizar else pd.read_csv(ARQUIVO_BRUTO, encoding="utf-8-sig")
    organizado = limpar(bruto)
    organizado.to_csv(ARQUIVO_LIMPO, index=False, encoding="utf-8-sig")
    return organizado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepara dados de sexo do Censo 2022")
    parser.add_argument("--atualizar", action="store_true", help="Tenta baixar novamente do IBGE")
    args = parser.parse_args()
    try:
        df = executar(args.atualizar)
        print("Arquivo gerado:", ARQUIVO_LIMPO.name)
        print(f"{len(df)} UFs | {df['Total'].sum():,} habitantes".replace(",", "."))
        print(f"Mulheres: {df['Mulheres'].sum():,} | Homens: {df['Homens'].sum():,}".replace(",", "."))
    except Exception as erro:
        print(f"Não foi possível preparar os dados: {erro}")
        raise SystemExit(1)
