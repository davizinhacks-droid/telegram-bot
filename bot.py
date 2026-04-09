import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from datetime import datetime

TOKEN = "8610620640:AAGuhN1xnszoy2VGhbbMBegBMYj8MLT9vBU"
ADMIN_IDS = [8601232068]

# ===== DB =====
DB_PATH = os.path.join(os.getcwd(), "bot.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password TEXT,
    estado TEXT DEFAULT 'activo',
    session INTEGER DEFAULT 0,
    saldo REAL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    name TEXT,
    price REAL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER,
    content TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    product_name TEXT,
    variant_name TEXT,
    price REAL,
    content TEXT,
    date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    name TEXT,
    price REAL DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    variant_id INTEGER,
    price REAL
)
""")

try:
    cursor.execute("ALTER TABLE variants ADD COLUMN delivery_type TEXT DEFAULT 'auto'")
    conn.commit()
except:
    pass



# ===== HELPERS =====
def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_logged(user_id):
    cursor.execute("SELECT session FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] == 1

def kb(b): return InlineKeyboardMarkup(b)

async def render(update, text, buttons):
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=kb(buttons), parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text, reply_markup=kb(buttons), parse_mode="HTML"
            )
    except:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text, reply_markup=kb(buttons), parse_mode="HTML"
            )

# ===== MENUS =====
def login_menu():
    return [
        [InlineKeyboardButton("🔐 Login", callback_data="login")],
        [InlineKeyboardButton("📝 Registrar", callback_data="register")]
    ]

def main_menu(uid):  
    rows = [
        [InlineKeyboardButton("🛒 Tienda", callback_data="shop")],
        [InlineKeyboardButton("👤 Perfil", callback_data="perfil")],
        [InlineKeyboardButton("📋 Historial", callback_data="history")]
    ]

    if is_admin(uid):
        rows.append([InlineKeyboardButton("👑 Panel Admin", callback_data="admin")])

    rows.append([InlineKeyboardButton("❌ Cerrar sesión", callback_data="logout")])

    return rows

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    username = update.message.from_user.first_name

    if is_logged(uid):
        await render(
            update,
            f"""👋 <b>Bienvenido de nuevo, {username}</b>

🛒 Compra rápida y segura
⚡ Entrega automática
💎 Mejores precios disponibles

━━━━━━━━━━━━━━
""",
            main_menu(uid)
        )
    else:
        context.user_data.clear()
        await render(
            update,
            f"""👋 <b>Bienvenido, {username}</b>

🛒 <b>Tienda automática 24/7</b>
💳 Recargas rápidas
⚡ Entrega instantánea

━━━━━━━━━━━━━━
🔐 <b>Inicia sesión</b>

usuario contraseña
""",
            login_menu()
        )

# ===== BOTONES =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    # AUTH
    if q.data == "login":
        context.user_data["state"] = "login"
        await render(update, "<b>🔐 Login</b>\n\nusuario contraseña", [])

    elif q.data == "register":
        context.user_data["state"] = "register"
        await render(update, "<b>📝 Registro</b>\n\nusuario contraseña", [])

    elif q.data == "logout":
        cursor.execute("UPDATE users SET session=0 WHERE user_id=?", (uid,))
        conn.commit()
        context.user_data.clear()
        await render(update, "✅ Sesión cerrada", login_menu())

    # ===== PERFIL =====
    elif q.data == "perfil":
        cursor.execute("SELECT username, saldo FROM users WHERE user_id=?", (uid,))
        u = cursor.fetchone()

        perfil_text = f"""👤 <b>PERFIL</b>

━━━━━━━━━━━━━━
🧑 Usuario: <code>@{u[0]}</code>
💰 Saldo: <code>${u[1]:.2f}</code>
━━━━━━━━━━━━━━

