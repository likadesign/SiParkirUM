import json, math, os
from datetime import datetime, timedelta, timezone
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="SiParkir UM", page_icon="🅿️")

FILE = "data_siparkir.json"
REFRESH = 15  # detik
WIB = timezone(timedelta(hours=7))
PUSAT = [-7.9607, 112.6190]

# kapasitas dan slot kosong masih CONTOH; koordinat FMIPA samping PIPA dan GKB A20 juga masih contoh
DEFAULT = [
    {"nama": "Parkir K", "kapasitas": 120, "kosong": 45, "lat": -7.959887, "lon": 112.619266, "update": "10.00"},
    {"nama": "FMIPA samping PIPA", "kapasitas": 100, "kosong": 12, "lat": -7.9590, "lon": 112.6185, "update": "10.02"},
    {"nama": "FMIPA seberang Gracak", "kapasitas": 80, "kosong": 0, "lat": -7.959687, "lon": 112.619016, "update": "10.05"},
    {"nama": "GKB A20", "kapasitas": 200, "kosong": 115, "lat": -7.9605, "lon": 112.6195, "update": "10.08"},
    {"nama": "GKB A19", "kapasitas": 150, "kosong": 30, "lat": -7.961313, "lon": 112.619328, "update": "10.10"},
    {"nama": "GKB depan", "kapasitas": 100, "kosong": 8, "lat": -7.961787, "lon": 112.620266, "update": "10.12"},
    {"nama": "Masjid", "kapasitas": 90, "kosong": 60, "lat": -7.961083, "lon": 112.616972, "update": "10.15"},
]

def sekarang():
    return datetime.now(WIB).strftime("%H.%M")


def stempel():
    return datetime.now(WIB).strftime("%d/%m %H.%M")


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


def jarak_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def fmt_jarak(m):
    return f"{m:.0f} m" if m < 1000 else f"{m / 1000:.1f} km"


def urut_terdekat(area):
    pos = st.session_state.get("pos")
    if not pos:
        return area
    for a in area:
        a["jarak"] = jarak_m(pos[0], pos[1], a["lat"], a["lon"])
    return sorted(area, key=lambda a: a["jarak"])


@st.fragment(run_every=REFRESH)
def beranda():
    area = urut_terdekat(muat()["area"])
    nama = st.session_state.get("profil", {}).get("nama")
    st.subheader(f"Halo, {nama}" if nama else "Parkir Kampus UM")
    st.caption("Pantau slot parkir motor sebelum tiba di fakultas.")

    kapasitas = sum(a["kapasitas"] for a in area)
    kosong = sum(a["kosong"] for a in area)
    c1, c2 = st.columns(2)
    c1.metric("Slot motor kosong", kosong)
    c1.caption(f"dari {kapasitas} kapasitas")
    c2.metric("Keterisian total", f"{100 * (kapasitas - kosong) / kapasitas:.0f}%")

    if not st.session_state.get("pos"):
        st.info("Aktifkan lokasi (tombol di atas) untuk mengurutkan dari yang terdekat.")
    st.markdown(f"**Area parkir terdekat** ({len(area)} titik)")
    for a in area:
        s, _, ikon, terisi = status(a)
        jarak = f" · {fmt_jarak(a['jarak'])} dari kamu" if "jarak" in a else ""
        with st.container(border=True):
            st.markdown(f"**{a['nama']}**{jarak}  \ndiperbarui {a['update']}")
            st.markdown(f"{ikon} {s}: **{a['kosong']}** dari {a['kapasitas']} slot kosong ({terisi:g}% terisi)")
            st.progress(terisi / 100)


@st.fragment(run_every=REFRESH)
def peta():
    area = urut_terdekat(muat()["area"])
    pos = st.session_state.get("pos")

    if pos:
        tersedia = [a for a in area if a["kosong"] > 0][:3]
        st.markdown("**Rekomendasi parkir terdekat**")
        if not tersedia:
            st.write("Semua titik sedang penuh.")
        for a in tersedia:
            st.write(f"📍 **{a['nama']}** · {fmt_jarak(a['jarak'])} · {a['kosong']} slot kosong")
    else:
        st.info("Aktifkan lokasi (tombol di atas) untuk melihat rekomendasi parkir terdekat.")

    m = folium.Map(location=PUSAT, zoom_start=17)
    for a in area:
        s, warna, _, _ = status(a)
        isi = (f"<b>{a['nama']}</b><br>{a['kosong']}/{a['kapasitas']} slot kosong"
               f"<br>{s} · diperbarui {a['update']}")
        folium.Marker([a["lat"], a["lon"]], tooltip=a["nama"],
                      popup=folium.Popup(isi, max_width=250),
                      icon=folium.Icon(color=warna)).add_to(m)
    if pos:
        folium.Marker(list(pos), tooltip="Lokasi kamu",
                      icon=folium.Icon(color="blue", icon="user", prefix="fa")).add_to(m)
    st_folium(m, height=450, use_container_width=True, returned_objects=[], key="peta")
    st.caption(f"🟢 Tersedia · 🟠 Hampir penuh · 🔴 Penuh. Dimuat {sekarang()} WIB, refresh otomatis.")


