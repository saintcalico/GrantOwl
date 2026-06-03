import streamlit as st
from agents.timeline import generate_timeline, generate_application_steps

def render_step4():
    if (
        st.session_state.selected_scholarship
        and st.session_state.step == 4
    ):
        s = st.session_state.selected_scholarship

        with st.expander(
            "Step 4 — Your application action plan",
            expanded=True,
        ):
            st.markdown(f"## Action Plan: {s['name']}")
            st.caption(
                "Follow these steps to complete your application. "
                "Download the calendar file to set reminders."
            )
            st.divider()

            steps = generate_application_steps(s)
            for step in steps:
                with st.container(border=True):
                    st.markdown(
                        f"### Step {step['number']} "
                        f"— {step['title']}"
                    )
                    st.markdown(step["description"])

            st.divider()

            st.markdown("### Add milestones to your calendar")
            st.caption(
                "Download the .ics file and open it to import all "
                "4 milestones into Apple Calendar, Google Calendar, "
                "or Outlook."
            )
            ics_bytes = generate_timeline(s)
            st.download_button(
                label="Download application timeline (.ics)",
                data=ics_bytes,
                file_name=f"timeline_{s['id']}.ics",
                mime="text/calendar",
                type="primary",
            )

        st.divider()
        st.caption(
            "Privacy notice: No personal information entered in "
            "this session is stored or transmitted beyond OpenAI's API. "
            "All data clears when you close this tab."
        )