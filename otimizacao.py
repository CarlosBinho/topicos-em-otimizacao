import sys
import pandas as pd # Panda: Biblioteca padrão para ler Excel/CSV
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pulp # PuLP: A biblioteca matemática que faz a "mágica" da otimização (Simplex)

# ==============================================================================
# 1. PARÂMETROS TÉCNICOS (LEITURA DO EXCEL)
# ==============================================================================
def ler_tabela(caminho_arquivo:str): 
    """
    Função para ler a planilha 'especies.xlsx'.
    Isso permite que o produtor mude o preço da ração no Excel 
    sem precisar chamar o programador para mexer no código.
    """
    try:
        df = pd.read_excel(caminho_arquivo)

        # "Traduz" os nomes das colunas do Excel (que tem acento e espaço)
        # para nomes de variáveis simples que usamos no Python (sem acento)
        mapeamento_colunas = {
            'Espécie': 'nome',
            'Valor Mercado (R$/kg)': 'valor_mercado_kg',
            'Peso Final Ideal (kg)': 'peso_final_ideal_kg',
            'Peso Inicial (g)': 'peso_inicial_g',
            'Taxa de Mortalidade': 'taxa_mortalidade',
            'Densidade Máxima (kg/m³)': 'densidade_max_kg_m3',
            'Conversão Alimentar': 'conversao_alimentar',
            'Tempo Ciclo (meses)': 'tempo_ciclo_meses',
            'Custo Alevino (R$/un)': 'custo_alevino_un',
            'Custo Ração (R$/kg)': 'custo_racao_kg'
        }
        # Converte a tabela em uma lista de dicionários (mais rápido de processar)
        especies_db = df.rename(columns=mapeamento_colunas).to_dict('records')
        return especies_db
    except Exception as e:
        # Se der erro (arquivo não existe, etc), retorna lista vazia
        return []

# ==============================================================================
# 2. MODELO DA FAZENDA (ESTRUTURA DE DADOS)
# ==============================================================================
class SistemaProdutivo:
    """
    Essa classe representa a 'realidade' do produtor.
    Ela guarda quanto dinheiro (Capital) e quanta água (Tanques) ele tem disponível.
    """
    def __init__(self, capital, qtd_tanques, vol_tanque, custo_fixo, sistema_opcao):
        self.capital_giro = capital
        self.qtd_tanques = qtd_tanques
        self.vol_por_tanque = vol_tanque
        self.custo_fixo_mensal = custo_fixo
        
        # Limitação do Modelo: Considera o volume total somado.
        # Não diferencia se são 10 tanques de 1.000L ou 1 tanque de 10.000L.
        self.volume_total = self.qtd_tanques * self.vol_por_tanque
        
        # Fator de Correção Tecnológica:
        # Extensivo usa 10% da capacidade do tanque. Intensivo usa 100%.
        if sistema_opcao == 1:
            self.fator_sistema = 0.10
            self.nome_sistema = "EXTENSIVO"
        elif sistema_opcao == 2:
            self.fator_sistema = 0.40
            self.nome_sistema = "SEMI-INTENSIVO"
        else: # opcao == 3
            self.fator_sistema = 1.00
            self.nome_sistema = "INTENSIVO"

