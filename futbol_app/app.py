import os

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Clasificación Histórica", page_icon="⚽", layout="wide")

# Carpeta "data" siempre relativa a la ubicación de este archivo,
# para que funcione sin importar cuál sea el directorio de trabajo
# (por ejemplo, en Streamlit Community Cloud).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


# ----------------------------------------------------------------------
# Carga de datos
# ----------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(DATA_DIR, "temporadas.csv"))
    meta = pd.read_csv(os.path.join(DATA_DIR, "equipos_meta.csv"))
    linajes = pd.read_csv(os.path.join(DATA_DIR, "linajes.csv"))
    return df, meta, linajes


df, meta, linajes = load_data()
SEASONS = sorted(df["temporada"].unique())

# Diccionarios de ayuda: id -> nombre actual / link
ID_TO_NAME = dict(zip(meta["equipo_id"], meta["nombre_actual"]))
ID_TO_LINK = dict(zip(meta["equipo_id"], meta["link"]))

# Linajes: agrupan IDs distintos que representan el mismo club tras una
# refundación. Por defecto cada equipo_id es su propio linaje (1:1).
LINAJE_MAP = dict(zip(linajes["equipo_id"], linajes["linaje_id"]))
LINAJE_TO_IDS = {}
for _eid, _lid in LINAJE_MAP.items():
    LINAJE_TO_IDS.setdefault(_lid, []).append(_eid)

st.title("⚽ Clasificación Histórica")
st.caption(f"Estadísticas de la liga · Temporadas T{SEASONS[0]} – T{SEASONS[-1]}")


# ----------------------------------------------------------------------
# Sidebar: selector de rango de temporadas
# ----------------------------------------------------------------------
st.sidebar.header("Filtros")
t_min, t_max = st.sidebar.select_slider(
    "Rango de temporadas",
    options=SEASONS,
    value=(SEASONS[0], SEASONS[-1]),
    format_func=lambda x: f"T{x}",
)

df_r = df[(df["temporada"] >= t_min) & (df["temporada"] <= t_max)].copy()
n_seasons_sel = t_max - t_min + 1
st.sidebar.markdown(f"**{n_seasons_sel} temporada(s)** seleccionadas (T{t_min} – T{t_max})")
st.sidebar.markdown("---")
st.sidebar.markdown(
    "Los equipos se identifican por su **ID de StrikerManager**, no por el "
    "nombre. Si un club cambia de nombre, sus temporadas anteriores se "
    "siguen contando igual."
)


# ----------------------------------------------------------------------
# Helper: historial de nombres de un equipo (por su id)
# ----------------------------------------------------------------------
def name_history(data: pd.DataFrame, tid) -> list[tuple[str, int, int]]:
    """Devuelve [(nombre, temporada_inicio, temporada_fin), ...] en orden cronológico."""
    sub = data[data["equipo_id"] == tid].sort_values("temporada")
    history = []
    current_name, start, end = None, None, None
    for _, r in sub.iterrows():
        if r["equipo_nombre"] != current_name:
            if current_name is not None:
                history.append((current_name, start, end))
            current_name, start = r["equipo_nombre"], r["temporada"]
        end = r["temporada"]
    if current_name is not None:
        history.append((current_name, start, end))
    return history


