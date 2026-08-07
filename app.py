import cv2
import numpy as np
import streamlit as st
from PIL import Image

from config import DEFAULT_DEFECT_TYPES, SIMILARITY_THRESHOLD
from utils.database import (
    get_all_defects,
    get_defect_types,
    get_defects_with_embeddings,
    get_stats,
    init_db,
    save_defect,
)
from utils.similarity import extract_embedding, find_similar_defects
from utils.yolo import run_yolo_detection

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
if "num_det" not in st.session_state:
    st.session_state.num_det = 0
if "best_match" not in st.session_state:
    st.session_state.best_match = None
if "image_embedding" not in st.session_state:
    st.session_state.image_embedding = None


def reset_state():
    st.session_state.current_image = None
    st.session_state.analysis_done = False
    st.session_state.annotated_image = None
    st.session_state.best_match = None
    st.session_state.image_embedding = None


# --- MAIN UI ---
st.title("🤖 AI CNC Inspector")
st.markdown("Akıllı kalite kontrol sistemi. Parçayı çekin, analiz edelim.")

# Navigation Tabs
tab_detect, tab_reports = st.tabs(["🔍 Hata Tespiti", "📊 Raporlar & Geçmiş"])

with tab_detect:
    if not st.session_state.analysis_done:
        # STEP 1: IMAGE CAPTURE
        st.markdown("### 1. Fotoğraf Çek veya Yükle")

        col_cam, col_upload = st.columns(2)

        with col_cam:
            st.markdown(
                "<div class='camera-text'>📸 Kameradan Çek</div>",
                unsafe_allow_html=True,
            )
            cam_image = st.camera_input("Kamera", label_visibility="hidden")

        with col_upload:
            st.markdown(
                "<div class='camera-text'>📁 Dosya Yükle</div>",
                unsafe_allow_html=True,
            )
            file_image = st.file_uploader(
                "Dosya",
                type=["jpg", "jpeg", "png", "webp"],
                label_visibility="hidden",
            )

        selected_image = cam_image or file_image

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
                # Run YOLO
                try:
                    annotated_img, num_det, classes = run_yolo_detection(
                        image_obj
                    )
                    st.session_state.annotated_image = annotated_img
                    st.session_state.num_det = num_det
                except Exception as e:
                    st.error(f"YOLO hatası: {e}")
                    st.session_state.annotated_image = image_obj
                    st.session_state.num_det = 0

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
                caption=f"Tespit Edilen Bölge ({st.session_state.num_det} nesne)",
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
                st.markdown("Lütfen bu hatayı manuel olarak etiketleyin:")

                defect_types = get_defect_types() or DEFAULT_DEFECT_TYPES
                defect_type = st.selectbox("Hata tipi seçin:", defect_types)
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