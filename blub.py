import streamlit as st
from netCDF4 import Dataset, num2date
import pandas as pd
import numpy as np
import io
import zipfile

# --------------------------------------------------
# 1. CONFIG & THEME
# --------------------------------------------------
SITE_NAME = "Blub Blub Blubbbbbb 🐠🫧"
st.set_page_config(page_title=SITE_NAME, layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0D1B2A; }
h1, h2, h3, p, span, label { color: #E0E1DD !important; }
.stButton>button { background-color: #0077B6; color: white; border-radius: 12px; font-weight: bold; }
.footer { position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 12px; color: #778DA9; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 2. SESSION STATE
# --------------------------------------------------
if 'final_excels' not in st.session_state:
    st.session_state.final_excels = []

# --------------------------------------------------
# 3. UI HEADER
# --------------------------------------------------
st.title(SITE_NAME)
st.subheader("Hey Mate! Ready to dive into the data? 🌊")

uploaded_files = st.file_uploader("Drop your ERA5 (.nc) files here", type=["nc"], accept_multiple_files=True)

# --------------------------------------------------
# 4. PROCESSING LOGIC
# --------------------------------------------------
if uploaded_files:
    if st.button("🚀 Process & Generate All Reports"):
        st.session_state.final_excels = [] 
        progress_bar = st.progress(0.0)
        
        for idx, file in enumerate(uploaded_files, start=1):
            try:
                ds = Dataset("inmemory.nc", memory=file.getvalue())
                vars_present = ds.variables.keys()

                time_var = ds.variables['valid_time']
                lat, lon = ds.variables['latitude'][:], ds.variables['longitude'][:]
                times = num2date(time_var[:], time_var.units)

                # --- NEW: Extract hours for hour column ---
                hours = np.array([t.hour for t in times])

                T, LAT, LON = np.meshgrid(range(len(times)), range(len(lat)), range(len(lon)), indexing='ij')

                # --- WIND PROCESSING ---
                if 'u10' in vars_present and 'v10' in vars_present:
                    u, v = ds.variables['u10'][:], ds.variables['v10'][:]
                    df = pd.DataFrame({
                        "time": np.array(times)[T.flatten()],
                        "hour": hours[T.flatten()],
                        "latitude": lat[LAT.flatten()],
                        "longitude": lon[LON.flatten()],
                        "u_wind": u[T, LAT, LON].flatten(),
                        "v_wind": v[T, LAT, LON].flatten(),
                    })
                    df["wind_speed"] = np.sqrt(df["u_wind"]**2 + df["v_wind"]**2)
                    df["wind_direction"] = (np.arctan2(-df["u_wind"], -df["v_wind"]) * 180 / np.pi) % 360
                    out_name = file.name.replace(".nc", "_wind.xlsx")

                # --- OTHER GRID VARIABLES ---
                else:
                    target_vars = ['sst', 'swh', 'mwd', 'hmax']
                    found_var = next((v for v in target_vars if v in vars_present), None)
                    
                    if not found_var:
                        st.error(f"❌ {file.name}: No compatible variables found.")
                        continue
                        
                    data = ds.variables[found_var][:]
                    df = pd.DataFrame({
                        "time": np.array(times)[T.flatten()],
                        "hour": hours[T.flatten()],
                        "latitude": lat[LAT.flatten()],
                        "longitude": lon[LON.flatten()],
                        found_var: data[T, LAT, LON].flatten()
                    })
                    out_name = file.name.replace(".nc", f"_{found_var}.xlsx")

                ds.close()

                # Save to Excel buffer
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                st.session_state.final_excels.append({"name": out_name, "content": buffer.getvalue()})

            except Exception as e:
                st.error(f"⚠️ Failed to process {file.name}: {e}")
            
            progress_bar.progress(idx / len(uploaded_files))
        
        st.success(f"Successfully processed {len(st.session_state.final_excels)} files!")

# --------------------------------------------------
# 5. ZIP & DOWNLOAD SECTION (FIXED DUPLICATE ID)
# --------------------------------------------------
if st.session_state.final_excels:
    st.divider()
    st.markdown("### 📥 Download Results")
    
    zip_out = io.BytesIO()
    with zipfile.ZipFile(zip_out, "w") as zf:
        for file_data in st.session_state.final_excels:
            zf.writestr(file_data["name"], file_data["content"])
    zip_out.seek(0)

    st.download_button(
        label="📦 DOWNLOAD ALL AS ZIP",
        data=zip_out,
        file_name="ocean_data_package.zip",
        mime="application/zip",
        use_container_width=True,
        key="zip_download_btn"
    )

    with st.expander("Or download files individually"):
        for idx, f in enumerate(st.session_state.final_excels):
            st.download_button(
                label=f"⬇️ {f['name']}", 
                data=f['content'], 
                file_name=f['name'],
                key=f"dl_{idx}" # Unique key for each button
            )

st.markdown('<div class="footer">🌊 Blub Blub Blubbbbbb Version 3.0.0.8 💦</div>', unsafe_allow_html=True)
