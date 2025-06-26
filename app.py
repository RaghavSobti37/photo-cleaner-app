import streamlit as st
import os
from PIL import Image
from backend.scanner import scan_images
from backend.duplicate_detector import find_duplicates, select_best_image
from backend.utils import log_progress
import shutil

st.set_page_config(page_title="🧠 AI-Based Photo Review Dashboard", layout="wide")
st.title("🧠 AI-Based Photo Review Dashboard")

folder = st.text_input("📁 Enter the folder to review:", value="CleanedPhotos/BestDuplicates")

if folder and os.path.isdir(folder):
    all_images = scan_images(folder)
    duplicate_groups = find_duplicates(all_images)

    total_groups = len(duplicate_groups)
    st.success(f"🔍 Found {len(all_images)} images | 🧬 {total_groups} duplicate groups")

    if total_groups > 0:
        output_folder = os.path.join(folder, "FinalSelected")
        os.makedirs(output_folder, exist_ok=True)

        st.markdown("---")
        st.subheader("🔄 Review Duplicate Groups")

        progress = st.progress(0)

        for idx, group in enumerate(duplicate_groups):
            st.markdown(f"### Group {idx+1} ({len(group)} images)")
            selected = select_best_image(group)

            cols = st.columns(len(group))
            manual_selection = st.empty()
            selected_index = group.index(selected)

            with st.expander("ℹ️ Why was this image selected?", expanded=False):
                st.write("This image was selected based on clearer facial features, better expressions, and overall sharpness using our AI-based scoring system.")

            chosen = st.session_state.get(f"group_{idx}_selection", selected)

            for i, img_path in enumerate(group):
                with cols[i]:
                    img = Image.open(img_path)
                    st.image(img, caption=os.path.basename(img_path), use_container_width=True)
                    if st.button("✅ SELECT THIS", key=f"select_{idx}_{i}"):
                        st.session_state[f"group_{idx}_selection"] = img_path
                        chosen = img_path

            st.info(f"✅ Selected image: {os.path.basename(chosen)}")

            # Save selected image
            save_btn = st.button(f"💾 Confirm & Save Selection for Group {idx+1}", key=f"save_{idx}")
            if save_btn:
                shutil.copy2(chosen, os.path.join(output_folder, os.path.basename(chosen)))
                st.success(f"Saved {os.path.basename(chosen)} to FinalSelected")

            progress.progress((idx + 1) / total_groups)
            st.markdown("---")

else:
    st.warning("⚠️ Please enter a valid folder path.")
