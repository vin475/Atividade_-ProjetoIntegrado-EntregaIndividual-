import numpy as np
import pandas as pd


def resumo_estatistico(ufs: pd.DataFrame) -> pd.DataFrame:

    saida = []
    for rotulo, campo in (("Mulheres", "Pct_Mulheres"), ("Homens", "Pct_Homens")):
        valores = ufs[campo].dropna().astype(float)
        if len(valores) < 2:
            continue

        q1 = float(valores.quantile(.25))
        mediana = float(valores.median())
        q3 = float(valores.quantile(.75))
        iqr = q3 - q1
        limite_inferior = q1 - 1.5 * iqr
        limite_superior = q3 + 1.5 * iqr

        arredondados = valores.round(2)
        contagem = arredondados.value_counts()
        mais_frequente = contagem.max()
        moda = "Sem moda"
        if mais_frequente > 1:
            candidatos = sorted(contagem[contagem == mais_frequente].index.tolist())
            moda = ", ".join(f"{n:.2f}%".replace(".", ",") for n in candidatos)

        extremos = ufs.loc[(ufs[campo] < limite_inferior) | (ufs[campo] > limite_superior), "UF"].tolist()
        saida.append({
            "Sexo": rotulo,
            "Média (%)": valores.mean(),
            "Mediana (%)": mediana,
            "Moda (2 casas)": moda,
            "Q1 (%)": q1,
            "Q2 (%)": mediana,
            "Q3 (%)": q3,
            "IQR (p.p.)": iqr,
            "Amplitude (p.p.)": valores.max() - valores.min(),
            "Desvio padrão (p.p.)": float(np.std(valores, ddof=0)),
            "Outliers": ", ".join(extremos) if extremos else "Nenhum",
        })
    return pd.DataFrame(saida)


def panorama(ufs: pd.DataFrame) -> dict:
    total_mulheres = int(ufs["Mulheres"].sum())
    total_homens = int(ufs["Homens"].sum())
    total = total_mulheres + total_homens
    return {
        "total": total,
        "mulheres": total_mulheres,
        "homens": total_homens,
        "pct_mulheres": total_mulheres / total * 100,
        "pct_homens": total_homens / total * 100,
        "razao": total_homens / total_mulheres * 100 if total_mulheres else float("nan"),
    }
