"""
Comparação entre v1 e v2 do modelo
Roda ambas as versões e mostra as diferenças nos resultados
"""

import subprocess
import pandas as pd
from pathlib import Path

print("=" * 70)
print("  COMPARAÇÃO: v1 (Normais) vs v2 (Dirichlet + Temporal)")
print("=" * 70)

# Roda v1
print("\n[1/2] Executando v1...")
subprocess.run(["python", "src/simulation.py"], check=True)

# Roda v2
print("\n[2/2] Executando v2...")
subprocess.run(["python", "src/simulation_v2.py"], check=True)

# Compara resultados
print("\n" + "=" * 70)
print("  COMPARAÇÃO DE RESULTADOS")
print("=" * 70)

# Carrega dados
df1_1t = pd.read_csv("outputs/resultados_1turno.csv")
df2_1t = pd.read_csv("outputs/resultados_1turno_v2.csv")

df1_2t = pd.read_csv("outputs/resultados_2turno.csv")
df2_2t = pd.read_csv("outputs/resultados_2turno_v2.csv")

# Estatísticas 1º turno
print("\n📊 1º TURNO — Médias:")
print(f"{'Candidato':<20} {'v1':>10} {'v2':>10} {'Diferença':>12}")
print("-" * 54)
for col in ["Lula", "Flávio", "Outros", "Brancos"]:
    v1 = df1_1t[col].mean()
    v2 = df2_1t[col].mean()
    diff = v2 - v1
    print(f"{col:<20} {v1:>9.2f}% {v2:>9.2f}% {diff:>+10.2f}pp")

# Desvios padrão
print("\n📊 1º TURNO — Desvios padrão:")
print(f"{'Candidato':<20} {'v1':>10} {'v2':>10} {'Diferença':>12}")
print("-" * 54)
for col in ["Lula", "Flávio", "Outros", "Brancos"]:
    v1 = df1_1t[col].std()
    v2 = df2_1t[col].std()
    diff = v2 - v1
    print(f"{col:<20} {v1:>9.2f}% {v2:>9.2f}% {diff:>+10.2f}pp")

# Probabilidades de vitória 1T
prob_v1 = df1_1t["vencedor"].value_counts() / len(df1_1t) * 100
prob_v2 = df2_1t["vencedor"].value_counts() / len(df2_1t) * 100

print("\n🏆 Prob. vitória 1º turno:")
print(f"{'Candidato':<20} {'v1':>10} {'v2':>10} {'Diferença':>12}")
print("-" * 54)
for cand in prob_v1.index:
    v1 = prob_v1.get(cand, 0)
    v2 = prob_v2.get(cand, 0)
    diff = v2 - v1
    print(f"{cand:<20} {v1:>9.2f}% {v2:>9.2f}% {diff:>+10.2f}pp")

# 2º turno
print("\n📊 2º TURNO:")
print(f"{'Candidato':<20} {'v1':>10} {'v2':>10} {'Diferença':>12}")
print("-" * 54)
for col in ["Lula_2T", "Flávio_2T"]:
    cand = col.replace("_2T", "")
    v1 = df1_2t[col].mean()
    v2 = df2_2t[col].mean()
    diff = v2 - v1
    print(f"{cand:<20} {v1:>9.2f}% {v2:>9.2f}% {diff:>+10.2f}pp")

prob2_v1 = df1_2t["vencedor_2T"].value_counts() / len(df1_2t) * 100
prob2_v2 = df2_2t["vencedor_2T"].value_counts() / len(df2_2t) * 100

print("\n🏆 Prob. vitória 2º turno:")
print(f"{'Candidato':<20} {'v1':>10} {'v2':>10} {'Diferença':>12}")
print("-" * 54)
for cand in prob2_v1.index:
    v1 = prob2_v1.get(cand, 0)
    v2 = prob2_v2.get(cand, 0)
    diff = v2 - v1
    print(f"{cand:<20} {v1:>9.2f}% {v2:>9.2f}% {diff:>+10.2f}pp")

print("\n" + "=" * 70)
print("✅ Comparação concluída!")
print("\nGráficos salvos:")
print("  - outputs/simulacao_eleicoes_brasil_2026.png (v1)")
print("  - outputs/simulacao_eleicoes_brasil_2026_v2.png (v2)")
print("=" * 70)
