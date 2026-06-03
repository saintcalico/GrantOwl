import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

def render_step3():
    if (
        st.session_state.selected_scholarship
        and st.session_state.step >= 3
    ):
        s = st.session_state.selected_scholarship
        p = st.session_state.profile

        with st.expander(
            "Step 3 — Why this is your best match",
            expanded=(st.session_state.step == 3),
        ):
            st.markdown(f"## {s['name']}")
            st.caption(f"{s['provider']} · {s['type'].capitalize()}")

            if st.session_state.rationale:
                st.info(
                    f"**Your AI Adviser says:** "
                    f"{st.session_state.rationale}"
                )

            st.divider()

            # Radar chart
            st.markdown(
                "### Your Profile vs. Scholarship Requirements"
            )
            user_gpa = p.get("gpa") or 0
            req_gpa = s.get("gpa_required") or 0
            user_major = (p.get("major") or "").lower()
            majors_lower = [m.lower() for m in s.get("majors", [])]
            user_skills = p.get("skills") or ""
            user_leadership = p.get("leadership_roles") or []
            user_extracurricular = p.get("extracurricular_focus") or []

            gpa_fit = (
                min((user_gpa / req_gpa) * 100, 100)
                if req_gpa > 0 and user_gpa
                else 80
            )
            major_fit = (
                100 if "all" in majors_lower
                else 90 if any(
                    user_major in m or m in user_major
                    for m in majors_lower
                )
                else 40
            )
            skills_fit = min(len(user_skills.split()) * 10, 100) if user_skills else 20
            leadership_fit = (
                100 if len(user_leadership) >= 2
                else 60 if len(user_leadership) == 1
                else 20
            )
            extracurricular_fit = min(
                len(user_extracurricular) * 25, 100
            )

            radar_cats = [
                "GPA Fit", "Major Fit", "Skills",
                "Leadership", "Extracurricular",
            ]
            user_vals = [
                gpa_fit, major_fit, skills_fit,
                leadership_fit, extracurricular_fit,
            ]
            radar_cats_c = radar_cats + [radar_cats[0]]
            user_vals_c = user_vals + [user_vals[0]]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=[100, 100, 100, 100, 100, 100],
                theta=radar_cats_c,
                fill="toself",
                name="Scholarship Ideal",
                fillcolor="rgba(108,99,255,0.15)",
                line=dict(color="#6C63FF", width=1, dash="dash"),
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=user_vals_c,
                theta=radar_cats_c,
                fill="toself",
                name="Your Profile",
                fillcolor="rgba(108,99,255,0.4)",
                line=dict(color="#6C63FF", width=2),
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        tickfont=dict(color="#FAFAFA"),
                        gridcolor="rgba(255,255,255,0.1)",
                    ),
                    angularaxis=dict(
                        tickfont=dict(color="#FAFAFA"),
                        gridcolor="rgba(255,255,255,0.1)",
                    ),
                    bgcolor="rgba(0,0,0,0)",
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5,
                ),
                margin=dict(t=20, b=40),
                height=380,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

            st.divider()

            # Horizontal bar chart
            st.markdown("### Match Score Breakdown")
            criteria_labels = [
                "GPA Fit", "Major Fit", "Skills",
                "Leadership", "Extracurricular",
            ]
            criteria_values = [
                gpa_fit, major_fit, skills_fit,
                leadership_fit, extracurricular_fit,
            ]
            bar_colors = [
                "#6C63FF" if v >= 70
                else "#F6C90E" if v >= 40
                else "#E05C5C"
                for v in criteria_values
            ]
            fig_bar = go.Figure(go.Bar(
                x=criteria_values,
                y=criteria_labels,
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:.0f}%" for v in criteria_values],
                textposition="outside",
            ))
            fig_bar.update_layout(
                xaxis=dict(range=[0, 120], showgrid=False),
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA",
                margin=dict(t=10, b=10, l=10, r=60),
                height=280,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()

            # Deadline urgency timeline
            st.markdown("### Time Until Deadline")
            deadline_str = s.get("deadline", "")
            try:
                deadline_dt = datetime.strptime(
                    deadline_str, "%Y-%m-%d"
                )
                days_left = max(
                    (deadline_dt - datetime.now()).days, 0
                )
                total_days = 180
                progress_pct = min(
                    (total_days - days_left) / total_days, 1.0
                )
                urgency_color = (
                    "#E05C5C" if days_left < 21
                    else "#F6C90E" if days_left < 42
                    else "#6C63FF"
                )
                urgency_label = (
                    f"{days_left} days left — Act now!"
                    if days_left < 21
                    else f"{days_left} days left — Start preparing"
                    if days_left < 42
                    else (
                        f"{days_left} days left "
                        f"— Good time to start"
                    )
                )
                fig_tl = go.Figure(go.Bar(
                    x=[progress_pct * 100],
                    y=["Deadline"],
                    orientation="h",
                    marker_color=urgency_color,
                    text=[urgency_label],
                    textposition="inside",
                    insidetextanchor="middle",
                ))
                fig_tl.add_trace(go.Bar(
                    x=[(1 - progress_pct) * 100],
                    y=["Deadline"],
                    orientation="h",
                    marker_color="rgba(255,255,255,0.08)",
                    showlegend=False,
                    hoverinfo="skip",
                ))
                fig_tl.update_layout(
                    barmode="stack",
                    xaxis=dict(
                        range=[0, 100],
                        showgrid=False,
                        showticklabels=False,
                    ),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#FAFAFA",
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=100,
                    showlegend=False,
                )
                st.plotly_chart(fig_tl, use_container_width=True)
                st.caption(
                    f"Deadline: "
                    f"**{deadline_dt.strftime('%B %d, %Y')}**"
                )
            except ValueError:
                st.info(
                    "Info: Deadline not available — check the official "
                    "website for the exact date."
                )

            st.divider()

            # Eligibility breakdown
            st.markdown("### Eligibility Breakdown")
            elig_col1, elig_col2 = st.columns(2)
            with elig_col1:
                if user_gpa and req_gpa and user_gpa >= req_gpa:
                    st.success(
                        f"Pass: **GPA** — {user_gpa} meets "
                        f"the {req_gpa} minimum."
                    )
                elif user_gpa and req_gpa and user_gpa < req_gpa:
                    st.error(
                        f"Fail: **GPA** — {user_gpa} is below "
                        f"the {req_gpa} minimum."
                    )
                else:
                    st.info("Info: **GPA** — Verify on official website.")

                if "all" in majors_lower:
                    st.success(
                        f"Pass: **Major** — Open to all majors "
                        f"including {p.get('major')}."
                    )
                elif any(
                    user_major in m or m in user_major
                    for m in majors_lower
                ):
                    st.success(
                        f"Pass: **Major** — {p.get('major')} "
                        f"is a priority field."
                    )
                else:
                    st.warning(
                        f"Warning: **Major** — {p.get('major')} may not "
                        f"be a primary target. Verify eligibility."
                    )

                if s.get("requires_filipino_citizen"):
                    if p.get("is_filipino_citizen"):
                        st.success(
                            "Pass: **Citizenship** — Filipino citizen "
                            "requirement met."
                        )
                    else:
                        st.error(
                            "Fail: **Citizenship** — Filipino citizen "
                            "required."
                        )
                else:
                    st.success(
                        "Pass: **Citizenship** — No citizenship "
                        "restriction."
                    )

            with elig_col2:
                user_level = (
                    p.get("level_seeking") or "undergraduate"
                )
                if user_level in s.get("level", []):
                    st.success(
                        f"Pass: **Level** — Available for "
                        f"{user_level} students."
                    )
                else:
                    st.error(
                        f"Fail: **Level** — May not be available for "
                        f"{user_level} students."
                    )

                if s.get("need_based"):
                    threshold = s.get("income_threshold")
                    user_income = p.get("income_ceiling")
                    if (
                        user_income
                        and threshold
                        and user_income <= threshold
                    ):
                        st.success(
                            "Pass: **Need-based** — Income bracket "
                            "qualifies."
                        )
                    elif (
                        user_income
                        and threshold
                        and user_income > threshold
                    ):
                        st.error(
                            f"Fail: **Need-based** — Income may exceed "
                            f"₱{threshold:,}/month threshold."
                        )
                    else:
                        st.info(
                            "Info: **Need-based** — Verify income "
                            "requirements on official page."
                        )
                else:
                    st.success(
                        "Pass: **Need-based** — Not income-restricted."
                    )

                if user_leadership and s.get("id") in [
                    "sm-foundation-it",
                    "apc-leadership",
                    "chevening",
                ]:
                    st.success(
                        "Pass: **Leadership** — Strong asset for "
                        "this scholarship."
                    )
                elif user_leadership:
                    st.info(
                        "Info: **Leadership** — May strengthen "
                        "your application."
                    )
                else:
                    st.warning(
                        "Warning: **Leadership** — None entered. "
                        "Consider adding informal roles."
                    )

            st.divider()
            st.caption(
                "Reminder: It is highly advisable to do your own research and not solely rely on this AI agent. "
                "Always verify details on the official scholarship websites."
            )
            st.divider()

            # Option C — AI strategic tips
            if st.session_state.tips:
                st.markdown(
                    "### Your Personalized Application Tips"
                )
                for i, tip in enumerate(st.session_state.tips):
                    with st.container(border=True):
                        st.markdown(
                            f"**Tip {i+1}: {tip['title']}**"
                        )
                        st.markdown(tip["description"])

            st.divider()

            # Scholarship details
            st.markdown("### Scholarship Details")
            det_col1, det_col2 = st.columns(2)
            with det_col1:
                st.markdown(f"**Benefits:** {s['benefits']}")
                st.markdown(f"**Deadline:** {s['deadline']}")
                st.markdown(
                    f"**Type:** {s['type'].capitalize()} scholarship"
                )
            with det_col2:
                st.markdown(f"**Core values:** {s['core_values']}")
                if s.get("link") and s["link"].startswith("http"):
                    st.markdown(
                        f"[Official website]({s['link']})"
                    )

            st.divider()
            st.markdown("### Essay Prompt to Prepare For")
            st.info(f'"{s["essay_prompt"]}"')
            st.divider()

            if st.button(
                "Generate my step-by-step action plan",
                type="primary",
            ):
                st.session_state.step = 4
                st.rerun()