# ----------------------------------------------------------------------
# Construcción de la clasificación histórica agregada.
# Incluye una fila por cada equipo_id (Individual) y, además, una fila
# extra por cada linaje con más de un equipo_id (Combinado), que suma
# todas sus etapas y compite por puesto igual que cualquier otro equipo.
# ----------------------------------------------------------------------
def build_classification(data: pd.DataFrame) -> pd.DataFrame:
    # --- Filas individuales (una por equipo_id) ---
    agg = data.groupby("equipo_id").agg(
        Temporadas=("temporada", "count"),
        PJ=("PJ", "sum"),
        PG=("PG", "sum"),
        PE=("PE", "sum"),
        PP=("PP", "sum"),
        GF=("GF", "sum"),
        GC=("GC", "sum"),
        Pnt=("Pnt", "sum"),
        Titulos=("pos", lambda x: int((x == 1).sum())),
        Podios=("pos", lambda x: int((x <= 3).sum())),
    ).reset_index()

    agg["Equipo"] = agg["equipo_id"].map(ID_TO_NAME)
    agg["Perfil"] = agg["equipo_id"].map(ID_TO_LINK)
    agg["Tipo"] = "Individual"
    agg["Etapas"] = "—"

    # Marca si el equipo jugó con más de un nombre dentro del rango seleccionado
    nombres_por_id = data.groupby("equipo_id")["equipo_nombre"].nunique()
    agg["cambio_nombre"] = agg["equipo_id"].map(nombres_por_id) > 1

    # --- Filas combinadas por linaje (refundaciones con 2+ equipo_id) ---
    data2 = data.copy()
    data2["linaje_id"] = data2["equipo_id"].map(LINAJE_MAP).fillna(data2["equipo_id"])
    grouped_ids = data2.groupby("linaje_id")["equipo_id"].nunique()
    multi = grouped_ids[grouped_ids > 1].index

    combo_rows = []
    for lin_id in multi:
        sub = data2[data2["linaje_id"] == lin_id]

        # Orden cronológico de las etapas (etapa 1, etapa 2, ...)
        rangos = sub.groupby("equipo_id")["temporada"].agg(["min", "max"])
        ids_incluidos = rangos.sort_values("min").index.tolist()
        etapas = []
        for i, eid in enumerate(ids_incluidos, start=1):
            t_ini, t_fin = rangos.loc[eid, "min"], rangos.loc[eid, "max"]
            rango = f"T{t_ini}" if t_ini == t_fin else f"T{t_ini}-T{t_fin}"
            etapas.append(f"Etapa {i}: {ID_TO_NAME.get(eid, str(eid))} ({rango})")

        combo_rows.append({
            "equipo_id": lin_id,
            "Equipo": f"{ID_TO_NAME.get(lin_id, str(lin_id))} (histórico)",
            "Perfil": ID_TO_LINK.get(lin_id),
            "Tipo": "🔁 Combinado",
            "Etapas": " → ".join(etapas),
            "Temporadas": len(sub),
            "PJ": int(sub["PJ"].sum()), "PG": int(sub["PG"].sum()), "PE": int(sub["PE"].sum()),
            "PP": int(sub["PP"].sum()), "GF": int(sub["GF"].sum()), "GC": int(sub["GC"].sum()),
            "Pnt": int(sub["Pnt"].sum()),
            "Titulos": int((sub["pos"] == 1).sum()), "Podios": int((sub["pos"] <= 3).sum()),
            "cambio_nombre": False,
        })

    if combo_rows:
        agg = pd.concat([agg, pd.DataFrame(combo_rows)], ignore_index=True)

    agg["DG"] = agg["GF"] - agg["GC"]
    agg["PG%"] = (agg["PG"] / agg["PJ"] * 100).round(1)
    agg["GF/PJ"] = (agg["GF"] / agg["PJ"]).round(2)
    agg["GC/PJ"] = (agg["GC"] / agg["PJ"]).round(2)
    agg["Pnt/PJ"] = (agg["Pnt"] / agg["PJ"]).round(2)

    agg = agg.sort_values(["Pnt", "DG", "GF"], ascending=False).reset_index(drop=True)
    agg.insert(0, "Pos", range(1, len(agg) + 1))
    return agg


clasificacion = build_classification(df_r)



# ----------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------
tab_clas, tab_records, tab_evol, tab_comp, tab_hist = st.tabs(
    ["📊 Clasificación", "🏆 Récords y curiosidades", "📈 Evolución de equipo",
     "⚔️ Comparador", "📜 Historial de equipos"]
)

