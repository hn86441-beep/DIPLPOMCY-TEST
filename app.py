# -*- coding: utf-8 -*-
"""
app.py — منصة الإعداد لامتحان السلك الدبلوماسي
تركيز خاص: اللغة الروسية والترجمة الدبلوماسية
================================================
تطبيق Streamlit تفاعلي يضم:
  1) مصطلحات دبلوماسية + بطاقات تعلم (Flashcards) + اختبار ذاتي
  2) محاكي ترجمة دبلوماسية مع تقييم ذكي ثلاثي اللغة
  3) اختبارات تحضيرية (اختيار من متعدد + أسئلة مقالية)
  4) لوحة متابعة التقدم (Dashboard) — لمسة إبداعية لتحفيز المذاكرة
"""

import random
from datetime import datetime

import pandas as pd
import streamlit as st

from utils.data_loader import load_glossary, load_diplomatic_texts, load_mcq
from utils.evaluator import evaluate_translation, evaluate_with_ai

# ------------------------------------------------------------------
# إعدادات الصفحة العامة
# ------------------------------------------------------------------
st.set_page_config(
    page_title="بوابة الإعداد للسلك الدبلوماسي 🇷🇺",
    page_icon="🕊️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# تنسيق CSS مخصص — هوية بصرية دبلوماسية (كحلي/ذهبي) + دعم RTL
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }
    .main { background-color: #0f1b2d; }
    .stApp {
        background: linear-gradient(180deg, #0f1b2d 0%, #13233a 100%);
    }
    h1, h2, h3 { color: #d4af37 !important; }
    p, li, span, label, div { color: #eef2f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #16273f;
        border-radius: 8px 8px 0 0;
        padding: 10px 18px;
        color: #d4af37;
        font-weight: 700;
    }
    .stTabs [aria-selected="true"] {
        background-color: #d4af37 !important;
        color: #0f1b2d !important;
    }
    .metric-card {
        background: #16273f;
        border: 1px solid #d4af37;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .flashcard {
        background: linear-gradient(135deg, #1a2c47, #0f1b2d);
        border: 2px solid #d4af37;
        border-radius: 16px;
        padding: 40px 20px;
        text-align: center;
        min-height: 160px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 4px 14px rgba(0,0,0,0.4);
    }
    .badge {
        display:inline-block; background:#d4af37; color:#0f1b2d;
        padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight:700;
        margin: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# تهيئة حالة الجلسة (Session State) لتتبع تقدم المستخدم
# ------------------------------------------------------------------
defaults = {
    "flash_index": 0,
    "flash_flipped": False,
    "known_terms": set(),
    "unknown_terms": set(),
    "quiz_score": 0,
    "quiz_total": 0,
    "translation_history": [],
    "mcq_answers": {},
    "study_streak_dates": set(),
    "api_key": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# تسجيل يوم المذاكرة الحالي لحساب سلسلة الانتظام (streak)
st.session_state.study_streak_dates.add(datetime.now().strftime("%Y-%m-%d"))

glossary_df = load_glossary()
texts_df = load_diplomatic_texts()
mcq_df = load_mcq()

# ------------------------------------------------------------------
# الشريط الجانبي
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🕊️ بوابة الدبلوماسي")
    st.markdown("**الإعداد لامتحان السلك الدبلوماسي**\nتركيز: اللغة الروسية 🇷🇺")
    st.markdown("---")

    st.markdown("### 🔥 سلسلة المذاكرة")
    st.markdown(
        f"<div class='metric-card'><h2>{len(st.session_state.study_streak_dates)}</h2>"
        f"<p>أيام مذاكرة مسجّلة</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### 📊 إحصائياتك")
    known = len(st.session_state.known_terms)
    total_terms = len(glossary_df)
    st.progress(known / total_terms if total_terms else 0)
    st.caption(f"مصطلحات متقنة: {known} / {total_terms}")

    if st.session_state.quiz_total:
        acc = round(st.session_state.quiz_score / st.session_state.quiz_total * 100, 1)
        st.caption(f"دقة الاختبار الذاتي: {acc}%")

    st.markdown("---")
    st.markdown("### ⚙️ تقييم متقدم بالذكاء الاصطناعي (اختياري)")
    st.caption("أدخل مفتاح Claude API الخاص بك لتفعيل تحليل أسلوبي أعمق للترجمة.")
    st.session_state.api_key = st.text_input("Anthropic API Key", type="password", value=st.session_state.api_key)

    st.markdown("---")
    st.caption("صُنع بعناية لطلاب السلك الدبلوماسي 🎓")

# ------------------------------------------------------------------
# الرأس الرئيسي
# ------------------------------------------------------------------
st.title("🕊️ بوابة الإعداد لامتحان السلك الدبلوماسي")
st.markdown("##### تركيز خاص على اللغة الروسية والترجمة الدبلوماسية 🇷🇺 🇸🇦")

quote_pool = [
    "«الدبلوماسية هي فن قول 'كلب لطيف' حتى تجد حجراً» — وينستون تشرشل",
    "«الكلمة الدبلوماسية الصحيحة توازي فيلقاً من الجيوش» — نابليون بونابرت",
    "«السياسة الخارجية ليست عملاً خيرياً، بل ممارسة لتبادل المصالح» — هنري كيسنجر",
]
st.info(random.choice(quote_pool))

tab1, tab2, tab3, tab4 = st.tabs(
    ["📚 المصطلحات والبطاقات", "🌐 محاكي الترجمة الدبلوماسية", "📝 الاختبارات التحضيرية", "🏆 لوحة التقدم"]
)

# ====================================================================
# التبويب 1: المصطلحات والبطاقات (Glossary & Flashcards)
# ====================================================================
with tab1:
    st.subheader("📚 قاموس المصطلحات الدبلوماسية")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        category_filter = st.selectbox(
            "تصفية حسب الفئة", ["الكل"] + sorted(glossary_df["category"].unique().tolist())
        )
    with col_filter2:
        search_term = st.text_input("🔍 بحث عن مصطلح")

    filtered_df = glossary_df.copy()
    if category_filter != "الكل":
        filtered_df = filtered_df[filtered_df["category"] == category_filter]
    if search_term:
        mask = filtered_df.apply(
            lambda r: search_term.lower() in str(r["term_ar"]).lower()
            or search_term.lower() in str(r["term_en"]).lower()
            or search_term.lower() in str(r["term_ru"]).lower(),
            axis=1,
        )
        filtered_df = filtered_df[mask]

    st.dataframe(
        filtered_df[["term_ar", "term_en", "term_ru", "category", "definition_ar"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "term_ar": "المصطلح (عربي)",
            "term_en": "English",
            "term_ru": "Русский",
            "category": "الفئة",
            "definition_ar": "التعريف",
        },
    )

    st.markdown("---")
    st.subheader("🎴 بطاقات التعلم التفاعلية (Flashcards)")

    upload = st.file_uploader("أو ارفع ملف CSV خاص بمصطلحاتك (نفس أعمدة الجدول أعلاه)", type=["csv"])
    active_df = pd.read_csv(upload) if upload is not None else filtered_df.reset_index(drop=True)

    if len(active_df) == 0:
        st.warning("لا توجد مصطلحات مطابقة لعرضها كبطاقات.")
    else:
        st.session_state.flash_index %= len(active_df)
        row = active_df.iloc[st.session_state.flash_index]

        card_html = f"""
        <div class="flashcard">
            <span class="badge">{row['category']}</span>
            <h2>{row['term_ar'] if not st.session_state.flash_flipped else row['term_ru']}</h2>
            <p style="opacity:0.7">{'اضغط "قلب البطاقة" لرؤية الترجمة الروسية والإنجليزية' if not st.session_state.flash_flipped else f"English: {row['term_en']}"}</p>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
        if st.session_state.flash_flipped:
            st.caption(f"📖 {row['definition_ar']}")

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            if st.button("⬅️ السابق"):
                st.session_state.flash_index -= 1
                st.session_state.flash_flipped = False
                st.rerun()
        with c2:
            if st.button("🔄 قلب البطاقة"):
                st.session_state.flash_flipped = not st.session_state.flash_flipped
                st.rerun()
        with c3:
            if st.button("➡️ التالي"):
                st.session_state.flash_index += 1
                st.session_state.flash_flipped = False
                st.rerun()
        with c4:
            if st.button("✅ أتقنتها"):
                st.session_state.known_terms.add(row["term_ar"])
                st.session_state.unknown_terms.discard(row["term_ar"])
                st.session_state.flash_index += 1
                st.session_state.flash_flipped = False
                st.rerun()
        with c5:
            if st.button("❌ أحتاج مراجعة"):
                st.session_state.unknown_terms.add(row["term_ar"])
                st.session_state.flash_index += 1
                st.session_state.flash_flipped = False
                st.rerun()

        st.caption(f"البطاقة {st.session_state.flash_index + 1} من {len(active_df)}")

    st.markdown("---")
    st.subheader("🧠 الاختبار الذاتي السريع (مصطلح ↔ ترجمة)")

    if st.button("🎲 ابدأ سؤالاً عشوائياً"):
        st.session_state.quiz_row = glossary_df.sample(1).iloc[0]
        st.session_state.quiz_options = None

    if "quiz_row" in st.session_state:
        qr = st.session_state.quiz_row
        st.write(f"ما هي الترجمة **الروسية** الصحيحة للمصطلح: **{qr['term_ar']}** ؟")

        if st.session_state.get("quiz_options") is None:
            wrong_options = glossary_df[glossary_df["term_ar"] != qr["term_ar"]]["term_ru"].sample(3).tolist()
            options = wrong_options + [qr["term_ru"]]
            random.shuffle(options)
            st.session_state.quiz_options = options

        choice = st.radio("اختر الإجابة:", st.session_state.quiz_options, key="quiz_choice")
        if st.button("تحقق من الإجابة"):
            st.session_state.quiz_total += 1
            if choice == qr["term_ru"]:
                st.success("✅ إجابة صحيحة! أحسنت.")
                st.session_state.quiz_score += 1
                st.session_state.known_terms.add(qr["term_ar"])
            else:
                st.error(f"❌ غير صحيح. الإجابة الصحيحة: **{qr['term_ru']}**")
                st.session_state.unknown_terms.add(qr["term_ar"])

# ====================================================================
# التبويب 2: محاكي الترجمة الدبلوماسية + التقييم الذكي
# ====================================================================
with tab2:
    st.subheader("🌐 محاكي نصوص الترجمة الدبلوماسية")
    st.caption("اختر نصاً رسمياً، ترجمه بنفسك، ثم قارن أداءك بمحرك التقييم الذكي ثلاثي اللغة.")

    text_titles = texts_df["title_ar"].tolist()
    selected_title = st.selectbox("اختر النص الدبلوماسي:", text_titles)
    text_row = texts_df[texts_df["title_ar"] == selected_title].iloc[0]

    lang_labels = {"ar": "العربية", "en": "الإنجليزية", "ru": "الروسية"}
    st.markdown(
        f"**اتجاه الترجمة:** {lang_labels[text_row['source_lang']]} ⬅️ {lang_labels[text_row['target_lang']]} "
        f"&nbsp; | &nbsp; **مستوى الصعوبة:** {text_row['difficulty']}"
    )

    st.markdown("##### 📄 النص المصدر")
    st.text_area("النص الأصلي", value=text_row["source_text"], height=120, disabled=True, label_visibility="collapsed")

    st.markdown("##### ✍️ ترجمتك")
    user_translation = st.text_area(
        "اكتب ترجمتك هنا", height=140, key=f"trans_{text_row['id']}", label_visibility="collapsed"
    )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        evaluate_clicked = st.button("🔎 قيّم ترجمتي", type="primary")
    with col_b:
        show_model = st.checkbox("👁️ أظهر النموذج المرجعي")

    if show_model:
        st.markdown("##### 🏛️ النموذج المرجعي (احترافي)")
        st.success(text_row["model_translation"])

    if evaluate_clicked:
        if not user_translation.strip():
            st.warning("يرجى كتابة ترجمتك أولاً.")
        else:
            result = evaluate_translation(
                user_text=user_translation,
                reference_text=text_row["model_translation"],
                target_lang=text_row["target_lang"],
                glossary_df=glossary_df,
            )
            st.session_state.translation_history.append(
                {"title": selected_title, "score": result.overall_score, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
            )

            st.markdown("### 📊 تقرير التقييم")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("النتيجة الإجمالية", f"{result.overall_score}")
            m2.metric("التشابه الدلالي", f"{result.similarity_score}%")
            m3.metric("المصطلحات", f"{result.terminology_score}%")
            m4.metric("الاكتمال", f"{result.completeness_score}%")
            m5.metric("الرسمية اللغوية", f"{result.formality_score}%")

            st.markdown(f"**التقييم العام:** {result.grade_label_ar}")

            if result.missing_terms:
                st.warning("مصطلحات دبلوماسية فاتتك: " + "، ".join(result.missing_terms))
            if result.matched_terms:
                st.info("مصطلحات وظّفتها بنجاح: " + "، ".join(result.matched_terms))

            with st.expander("🔍 مقارنة تفصيلية (فروقات النص)"):
                st.markdown(result.diff_html, unsafe_allow_html=True)

            lang_tab_ar, lang_tab_en, lang_tab_ru = st.tabs(["🇸🇦 تقرير عربي", "🇬🇧 English Report", "🇷🇺 Отчёт на русском"])
            with lang_tab_ar:
                st.text(result.feedback_ar)
            with lang_tab_en:
                st.text(result.feedback_en)
            with lang_tab_ru:
                st.text(result.feedback_ru)

            if st.session_state.api_key:
                with st.spinner("جارٍ التحليل المتقدم عبر الذكاء الاصطناعي..."):
                    try:
                        ai_feedback = evaluate_with_ai(
                            user_translation, text_row["model_translation"], text_row["target_lang"], st.session_state.api_key
                        )
                        st.markdown("### 🤖 تحليل احترافي إضافي (Claude API)")
                        st.markdown(ai_feedback)
                    except Exception as e:
                        st.error(f"تعذّر الاتصال بالـ API: {e}")

# ====================================================================
# التبويب 3: الاختبارات التحضيرية (MCQ + Essay)
# ====================================================================
with tab3:
    st.subheader("📝 الاختبارات التحضيرية")

    mode = st.radio("اختر نوع الاختبار:", ["اختيار من متعدد (MCQ)", "أسئلة مقالية (Essay)"], horizontal=True)

    if mode == "اختيار من متعدد (MCQ)":
        mcqs = mcq_df[mcq_df["type"] == "mcq"].reset_index(drop=True)
        score = 0
        with st.form("mcq_form"):
            answers = {}
            for _, q in mcqs.iterrows():
                question_text = q["question_ar"] if pd.notna(q["question_ar"]) and str(q["question_ar"]).strip() else q["question_ru"]
                st.markdown(f"**{int(q['id'])}. {question_text}**")
                if pd.notna(q["question_ru"]) and str(q["question_ru"]).strip() and question_text != q["question_ru"]:
                    st.caption(f"🇷🇺 {q['question_ru']}")
                options = {"A": q["option_a"], "B": q["option_b"], "C": q["option_c"], "D": q["option_d"]}
                choice = st.radio(
                    "اختر:",
                    list(options.keys()),
                    format_func=lambda k, o=options: f"{k}) {o}",
                    key=f"mcq_{q['id']}",
                    horizontal=True,
                    label_visibility="collapsed",
                )
                answers[q["id"]] = choice
                st.markdown("---")

            submitted = st.form_submit_button("📤 تسليم الاختبار", type="primary")

        if submitted:
            correct = 0
            for _, q in mcqs.iterrows():
                if answers[q["id"]] == q["correct_answer"]:
                    correct += 1
            pct = round(correct / len(mcqs) * 100, 1)
            st.success(f"🎯 نتيجتك: {correct} / {len(mcqs)} ({pct}%)")

            with st.expander("📋 مراجعة الإجابات والشروحات"):
                for _, q in mcqs.iterrows():
                    is_correct = answers[q["id"]] == q["correct_answer"]
                    icon = "✅" if is_correct else "❌"
                    question_text = q["question_ar"] if pd.notna(q["question_ar"]) and str(q["question_ar"]).strip() else q["question_ru"]
                    st.markdown(f"{icon} **{question_text}** — الإجابة الصحيحة: {q['correct_answer']}")
                    st.caption(q["explanation_ar"])

    else:
        essays = mcq_df[mcq_df["type"] == "essay"].reset_index(drop=True)
        for _, q in essays.iterrows():
            st.markdown(f"**سؤال {int(q['id'])}:** {q['question_ar']}")
            st.text_area("اكتب إجابتك هنا:", height=180, key=f"essay_{q['id']}")
            with st.expander("🧭 معايير التقييم"):
                st.caption(q["explanation_ar"])
            st.markdown("---")
        st.info("💡 نصيحة: بعد كتابة إجابتك، يمكنك لصقها في تبويب «محاكي الترجمة» كنص مصدر لتقييم جودة لغتك الروسية إن رغبت.")

# ====================================================================
# التبويب 4: لوحة التقدم (Dashboard) — اللمسة الإبداعية
# ====================================================================
with tab4:
    st.subheader("🏆 لوحة متابعة تقدمك")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"<div class='metric-card'><h1>{len(st.session_state.known_terms)}</h1>"
            f"<p>مصطلح متقن ✅</p></div>", unsafe_allow_html=True
        )
    with c2:
        acc = (
            round(st.session_state.quiz_score / st.session_state.quiz_total * 100, 1)
            if st.session_state.quiz_total else 0
        )
        st.markdown(
            f"<div class='metric-card'><h1>{acc}%</h1><p>دقة الاختبارات الذاتية 🎯</p></div>",
            unsafe_allow_html=True,
        )
    with c3:
        avg_trans = (
            round(sum(h["score"] for h in st.session_state.translation_history) / len(st.session_state.translation_history), 1)
            if st.session_state.translation_history else 0
        )
        st.markdown(
            f"<div class='metric-card'><h1>{avg_trans}</h1><p>متوسط درجات الترجمة 🌐</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if st.session_state.translation_history:
        st.markdown("### 📈 تطور درجات الترجمة عبر الزمن")
        hist_df = pd.DataFrame(st.session_state.translation_history)
        st.line_chart(hist_df, x="date", y="score")
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.info("لم تُقيّم أي ترجمة بعد. توجّه إلى تبويب «محاكي الترجمة» للبدء.")

    if st.session_state.unknown_terms:
        st.markdown("### 🔁 مصطلحات بحاجة لمراجعة")
        for t in sorted(st.session_state.unknown_terms):
            st.markdown(f"- {t}")

    st.markdown("---")
    st.markdown("### 🎯 نصيحة اليوم")
    tips = [
        "راجع 5 مصطلحات جديدة يومياً بدلاً من 30 مصطلحاً مرة واحدة — التكرار المتباعد أفعل للحفظ.",
        "عند الترجمة الدبلوماسية، حافظ على درجة الرسمية نفسها في اللغة الهدف، لا تُبسّط الأسلوب.",
        "استمع لنشرات الأخبار الروسية الرسمية (RT بالعربية / ТАСС) لتعزيز حصيلتك من المصطلحات الحيّة.",
        "تدرّب على الترجمة الفورية الذهنية: اقرأ جملة وترجمها شفهياً خلال 10 ثوانٍ.",
    ]
    st.success(random.choice(tips))