# ==============================================================================
# 3. CORE DE CÁLCULO (SIMULAÇÃO INDIVIDUAL)
# ==============================================================================
def simular_cenarios(sis, especies_db):
    """
    Testa cada espécie isoladamente (Monocultivo).
    Responde a pergunta: "E se eu colocar só Tilápia em tudo?"
    """
    resultados = []
    
    for esp in especies_db:
        # --- 1. Engenharia Reversa de Custos ---
        # Calcula quanto o peixe cresce e quanta ração ele come no total
        ganho_peso = esp['peso_final_ideal_kg'] - (esp['peso_inicial_g']/1000)
        consumo_racao_kg_por_peixe = ganho_peso * esp['conversao_alimentar']
        custo_alim_un = consumo_racao_kg_por_peixe * esp['custo_racao_kg']
        
        # Custo Variável Unitário: Quanto custa 1 peixe (Alevino + Comida)
        custo_var_unit = esp['custo_alevino_un'] + custo_alim_un
        # Custo Fixo Total do ciclo (Luz, funcionário x Meses)
        custo_fixo_ciclo = sis.custo_fixo_mensal * esp['tempo_ciclo_meses']
        
        # --- 2. TETO FÍSICO (Restrição de Espaço) ---
        # Quantos peixes cabem na água sem morrer por falta de oxigênio?
        densidade_real_aplicada = esp['densidade_max_kg_m3'] * sis.fator_sistema
        biomassa_max = sis.volume_total * densidade_real_aplicada
        max_fisico = int(biomassa_max / esp['peso_final_ideal_kg'])
        
        # --- 3. TETO FINANCEIRO (Restrição de Orçamento) ---
        # Quanto dinheiro sobra pros peixes depois de pagar a luz (custo fixo)?
        orcamento_operacional = sis.capital_giro - custo_fixo_ciclo
       
        if orcamento_operacional <= 0:
            resultados.append({'especie': esp['nome'], 'status': 'INVIÁVEL', 'motivo': 'Custo fixo excede capital.'})
            continue
            
        # Quantos peixes consigo comprar e alimentar com o dinheiro que sobrou?
        max_financeiro = int(orcamento_operacional / custo_var_unit)
        
        # --- 4. A DECISÃO (Lei do Mínimo) ---
        # Produzimos o menor valor entre o que CABE e o que podemos PAGAR.
        qtd_real = min(max_fisico, max_financeiro)
        
        if qtd_real <= 0:
            resultados.append({'especie': esp['nome'], 'status': 'INVIÁVEL', 'motivo': 'Capital insuficiente.'})
            continue

        # --- 5. Consolidação dos Resultados (Output) ---
        # Aplica a mortalidade para saber quantos chegam no final
        peixes_finais = int(qtd_real * (1 - esp['taxa_mortalidade']))
        biomassa_vendida_kg = peixes_finais * esp['peso_final_ideal_kg']
        
        investimento_alevinos = qtd_real * esp['custo_alevino_un']
        investimento_racao = (qtd_real * consumo_racao_kg_por_peixe * esp['custo_racao_kg'])
        custo_total_ciclo = investimento_alevinos + investimento_racao + custo_fixo_ciclo
        
        receita_bruta = biomassa_vendida_kg * esp['valor_mercado_kg']
        lucro_liquido = receita_bruta - custo_total_ciclo
        
        # Indicadores para tomada de decisão
        custo_producao_por_kg = custo_total_ciclo / biomassa_vendida_kg if biomassa_vendida_kg > 0 else 0
        ponto_equilibrio_kg = custo_total_ciclo / esp['valor_mercado_kg']
        roi = (lucro_liquido / custo_total_ciclo) * 100
        lucro_mensal = lucro_liquido / esp['tempo_ciclo_meses'] # Normaliza para comparar ciclos diferentes
        racao_total_ton = (qtd_real * consumo_racao_kg_por_peixe) / 1000
        
        # Cálculo do Payback
        if lucro_mensal > 0:
            payback_meses = custo_total_ciclo / lucro_mensal
        else:
            payback_meses = 0 

        ocupacao = (qtd_real / max_fisico) * 100
        
        # Define qual foi o limitador (Gargalo)
        gargalo = "FINANCEIRO" if max_financeiro < max_fisico else "FÍSICO"

        resultados.append({
            'especie': esp['nome'],
            'dados_tec': esp,
            'qtd_povoamento': qtd_real,
            'biomassa_kg': biomassa_vendida_kg,
            'custo_alevinos': investimento_alevinos,
            'custo_racao': investimento_racao,
            'custo_fixo': custo_fixo_ciclo,
            'custo_total': custo_total_ciclo,
            'custo_kg_produzido': custo_producao_por_kg,
            'receita': receita_bruta,
            'lucro_liquido': lucro_liquido,
            'lucro_mensal': lucro_mensal,
            'roi': roi,
            'payback_meses': payback_meses, 
            'racao_ton': racao_total_ton,
            'ocupacao': ocupacao,
            'gargalo': gargalo,
            'ponto_equilibrio': ponto_equilibrio_kg,
            'status': 'VIÁVEL'
        })

    # Ordena a lista: Quem dá mais lucro mensal aparece primeiro
    return sorted([r for r in resultados if r['status']=='VIÁVEL'], key=lambda x: x['lucro_mensal'], reverse=True)

