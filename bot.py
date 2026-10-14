import telebot
from telebot import types
import threading
import sqlite3
import schedule
import time
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
CHAVE_API = "8815361665:AAGTImf-piBr8SeDIaU0bKEa5zdbv-JDV7M"
bot = telebot.TeleBot(CHAVE_API)

# ==========================================
# 2. BANCO DE DADOS
# ==========================================
conexao = sqlite3.connect('treinos.db', check_same_thread=False)
cursor = conexao.cursor()

cursor.executescript('''
    CREATE TABLE IF NOT EXISTS treinos (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, aparelho TEXT, carga TEXT, data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS agua (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, ml INTEGER, data_registro DATE DEFAULT CURRENT_DATE);
    CREATE TABLE IF NOT EXISTS peso (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, peso REAL, data_registro DATE DEFAULT CURRENT_DATE);
    CREATE TABLE IF NOT EXISTS cardio (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, tempo TEXT, velocidade TEXT, km TEXT, data_registro DATE DEFAULT CURRENT_DATE);
    CREATE TABLE IF NOT EXISTS mounjaro (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, dose_ui REAL, data_aplicacao DATE DEFAULT CURRENT_DATE);
''')
conexao.commit()

# ==========================================
# 3. MOTORES DE LEMBRETE (BACKGROUND)
# ==========================================
def buscar_usuarios():
    cursor.execute("SELECT DISTINCT chat_id FROM agua UNION SELECT DISTINCT chat_id FROM peso UNION SELECT DISTINCT chat_id FROM mounjaro")
    return [linha[0] for linha in cursor.fetchall()]

def lembrar_agua():
    for chat_id in buscar_usuarios():
        try: bot.send_message(chat_id, "💧 *Beba Água!* Mantenha-se hidratada.", parse_mode="Markdown")
        except: pass

def lembrar_creatina():
    for chat_id in buscar_usuarios():
        try: bot.send_message(chat_id, "💊 *Lembrete:* Hora de tomar sua Creatina!", parse_mode="Markdown")
        except: pass

def verificar_mounjaro():
    for chat_id in buscar_usuarios():
        cursor.execute("SELECT data_aplicacao, dose_ui FROM mounjaro WHERE chat_id = ? ORDER BY id DESC LIMIT 1", (chat_id,))
        ultimo = cursor.fetchone()
        if ultimo:
            data_ultima = datetime.strptime(ultimo[0], "%Y-%m-%d").date()
            if (datetime.now().date() - data_ultima).days >= 7:
                try: bot.send_message(chat_id, f"💉 *Atenção!* Hoje completam 7 dias da sua última aplicação de Mounjaro ({ultimo[1]} UI). Hora da nova dose!", parse_mode="Markdown")
                except: pass

schedule.every(2).hours.do(lembrar_agua)
schedule.every().day.at("10:00").do(lembrar_creatina)
schedule.every().day.at("09:00").do(verificar_mounjaro)

def rodar_agendador():
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=rodar_agendador, daemon=True).start()

# ==========================================
# 4. MENU PRINCIPAL E COMANDOS
# ==========================================
@bot.message_handler(commands=['start', 'menu'])
@bot.message_handler(func=lambda msg: msg.text.lower() in ['oi', 'olá', 'ola', 'menu', 'treinar'])
def enviar_menu(mensagem):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💧 Água", callback_data="menu_agua"),
        types.InlineKeyboardButton("🏋️ Aparelhos", callback_data="menu_aparelhos"),
        types.InlineKeyboardButton("🏃 Cardio", callback_data="menu_cardio"),
        types.InlineKeyboardButton("⚖️ Peso", callback_data="menu_peso"),
        types.InlineKeyboardButton("💉 Mounjaro", callback_data="menu_mounjaro"),
        types.InlineKeyboardButton("📊 Relatório do Mês", callback_data="menu_relatorio")
    )
    bot.reply_to(mensagem, "🤖 *bora fazer aquele treinão 💪*\n\nSelecione o que deseja registrar hoje:\n*(Dica: Envie /zerar se quiser apagar tudo e recomeçar)*", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['zerar'])
def zerar_dados(mensagem):
    chat_id = mensagem.chat.id
    cursor.execute("DELETE FROM treinos WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM agua WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM peso WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM cardio WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM mounjaro WHERE chat_id = ?", (chat_id,))
    conexao.commit()
    
    bot.reply_to(mensagem, "🗑️ *Todos os seus dados foram zerados com sucesso!* Sistema limpo para recomeçar.", parse_mode="Markdown")

