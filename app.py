# -*- coding: utf-8 -*-
"""
app.py — منصة الإعداد لامتحان السلك الدبلوماسي (نسخة ملف واحد Self-Contained)
تركيز خاص: اللغة الروسية والترجمة الدبلوماسية
================================================================
ملف واحد يضم كل شيء: البيانات + محرك التقييم + الواجهة، تجنباً لأي
مشاكل استيراد (ModuleNotFoundError) عند النشر على Streamlit Cloud.

الميزات:
  1) قاموس مصطلحات + بطاقات تعلّم بنظام Leitner (تكرار متباعد حقيقي)
  2) اختبار ذاتي عشوائي
  3) محاكي ترجمة دبلوماسية + محرك تقييم ذكي ثلاثي اللغة (عربي/إنجليزي/روسي)
  4) اختبارات تحضيرية (MCQ + مقالية)
  5) لوحة تقدم مع تصدير/استيراد التقدم كملف JSON (لحفظ التقدم بين الجلسات دون تسجيل دخول)
  6) كلمة اليوم + نصائح تحفيزية
"""

import re
import io
import json
import random
import difflib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ============================================================================
# 1) البيانات المضمّنة (لا حاجة لملفات CSV خارجية إطلاقاً)
# ============================================================================

GLOSSARY = [
    {"term_ar": "السيادة الوطنية", "term_en": "National Sovereignty", "term_ru": "Национальный суверенитет", "category": "سياسي", "definition_ar": "حق الدولة في ممارسة سلطتها الكاملة على إقليمها دون تدخل خارجي"},
    {"term_ar": "حق النقض (الفيتو)", "term_en": "Veto Power", "term_ru": "Право вето", "category": "سياسي", "definition_ar": "صلاحية تمنح لعضو دائم في مجلس الأمن لإسقاط أي قرار"},
    {"term_ar": "اتفاقية فيينا للعلاقات الدبلوماسية", "term_en": "Vienna Convention on Diplomatic Relations", "term_ru": "Венская конвенция о дипломатических сношениях", "category": "قانوني", "definition_ar": "معاهدة دولية لعام 1961 تنظم العلاقات الدبلوماسية بين الدول"},
    {"term_ar": "الحصانة الدبلوماسية", "term_en": "Diplomatic Immunity", "term_ru": "Дипломатический иммунитет", "category": "قانوني", "definition_ar": "حماية قانونية تمنح للدبلوماسيين من الملاحقة القضائية في الدولة المضيفة"},
    {"term_ar": "شخصية غير مرغوب فيها", "term_en": "Persona Non Grata", "term_ru": "Персона нон грата", "category": "قانوني", "definition_ar": "مصطلح يشير إلى دبلوماسي مرفوض من قبل الدولة المضيفة"},
    {"term_ar": "مذكرة تفاهم", "term_en": "Memorandum of Understanding", "term_ru": "Меморандум о взаимопонимании", "category": "قانوني", "definition_ar": "وثيقة تعبر عن اتفاق مبدئي غير ملزم قانونياً بين طرفين"},
    {"term_ar": "العقوبات الاقتصادية", "term_en": "Economic Sanctions", "term_ru": "Экономические санкции", "category": "اقتصادي", "definition_ar": "تدابير تقييدية تفرضها دولة أو منظمة على دولة أخرى"},
    {"term_ar": "التعريفة الجمركية", "term_en": "Customs Tariff", "term_ru": "Таможенный тариф", "category": "اقتصادي", "definition_ar": "ضريبة تفرض على السلع المستوردة أو المصدرة"},
    {"term_ar": "ميزان المدفوعات", "term_en": "Balance of Payments", "term_ru": "Платёжный баланс", "category": "اقتصادي", "definition_ar": "سجل لجميع المعاملات الاقتصادية بين دولة وبقية العالم"},
    {"term_ar": "منظمة التجارة العالمية", "term_en": "World Trade Organization", "term_ru": "Всемирная торговая организация", "category": "اقتصادي", "definition_ar": "منظمة دولية تنظم التجارة بين الدول"},
    {"term_ar": "القرار الأممي", "term_en": "UN Resolution", "term_ru": "Резолюция ООН", "category": "سياسي", "definition_ar": "قرار صادر عن هيئة تابعة للأمم المتحدة"},
    {"term_ar": "الوساطة الدبلوماسية", "term_en": "Diplomatic Mediation", "term_ru": "Дипломатическое посредничество", "category": "سياسي", "definition_ar": "تدخل طرف ثالث لتسهيل التفاوض بين طرفين متنازعين"},
    {"term_ar": "التصعيد العسكري", "term_en": "Military Escalation", "term_ru": "Военная эскалация", "category": "سياسي", "definition_ar": "تصاعد حدة النزاع نحو استخدام القوة العسكرية"},
    {"term_ar": "وقف إطلاق النار", "term_en": "Ceasefire", "term_ru": "Прекращение огня", "category": "سياسي", "definition_ar": "اتفاق مؤقت لوقف الأعمال القتالية"},
    {"term_ar": "المفوضية السامية لشؤون اللاجئين", "term_en": "UNHCR", "term_ru": "Верховный комиссар ООН по делам беженцев", "category": "قانوني", "definition_ar": "وكالة أممية تعنى بحماية اللاجئين"},
    {"term_ar": "اعتماد أوراق السفير", "term_en": "Presentation of Credentials", "term_ru": "Вручение верительных грамот", "category": "دبلوماسي", "definition_ar": "مراسم تقديم السفير أوراق اعتماده لرئيس الدولة المضيفة"},
    {"term_ar": "القمة الثنائية", "term_en": "Bilateral Summit", "term_ru": "Двусторонний саммит", "category": "دبلوماسي", "definition_ar": "لقاء رفيع المستوى بين ممثلي دولتين"},
    {"term_ar": "التعددية القطبية", "term_en": "Multipolarity", "term_ru": "Многополярность", "category": "سياسي", "definition_ar": "نظام دولي يتوزع فيه النفوذ على عدة أقطاب قوة"},
    {"term_ar": "حزام الأمن الإقليمي", "term_en": "Regional Security Belt", "term_ru": "Пояс региональной безопасности", "category": "سياسي", "definition_ar": "ترتيبات أمنية جماعية بين دول متجاورة"},
    {"term_ar": "الدبلوماسية الوقائية", "term_en": "Preventive Diplomacy", "term_ru": "Превентивная дипломатия", "category": "سياسي", "definition_ar": "إجراءات لمنع نشوب النزاعات قبل تفاقمها"},
    {"term_ar": "التطبيع الدبلوماسي", "term_en": "Diplomatic Normalization", "term_ru": "Дипломатическая нормализация", "category": "دبلوماسي", "definition_ar": "استعادة العلاقات الرسمية الكاملة بين دولتين بعد قطيعة"},
    {"term_ar": "الملحق العسكري", "term_en": "Military Attaché", "term_ru": "Военный атташе", "category": "دبلوماسي", "definition_ar": "ضابط عسكري يمثل بلاده في بعثة دبلوماسية"},
]

