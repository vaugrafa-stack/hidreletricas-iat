"""Atualiza pendentes_geo.csv com resultados da revisão visual #22 em diante."""
import pandas as pd

df = pd.read_csv("data/processed/pendentes_geo.csv", encoding="utf-8-sig")

# Mapeamento: protocolo -> (status, grau_confianca, observacao)
updates = {
    # #22-23 CGH TAPERA (dois registros, mesmo protocolo)
    "22.330.096-0": ("Pendente de validação", "Baixo",
        "Rio Tapera / área agrícola identificada; sem estrutura de barragem visível na imagem; marcador em campo próximo a PR-277."),
    "25.766.890-8": ("Pendente de validação", "Baixo",
        "Mesma coordenada do protocolo 22.330.096-0 — área agrícola sem barramento identificável."),

    # #24 CGH VILA NOVA
    "25.457.893-2": ("Pendente de validação", "Baixo",
        "Área rural em Mangueirinha; sem curso d'água ou barramento identificável no entorno imediato da coordenada."),

    # #25 MGH SANTIN
    "25.933.279-6": ("Não identificado", "Baixo",
        "Coordenada aponta para Estação de Tratamento de Esgoto Sanepar (EET-01 UT Rio do Salto, Cascavel); sem estrutura de usina hidrelétrica identificável."),

    # #26 MGH SÃO JOÃO (Carambeí)
    "25.338.437-9": ("Pendente de validação", "Baixo",
        "Área próxima ao Rio São João em Carambeí; sem barramento identificável na imagem; possível coordenada imprecisa."),

    # #27 PCH RANCHO GRANDE
    "24.829.490-6": ("Pendente de validação", "Baixo",
        "Rio Chopim confirmado pelo GEP; marcador em área florestal às margens do rio; sem estrutura de barragem identificável."),

    # #28 PCH BEIRA RIO
    "24.781.257-1": ("Não identificado", "Baixo",
        "Coordenada aponta para operação de mineração/extração em Jaguariaíva; sem estrutura de barragem ou curso d'água relacionado à PCH identificável."),

    # #29 PCH CANTU 1
    "25.204.208-3": ("Pendente de validação", "Médio",
        "Rio Cantu confirmado pelo GEP; etiqueta de PCH visível nas proximidades; sem barramento claramente identificável no marcador exato."),

    # #30 PCH CANTU 2
    "22.478.640-9": ("Validado", "Alto",
        "Barramento e reservatório claramente visíveis no Rio Cantu; marcador sobre a estrutura da PCH."),

    # #31 PCH CONFLUÊNCIA
    "23.510.661-2": ("Validado", "Alto",
        "Barramento claramente visível cruzando o rio no ponto do marcador; Rio Marrecas/confluência confirmado."),

    # #32 PCH CÓRREGO FUNDO
    "24.763.816-4": ("Validado", "Médio",
        "Etiquetas GEP 'PCH Córrego Fundo' e 'Rio Pirapó' confirmadas; estrutura da PCH identificada próxima ao marcador."),

    # #33 PCH MACACOS
    "24.781.262-8": ("Validado", "Alto",
        "Etiqueta GEP 'PCH MACACOS' confirmada; barramento identificado no Rio Jaguariaíva; marcador sobre a estrutura."),

    # #34 PCH PARANHOS MONTANTE
    "24.195.497-8": ("Pendente de validação", "Baixo",
        "Rio Chopim confirmado; marcador em área de meandro/planície de inundação sem estrutura de barragem identificável na imagem."),

    # #35 PCH PAREDINHA
    "25.111.580-0": ("Pendente de validação", "Médio",
        "Rio Cachoeira confirmado; barramento identificado ~300m a montante do marcador; coordenada posicionada nas corredeiras a jusante da estrutura."),

    # #36 PCH SALTINHO
    "25.100.265-7": ("Validado", "Médio",
        "Rio Santana confirmado; estrutura na margem do rio identificada no ponto do marcador; corredeira visível consistente com o nome 'Saltinho'; provável barramento de pequena PCH."),

    # #39 UHE SALTO SANTIAGO
    "21.939.642-2": ("Validado", "Alto",
        "Etiqueta GEP 'Vertedouro - Usina Hidrelétrica Santiago' confirmada; barramento e vertedouros múltiplos claramente identificados no Rio Iguaçu; marcador levemente a jusante do eixo."),

    # #40 UHE TIBAGI MONTANTE
    "20.462.636-7": ("Validado", "Alto",
        "Etiqueta GEP 'Usina Hidrelétrica Rio Tibagi' confirmada; barramento e casa de força claramente identificados no Rio Tibagi; marcador levemente deslocado mas na área do empreendimento."),
}

# PCH SÃO JOÃO II — dois registros com mesmo protocolo; atualizar ambos
sao_joao_ii_result = ("Sem imagem suficiente", "Médio",
    "Rio São João confirmado; canteiro de obras de barramento claramente visível (imagem: jun/2023); coordenada no local da PCH; estrutura em construção.")

count = 0
for idx, row in df.iterrows():
    proto = str(row.get("protocolo", "")).strip()

    if proto in updates:
        status, grau, obs = updates[proto]
        df.at[idx, "status_georreferenciamento"] = status
        df.at[idx, "grau_confianca"] = grau
        df.at[idx, "observacao_geoespacial"] = obs
        count += 1

    elif proto == "25.245.107-2":  # PCH SÃO JOÃO II (duplicado)
        status, grau, obs = sao_joao_ii_result
        df.at[idx, "status_georreferenciamento"] = status
        df.at[idx, "grau_confianca"] = grau
        df.at[idx, "observacao_geoespacial"] = obs
        count += 1

df.to_csv("data/processed/pendentes_geo.csv", index=False, encoding="utf-8-sig")
print(f"{count} registros atualizados.")

# Resumo final
print("\n=== RESUMO FINAL ===")
print(df["status_georreferenciamento"].value_counts().to_string())
print("\n--- Grau de Confiança ---")
print(df["grau_confianca"].value_counts().to_string())
