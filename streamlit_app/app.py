"""UI démonstrateur Projet Goutte d'eau — appelle l'API FastAPI locale."""
from datetime import date, timedelta

import httpx
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Goutte d'eau – Prévision pluie Occitanie",
    page_icon="🌧️",
    layout="centered",
)

st.title("🌧️ Projet Goutte d'eau")
st.caption(
    "Prévision de pluie pour les agriculteurs d'Occitanie · "
    "MVP France Météo / Mastère IA Léonard de Vinci"
)


@st.cache_data(ttl=300)
def fetch_stations() -> list[dict]:
    r = httpx.get(f"{API_BASE}/stations", timeout=10)
    r.raise_for_status()
    return r.json()


def call_predict(station_id: int, target_date: date) -> dict | None:
    try:
        r = httpx.post(
            f"{API_BASE}/predict",
            json={"station_id": station_id, "target_date": target_date.isoformat()},
            timeout=10,
        )
    except httpx.RequestError as exc:
        st.error(f"Erreur réseau : {exc}")
        return None
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        st.error(f"Erreur API {r.status_code} : {detail}")
        return None
    return r.json()


def call_health() -> dict | None:
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=5)
        if r.status_code == 200:
            return r.json()
    except httpx.RequestError:
        return None
    return None


# Sidebar : sélection des paramètres
with st.sidebar:
    st.header("Paramètres")

    health = call_health()
    if not health:
        st.error("⚠️ API indisponible sur localhost:8000")
        st.info("Lancer `make api` dans un autre terminal.")
        st.stop()
    if health["status"] != "ok":
        st.warning(f"⚠️ API en mode dégradé : DB={health['db']}, modèle={health['model_version']}")

    try:
        stations = fetch_stations()
    except Exception as exc:
        st.error(f"Impossible de récupérer les stations : {exc}")
        st.stop()

    if not stations:
        st.error("Aucune station configurée — exécuter `make db-init`.")
        st.stop()

    station_label = st.selectbox(
        "Station météo",
        options=[f"{s['name']} ({s.get('department') or '?'})" for s in stations],
        help="Sélectionnez une station d'Occitanie",
    )
    station_id = next(
        s["id"]
        for s in stations
        if f"{s['name']} ({s.get('department') or '?'})" == station_label
    )

    target_date = st.date_input(
        "Date cible",
        value=date.today() + timedelta(days=1),
        min_value=date.today() - timedelta(days=7),
        max_value=date.today() + timedelta(days=7),
        help="Pour quel jour prédire le risque de pluie ?",
    )

    submit = st.button(
        "🔍 Prédire le risque de pluie",
        type="primary",
        use_container_width=True,
    )


# Main area
if submit:
    with st.spinner("Calcul en cours…"):
        pred = call_predict(station_id, target_date)

    if pred:
        proba = pred["predicted_proba"]
        risk = pred["risk_level"]
        colors = {"bas": "#22c55e", "modéré": "#f59e0b", "élevé": "#ef4444"}
        color = colors.get(risk, "#6b7280")

        st.subheader(f"📍 {pred['station_name']} — {pred['target_date']}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Probabilité de pluie", f"{proba * 100:.1f} %")
        c2.metric("Niveau de risque", risk.capitalize())
        c3.metric("Modèle", pred["model_version"])

        # Barre de progression accessible (texte + couleur)
        st.progress(min(1.0, max(0.0, proba)), text=f"Risque : {risk}")

        # Recommandation (a11y : aria-live="polite", info aussi en texte pas que couleur)
        recos = {
            "bas": (
                "☀️ Pas de pluie attendue — fenêtre favorable pour les travaux culturaux."
            ),
            "modéré": (
                "⚠️ Risque modéré — surveiller la météo, reporter les opérations sensibles."
            ),
            "élevé": (
                "🌧️ Pluie probable — reporter semis, traitements et récoltes sensibles."
            ),
        }
        reco_text = recos.get(risk, "")

        st.markdown(
            f"""
            <div role='status' aria-live='polite'
                 style='padding:1rem; background:{color}22;
                        border-left:4px solid {color};
                        border-radius:4px; margin-top:1rem;'>
              <strong>Recommandation pour l'agriculteur :</strong><br/>
              {reco_text}
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Détails techniques de la prédiction"):
            st.json(pred)

else:
    st.info(
        "👈 Sélectionnez une station et une date dans le panneau de gauche, "
        "puis cliquez sur **Prédire**."
    )

st.divider()
st.caption(
    "API : http://localhost:8000/docs · Modèle XGBoost · "
    "Données SYNOP Météo France · Stations Occitanie"
)