TEXTS = [
    {"id": 1, "title_ar": "بيان مشترك حول العلاقات الثنائية", "source_lang": "ru", "target_lang": "ar",
     "source_text": "Стороны подтвердили приверженность дальнейшему укреплению стратегического партнёрства и договорились продолжить консультации по региональным вопросам, представляющим взаимный интерес.",
     "model_translation": "أكد الطرفان التزامهما بمواصلة تعزيز الشراكة الاستراتيجية، واتفقا على استمرار المشاورات بشأن القضايا الإقليمية ذات الاهتمام المشترك.",
     "difficulty": "متوسط"},
    {"id": 2, "title_ar": "تصريح وزاري حول وقف إطلاق النار", "source_lang": "ar", "target_lang": "ru",
     "source_text": "دعت وزارة الخارجية جميع الأطراف إلى الالتزام الكامل بوقف إطلاق النار، والامتناع عن أي أعمال من شأنها تصعيد الموقف الميداني.",
     "model_translation": "Министерство иностранных дел призвало все стороны полностью соблюдать режим прекращения огня и воздерживаться от любых действий, способных привести к эскалации ситуации на месте.",
     "difficulty": "متوسط"},
    {"id": 3, "title_ar": "بيان حول العقوبات الاقتصادية", "source_lang": "ru", "target_lang": "ar",
     "source_text": "Российская сторона выразила серьёзную обеспокоенность введением новых односторонних санкций, заявив, что подобные меры противоречат нормам международного права и Уставу ООН.",
     "model_translation": "أعرب الجانب الروسي عن قلقه البالغ إزاء فرض عقوبات أحادية جديدة، مؤكداً أن مثل هذه الإجراءات تتعارض مع قواعد القانون الدولي وميثاق الأمم المتحدة.",
     "difficulty": "صعب"},
    {"id": 4, "title_ar": "دعوة لقمة إقليمية", "source_lang": "ar", "target_lang": "ru",
     "source_text": "وجهت المملكة الدعوة لعقد قمة إقليمية طارئة لبحث سبل تعزيز الأمن الجماعي ومواجهة التحديات الاقتصادية المشتركة.",
     "model_translation": "Королевство направило приглашение к проведению внеочередного регионального саммита для обсуждения путей укрепления коллективной безопасности и решения общих экономических проблем.",
     "difficulty": "صعب"},
    {"id": 5, "title_ar": "مذكرة تفاهم بشأن التعاون العلمي", "source_lang": "ru", "target_lang": "ar",
     "source_text": "Стороны подписали меморандум о взаимопонимании в области научного и технологического сотрудничества, включая обмен студентами и совместные исследовательские программы.",
     "model_translation": "وقّع الطرفان مذكرة تفاهم في مجال التعاون العلمي والتكنولوجي، تشمل تبادل الطلاب وبرامج البحث المشترك.",
     "difficulty": "سهل"},
    {"id": 6, "title_ar": "بيان حول حرية الملاحة", "source_lang": "ar", "target_lang": "ru",
     "source_text": "شددت الدولة على أهمية ضمان حرية الملاحة الدولية في الممرات المائية الاستراتيجية، وفقاً لأحكام القانون الدولي للبحار.",
     "model_translation": "Государство подчеркнуло важность обеспечения свободы международного судоходства в стратегических морских проливах в соответствии с положениями международного морского права.",
     "difficulty": "متوسط"},
    {"id": 7, "title_ar": "تصريح حول التطبيع الدبلوماسي", "source_lang": "ru", "target_lang": "ar",
     "source_text": "Обе стороны выразили готовность к полной нормализации дипломатических отношений и обмену послами в ближайшее время.",
     "model_translation": "أعرب الطرفان عن استعدادهما للتطبيع الكامل للعلاقات الدبلوماسية وتبادل السفراء في القريب العاجل.",
     "difficulty": "سهل"},
]

