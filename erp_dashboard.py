import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
from sqlalchemy import text

st.set_page_config(page_title="لوحة متابعة نظام ERP", layout="wide", initial_sidebar_state="expanded")

# --- الاتصال بقاعدة البيانات (Supabase) ---
conn = st.connection("supabase", type="sql")

# ── Functions to Load/Save Data from SQL ─────────────────────────
def load_json_from_db(doc_id):
    try:
        df = conn.query(f"SELECT doc_data FROM app_storage WHERE doc_id = '{doc_id}'", ttl=0)
        if not df.empty and df.iloc[0]['doc_data']:
            data = df.iloc[0]['doc_data']
            return data if isinstance(data, dict) else json.loads(data)
    except:
        pass
    return {}

def save_json_to_db(data, doc_id):
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        with conn.session as s:
            s.execute(
                text("UPDATE app_storage SET doc_data = :data WHERE doc_id = :id"),
                {"data": json_str, "id": doc_id}
            )
            s.commit()
    except Exception as e:
        st.error(f"خطأ في الحفظ: {e}")

# --- دوال التعامل مع البيانات في التطبيق ---
def load_data(): return load_json_from_db('erp_data')
def save_data(data): save_json_to_db(data, 'erp_data')
def load_users(): return load_json_from_db('users')
def save_users(users): save_json_to_db(users, 'users')

def log_event(req, action):
    if "history" not in req:
        req["history"] = []
    user_name = st.session_state.user_info.get("name", "مجهول")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    req["history"].insert(0, {"action": action, "user": user_name, "time": timestamp})

def recompute_stats(data_dict):
    for dept_name, dept_info in data_dict.items():
        reqs = dept_info.get("requirements", [])
        active_reqs = [r for r in reqs if r.get("status") != "محذوف"]
        completed_reqs = [r for r in reqs if r.get("status") == "مكتمل"]
        dept_info["total"] = len(active_reqs)
        dept_info["completed"] = len(completed_reqs)
    return data_dict

# ── Session State ───────────────────────────────────────
if "dark_mode" not in st.session_state: st.session_state.dark_mode = True
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_info" not in st.session_state: st.session_state.user_info = None
if "show_audit_for" not in st.session_state: st.session_state.show_audit_for = []
if "edit_user_id" not in st.session_state: st.session_state.edit_user_id = None

# ── Theme Variables & CSS ───────────────────────────────
if st.session_state.dark_mode:
    bg_main, bg_sidebar = "linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%)", "linear-gradient(180deg, #1F3864 0%, #0f1f3d 100%)"
    text_color, text_muted, sidebar_txt, tick_color = "white", "rgba(255,255,255,0.6)", "white", "rgba(255,255,255,0.6)"
    card_bg, card_border = "rgba(255,255,255,0.05)", "rgba(255,255,255,0.12)"
    input_bg, input_border = "rgba(255,255,255,0.07)", "rgba(255,255,255,0.2)"
    hr_color, grid_color = "rgba(255,255,255,0.08)", "rgba(255,255,255,0.07)"
    plot_bg, paper_bg, section_bg = "rgba(0,0,0,0)", "rgba(255,255,255,0.03)", "rgba(74,144,217,0.08)"
    header_bg = "linear-gradient(135deg, rgba(74,144,217,0.15), rgba(31,56,100,0.3))"
else:
    bg_main, bg_sidebar = "linear-gradient(135deg, #f8f9fa 0%, #e9ecef 50%, #f8f9fa 100%)", "linear-gradient(180deg, #1F3864 0%, #2c4c82 100%)"
    text_color, text_muted, sidebar_txt, tick_color = "#1a202c", "#6c757d", "white", "#495057"
    card_bg, card_border = "white", "#dee2e6"
    input_bg, input_border = "white", "#ced4da"
    hr_color, grid_color = "#e9ecef", "#e9ecef"
    plot_bg, paper_bg, section_bg = "rgba(0,0,0,0)", "white", "rgba(74,144,217,0.1)"
    header_bg = "linear-gradient(135deg, #ffffff, #f1f3f5)"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800&display=swap');
* {{ font-family: 'Tajawal', sans-serif !important; }}
header[data-testid="stHeader"] {{ background: transparent !important; }}
.stApp {{ background: {bg_main} !important; }}
.main .block-container {{ background: transparent !important; padding: 2rem 2rem; margin-top: -30px; }}
.main {{ direction: rtl !important; }}
.block-container, .stMarkdown, .stAlert, div[data-testid="column"], div[data-testid="stVerticalBlock"] {{ direction: rtl !important; text-align: right !important; }}
section[data-testid="stSidebar"] > div {{ background: {bg_sidebar} !important; border-left: 1px solid rgba(255,255,255,0.1); }}
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {{ direction: rtl !important; }}
section[data-testid="stSidebarUserContent"] * {{ color: {sidebar_txt} !important; }}

