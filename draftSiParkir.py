import json, os
from datetime import datetime, timedelta, timezone
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="SiParkir UM", page_icon="🅿️")

FILE = "data_parkir.json"
REFRESH = 15  # detik, ubah ke 300 kalau mau 5 menit
WIB = timezone(timedelta(hours=7))

# koordinat masih perkiraan, ganti dengan lokasi asli (klik kanan di Google Maps)
DEFAULT = [
    {"nama": "Gedung Rektorat UM", "jenis": "Mobil", "kapasitas": 40, "kosong": 0, "lat": -7.9600, "lon": 112.6170, "update": "10.09"},
    {"nama": "Gedung Sasana Budaya", "jenis": "Mobil", "kapasitas": 50, "kosong": 0, "lat": -7.9610, "lon": 112.6180, "update": "10.01"},
    {"nama": "Gedung Graha Cakrawala", "jenis": "Motor", "kapasitas": 80, "kosong": 10, "lat": -7.9615, "lon": 112.6165, "update": "10.05"},
    {"nama": "Parkiran Gedung A1 (FT)", "jenis": "Motor", "kapasitas": 150, "kosong": 12, "lat": -7.9595, "lon": 112.6185, "update": "10.11"},
    {"nama": "Gedung O1 (FIP)", "jenis": "Mobil", "kapasitas": 45, "kosong": 27, "lat": -7.9620, "lon": 112.6175, "update": "10.13"},
    {"nama": "Gedung Kuliah Bersama (GKB A20)", "jenis": "Motor", "kapasitas": 200, "kosong": 115, "lat": -7.9605, "lon": 112.6195, "update": "10.28"},
]


def sekarang():
    return datetime.now(WIB).strftime("%H.%M")


def simpan(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def muat():
    if not os.path.exists(FILE):
        simpan({"area": DEFAULT, "log": []})
    with open(FILE, encoding="utf-8") as f:
        return json.load(f)


def status(a):
    terisi = 100 * (a["kapasitas"] - a["kosong"]) / a["kapasitas"]
    if a["kosong"] == 0:
        return "Penuh", "red", "🔴", terisi
    if terisi >= 85:
        return "Hampir Penuh", "orange", "🟠", terisi
    return "Tersedia", "green", "🟢", terisi


def cek_password(masukan):
    try:
        benar = st.secrets["PASSWORD_PETUGAS"]
    except Exception:
        benar = "petugas123"  # cuma untuk coba di laptop
    return masukan == benar


@st.fragment(run_every=REFRESH)
def beranda():
    area = muat()["area"]
    st.subheader("Parkir Kampus UM")
    st.caption("Pantau slot kosong sebelum tiba di fakultas.")

    c1, c2 = st.columns(2)
    for kolom, jenis in ((c1, "Motor"), (c2, "Mobil")):
        sub = [a for a in area if a["jenis"] == jenis]
        kolom.metric(f"Slot {jenis.lower()} kosong", sum(a["kosong"] for a in sub))
        kolom.caption(f"dari {sum(a['kapasitas'] for a in sub)} kapasitas")

    pilih = st.radio("Filter", ["Semua area", "Motor", "Mobil"],
                     horizontal=True, label_visibility="collapsed")
    tampil = [a for a in area if pilih == "Semua area" or a["jenis"] == pilih]

    st.markdown(f"**Area parkir terdekat** ({len(tampil)} area)")
    for a in tampil:
        s, _, ikon, terisi = status(a)
        with st.container(border=True):
            st.markdown(f"**{a['nama']}**  \n{a['jenis']} · diperbarui {a['update']}")
            st.markdown(f"{ikon} {s}: **{a['kosong']}** dari {a['kapasitas']} slot kosong ({terisi:g}% terisi)")
            st.progress(terisi / 100)


@st.fragment(run_every=REFRESH)
def peta():
    area = muat()["area"]
    m = folium.Map(location=[-7.9607, 112.6178], zoom_start=17)
    for a in area:
        s, warna, _, _ = status(a)
        isi = (f"<b>{a['nama']}</b><br>{a['jenis']}: {a['kosong']}/{a['kapasitas']} kosong"
               f"<br>{s} · diperbarui {a['update']}")
        folium.Marker([a["lat"], a["lon"]], tooltip=a["nama"],
                      popup=folium.Popup(isi, max_width=250),
                      icon=folium.Icon(color=warna)).add_to(m)
    st_folium(m, height=450, use_container_width=True, returned_objects=[], key="peta")
    st.caption(f"Peta diperbarui otomatis. Terakhir dimuat {sekarang()} WIB.")


def form_petugas():
    data = muat()
    area = data["area"]
    label = [f"{a['nama']} · {a['jenis']}" for a in area]

    st.subheader("Perbarui status area")
    st.caption("Petugas dapat mencatat kendaraan masuk dan keluar.")
    with st.form("form_petugas", clear_on_submit=True):
        pilih = st.selectbox("Area parkir", label)
        c1, c2 = st.columns(2)
        masuk = c1.number_input("Kendaraan masuk", min_value=0, step=1)
        keluar = c2.number_input("Kendaraan keluar", min_value=0, step=1)
        petugas = st.text_input("Nama petugas")
        kirim = st.form_submit_button("Simpan pembaruan slot")

    if kirim:
        if not petugas.strip():
            st.error("Isi nama petugas dulu.")
        else:
            a = area[label.index(pilih)]
            a["kosong"] = max(0, min(a["kapasitas"], a["kosong"] - masuk + keluar))
            a["update"] = sekarang()
            data["log"].insert(0, {"waktu": sekarang(), "area": pilih,
                                   "masuk": masuk, "keluar": keluar, "petugas": petugas})
            simpan(data)
            st.toast("Slot berhasil diperbarui")
            st.rerun()


@st.fragment(run_every=REFRESH)
def riwayat():
    log = muat()["log"]
    st.subheader("Riwayat terbaru")
    if not log:
        st.info("Belum ada pencatatan.")
    for l in log[:10]:
        st.write(f"{l['waktu']} · **{l['area']}** · {l['masuk']} masuk, {l['keluar']} keluar · {l['petugas']}")


def aktivitas():
    if not st.session_state.get("petugas"):
        st.subheader("Masuk sebagai petugas")
        st.caption("Pengguna biasa cukup melihat Beranda dan Peta.")
        with st.form("login"):
            pw = st.text_input("Password petugas", type="password")
            masuk = st.form_submit_button("Masuk")
        if masuk:
            if cek_password(pw):
                st.session_state["petugas"] = True
                st.rerun()
            else:
                st.error("Password salah.")
    else:
        form_petugas()
        if st.button("Keluar"):
            st.session_state["petugas"] = False
            st.rerun()
    riwayat()


st.title("🅿️ SiParkir UM")
tab1, tab2, tab3 = st.tabs(["Beranda", "Peta", "Aktivitas"])
with tab1:
    beranda()
with tab2:
    peta()
with tab3:
    aktivitas()