MCQ = [
    {"id": 1, "type": "mcq", "question_ar": "ما هو العام الذي أُبرمت فيه اتفاقية فيينا للعلاقات الدبلوماسية؟", "question_ru": "", "option_a": "1955", "option_b": "1961", "option_c": "1970", "option_d": "1985", "correct_answer": "B", "explanation_ar": "أُبرمت اتفاقية فيينا للعلاقات الدبلوماسية عام 1961 وتُعد الأساس القانوني الدولي لتنظيم العلاقات الدبلوماسية.", "category": "قانوني"},
    {"id": 2, "type": "mcq", "question_ar": "أي عضو من أعضاء مجلس الأمن الدولي لا يملك حق النقض (الفيتو)؟", "question_ru": "", "option_a": "روسيا", "option_b": "الصين", "option_c": "ألمانيا", "option_d": "فرنسا", "correct_answer": "C", "explanation_ar": "الأعضاء الدائمون الخمسة الذين يملكون حق الفيتو هم: الولايات المتحدة، روسيا، الصين، فرنسا، والمملكة المتحدة. ألمانيا ليست عضواً دائماً.", "category": "سياسي"},
    {"id": 3, "type": "mcq", "question_ar": "ماذا يعني مصطلح Persona Non Grata؟", "question_ru": "", "option_a": "دبلوماسي معتمد حديثاً", "option_b": "شخصية مرفوضة من الدولة المضيفة", "option_c": "مبعوث خاص للأمم المتحدة", "option_d": "مستشار اقتصادي", "correct_answer": "B", "explanation_ar": "يستخدم هذا المصطلح للإشارة إلى دبلوماسي تعلن الدولة المضيفة رفضها له وتطلب استبداله أو مغادرته.", "category": "قانوني"},
    {"id": 4, "type": "mcq", "question_ar": "ماذا يعني تعبير 'вручение верительных грамот'؟", "question_ru": "Что означает термин «вручение верительных грамот»?", "option_a": "توقيع اتفاقية تجارية", "option_b": "مراسم تقديم أوراق اعتماد السفير", "option_c": "عقد قمة ثنائية", "option_d": "فرض عقوبات دبلوماسية", "correct_answer": "B", "explanation_ar": "هذا التعبير يعني مراسم تقديم السفير أوراق اعتماده رسمياً لرئيس الدولة المضيفة.", "category": "دبلوماسي"},
    {"id": 5, "type": "mcq", "question_ar": "ما المقصود بـ'التعددية القطبية' في العلاقات الدولية؟", "question_ru": "", "option_a": "هيمنة قوة عظمى واحدة على النظام الدولي", "option_b": "توزع النفوذ الدولي على عدة أقطاب قوة", "option_c": "اتحاد الدول في منظمة واحدة", "option_d": "إلغاء مجلس الأمن الدولي", "correct_answer": "B", "explanation_ar": "التعددية القطبية تصف نظاماً دولياً يتوزع فيه ميزان القوى والنفوذ بين عدة قوى كبرى بدلاً من هيمنة قوة واحدة.", "category": "سياسي"},
    {"id": 6, "type": "mcq", "question_ar": "أي من التالي يُعد مثالاً على 'الدبلوماسية الوقائية'؟", "question_ru": "", "option_a": "فرض عقوبات اقتصادية بعد اندلاع حرب", "option_b": "إرسال بعثة مراقبة أممية لمنع تصاعد نزاع حدودي", "option_c": "إعلان الحرب رسمياً", "option_d": "سحب السفير من دولة معادية", "correct_answer": "B", "explanation_ar": "الدبلوماسية الوقائية تهدف إلى منع نشوب النزاعات قبل تفاقمها، ومن أمثلتها إيفاد بعثات المراقبة والوساطة المبكرة.", "category": "سياسي"},
    {"id": 7, "type": "mcq", "question_ar": "ما الترجمة الروسية الصحيحة لمصطلح 'الحصانة الدبلوماسية'؟", "question_ru": "", "option_a": "Дипломатическая нота", "option_b": "Дипломатический иммунитет", "option_c": "Дипломатический протокол", "option_d": "Дипломатический корпус", "correct_answer": "B", "explanation_ar": "'Дипломатический иммунитет' هي الترجمة الروسية الدقيقة لمصطلح الحصانة الدبلوماسية.", "category": "لغوي"},
]

ESSAYS = [
    {"id": 8, "question_ar": "اكتب مقالاً موجزاً (150-200 كلمة) باللغة الروسية حول أهمية الدبلوماسية الوقائية في منع النزاعات الإقليمية.", "explanation_ar": "يُقيَّم المقال بناءً على: صحة القواعد النحوية الروسية، استخدام المصطلحات الدبلوماسية الدقيقة، ترابط الأفكار، والقدرة على الإقناع."},
    {"id": 9, "question_ar": "ناقش دور منظمة الأمم المتحدة في تنظيم العلاقات الاقتصادية بين الدول، مستخدماً ثلاثة مصطلحات دبلوماسية على الأقل.", "explanation_ar": "يُقيَّم المقال بناءً على: الدقة المفاهيمية، توظيف المصطلحات الصحيحة، بناء حجة منطقية متماسكة."},
    {"id": 10, "question_ar": "بالروسية: عبّر عن رأيك حول أهمية الحصانة الدبلوماسية وحدودها القانونية في العلاقات الدولية المعاصرة.", "explanation_ar": "يُقيَّم بناءً على: الدقة الاصطلاحية، سلامة التركيب النحوي الروسي، ووضوح الحجة القانونية."},
]

# ============================================================================
# 2) محرك تقييم الترجمة الذكي (ثلاثي اللغة)
# ============================================================================

