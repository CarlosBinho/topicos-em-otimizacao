# 🐟 Sistema de Apoio à Decisão para Piscicultura (SADP)

> **Projeto Final:** Tópicos de Otimização  
> **Curso:** Bacharelado em Sistemas de Informação (UFRPE)  
> **Status:** Concluído (3ª VA)

Este projeto é uma ferramenta desenvolvida em Python para auxiliar pequenos produtores de peixe no planejamento da produção. O sistema utiliza técnicas de **Pesquisa Operacional** para sugerir quais espécies cultivar e em qual quantidade, visando maximizar o lucro respeitando as restrições de dinheiro (capital de giro) e espaço (tanques).

## 📋 Funcionalidades

O sistema opera em dois modos distintos de análise:

1.  **📊 Ranking de Monocultivo (Heurística):**
    * Analisa cada espécie individualmente.
    * Identifica o **Gargalo de Produção**: Informa se o produtor está limitado por falta de dinheiro ou falta de tanque.
    * Calcula indicadores financeiros: Lucro Mensal, ROI (Retorno sobre Investimento), Payback e Ponto de Equilíbrio.

2.  **🎯 Otimização de Mix (Programação Linear):**
    * Utiliza o algoritmo **Simplex** (via biblioteca `PuLP`) para calcular a combinação matemática perfeita de espécies.
    * Respeita meta mínima de produção (em kg).
    * Maximiza o lucro utilizando cada centavo e metro cúbico disponível.

3.  **📂 Banco de Dados Dinâmico (Excel):**
    * Os dados das espécies (preço de ração, venda, conversão alimentar, etc.) são lidos de um arquivo Excel externo (`especies.xlsx`).
    * Permite que o usuário atualize os preços do mercado sem precisar alterar o código do programa.

## ⚠️ Limitações e Desafios do Modelo

Este software é um protótipo acadêmico. A aplicação prática deve considerar as seguintes restrições não cobertas pelo código:

* **Parâmetros da Água (pH e Temperatura):** O sistema ignora a qualidade da água. Espécies sensíveis ao frio ou pH ácido podem ser indicadas como "lucrativas" matematicamente, mas seriam inviáveis biologicamente em certas regiões.
* **Compatibilidade de Espécies:** O otimizador de Mix não possui uma matriz de compatibilidade. Ele pode sugerir criar predadores (ex: Pintado) com presas (ex: Lambari), resultando em canibalismo.
* **Volume Agregado dos Tanques:** O cálculo considera a soma total do volume de água. Ele não diferencia se a fazenda tem 10 tanques pequenos ou 1 grande, o que pode gerar sugestões inadequadas para peixes de grande porte que exigem área de nado.
* **"Sujeira Matemática":** O solver busca a otimização exata. Para aproveitar sobras mínimas de orçamento, ele pode sugerir quantidades irrelevantes (ex: "Criar 1 Lambari"), o que é operacionalmente inviável.

## 🛠️ Tecnologias e Instalação

**Linguagem:** Python 3.x  
**Bibliotecas:** `Tkinter`, `Pandas`, `OpenPyXL`, `PuLP`.

Para rodar, instale as dependências:
```bash
pip install pandas openpyxl pulp