💡 Puedes recargar saldo para comprar
"""

        await render(update, perfil_text, main_menu(uid))

    # ===== HISTORIAL USUARIO =====
    elif q.data == "history":
        cursor.execute("""
        SELECT product_name, variant_name, price, date 
        FROM history 
        WHERE user_id=? 
        ORDER BY date DESC 
        LIMIT 10
        """, (uid,))
        compras = cursor.fetchall()

        if not compras:
            await render(update, "📋 <b>No tienes compras aún</b>", main_menu(uid))
            return

        historial_text = "📋 <b>TUS ÚLTIMAS COMPRAS</b>\n\n"
        for i, compra in enumerate(compras, 1):
            historial_text += f"""<b>{i}.</b> {compra[0]}<b> - </b>{compra[1]}
💰 <code>${compra[2]:.2f}</code> | 📅 <code>{compra[3][:16]}</code>
━━━━━━━━━━━━━━"""
        
        historial_text += f"\n\n📊 Total: <b>{len(compras)}</b> compras"
        await render(update, historial_text, main_menu(uid))

    elif q.data == "menu":
        await render(
            update,
            """🏠 <b>MENÚ PRINCIPAL</b>

Selecciona una opción:

🛒 Comprar productos
👤 Ver tu perfil
📋 Revisar historial

━━━━━━━━━━━━━━
""",
            main_menu(uid)
        )

    # ===== TIENDA =====
    elif q.data == "shop":
        cursor.execute("SELECT id, name FROM products")
        products = cursor.fetchall()

        if not products:
            await render(update, "🛒 <b>No hay productos</b>", main_menu(uid))
            return

        btns = [[InlineKeyboardButton(p[1], callback_data=f"p_{p[0]}")] for p in products]
        btns.append([InlineKeyboardButton("⬅️ Menú", callback_data="menu")])
        await render(
    update,
    """🛒 <b>TIENDA</b>

Selecciona un producto:

💡 Todos los accesos son automáticos
⚡ Entrega inmediata

