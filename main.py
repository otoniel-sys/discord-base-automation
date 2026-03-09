import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import re
from datetime import datetime
import random

# ==============================================================================
# 1. CONFIGURAÇÕES & MAPA DE CANAIS (O Cérebro)
# ==============================================================================
class Config:
    # --- CREDENCIAIS ---
    TOKEN = "TOKEN" 
    ADMIN_ID = 162520339035848704
    GUILD_ID = discord.Object(id=672839520873349120) 

    # --- CORES & VISUAL ---
    COR_NAVI = discord.Color.from_rgb(123, 104, 238) 
    
    # --- MAPA DE CANAIS (A Mágica acontece aqui) ---
    # Adicionar um novo canal é só colocar uma nova linha aqui!
    # Estrutura: ID_DO_CANAL: { Configurações }
    CANAIS = {
        # 1. JOGOS
        1071867983800041522: {
            "tipo": "Jogos",
            "tabela": "reviews_jogos",
            "regex_nome": r"Nome do Jogo.*?:(.*)",
            "regex_nota": r"NOTA FINAL.*?(\d+[\.,]?\d*)",
            "coluna_db": "jogo"
        },
        # 2. FILMES
        672966154788143131: {
            "tipo": "Filmes",
            "tabela": "reviews_filmes",
            "regex_nome": r"Nome do filme.*?:(.*)",
            "regex_nota": r"Nota:.*?(\d+[\.,]?\d*)",
            "coluna_db": "filme"
        },
        # 3. ANIMES
        1237737555299008512: {
            "tipo": "Animes",
            "tabela": "reviews_animes",
            "regex_nome": r"Nome do Anime.*?:(.*)",
            "regex_nota": r"NOTA FINAL.*?(\d+[\.,]?\d*)", # Ajuste o regex se for 'Nota:' ou 'NOTA FINAL'
            "coluna_db": "anime"
        },
        # 4. CLUBE DOS JOGOS
        1411715018281451652: {
            "tipo": "Clube",
            "tabela": "reviews_clube",
            "regex_nome": r"Nome do Jogo.*?:(.*)",
            "regex_nota": r"NOTA FINAL.*?(\d+[\.,]?\d*)",
            "coluna_db": "jogo"
        }
    }

    # --- RECURSOS VISUAIS ---
    IMAGENS = {
        "10": "https://cdn.discordapp.com/attachments/1105673022536437840/1461114910741102730/Navi10.png?ex=696960cc&is=69680f4c&hm=bad884214dd07eec3393beb0ca18c4274fc77932a3371e46e64e6b8a8fc6bc18&",
        "8-9": "https://cdn.discordapp.com/attachments/1105673022536437840/1461114920761294848/Navi89.png?ex=696960cf&is=69680f4f&hm=d5529715f003fab3f336ae015f2f7ecc6da931277b6384eab2f8f297bc864722&",
        "6-7": "https://cdn.discordapp.com/attachments/1105673022536437840/1461114919780089979/Navi67.png?ex=696960cf&is=69680f4f&hm=5558b0a15f1d4bd8617d50f8d3a77fe00d69ba644911cd8d215d151ebba5dc50&",
        "4-5": "https://cdn.discordapp.com/attachments/1105673022536437840/1461114912443990167/Navi45.png?ex=696960cd&is=69680f4d&hm=c79e7a0fbc7440963da7d41e88e0ac14760642d6f9a47961ad935c4d88dd2f33&",
        "2-3": "https://cdn.discordapp.com/attachments/1105673022536437840/1461114911617843428/Navi23.png?ex=696960cd&is=69680f4d&hm=6b2bf70134d090c106e23b4ad33555ea10299540b1e9ff387e764d5cc481ba5b&",
        "0-1": "https://cdn.discordapp.com/attachments/1105673022536437840/1461114909881405573/Navi01.png?ex=696960cc&is=69680f4c&hm=368edb623c174d47a04145e5b60f70861b046b11fcf3841b6bbd603e277d0e84&"
    }

    FRASES_PISTOLA = [
        "Tu é burro ou só se faz? A nota é de 0 a 10, animal! 🤬",
        "Sai daqui com esse número torto! Eu não sou calculadora de padaria não!",
        "HEY! LISTEN! Tu tá querendo crashar meu banco? Vaza daqui! 🖕",
        "Detectei um usuário com QI negativo tentando usar o comando. Bloqueado. 🚫"
    ]