/* -- HIDE BUGGY ICONS & ANCHOR LINKS -- */
span.material-symbols-rounded, 
span.material-symbols-outlined,
div[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
.stMarkdown h1 > div > a,
.stMarkdown h2 > div > a,
.stMarkdown h3 > div > a,
.stMarkdown h4 > div > a,
[data-testid="stHeaderActionElements"] {{ display: none !important; }}

/* -- FIX TITLES COLOR -- */
h1, h2, h3, h4, h5, h6 {{ color: {text_color} !important; text-shadow: none !important; background: none !important; -webkit-text-fill-color: initial !important; }}
.title-container {{ background: {header_bg}; border: 1px solid {card_border}; border-radius: 16px; padding: 24px; margin-bottom: 20px; display: block; }}
.title-container h1, .title-container h2 {{ margin: 0 !important; padding: 0 !important; color: {text_color} !important; font-weight:700; }}

/* -- General Styling -- */
.stTextInput input, .stSelectbox > div > div, .stMultiSelect > div > div, .stNumberInput input {{ background: {input_bg} !important; color: {text_color} !important; border: 1px solid {input_border} !important; border-radius: 8px !important; direction: rtl !important; }}
.stTextInput input:disabled {{ background: rgba(128,128,128,0.1) !important; color: {text_muted} !important; }}

/* ---------------------------------------------------
   إصلاح حقول الاختيار المتعدد (Multiselect Tags Fix)
   --------------------------------------------------- */
span[data-baseweb="tag"] {{
    background-color: rgba(74, 144, 217, 0.2) !important; /* لون هادئ بدلاً من الأحمر */
    color: {text_color} !important;
    border-radius: 4px !important;
    padding-right: 8px !important;
    padding-left: 28px !important; /* مساحة لعلامة الحذف (x) على اليسار */
    border: 1px solid #4A90D9 !important;
    font-size: 14px !important;
}}
span[data-baseweb="tag"] span[role="button"] {{
    left: 4px !important;
    right: auto !important;
    padding: 2px !important;
}}
ul[role="listbox"] {{
    direction: rtl !important;
    text-align: right !important;
}}

div[data-testid="metric-container"] {{ background: {card_bg} !important; border: 1px solid {card_border} !important; border-radius: 12px !important; padding: 12px !important; direction: rtl !important; }}
div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] {{ text-align: right !important; }}
p, li, span {{ color: {text_muted}; }}
hr {{ border-color: {hr_color} !important; }}
.kpi-card {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 16px; padding: 24px 20px; text-align: center; margin-bottom: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
.kpi-value {{ font-size: 2.2rem; font-weight: 800; margin: 8px 0 4px; }}
.kpi-label {{ font-size: 0.85rem; color: {text_muted} !important; font-weight: 500; }}
.kpi-blue {{ border-top: 3px solid #4A90D9; }} .kpi-blue .kpi-value {{ color: #4A90D9; }}
.kpi-green {{ border-top: 3px solid #27AE60; }} .kpi-green .kpi-value {{ color: #27AE60; }}
.kpi-orange {{ border-top: 3px solid #F39C12; }} .kpi-orange .kpi-value {{ color: #F39C12; }}
.kpi-red {{ border-top: 3px solid #E74C3C; }} .kpi-red .kpi-value {{ color: #E74C3C; }}
.section-header {{ font-size: 1.05rem; font-weight: 700; color: {text_color} !important; padding: 10px 16px; margin: 16px 0 12px; border-right: 4px solid #4A90D9; background: {section_bg}; border-radius: 0 8px 8px 0; direction: rtl; }}
.progress-container {{ background: {card_border}; border-radius: 50px; height: 28px; overflow: hidden; margin: 10px 0; border: 1px solid {card_border}; }}
.progress-fill {{ height: 100%; border-radius: 50px; background: linear-gradient(90deg, #1F3864, #4A90D9, #27AE60); display: flex; align-items: center; justify-content: center; color: white !important; font-weight: 700; font-size: 14px; }}
.dept-card {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; padding: 18px; margin-bottom: 10px; direction: rtl; }}
.dept-name {{ color: {text_color} !important; font-weight: 700; font-size: 1rem; margin-bottom: 8px; }}
.dept-stats {{ color: {text_muted} !important; font-size: 0.8rem; margin-bottom: 10px; }}
.mini-bar-bg {{ background: {card_border}; border-radius: 20px; height: 8px; }}
.mini-bar-fill {{ height: 8px; border-radius: 20px; }}
.badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 700; }}
.badge-critical {{ background: rgba(231,76,60,0.15); color: #E74C3C !important; border: 1px solid #E74C3C; }}
.badge-high {{ background: rgba(243,156,18,0.15); color: #d35400 !important; border: 1px solid #d35400; }}
.badge-medium {{ background: rgba(241,196,15,0.2); color: #b58900 !important; border: 1px solid #b58900; }}
.badge-low {{ background: rgba(39,174,96,0.15); color: #27AE60 !important; border: 1px solid #27AE60; }}
.stButton > button {{ background-color: rgba(255,255,255,0.1) !important; color: {text_color} !important; border-radius: 8px !important; font-weight: 600 !important; border: 1px solid {card_border} !important; transition: all 0.3s; }}
.stButton > button:hover {{ background-color: #4A90D9 !important; color: white !important; border-color:#4A90D9 !important; }}
.btn-primary > button {{ background-color: #4A90D9 !important; color: white !important; border:none !important; }}
</style>
""", unsafe_allow_html=True)

# ── Login Screen ────────────────────────────────────────
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"""
        <div style='background:{header_bg}; border:1px solid {card_border}; border-radius:16px; padding:30px; text-align:center; margin-top:50px;'>
            <h2 style='color:{text_color}; margin:0;'>🔐 تسجيل الدخول للنظام</h2>
            <p style='color:{text_muted}; margin-top:10px;'>أدخل بيانات الاعتماد للمتابعة</p>
        </div>""", unsafe_allow_html=True)
        with st.form("login"):
            usr = st.text_input("اسم المستخدم")
            pwd = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("تسجيل الدخول"):
                users = load_users()
                if usr in users and users[usr]["password"] == pwd:
                    st.session_state.logged_in = True
                    st.session_state.user_info = users[usr]
                    st.session_state.user_info["username"] = usr
                    st.rerun()
                else:
                    st.error("❌ بيانات الدخول غير صحيحة")
    st.stop()

# ── Main Application ────────────────────────────────────
data = recompute_stats(load_data()) 
user_name = st.session_state.user_info['name']
user_role = st.session_state.user_info['role']
user_allowed_depts = st.session_state.user_info.get('allowed_depts', ["الجميع"])

# تصفية الأقسام بناءً على صلاحيات المستخدم
all_depts_keys = list(data.keys())
if "الجميع" in user_allowed_depts or user_role == "admin":
    viewable_depts = all_depts_keys
else:
    viewable_depts = [d for d in all_depts_keys if d in user_allowed_depts]

with st.sidebar:
    st.markdown(f"<div style='text-align:center; padding:10px; background:rgba(255,255,255,0.05); border-radius:10px; margin-bottom:15px;'><p style='margin:0; font-size:0.8rem;'>مرحباً بك،</p><h3 style='margin:0; color:white;'>{user_name}</h3></div>", unsafe_allow_html=True)
    
    pages = ["📊 لوحة المتابعة", "📝 إدارة المتطلبات"]
    if user_role == "admin":
        pages.append("⚙️ إدارة المستخدمين والنظام")
        
    page = st.radio("القائمة الرئيسية", pages)
    st.divider()
    st.session_state.dark_mode = st.toggle("🌙 الوضع الداكن", value=st.session_state.dark_mode)
    
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.rerun()
        
    if page == "📊 لوحة المتابعة":
        st.divider()
        selected_depts = st.multiselect("تصفية الأقسام", viewable_depts, default=viewable_depts)
        priority_filter = st.multiselect("تصفية الأولويات", ["حرج","عالي","متوسط","منخفض"], default=["حرج","عالي","متوسط","منخفض"])
        view_mode = st.radio("طريقة العرض", ["ملخص عام", "تفاصيل قسم"])

# ── Page: System & User Management (Admin Only) ─────────────────────────
if page == "⚙️ إدارة المستخدمين والنظام" and user_role == "admin":
    st.markdown("<div class='title-container'><h1>⚙️ إدارة المستخدمين وإعدادات النظام</h1></div>", unsafe_allow_html=True)
    users = load_users()
    
    tab_users, tab_depts, tab_backup = st.tabs(["👥 المستخدمين والصلاحيات", "🏢 إدارة الأقسام", "💾 النسخ الاحتياطي والاستعادة"])
    
    # --- Tab 1: Users ---
    with tab_users:
        with st.container(border=True):
            st.markdown("**➕ إضافة مستخدم جديد**")
            with st.form("add_user"):
                c1, c2 = st.columns(2)
                with c1:
                    n_usr = st.text_input("اسم المستخدم (للدخول)")
                    n_name = st.text_input("الاسم الكامل")
                with c2:
                    n_pwd = st.text_input("كلمة المرور")
                    n_role = st.selectbox("الصلاحية", ["editor", "admin"], format_func=lambda x: "مدير نظام" if x=="admin" else "مستخدم عادي")
                    
                n_depts = st.multiselect("الأقسام المسموح برؤيتها", ["الجميع"] + all_depts_keys, default=["الجميع"])
                
                st.markdown("<div class='btn-primary'>", unsafe_allow_html=True)
                if st.form_submit_button("حفظ المستخدم"):
                    if n_usr and n_pwd and n_name:
                        if n_usr in users: 
                            st.error("اسم المستخدم موجود مسبقاً!")
                        else:
                            users[n_usr] = {"password": n_pwd, "name": n_name, "role": n_role, "allowed_depts": n_depts}
                            save_users(users)
                            st.success("✅ تم إضافة المستخدم بنجاح")
                            st.rerun()
                    else: 
                        st.error("يرجى تعبئة جميع الحقول")
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-header'>قائمة المستخدمين</div>", unsafe_allow_html=True)
        for u_id, u_info in users.items():
            with st.container():
                c1, c2, c3, c4 = st.columns([2.5, 2, 1, 1])
                c1.write(f"**{u_info['name']}** ({u_id})")
                role_label = "مدير نظام 👑" if u_info['role'] == 'admin' else "مستخدم عادي 👤"
                allowed_str = ", ".join(u_info.get('allowed_depts', ['الجميع']))
                c2.markdown(f"{role_label}<br><span style='font-size:0.8rem;color:{text_muted}'>صلاحية الرؤية: {allowed_str}</span>", unsafe_allow_html=True)
                
                if c3.button("✏️ تعديل", key=f"edit_btn_{u_id}"):
                    st.session_state.edit_user_id = u_id
                    st.rerun()
                    
                if u_id != st.session_state.user_info['username']:
                    if c4.button("🗑️ حذف", key=f"del_u_{u_id}"):
                        del users[u_id]
                        save_users(users)
                        st.rerun()
                
                if st.session_state.edit_user_id == u_id:
                    st.markdown(f"<div style='background:{input_bg}; padding:15px; border-radius:10px; border:1px solid #4A90D9; margin-top:10px;'>", unsafe_allow_html=True)
                    st.markdown(f"**تعديل بيانات المستخدم: {u_id}**")
                    with st.form(f"edit_form_{u_id}"):
                        edit_c1, edit_c2 = st.columns(2)
                        with edit_c1:
                            new_name = st.text_input("الاسم الكامل", value=u_info['name'])
                        with edit_c2:
                            new_pwd = st.text_input("كلمة المرور", value=u_info['password'])
                            
                        new_role = u_info['role']
                        if u_id != st.session_state.user_info['username']:
                            new_role = st.selectbox("الصلاحية", ["editor", "admin"], index=0 if u_info['role'] == "editor" else 1, format_func=lambda x: "مدير نظام" if x=="admin" else "مستخدم عادي")
                        
                        current_depts = u_info.get('allowed_depts', ["الجميع"])
                        new_depts = st.multiselect("الأقسام المسموح برؤيتها", ["الجميع"] + all_depts_keys, default=current_depts)

                        save_c1, save_c2 = st.columns([1, 4])
                        if save_c1.form_submit_button("💾 حفظ"):
                            if new_name and new_pwd:
                                users[u_id].update({'name': new_name, 'password': new_pwd, 'role': new_role, 'allowed_depts': new_depts})
                                save_users(users)
                                if u_id == st.session_state.user_info['username']:
                                    st.session_state.user_info.update({'name': new_name, 'password': new_pwd, 'role': new_role, 'allowed_depts': new_depts})
                                st.session_state.edit_user_id = None
                                st.success("تم التحديث!")
                                st.rerun()
                            else:
                                st.error("الرجاء عدم ترك حقول فارغة.")
                        if save_c2.form_submit_button("❌ إلغاء"):
                            st.session_state.edit_user_id = None
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(f"<hr style='margin:10px 0; border-color:{hr_color}'>", unsafe_allow_html=True)

    # --- Tab 2: Departments Management ---
    with tab_depts:
        st.markdown("<div class='section-header'>تحديث بيانات الأقسام الحالية</div>", unsafe_allow_html=True)
        up_dept = st.selectbox("القسم", all_depts_keys, key="up_dept")
        if up_dept:
            with st.form("update_dept"):
                c1, c2 = st.columns(2)
                with c1: owner = st.text_input("مسؤول القسم", value=data[up_dept].get("owner",""))
                with c2: prefix = st.text_input("رمز القسم (Prefix)", value=data[up_dept].get("prefix","REQ"))
                st.markdown("<div class='btn-primary'>", unsafe_allow_html=True)
                if st.form_submit_button("💾 حفظ التحديثات"):
                    data[up_dept]["owner"] = owner
                    data[up_dept]["prefix"] = prefix
                    save_data(data); st.success("تم التحديث!"); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<br><div class='section-header'>إضافة قسم جديد</div>", unsafe_allow_html=True)
        with st.form("new_dept"):
            c1, c2, c3 = st.columns(3)
            with c1: nd_name = st.text_input("اسم القسم")
            with c2: nd_owner = st.text_input("اسم المسؤول")
            with c3: nd_pref = st.text_input("الرمز (مثال: SLS)")
            st.markdown("<div class='btn-primary'>", unsafe_allow_html=True)
            if st.form_submit_button("➕ إضافة القسم"):
                if nd_name and nd_pref:
                    data[nd_name] = {"total": 0, "completed": 0, "owner": nd_owner, "prefix": nd_pref.upper(), "requirements": []}
                    save_data(data); st.success("تم الإضافة!"); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # --- Tab 3: Backup & Restore ---
    with tab_backup:
        def restore_backup_callback(file_obj):
            try:
                restored_data = json.load(file_obj)
                restored_data = recompute_stats(restored_data)
                save_data(restored_data)
                st.session_state.restore_success = True
            except Exception as e:
                st.session_state.restore_error = True

        if "restore_success" in st.session_state and st.session_state.restore_success:
            st.success("✅ تم استعادة البيانات بنجاح!")
            st.session_state.restore_success = False
        if "restore_error" in st.session_state and st.session_state.restore_error:
            st.error("❌ ملف غير صالح. يرجى التأكد من رفع ملف بصيغة JSON صحيح.")
            st.session_state.restore_error = False

        st.markdown("<div class='section-header'>نسخ واستعادة قاعدة البيانات (JSON)</div>", unsafe_allow_html=True)
        with st.container(border=True):
            col_backup, col_restore = st.columns(2)
            with col_backup:
                st.markdown("**تنزيل نسخة من البيانات الحالية:**")
                json_string = json.dumps(data, ensure_ascii=False, indent=4)
                st.download_button(
                    label="⬇️ تحميل نسخة احتياطية",
                    data=json_string,
                    file_name=f"erp_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            with col_restore:
                st.markdown("**استعادة بيانات من ملف سابق:**")
                uploaded_file = st.file_uploader("اختر ملف النسخة الاحتياطية", type="json", label_visibility="collapsed")
                if uploaded_file is not None:
                    st.button(
                        "⚠️ تأكيد الاستعادة (سيمسح البيانات الحالية)", 
                        type="primary", 
                        use_container_width=True,
                        on_click=restore_backup_callback,
                        args=(uploaded_file,)
                    )

# ── Page: Requirements Management ───────────────────────────────────
elif page == "📝 إدارة المتطلبات":
    st.markdown("<div class='title-container'><h1>📝 إدارة متطلبات النظام</h1></div>", unsafe_allow_html=True)
    
    if not viewable_depts:
        st.warning("ليس لديك صلاحية لرؤية أي أقسام. يرجى مراجعة مدير النظام.")
        st.stop()
        
    st.markdown("<div class='section-header'>إضافة متطلب جديد</div>", unsafe_allow_html=True)
    dept_sel = st.selectbox("القسم", viewable_depts, key="add_req_dept")
    
    def generate_next_id(dept_name):
        prefix = data[dept_name].get("prefix", "REQ")
        reqs = data[dept_name].get("requirements", [])
        max_num = 0
        for r in reqs:
            parts = r["id"].split("-")
            if len(parts) == 2 and parts[0] == prefix:
                try: max_num = max(max_num, int(parts[1]))
                except: pass
        return f"{prefix}-{str(max_num + 1).zfill(3)}"
        
    auto_req_id = generate_next_id(dept_sel)
    
    with st.form("add_req_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: req_title = st.text_input("وصف المتطلب (Title)")
        with col2:
            st.text_input("رقم المتطلب (تلقائي)", value=auto_req_id, disabled=True)
            req_prio = st.selectbox("الأولوية", ["حرج", "عالي", "متوسط", "منخفض"])
        
        st.markdown("<div class='btn-primary'>", unsafe_allow_html=True)
        if st.form_submit_button("➕ إضافة المتطلب"):
            if req_title:
                new_req = {"id": auto_req_id, "title": req_title, "priority": req_prio, "status": "معلق"}
                log_event(new_req, "إنشاء")
                data[dept_sel]["requirements"].append(new_req)
                data = recompute_stats(data)
                save_data(data)
                st.success(f"تمت الإضافة: {auto_req_id}")
                st.rerun()
            else: st.error("يرجى كتابة وصف المتطلب!")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='section-header'>تعديل حالة المتطلبات الحالية</div>", unsafe_allow_html=True)
    edit_dept = st.selectbox("اختر القسم للعمل عليه", viewable_depts, key="edit_dept")
    reqs = data[edit_dept].get("requirements", [])
    
    pen_reqs = [r for r in reqs if r.get("status") == "معلق"]
    com_reqs = [r for r in reqs if r.get("status") == "مكتمل"]
    del_reqs = [r for r in reqs if r.get("status") == "محذوف"]
    
    def get_last_action(req_data):
        if "history" in req_data and len(req_data["history"]) > 0:
            last = req_data["history"][0]
            return f"<span style='font-size:0.75rem; color:{text_muted}; display:block; margin-top:2px;'>📝 {last['action']} بواسطة: <b>{last['user']}</b> ({last['time']})</span>"
        return ""

    st.markdown(f"**⏳ المتطلبات المعلقة ({len(pen_reqs)}):**")
    for r in pen_reqs:
        c1, c2, c3, c4 = st.columns([1.2, 3, 1, 1])
        c1.write(r["id"])
        c2.markdown(f"{r['title']} {get_last_action(r)}", unsafe_allow_html=True)
        if c3.button("✅ إنجاز", key=f"d_{r['id']}"):
            r["status"] = "مكتمل"
            log_event(r, "إنجاز")
            data = recompute_stats(data)
            save_data(data); st.rerun()
        if c4.button("🗑️ حذف", key=f"del_{r['id']}"):
            r["status"] = "محذوف"
            log_event(r, "حذف")
            data = recompute_stats(data)
            save_data(data); st.rerun()
            
    st.markdown(f"**✅ المتطلبات المكتملة ({len(com_reqs)}):**")
    for r in com_reqs:
        c1, c2, c3 = st.columns([1.2, 4, 1])
        c1.write(r["id"])
        c2.markdown(f"~~{r['title']}~~ {get_last_action(r)}", unsafe_allow_html=True)
        if c3.button("↩️ التراجع", key=f"u_{r['id']}"):
            r["status"] = "معلق"
            log_event(r, "تراجع (إعادة لمعلق)")
            data = recompute_stats(data)
            save_data(data); st.rerun()

    st.markdown(f"**🗑️ سلة المحذوفات ({len(del_reqs)}):**")
    with st.container(border=True):
        if not del_reqs:
            st.info("سلة المحذوفات فارغة.")
        else:
            for r in del_reqs:
                c1, c2, c3 = st.columns([1.2, 4, 1])
                c1.write(r["id"])
                c2.markdown(f"{r['title']} {get_last_action(r)}", unsafe_allow_html=True)
                if c3.button("♻️ استرجاع", key=f"res_{r['id']}"):
                    r["status"] = "معلق"
                    log_event(r, "استرجاع")
                    data = recompute_stats(data)
                    save_data(data); st.rerun()

# ── Page: Dashboard ─────────────────────────────────────
elif page == "📊 لوحة المتابعة":
    if not viewable_depts:
        st.warning("ليس لديك صلاحية لرؤية أي أقسام. يرجى مراجعة مدير النظام.")
        st.stop()
        
    filtered_data = {k: v for k, v in data.items() if k in selected_depts and k in viewable_depts}
    st.markdown("<div class='title-container'><h1>📊 لوحة متابعة تطوير نظام ERP</h1></div>", unsafe_allow_html=True)

    total_reqs = sum(d["total"] for d in filtered_data.values())
    total_done = sum(d["completed"] for d in filtered_data.values())
    total_pending = total_reqs - total_done
    overall_pct = round((total_done / total_reqs) * 100, 1) if total_reqs else 0
    critical_count = sum(1 for d in filtered_data.values() for r in d.get("requirements", []) if r.get("priority") == "حرج" and r.get("status") == "معلق")

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='kpi-card kpi-blue'><div class='kpi-label'>نسبة الإنجاز الكلية</div><div class='kpi-value'>{overall_pct}%</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='kpi-card kpi-green'><div class='kpi-label'>المتطلبات المكتملة</div><div class='kpi-value'>{total_done}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='kpi-card kpi-orange'><div class='kpi-label'>المتطلبات المتبقية</div><div class='kpi-value'>{total_pending}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='kpi-card kpi-red'><div class='kpi-label'>متطلبات حرجة معلقة</div><div class='kpi-value'>{critical_count}</div></div>", unsafe_allow_html=True)

    st.markdown(f"<div class='progress-container'><div class='progress-fill' style='width:{overall_pct}%'>{overall_pct}% مكتمل</div></div><br>", unsafe_allow_html=True)

    if view_mode == "ملخص عام":
        col_chart, col_pie = st.columns([3, 2])
        with col_chart:
            st.markdown("<div class='section-header'>نسبة الإنجاز حسب القسم</div>", unsafe_allow_html=True)
            dept_names = list(filtered_data.keys())
            dept_pcts = [round(filtered_data[d]["completed"] / filtered_data[d]["total"] * 100, 1) if filtered_data[d]["total"]>0 else 0 for d in dept_names]
            colors_bar = ['#27AE60' if p==100 else '#4A90D9' if p>=75 else '#F39C12' if p>=50 else '#E74C3C' for p in dept_pcts]
            fig = go.Figure(go.Bar(x=dept_names, y=dept_pcts, marker_color=colors_bar, text=[f"{p}%" for p in dept_pcts], textposition='outside', textfont=dict(color=text_color, size=12)))
            fig.update_layout(plot_bgcolor=plot_bg, paper_bgcolor=paper_bg, yaxis=dict(range=[0,120], gridcolor=grid_color, color=tick_color), xaxis=dict(color=tick_color), margin=dict(t=20, b=10, l=10, r=10), height=300, font=dict(family='Tajawal'))
            st.plotly_chart(fig, use_container_width=True)

        with col_pie:
            st.markdown("<div class='section-header'>توزيع الأولويات للمتطلبات المعلقة</div>", unsafe_allow_html=True)
            all_pending_reqs = [r for d in filtered_data.values() for r in d.get("requirements", []) if r.get("priority") in priority_filter and r.get("status") == "معلق"]
            if all_pending_reqs:
                pc = pd.Series([r["priority"] for r in all_pending_reqs]).value_counts().reset_index()
                pc.columns = ["الأولوية", "العدد"]
                pie_colors = {"حرج":"#E74C3C","عالي":"#F39C12","متوسط":"#F1C40F","منخفض":"#27AE60"}
                fig2 = px.pie(pc, names="الأولوية", values="العدد", color="الأولوية", color_discrete_map=pie_colors, hole=0.5)
                fig2.update_layout(paper_bgcolor=paper_bg, plot_bgcolor=plot_bg, legend=dict(font=dict(color=text_color)), margin=dict(t=20, b=10, l=10, r=10), height=300, font=dict(family='Tajawal'))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("لا توجد متطلبات معلقة مطابقة.")

        st.markdown("<div class='section-header'>بطاقات الأقسام</div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, (dept_name, dept_info) in enumerate(filtered_data.items()):
            pct = round(dept_info["completed"] / dept_info["total"] * 100, 1) if dept_info.get("total", 0) > 0 else 0
            pending = dept_info.get("total", 0) - dept_info.get("completed", 0)
            bar_color = '#27AE60' if pct==100 else '#4A90D9' if pct>=75 else '#F39C12' if pct>=50 else '#E74C3C'
            critical = sum(1 for r in dept_info.get("requirements", []) if r.get("priority") == "حرج" and r.get("status") == "معلق")
            critical_badge = f"<span class='badge badge-critical'>⚠ {critical} حرج</span>" if critical else "<span style='color:#27AE60; font-size:0.8rem'>✅ لا يوجد حرج معلق</span>"
            
            with cols[idx % 3]:
                st.markdown(f"""
                <div class='dept-card'>
                    <div class='dept-name'>🏢 {dept_name}</div>
                    <div class='dept-stats'>المسؤول: {dept_info.get('owner', 'غير محدد')} &nbsp;|&nbsp; المتبقي: {pending} متطلب</div>
                    <div class='mini-bar-bg'><div class='mini-bar-fill' style='width:{pct}%; background:{bar_color}'></div></div>
                    <div style='display:flex; justify-content:space-between; margin-top:8px'>
                        <span style='color:{text_color}; font-weight:700; font-size:1.1rem'>{pct}%</span>{critical_badge}
                    </div>
                </div>""", unsafe_allow_html=True)

    else:
        st.markdown("<div class='section-header'>تفاصيل القسم والمتطلبات وسجل التتبع</div>", unsafe_allow_html=True)
        selected_dept = st.selectbox("اختر القسم", list(filtered_data.keys()))
        if selected_dept:
            dept = filtered_data[selected_dept]
            all_reqs = [r for r in dept.get("requirements", []) if r.get("priority") in priority_filter and r.get("status") != "محذوف"]
            pending_reqs = [r for r in all_reqs if r.get("status") == "معلق"]
            completed_reqs = [r for r in all_reqs if r.get("status") == "مكتمل"]
            
            priority_icons = {"حرج":"🔴", "عالي":"🟠", "متوسط":"🟡", "منخفض":"🟢"}
            badge_classes = {"حرج":"badge-critical", "عالي":"badge-high", "متوسط":"badge-medium", "منخفض":"badge-low"}

            tab_pending, tab_completed = st.tabs([f"المعلقة ({len(pending_reqs)})", f"المكتملة ({len(completed_reqs)})"])
            
            def render_reqs(req_list, is_completed=False):
                if not req_list:
                    st.info("لا توجد متطلبات هنا.")
                    return
                for r in req_list:
                    with st.container():
                        c1, c2, c3, c4, c5 = st.columns([1.2, 4.5, 1.5, 1.5, 1.5])
                        with c1: st.markdown(f"<p style='color:{text_muted}; font-family:monospace'>{r.get('id', '')}</p>", unsafe_allow_html=True)
                        with c2: st.markdown(f"<p style='color:{text_color}; {'text-decoration:line-through' if is_completed else ''}'>{r.get('title', '')}</p>", unsafe_allow_html=True)
                        with c3: st.markdown(f"<span class='badge {badge_classes.get(r.get('priority', 'متوسط'))}'>{priority_icons.get(r.get('priority', 'متوسط'))} {r.get('priority', '')}</span>", unsafe_allow_html=True)
                        with c4: st.markdown(f"<span style='color:{'#27AE60' if is_completed else '#F39C12'}'>{'✅ مكتمل' if is_completed else '⏳ معلق'}</span>", unsafe_allow_html=True)
                        with c5:
                            btn_label = "إخفاء السجل" if r['id'] in st.session_state.show_audit_for else "📋 السجل"
                            if st.button(btn_label, key=f"btn_h_{r['id']}"):
                                if r['id'] in st.session_state.show_audit_for: st.session_state.show_audit_for.remove(r['id'])
                                else: st.session_state.show_audit_for.append(r['id'])
                                st.rerun()
                                
                        if r['id'] in st.session_state.show_audit_for:
                            st.markdown(f"<div style='background:{input_bg}; padding:10px; border-radius:8px; margin-bottom:10px; border:1px solid {card_border}; font-size:0.85rem;'>", unsafe_allow_html=True)
                            if "history" in r and r["history"]:
                                for h in r["history"]:
                                    st.markdown(f"<span style='color:{text_muted}'>- {h.get('action', '')} بواسطة <b>{h.get('user', '')}</b> في {h.get('time', '')}</span><br>", unsafe_allow_html=True)
                            else:
                                st.markdown("<span style='color:#F39C12'>لا يوجد سجل تتبع قديم لهذا المتطلب</span>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                            
                    st.markdown(f"<hr style='margin:4px 0; border-color:{hr_color}'>", unsafe_allow_html=True)

            with tab_pending: render_reqs(pending_reqs, False)
            with tab_completed: render_reqs(completed_reqs, True)

st.divider()
st.markdown(f"<p style='text-align:center; color:{text_muted}; font-size:0.75rem'>لوحة متابعة نظام ERP • فريق تقنية المعلومات • {datetime.now().strftime('%Y-%m-%d')}</p>", unsafe_allow_html=True)
