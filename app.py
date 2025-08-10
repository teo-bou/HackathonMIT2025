import streamlit as st
import agent
import os

st.set_page_config(page_title="Viral Video Maker", layout="wide")
st.title("🎬 VIRAL VIDEO MAKER")

# --- User inputs ---
user_text = st.text_input("💡 Enter your idea or text:")
option1 = st.checkbox("🔍 Search Trends & Generate New Topic", value=False)

st.write("You entered:", user_text)
st.write("Search Trend + new topic:", option1)

if st.button("🚀 Run Agent"):
    if not user_text.strip():
        st.error("❌ Please enter some text before running.")
        st.stop()

    st.info("⏳ Running agent pipeline... Please wait.")

    # Initial state for the pipeline
    state = {
        "messages": {"user_prompt": user_text},
        "generate_topic": option1
    }

    graph = agent.pipeline()

    # Progress tracking
    progress = st.progress(0)
    status_text = st.empty()

    # Output placeholders in tabs
    tabs = st.tabs(["📈 Trends", "🗞️ Topic", "🎭 Storyboard", "🎬 Scenes", "🎥 Media", "📝 Script", "🎶 SFX Description", "🔊 Audio Files", "📜 Prompt"])
    with tabs[0]:
        trends_area = st.empty()
    with tabs[1]:
        topic_area = st.empty()
    with tabs[2]:
        storyboard_area = st.empty()
    with tabs[3]:
        scenes_area = st.empty()
    with tabs[4]:
        media_area = st.container()
    with tabs[5]:
        script_area = st.empty()
    with tabs[6]:
        sfx_area = st.empty()
    with tabs[7]:
        audio_files_area = st.container()
    with tabs[8]:
        prompt_area = st.container()

    step_count = 8
    current_step = 0


    for output in graph.stream(state):

        # Trends
        if "get_trends" in output:
            try:
                content = output["get_trends"]["trends"].content
                trends_area.markdown(f"## Current Trends\n{content}")
            except Exception as e:
                trends_area.error(f"Error reading trends: {e}")

        # Topic
        if "create_topic" in output:
            try:
                topic_text = output["create_topic"]["messages"]["user_prompt"]
                topic_area.markdown(f"## Generated Topic\n{topic_text}")
            except Exception as e:
                topic_area.error(f"Error reading topic: {e}")

        # Storyboard
        if "get_storyboard" in output:
            try:
                story = output["get_storyboard"]["messages"]["storyboard"].content
                storyboard_area.markdown(f"## Storyboard\n{story}")
            except Exception as e:
                storyboard_area.error(f"Error reading storyboard: {e}")

        # Scenes
        if "split_into_scenes" in output:
            try:
                scenes = output["split_into_scenes"]["scenes"]
                scenes_text = f"## Scenes\n"
                for scene in scenes:
                    scenes_text += (
                        f"### Scene {scene['scene_number']} - {scene['title']}\n\n"
                        f"*Timestamp: [{scene['timestart']}, {scene['timeend']}]*\n\n"
                        f"Content: {scene['content']}\n\n"
                        f"Image: {scene['image']}\n\n"
                        f"Onscreen Text: {scene['onscreen_text']}\n\n"
                    )
                scenes_area.markdown(scenes_text)
            except Exception as e:
                scenes_area.error(f"Error creating scenes: {e}")

        # Media
        if "download_media" in output:
            try:
                with media_area:
                    image_files = [f for f in os.listdir('medias') if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
                    if not image_files:
                        st.warning("Aucune image trouvée.")
                    else:
                        for filename in image_files:
                            filepath = os.path.join('medias', filename)
                            st.markdown(f"**📷 {filename}**")
                            st.image(filepath, use_container_width=True)
                            st.markdown("---")
            except Exception as e:
                media_area.error(f"Error creating medias: {e}")

        # Script
        if "generate_script" in output:
            try:
                script = output["generate_script"]["script"]
                script_text = f"## Script\n"
                for scene in script:
                    script_text += (
                        f"### Scene {scene['scene_number']}\n\n"
                        f"Dialog: {scene['dialog']}\n\n"
                        f"*Voice: {scene['voice']}*\n\n"
                    )
                script_area.markdown(script_text)
            except Exception as e:
                script_area.error(f"Error creating script: {e}")

        # SFX
        if "generate_sfx" in output:
            try:
                sfx = output["generate_sfx"]["sfx"]
                sfx_text = f"## SFX\n"
                for timestamp in sfx:
                    sfx_text += (
                        f"### Timestamp {timestamp['timestamp']}\n\n"
                        f"Description: {timestamp['description']}\n\n"
                        f"*Duration: {timestamp['duration']}*\n\n"
                    )
                sfx_area.markdown(sfx_text)
            except Exception as e:
                sfx_area.error(f"Error creating SFX: {e}")

        if "generate_audio_files" in output and output["generate_audio_files"]["audio_files_generated"]:
            try:
                with audio_files_area:
                    files = [f for f in os.listdir("audio") if f.lower().endswith(".mp3")]
                    if not files:
                        st.warning("Aucun fichier audio trouvé dans le dossier.")
                    else:
                        for filename in files:
                            filepath = os.path.join("audio", filename)
                            st.markdown(f"**🎵 {filename}**")
                            st.audio(filepath, format="audio/mp3")  # format peut être ajusté
                            st.markdown("---")
            except Exception as e:
                audio_files_area.error(f"Error creating audio files: {e}")

        if "create_prompt" in output and output["create_prompt"]["prompt"]:
            try:
                with prompt_area:
                    with open("prompt.txt", "r", encoding="utf-8") as f:
                        prompt_content = f.read()

                    st.title("🎬 Générateur de prompt.txt")
                    st.subheader("Contenu du fichier :")
                    st.text_area("prompt.txt", prompt_content, height=400)
                    # Bouton pour télécharger
                    st.download_button(
                        label="📥 Télécharger prompt.txt",
                        data=prompt_content,
                        file_name="prompt.txt",
                        mime="text/plain"
                    )
            except Exception as e:
                prompt_area.error(f"Error creating prompt file: {e}")


        current_step += 1
        progress.progress(min(current_step / step_count, 1.0))
        status_text.text(f"Step {current_step}/{step_count} completed")

    st.success("✅ Pipeline completed!")