━━━━━━━━━━━━━━
""",
    btns
)

    elif q.data.startswith("p_"):
        pid = int(q.data.split("_")[1])

        cursor.execute(
            "SELECT id, name, price FROM variants WHERE product_id=?",
            (pid,)
        )
        variants = cursor.fetchall()

        btns = []

        for v in variants:
            vid = v[0]

            cursor.execute(
                "SELECT price FROM user_prices WHERE user_id=? AND variant_id=?",
                (uid, vid)
            )
            custom = cursor.fetchone()

            if custom:
                price = custom[0]
            else:
                price = v[2]

            btns.append([
                InlineKeyboardButton(
                    f"{v[1]} - ${price:.2f}",
                    callback_data=f"confirm_{vid}"
                )
            ])

        btns.append([
            InlineKeyboardButton("⬅️ Volver", callback_data="shop")
        ])

        await render(update, "🔀 <b>Selecciona plan</b>", btns)

    # ===== COMPRA =====
    elif q.data.startswith("confirm_"):
        vid = int(q.data.split("_")[1])
        context.user_data["buy_vid"] = vid

        cursor.execute("SELECT name, price FROM variants WHERE id=?", (vid,))
        v = cursor.fetchone()

        await render(update, f"🛒 <b>Confirmar compra</b>\n\n{v[0]}\n💰 <code>${v[1]:.2f}</code>", [
            [InlineKeyboardButton("🟢 Comprar", callback_data="do_buy")],
            [InlineKeyboardButton("🔴 Cancelar", callback_data="shop")]
        ])

    elif q.data == "do_buy":
        vid = context.user_data.get("buy_vid")

        # 🔎 buscar precio personalizado
        cursor.execute(
            "SELECT price FROM user_prices WHERE user_id=? AND variant_id=?",
            (uid, vid)
        )
        custom = cursor.fetchone()

        if custom:
            price = custom[0]
        else:
            cursor.execute("SELECT price, delivery_type FROM variants WHERE id=?", (vid,))
        row = cursor.fetchone()

        price = row[0]
        delivery_type = row[1]

        if delivery_type == "manual_ip":
            context.user_data["waiting_ip"] = True
            context.user_data["buy_vid"] = vid

            await render(
                update,
                "🌐 <b>Activación requerida</b>\n\nEnvía tu IP para activar el servicio.",
                []
            )
            return

        cursor.execute("SELECT saldo FROM users WHERE user_id=?", (uid,))
        saldo = cursor.fetchone()[0]

        cursor.execute("SELECT saldo FROM users WHERE user_id=?", (uid,))
        saldo = cursor.fetchone()[0]

        if saldo < price:
            await q.answer("💳 Saldo insuficiente")
            return

        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("SELECT id, content FROM stock WHERE variant_id=? LIMIT 1", (vid,))
        item = cursor.fetchone()

        if not item:
            conn.commit()
            await q.answer("❌ Sin stock disponible")
            return

        
        conn.commit()

        # ===== GUARDAR HISTORIAL =====
        cursor.execute("""
        SELECT p.name, v.name FROM variants v
        JOIN products p ON v.product_id = p.id
        WHERE v.id=?
        """, (vid,))
        product_name, variant_name = cursor.fetchone()

        cursor.execute("SELECT username FROM users WHERE user_id=?", (uid,))
        username = cursor.fetchone()[0]

        cursor.execute("""
        INSERT INTO history (user_id, username, product_name, variant_name, price, content, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (uid, username, product_name, variant_name, price, item[1], 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        # ===== PROCESAR COMPRA =====
        cursor.execute("DELETE FROM stock WHERE id=?", (item[0],))
        cursor.execute("UPDATE users SET saldo = saldo - ? WHERE user_id=?", (price, uid))
        conn.commit()

        ticket = f"""🎫 <b>TICKET DE COMPRA</b>

━━━━━━━━━━━━━━
📦 <b>{product_name}</b>
🔀 <b>{variant_name}</b>
💰 <b>${price:.2f}</b>
━━━━━━━━━━━━━━

🔑 <b>ACCESO:</b>
<code>{item[1]}</code>

━━━━━━━━━━━━━━
⚠️ <i>No compartir tu acceso</i>"""

        try:
            await context.bot.send_message(chat_id=uid, text=ticket, parse_mode="HTML")

            admin_msg = f"""🛒 <b>NUEVA COMPRA</b>

👤 ID: <code>{uid}</code>
📦 {product_name}
🔀 {variant_name}
💰 ${price:.2f}

{ticket}"""

            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(chat_id=admin_id, text=admin_msg, parse_mode="HTML")
                except:
                    pass

        except:
            await render(update, "❌ Abre el bot en privado", main_menu(uid))
            return

        await render(update, "✅ <b>Compra exitosa!</b>\n📩 Revisa mensajes privados\n📋 Ver historial", main_menu(uid))

    # ===== ADMIN =====
    elif q.data == "admin":
        if not is_admin(uid):
            await q.answer("❌ No eres admin")
            return

        # ===== ESTADÍSTICAS =====
        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM history")
        compras = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(price) FROM history")
        total = cursor.fetchone()[0] or 0

        texto = f"""👑 <b>PANEL ADMIN</b>

📊 <b>Estadísticas</b>
━━━━━━━━━━━━━━
👥 Usuarios: <code>{users}</code>
🛒 Compras: <code>{compras}</code>
💰 Ventas: <code>${total:.2f}</code>
━━━━━━━━━━━━━━
"""

        await render(update, texto, [
            [InlineKeyboardButton("📦 Productos", callback_data="ap")],
            [InlineKeyboardButton("👥 Usuarios", callback_data="users")],
            [InlineKeyboardButton("📊 Historial", callback_data="admin_history")],
            [InlineKeyboardButton("⬅️ Menú", callback_data="menu")]
        ])

    elif q.data == "admin_history":
        if not is_admin(uid): return
            
        cursor.execute("SELECT username, product_name, variant_name, price, date FROM history ORDER BY date DESC LIMIT 15")
        compras = cursor.fetchall()

        if not compras:
            await render(update, "📊 <b>No hay historial</b>", [[InlineKeyboardButton("⬅️ Admin", callback_data="admin")]])
            return

        historial_text = "📊 <b>ÚLTIMAS COMPRAS</b>\n\n"
        for compra in compras:
            historial_text += f"""👤 <code>{compra[0]}</code>
📦 {compra[1]} - {compra[2]}
💰 <code>${compra[3]:.2f}</code> | 📅 <code>{compra[4][:16]}</code>
━━━━━━━━━━━━━━"""
        
        await render(update, historial_text, [[InlineKeyboardButton("⬅️ Admin", callback_data="admin")]])

    # ===== ADMIN USUARIOS/PRODUCTOS (igual que antes) =====
    elif q.data == "users":
        if not is_admin(uid): return
        cursor.execute("SELECT username FROM users")
        users = cursor.fetchall()
        if not users:
            await render(update, "👥 <b>No hay usuarios</b>", [[InlineKeyboardButton("⬅️ Admin", callback_data="admin")]])
            return
        btns = [[InlineKeyboardButton(u[0], callback_data=f"user_{u[0]}")] for u in users]
        btns.append([InlineKeyboardButton("⬅️ Admin", callback_data="admin")])
        await render(update, "👥 <b>Usuarios</b>", btns)

    elif q.data.startswith("user_"):
        if not is_admin(uid): 
            return

        target = q.data.replace("user_", "")
        context.user_data["target"] = target

        cursor.execute("SELECT saldo, user_id FROM users WHERE username=?", (target,))
        data = cursor.fetchone()

        saldo = data[0]
        target_id = data[1]

        context.user_data["target_id"] = target_id

        await render(
            update,
            f"👤 <b>{target}</b>\n💰 <b>Saldo:</b> <code>${saldo:.2f}</code>",
            [
                [InlineKeyboardButton("💰 ➕ Agregar saldo", callback_data="addsaldo")],
                [InlineKeyboardButton("💸 Precio especial", callback_data="set_price_user")],
                [InlineKeyboardButton("⬅️ Usuarios", callback_data="users")]
            ]
        )
    elif q.data == "set_price_user":
        if not is_admin(uid):
            return

        cursor.execute("""
        SELECT v.id, p.name, v.name
        FROM variants v
        JOIN products p ON v.product_id = p.id
        """)
        data = cursor.fetchall()

        btns = []
        for d in data:
            btns.append([
                InlineKeyboardButton(f"{d[1]} - {d[2]}", callback_data=f"setprice_{d[0]}")
            ])

        btns.append([InlineKeyboardButton("⬅️ Volver", callback_data="users")])

        await render(update, "💸 <b>Selecciona variante</b>", btns)      
        
    elif q.data.startswith("setprice_"):
        if not is_admin(uid):
            return

        vid = int(q.data.split("_")[1])
        context.user_data["set_vid"] = vid
        context.user_data["state"] = "set_price_user"

        await render(update, "💰 <b>Nuevo precio para este usuario:</b>", [])                            
    
    elif q.data == "addsaldo":
        if not is_admin(uid): return
        context.user_data["state"] = "addsaldo"
        await render(update, "💰 <b>Monto a agregar:</b>", [])

    elif q.data == "ap":
        if not is_admin(uid): return
        cursor.execute("SELECT id, name FROM products")
        products = cursor.fetchall()
        btns = [[InlineKeyboardButton(p[1], callback_data=f"ap_{p[0]}")] for p in products]
        btns.append([InlineKeyboardButton("➕ Nuevo producto", callback_data="newp")])
        btns.append([InlineKeyboardButton("⬅️ Admin", callback_data="admin")])
        await render(update, "📦 <b>Productos</b>", btns)

    elif q.data == "newp":
        if not is_admin(uid): return
        context.user_data["state"] = "newp"
        await render(update, "📦 <b>Nombre del producto:</b>", [])

    elif q.data.startswith("ap_"):
        if not is_admin(uid): return
        pid = int(q.data.split("_")[1])
        context.user_data["pid"] = pid
        cursor.execute("SELECT id, name FROM variants WHERE product_id=?", (pid,))
        variants = cursor.fetchall()
        btns = [[InlineKeyboardButton(v[1], callback_data=f"v_{v[0]}")] for v in variants]
        btns.append([InlineKeyboardButton("➕ Nueva variante", callback_data="newv")])
        btns.append([InlineKeyboardButton("⬅️ Productos", callback_data="ap")])
        await render(update, "🔀 <b>Variantes</b>", btns)

    elif q.data == "newv":
        if not is_admin(uid):
            return

        await render(
            update,
            "⚙️ <b>Tipo de entrega</b>",
            [
                [InlineKeyboardButton("⚡ Automático", callback_data="type_auto")],
                [InlineKeyboardButton("🌐 Proxy (IP)", callback_data="type_manual")]
            ]
        )


    elif q.data == "type_auto":
        context.user_data["delivery_type"] = "auto"
        context.user_data["state"] = "newv"

        await render(
            update,
            "🔀 <b>Nombre de la variante:</b>",
            []
        )


    elif q.data == "type_manual":
        context.user_data["delivery_type"] = "manual_ip"
        context.user_data["state"] = "newv"

        await render(
            update,
            "🔀 <b>Nombre de la variante:</b>",
            []
        )

    elif q.data.startswith("v_"):
        if not is_admin(uid): return
        vid = int(q.data.split("_")[1])
        context.user_data["vid"] = vid
        await render(update, "⚙️ <b>Opciones</b>", [
            [InlineKeyboardButton("➕ Stock", callback_data="stock")],
            [InlineKeyboardButton("💰 Precio", callback_data="price")],
            [InlineKeyboardButton("⬅️ Volver", callback_data=f"ap_{context.user_data.get('pid', 0)}")]
        ])

    elif q.data == "stock":
        if not is_admin(uid): return
        context.user_data["state"] = "stock"
        await render(update, "🔑 <b>Keys (una por línea):</b>", [])

    elif q.data == "price":
        if not is_admin(uid): return
        context.user_data["state"] = "price"
        await render(update, "💰 <b>Nuevo precio:</b>", [])


    elif q.data.startswith("approve_"):
        _, user_id, vid = q.data.split("_")
        user_id = int(user_id)
        vid = int(vid)

        cursor.execute("SELECT id, content FROM stock WHERE variant_id=? LIMIT 1", (vid,))
        item = cursor.fetchone()

        if not item:
            await q.answer("❌ Sin stock")
            return

        cursor.execute("""
        SELECT p.name, v.name, v.price FROM variants v
        JOIN products p ON v.product_id = p.id
        WHERE v.id=?
        """, (vid,))
        product_name, variant_name, price = cursor.fetchone()

        cursor.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
        username = cursor.fetchone()[0]

        cursor.execute("""
        INSERT INTO history (user_id, username, product_name, variant_name, price, content, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            username,
            product_name,
            variant_name,
            price,
            item[1],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        cursor.execute("DELETE FROM stock WHERE id=?", (item[0],))
        conn.commit()

        await context.bot.send_message(
            chat_id=user_id,
            text=f"""✅ <b>Activación completada</b>

📦 {product_name}
🔀 {variant_name}

🔑 <b>Acceso:</b>
<code>{item[1]}</code>
""",
            parse_mode="HTML"
        )

        await q.answer("Activado")


    elif q.data.startswith("reject_"):
        _, user_id, vid = q.data.split("_")
        user_id = int(user_id)

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Tu IP no pudo ser activada. Contacta soporte."
        )

        await q.answer("Rechazado")

# ===== HANDLE MENSAJES =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    
    state = context.user_data.get("state")
    waiting_ip = context.user_data.get("waiting_ip")

    if not state and not waiting_ip:
        return

    text = update.message.text.strip()
    parts = text.split()

    if waiting_ip:
        ip = text

        vid = context.user_data.get("buy_vid")

        cursor.execute("""
        SELECT p.name, v.name FROM variants v
        JOIN products p ON v.product_id = p.id
        WHERE v.id=?
        """, (vid,))
        product_name, variant_name = cursor.fetchone()

        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"""🆕 <b>Activación requerida</b>

👤 ID: <code>{uid}</code>
📦 {product_name}
🔀 {variant_name}

🌐 IP:
<code>{ip}</code>
""",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Activar", callback_data=f"approve_{uid}_{vid}"),
                        InlineKeyboardButton("❌ Rechazar", callback_data=f"reject_{uid}_{vid}")
                    ]
                ]),
                parse_mode="HTML"
            )

        context.user_data.clear()

        await update.message.reply_text("⏳ IP enviada. Espera activación.")
        return
        
    elif state == "newv":
        pid = context.user_data.get("pid")
        delivery_type = context.user_data.get("delivery_type", "auto")

        if not pid:
            await update.message.reply_text("❌ Error: producto no seleccionado")
            return

        cursor.execute(
            "INSERT INTO variants (product_id, name, delivery_type) VALUES (?, ?, ?)",
            (pid, text, delivery_type)
        )
        conn.commit()

        context.user_data.clear()

        await update.message.reply_text("✅ Variante creada")

    if state == "register":
        if len(parts) != 2:
            await update.message.reply_text("usuario contraseña")
            return
        u, p = parts
        cursor.execute("SELECT 1 FROM users WHERE username=?", (u,))
        if cursor.fetchone():
            await update.message.reply_text("❌ Usuario existe")
            return
        cursor.execute("INSERT INTO users (user_id, username, password, session) VALUES (?, ?, ?, 1)", (uid, u, p))
        conn.commit()
        context.user_data.clear()
        await update.message.reply_text("✅ Registrado", reply_markup=kb(main_menu(uid)))

    elif state == "login":
        if len(parts) != 2:
            await update.message.reply_text("usuario contraseña")
            return
        u, p = parts
        cursor.execute("SELECT estado FROM users WHERE username=? AND password=?", (u, p))
        d = cursor.fetchone()
        if not d or d[0] != "activo":
            await update.message.reply_text("❌ Datos incorrectos")
            return
        cursor.execute("UPDATE users SET session=1 WHERE username=?", (u,))
        conn.commit()
        context.user_data.clear()
        await update.message.reply_text("✅ Login exitoso", reply_markup=kb(main_menu(uid)))

    elif state == "addsaldo":
        try:
            amount = float(text)
            target = context.user_data.get("target")
            cursor.execute("UPDATE users SET saldo = saldo + ? WHERE username=?", (amount, target))
            conn.commit()
            context.user_data.clear()
            await update.message.reply_text(f"✅ +${amount:.2f} a {target}")
        except:
            await update.message.reply_text("❌ Número inválido")

    elif state == "newp":
        cursor.execute("INSERT INTO products (name) VALUES (?)", (text,))
        conn.commit()
        context.user_data.clear()
        await update.message.reply_text("✅ Producto creado")

    elif state == "set_price_user":
        try:
            price = float(text)

            target_id = context.user_data.get("target_id")
            vid = context.user_data.get("set_vid")

            cursor.execute(
                "SELECT id FROM user_prices WHERE user_id=? AND variant_id=?",
                (target_id, vid)
            )
            exists = cursor.fetchone()

            if exists:
                cursor.execute(
                    "UPDATE user_prices SET price=? WHERE user_id=? AND variant_id=?",
                    (price, target_id, vid)
                )
            else:
                cursor.execute(
                    "INSERT INTO user_prices (user_id, variant_id, price) VALUES (?, ?, ?)",
                    (target_id, vid, price)
                )

            conn.commit()
            context.user_data.clear()

            await update.message.reply_text("✅ Precio personalizado guardado")

        except:
            await update.message.reply_text("❌ Precio inválido")

    elif state == "stock":
        vid = context.user_data["vid"]
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        count = 0
        for line in lines:
            cursor.execute("INSERT INTO stock (variant_id, content) VALUES (?, ?)", (vid, line))
            count += 1
        conn.commit()
        context.user_data.clear()
        await update.message.reply_text(f"✅ {count} keys agregadas")

    elif state == "price":
        try:
            vid = context.user_data["vid"]
            cursor.execute("UPDATE variants SET price=? WHERE id=?", (float(text), vid))
            conn.commit()
            context.user_data.clear()
            await update.message.reply_text(f"✅ Precio: ${float(text):.2f}")
        except:
            await update.message.reply_text("❌ Número inválido")

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🔥 BOT INICIADO")
    app.run_polling()

if __name__ == "__main__":
    main()