def form_petugas():
    data = muat()
    area = data["area"]
    daftar = [a["nama"] for a in area]

    st.subheader("Perbarui slot parkir")
    st.caption("Petugas mencatat kendaraan masuk dan keluar di tiap titik.")
    with st.form("form_petugas", clear_on_submit=True):
        pilih = st.selectbox("Titik parkir", daftar)
        c1, c2 = st.columns(2)
        masuk = c1.number_input("Motor masuk", min_value=0, step=1)
        keluar = c2.number_input("Motor keluar", min_value=0, step=1)
        petugas = st.text_input("Nama petugas")
        kirim = st.form_submit_button("Simpan pembaruan")

    if kirim:
        if not petugas.strip():
            st.error("Isi nama petugas dulu.")
        elif masuk == 0 and keluar == 0:
            st.error("Isi jumlah masuk atau keluar.")
        else:
            a = area[daftar.index(pilih)]
            lama = a["kosong"]
            a["kosong"] = max(0, min(a["kapasitas"], lama - masuk + keluar))
            a["update"] = sekarang()
            data["log"].insert(0, {"waktu": stempel(), "area": pilih,
                                   "delta": a["kosong"] - lama, "kosong": a["kosong"],
                                   "kapasitas": a["kapasitas"], "petugas": petugas})
            data["log"] = data["log"][:200]
            simpan(data)
            st.toast("Slot berhasil diperbarui")
            st.rerun()


@st.fragment(run_every=REFRESH)
def riwayat():
    data = muat()
    st.subheader("Riwayat pembaruan slot")
    titik = st.selectbox("Titik parkir", ["Semua titik"] + [a["nama"] for a in data["area"]],
                         key="filter_riwayat")
    log = [l for l in data["log"] if titik == "Semua titik" or l["area"] == titik]
    if not log:
        st.info("Belum ada pembaruan.")
    for l in log[:15]:
        tanda = "+" if l["delta"] > 0 else ""
        st.write(f"{l['waktu']} · **{l['area']}** · {tanda}{l['delta']} slot kosong "
                 f"(jadi {l['kosong']}/{l['kapasitas']}) · {l['petugas']}")


def aktivitas():
    if not st.session_state.get("petugas"):
        st.subheader("Masuk sebagai petugas")
        st.caption("Pengguna biasa cukup melihat riwayat di bawah.")
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


def profil():
    p = st.session_state.get("profil", {})
    opsi = ["Motor", "Mobil"]
    st.subheader("Profil")
    st.caption("Dipakai untuk personalisasi selama kamu membuka aplikasi, tidak disimpan permanen.")
    with st.form("form_profil"):
        nama = st.text_input("Nama", value=p.get("nama", ""))
        email = st.text_input("Email", value=p.get("email", ""))
        kendaraan = st.selectbox("Jenis kendaraan", opsi, index=opsi.index(p.get("kendaraan", "Motor")))
        kirim = st.form_submit_button("Simpan profil")
    if kirim:
        if email and "@" not in email:
            st.error("Format email belum benar.")
        else:
            st.session_state["profil"] = {"nama": nama.strip(), "email": email.strip(), "kendaraan": kendaraan}
            st.toast("Profil disimpan")
            st.rerun()
    if p.get("kendaraan") == "Mobil":
        st.warning("SiParkir saat ini baru mencakup parkir motor.")


st.title("🅿️ SiParkir UM")
lok = streamlit_geolocation()
if lok and lok.get("latitude") is not None and lok.get("longitude") is not None:
    st.session_state["pos"] = (lok["latitude"], lok["longitude"])
st.caption("✅ Lokasi aktif" if st.session_state.get("pos")
           else "📍 Tekan tombol di atas, lalu izinkan akses lokasi di browser.")

tab1, tab2, tab3, tab4 = st.tabs(["Beranda", "Peta", "Aktivitas", "Profil"])
with tab1:
    beranda()
with tab2:
    peta()
with tab3:
    aktivitas()
with tab4:
    profil()
