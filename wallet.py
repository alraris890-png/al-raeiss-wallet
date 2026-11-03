import sqlite3
import re
import os
from datetime import datetime
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = "8727547966:AAHBpW-sKdqYGUtd8zSESMOogNqh2nSQFYQ"
ADMIN_USER_ID = 8822051394
CHANNEL_USERNAME = "@al_raeiss210"
CHANNEL_LINK = "https://t.me/al_raeiss210"

web_app = Flask('')

@web_app.route('/')
def home():
    return "AL.RAEISS Wallet Bot is active and running 24/7! 🏛️"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

def init_db():
    conn = sqlite3.connect("wallet_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            login_pass TEXT,
            withdraw_pass TEXT,
            phone TEXT,
            usd_balance REAL DEFAULT 0.0,
            syp_balance REAL DEFAULT 0.0,
            usdt_balance REAL DEFAULT 0.0,
            admin_usd_profit REAL DEFAULT 0.0,
            admin_syp_profit REAL DEFAULT 0.0,
            admin_usdt_profit REAL DEFAULT 0.0,
            step TEXT,
            last_active TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            currency TEXT,
            amount REAL,
            gateway TEXT,
            reference_code TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            rating INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect("wallet_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, login_pass, withdraw_pass, phone, usd_balance, syp_balance, usdt_balance, admin_usd_profit, admin_syp_profit, admin_usdt_profit, step, last_active FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_user_step(user_id, step):
    conn = sqlite3.connect("wallet_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET step = ?, last_active = ? WHERE user_id = ?", (step, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def update_balances(user_id, usd_change=0.0, syp_change=0.0, usdt_change=0.0, profit_usd=0.0, profit_syp=0.0, profit_usdt=0.0):
    conn = sqlite3.connect("wallet_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET 
            usd_balance = usd_balance + ?, 
            syp_balance = syp_balance + ?, 
            usdt_balance = usdt_balance + ?, 
            admin_usd_profit = admin_usd_profit + ?, 
            admin_syp_profit = admin_syp_profit + ?, 
            admin_usdt_profit = admin_usdt_profit + ?, 
            last_active = ? 
        WHERE user_id = ?
    """, (usd_change, syp_change, usdt_change, profit_usd, profit_syp, profit_usdt, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False

async def set_commands(app):
    commands = [
        BotCommand("start", "تشغيل المحفظة والقائمة الرئيسية 🚀")
    ]
    await app.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة الآن (مجانـاً)", url=CHANNEL_LINK)],
            [InlineKeyboardButton("🔄 تحقق من اشتراكي", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_text = (
            "🌹 أهلاً بك يا منوّرنا!\n\n"
            f"🆔 معرف حسابك الشخصي (ID): `{user_id}`\n\n"
            "يسعدنا انضمامك إلينا. للانتقال إلى محفظتك والاستفادة من كافة الخدمات بشكل مجاني بالكامل، نرجو منك الانضمام إلى قناتنا الرسمية 🌸\n\n"
            "بعد الانضمام، اضغط على زر التحقق بالأسفل:"
        )
        if update.callback_query:
            await update.callback_query.message.edit_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
        return

    user = get_user(user_id)
    if user and user[1]: 
        update_user_step(user_id, 'LOGGED_IN')
        await show_main_menu(update, context)
    else:
        conn = sqlite3.connect("wallet_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (user_id, usd_balance, syp_balance, usdt_balance, admin_usd_profit, admin_syp_profit, admin_usdt_profit, step, last_active) VALUES (?, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 'WAITING_NAME', ?)", (user_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        msg = (
            f"🆔 معرف حسابك الشخصي (ID): `{user_id}`\n\n"
            "🌐 مرحباً بك في محفظة al.raeiss الرقمية الآمنة\n\n"
            "👤 يرجى إدخال الاسم الكامل الخاص بك للبدء:"
        )
        if update.callback_query:
            await update.callback_query.message.edit_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    usd = user[5] if user else 0.0
    syp = user[6] if user else 0.0
    usdt = user[7] if user else 0.0

    text = (
        "🌌 𝕬𝖑.𝖗𝖆𝖊𝖎𝖘𝖘 𝖂𝖆𝖑𝖑𝖊𝖙 🌌\n"
        "┏━━━━━━━ 𝗕𝗢𝗧 ━━━━━━━┓\n"
        "┃   💥 **محفظة al.raeiss** 💥   ┃\n"
        "┗━━━━━━━━━━━━━━━━━━┛\n\n"
        f"🆔 معرف الحساب: `{user_id}`\n\n"
        "💼 **لوحة تحكم المحفظة الرئيسية**\n\n"
        f"💎 رصيد USDT: `{usdt:.2f} USDT`\n"
        f"💵 رصيد الدولار: `{usd:.2f} USD`\n"
        f"🥏 رصيد الليرة السورية: `{syp:,.2f} SYP`\n\n"
        "اختر العملية المطلوبة أدناه 👇\n\n"
        "░░░░░░░░░░░░░░░░░░░░\n"
        "▫️ `[ محمد شادي ℳᥫ᭡. ]` ▫️"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📥 إيداع وتعبئة", callback_data="deposit"),
            InlineKeyboardButton("📤 سحب للخارج", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("🔄 تحويل لحساب آخر", callback_data="transfer"),
            InlineKeyboardButton("⭐ تقييم الخدمة", callback_data="rate_service")
        ],
        [
            InlineKeyboardButton("🗂️ محفظة المدير والأرباح", callback_data="admin_wallet") if user_id == ADMIN_USER_ID else InlineKeyboardButton("📖 دليل الاستخدام", callback_data="guide")
        ]
    ]
    if user_id == ADMIN_USER_ID:
        keyboard.append([InlineKeyboardButton("📖 دليل الاستخدام", callback_data="guide")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

def validate_login_password(password):
    if len(password) < 10:
        return False
    has_upper = bool(re.search(r'[A-Z]', password))
    lower_count = len(re.findall(r'[a-z]', password))
    digit_count = len(re.findall(r'[0-9]', password))
    symbol_count = len(re.findall(r'[\W_]', password))
    return has_upper and (lower_count >= 4) and (digit_count >= 4) and (symbol_count >= 1)

def validate_withdraw_password(password):
    letter_count = len(re.findall(r'[a-zA-Z]', password))
    digit_count = len(re.findall(r'[0-9]', password))
    return (letter_count >= 3) and (digit_count >= 3)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user = get_user(user_id)

    if not user:
        await start(update, context)
        return

    step = user[10]

    if step == 'WAITING_NAME':
        context.user_data['temp_name'] = text
        update_user_step(user_id, 'WAITING_LOGIN_PASS')
        await update.message.reply_text(
            f"🆔 معرف حسابك: `{user_id}`\n\n"
            "🔐 إنشاء كلمة سر التسجيل:\n\n"
            "يجب أن تحتوي على:\n"
            "• حرف كبير واحد على الأقل (A-Z)\n"
            "• 4 أحرف صغيرة على الأقل (a-z)\n"
            "• 4 أرقام على الأقل (0-9)\n"
            "• رمز خاص واحد على الأقل (مثل @, #, $, !)\n\n"
            "أدخل كلمة سر التسجيل الآن:",
            parse_mode="Markdown"
        )

    elif step == 'WAITING_LOGIN_PASS':
        if not validate_login_password(text):
            await update.message.reply_text("❌ كلمة سر التسجيل لا توفي بالشروط المطلوبة (حرف كبير، 4 أحرف صغيرة، 4 أرقام، ورمز واحد). حاول مجدداً:")
            return
        context.user_data['temp_login_pass'] = text
        update_user_step(user_id, 'WAITING_WITHDRAW_PASS')
        await update.message.reply_text("🔒 إنشاء كلمة سر الشحن والسحب:\n\nيجب أن تحتوي على 3 أحرف و3 أرقام على الأقل (يسمح بالزيادة).\nأدخل كلمة السر الجديدة:")

    elif step == 'WAITING_WITHDRAW_PASS':
        if not validate_withdraw_password(text):
            await update.message.reply_text("❌ كلمة سر الشحن يجب ألا تقل عن 3 أحرف و3 أرقام. حاول مجدداً:")
            return
        login_pass = context.user_data.get('temp_login_pass')
        if text == login_pass:
            await update.message.reply_text("❌ يجب أن تختلف كلمة سر الشحن عن كلمة سر التسجيل لأسباب أمنية! أدخل كلمة سر أخرى:")
            return
        context.user_data['temp_withdraw_pass'] = text
        update_user_step(user_id, 'WAITING_PHONE')
        await update.message.reply_text("📱 أخيراً، يرجى إدخال رقم الهاتف الخاص بك:")

    elif step == 'WAITING_PHONE':
        name = context.user_data.get('temp_name')
        l_pass = context.user_data.get('temp_login_pass')
        w_pass = context.user_data.get('temp_withdraw_pass')
        phone = text

        conn = sqlite3.connect("wallet_database.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET username = ?, login_pass = ?, withdraw_pass = ?, phone = ?, step = 'LOGGED_IN', last_active = ? WHERE user_id = ?
        """, (name, l_pass, w_pass, phone, datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            "✅ تم إنشاء وتفعيل حسابك وحمايته بنجاح!\n\n"
            "⚠️ **تنبيه أمني هام جداً:**\n"
            "حسابك وأرصدتك هي تحت **مسؤوليتك الشخصية الكاملة**. يُمنع منعاً باتاً مشاركة كلمة السر الخاصة بك مع أي شخص كان لتفادي سرقة أو ضياع أموالك وأرصدتك داخل المحفظة!",
            parse_mode="Markdown"
        )
        await show_main_menu(update, context)

    elif step == 'DEPOSIT_AMOUNT':
        try:
            amount = float(text)
            curr = context.user_data.get('dep_curr')
            
            if curr in ['USDT', 'USD'] and amount < 1.5:
                await update.message.reply_text(f"❌ الحد الأدنى لشحن {curr} هو 1.5. أدخل مبلغاً صالحاً:")
                return
            elif curr == 'SYP' and amount < 87650:
                await update.message.reply_text("❌ الحد الأدنى لشحن الليرة السورية هو 87,650 SYP. أدخل مبلغاً صالحاً:")
                return
            
            if amount <= 0:
                raise ValueError()

            context.user_data['dep_amount'] = amount
            update_user_step(user_id, 'DEPOSIT_TXID')
            gateway = context.user_data.get('dep_gateway')
            
            await update.message.reply_text(
                "📥 أمان الإيداع وتأكيد العملية:\n\n"
                f"🆔 معرف حسابك: `{user_id}`\n"
                f"قم بتحويل المبلغ المطلوب عبر ({gateway}) للعملة ({curr}).\n"
                "ثم أدخل الآن رقم العملية أو المعرف المالي (TXID / رقم الإيصال) بدقة تامة لتفادي أي ضياع للأموال:",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("❌ مبلغ غير صالح. أدخل رقماً صحيحاً:")

    elif step == 'DEPOSIT_TXID':
        txid = text
        amount = context.user_data.get('dep_amount')
        gateway = context.user_data.get('dep_gateway')
        curr = context.user_data.get('dep_curr')

        conn = sqlite3.connect("wallet_database.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, gateway, reference_code, status)
            VALUES (?, 'DEPOSIT', ?, ?, ?, ?, 'PENDING')
        """, (user_id, curr, amount, gateway, txid))
        conn.commit()
        conn.close()

        update_user_step(user_id, 'LOGGED_IN')
        await update.message.reply_text(
            "🛡️ تم استلام طلب الإيداع وتوثيقه بأمان تام!\n\n"
            f"🆔 معرف حسابك الخاص: `{user_id}`\n"
            f"المبلغ: `{amount} {curr}`\n"
            f"البوابة: `{gateway}`\n"
            f"رقم المعرف: `{txid}`\n\n"
            "⏳ جاري التحقق من العملية وإضافة الرصيد لحسابك فور التأكيد.",
            parse_mode="Markdown"
        )
        await show_main_menu(update, context)

    elif step == 'WITHDRAW_AMOUNT':
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError()
            context.user_data['w_amount'] = amount
            update_user_step(user_id, 'WITHDRAW_PASS_CHECK')
            await update.message.reply_text("🔒 أدخل كلمة سر الشحن والسحب الخاصة بك للتأكيد:")
        except ValueError:
            await update.message.reply_text("❌ مبلغ غير صالح. أدخل رقماً صحيحاً:")

    elif step == 'WITHDRAW_PASS_CHECK':
        if text == user[2]:
            amount = context.user_data.get('w_amount', 0)
            curr = context.user_data.get('w_curr', 'USD')
            
            if curr == 'USDT':
                if user[7] < amount:
                    await update.message.reply_text("❌ رصيدك من USDT لا يكفي.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                fee = amount * 0.007
                net = amount - fee
                update_balances(user_id, usdt_change=-amount, profit_usdt=fee)
                msg = f"✅ تم تقديم طلب السحب:\n🆔 معرف الحساب: `{user_id}`\nالمبلغ: `{net:.2f} USDT`\nالرسوم: `{fee:.2f} USDT`"
            elif curr == 'USD':
                if user[5] < amount:
                    await update.message.reply_text("❌ رصيدك من الدولار لا يكفي.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                fee = amount * 0.02
                net = amount - fee
                update_balances(user_id, usd_change=-amount, profit_usd=fee)
                msg = f"✅ تم تقديم طلب السحب:\n🆔 معرف الحساب: `{user_id}`\nالمبلغ: `{net:.2f} USD`\nالرسوم: `{fee:.2f} USD`"
            else:
                if user[6] < amount:
                    await update.message.reply_text("❌ رصيدك من الليرة السورية لا يكفي.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                fee = amount * 0.02
                net = amount - fee
                update_balances(user_id, syp_change=-amount, profit_syp=fee)
                msg = f"✅ تم تقديم طلب السحب:\n🆔 معرف الحساب: `{user_id}`\nالمبلغ: `{net:,.2f} SYP`\nالرسوم: `{fee:,.2f} SYP`"

            update_user_step(user_id, 'LOGGED_IN')
            await update.message.reply_text(msg, parse_mode="Markdown")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ كلمة سر السحب خاطئة! تم إلغاء العملية.")
            update_user_step(user_id, 'LOGGED_IN')
            await show_main_menu(update, context)

    elif step == 'TRANSFER_ID':
        try:
            target_id = int(text)
            target_user = get_user(target_id)
            if not target_user:
                await update.message.reply_text("❌ المستخدم غير موجود بالنظام. أدخل ID صحيح:")
                return
            if target_id == user_id:
                await update.message.reply_text("❌ لا يمكنك التحويل لنفسك! أدخل ID آخر:")
                return
            context.user_data['t_target'] = target_id
            update_user_step(user_id, 'TRANSFER_AMOUNT')
            await update.message.reply_text("💵 أدخل المبلغ المراد تحويله:")
        except ValueError:
            await update.message.reply_text("❌ ID غير صالح. أدخل أرقاماً فقط:")

    elif step == 'TRANSFER_AMOUNT':
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError()
            context.user_data['t_amount'] = amount
            update_user_step(user_id, 'TRANSFER_PASS_CHECK')
            await update.message.reply_text("🔒 أدخل كلمة سر الشحن والسحب الخاصة بك لتأكيد التحويل:")
        except ValueError:
            await update.message.reply_text("❌ مبلغ غير صالح. أدخل رقماً صحيحاً:")

    elif step == 'TRANSFER_PASS_CHECK':
        if text == user[2]:
            amount = context.user_data.get('t_amount', 0)
            target_id = context.user_data.get('t_target')
            curr = context.user_data.get('t_curr', 'USD')

            fee = amount * 0.0035
            net = amount - fee

            if curr == 'USDT':
                if user[7] < amount:
                    await update.message.reply_text("❌ رصيدك لا يكفي.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, usdt_change=-amount)
                update_balances(target_id, usdt_change=net)
                update_balances(ADMIN_USER_ID, profit_usdt=fee)
            elif curr == 'USD':
                if user[5] < amount:
                    await update.message.reply_text("❌ رصيدك لا يكفي.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, usd_change=-amount)
                update_balances(target_id, usd_change=net)
                update_balances(ADMIN_USER_ID, profit_usd=fee)
            else:
                if user[6] < amount:
                    await update.message.reply_text("❌ رصيدك لا يكفي.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, syp_change=-amount)
                update_balances(target_id, syp_change=net)
                update_balances(ADMIN_USER_ID, profit_syp=fee)

            update_user_step(user_id, 'LOGGED_IN')
            await update.message.reply_text(f"✅ تم التحويل بنجاح من حسابك ({user_id}) إلى الحساب ({target_id}) بقيمة `{net:.2f}` مع احتساب الرسوم (0.35%).", parse_mode="Markdown")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ كلمة سر السحب خاطئة! تم إلغاء العملية.")
            update_user_step(user_id, 'LOGGED_IN')
            await show_main_menu(update, context)

    elif step == 'ADMIN_W_AMOUNT':
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError()
            context.user_data['admin_w_amount'] = amount
            update_user_step(user_id, 'ADMIN_W_PASS')
            await update.message.reply_text("🔒 أدخل كلمة سر الشحن الخاصة بحساب المدير للتأكيد:")
        except ValueError:
            await update.message.reply_text("❌ مبلغ غير صالح:")

    elif step == 'ADMIN_W_PASS':
        if text == user[2]:
            amount = context.user_data.get('admin_w_amount', 0)
            curr = context.user_data.get('admin_w_curr', 'USDT')

            if curr == 'USDT':
                if user[9] < amount:
                    await update.message.reply_text("❌ رصيد أرباح USDT لمحفظة المدير لا يكفي.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, profit_usdt=-amount)
                msg = f"✅ تم سحب أرباح المدير بنجاح بقيمة `{amount:.2f} USDT`"
            elif curr == 'USD':
                if user[7] < amount:
                    await update.message.reply_text("❌ رصيد أرباح USD لمحفظة المدير لا يكفي.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, profit_usd=-amount)
                msg = f"✅ تم سحب أرباح المدير بنجاح بقيمة `{amount:.2f} USD`"
            else:
                if user[8] < amount:
                    await update.message.reply_text("❌ رصيد أرباح SYP لمحفظة المدير لا يكفي.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, profit_syp=-amount)
                msg = f"✅ تم سحب أرباح المدير بنجاح بقيمة `{amount:,.2f} SYP`"

            update_user_step(user_id, 'LOGGED_IN')
            await update.message.reply_text(msg, parse_mode="Markdown")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ كلمة سر الشحن غير صحيحة!")
            update_user_step(user_id, 'LOGGED_IN')
            await show_main_menu(update, context)

    else:
        await update.message.reply_text(f"أهلاً بك يا بطل! لقد استلمت رسالتك: '{text}'. استخدم القائمة الرئيسية للتحكم بالمحفظة بكل أمان 🌟")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    if query.data == "check_sub":
        is_sub = await check_subscription(user_id, context)
        if is_sub:
            await start(update, context)
        else:
            await query.answer("🌸 عذراً، لم تقم بالاشتراك بالقناة بعد. يرجى الاشتراك ثم الضغط على التحقق مجدداً!", show_alert=True)
        return

    if query.data == "rate_service":
        keyboard = [
            [
                InlineKeyboardButton("⭐ 1", callback_data="rate_1"),
                InlineKeyboardButton("⭐⭐ 2", callback_data="rate_2"),
                InlineKeyboardButton("⭐⭐⭐ 3", callback_data="rate_3")
            ],
            [
                InlineKeyboardButton("⭐⭐⭐⭐ 4", callback_data="rate_4"),
                InlineKeyboardButton("⭐⭐⭐⭐⭐ 5", callback_data="rate_5")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🌟 ما مدى رضاك عن خدمتنا؟ اختر تقييمك من 5 نجوم:", reply_markup=reply_markup)
        return

    if query.data.startswith("rate_"):
        score = int(query.data.split("_")[1])
        conn = sqlite3.connect("wallet_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ratings (user_id, rating) VALUES (?, ?)", (user_id, score))
        conn.commit()
        conn.close()
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"❤️ شكراً لك على تقييمك بـ {score} نجوم! رأيك يهمنا ويساعدنا على التطوير.", reply_markup=reply_markup)
        return

    if query.data == "main_menu":
        update_user_step(user_id, 'LOGGED_IN')
        await show_main_menu(update, context)
        return

    if query.data == "guide":
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "📖 الدليل الشامل لاستخدام محفظة al.raeiss:\n\n"
            f"🆔 معرف الحساب: `{user_id}`\n"
            "1️⃣ الأمان الصارم: كلمة سر تسجيل متكاملة، وكلمة سر شحن مستقلة.\n"
            "2️⃣ الإيداع والتحويل: توثيق آمن للمعاملات عبر معرفات الـ TXID.\n",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if query.data == "deposit":
        keyboard = [
            [InlineKeyboardButton("🔹 Sham Cash (SYP)", callback_data="sham_syp")],
            [InlineKeyboardButton("🔹 Sham Cash (USD)", callback_data="sham_usd")],
            [InlineKeyboardButton("🟢 Syriatel Cash", callback_data="syriatel_all")],
            [InlineKeyboardButton("💎 USDT - TRC20", callback_data="usdt_trc")],
            [InlineKeyboardButton("💎 USDT - BEP20", callback_data="usdt_bep")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📥 **اختر طريقة الشحن والإيداع المناسبة:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data in ["sham_syp", "sham_usd", "syriatel_all", "usdt_trc", "usdt_bep"]:
        gateway_map = {
            "sham_syp": ("شام كاش (SYP)", "SYP"),
            "sham_usd": ("شام كاش (USD)", "USD"),
            "syriatel_all": ("سريتل كاش", "USD"),
            "usdt_trc": ("USDT - TRC20", "USDT"),
            "usdt_bep": ("USDT - BEP20", "USDT")
        }
        gateway, curr = gateway_map[query.data]
        context.user_data['dep_gateway'] = gateway
        context.user_data['dep_curr'] = curr
        update_user_step(user_id, 'DEPOSIT_AMOUNT')
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="deposit")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        min_msg = "1.5" if curr in ["USD", "USDT"] else "87,650"
        await query.message.edit_text(
            f"📥 بوابة الإيداع الآمن عبر {gateway} ({curr}):\n\n"
            f"⚠️ الحد الأدنى للشحن: `{min_msg} {curr}`\n"
            "حساب التحويل المعتمد للإدارة:\n`987654321`\n\n"
            "💵 أدخل الآن المبلغ الذي قمت بتحويله:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif query.data == "withdraw":
        keyboard = [
            [InlineKeyboardButton("💎 سحب USDT", callback_data="w_usdt")],
            [InlineKeyboardButton("💵 سحب دولار USD", callback_data="w_usd")],
            [InlineKeyboardButton("🥏 سحب ليرة سورية SYP", callback_data="w_syp")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📤 **اختر عملة السحب:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "w_usdt":
        context.user_data['w_curr'] = 'USDT'
        update_user_step(user_id, 'WITHDRAW_AMOUNT')
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="withdraw")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📤 أدخل المبلغ المراد سحبه بـ USDT:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "w_usd":
        context.user_data['w_curr'] = 'USD'
        update_user_step(user_id, 'WITHDRAW_AMOUNT')
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="withdraw")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📤 أدخل المبلغ المراد سحبه بالدولار USD:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "w_syp":
        context.user_data['w_curr'] = 'SYP'
        update_user_step(user_id, 'WITHDRAW_AMOUNT')
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="withdraw")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📤 أدخل المبلغ المراد سحبه بالليرة السورية SYP:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "transfer":
        keyboard = [
            [InlineKeyboardButton("💎 تحويل USDT", callback_data="t_usdt")],
            [InlineKeyboardButton("💵 تحويل دولار USD", callback_data="t_usd")],
            [InlineKeyboardButton("🥏 تحويل ليرة سورية SYP", callback_data="t_syp")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🔄 **اختر عملة التحويل:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "t_usdt":
        context.user_data['t_curr'] = 'USDT'
        update_user_step(user_id, 'TRANSFER_ID')
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="transfer")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🔄 أدخل ID الحساب المستلم:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "t_usd":
        context.user_data['t_curr'] = 'USD'
        update_user_step(user_id, 'TRANSFER_ID')
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="transfer")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🔄 أدخل ID الحساب المستلم:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "t_syp":
        context.user_data['t_curr'] = 'SYP'
        update_user_step(user_id, 'TRANSFER_ID')
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="transfer")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🔄 أدخل ID الحساب المستلم:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "admin_wallet" and user_id == ADMIN_USER_ID:
        user = get_user(ADMIN_USER_ID)
        p_usd = user[7] if user else 0.0
        p_syp = user[8] if user else 0.0
        p_usdt = user[9] if user else 0.0

        keyboard = [
            [InlineKeyboardButton("📊 إحصائيات وتقييمات العملاء", callback_data="admin_ratings")],
            [InlineKeyboardButton("📤 سحب أرباح المدير", callback_data="admin_withdraw_menu")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            f"🗂️ **محفظة المدير والأرباح:**\n\n"
            f"💎 أرباح USDT: `{p_usdt:.2f} USDT`\n"
            f"💵 أرباح USD: `{p_usd:.2f} USD`\n"
            f"🥏 أرباح SYP: `{p_syp:,.2f} SYP`\n\n"
            "يمكنك سحب أرباحك بكلمة سر الشحن الخاصة بك.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif query.data == "admin_withdraw_menu" and user_id == ADMIN_USER_ID:
        keyboard = [
            [InlineKeyboardButton("💎 سحب أرباح USDT", callback_data="admin_w_usdt")],
            [InlineKeyboardButton("💵 سحب أرباح USD", callback_data="admin_w_usd")],
            [InlineKeyboardButton("🥏 سحب أرباح SYP", callback_data="admin_w_syp")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_wallet")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📤 **اختر عملة أرباح المدير المراد سحبها:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data in ["admin_w_usdt", "admin_w_usd", "admin_w_syp"] and user_id == ADMIN_USER_ID:
        curr_map = {
            "admin_w_usdt": "USDT",
            "admin_w_usd": "USD",
            "admin_w_syp": "SYP"
        }
        curr = curr_map[query.data]
        context.user_data['admin_w_curr'] = curr
        update_user_step(user_id, 'ADMIN_W_AMOUNT')
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_withdraw_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"📤 أدخل مبلغ أرباح ({curr}) المراد سحبه:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "admin_ratings" and user_id == ADMIN_USER_ID:
        conn = sqlite3.connect("wallet_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(rating), COUNT(rating) FROM ratings")
        avg_rating, total_ratings = cursor.fetchone()
        conn.close()
        
        avg_text = f"{avg_rating:.1f} ⭐" if avg_rating else "لا توجد تقييمات بعد"

        keyboard = [[InlineKeyboardButton("🔙 رجوع محفظة المدير", callback_data="admin_wallet")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            f"📊 **إحصائيات إرضاء الزبون:**\n\n"
            f"⭐ التقييم العام: {avg_text}\n"
            f"👥 إجمالي عدد المقيمين: `{total_ratings}`",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

def main():
    t = Thread(target=run_web)
    t.start()

    app = ApplicationBuilder().token(TOKEN).post_init(set_commands).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    print("🤖 البوت يعمل بأعلى معايير الأمان والثبات...")
    app.run_polling()

if __name__ == "__main__":
    main()