FORMALITY_MARKERS = {
    "ar": ["بموجب", "وفقاً ل", "وفقا ل", "فخامة", "معالي", "سعادة", "يشرفني", "أكدت", "أعربت",
           "شددت", "دعت", "التزام", "بالنيابة عن", "إثر", "من جانبه", "الجانبين", "الطرفين",
           "في هذا السياق", "تجدر الإشارة"],
    "en": ["pursuant to", "in accordance with", "his excellency", "her excellency", "on behalf of",
           "the parties", "reaffirmed", "expressed", "underscored", "hereby", "with regard to",
           "in this context", "shall", "commitment"],
    "ru": ["в соответствии с", "стороны", "выразил", "подчеркнул", "подтвердил", "от имени",
           "его превосходительство", "её превосходительство", "в связи с", "настоящим",
           "обязательство", "в рамках"],
}
INFORMALITY_PENALTY_WORDS = {
    "ar": ["يعني", "بصراحة", "حلو", "تمام", "اوكي", "أوكي"],
    "en": ["gonna", "wanna", "kinda", "stuff", "guys", "ok", "okay"],
    "ru": ["короче", "типа", "ладно", "окей", "клёво"],
}


@dataclass
class EvaluationResult:
    overall_score: float
    similarity_score: float
    terminology_score: float
    completeness_score: float
    formality_score: float
    matched_terms: list = field(default_factory=list)
    missing_terms: list = field(default_factory=list)
    feedback_ar: str = ""
    feedback_en: str = ""
    feedback_ru: str = ""
    diff_html: str = ""
    grade_label_ar: str = ""


def _normalize(text: str, lang: str) -> str:
    text = text.strip()
    if lang == "ar":
        text = re.sub(r"[\u064B-\u0652\u0670\u0640]", "", text)
    else:
        text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_terms_for_text(text: str, lang: str, glossary_df: pd.DataFrame) -> set:
    col = {"ar": "term_ar", "en": "term_en", "ru": "term_ru"}[lang]
    norm_text = _normalize(text, lang)
    found = set()
    for term in glossary_df[col].dropna().unique():
        norm_term = _normalize(str(term), lang)
        if norm_term and norm_term in norm_text:
            found.add(term)
    return found


def _similarity_score(user_text: str, reference_text: str, lang: str) -> float:
    a = _normalize(user_text, lang)
    b = _normalize(reference_text, lang)
    if not a or not b:
        return 0.0
    try:
        vectorizer = TfidfVectorizer(analyzer="word", token_pattern=r"(?u)\b\w+\b")
        tfidf = vectorizer.fit_transform([a, b])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(sim) * 100, 1)
    except ValueError:
        seq_sim = difflib.SequenceMatcher(None, a, b).ratio()
        return round(seq_sim * 100, 1)


def _completeness_score(user_text: str, reference_text: str) -> float:
    len_user = len(user_text.split())
    len_ref = len(reference_text.split())
    if len_ref == 0:
        return 0.0
    ratio = len_user / len_ref
    if 0.85 <= ratio <= 1.25:
        return 100.0
    elif ratio < 0.85:
        return round(max(0.0, ratio / 0.85) * 100, 1)
    else:
        excess = ratio - 1.25
        return round(max(0.0, 100 - excess * 60), 1)


def _formality_score(user_text: str, lang: str) -> float:
    norm = _normalize(user_text, lang)
    markers = FORMALITY_MARKERS.get(lang, [])
    informal = INFORMALITY_PENALTY_WORDS.get(lang, [])
    hits = sum(1 for m in markers if _normalize(m, lang) in norm)
    penalties = sum(1 for w in informal if _normalize(w, lang) in norm)
    base = min(100.0, 55 + hits * 15)
    base -= penalties * 20
    return round(max(0.0, min(100.0, base)), 1)


def _terminology_score(user_text: str, reference_text: str, lang: str, glossary_df: pd.DataFrame) -> tuple:
    ref_terms = _extract_terms_for_text(reference_text, lang, glossary_df)
    user_terms = _extract_terms_for_text(user_text, lang, glossary_df)
    if not ref_terms:
        return 100.0, [], []
    matched = ref_terms & user_terms
    missing = ref_terms - user_terms
    score = round((len(matched) / len(ref_terms)) * 100, 1)
    return score, sorted(matched), sorted(missing)


def _make_diff_html(user_text: str, reference_text: str) -> str:
    sm = difflib.SequenceMatcher(None, user_text.split(), reference_text.split())
    parts = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        user_chunk = " ".join(user_text.split()[i1:i2])
        ref_chunk = " ".join(reference_text.split()[j1:j2])
        if tag == "equal":
            parts.append(f"<span>{user_chunk}</span>")
        elif tag == "replace":
            parts.append(f"<span style='background:#ffe3e3;text-decoration:line-through'>{user_chunk}</span> "
                          f"<span style='background:#d3f9d8'>{ref_chunk}</span>")
        elif tag == "delete":
            parts.append(f"<span style='background:#d3f9d8'>+ {ref_chunk}</span>")
        elif tag == "insert":
            parts.append(f"<span style='background:#ffe3e3;text-decoration:line-through'>{user_chunk}</span>")
    return " ".join(parts)


def _grade_label(score: float) -> str:
    if score >= 90:
        return "ممتاز — بمستوى مترجم دبلوماسي محترف 🏅"
    elif score >= 75:
        return "جيد جداً — قريب من الاحتراف مع ملاحظات بسيطة 👍"
    elif score >= 60:
        return "مقبول — يحتاج تحسين في الدقة الاصطلاحية 📘"
    elif score >= 40:
        return "ضعيف — راجع المفردات الدبلوماسية الأساسية 📖"
    else:
        return "يحتاج إعادة عمل جوهرية 🔄"


