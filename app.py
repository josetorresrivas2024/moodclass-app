with tab1:
          day_sel = st.date_input("Fecha a analizar", value=date.today(), key="teacher_day")

            # =======================
            # PDF mensual
            # =======================
            st.divider()
            st.markdown("### 📄 Reporte mensual (PDF)")

            cmy1, cmy2 = st.columns(2)
            with cmy1:
                rep_year = st.number_input(
                    "Año",
                    min_value=2020,
                    max_value=2100,
                    value=date.today().year,
                    step=1,
                )
            with cmy2:
                rep_month = st.selectbox(
                    "Mes",
                    list(range(1, 13)),
                    index=date.today().month - 1,
                )

            if st.button("📄 Generar PDF mensual", use_container_width=True):
                pdf_bytes = generate_monthly_pdf(int(rep_year), int(rep_month))
                file_name = f"moodclass_reporte_{int(rep_year)}_{int(rep_month):02d}.pdf"
                st.download_button(
                    "⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=file_name,
                    mime="application/pdf",
                    use_container_width=True,
                )

            st.divider()

            df = load_moods(day=str(day_sel))
            df_entrada = df[df["moment"] == "entrada"].copy()
            df_salida = df[df["moment"] == "salida"].copy()

            # =======================
            # KPIs + semáforo
            # =======================
            total_registros = len(df)
            total_entrada = len(df_entrada)

            if not df_entrada.empty:
                labels = df_entrada["emotion"].apply(emotion_label)
                emocion_top = labels.value_counts().idxmax()
            else:
                emocion_top = "—"

            status, pct = traffic_light(df_entrada)
            if status.startswith("🟢"):
                badge_class = "badge badge-green"
            elif status.startswith("🟡"):
                badge_class = "badge badge-yellow"
            else:
                badge_class = "badge badge-red"

            st.markdown("### 📊 Resumen del día")

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(
                    f"<div class='kpi'><div class='kpi-title'>Registros hoy</div>"
                    f"<div class='kpi-value'>{total_registros}</div>"
                    f"<div class='kpi-sub'>Entrada + salida</div></div>",
                    unsafe_allow_html=True,
                )
            with k2:
                st.markdown(
                    f"<div class='kpi'><div class='kpi-title'>Entradas registradas</div>"
                    f"<div class='kpi-value'>{total_entrada}</div>"
                    f"<div class='kpi-sub'>inicio de jornada</div></div>",
                    unsafe_allow_html=True,
                )
            with k3:
                st.markdown(
                    f"<div class='kpi'><div class='kpi-title'>Emoción más frecuente</div>"
                    f"<div class='kpi-value'>{emocion_top}</div>"
                    f"<div class='kpi-sub'>al ingresar</div></div>",
                    unsafe_allow_html=True,
                )
            with k4:
                st.markdown(
                    f"<div class='kpi'><div class='kpi-title'>Estados cargados</div>"
                    f"<div class='kpi-value'>{pct:.1f}%</div>"
                    f"<div class='kpi-sub'>Molesto/Triste/Ansioso/Preocupado/Cansado</div></div>",
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"<div class='{badge_class}'>🚦 {status} · {pct:.1f}% cargado</div>",
                unsafe_allow_html=True,
            )

            # =======================
            # Top 3 + comparación
            # =======================
            st.divider()

            a, b = st.columns(2)
            with a:
                st.markdown(
                    "<div class='mcard'><div class='mcard-title'>🏁 Top 3 al entrar</div>",
                    unsafe_allow_html=True,
                )
                st.dataframe(top3_table(df_entrada), use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with b:
                st.markdown(
                    "<div class='mcard'><div class='mcard-title'>🏁 Top 3 al salir</div>",
                    unsafe_allow_html=True,
                )
                st.dataframe(top3_table(df_salida), use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)

            comp = compare_entrada_salida(df_entrada, df_salida)
            st.markdown(
                "<div class='mcard'><div class='mcard-title'>🔁 Comparación Entrada vs Salida</div>",
                unsafe_allow_html=True,
            )
            if comp.empty:
                st.info("Sin datos suficientes para comparar.")
            else:
                st.dataframe(comp, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # =======================
            # Gráficos
            # =======================
            c1, c2 = st.columns(2)

            with c1:
                st.markdown(
                    "<div class='mcard'><div class='mcard-title'>📊 Emociones al entrar</div>",
                    unsafe_allow_html=True,
                )
                if df_entrada.empty:
                    st.info("Sin registros de entrada.")
                else:
                    vc = df_entrada["emotion"].value_counts().reset_index()
                    vc.columns = ["emotion", "count"]
                    fig = px.bar(vc, x="emotion", y="count")
                    st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with c2:
                st.markdown(
                    "<div class='mcard'><div class='mcard-title'>🟠 Emociones al salir</div>",
                    unsafe_allow_html=True,
                )
                if df_salida.empty:
                    st.info("Sin registros de salida.")
                else:
                    vc = df_salida["emotion"].value_counts().reset_index()
                    vc.columns = ["emotion", "count"]
                    fig = px.pie(vc, names="emotion", values="count")
                    st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # =======================
            # Botiquín
            # =======================
            st.divider()
            st.markdown(
                "<div class='mcard'><div class='mcard-title'>🧰 Botiquín emocional sugerido</div>",
                unsafe_allow_html=True,
            )
            msg, tools = recommended_tool(df_entrada)
            st.write(msg)
            for t in tools:
                st.write("• " + t)
            st.markdown("</div>", unsafe_allow_html=True)

            # =======================
            # Detalle + CSV
            # =======================
            st.divider()
            st.markdown(
                "<div class='mcard'><div class='mcard-title'>🧾 Registros del día (detalle)</div>",
                unsafe_allow_html=True,
            )
            if df.empty:
                st.info("Sin datos en esta fecha.")
            else:
                show = df.copy()
                show["estudiante"] = show.apply(
                    lambda r: "Anónimo" if r["is_anonymous"] == 1 else (r["student_name"] or "—"),
                    axis=1,
                )
                show = show[["created_at", "moment", "estudiante", "emotion", "reason", "note"]]
                st.dataframe(show, use_container_width=True, hide_index=True)

                csv = show.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "⬇️ Descargar CSV (piloto)",
                    data=csv,
                    file_name=f"moodclass_{day_sel}.csv",
                    mime="text/csv",
                )
            st.markdown("</div>", unsafe_allow_html=True)