# ===================== TAB 1: CLASIFICACIÓN =====================
with tab_clas:
    st.subheader(f"Clasificación histórica · T{t_min} – T{t_max}")

    display_cols = [
        "Pos", "Equipo", "Tipo", "Perfil", "Temporadas", "PJ", "PG", "PE", "PP",
        "GF", "GC", "DG", "Pnt", "Pnt/PJ", "PG%", "Titulos", "Podios"
    ]
    rename_cols = {"Temporadas": "Temp.", "Titulos": "Títulos"}

    st.dataframe(
        clasificacion[display_cols].rename(columns=rename_cols),
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Perfil": st.column_config.LinkColumn("Perfil", display_text="🔗 StrikerManager"),
        },
    )

    # Avisos de cambios de nombre dentro del rango
    cambios = clasificacion[clasificacion["cambio_nombre"]]
    if not cambios.empty:
        with st.expander(f"🔄 {len(cambios)} equipo(s) cambiaron de nombre en este rango"):
            for _, r in cambios.iterrows():
                hist = name_history(df_r, r["equipo_id"])
                texto = " → ".join(f"{n} (T{a}-T{b})" for n, a, b in hist)
                st.write(f"**{r['Equipo']}**: {texto}")

    # Desglose de las filas "Combinado" (refundaciones)
    combinados = clasificacion[clasificacion["Tipo"] == "🔁 Combinado"]
    if not combinados.empty:
        with st.expander(f"🔁 {len(combinados)} equipo(s) combinan varias etapas (refundaciones)"):
            st.caption(
                "Estas filas ya están incluidas arriba con su propio puesto: "
                "suman todas las etapas del linaje y compiten como una sola entidad."
            )
            for _, r in combinados.iterrows():
                st.write(f"**#{int(r['Pos'])} {r['Equipo']}** — {r['Etapas']}")



    st.markdown("##### Top 10 por puntos en el rango seleccionado")
    top10 = clasificacion.head(10)
    fig = px.bar(
        top10, x="Pnt", y="Equipo", orientation="h",
        text="Pnt", labels={"Equipo": "", "Pnt": "Puntos"},
        color="Pnt", color_continuous_scale="Blues",
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False, height=400)
    st.plotly_chart(fig, use_container_width=True)


# ===================== TAB 2: RÉCORDS Y CURIOSIDADES =====================
with tab_records:
    st.subheader(f"Récords y curiosidades · T{t_min} – T{t_max}")

    if df_r.empty:
        st.info("No hay datos en el rango seleccionado.")
    else:
        df_r_named = df_r.copy()
        df_r_named["Equipo"] = df_r_named["equipo_id"].map(ID_TO_NAME)

        def record_row(data, col, ascending=False, n=3):
            d = data.sort_values(col, ascending=ascending).head(n)
            return d[["Equipo", "equipo_nombre", "temporada", col]]

        def write_record(data, col, ascending=False, n=3, suffix=""):
            for _, r in record_row(data, col, ascending, n).iterrows():
                nombre = r["Equipo"]
                nota = ""
                if r["equipo_nombre"] != nombre:
                    nota = f" _(jugaba como '{r['equipo_nombre']}')_"
                st.write(f"{r[col]:g}{suffix} — {nombre}{nota} (T{int(r['temporada'])})")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**🏅 Más puntos en una temporada**")
            write_record(df_r_named, "Pnt", suffix=" pts")

            st.markdown("**⚽ Más goles a favor en una temporada**")
            write_record(df_r_named, "GF", suffix=" goles")

            st.markdown("**🧱 Mejor defensa en una temporada (menos GC)**")
            write_record(df_r_named, "GC", ascending=True, suffix=" encajados")

        with col2:
            st.markdown("**📉 Menos puntos en una temporada**")
            write_record(df_r_named, "Pnt", ascending=True, suffix=" pts")

            st.markdown("**🚫 Peor defensa en una temporada (más GC)**")
            write_record(df_r_named, "GC", suffix=" encajados")

            st.markdown("**💥 Mayor diferencia de goles en una temporada**")
            write_record(df_r_named, "DG", suffix="")

        with col3:
            st.markdown("**🔻 Peor diferencia de goles en una temporada**")
            write_record(df_r_named, "DG", ascending=True, suffix="")

            st.markdown("**🟢 Más victorias en una temporada**")
            write_record(df_r_named, "PG", suffix=" victorias")

            st.markdown("**🔴 Más derrotas en una temporada**")
            write_record(df_r_named, "PP", suffix=" derrotas")

        st.markdown("---")

        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown("**👑 Más títulos en el rango**")
            titulos = clasificacion[clasificacion["Titulos"] > 0].sort_values(
                "Titulos", ascending=False
            ).head(5)
            if titulos.empty:
                st.write("Ninguno todavía.")
            for _, r in titulos.iterrows():
                st.write(f"{int(r['Titulos'])}x — {r['Equipo']}")

        with col5:
            st.markdown("**🥉 Más podios en el rango**")
            podios = clasificacion[clasificacion["Podios"] > 0].sort_values(
                "Podios", ascending=False
            ).head(5)
            for _, r in podios.iterrows():
                st.write(f"{int(r['Podios'])}x — {r['Equipo']}")

        with col6:
            st.markdown("**📈 Mejor media de puntos/partido**")
            elegibles = clasificacion[clasificacion["PJ"] >= n_seasons_sel * 10]
            mejor_ratio = elegibles.sort_values("Pnt/PJ", ascending=False).head(5)
            for _, r in mejor_ratio.iterrows():
                st.write(f"{r['Pnt/PJ']:.2f} pts/PJ — {r['Equipo']}")

        st.markdown("---")
        total_goles = int(df_r["GF"].sum())
        total_pj = int(df_r["PJ"].sum())
        media_goles = total_goles / total_pj if total_pj else 0
        n_equipos = df_r["equipo_id"].nunique()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Equipos distintos", n_equipos)
        c2.metric("Goles totales", f"{total_goles:,}")
        c3.metric("Partidos jugados (suma)", f"{total_pj:,}")
        c4.metric("Goles/partido", f"{media_goles:.2f}")