# ==============================================================================
# 3.1 CORE DE OTIMIZAÇÃO (MIX + META MÍNIMA)
# ==============================================================================
def otimizar_mix_ideal(sis, especies_db, meta_minima_kg=0):
    """
    Usa Programação Linear (Simplex via PuLP) para achar a mistura perfeita de peixes.
    Diferente da simulação acima, aqui o algoritmo tenta combinar espécies
    para usar cada centavo e cada metro cúbico disponível.
    """
    model_data = []
    orcamento_operacional = sis.capital_giro
    
    # Prepara os dados para o formato que o Solver entende
    for esp in especies_db:
        # Recalcula custos variáveis (igual à função anterior)
        ganho_peso = esp['peso_final_ideal_kg'] - (esp['peso_inicial_g']/1000)
        consumo_racao = ganho_peso * esp['conversao_alimentar']
        custo_alim_un = consumo_racao * esp['custo_racao_kg']
        custo_var_unit = esp['custo_alevino_un'] + custo_alim_un
        
        # Calcula limites físicos
        densidade_real = esp['densidade_max_kg_m3'] * sis.fator_sistema
        biomassa_max = sis.volume_total * densidade_real
        max_fisico = int(biomassa_max / esp['peso_final_ideal_kg'])
        
        # Estima Lucro Unitário (Margem de Contribuição)
        receita_un = esp['peso_final_ideal_kg'] * esp['valor_mercado_kg']
        custo_fixo_rateado = (sis.custo_fixo_mensal * esp['tempo_ciclo_meses']) / max_fisico if max_fisico > 0 else 0
        lucro_un = receita_un - custo_var_unit - custo_fixo_rateado
        
        if max_fisico > 0:
            model_data.append({
                'nome': esp['nome'],
                'lucro_un': lucro_un,
                'custo_un': custo_var_unit,
                'peso_final': esp['peso_final_ideal_kg'],
                'tempo_ciclo': esp['tempo_ciclo_meses'],
                'max_fisico': max_fisico
            })

    # --- INÍCIO DO MODELO MATEMÁTICO (PULP) ---
    prob = pulp.LpProblem("Mix_Aquicultura", pulp.LpMaximize)
    
    # Variáveis de Decisão: Quantidade de peixes de cada tipo (inteiro)
    peixes_vars = pulp.LpVariable.dicts("Qtd", [m['nome'] for m in model_data], lowBound=0, cat='Integer')

    # Função Objetivo: Maximizar o Lucro Total
    prob += pulp.lpSum([m['lucro_un'] * peixes_vars[m['nome']] for m in model_data])
    
    # Restrição 1: Não gastar mais do que o orçamento
    prob += pulp.lpSum([m['custo_un'] * peixes_vars[m['nome']] for m in model_data]) <= orcamento_operacional
    
    # Restrição 2: Não lotar o tanque acima de 100% da capacidade
    # (Soma das frações de ocupação de cada espécie)
    prob += pulp.lpSum([(peixes_vars[m['nome']] / m['max_fisico']) for m in model_data]) <= 1.0
    
    # Restrição 3: Atingir a Meta Mínima (se houver)
    if meta_minima_kg > 0:
        prob += pulp.lpSum([peixes_vars[m['nome']] * m['peso_final'] for m in model_data]) >= meta_minima_kg

    # Resolve o problema
    prob.solve(pulp.PULP_CBC_CMD(msg=0)) 

    # Recupera e processa os resultados
    status = pulp.LpStatus[prob.status]
    if status == 'Optimal':
        lucro_total = pulp.value(prob.objective)
        custo_total_mix = 0
        mix = []
        biomassa_total = 0
        max_ciclo = 0
        
        for m in model_data:
            qtd = peixes_vars[m['nome']].varValue
            if qtd > 0:
                peso = qtd * m['peso_final']
                custo = qtd * m['custo_un']
                custo_total_mix += custo
                biomassa_total += peso
                if m['tempo_ciclo'] > max_ciclo: max_ciclo = m['tempo_ciclo']
                
                mix.append({
                    'especie': m['nome'], 
                    'qtd': int(qtd), 
                    'peso': peso, 
                    'ciclo': m['tempo_ciclo'], 
                    'ocupacao': (qtd/m['max_fisico'])*100
                })
        
        # Ajuste de Payback para o Mix
        custo_total_mix_final = custo_total_mix + (sis.custo_fixo_mensal * max_ciclo)
        lucro_mensal_mix = lucro_total / max_ciclo if max_ciclo > 0 else 0
        payback_mix = custo_total_mix_final / lucro_mensal_mix if lucro_mensal_mix > 0 else 0
        
        return {
            'status': 'ÓTIMO', 
            'lucro_total': lucro_total, 
            'biomassa_total': biomassa_total, 
            'mix': mix,
            'payback_meses': payback_mix
        }
    elif status == 'Infeasible':
        return {'status': 'IMPOSSÍVEL', 'motivo': 'Recursos insuficientes.'}
    else:
        return {'status': 'ERRO', 'motivo': 'Erro numérico.'}


