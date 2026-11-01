import sqlite3
import re
import random
from datetime import datetime, timedelta
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
            referred_by INTEGER,
            referral_earnings REAL DEFAULT 0.0,
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
            status TEXT,
            date TEXT
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
    cursor.execute("SELECT username, login_pass, withdraw_pass, phone, usd_balance, syp_balance, usdt_balance, admin_usd_profit, admin_syp_profit, admin_usdt_profit, referred_by, referral_earnings, step, last_active FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_user_step(user_id, step):
    conn = sqlite3.connect("wallet_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET step = ?, last_active = ? WHERE user_id = ?", (step, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def update_balances(user_id, usd_change=0.0, syp_change=0.0, usdt_change=0.0, profit_usd=0.0, profit_syp=0.0, profit_usdt=0.0, ref_change=0.0):
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
            referral_earnings = referral_earnings + ?,
            last_active = ? 
        WHERE user_id = ?
    """, (usd_change, syp_change, usdt_change, profit_usd, profit_syp, profit_usdt, ref_change, datetime.now().isoformat(), user_id))
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

async def periodic_check(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("wallet_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, last_active FROM users")
    all_users = cursor.fetchall()
    conn.close()

async def set_commands(app):
    commands = [
        BotCommand("start", "تشغيل المنصة المالية والقائمة الرئيسية 🌐")
    ]
    await app.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    args = context.args
    referrer_id = None
    if args and args[0].isdigit():
        possible_ref = int(args[0])
        if possible_ref != user_id:
            referrer_id = possible_ref

    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 قناة التوثيق الرسمية", url=CHANNEL_LINK)],
            [InlineKeyboardButton("🔄 التحقق من الاشتراك", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_text = (
            "🏛️ **مرحباً بك في منصة المعاملات الرقمية الآمنة**\n\n"
            f"🆔 رقم المعرف التعريفي (ID): `{user_id}`\n\n"
            "⚠️ **شرط أساسي للاستخدام:**\n"
            "يجب عليك الانضمام إلى قناتنا الرسمية المعتمدة لاستخدام البوت والاستفادة من الخدمات المادية 🛡️\n\n"
            "بعد الانضمام، اضغط على زر التحقق أدناه:"
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
        cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, usd_balance, syp_balance, usdt_balance, admin_usd_profit, admin_syp_profit, admin_usdt_profit, referred_by, referral_earnings, step, last_active) 
            VALUES (?, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ?, 0.0, 'WAITING_NAME', ?)
        """, (user_id, referrer_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        msg = (
            f"🆔 رقم المعرف التعريفي (ID): `{user_id}`\n\n"
            "🔒 **بروتوكول التسجيل المعتمد**\n\n"
            "يرجى إدخال الاسم الثلاثي أو الاسم الرسمي المعتمد للبدء:"
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
    ref_earn = user[11] if user else 0.0

    text = (
        "🏛️ **AL.RAEISS FINANCIAL** 🏛️\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 معرف الحساب المعتمد: `{user_id}`\n"
        "🛡️ حالة الحساب: **موثق ومؤمن بالكامل ✅**\n\n"
        "💼 **اللوحة المالية الرئيسية**\n"
        "────────────────────────\n"
        f"💎 USDT: `{usdt:.2f}`\n"
        f"💵 USD: `{usd:.2f}`\n"
        f"🥏 SYP: `{syp:,.2f}`\n"
        f"🎁 أرباح الإحالة: `{ref_earn:.2f} USD`\n"
        "────────────────────────\n"
        "🔻 اختر الخدمة المطلوبة أدناه 👇"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📥 إيداع وتعبئة", callback_data="deposit"),
            InlineKeyboardButton("📤 سحب نقدي", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("🔄 تحويل مالي آمن", callback_data="transfer"),
            InlineKeyboardButton("📋 سجل معاملاتي (آخر 10)", callback_data="my_history")
        ],
        [
            InlineKeyboardButton("🔗 برنامج الإحالة", callback_data="referral_program"),
            InlineKeyboardButton("⭐ تقييم الخدمة", callback_data="rate_service")
        ],
        [
            InlineKeyboardButton("📖 الدليل المعتمد", callback_data="guide")
        ]
    ]
    if user_id == ADMIN_USER_ID:
        keyboard.append([InlineKeyboardButton("🗂️ لوحة إدارة النظام والأرباح", callback_data="admin_wallet")])

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

    step = user[12]

    # --- نظام التفاعلات الذكي على الرسائل ---
    # بنسبة 60% يقوم البوت بالتفاعل على الرسالة لكي لا يبدو متفاعلاً على كل حرف
    if random.random() < 0.6:
        try:
            # التحقق إذا كانت الرسالة غير صحيحة أو خارج التنسيق أو استعلام خاطئ
            is_error_msg = False
            if step == 'WAITING_LOGIN_PASS' and not validate_login_password(text):
                is_error_msg = True
            elif step == 'WAITING_WITHDRAW_PASS' and not validate_withdraw_password(text):
                is_error_msg = True
            elif step in ['DEPOSIT_AMOUNT', 'WITHDRAW_AMOUNT', 'TRANSFER_AMOUNT'] and not text.replace('.', '', 1).isdigit():
                is_error_msg = True

            if is_error_msg:
                # شعور حزين أو ندم أو مظلوم للرسائل غير الصحيحة
                sad_reactions = ["😢", "💔", "😔", "🤷‍♂️", "⚠️"]
                chosen_reaction = random.choice(sad_reactions)
                await update.message.set_reaction(reaction=chosen_reaction)
            else:
                # قلوب بمختلف الألوان، 100، لايك، حمامة بيضاء، غصن زيتون، وورد
                good_reactions = ["❤️", "💙", "💚", "💜", "🧡", "💯", "👍", "🕊️", "🫒", "🌹", "😍", "✨"]
                chosen_reaction = random.choice(good_reactions)
                await update.message.set_reaction(reaction=chosen_reaction)
        except Exception:
            pass
    # ----------------------------------------

    if step == 'WAITING_NAME':
        context.user_data['temp_name'] = text
        update_user_step(user_id, 'WAITING_LOGIN_PASS')
        await update.message.reply_text(
            f"🆔 معرف حسابك: `{user_id}`\n\n"
            "🔐 **إعداد كلمة سر الأمان الرئيسية:**\n\n"
            "الشروط الأمنية:\n"
            "• حرف كبير واحد على الأقل (A-Z)\n"
            "• 4 أحرف صغيرة على الأقل (a-z)\n"
            "• 4 أرقام على الأقل (0-9)\n"
            "• رمز خاص واحد على الأقل (مثل @, #, $, !)\n\n"
            "أدخل كلمة سر الأمان الآن:",
            parse_mode="Markdown"
        )

    elif step == 'WAITING_LOGIN_PASS':
        if not validate_login_password(text):
            await update.message.reply_text("❌ كلمة السر لا توفي بالمعايير الأمنية المطلوبة (حرف كبير، 4 أحرف صغيرة، 4 أرقام، ورمز). حاول مجدداً:")
            return
        context.user_data['temp_login_pass'] = text
        update_user_step(user_id, 'WAITING_WITHDRAW_PASS')
        await update.message.reply_text("🔒 **إعداد كلمة سر العمليات المالية (السحب والتحويل):**\n\nيجب أن تحتوي على 3 أحرف و3 أرقام على الأقل.\nأدخل كلمة السر المالية الجديدة:")

    elif step == 'WAITING_WITHDRAW_PASS':
        if not validate_withdraw_password(text):
            await update.message.reply_text("❌ كلمة سر العمليات المالية يجب ألا تقل عن 3 أحرف و3 أرقام. حاول مجدداً:")
            return
        login_pass = context.user_data.get('temp_login_pass')
        if text == login_pass:
            await update.message.reply_text("❌ لأسباب أمنية صارمة، يجب أن تختلف كلمة سر العمليات عن كلمة سر الأمان! أدخل كلمة سر أخرى:")
            return
        context.user_data['temp_withdraw_pass'] = text
        update_user_step(user_id, 'WAITING_PHONE')
        await update.message.reply_text("📱 يرجى إدخال رقم الهاتف المعتمد لإتمام التوثيق:")

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
            "✅ تم توثيق وإنشاء حسابك المالي بنجاح تام!\n\n"
            "🛡️ **إشعار أمني رسمي هام:**\n"
            "حسابك وأرصدتك الرقمية تقع تحت **مسؤوليتك الشخصية والكاملة**. يُمنع منعاً باتاً مشاركة كلمات السر الخاصة بك مع أي جهة أو شخص لضمان حماية أصولك المالية وعدم تعرضها للضياع!",
            parse_mode="Markdown"
        )
        await show_main_menu(update, context)

    elif step == 'DEPOSIT_AMOUNT':
        try:
            amount = float(text)
            curr = context.user_data.get('dep_curr')
            
            if curr in ['USDT', 'USD'] and amount < 1.5:
                await update.message.reply_text(f"❌ الحد الأدنى للإيداع لعملة {curr} هو 1.5. أدخل مبلغاً صالحاً:")
                return
            elif curr == 'SYP' and amount < 87650:
                await update.message.reply_text("❌ الحد الأدنى للإيداع هو 87,650 SYP. أدخل مبلغاً صالحاً:")
                return
            
            if amount <= 0:
                raise ValueError()

            context.user_data['dep_amount'] = amount
            update_user_step(user_id, 'DEPOSIT_TXID')
            gateway = context.user_data.get('dep_gateway')
            
            await update.message.reply_text(
                "📥 **بروتوكول توثيق الإيداع المالي:**\n\n"
                f"🆔 رقم الحساب: `{user_id}`\n"
                f"يرجى تحويل القيمة عبر ({gateway}) للعملة ({curr}).\n"
                "ثم أدخل الآن رقم المعرف المالي (TXID أو رقم الإيصال الرسمي) بدقة تامة لضمان الاعتماد السريع:",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("❌ قيمة غير صالحة. أدخل رقماً صحيحاً:")

    elif step == 'DEPOSIT_TXID':
        txid = text
        amount = context.user_data.get('dep_amount')
        gateway = context.user_data.get('dep_gateway')
        curr = context.user_data.get('dep_curr')
        now_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = sqlite3.connect("wallet_database.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, gateway, reference_code, status, date)
            VALUES (?, 'إيداع 📥', ?, ?, ?, ?, 'قيد التدقيق ⏳', ?)
        """, (user_id, curr, amount, gateway, txid, now_date))
        conn.commit()
        conn.close()

        update_user_step(user_id, 'LOGGED_IN')
        await update.message.reply_text(
            "🛡️ **تم استلام طلب الإيداع وإرساله للتدقيق المالي:**\n\n"
            f"🆔 معرف الحساب: `{user_id}`\n"
            f"القيمة: `{amount} {curr}`\n"
            f"البوابة: `{gateway}`\n"
            f"رقم الإيصال: `{txid}`\n\n"
            "⏳ جاري التحقق من السجل المالي وإضافة الأرصدة لحسابك فور الاعتماد.",
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
            await update.message.reply_text("🔒 أدخل كلمة سر العمليات المالية الخاصة بك لاعتماد السحب:")
        except ValueError:
            await update.message.reply_text("❌ قيمة غير صالحة. أدخل رقماً صحيحاً:")

    elif step == 'WITHDRAW_PASS_CHECK':
        if text == user[2]:
            amount = context.user_data.get('w_amount', 0)
            curr = context.user_data.get('w_curr', 'USD')
            now_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            if curr == 'USDT':
                if user[7] < amount:
                    await update.message.reply_text("❌ رصيدك الحالي من USDT غير كافٍ.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                fee = amount * 0.007
                net = amount - fee
                update_balances(user_id, usdt_change=-amount, profit_usdt=fee)
                msg = f"✅ **تم اعتماد طلب السحب بنجاح:**\n🆔 معرف الحساب: `{user_id}`\nالمبلغ الصافي: `{net:.2f} USDT`\nرسوم الخدمة: `{fee:.2f} USDT`"
            elif curr == 'USD':
                if user[5] < amount:
                    await update.message.reply_text("❌ رصيدك الحالي من الدولار غير كافٍ.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                fee = amount * 0.02
                net = amount - fee
                update_balances(user_id, usd_change=-amount, profit_usd=fee)
                msg = f"✅ **تم اعتماد طلب السحب بنجاح:**\n🆔 معرف الحساب: `{user_id}`\nالمبلغ الصافي: `{net:.2f} USD`\nرسوم الخدمة: `{fee:.2f} USD`"
            else:
                if user[6] < amount:
                    await update.message.reply_text("❌ رصيدك الحالي من الليرة السورية غير كافٍ.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                fee = amount * 0.02
                net = amount - fee
                update_balances(user_id, syp_change=-amount, profit_syp=fee)
                msg = f"✅ **تم اعتماد طلب السحب بنجاح:**\n🆔 معرف الحساب: `{user_id}`\nالمبلغ الصافي: `{net:,.2f} SYP`\nرسوم الخدمة: `{fee:.2f} SYP`"

            conn = sqlite3.connect("wallet_database.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (user_id, type, currency, amount, gateway, reference_code, status, date)
                VALUES (?, 'سحب 📤', ?, ?, 'محفظة النظام', 'معتمد', 'مكتملة ✅', ?)
            """, (user_id, curr, amount, now_date))
            conn.commit()
            conn.close()

            update_user_step(user_id, 'LOGGED_IN')
            await update.message.reply_text(msg, parse_mode="Markdown")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ كلمة سر العمليات المالية غير صحيحة! تم إلغاء الطلب لأسباب أمنية.")
            update_user_step(user_id, 'LOGGED_IN')
            await show_main_menu(update, context)

    elif step == 'TRANSFER_ID':
        try:
            target_id = int(text)
            target_user = get_user(target_id)
            if not target_user:
                await update.message.reply_text("❌ رقم المعرف (ID) غير مسجل في النظام المالي. أدخل معرفاً صحيحاً:")
                return
            if target_id == user_id:
                await update.message.reply_text("❌ عذراً، لا يمكنك إجراء تحويل مالي لحسابك الشخصي. أدخل معرف مستلم آخر:")
                return
            context.user_data['t_target'] = target_id
            update_user_step(user_id, 'TRANSFER_AMOUNT')
            await update.message.reply_text("💵 أدخل المبلغ المراد تحويله:")
        except ValueError:
            await update.message.reply_text("❌ معرف غير صالح. أدخل أرقاماً فقط:")

    elif step == 'TRANSFER_AMOUNT':
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError()
            context.user_data['t_amount'] = amount
            update_user_step(user_id, 'TRANSFER_PASS_CHECK')
            await update.message.reply_text("🔒 أدخل كلمة سر العمليات المالية الخاصة بك لاعتماد التحويل:")
        except ValueError:
            await update.message.reply_text("❌ قيمة غير صالحة. أدخل رقماً صحيحاً:")

    elif step == 'TRANSFER_PASS_CHECK':
        if text == user[2]:
            amount = context.user_data.get('t_amount', 0)
            target_id = context.user_data.get('t_target')
            curr = context.user_data.get('t_curr', 'USD')
            now_date = datetime.now().strftime("%Y-%m-%d %H:%M")

            fee = amount * 0.0035
            net = amount - fee

            referred_by = user[10]
            ref_commission = fee * 0.20 if referred_by else 0.0
            admin_net_fee = fee - ref_commission

            if curr == 'USDT':
                if user[7] < amount:
                    await update.message.reply_text("❌ رصيدك غير كافٍ.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, usdt_change=-amount)
                update_balances(target_id, usdt_change=net)
                update_balances(ADMIN_USER_ID, profit_usdt=admin_net_fee)
                if referred_by:
                    update_balances(referred_by, ref_change=ref_commission)
            elif curr == 'USD':
                if user[5] < amount:
                    await update.message.reply_text("❌ رصيدك غير كافٍ.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, usd_change=-amount)
                update_balances(target_id, usd_change=net)
                update_balances(ADMIN_USER_ID, profit_usd=admin_net_fee)
                if referred_by:
                    update_balances(referred_by, ref_change=ref_commission)
            else:
                if user[6] < amount:
                    await update.message.reply_text("❌ رصيدك غير كافٍ.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, syp_change=-amount)
                update_balances(target_id, syp_change=net)
                update_balances(ADMIN_USER_ID, profit_syp=admin_net_fee)
                if referred_by:
                    update_balances(referred_by, ref_change=ref_commission)

            conn = sqlite3.connect("wallet_database.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (user_id, type, currency, amount, gateway, reference_code, status, date)
                VALUES (?, 'تحويل 🔄', ?, ?, ?, ?, 'مكتملة ✅', ?)
            """, (user_id, curr, amount, f"إلى ID: {target_id}", "تحويل داخلي", now_date))
            conn.commit()
            conn.close()

            update_user_step(user_id, 'LOGGED_IN')
            await update.message.reply_text(f"✅ **تم إجراء التحويل المالي بنجاح:**\nمستلم المعاملة (ID): `{target_id}`\nالمبلغ الواصل: `{net:.2f}` (بعد احتساب رسوم الشبكة 0.35%).", parse_mode="Markdown")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ كلمة سر العمليات المالية خاطئة! تم إلغاء المعاملة.")
            update_user_step(user_id, 'LOGGED_IN')
            await show_main_menu(update, context)

    elif step == 'ADMIN_W_AMOUNT':
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError()
            context.user_data['admin_w_amount'] = amount
            update_user_step(user_id, 'ADMIN_W_PASS')
            await update.message.reply_text("🔒 أدخل كلمة سر العمليات المالية الخاصة بالمدير لتأكيد السحب:")
        except ValueError:
            await update.message.reply_text("❌ مبلغ غير صالح:")

    elif step == 'ADMIN_W_PASS':
        if text == user[2]:
            amount = context.user_data.get('admin_w_amount', 0)
            curr = context.user_data.get('admin_w_curr', 'USDT')

            if curr == 'USDT':
                if user[9] < amount:
                    await update.message.reply_text("❌ رصيد أرباح USDT في خزينة المدير غير كافٍ.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, profit_usdt=-amount)
                msg = f"✅ **تم سحب أرباح المدير بنجاح:**\nالقيمة: `{amount:.2f} USDT`"
            elif curr == 'USD':
                if user[7] < amount:
                    await update.message.reply_text("❌ رصيد أرباح USD في خزينة المدير غير كافٍ.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, profit_usd=-amount)
                msg = f"✅ **تم سحب أرباح المدير بنجاح:**\nالقيمة: `{amount:.2f} USD`"
            else:
                if user[8] < amount:
                    await update.message.reply_text("❌ رصيد أرباح SYP في خزينة المدير غير كافٍ.")
                    update_user_step(user_id, 'LOGGED_IN')
                    await show_main_menu(update, context)
                    return
                update_balances(user_id, profit_syp=-amount)
                msg = f"✅ **تم سحب أرباح المدير بنجاح:**\nالقيمة: `{amount:,.2f} SYP`"

            update_user_step(user_id, 'LOGGED_IN')
            await update.message.reply_text(msg, parse_mode="Markdown")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ كلمة سر العمليات غير صحيحة!")
            update_user_step(user_id, 'LOGGED_IN')
            await show_main_menu(update, context)

    else:
        await update.message.reply_text(f"مرحباً بك في المنصة الرسمية. لقد استلامنا إشعارك: '{text}'. يمكنك الاعتماد على القائمة الرئيسية لإنجاز معاملاتك بكل ثقة 🏛️")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    if query.data == "check_sub":
        is_sub = await check_subscription(user_id, context)
        if is_sub:
            await start(update, context)
        else:
            await query.answer("🛡️ عذراً، لم تقم بالانضمام للقناة الرسمية بعد. يرجى الانضمام ثم إعادة المحاولة!", show_alert=True)
        return

    if query.data == "my_history":
        conn = sqlite3.connect("wallet_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT type, currency, amount, status, date FROM transactions WHERE user_id = ? ORDER BY tx_id DESC LIMIT 10", (user_id,))
        txs = cursor.fetchall()
        conn.close()

        history_text = "📋 **سجل المعاملات الشخصية (آخر 10 عمليات):**\n\n"
        if txs:
            for t in txs:
                history_text += f"• **{t[0]}** | `{t[2]} {t[1]}`\n  الحالة: {t[3]} | التاريخ: {t[4]}\n\n"
        else:
            history_text += "لا توجد معاملات مسجلة حتى الآن.\n\n"

        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(history_text, reply_markup=reply_markup, parse_mode="Markdown")
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
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🌟 ما مدى تقييمك لمستوى جودة وأمان خدماتنا المعتمدة؟", reply_markup=reply_markup)
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
        await query.message.edit_text(f"🏛️ نشكر ثقتك الكريمة وتقييمك بـ {score} نجوم! نعتز بخدمتكم.", reply_markup=reply_markup)
        return

    if query.data == "referral_program":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        user = get_user(user_id)
        ref_earn = user[11] if user else 0.0

        keyboard = [
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "🔗 **برنامج الإحالة والأرباح التضامنية:**\n\n"
            "اربح معنا حصرياً عبر دعوة أصدقائك والمعارف للمنصة!\n"
            "• تحصد **20%** من أرباح رسوم التحويل الخاصة بأصدقائك المدعوين مدى الحياة.\n\n"
            f"🎁 أرباحك الحالية من الإحالات: `{ref_earn:.2f} USD`\n\n"
            "📋 **رابط الدعوة الخاص بك:**\n"
            f"`{ref_link}`\n\n"
            "انقر فوق الرابط لنسخه ومشاركته فوراً مع شبكتك 🚀",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    if query.data == "main_menu":
        update_user_step(user_id, 'LOGGED_IN')
        await show_main_menu(update, context)
        return

    if query.data == "guide":
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "📖 **دليل التشغيل وبروتوكول الاستخدام:**\n\n"
            f"🆔 معرف الحساب المعتمد: `{user_id}`\n"
            "1️⃣ الأمان المصرفي: فصل كامل بين كلمة سر الدخول وكلمة سر العمليات المالية.\n"
            "2️⃣ المعاملات الرقمية: توثيق دقيق وفوري عبر الإيصالات والمعرفات (TXID).\n",
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
        await query.message.edit_text("📥 **اختر بوابة الشحن المعتمدة المناسبة:**", reply_markup=reply_markup, parse_mode="Markdown")

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
            f"📥 بوابة الإيداع عبر {gateway} ({curr}):\n\n"
            f"⚠️ الحد الأدنى المعتمد للإيداع: `{min_msg} {curr}`\n"
            "الحساب المالي المعتمد للإدارة:\n`987654321`\n\n"
            "💵 أدخل الآن القيمة المالية المحولة:",
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
        await query.message.edit_text("📤 **اختر عملة السحب النقدي المعتمدة:**", reply_markup=reply_markup, parse_mode="Markdown")

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
        await query.message.edit_text("🔄 **اختر عملة التحويل المالي المعتمد:**", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "t_usdt":
        context.user_data['t_curr'] = 'USDT'
        update_user_step(user_id, 'TRANSFER_ID')
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="transfer")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🔄 أدخل رقم المعرف (ID) للمستلم:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "t_usd":
        context.user_data['t_curr'] = 'USD'
        update_user_step(user_id, 'TRANSFER_ID')
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="transfer")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🔄 أدخل رقم المعرف (ID) للمستلم:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "t_syp":
        context.user_data['t_curr'] = 'SYP'
        update_user_step(user_id, 'TRANSFER_ID')
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="transfer")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🔄 أدخل رقم المعرف (ID) للمستلم:", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "admin_wallet" and user_id == ADMIN_USER_ID:
        user = get_user(ADMIN_USER_ID)
        p_usd = user[7] if user else 0.0
        p_syp = user[8] if user else 0.0
        p_usdt = user[9] if user else 0.0

        keyboard = [
            [InlineKeyboardButton("📊 تقارير إرضاء العملاء", callback_data="admin_ratings")],
            [InlineKeyboardButton("📤 سحب أرباح الخزينة", callback_data="admin_withdraw_menu")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            f"🗂️ **لوحة خزينة المدير والأرباح العامة:**\n\n"
            f"💎 أرباح شبكة USDT: `{p_usdt:.2f} USDT`\n"
            f"💵 أرباح النقد USD: `{p_usd:.2f} USD`\n"
            f"🥏 أرباح الحسابات SYP: `{p_syp:,.2f} SYP`\n\n"
            "يمكنك سحب أرباحك المصرفية باستخدام كلمة سر العمليات.",
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
        await query.message.edit_text("📤 **اختر العملة المراد سحب أرباحها من الخزينة:**", reply_markup=reply_markup, parse_mode="Markdown")

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
        await query.message.edit_text(f"📤 أدخل القيمة المراد سحبها من أرباح ({curr}):", reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "admin_ratings" and user_id == ADMIN_USER_ID:
        conn = sqlite3.connect("wallet_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(rating), COUNT(rating) FROM ratings")
        avg_rating, total_ratings = cursor.fetchone()
        conn.close()
        
        avg_text = f"{avg_rating:.1f} ⭐" if avg_rating else "لا توجد تقييمات معتمدة بعد"

        keyboard = [[InlineKeyboardButton("🔙 رجوع للوحة المدير", callback_data="admin_wallet")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            f"📊 **تقارير إرضاء وموثوقية العملاء:**\n\n"
            f"⭐ متوسط التقييم المعتمد: {avg_text}\n"
            f"👥 إجمالي عدد المستفتين: `{total_ratings}`",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

def main():
    app = ApplicationBuilder().token(TOKEN).post_init(set_commands).build()

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(periodic_check, interval=14400, first=10)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    print("🏛️ نظام AL.RAEISS المالي يعمل بأعلى معايير الموثوقية والثقة...")
    app.run_polling()

if __name__ == "__main__":
    main()