# ==============================================================================
# 2. GERENCIADOR DE BANCO DE DADOS
# ==============================================================================
class DatabaseManager:
    def __init__(self, db_name="criticas.db"):
        self.db_name = db_name

    def conectar(self):
        return sqlite3.connect(self.db_name)

    def criar_tabelas(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            # Criação dinâmica baseada no mapa de canais não é ideal pois SQL precisa ser fixo,
            # então mantemos a criação explícita para segurança.
            cursor.execute('CREATE TABLE IF NOT EXISTS reviews_jogos (msg_id INTEGER PRIMARY KEY, user_id INTEGER, jogo TEXT NOT NULL, nota REAL NOT NULL, autor TEXT NOT NULL, data TEXT NOT NULL, link_msg TEXT NOT NULL)')
            cursor.execute('CREATE TABLE IF NOT EXISTS reviews_filmes (msg_id INTEGER PRIMARY KEY, user_id INTEGER, filme TEXT NOT NULL, nota REAL NOT NULL, autor TEXT NOT NULL, data TEXT NOT NULL, link_msg TEXT NOT NULL)')
            cursor.execute('CREATE TABLE IF NOT EXISTS reviews_animes (msg_id INTEGER PRIMARY KEY, user_id INTEGER, anime TEXT NOT NULL, nota REAL NOT NULL, autor TEXT NOT NULL, data TEXT NOT NULL, link_msg TEXT NOT NULL)')
            cursor.execute('CREATE TABLE IF NOT EXISTS reviews_clube (msg_id INTEGER PRIMARY KEY, user_id INTEGER, jogo TEXT NOT NULL, nota REAL NOT NULL, autor TEXT NOT NULL, data TEXT NOT NULL, link_msg TEXT NOT NULL)')
            conn.commit()

    # Função Auxiliar Inteligente para pegar o nome da coluna correta
    def _obter_coluna_obra(self, tabela):
        if "filmes" in tabela: return "filme"
        if "animes" in tabela: return "anime"
        return "jogo"

    def salvar_critica(self, tabela, msg_id, user_id, obra, nota, autor, data, link):
        coluna = self._obter_coluna_obra(tabela)
        try:
            with self.conectar() as conn:
                conn.cursor().execute(f'''
                    INSERT OR IGNORE INTO {tabela} (msg_id, user_id, {coluna}, nota, autor, data, link_msg)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (msg_id, user_id, obra, nota, autor, data, link))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERRO DB] Salvar em {tabela}: {e}")
            return False

    def deletar_critica(self, tabela, msg_id):
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {tabela} WHERE msg_id = ?", (msg_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ERRO DB] Deletar: {e}")
            return False

    def buscar_por_nota(self, tabela, nota_alvo, busca_ampla=True):
        coluna = self._obter_coluna_obra(tabela)
        op = ">=" if busca_ampla else ">"
        op2 = "<"
        
        # Margem de erro para floats (ex: 8.5)
        margem_inf = 0 if busca_ampla else 0.01
        margem_sup = 1 if busca_ampla else 0.01
        
        query = f"SELECT {coluna}, nota, autor, link_msg, data FROM {tabela} WHERE nota {op} ? AND nota {op2} ? ORDER BY nota DESC"
        params = (nota_alvo - margem_inf, nota_alvo + margem_sup)
        
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def buscar_por_nome(self, tabela, texto_busca):
        coluna = self._obter_coluna_obra(tabela)
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {coluna}, nota, autor, link_msg, data FROM {tabela} WHERE {coluna} LIKE ?", (f'%{texto_busca}%',))
            return cursor.fetchall()

    def obter_estatisticas(self, tabela, user_id):
        coluna = self._obter_coluna_obra(tabela)
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {tabela} WHERE user_id = ?", (user_id,))
            total = cursor.fetchone()[0]
            if total == 0: return None
            
            cursor.execute(f"SELECT AVG(nota) FROM {tabela} WHERE user_id = ?", (user_id,))
            media = round(cursor.fetchone()[0], 1)
            
            cursor.execute(f"SELECT {coluna}, nota FROM {tabela} WHERE user_id = ? ORDER BY nota DESC LIMIT 1", (user_id,))
            fav = cursor.fetchone()
            return {"total": total, "media": media, "favorito": fav[0], "nota_fav": fav[1]}

    def obter_ranking(self, tabela):
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT autor, COUNT(*) as total FROM {tabela} GROUP BY user_id ORDER BY total DESC LIMIT 10")
            return cursor.fetchall()
    

    def obter_recorde_tabela(self, tabela):
        """Descobre qual é o maior número de críticas que alguém tem nessa tabela."""
        with self.conectar() as conn:
            cursor = conn.cursor()
            # Conta reviews por usuário, ordena do maior pro menor e pega o primeiro
            cursor.execute(f'''
                SELECT COUNT(*) as total 
                FROM {tabela} 
                GROUP BY user_id 
                ORDER BY total DESC 
                LIMIT 1
            ''')
            resultado = cursor.fetchone()
            return resultado[0] if resultado else 0
    # ... dentro da classe DatabaseManager ...

    def obter_todos_ranking(self, tabela):
        """Retorna uma lista de tuplas [(Autor, Total), ...] de todos os usuários."""
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT autor, COUNT(*) as total 
                FROM {tabela} 
                GROUP BY user_id 
                ORDER BY total DESC
            ''')
            return cursor.fetchall()
    # ... (dentro da classe DatabaseManager) ...

    def obter_indicacao_aleatoria(self, tabela, nota_min, nota_max):
        """Busca 1 review aleatório dentro da faixa de nota."""
        with self.conectar() as conn:
            cursor = conn.cursor()
            # ORDER BY RANDOM() sorteia um item
            cursor.execute(f'''
                SELECT {self._obter_coluna_obra(tabela)}, nota, autor, link_msg, data 
                FROM {tabela} 
                WHERE nota >= ? AND nota <= ? 
                ORDER BY RANDOM() 
                LIMIT 1
            ''', (nota_min, nota_max))
            return cursor.fetchone()
        
db = DatabaseManager()

# ==============================================================================
# 3. INTERFACE VISUAL & NAVEGADOR
# ==============================================================================
class InterfaceVisual:
    @staticmethod
    def obter_visual_nota(nota):
        if nota >= 10:   return Config.IMAGENS["10"], "UMA LENDA! 👑"
        elif nota >= 8:  return Config.IMAGENS["8-9"], "Obra indispensável! ✨"
        elif nota >= 6:  return Config.IMAGENS["6-7"], "Divertido, vale a pena. 👍"
        elif nota >= 4:  return Config.IMAGENS["4-5"], "Meh... só se não tiver nada melhor. 😐"
        elif nota >= 2:  return Config.IMAGENS["2-3"], "Dor e sofrimento. 🤢"
        else:            return Config.IMAGENS["0-1"], "FUJA ENQUANTO PODE! 💀"

    @staticmethod
    def criar_embed(nome_obra, nota, autor, link, data_msg, avatar_bot, cor_tema):
        url_img, texto_reacao = InterfaceVisual.obter_visual_nota(nota)
        data_limpa = str(data_msg).split(".")[0]
        
        embed = discord.Embed(
            title=f"⭐ {nome_obra.upper()}",
            description=f"### Nota: {nota}\n*{texto_reacao}*\n────────────────────\n✨ *Avaliação por **{autor}**.*",
            url=link,
            color=cor_tema
        )
        embed.set_thumbnail(url=url_img)
        if avatar_bot: embed.set_author(name="🧚 Hey, listen! Encontrei isso:", icon_url=avatar_bot)
        embed.set_footer(text=f"📅 Postado em: {data_limpa} • Memória da Navi")
        return embed

class NavegadorCriticas(discord.ui.View):
    def __init__(self, resultados, autor_id, avatar_bot, cor_tema):
        super().__init__(timeout=120)
        self.resultados = resultados
        self.index = 0
        self.autor_id = autor_id
        self.avatar_bot = avatar_bot
        self.cor_tema = cor_tema 
        self.atualizar_botoes()

    def atualizar_botoes(self):
        self.btn_ant.disabled = (self.index == 0)
        self.btn_prox.disabled = (self.index == len(self.resultados) - 1)
        self.btn_count.label = f"{self.index + 1}/{len(self.resultados)}"

    def get_embed(self):
        obra, nota, autor, link, data = self.resultados[self.index]
        return InterfaceVisual.criar_embed(obra, nota, autor, link, data, self.avatar_bot, self.cor_tema)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary)
    async def btn_ant(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id: return
        self.index -= 1
        self.atualizar_botoes()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.grey, disabled=True)
    async def btn_count(self, interaction: discord.Interaction, button: discord.ui.Button): pass

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
    async def btn_prox(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id: return
        self.index += 1
        self.atualizar_botoes()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ==============================================================================
# 4. BOT CORE (Eventos Simplificados)
# ==============================================================================
class NaviBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.tree.copy_global_to(guild=Config.GUILD_ID)
        await self.tree.sync(guild=Config.GUILD_ID)
        print("--- Comandos Sincronizados! ---")

    async def on_ready(self):
        db.criar_tabelas()
        print(f"--- Navi Logada: {self.user} ---")

    # --- AUTO-SAVE (AGORA USA O DICIONÁRIO) ---
    async def on_message(self, message):
        if message.author.bot: return

        # Verifica se o canal está no nosso mapa de canais
        config_canal = Config.CANAIS.get(message.channel.id)
        
        if config_canal:
            match_nome = re.search(config_canal["regex_nome"], message.content, re.IGNORECASE)
            match_nota = re.search(config_canal["regex_nota"], message.content, re.IGNORECASE)

            if match_nome and match_nota:
                try:
                    nome = match_nome.group(1).replace('*', '').strip()
                    nota = float(match_nota.group(1).replace(',', '.'))
                    
                    salvou = db.salvar_critica(
                        config_canal["tabela"],
                        message.id, message.author.id, nome, nota, 
                        message.author.name, str(message.created_at), message.jump_url
                    )
                    if salvou:
                        await message.add_reaction("💾")
                        await message.add_reaction("✅")
                        print(f"[AUTO] {config_canal['tipo']} salvo: {nome}")
                except Exception as e:
                    print(f"[ERRO] Falha ao salvar: {e}")

        await self.process_commands(message)

    # --- AUTO-DELETE (AGORA USA O DICIONÁRIO) ---
    async def on_message_delete(self, message):
        config_canal = Config.CANAIS.get(message.channel.id)
        if config_canal:
            if db.deletar_critica(config_canal["tabela"], message.id):
                print(f"[AUTO] Deletado de {config_canal['tabela']} - ID: {message.id}")

bot = NaviBot()

# ==============================================================================
# 5. LÓGICA COMPARTILHADA DE COMANDOS (Helpers)
# ==============================================================================
async def helper_buscar_nota(interaction: discord.Interaction, nota_str: str, tabela: str):
    nota_limpa = nota_str.replace(",", ".").strip()
    try: valor = float(nota_limpa)
    except: return await interaction.response.send_message("❌ Isso não é número!", ephemeral=True)

    if not (0 <= valor <= 100):
        embed = discord.Embed(title="🚨 ERRO CAMADA 8", description=random.choice(Config.FRASES_PISTOLA), color=0xFF0000)
        return await interaction.response.send_message(embed=embed)

    await interaction.response.defer()
    busca_ampla = "." not in nota_limpa
    resultados = db.buscar_por_nota(tabela, valor, busca_ampla)

    if not resultados:
        return await interaction.followup.send(f"❌ Nada com nota **{valor}** em {tabela.replace('reviews_', '').upper()}.")

    view = NavegadorCriticas(resultados, interaction.user.id, bot.user.avatar.url, Config.COR_NAVI)
    await interaction.followup.send(embed=view.get_embed(), view=view)

async def helper_buscar_nome(interaction: discord.Interaction, nome: str, tabela: str):
    if len(nome) > 60: return await interaction.response.send_message("❌ Texto muito longo!", ephemeral=True)
    if any(x in nome.upper() for x in [";", "DROP TABLE", "DELETE FROM"]):
        return await interaction.response.send_message("🚨 Sai daqui hacker!", ephemeral=True)

    await interaction.response.defer()
    resultados = db.buscar_por_nome(tabela, nome.strip())

    if not resultados:
        return await interaction.followup.send(f"❌ Nada encontrado para **'{nome}'** em {tabela.replace('reviews_', '').upper()}.")

    view = NavegadorCriticas(resultados, interaction.user.id, bot.user.avatar.url, Config.COR_NAVI)
    await interaction.followup.send(f"🔎 Encontrei **{len(resultados)}** resultados:", embed=view.get_embed(), view=view)

def gerar_barra_xp(atual, meta):
    """Gera uma barra visual: [▓▓▓▓░░░░░░]"""
    # Garante que não passe de 100%
    porcentagem = min(atual / meta, 1.0)
    cheios = int(porcentagem * 15) # 15 blocos de largura
    vazios = 15 - cheios
    
    # Efeito visual de carregamento
    barra = "▓" * cheios + "░" * vazios
    return f"[`{barra}`] {int(porcentagem * 100)}%"
# ==============================================================================
# 6. COMANDOS REGISTRADOS
# ==============================================================================

# --- ADMIN ---
@bot.tree.command(name="admin_sync", description="[ADMIN] Força leitura do canal atual")
async def admin_sync(interaction: discord.Interaction):
    if interaction.user.id != Config.ADMIN_ID: return await interaction.response.send_message("🚫 Sai!", ephemeral=True)
    
    config = Config.CANAIS.get(interaction.channel.id)
    if not config: return await interaction.response.send_message("❌ Canal não configurado!", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    lidas, salvas = 0, 0
    
    async for message in interaction.channel.history(limit=None):
        lidas += 1
        if message.author.bot or not message.content: continue
        
        match_nome = re.search(config["regex_nome"], message.content, re.IGNORECASE)
        match_nota = re.search(config["regex_nota"], message.content, re.IGNORECASE)

        if match_nome and match_nota:
            nome = match_nome.group(1).replace('*', '').strip()
            nota = float(match_nota.group(1).replace(',', '.'))
            db.salvar_critica(config["tabela"], message.id, message.author.id, nome, nota, message.author.name, str(message.created_at), message.jump_url)
            salvas += 1
            
    await interaction.followup.send(f"✅ **Sync de {config['tipo']} Concluído!**\n🔍 Lidas: {lidas}\n💾 Salvas: **{salvas}**")

@bot.command(name="exorcizar")
async def exorcizar(ctx):
    if ctx.author.id != Config.ADMIN_ID: return
    msg = await ctx.send("👻 Limpando comandos...")
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    await msg.edit(content="✨ Limpeza Concluída! Reinicie o bot.")

# --- JOGOS ---
@bot.tree.command(name="buscar_jogo", description="🎮 Busca Jogos por nome")
async def b_jogo(interaction: discord.Interaction, nome: str): await helper_buscar_nome(interaction, nome, "reviews_jogos")

@bot.tree.command(name="buscar_nota_jogo", description="🎮 Busca Jogos por nota")
async def b_nota_jogo(interaction: discord.Interaction, nota: str): await helper_buscar_nota(interaction, nota, "reviews_jogos")

# --- FILMES ---
@bot.tree.command(name="buscar_filme", description="🎬 Busca Filmes por nome")
async def b_filme(interaction: discord.Interaction, nome: str): await helper_buscar_nome(interaction, nome, "reviews_filmes")

@bot.tree.command(name="buscar_nota_filme", description="🎬 Busca Filmes por nota")
async def b_nota_filme(interaction: discord.Interaction, nota: str): await helper_buscar_nota(interaction, nota, "reviews_filmes")

# --- ANIMES ---
@bot.tree.command(name="buscar_anime", description="⛩️ Busca Animes por nome")
async def b_anime(interaction: discord.Interaction, nome: str): await helper_buscar_nome(interaction, nome, "reviews_animes")

@bot.tree.command(name="buscar_nota_anime", description="⛩️ Busca Animes por nota")
async def b_nota_anime(interaction: discord.Interaction, nota: str): await helper_buscar_nota(interaction, nota, "reviews_animes")

# --- CLUBE ---
@bot.tree.command(name="buscar_clube", description="🎲 Busca no Clube por nome")
async def b_clube(interaction: discord.Interaction, nome: str): await helper_buscar_nome(interaction, nome, "reviews_clube")

@bot.tree.command(name="buscar_nota_clube", description="🎲 Busca no Clube por nota")
async def b_nota_clube(interaction: discord.Interaction, nota: str): await helper_buscar_nota(interaction, nota, "reviews_clube")

# --- SOCIAL ---
@bot.tree.command(name="perfil", description="👤 Exibe sua Carteira e Status Financeiro do Clube")
async def perfil(interaction: discord.Interaction, usuario: discord.Member = None):
    await interaction.response.defer()
    alvo = usuario or interaction.user
    
    # 1. Coleta estatísticas individuais
    s_jogos = db.obter_estatisticas("reviews_jogos", alvo.id)
    s_filmes = db.obter_estatisticas("reviews_filmes", alvo.id)
    s_animes = db.obter_estatisticas("reviews_animes", alvo.id)
    s_clube = db.obter_estatisticas("reviews_clube", alvo.id)
    
    # 2. Descobre a META DO CLUBE (Quantas críticas o Líder tem?)
    meta_do_clube = db.obter_recorde_tabela("reviews_clube")
    
    # 3. Contagem Simples
    qtd_jogos = s_jogos['total'] if s_jogos else 0
    qtd_filmes = s_filmes['total'] if s_filmes else 0
    qtd_animes = s_animes['total'] if s_animes else 0
    qtd_clube = s_clube['total'] if s_clube else 0
    
    # XP GERAL
    total_xp = qtd_jogos + qtd_filmes + qtd_animes + qtd_clube

    # 4. Nível Geral (RPG)
    if total_xp < 10:   nivel, meta_xp, titulo = 1, 10, "Iniciado"
    elif total_xp < 30: nivel, meta_xp, titulo = 5, 30, "Entusiasta"
    elif total_xp < 60: nivel, meta_xp, titulo = 10, 60, "Crítico Sênior"
    elif total_xp < 100: nivel, meta_xp, titulo = 25, 100, "Mestre da Cultura"
    else:               nivel, meta_xp, titulo = 50, 200, "Oráculo Supremo"

    # 5. Montagem do Embed
    embed = discord.Embed(
        title=f"🆔 CARD DE CRÍTICO: {alvo.display_name.upper()}",
        color=Config.COR_NAVI
    )
    if alvo.avatar: embed.set_thumbnail(url=alvo.avatar.url)

    # Barra de XP Geral
    barra_visual = gerar_barra_xp(total_xp, meta_xp)
    embed.add_field(
        name=f"🏆 Nível {nivel} - {titulo}",
        value=f"{barra_visual}\n*XP Total: {total_xp} / {meta_xp}*",
        inline=False
    )

    # Histórico Geral
    resumo = (
        f"🎮 **Jogos:** {qtd_jogos}\n"
        f"🎬 **Filmes:** {qtd_filmes}\n"
        f"⛩️ **Animes:** {qtd_animes}"
    )
    embed.add_field(name="📊 Histórico", value=resumo, inline=True)

    # 6. --- LÓGICA DO CLUBE (O Débito) ---
    embed.add_field(name="\u200b", value="\u200b", inline=False) 

    # Cores ANSI: 31=Vermelho, 32=Verde, 33=Amarelo, 36=Ciano, 37=Branco
    
    if qtd_clube == 0:
        # CASO 1: NÃO MEMBRO (Vermelho)
        status_txt = "\u001b[0;31m❌ NÃO ASSOCIADO"
        detalhes = "\u001b[0;30mNenhuma participação.\u001b[0m"
        meta_txt = "\u001b[0;30mJunte-se a nós!\u001b[0m"
    
    elif qtd_clube >= meta_do_clube:
        # CASO 2: EM DIA / LÍDER (Verde)
        status_txt = "\u001b[0;32m✅ MEMBRO EM DIA"
        detalhes = f"\u001b[0;36mParticipações: \u001b[1;37m{qtd_clube}\u001b[0m"
        meta_txt = "\u001b[0;32mVocê é o exemplo do Clube!\u001b[0m"
        
    else:
        # CASO 3: EM DÉBITO (Amarelo)
        # Calcula quantos jogos ele deve
        divida = meta_do_clube - qtd_clube
        status_txt = "\u001b[0;33m⚠️ EM DÉBITO"
        detalhes = f"\u001b[0;36mParticipações: \u001b[1;37m{qtd_clube}\u001b[0m"
        meta_txt = f"\u001b[0;33mFaltam {divida} jogos para alcançar a meta!\u001b[0m"

    # Bloco Visual ANSI
    bloco_clube = (
        "```ansi\n"
        "\u001b[1;37m═══ 💎 CLUBE DOS JOGOS 💎 ═══\u001b[0m\n"
        f"{status_txt}\u001b[0m\n\n"
        f"{detalhes}\n"
        f"{meta_txt}\n"
        "```"
    )

    embed.add_field(name="SITUAÇÃO CADASTRAL", value=bloco_clube, inline=False)
    
    embed.set_footer(text="Navi System • Documento Intransferível")

    await interaction.followup.send(embed=embed)
@bot.tree.command(name="ranking", description="🏆 Ranking Geral")
async def ranking(interaction: discord.Interaction):
    await interaction.response.defer()
    
    def formatar(lista):
        if not lista: return "🦗 *Ninguém*"
        return "\n".join([f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'`#{i+1}`'} **{n}** — {t}" for i, (n, t) in enumerate(lista)])

    embed = discord.Embed(title="🏆 HALL DA FAMA", color=Config.COR_NAVI)
    embed.add_field(name="🎮 Jogos", value=formatar(db.obter_ranking("reviews_jogos")), inline=True)
    embed.add_field(name="🎬 Filmes", value=formatar(db.obter_ranking("reviews_filmes")), inline=True)
    embed.add_field(name="⛩️ Animes", value=formatar(db.obter_ranking("reviews_animes")), inline=True)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="mural_clube", description="🎲 Mostra quem está devendo jogos no Clube!")
async def mural_clube(interaction: discord.Interaction):
    await interaction.response.defer()
    
    # Pega todos os participantes
    ranking = db.obter_todos_ranking("reviews_clube")
    
    if not ranking:
        await interaction.followup.send("🦗 O Clube está vazio. Comecem a jogar!")
        return

    # O primeiro da lista é o Líder (maior número)
    lider_nome, lider_total = ranking[0]
    
    texto_em_dia = ""
    texto_devedores = ""
    
    for nome, total in ranking:
        divida = lider_total - total
        
        if divida == 0:
            texto_em_dia += f"🏆 **{nome}** ({total})\n"
        else:
            # Calcula porcentagem da dívida para gerar barra de vergonha
            # Quanto mais deve, mais vermelha a situação (simbolicamente)
            texto_devedores += f"⚠️ **{nome}** — Tem {total} (Deve **{divida}**)\n"

    embed = discord.Embed(
        title="🎲 SITUAÇÃO CADASTRAL DO CLUBE",
        description=f"A meta atual é **{lider_total} jogos** (Definida por {lider_nome}).",
        color=Config.COR_NAVI
    )
    
    embed.add_field(name="✅ MEMBROS EM DIA", value=texto_em_dia if texto_em_dia else "Ninguém...", inline=False)
    
    if texto_devedores:
        embed.add_field(name="💸 LISTA DE DEVEDORES", value=texto_devedores, inline=False)
        embed.set_footer(text="A Navi não esquece. Paguem seus jogos!")
    else:
        embed.set_footer(text="Milagre! Todos estão em dia! 🎉")

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="indicar", description="🎲 A Navi escolhe o que você vai consumir hoje!")
@app_commands.describe(
    categoria="O que você quer assistir/jogar?", 
    vibe="Qual a qualidade que você procura?"
)
@app_commands.choices(
    categoria=[
        app_commands.Choice(name="🎮 Jogos", value="reviews_jogos"),
        app_commands.Choice(name="🎬 Filmes", value="reviews_filmes"),
        app_commands.Choice(name="⛩️ Animes", value="reviews_animes"),
        app_commands.Choice(name="🎲 Clube dos Jogos", value="reviews_clube")
    ],
    vibe=[
        app_commands.Choice(name="💎 Obra-Prima (Nota 8+)", value="bom"),
        app_commands.Choice(name="😐 Passatempo (Nota 5 a 7)", value="medio"),
        app_commands.Choice(name="☠️ Chorume Radioativo (Nota 0 a 4)", value="ruim")
    ]
)
async def indicar(interaction: discord.Interaction, categoria: str, vibe: str):
    await interaction.response.defer()

    # 1. Define as regras baseado na escolha
    if vibe == "bom":
        min_n, max_n = 8.0, 100.0
        titulo = "💎 A NAVI RECOMENDA (Qualidade Garantida)"
        cor = 0xFFD700 # Dourado
        frase_fail = "Nenhuma obra-prima encontrada... Vocês são muito chatos ou o banco está vazio!"
    
    elif vibe == "medio":
        min_n, max_n = 5.0, 7.9
        titulo = "😐 A NAVI RECOMENDA (Dá pro gasto)"
        cor = 0xFFA500 # Laranja
        frase_fail = "Nada 'mais ou menos' encontrado. Aqui é 8 ou 80!"

    else: # ruim
        min_n, max_n = 0.0, 4.9
        titulo = "☠️ A NAVI RECOMENDA (Por sua conta e risco...)"
        cor = 0x543632 # Marrom cocô / Vermelho escuro
        frase_fail = "Infelizmente (ou felizmente?) ninguém jogou nada tão horrível assim ainda."

    # 2. Busca no banco
    resultado = db.obter_indicacao_aleatoria(categoria, min_n, max_n)

    if not resultado:
        await interaction.followup.send(f"❌ **{frase_fail}**")
        return

    # 3. Monta o Embed da Recomendação
    obra, nota, autor, link, data = resultado
    
    # Reutiliza sua classe visual para ficar bonito
    embed = InterfaceVisual.criar_embed(
        nome_obra=obra,
        nota=nota,
        autor=autor,
        link=link,
        data_msg=data,
        avatar_bot=bot.user.avatar.url,
        cor_tema=cor # Usa a cor da vibe (Dourado/Laranja/Marrom)
    )
    
    # Muda o título para o título da recomendação
    embed.title = f"{titulo}\n⭐ {obra.upper()}"
    
    await interaction.followup.send(content=f"Ei {interaction.user.mention}, olha o que eu achei pra você:", embed=embed)

@bot.tree.command(name="ping", description="Latência")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🧚 **Hey!** {round(bot.latency * 1000)}ms")

if __name__ == "__main__":
    bot.run(Config.TOKEN)