def fmt_moeda(valor): return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def fmt_num(valor): return f"{valor:,.0f}".replace(",", ".")

# ==============================================================================
# 5. INTERFACE GRÁFICA (TKINTER)
# ==============================================================================
class OtimizacaoApp:
    def __init__(self, root, db):
        self.root = root
        self.root.title("Sistema Integrado de Planejamento Aquícola")
        self.root.geometry("900x750")

        # Carrega o banco de dados na inicialização
        self.especies_db = ler_tabela(db)

        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.LabelFrame(main_frame, text="1. Parâmetros de Entrada", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="Capital Disponível (R$):").grid(row=0, column=0, sticky=tk.W)
        self.capital_entry = ttk.Entry(input_frame, width=20); self.capital_entry.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(input_frame, text="Quantidade de Tanques:").grid(row=1, column=0, sticky=tk.W)
        self.tanques_entry = ttk.Entry(input_frame, width=20); self.tanques_entry.grid(row=1, column=1, sticky=tk.W)

        ttk.Label(input_frame, text="Volume por Tanque (m³):").grid(row=2, column=0, sticky=tk.W)
        self.volume_entry = ttk.Entry(input_frame, width=20); self.volume_entry.grid(row=2, column=1, sticky=tk.W)

        ttk.Label(input_frame, text="Custo Fixo Mensal (R$):").grid(row=3, column=0, sticky=tk.W)
        self.custo_fixo_entry = ttk.Entry(input_frame, width=20); self.custo_fixo_entry.grid(row=3, column=1, sticky=tk.W)
        
        ttk.Label(input_frame, text="Meta Mínima de Produção (Kg):").grid(row=4, column=0, sticky=tk.W)
        self.meta_entry = ttk.Entry(input_frame, width=20); self.meta_entry.grid(row=4, column=1, sticky=tk.W)
        self.meta_entry.insert(0, "0")

        sistema_frame = ttk.LabelFrame(main_frame, text="2. Nível Tecnológico", padding="10")
        sistema_frame.pack(fill=tk.X, pady=5)
        self.sistema_var = tk.IntVar(value=3)
        ttk.Radiobutton(sistema_frame, text="EXTENSIVO", variable=self.sistema_var, value=1).pack(anchor=tk.W)
        ttk.Radiobutton(sistema_frame, text="SEMI-INTENSIVO", variable=self.sistema_var, value=2).pack(anchor=tk.W)
        ttk.Radiobutton(sistema_frame, text="INTENSIVO", variable=self.sistema_var, value=3).pack(anchor=tk.W)
        
        ttk.Button(main_frame, text="3. Processar Simulação Completa", command=self.run_simulation).pack(pady=10, fill=tk.X)

        results_frame = ttk.LabelFrame(main_frame, text="4. Relatório Detalhado + Estratégia", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.results_text = scrolledtext.ScrolledText(results_frame, width=90, height=20, state=tk.DISABLED)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Tags de estilo para o relatório ficar bonito e legível
        self.results_text.tag_config("title", font=("Helvetica", 11, "bold"), background="#f0f0f0")
        self.results_text.tag_config("header", font=("Helvetica", 10, "bold"))
        self.results_text.tag_config("highlight", foreground="blue", font=("Helvetica", 10, "bold"))
        self.results_text.tag_config("negative", foreground="red", font=("Helvetica", 10, "bold"))
        self.results_text.tag_config("normal", font=("Courier", 9))

    def run_simulation(self):
        try:
            # Pega os inputs da tela e converte (troca vírgula por ponto)
            capital = float(self.capital_entry.get().replace(',', '.'))
            qtd_tanques = int(self.tanques_entry.get())
            vol_tanque = float(self.volume_entry.get().replace(',', '.'))
            custo_fixo = float(self.custo_fixo_entry.get().replace(',', '.'))
            try: meta_kg = float(self.meta_entry.get().replace(',', '.'))
            except: meta_kg = 0.0
            
            # Instancia o "gêmeo digital" da fazenda
            sis = SistemaProdutivo(capital, qtd_tanques, vol_tanque, custo_fixo, self.sistema_var.get())
            # Roda a simulação heurística
            ranking = simular_cenarios(sis,self.especies_db)
            # Gera o texto na tela
            self.gerar_relatorio_gui(sis, ranking, meta_kg)

        except ValueError: messagebox.showerror("Erro", "Verifique os números digitados.")

    def gerar_relatorio_gui(self, sis, ranking, meta_kg):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)

        if not ranking:
            self.results_text.insert(tk.END, "NENHUM CENÁRIO VIÁVEL.\n", "negative")
            return

        # ======================================================================
        # PARTE 1: O RELATÓRIO "DIDÁTICO"
        # ======================================================================
        self.results_text.insert(tk.END, f"{'='*80}\n", "title")
        self.results_text.insert(tk.END, f"{' RANKING GERAL DE VIABILIDADE (MONOCULTIVO) ':^80}\n", "title")
        self.results_text.insert(tk.END, f"{'='*80}\n", "title")
        self.results_text.insert(tk.END, f"{'RK':<3} {'ESPÉCIE':<25} {'LUCRO MENSAL':<18} {'ROI':<10} {'INVESTIMENTO'}\n", "header")
        self.results_text.insert(tk.END, f"{'-'*80}\n", "normal")
        
        for i, cen in enumerate(ranking):
            tag = "highlight" if cen['lucro_mensal'] > 0 else "negative"
            self.results_text.insert(tk.END, f"{i+1:02d}. {cen['especie']:<25} {fmt_moeda(cen['lucro_mensal']):<18} {cen['roi']:>5.1f}%    {fmt_moeda(cen['custo_total'])}\n", "normal")
        self.results_text.insert(tk.END, "\n")

        for cen in ranking:
            esp = cen['dados_tec']
            if cen['lucro_mensal'] < 0:
                self.results_text.insert(tk.END, f"{'='*80}\n INVIÁVEL: {cen['especie']}\n{'='*80}\n", "title")
                self.results_text.insert(tk.END, f" Prejuízo Mensal: {fmt_moeda(abs(cen['lucro_mensal']))}\n\n", "negative")
                continue 
            
            self.results_text.insert(tk.END, f"{'='*80}\n", "title")
            self.results_text.insert(tk.END, f" ANÁLISE DETALHADA: {cen['especie'].upper()}\n", "title")
            self.results_text.insert(tk.END, f"{'='*80}\n", "title")

            self.results_text.insert(tk.END, f"\n1. RESUMO DE RESULTADOS\n{'-'*80}\n", "header")
            self.results_text.insert(tk.END, f"   • Lucro Líquido Total: {fmt_moeda(cen['lucro_liquido'])} ", "highlight")
            self.results_text.insert(tk.END, f"(Ciclo de {esp['tempo_ciclo_meses']} meses)\n", "highlight")
            self.results_text.insert(tk.END, f"   • Lucro Mensal (Méd):  {fmt_moeda(cen['lucro_mensal'])}\n", "normal")
            
            self.results_text.insert(tk.END, f"   • Payback (Retorno):   {cen['payback_meses']:.1f} meses (Tempo p/ recuperar 100% do capital via lucro)\n", "normal")
            
            self.results_text.insert(tk.END, f"   • ROI:                 {cen['roi']:.1f}%\n", "normal")
            self.results_text.insert(tk.END, f"   • Custo Prod.:         {fmt_moeda(cen['custo_kg_produzido'])}/kg (Venda: {fmt_moeda(esp['valor_mercado_kg'])})\n", "normal")

            self.results_text.insert(tk.END, f"\n2. ORÇAMENTO (DESTINAÇÃO DO CAPITAL)\n{'-'*80}\n", "header")
            self.results_text.insert(tk.END, f"   • Alevinos:            {fmt_num(cen['qtd_povoamento'])} un. -> {fmt_moeda(cen['custo_alevinos'])}\n", "normal")
            self.results_text.insert(tk.END, f"   • Ração:               {cen['racao_ton']:.2f} ton -> {fmt_moeda(cen['custo_racao'])}\n", "normal")
            self.results_text.insert(tk.END, f"   • Custo Fixo:          {fmt_moeda(cen['custo_fixo'])}\n", "normal")
            self.results_text.insert(tk.END, f"   ► TOTAL:               {fmt_moeda(cen['custo_total'])}\n", "highlight")
            if cen['custo_total'] < sis.capital_giro:
                self.results_text.insert(tk.END, f"     (Sobra de Caixa: {fmt_moeda(sis.capital_giro - cen['custo_total'])})\n", "normal")

            self.results_text.insert(tk.END, f"\n3. SEGURANÇA (PONTO DE EQUILÍBRIO)\n{'-'*80}\n", "header")
            self.results_text.insert(tk.END, f"   Precisa produzir {fmt_num(cen['ponto_equilibrio'])} kg para pagar contas.\n", "normal")
            self.results_text.insert(tk.END, f"   Projeção atual:  {fmt_num(cen['biomassa_kg'])} kg.\n", "highlight")

            self.results_text.insert(tk.END, f"\n4. DIAGNÓSTICO DE INFRAESTRUTURA\n{'-'*80}\n", "header")
            self.results_text.insert(tk.END, f"   • Ocupação Tanques: {cen['ocupacao']:.1f}%\n", "normal")
            msg_gargalo = "Falta Dinheiro (Tanques ociosos)" if cen['gargalo'] == 'FINANCEIRO' else "Falta Espaço (Dinheiro sobrando)"
            self.results_text.insert(tk.END, f"   • Gargalo Principal: {msg_gargalo}\n", "normal")
            self.results_text.insert(tk.END, "\n")

        # Chama a função de Otimização (Simplex)
        # Passamos a 'meta_kg' como argumento posicional (ela entra no meta_minima_kg da função)
        opt = otimizar_mix_ideal(sis, self.especies_db, meta_kg)
        
        self.results_text.insert(tk.END, f"\n{'#'*80}\n", "highlight")
        meta_txt = f"{fmt_num(meta_kg)} kg" if meta_kg > 0 else "NÃO DEFINIDA (Livre)"
        self.results_text.insert(tk.END, f"   CONCLUSÃO ESTRATÉGICA: MIX IDEAL (Meta: {meta_txt})\n", "header")
        self.results_text.insert(tk.END, f"{'#'*80}\n", "highlight")

        if opt['status'] == 'ÓTIMO':
            self.results_text.insert(tk.END, f"\n Para atingir a meta lucrando o máximo possível, sugere-se:\n", "normal")
            for item in opt['mix']:
                self.results_text.insert(tk.END, f"   ► {item['qtd']:>5} un. de {item['especie']:<20} (Ciclo: {item['ciclo']} meses)\n", "highlight")
            
            self.results_text.insert(tk.END, f"\n   • Produção Total:      {fmt_num(opt['biomassa_total'])} kg\n", "header")
            self.results_text.insert(tk.END, f"   • Lucro Total (Ciclo): {fmt_moeda(opt['lucro_total'])}\n", "header")
            self.results_text.insert(tk.END, f"   • Payback Estimado:    {opt['payback_meses']:.1f} meses\n", "header")
        
        elif opt['status'] == 'IMPOSSÍVEL':
            self.results_text.insert(tk.END, f"\n [!] IMPOSSÍVEL ATINGIR A META COM OS RECURSOS ATUAIS.\n", "negative")
            self.results_text.insert(tk.END, f"     Tente reduzir a meta ou aumentar o capital.\n", "normal")
        
        self.results_text.insert(tk.END, f"\n{'='*80}\n", "title")
        self.results_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    # Define o nome do arquivo Excel que deve estar na mesma pasta
    db = "especies.xlsx"
    app = OtimizacaoApp(root, db)
    root.mainloop()