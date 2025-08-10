import streamlit as st
import agent

st.title("Streamlit App Example")

# Text input
user_text = st.text_input("Enter some text:")

# Checkboxes
option1 = st.checkbox("Search")

st.write("You entered:", user_text)
st.write("Search Trend + new topic:", option1)

if st.button("Run Agent"):
    st.info("Running agent pipeline...")

    # Initial state for the pipeline
    state = {
        "messages": {
            "user_prompt": user_text
        },
        "generate_topic": option1
    }

    graph = agent.pipeline()
    output_state = None

    # Placeholders for dynamic updates
    trends_placeholder = st.empty()
    topic_placeholder = st.empty()
    storyboard_placeholder = st.empty()



    
    

    # Iterate over the graph to get the final state
    for output in graph.stream(state):
        #st.write("Current Output:", output)
        with trends_placeholder.expander("Show Trends"):
            try:
                st.markdown("## Trends\n" + output.get("get_trends").get("trends", "").content)
            except Exception as e:
                pass
        with topic_placeholder.expander("Show Topics"):
            try:
                st.markdown("## Topics\n" + output.get("create_topic").get("messages", "").get("user_prompt", ""))
            except Exception as e:
                pass
        with storyboard_placeholder.expander("Show Storyboard"):
            try:
                st.markdown("## Storyboard\n" + output.get("get_storyboard").get("messages", "").get("storyboard", "").content)
            except Exception as e:
                pass
    st.success("Pipeline completed!")