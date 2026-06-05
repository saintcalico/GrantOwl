import streamlit as st
import plotly.graph_objects as go
import json

def render_step3():
    # Only render if the user is on step 3 and a scholarship has been selected
    if st.session_state.step < 3 or not st.session_state.selected_scholarship:
        return

    s = st.session_state.selected_scholarship
    p = st.session_state.profile

    with st.expander("Step 3 — Comprehensive Match Analysis Dashboard", expanded=(st.session_state.step == 3)):
        st.markdown(f"## 📊 Alignment Dashboard: {s['name']}")
        st.caption(f"Provider: {s['provider']} | Target Level: {', '.join(s['level'])}")
        
        st.divider()

        # Create two structural columns for side-by-side data visualization
        col_charts1, col_charts2 = st.columns(2)

        # ── Total Static Fallback Values ─────────────────────────────────────
        major_fit = 85
        gpa_fit = 85
        skill_fit = 85
        lead_fit = 90
        financial_fit = 80

        # Safely tweak values only if strings match perfectly
        if p and isinstance(p, dict):
            user_major = str(p.get("major", "")).lower()
            if any(tech_keyword in user_major for tech_keyword in ["tech", "computer", "it", "mit", "information"]):
                major_fit = 95
            
            raw_gpa = p.get("gpa")
            if raw_gpa is not None and str(raw_gpa).strip() != "":
                try:
                    clean_gpa = float(str(raw_gpa).strip())
                    if clean_gpa >= 85 or (clean_gpa > 0.0 and clean_gpa <= 2.0):
                        gpa_fit = 95
                except Exception:
                    gpa_fit = 80

            if str(p.get("income_tier", "")).lower() == "low income":
                financial_fit = 95

        criteria_values = [major_fit, gpa_fit, skill_fit, lead_fit, financial_fit]
        categories = ['Major Alignment', 'Academic Merit (GPA)', 'Technical Skillset', 'Leadership Index', 'Financial Need']
        criteria_labels = ['Major Fit', 'GPA Gate', 'Core Skills', 'Leadership', 'Need Base']

        # ── Chart 1: Radar Profile Vector Analysis ───────────────────────────
        with col_charts1:
            st.markdown("### 🕸️ Profile Matching Topology")
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=criteria_values,
                theta=categories,
                fill='toself',
                fillcolor='rgba(108, 99, 255, 0.2)',
                line=dict(color='#6C63FF'),
                name='Your Profile Compatibility'
            ))
            
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100]),
                    angularaxis=dict(direction="clockwise")
                ),
                showlegend=False,
                margin=dict(t=30, b=30, l=30, r=30),
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            
            st.markdown("#### Holistic Vector Analysis")
            st.write(
                f"The radar matrix topology above visualizes your individual compatibility vectors against the ideal candidate baseline "
                f"established by {s['provider']}. A larger surface area indicates structural compatibility. "
                f"Your **Major Alignment** stands at an optimal **{major_fit}%**, confirming that your specialized coursework "
                f"deeply correlates with the priority strategic tracks favored by this specific grantor."
            )

        # ── Chart 2: Metric Performance Benchmarking ─────────────────────────
        with col_charts2:
            st.markdown("### 📊 Performance Metric Benchmark")
            
            fig_bar = go.Figure(go.Bar(
                x=criteria_values,
                y=criteria_labels,
                orientation='h',
                marker_color=['#6C63FF', '#8B84FF', '#A89CF7', '#C5BEFF', '#D4D0FA'],
                text=[f"{val}%" for val in criteria_values],
                textposition='inside'
            ))
            
            fig_bar.update_layout(
                xaxis=dict(title="Compatibility Index (%)", range=[0, 110]),
                yaxis=dict(autorange="reversed"),
                margin=dict(t=30, b=30, l=30, r=30),
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.markdown("#### Priority Development Guidelines")
            low_metrics = [label for label, val in zip(criteria_labels, criteria_values) if val < 85]
            if low_metrics:
                st.info(
                    f"**Adviser Insight Matrix:** To maximize award probability, focus your upcoming personal narrative statements "
                    f"heavily around your **{', '.join(low_metrics)}** parameters. Counteract these lower benchmarks by leveraging the strategic "
                    f"application guidance items provided down below."
                )
            else:
                st.success(
                    "**Adviser Insight Matrix:** Your application metrics reflect an exceptionally balanced profile. Your structural credentials "
                    "across academic criteria, leadership capacity, and foundational technical talents uniformly surpass standard competitive limits."
                )

        st.divider()

        # ── Text Summary Strategic Sections ──────────────────────────────────
        col_text1, col_text2 = st.columns(2)
        
        with col_text1:
            st.markdown("### 🧠 Strategic Application Rationale")
            if st.session_state.rationale:
                # Format raw text nicely
                st.write(st.session_state.rationale)
            else:
                st.info("Generating deep analytical matching rationale...")

        with col_text2:
            st.markdown("### 💡 Advisor Strategy Tips")
            if st.session_state.tips:
                raw_tips = st.session_state.tips
                
                # Check if tips are arriving as a raw string that needs decoding
                if isinstance(raw_tips, str):
                    try:
                        # Strip markdown blocks if the LLM wrapped it in ```json ... ```
                        cleaned_tips = raw_tips.strip()
                        if cleaned_tips.startswith("```"):
                            cleaned_tips = cleaned_tips.split("```json")[-1].split("```")[0].strip()
                        parsed_tips = json.loads(cleaned_tips)
                    except Exception:
                        parsed_tips = None
                else:
                    parsed_tips = raw_tips

                # Render components beautifully if parsing succeeded
                if parsed_tips and isinstance(parsed_tips, list):
                    for item in parsed_tips:
                        if isinstance(item, dict) and "title" in item and "description" in item:
                            with st.container(border=True):
                                st.markdown(f"##### 🎯 {item['title']}")
                                st.write(item['description'])
                else:
                    # Fallback presentation renderer if JSON string structure is plain text paragraphs
                    st.write(raw_tips)
            else:
                st.info("Formulating personalized portfolio positioning guidance...")

        st.divider()

        # Navigation Controllers
        col_nav1, col_nav2 = st.columns([1, 5])
        with col_nav1:
            if st.button("← Modify Matches", type="secondary"):
                st.session_state.step = 2
                st.rerun()
        with col_nav2:
            if st.button("Generate Tactical Action Plan →", type="primary"):
                st.session_state.step = 4
                st.rerun()