# ==========================================
# 5. LISTAS DE APARELHOS SEPARADAS
# ==========================================
APARELHOS_SUPERIORES = [
    "Supino Reto", "Supino Inclinado", "Supino Deitado", "Crucifixo", 
    "Puxada Frontal", "Remada Baixa", "Remada Curvada", "Elevação Lateral", 
    "Desenvolvimento", "Rosca Direta", "Rosca Scott", "Tríceps Pulley", 
    "Tríceps Testa", "Paralelas"
]

APARELHOS_INFERIORES = [
    "Agachamento Livre", "Leg Press 45", "Cadeira Extensora", "Mesa Flexora", 
    "Cadeira Flexora", "Leg Press Horizontal", "Panturrilha em Pé", 
    "Panturrilha Sentado", "Afundo", "Elevação Pélvica", "Abdutor", "Adutor"
]

# ==========================================
# 6. GERENCIADOR DE CLIQUES
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def gerenciar_cliques(call):
    chat_id = call.message.chat.id
    dado = call.data
    
    if dado == "menu_agua":
        msg = bot.send_message(chat_id, "Quantos ml de água você tomou agora? (Ex: 300)")
        bot.register_next_step_handler(msg, registrar_agua)
        
    elif dado == "menu_peso":
        msg = bot.send_message(chat_id, "Qual o seu peso atual hoje? (Ex: 65.5)")
        bot.register_next_step_handler(msg, registrar_peso)
        
    elif dado == "menu_mounjaro":
        msg = bot.send_message(chat_id, "Quantas UI de Mounjaro você aplicou hoje? (Ex: 50)")
        bot.register_next_step_handler(msg, registrar_mounjaro)
        
    elif dado == "menu_cardio":
        msg = bot.send_message(chat_id, "Quanto tempo durou o cardio? (Ex: 30 min)")
        bot.register_next_step_handler(msg, cardio_tempo)
        
    elif dado == "menu_relatorio":
        gerar_relatorio_mes(chat_id)
        
    elif dado == "menu_aparelhos":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("💪 Treino Superior", callback_data="cat_superior"),
            types.InlineKeyboardButton("🦵 Treino Inferior", callback_data="cat_inferior")
        )
        bot.send_message(chat_id, "Escolha a categoria do treino:", reply_markup=markup)
        
    elif dado == "cat_superior":
        markup = types.InlineKeyboardMarkup(row_width=2)
        for ap in APARELHOS_SUPERIORES:
            markup.add(types.InlineKeyboardButton(ap, callback_data=f"ap_{ap}"))
        bot.edit_message_text("💪 *Exercícios Superiores:*", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    elif dado == "cat_inferior":
        markup = types.InlineKeyboardMarkup(row_width=2)
        for ap in APARELHOS_INFERIORES:
            markup.add(types.InlineKeyboardButton(ap, callback_data=f"ap_{ap}"))
        bot.edit_message_text("🦵 *Exercícios Inferiores:*", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    elif dado.startswith("ap_"):
        aparelho = dado.replace("ap_", "")
        msg = bot.send_message(chat_id, f"Aparelho: *{aparelho}*\nDigite a carga e repetições (Ex: 20kg 12):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, registrar_carga_treino, aparelho)

    bot.answer_callback_query(call.id)

# ==========================================
# 7. FUNÇÕES DE PROCESSAMENTO E RELATÓRIO
# ==========================================

def gerar_relatorio_mes(chat_id):
    # Conta quantos dias únicos o usuário treinou no mês atual (considerando o formato YYYY-MM)
    mes_atual = datetime.now().strftime("%Y-%m")
    
    cursor.execute("""
        SELECT COUNT(DISTINCT DATE(data_registro)) 
        FROM treinos 
        WHERE chat_id = ? AND strftime('%Y-%m', data_registro) = ?
    """, (chat_id, mes_atual))
    
    dias_treinados = cursor.fetchone()[0]
    
    # Nome do mês atual em português aproximado ou direto
    mes_nome = datetime.now().strftime("%B / %Y")
    
    texto = f"""
📊 *RELATÓRIO DO MÊS ({mes_nome})*

🏋️ Dias totais treinados este mês: *{dias_treinamento_formatado := dias_treinados} dias*

Continue focado(a)! Cada treino conta para o seu objetivo. 💪🔥
"""
    bot.send_message(chat_id, texto, parse_mode="Markdown")

def registrar_agua(mensagem):
    try:
        ml = int(mensagem.text.replace("ml", "").strip())
        cursor.execute("INSERT INTO agua (chat_id, ml) VALUES (?, ?)", (mensagem.chat.id, ml))
        conexao.commit()
        
        cursor.execute("SELECT SUM(ml) FROM agua WHERE chat_id = ? AND data_registro = CURRENT_DATE", (mensagem.chat.id,))
        total = cursor.fetchone()[0]
        bot.reply_to(mensagem, f"✅ *{ml}ml* registrados!\n💧 Total acumulado hoje: *{total}ml*.", parse_mode="Markdown")
    except:
        bot.reply_to(mensagem, "Digite apenas números (Ex: 300). Abra o /menu novamente.")

def registrar_peso(mensagem):
    try:
        peso_atual = float(mensagem.text.replace(",", "."))
        chat_id = mensagem.chat.id
        
        cursor.execute("SELECT peso, data_registro FROM peso WHERE chat_id = ? AND data_registro <= date('now', '-15 days') ORDER BY data_registro DESC LIMIT 1", (chat_id,))
        antigo = cursor.fetchone()
        
        cursor.execute("INSERT INTO peso (chat_id, peso) VALUES (?, ?)", (chat_id, peso_atual))
        conexao.commit()
        
        resposta = f"✅ Peso de *{peso_atual}kg* registrado!\n\n"
        if antigo:
            diferenca = peso_atual - antigo[0]
            if diferenca > 0:
                resposta += f"📊 Comparado a 15 dias atrás ({antigo[0]}kg), você **ganhou {abs(diferenca):.1f}kg**."
            elif diferenca < 0:
                resposta += f"📊 Comparado a 15 dias atrás ({antigo[0]}kg), você **perdeu {abs(diferenca):.1f}kg**. Excelente!"
            else:
                resposta += "📊 Seu peso manteve-se exatamente igual comparado a 15 dias atrás."
        else:
            resposta += "📊 Primeiro registro salvo! Daqui a 15 dias faremos o comparativo automático."
            
        bot.reply_to(mensagem, resposta, parse_mode="Markdown")
    except:
        bot.reply_to(mensagem, "Digite apenas o número (Ex: 65.5). Abra o /menu novamente.")

def registrar_mounjaro(mensagem):
    try:
        ui = float(mensagem.text.replace(",", "."))
        cursor.execute("INSERT INTO mounjaro (chat_id, dose_ui) VALUES (?, ?)", (mensagem.chat.id, ui))
        conexao.commit()
        bot.reply_to(mensagem, f"💉 Aplicação de *{ui} UI* registrada! Te avisarei em exatamente 7 dias.", parse_mode="Markdown")
    except:
        bot.reply_to(mensagem, "Digite apenas o número. Abra o /menu novamente.")

def registrar_carga_treino(mensagem, aparelho):
    chat_id = mensagem.chat.id
    cursor.execute("INSERT INTO treinos (chat_id, aparelho, carga) VALUES (?, ?, ?)", (chat_id, aparelho, mensagem.text))
    conexao.commit()
    
    bot.reply_to(mensagem, f"✅ Salvo no {aparelho}: *{mensagem.text}*\n⏱️ Descanso de 60 segundos iniciado.", parse_mode="Markdown")
    threading.Timer(60.0, lambda: bot.send_message(chat_id, f"⏰ *FIM DO DESCANSO!* Pode ir para a próxima série ou digitar /menu.", parse_mode="Markdown")).start()

def cardio_tempo(mensagem):
    bot.reply_to(mensagem, "Qual foi a velocidade média? (Ex: 5.5)")
    bot.register_next_step_handler(mensagem, cardio_velocidade, mensagem.text)

def cardio_velocidade(mensagem, tempo):
    bot.reply_to(mensagem, "Quantos KM você percorreu no total? (Ex: 3.2)")
    bot.register_next_step_handler(mensagem, cardio_km, tempo, mensagem.text)

def cardio_km(mensagem, tempo, velocidade):
    km = mensagem.text
    cursor.execute("INSERT INTO cardio (chat_id, tempo, velocidade, km) VALUES (?, ?, ?, ?)", (mensagem.chat.id, tempo, velocidade, km))
    conexao.commit()
    bot.reply_to(mensagem, f"🏃 *Cardio Concluído e Salvo!*\n⏱️ Tempo: {tempo}\n⚡ Velocidade: {velocidade}\n📏 Distância: {km} km", parse_mode="Markdown")

print("🚀 Sistema completo com Relatório do Mês rodando perfeitamente!")
bot.polling()