def evaluate_translation(user_text, reference_text, target_lang, glossary_df, weights=None) -> EvaluationResult:
    weights = weights or {"similarity": 0.40, "terminology": 0.30, "completeness": 0.15, "formality": 0.15}
    similarity = _similarity_score(user_text, reference_text, target_lang)
    completeness = _completeness_score(user_text, reference_text)
    formality = _formality_score(user_text, target_lang)
    terminology, matched, missing = _terminology_score(user_text, reference_text, target_lang, glossary_df)

    overall = round(
        similarity * weights["similarity"] + terminology * weights["terminology"]
        + completeness * weights["completeness"] + formality * weights["formality"], 1
    )
    diff_html = _make_diff_html(user_text, reference_text)

    fb_ar = (f"النتيجة الإجمالية: {overall}/100 — {_grade_label(overall)}\n"
             f"• التشابه مع النموذج: {similarity}%\n"
             f"• تغطية المصطلحات الدبلوماسية: {terminology}%" +
             (f" (فاتتك: {', '.join(missing)})" if missing else " (تغطية كاملة ✅)") +
             f"\n• اكتمال المحتوى: {completeness}%\n• مستوى الرسمية الدبلوماسية: {formality}%")
    fb_en = (f"Overall Score: {overall}/100\n"
             f"• Semantic similarity to reference: {similarity}%\n"
             f"• Diplomatic terminology coverage: {terminology}%" +
             (f" (missing: {', '.join(missing)})" if missing else " (full coverage ✅)") +
             f"\n• Content completeness: {completeness}%\n• Diplomatic register/formality: {formality}%")
    fb_ru = (f"Общий балл: {overall}/100\n"
             f"• Смысловое сходство с эталоном: {similarity}%\n"
             f"• Охват дипломатической терминологии: {terminology}%" +
             (f" (пропущено: {', '.join(missing)})" if missing else " (полный охват ✅)") +
             f"\n• Полнота содержания: {completeness}%\n• Дипломатический регистр: {formality}%")

    return EvaluationResult(
        overall_score=overall, similarity_score=similarity, terminology_score=terminology,
        completeness_score=completeness, formality_score=formality, matched_terms=matched,
        missing_terms=missing, feedback_ar=fb_ar, feedback_en=fb_en, feedback_ru=fb_ru,
        diff_html=diff_html, grade_label_ar=_grade_label(overall),
    )


def evaluate_with_ai(user_text, reference_text, target_lang, api_key) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    lang_names = {"ar": "العربية", "en": "الإنجليزية", "ru": "الروسية"}
    prompt = f"""أنت خبير ترجمة دبلوماسية محترف. قيّم ترجمة المتدرب التالية مقارنة بالنموذج المرجعي باللغة {lang_names.get(target_lang, target_lang)}.

النموذج المرجعي:
{reference_text}

ترجمة المتدرب:
{user_text}

قدّم تقييماً موجزاً ومهنياً (لا يتجاوز 150 كلمة) يتضمن: 1) نقاط القوة 2) الأخطاء الاصطلاحية أو الأسلوبية إن وجدت 3) توصية عملية واحدة للتحسين. اكتب باللغة العربية."""
    message = client.messages.create(model="claude-sonnet-4-6", max_tokens=500,
                                      messages=[{"role": "user", "content": prompt}])
    return message.content[0].text