# ===================== TAB 3: EVOLUCIÓN DE EQUIPO =====================
with tab_evol:
    st.subheader("Evolución histórica de un equipo")

    teams_sorted = meta.sort_values("nombre_actual")
    options = teams_sorted["equipo_id"].tolist()
    equipo_id_sel = st.selectbox(
        "Selecciona un equipo", options,
        format_func=lambda tid: ID_TO_NAME.get(tid, str(tid)),
    )

    df_equipo = df[df["equipo_id"] == equipo_id_sel].sort_values("temporada")

    # Si este equipo forma parte de un linaje (refundación) con más IDs,
    # ofrecer incluir las temporadas del/los otro(s) ID(s).
    grupo_ids = LINAJE_TO_IDS.get(LINAJE_MAP.get(equipo_id_sel, equipo_id_sel), [equipo_id_sel])
    otros_ids = [i for i in grupo_ids if i != equipo_id_sel]
    if otros_ids:
        otros_nombres = ", ".join(f"'{ID_TO_NAME.get(i, str(i))}'" for i in otros_ids)
        incluir_combinado = st.checkbox(
            f"Incluir también las temporadas de {otros_nombres} (refundación, mismo linaje)"
        )
        if incluir_combinado:
            df_equipo = df[df["equipo_id"].isin(grupo_ids)].sort_values("temporada")

    if df_equipo.empty:
        st.info("Este equipo no tiene datos.")
    else:
        hist = name_history(df, equipo_id_sel)
        if len(hist) > 1:
            texto = " → ".join(f"'{n}' (T{a}-T{b})" for n, a, b in hist)
            st.caption(f"🔄 Historial de nombres: {texto}")

        link = ID_TO_LINK.get(equipo_id_sel)
        if link:
            st.caption(f"Perfil: {link}")
        for otro in otros_ids:
            if otro in df_equipo["equipo_id"].values:
                st.caption(f"Perfil de '{ID_TO_NAME.get(otro, otro)}' (linaje anterior): {ID_TO_LINK.get(otro)}")

        fig_pos = go.Figure()
        fig_pos.add_trace(go.Scatter(
            x=df_equipo["temporada"], y=df_equipo["pos"],
            mode="lines+markers", name="Posición",
            line=dict(color="#1f77b4", width=3), marker=dict(size=8),
        ))
        fig_pos.add_vrect(x0=t_min - 0.5, x1=t_max + 0.5,
                          fillcolor="orange", opacity=0.1, line_width=0)
        fig_pos.update_yaxes(autorange="reversed", title="Posición final", dtick=1)
        fig_pos.update_xaxes(title="Temporada", dtick=1, tickprefix="T")
        fig_pos.update_layout(title="Posición final por temporada", height=350)
        st.plotly_chart(fig_pos, use_container_width=True)

        fig_pnt = px.bar(
            df_equipo, x="temporada", y="Pnt",
            labels={"temporada": "Temporada", "Pnt": "Puntos"},
            title="Puntos por temporada",
        )
        fig_pnt.update_xaxes(tickprefix="T", dtick=1)
        fig_pnt.add_vrect(x0=t_min - 0.5, x1=t_max + 0.5,
                          fillcolor="orange", opacity=0.1, line_width=0)
        fig_pnt.update_layout(height=350)
        st.plotly_chart(fig_pnt, use_container_width=True)

        st.markdown("##### Tabla completa de temporadas")
        tabla = df_equipo[["temporada", "equipo_nombre", "pos", "PJ", "PG", "PE", "PP",
                            "GF", "GC", "DG", "Pnt"]].rename(columns={
            "temporada": "Temporada", "equipo_nombre": "Nombre esa temporada", "pos": "Posición"
        })
        st.dataframe(tabla, use_container_width=True, hide_index=True)


