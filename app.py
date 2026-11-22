import cv2
import numpy as np
import streamlit as st
from PIL import Image

from config import CUSTOM_MODEL_PATH, DEFAULT_DEFECT_TYPES, SIMILARITY_THRESHOLD
from utils.database import (
    get_all_defects,
    get_defect_types,
    get_defects_with_embeddings,
    get_stats,
    init_db,
    save_defect,
)
from utils.export_dataset import export_dataset, get_dataset_status
from utils.image_processing import preprocess_image
from utils.similarity import extract_embedding, find_similar_defects
from utils.yolo import reload_model, run_yolo_classification

# Set page config
st.set_page_config(
    page_title="AI CNC Inspector",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Premium CSS
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Make primary buttons larger and more prominent */
    .stButton>button[kind="primary"] {
        background-color: #3b82f6;
        color: white;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.5);
        transition: all 0.2s ease;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #2563eb;
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.5);
    }
    
    /* Make secondary buttons larger too */
    .stButton>button[kind="secondary"] {
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    /* Alert / Info boxes */
    .stAlert {
        border-radius: 8px;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    h1 {
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .camera-text {
        text-align: center;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: -1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

init_db()


# --- STATE MANAGEMENT ---
if "current_image" not in st.session_state:
    st.session_state.current_image = None
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "annotated_image" not in st.session_state:
    st.session_state.annotated_image = None
if "yolo_pred_class" not in st.session_state:
    st.session_state.yolo_pred_class = None
if "yolo_pred_score" not in st.session_state:
    st.session_state.yolo_pred_score = 0.0
if "best_match" not in st.session_state:
    st.session_state.best_match = None
if "image_embedding" not in st.session_state:
    st.session_state.image_embedding = None
if "camera_active" not in st.session_state:
    st.session_state.camera_active = False


def reset_state():
    st.session_state.current_image = None
    st.session_state.analysis_done = False
    st.session_state.annotated_image = None
    st.session_state.best_match = None
    st.session_state.image_embedding = None
    st.session_state.camera_active = False


# --- MAIN UI ---
st.title("🤖 AI CNC Inspector")
st.markdown("Akıllı kalite kontrol sistemi. Parçayı çekin, analiz edelim.")

# Aktif model bilgisi
_model_label = "🟢 Özel Model (best.pt)" if CUSTOM_MODEL_PATH.exists() else "🟡 Temel Model (Henüz eğitilmedi)"
st.caption(f"Aktif Model: {_model_label}")

# Navigation Tabs
tab_detect, tab_reports, tab_admin = st.tabs(
    ["🔍 Hata Tespiti", "📊 Raporlar & Geçmiş", "🧠 Model Eğitimi"]
)

with tab_detect:
    if not st.session_state.analysis_done:
        # STEP 1: IMAGE CAPTURE
        st.markdown("### 1. Parçayı İncele")

        selected_image = None

        if not st.session_state.camera_active:
            # Ana Ekran: Kamerayı Aç Butonu ve Dosya Yükleyici
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📸 Kamerayı Aç (Fotoğraf Çek)", use_container_width=True, type="primary"):
                st.session_state.camera_active = True
                st.rerun()

            st.markdown(
                "<div style='text-align: center; margin: 2rem 0; color: #666; font-weight: 600;'>— VEYA —</div>",
                unsafe_allow_html=True,
            )

            selected_image = st.file_uploader(
                "📁 Galeriden veya Cihazdan Yükle",
                type=["jpg", "jpeg", "png", "webp"],
            )
        else:
            # Kamera Modu: Tam Ekran Kamera
            st.markdown("#### 📸 Kameradan Çekim Yapılıyor...")
            cam_image = st.camera_input("Kamera", label_visibility="hidden")
            
            if st.button("❌ Vazgeç / Geri Dön", use_container_width=True):
                st.session_state.camera_active = False
                st.rerun()
                
            if cam_image:
                selected_image = cam_image
                st.session_state.camera_active = False

        if selected_image:
            image_obj = Image.open(selected_image)
            st.session_state.current_image = image_obj
            st.session_state.image_bytes = selected_image.getvalue()
            st.session_state.filename = (
                selected_image.name
                if hasattr(selected_image, "name")
                else "camera_capture.jpg"
            )

            with st.spinner(
                "🧠 Yapay zeka fotoğrafı inceliyor... Lütfen bekleyin."
            ):
                # Run YOLO Classification
                try:
                    orig_img, top_class, top_score = run_yolo_classification(
                        image_obj
                    )
                    st.session_state.annotated_image = orig_img
                    st.session_state.yolo_pred_class = top_class
                    st.session_state.yolo_pred_score = top_score
                except Exception as e:
                    st.error(f"YOLO hatası: {e}")
                    st.session_state.annotated_image = image_obj
                    st.session_state.yolo_pred_class = None
                    st.session_state.yolo_pred_score = 0.0

                # Run Similarity
                embedding = extract_embedding(image_obj)
                st.session_state.image_embedding = embedding
                known = get_defects_with_embeddings()

                if known:
                    matches = find_similar_defects(
                        embedding,
                        known,
                        top_k=1,
                        threshold=SIMILARITY_THRESHOLD,
                    )
                    if matches:
                        st.session_state.best_match = matches[0]

                st.session_state.analysis_done = True
                st.rerun()

    else:
        # STEP 2: REVIEW & DECIDE
        st.markdown("### 2. Analiz Sonucu")

        if st.button("← Geri Dön (İptal)"):
            reset_state()
            st.rerun()

        col_img, col_action = st.columns([1, 1.2])

        with col_img:
            st.image(
                st.session_state.annotated_image,
                caption="Analiz Edilen Fotoğraf",
                use_container_width=True,
            )

        with col_action:
            if st.session_state.best_match:
                match = st.session_state.best_match
                percent = match["similarity"] * 100
                st.info(
                    f"💡 **Sistem Önerisi:** Bu hatayı daha önce görmüş olabiliriz. (**% {percent:.0f} Benzerlik**)"
                )
                st.image(
                    match["image_path"],
                    width=200,
                    caption="Geçmişteki Benzer Hata",
                )
                
                if st.session_state.yolo_pred_class and st.session_state.yolo_pred_class != "Bilinmiyor":
                    st.markdown(f"**YOLO Model Tahmini:** `{st.session_state.yolo_pred_class}` (%{st.session_state.yolo_pred_score*100:.1f} güven)")
                st.markdown(
                    f"**Önerilen Hata Tipi:** `{match['defect_type']}`"
                )

                st.markdown("---")
                st.markdown("#### Bu tahmin doğru mu?")

                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button(
                        "✅ Evet, Kaydet",
                        type="primary",
                        use_container_width=True,
                    ):
                        save_defect(
                            image_bytes=st.session_state.image_bytes,
                            filename=st.session_state.filename,
                            defect_type=match["defect_type"],
                            embedding=st.session_state.image_embedding,
                        )
                        st.success(
                            f"Başarıyla kaydedildi: {match['defect_type']}"
                        )
                        import time

                        time.sleep(1.5)
                        reset_state()
                        st.rerun()

                with col_no:
                    new_decision = st.button(
                        "❌ Hayır, Farklı Bir Hata", use_container_width=True
                    )
                    if new_decision:
                        st.session_state.best_match = None
                        st.rerun()
            else:
                st.warning(
                    "⚠️ Daha önce benzer bir hata görülmedi veya sistem emin olamadı."
                )
                if st.session_state.yolo_pred_class and st.session_state.yolo_pred_class != "Bilinmiyor":
                    st.info(
                        f"🤖 **YOLO Model Önerisi:** `{st.session_state.yolo_pred_class}` (%{st.session_state.yolo_pred_score*100:.1f} güven)"
                    )
                st.markdown("Lütfen bu hatayı etiketleyin:")

                defect_types = get_defect_types() or DEFAULT_DEFECT_TYPES
                default_idx = 0
                if st.session_state.yolo_pred_class in defect_types:
                    default_idx = defect_types.index(st.session_state.yolo_pred_class)
                defect_type = st.selectbox("Hata tipi seçin:", defect_types, index=default_idx)
                custom_type = st.text_input("Veya yeni bir hata tipi yazın:")
                notes = st.text_area(
                    "Ek Not (Opsiyonel):",
                    placeholder="Hatanın konumu, sebebi vb.",
                )

                final_type = custom_type.strip() or defect_type

                if st.button(
                    "💾 Yeni Hata Olarak Kaydet",
                    type="primary",
                    use_container_width=True,
                ):
                    save_defect(
                        image_bytes=st.session_state.image_bytes,
                        filename=st.session_state.filename,
                        defect_type=final_type,
                        notes=notes,
                        embedding=st.session_state.image_embedding,
                    )
                    st.success(
                        f"Yeni hata başarıyla kaydedildi: {final_type}"
                    )
                    import time

                    time.sleep(1.5)
                    reset_state()
                    st.rerun()

        # --- OPENCV GÖRÜNTÜ ÖN İŞLEME TEST BÖLÜMÜ ---
        st.markdown("---")
        with st.expander("🛠️ OpenCV Görüntü Ön İşleme Adımlarını İncele"):
            if st.session_state.current_image is not None:
                orig, gray, blur, edges = preprocess_image(
                    st.session_state.current_image
                )

                p_col1, p_col2, p_col3, p_col4 = st.columns(4)

                with p_col1:
                    st.image(orig, caption="Orijinal Görüntü")

                with p_col2:
                    st.image(gray, caption="Gri Ton (Gray)")

                with p_col3:
                    st.image(blur, caption="Bulanıklaştırılmış (Blur)")

                with p_col4:
                    st.image(edges, caption="Kenarlar (Canny)")

with tab_reports:
    st.header("Raporlar & Geçmiş")
    stats = get_stats()

    col1, col2 = st.columns(2)
    col1.metric("Toplam Kayıtlı Hata", stats["total"])
    col2.metric("Farklı Hata Tipi Sayısı", len(stats["by_type"]))

    if stats["by_type"]:
        st.subheader("Hata Tipine Göre Dağılım")
        for defect_type, count in stats["by_type"].items():
            st.progress(
                min(count / max(stats["total"], 1), 1.0),
                text=f"{defect_type}: {count}",
            )

    st.markdown("---")
    st.subheader("Son Kayıtlar")
    defects = get_all_defects(limit=10)

    if not defects:
        st.info("Henüz kayıt bulunmuyor.")
    else:
        for item in defects:
            with st.expander(
                f"{item['defect_code']} — {item['defect_type']} ({item['created_at'][:10]})"
            ):
                col_i, col_inf = st.columns([1, 2])
                with col_i:
                    st.image(item["image_path"], use_container_width=True)
                with col_inf:
                    st.write(f"**Tarih:** {item['created_at']}")
                    st.write(f"**Not:** {item['notes'] or '-'}")

with tab_admin:
    st.header("🧠 Model Eğitimi & Veri Yönetimi")

    # --- Veri Durumu ---
    st.subheader("📊 Veri Durumu")
    ds_status = get_dataset_status()

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Toplam Görsel", ds_status["total_images"])
    col_m2.metric("Eğitilmemiş Yeni Görsel", ds_status["untrained_images"])
    col_m3.metric("Sınıf Sayısı", len(ds_status["class_counts"]))

    if ds_status["class_counts"]:
        st.markdown("**Sınıf Dağılımı:**")
        for cls_name, count in sorted(
            ds_status["class_counts"].items(), key=lambda x: -x[1]
        ):
            min_ok = "✅" if count >= ds_status["min_per_class"] else "⚠️"
            st.write(f"{min_ok} `{cls_name}`: {count} görsel")

    if ds_status["ready_for_training"]:
        st.success(
            f"✅ Eğitim için yeterli veri var! "
            f"({ds_status['total_images']} görsel, {len(ds_status['class_counts'])} sınıf)"
        )
    else:
        st.warning(
            f"⚠️ Eğitim için en az {ds_status['min_required']} toplam görsel "
            f"ve her sınıfta en az {ds_status['min_per_class']} görsel gerekiyor."
        )

    # --- Model Durumu ---
    st.markdown("---")
    st.subheader("🤖 Model Durumu")

    if CUSTOM_MODEL_PATH.exists():
        import os
        from datetime import datetime

        mod_time = os.path.getmtime(CUSTOM_MODEL_PATH)
        mod_date = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
        st.info(f"🟢 Özel eğitilmiş model mevcut. Son güncelleme: **{mod_date}**")
    else:
        st.warning(
            "🟡 Henüz özel bir model eğitilmedi. "
            "Sistem şu an temel (pre-trained) model kullanıyor."
        )

    # --- Aksiyonlar ---
    st.markdown("---")
    st.subheader("⚡ Aksiyonlar")

    col_act1, col_act2 = st.columns(2)

    with col_act1:
        if st.button(
            "📦 Veri Setini Dışa Aktar",
            use_container_width=True,
            help="Veritabanındaki görselleri YOLO eğitim formatına dönüştürür.",
        ):
            with st.spinner("Veri seti oluşturuluyor..."):
                result = export_dataset(force=True)
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result["message"])

    with col_act2:
        train_disabled = not ds_status["ready_for_training"]
        if st.button(
            "🚀 Modeli Eğit",
            type="primary",
            use_container_width=True,
            disabled=train_disabled,
            help="Yeterli veri varsa modeli yeniden eğitir."
            if not train_disabled
            else "Eğitim için yeterli veri yok.",
        ):
            with st.spinner(
                "🧠 Model eğitiliyor... Bu işlem birkaç dakika sürebilir."
            ):
                from train_model import train

                result = train(force_export=True)
            if result["success"]:
                reload_model()
                st.success(result["message"])
                st.balloons()
            else:
                st.error(f"[{result['stage']}] {result['message']}")