# ============================================================================
# 3) إعداد الصفحة والتنسيق
# ============================================================================
st.set_page_config(page_title="بوابة الإعداد للسلك الدبلوماسي 🇷🇺", page_icon="🕊️",
                    layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Tajawal', sans-serif; direction: rtl; }
.stApp { background: linear-gradient(180deg, #0f1b2d 0%, #13233a 100%); }
h1, h2, h3 { color: #d4af37 !important; }
p, li, span, label, div { color: #eef2f6; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { background-color: #16273f; border-radius: 8px 8px 0 0; padding: 10px 18px; color: #d4af37; font-weight: 700; }
.stTabs [aria-selected="true"] { background-color: #d4af37 !important; color: #0f1b2d !important; }
.metric-card { background: #16273f; border: 1px solid #d4af37; border-radius: 12px; padding: 16px; text-align: center; }
.flashcard { background: linear-gradient(135deg, #1a2c47, #0f1b2d); border: 2px solid #d4af37; border-radius: 16px;
             padding: 40px 20px; text-align: center; min-height: 160px; display: flex; flex-direction: column;
             justify-content: center; box-shadow: 0 4px 14px rgba(0,0,0,0.4); }
.badge { display:inline-block; background:#d4af37; color:#0f1b2d; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight:700; margin: 2px; }
.box-badge { display:inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight:700; margin-inline-start:6px; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 4) حالة الجلسة — بما في ذلك نظام Leitner للتكرار المتباعد
# ============================================================================
defaults = {
    "flash_index": 0,
    "flash_flipped": False,
    "leitner_boxes": {},       # term_ar -> box level (1..5)
    "quiz_score": 0,
    "quiz_total": 0,
    "translation_history": [],
    "study_streak_dates": set(),
    "api_key": "",
    "daily_word": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.session_state.study_streak_dates.add(datetime.now().strftime("%Y-%m-%d"))

glossary_df = pd.DataFrame(GLOSSARY)
texts_df = pd.DataFrame(TEXTS)
mcq_df = pd.DataFrame(MCQ)
essays_df = pd.DataFrame(ESSAYS)

# تهيئة صناديق Leitner لكل مصطلح غير مصنّف بعد (تبدأ من الصندوق 1)
for term in glossary_df["term_ar"]:
    st.session_state.leitner_boxes.setdefault(term, 1)

if st.session_state.daily_word is None:
    st.session_state.daily_word = glossary_df.sample(1).iloc[0].to_dict()

BOX_COLORS = {1: "#ff6b6b", 2: "#ffa94d", 3: "#ffd43b", 4: "#69db7c", 5: "#38d9a9"}
BOX_LABELS = {1: "جديد", 2: "قيد التعلم", 3: "مألوف", 4: "شبه متقن", 5: "متقن تماماً"}

# ============================================================================
# 5) الشريط الجانبي
# ============================================================================
with st.sidebar:
    st.markdown("## 🕊️ بوابة الدبلوماسي")
    st.markdown("**الإعداد لامتحان السلك الدبلوماسي**\nتركيز: اللغة الروسية 🇷🇺")
    st.markdown("---")

    st.markdown("### 🔥 سلسلة المذاكرة")
    st.markdown(f"<div class='metric-card'><h2>{len(st.session_state.study_streak_dates)}</h2><p>أيام مذاكرة مسجّلة</p></div>", unsafe_allow_html=True)

    mastered = sum(1 for b in st.session_state.leitner_boxes.values() if b >= 5)
    total_terms = len(glossary_df)
    st.markdown("### 📊 إحصائياتك")
    st.progress(mastered / total_terms if total_terms else 0)
    st.caption(f"مصطلحات متقنة تماماً: {mastered} / {total_terms}")

    if st.session_state.quiz_total:
        acc = round(st.session_state.quiz_score / st.session_state.quiz_total * 100, 1)
        st.caption(f"دقة الاختبار الذاتي: {acc}%")

    st.markdown("---")
    st.markdown("### 💾 حفظ / استعادة تقدمك")
    st.caption("لا يوجد تسجيل دخول — احفظ تقدمك كملف JSON واستورده لاحقاً لمتابعة نفس النقطة.")

    progress_payload = {
        "leitner_boxes": st.session_state.leitner_boxes,
        "quiz_score": st.session_state.quiz_score,
        "quiz_total": st.session_state.quiz_total,
        "translation_history": st.session_state.translation_history,
        "study_streak_dates": list(st.session_state.study_streak_dates),
    }
    st.download_button(
        "⬇️ تحميل ملف التقدم",
        data=json.dumps(progress_payload, ensure_ascii=False, indent=2),
        file_name=f"my_progress_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
    )
    uploaded_progress = st.file_uploader("⬆️ استيراد ملف تقدم سابق", type=["json"], key="progress_uploader")
    if uploaded_progress is not None:
        try:
            data = json.load(uploaded_progress)
            st.session_state.leitner_boxes.update(data.get("leitner_boxes", {}))
            st.session_state.quiz_score = data.get("quiz_score", st.session_state.quiz_score)
            st.session_state.quiz_total = data.get("quiz_total", st.session_state.quiz_total)
            st.session_state.translation_history = data.get("translation_history", st.session_state.translation_history)
            st.session_state.study_streak_dates.update(set(data.get("study_streak_dates", [])))
            st.success("✅ تم استيراد تقدمك بنجاح!")
        except Exception as e:
            st.error(f"تعذّر قراءة الملف: {e}")

    st.markdown("---")
    st.markdown("### ⚙️ تقييم متقدم بالذكاء الاصطناعي (اختياري)")
    st.caption("أدخل مفتاح Claude API الخاص بك لتفعيل تحليل أسلوبي أعمق للترجمة.")
    st.session_state.api_key = st.text_input("Anthropic API Key", type="password", value=st.session_state.api_key)

    st.markdown("---")
    st.caption("صُنع بعناية لطلاب السلك الدبلوماسي 🎓")

# ============================================================================
# 6) الرأس الرئيسي + كلمة اليوم
# ============================================================================
st.title("🕊️ بوابة الإعداد لامتحان السلك الدبلوماسي")
st.markdown("##### تركيز خاص على اللغة الروسية والترجمة الدبلوماسية 🇷🇺 🇸🇦")

dw = st.session_state.daily_word
st.markdown(
    f"<div class='metric-card' style='text-align:right;padding:14px 20px;'>"
    f"🌟 <b>مصطلح اليوم:</b> {dw['term_ar']} — <span style='color:#d4af37'>{dw['term_ru']}</span> "
    f"<i>({dw['term_en']})</i><br><span style='opacity:0.8;font-size:13px'>{dw['definition_ar']}</span></div>",
    unsafe_allow_html=True,
)

quote_pool = [
    "«الدبلوماسية هي فن قول 'كلب لطيف' حتى تجد حجراً» — وينستون تشرشل",
    "«الكلمة الدبلوماسية الصحيحة توازي فيلقاً من الجيوش» — نابليون بونابرت",
    "«السياسة الخارجية ليست عملاً خيرياً، بل ممارسة لتبادل المصالح» — هنري كيسنجر",
]
st.info(random.choice(quote_pool))

tab1, tab2, tab3, tab4 = st.tabs(
    ["📚 المصطلحات والبطاقات", "🌐 محاكي الترجمة الدبلوماسية", "📝 الاختبارات التحضيرية", "🏆 لوحة التقدم"]
)

# ============================================================================
# التبويب 1: المصطلحات + بطاقات Leitner
# ============================================================================
with tab1:
    st.subheader("📚 قاموس المصطلحات الدبلوماسية")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        category_filter = st.selectbox("تصفية حسب الفئة", ["الكل"] + sorted(glossary_df["category"].unique().tolist()))
    with col_filter2:
        search_term = st.text_input("🔍 بحث عن مصطلح")

    filtered_df = glossary_df.copy()
    if category_filter != "الكل":
        filtered_df = filtered_df[filtered_df["category"] == category_filter]
    if search_term:
        mask = filtered_df.apply(
            lambda r: search_term.lower() in str(r["term_ar"]).lower()
            or search_term.lower() in str(r["term_en"]).lower()
            or search_term.lower() in str(r["term_ru"]).lower(), axis=1)
        filtered_df = filtered_df[mask]

    st.dataframe(
        filtered_df[["term_ar", "term_en", "term_ru", "category", "definition_ar"]],
        use_container_width=True, hide_index=True,
        column_config={"term_ar": "المصطلح (عربي)", "term_en": "English", "term_ru": "Русский",
                        "category": "الفئة", "definition_ar": "التعريف"},
    )

    st.markdown("---")
    st.subheader("🎴 بطاقات التعلّم بنظام Leitner (تكرار متباعد)")
    st.caption("كل بطاقة تنتقل بين 5 صناديق حسب أدائك: كل إجابة صحيحة تدفعها صندوقاً للأمام، وكل خطأ يعيدها للصندوق الأول — هكذا تركّز جهدك على ما لا تتقنه.")

    upload = st.file_uploader("أو ارفع ملف CSV خاص بمصطلحاتك (أعمدة: term_ar, term_en, term_ru, category, definition_ar)", type=["csv"])
    active_df = pd.read_csv(upload) if upload is not None else filtered_df.reset_index(drop=True)

    review_mode = st.checkbox("🎯 وضع المراجعة الذكية (أولوية للبطاقات الأضعف)", value=True)
    if review_mode and upload is None:
        active_df = active_df.copy()
        active_df["_box"] = active_df["term_ar"].map(lambda t: st.session_state.leitner_boxes.get(t, 1))
        active_df = active_df.sort_values("_box").reset_index(drop=True)

    if len(active_df) == 0:
        st.warning("لا توجد مصطلحات مطابقة لعرضها كبطاقات.")
    else:
        st.session_state.flash_index %= len(active_df)
        row = active_df.iloc[st.session_state.flash_index]
        term_key = row["term_ar"]
        box_level = st.session_state.leitner_boxes.get(term_key, 1)

        card_html = f"""
        <div class="flashcard">
            <span class="badge">{row['category']}</span>
            <span class="box-badge" style="background:{BOX_COLORS[box_level]};color:#0f1b2d;">صندوق {box_level} — {BOX_LABELS[box_level]}</span>
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
                st.session_state.leitner_boxes[term_key] = min(5, box_level + 1)
                st.session_state.flash_index += 1
                st.session_state.flash_flipped = False
                st.rerun()
        with c5:
            if st.button("❌ أحتاج مراجعة"):
                st.session_state.leitner_boxes[term_key] = 1
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
            box_level = st.session_state.leitner_boxes.get(qr["term_ar"], 1)
            if choice == qr["term_ru"]:
                st.success("✅ إجابة صحيحة! أحسنت.")
                st.session_state.quiz_score += 1
                st.session_state.leitner_boxes[qr["term_ar"]] = min(5, box_level + 1)
            else:
                st.error(f"❌ غير صحيح. الإجابة الصحيحة: **{qr['term_ru']}**")
                st.session_state.leitner_boxes[qr["term_ar"]] = 1

# ============================================================================
# التبويب 2: محاكي الترجمة الدبلوماسية + التقييم الذكي
# ============================================================================
with tab2:
    st.subheader("🌐 محاكي نصوص الترجمة الدبلوماسية")
    st.caption("اختر نصاً رسمياً، ترجمه بنفسك، ثم قارن أداءك بمحرك التقييم الذكي ثلاثي اللغة.")

    text_titles = texts_df["title_ar"].tolist()
    selected_title = st.selectbox("اختر النص الدبلوماسي:", text_titles)
    text_row = texts_df[texts_df["title_ar"] == selected_title].iloc[0]

    lang_labels = {"ar": "العربية", "en": "الإنجليزية", "ru": "الروسية"}
    st.markdown(f"**اتجاه الترجمة:** {lang_labels[text_row['source_lang']]} ⬅️ {lang_labels[text_row['target_lang']]} "
                f"&nbsp; | &nbsp; **مستوى الصعوبة:** {text_row['difficulty']}")

    st.markdown("##### 📄 النص المصدر")
    st.text_area("النص الأصلي", value=text_row["source_text"], height=120, disabled=True, label_visibility="collapsed")

    st.markdown("##### ✍️ ترجمتك")
    user_translation = st.text_area("اكتب ترجمتك هنا", height=140, key=f"trans_{text_row['id']}", label_visibility="collapsed")

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
            result = evaluate_translation(user_translation, text_row["model_translation"], text_row["target_lang"], glossary_df)
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

            lt_ar, lt_en, lt_ru = st.tabs(["🇸🇦 تقرير عربي", "🇬🇧 English Report", "🇷🇺 Отчёт на русском"])
            with lt_ar:
                st.text(result.feedback_ar)
            with lt_en:
                st.text(result.feedback_en)
            with lt_ru:
                st.text(result.feedback_ru)

            if st.session_state.api_key:
                with st.spinner("جارٍ التحليل المتقدم عبر الذكاء الاصطناعي..."):
                    try:
                        ai_feedback = evaluate_with_ai(user_translation, text_row["model_translation"], text_row["target_lang"], st.session_state.api_key)
                        st.markdown("### 🤖 تحليل احترافي إضافي (Claude API)")
                        st.markdown(ai_feedback)
                    except Exception as e:
                        st.error(f"تعذّر الاتصال بالـ API: {e}")

# ============================================================================
# التبويب 3: الاختبارات التحضيرية
# ============================================================================
with tab3:
    st.subheader("📝 الاختبارات التحضيرية")
    mode = st.radio("اختر نوع الاختبار:", ["اختيار من متعدد (MCQ)", "أسئلة مقالية (Essay)"], horizontal=True)

    if mode == "اختيار من متعدد (MCQ)":
        with st.form("mcq_form"):
            answers = {}
            for _, q in mcq_df.iterrows():
                question_text = q["question_ar"]
                st.markdown(f"**{int(q['id'])}. {question_text}**")
                if str(q["question_ru"]).strip():
                    st.caption(f"🇷🇺 {q['question_ru']}")
                options = {"A": q["option_a"], "B": q["option_b"], "C": q["option_c"], "D": q["option_d"]}
                choice = st.radio("اختر:", list(options.keys()), format_func=lambda k, o=options: f"{k}) {o}",
                                   key=f"mcq_{q['id']}", horizontal=True, label_visibility="collapsed")
                answers[q["id"]] = choice
                st.markdown("---")
            submitted = st.form_submit_button("📤 تسليم الاختبار", type="primary")

        if submitted:
            correct = sum(1 for _, q in mcq_df.iterrows() if answers[q["id"]] == q["correct_answer"])
            pct = round(correct / len(mcq_df) * 100, 1)
            st.success(f"🎯 نتيجتك: {correct} / {len(mcq_df)} ({pct}%)")
            with st.expander("📋 مراجعة الإجابات والشروحات"):
                for _, q in mcq_df.iterrows():
                    is_correct = answers[q["id"]] == q["correct_answer"]
                    icon = "✅" if is_correct else "❌"
                    st.markdown(f"{icon} **{q['question_ar']}** — الإجابة الصحيحة: {q['correct_answer']}")
                    st.caption(q["explanation_ar"])
    else:
        for _, q in essays_df.iterrows():
            st.markdown(f"**سؤال {int(q['id'])}:** {q['question_ar']}")
            st.text_area("اكتب إجابتك هنا:", height=180, key=f"essay_{q['id']}")
            with st.expander("🧭 معايير التقييم"):
                st.caption(q["explanation_ar"])
            st.markdown("---")
        st.info("💡 نصيحة: يمكنك لصق إجابتك في تبويب «محاكي الترجمة» كترجمة لتقييم جودة لغتك الروسية إن رغبت.")

# ============================================================================
# التبويب 4: لوحة التقدم
# ============================================================================
with tab4:
    st.subheader("🏆 لوحة متابعة تقدمك")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='metric-card'><h1>{mastered}</h1><p>مصطلح متقن تماماً ✅</p></div>", unsafe_allow_html=True)
    with c2:
        acc = round(st.session_state.quiz_score / st.session_state.quiz_total * 100, 1) if st.session_state.quiz_total else 0
        st.markdown(f"<div class='metric-card'><h1>{acc}%</h1><p>دقة الاختبارات الذاتية 🎯</p></div>", unsafe_allow_html=True)
    with c3:
        avg_trans = (round(sum(h["score"] for h in st.session_state.translation_history) / len(st.session_state.translation_history), 1)
                     if st.session_state.translation_history else 0)
        st.markdown(f"<div class='metric-card'><h1>{avg_trans}</h1><p>متوسط درجات الترجمة 🌐</p></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📦 توزيع المصطلحات على صناديق Leitner")
    box_counts = pd.Series(st.session_state.leitner_boxes.values()).value_counts().sort_index()
    box_df = pd.DataFrame({
        "الصندوق": [f"{i} — {BOX_LABELS[i]}" for i in box_counts.index],
        "عدد المصطلحات": box_counts.values,
    })
    st.bar_chart(box_df, x="الصندوق", y="عدد المصطلحات")

    st.markdown("---")
    if st.session_state.translation_history:
        st.markdown("### 📈 تطور درجات الترجمة عبر الزمن")
        hist_df = pd.DataFrame(st.session_state.translation_history)
        st.line_chart(hist_df, x="date", y="score")
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.info("لم تُقيّم أي ترجمة بعد. توجّه إلى تبويب «محاكي الترجمة» للبدء.")

    weak_terms = [t for t, b in st.session_state.leitner_boxes.items() if b <= 2]
    if weak_terms:
        st.markdown("### 🔁 مصطلحات بحاجة لمراجعة عاجلة")
        for t in sorted(weak_terms):
            st.markdown(f"- {t}")

    st.markdown("---")
    st.markdown("### 🎯 نصيحة اليوم")
    tips = [
        "راجع 5 مصطلحات جديدة يومياً بدلاً من 30 مصطلحاً مرة واحدة — التكرار المتباعد أفعل للحفظ.",
        "عند الترجمة الدبلوماسية، حافظ على درجة الرسمية نفسها في اللغة الهدف، لا تُبسّط الأسلوب.",
        "استمع لنشرات الأخبار الروسية الرسمية لتعزيز حصيلتك من المصطلحات الحيّة.",
        "تدرّب على الترجمة الفورية الذهنية: اقرأ جملة وترجمها شفهياً خلال 10 ثوانٍ.",
        "لا تتجاهل صندوق Leitner الأول — هو مؤشرك الحقيقي لنقاط الضعف قبل الامتحان.",
    ]
    st.success(random.choice(tips))