# ===================== TAB 4: COMPARADOR =====================
with tab_comp:
    st.subheader(f"Comparador de equipos · T{t_min} – T{t_max}")

    ids_rango = sorted(df_r["equipo_id"].unique(), key=lambda tid: ID_TO_NAME.get(tid, ""))
    if len(ids_rango) < 2:
        st.info("Se necesitan al menos 2 equipos con datos en el rango seleccionado.")
    else:
        c1, c2 = st.columns(2)
        id_a = c1.selectbox("Equipo A", ids_rango, index=0,
                            format_func=lambda tid: ID_TO_NAME.get(tid, str(tid)), key="comp_a")
        id_b = c2.selectbox("Equipo B", ids_rango,
                            index=1 if len(ids_rango) > 1 else 0,
                            format_func=lambda tid: ID_TO_NAME.get(tid, str(tid)), key="comp_b")

        fila_a = clasificacion[clasificacion["equipo_id"] == id_a].iloc[0]
        fila_b = clasificacion[clasificacion["equipo_id"] == id_b].iloc[0]

        metrics = ["Temporadas", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "Pnt",
                   "Pnt/PJ", "Titulos", "Podios"]

        comp_df = pd.DataFrame({
            "Estadística": metrics,
            fila_a["Equipo"]: [fila_a[m] for m in metrics],
            fila_b["Equipo"]: [fila_b[m] for m in metrics],
        })
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

        metrics_chart = ["PG", "PE", "PP", "GF", "GC", "Pnt"]
        chart_df = pd.DataFrame({
            "Estadística": metrics_chart * 2,
            "Equipo": [fila_a["Equipo"]] * len(metrics_chart) + [fila_b["Equipo"]] * len(metrics_chart),
            "Valor": [fila_a[m] for m in metrics_chart] + [fila_b[m] for m in metrics_chart],
        })
        fig_comp = px.bar(chart_df, x="Estadística", y="Valor", color="Equipo",
                          barmode="group")
        fig_comp.update_layout(height=400)
        st.plotly_chart(fig_comp, use_container_width=True)

        st.markdown("##### Posiciones temporada a temporada (rango seleccionado)")
        comunes = df_r[df_r["equipo_id"].isin([id_a, id_b])].copy()
        comunes["Equipo"] = comunes["equipo_id"].map(ID_TO_NAME)
        pivot = comunes.pivot_table(index="temporada", columns="Equipo", values="pos")
        pivot = pivot.reindex(columns=[c for c in [fila_a["Equipo"], fila_b["Equipo"]] if c in pivot.columns])
        st.dataframe(pivot, use_container_width=True)


# ===================== TAB 5: HISTORIAL DE EQUIPOS =====================
with tab_hist:
    st.subheader("Historial de equipos y palmarés (T6 – T18 completo)")
    st.caption(
        "Esta pestaña no se ve afectada por el filtro de temporadas. "
        "Cada equipo está identificado por su ID de StrikerManager; el nombre "
        "puede cambiar con el tiempo pero el ID es estable."
    )

    def cambios_en_primera(tid):
        """Solo muestra historial si hubo más de un nombre CON registro en T6-T18."""
        hist = name_history(df, tid)
        if len(hist) <= 1:
            return "—"
        return " → ".join(f"{n} (T{a}-T{b})" for n, a, b in hist)

    meta_display = meta.copy()
    meta_display["Cambios de nombre en Primera"] = meta_display["equipo_id"].apply(cambios_en_primera)
    meta_display = meta_display.rename(columns={
        "equipo_id": "ID",
        "nombre_actual": "Nombre actual",
        "primeros": "1º",
        "segundos": "2º",
        "playoff": "Playoffs",
        "podios": "Podios",
        "link": "Perfil",
    })
    st.dataframe(
        meta_display[["ID", "Nombre actual", "Cambios de nombre en Primera",
                       "1º", "2º", "Playoffs", "Podios", "Perfil"]]
        .sort_values("Podios", ascending=False),
        use_container_width=True, hide_index=True, height=600,
        column_config={
            "Perfil": st.column_config.LinkColumn("Perfil", display_text="🔗 StrikerManager"),
        },
    )
