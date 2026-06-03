import streamlit as st
import plotly.graph_objects as go
from agents.explainer import generate_match_rationale, generate_application_tips

def render_step2(client):
    if not st.session_state.matches:
        return

    with st.expander("Step 2 — Your top scholarship matches", expanded=(st.session_state.step == 2)):
        if st.session_state.match_source == "live":
            st.success("Live results — sourced from real-time web search via Tavily, ranked by AI adviser.")
        else:
            st.warning("Showing curated local results — live search unavailable. Ranked by AI adviser.")

        # Comparison bar chart
        if len(st.session_state.matches) > 1:
            st.markdown("### How your top matches compare")
            names = [s["name"][:30] + "..." if len(s["name"]) > 30 else s["name"] for s in st.session_state.matches]
            scores = [s["match_score"] for s in st.session_state.matches]
            colors = ["#6C63FF", "#8B84FF", "#A89CF7", "#C5BEFF", "#D4D0FA"]

            fig_compare = go.Figure(go.Bar(
                x=names, y=scores, marker_color=colors[:len(names)], text=scores, textposition="outside"
            ))
            fig_compare.update_layout(
                yaxis_title="AI Match Score", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA", yaxis=dict(range=[0, 11]), margin=dict(t=20, b=20), height=300,
            )
            st.plotly_chart(fig_compare, use_container_width=True)

        st.markdown(f"Found **{len(st.session_state.matches)}** matches ranked by your AI adviser:")

        for i, s in enumerate(st.session_state.matches):
            score = s["match_score"]
            score_color = "High" if score >= 7 else "Medium" if score >= 4 else "Low"
            badge = "Best Match" if i == 0 else f"#{i + 1}"

            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {badge} — {s['name']}")
                    st.caption(f"{s['provider']} · {s['type'].capitalize()} · {', '.join(s['level']).capitalize()}")
                    st.markdown(f"**Benefits:** {s['benefits']}")
                    st.markdown(f"**Deadline:** {s['deadline']}")
                    st.markdown(f"**Why you match:** {' · '.join(s['match_reasons'])}")
                    
                    if s.get("adviser_note"):
                        st.info(f"Adviser: {s['adviser_note']}")
                    if s.get("link") and s["link"].startswith("http"):
                        st.markdown(f"[View scholarship]({s['link']})")
                
                with col2:
                    st.metric("AI Score", f"{score}/10 ({score_color})")
                    
                    # Dashboard button (Updates memory log)
                    if st.button("View full dashboard", key=f"dashboard_{i}", type="primary"):
                        if s['name'] not in st.session_state.preference_log:
                            st.session_state.preference_log.append(s['name'])
                        
                        st.session_state.selected_scholarship = s
                        st.session_state.step = 3
                        with st.spinner("Generating your personalized match analysis..."):
                            st.session_state.rationale = generate_match_rationale(st.session_state.profile, s, client)
                            st.session_state.tips = generate_application_tips(st.session_state.profile, s, client)
                        st.rerun()
                    
                    # Action plan button (Updates memory log)
                    if st.button("View action plan", key=f"action_{i}"):
                        if s['name'] not in st.session_state.preference_log:
                            st.session_state.preference_log.append(s['name'])
                            
                        st.session_state.selected_scholarship = s
                        st.session_state.step = 4
                        st.rerun()