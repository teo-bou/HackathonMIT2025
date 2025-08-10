# State definition
from typing import TypedDict, Dict
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
import uuid
import json
import prompts
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
from audiogen import generate_audio, generate_audio_sfx
import search_online
from webscraping_videos_pictures import get_pictures_videos
from montage import montage


class State(TypedDict):
    generate_topic: bool
    messages: Dict
    scenes: Dict
    script: Dict
    sfx: Dict
    audio_files_generated: bool
    prompt: bool
    trends: Dict

load_dotenv()  # take environment variables

    ### MISTRAL EXAMPLE

    # Configure Mistral API Key

    # LLM Configuration
llm = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0,
        max_retries=5
)

def get_trends(state: dict) -> State:
    print("***** get_trends *****")
    #if the file trends.txt exists, read it and return the content
    if os.path.exists("trends.txt"):
        with open("trends.txt", "r") as f:
            trends_content = f.read()
        print("Trends loaded from file.")
        # Create an AIMessage object with the content and a unique AI call ID
        ai_call = AIMessage(
            content=trends_content,
            ai_call_id=str(uuid.uuid4())
        )
        # Update the state with the trends content
        new_state = {       
            "trends": ai_call
        }  
        return new_state
    # Create the system prompt for the LLM
    sys_prompt = prompts.search_online_trends_tiktok

    # Invoke LLM
    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=search_online.search_and_scrape(query="latest trends online Tiktok", max_results=3))]
    ).content.strip()
    
    # Create an AIMessage object with the evaluation response and a unique AI call ID
    ai_call = AIMessage(
        content=response,
        ai_call_id=str(uuid.uuid4())
    )
    print(response)

    # Store the trends in a file
    with open("trends.txt", "w") as f:
        f.write(response)
    # Update the state with the evaluation response
    new_state = {
        "trends": ai_call
    }
    return new_state

def get_hot_topic(state: dict) -> State:
    print("***** get_hot_topic *****")
    print(state)
    #Check if hot_topic.txt exists, if so, read it and return the content
    if os.path.exists("hot_topic.txt"):
        with open("hot_topic.txt", "r") as f:
            hot_topic_content = f.read()
        print("Hot topic loaded from file.")
        # Create an AIMessage object with the content and a unique AI call ID
        
        # Update the state with the hot topic content
        new_state = {       
            "messages": {
                "user_prompt": hot_topic_content
            }
        }  
        return new_state

    # Extract the trends content from the state
    trends_content = state["trends"].content

    # Create the system prompt for the LLM
    sys_prompt = prompts.generate_hot_topic

    # Invoke LLM
    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=search_online.search_and_scrape(query="latest news", max_results=5))]
    ).content.strip()
    
    
    print(response)
    # Store the hot topic in a file
    with open("hot_topic.txt", "w") as f:
        f.write(response)

    # Update the state with the evaluation response
    new_state = {
        "messages": {
            "user_prompt": response
        }
    }
    return new_state


def create_topic(state: dict) -> State:
    if state.get("generate_topic", False):
        print("***** create_topic *****")
        # Generate a hot topic based on the trends
        new_state = get_hot_topic(state)
        return new_state
    else:
        print("***** create_topic - No topic generation requested *****")
        # If no topic generation is requested, return the state unchanged
        return state

def get_storyboard(state: dict) -> State:
    print("***** get_storyboard *****")

    # Extract the user prompt from the state
    user_prompt = state["messages"]["user_prompt"]
    # Create the system prompt for the LLM
    sys_prompt = prompts.generate_storyboard + "\n You may use those current trends on TikTok : " + state["trends"].content
    # Invoke LLM
    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=user_prompt)]
    ).content.strip()
    # Create an AIMessage object with the evaluation response and a unique AI call ID
    ai_call = AIMessage(
        content=response,
        ai_call_id=str(uuid.uuid4())
    )
    print(response)

    # Update the state with the evaluation response
    new_state = {
        "messages": {
            "storyboard": ai_call
        }
    }
    return new_state


def split_into_scenes(state: dict) -> State:
    print("***** split_into_scenes *****")

    # Extract the storyboard content from the state
    storyboard_content = state["messages"]["storyboard"].content
    sys_prompt = prompts.split_into_scenes

    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=storyboard_content)]
    ).content.strip().replace("```json", "").replace("```", "")
    print(response)
    # Parse the response into a JSON object
    scenes = json.loads(response)["scenes"]
    # Create a new state with the split scenes
    new_state = {
        "scenes": scenes

    }
    # Write the scenes to a file for debugging purposes
    with open("scenes.json", "w") as f:
        json.dump(new_state, f, indent=4)
    return new_state



def generate_script(state: dict) -> State:
    print("***** generate_script *****")

    # Extract the scenes from the state
    scenes = state["scenes"]
    #with open("scenes.json", "r") as f:
        #scenes = json.load(f)["scenes"]

    # Generate a script based on the scenes
    scenes_text = "\n".join(
        f"Scene {scene['scene_number']}: {scene['title']}\n"
        f"Description: {scene['content']}\n"
        f"Image: {scene['image']}\n"
        f"On-screen text: {scene.get('onscreen_text', 'N/A')}\n"
        for scene in scenes
    )
    
    

    sys_prompt = prompts.generate_script

    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=scenes_text)]
    ).content.strip().replace("```json", "").replace("```", "")
    print(response)
    # Parse the response into a JSON object
    script = json.loads(response)["script"]
    # Write the script to a file for debugging purposes
    with open("script.json", "w") as f:
        json.dump(script, f, indent=4)
    # Create a new state with the split scenes
    new_state = {
        "script": script
    }
    return new_state


def generate_sfx(state: dict) -> State:
    print("***** generate_sfx *****")

    # Extract the scenes from the state
    scenes = state["scenes"]
    # with open("scenes.json", "r") as f:
    # scenes = json.load(f)["scenes"]

    # Generate sound design based on the scenes
    scenes_text = "\n".join(
        f"Scene {scene['scene_number']}: {scene['title']}\n"
        f"Timestamp beginning: {scene['timestart']}\n"
        f"Timestamp end: {scene['timeend']}\n"
        f"Description: {scene['content']}\n"
        f"Image: {scene['image']}\n"
        f"On-screen text: {scene.get('onscreen_text', 'N/A')}\n"
        for scene in scenes
    )

    sys_prompt = prompts.generate_sfx

    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=scenes_text)]
    ).content.strip().replace("```json", "").replace("```", "")
    print(response)
    # Parse the response into a JSON object
    sfx = json.loads(response)["sfx"]
    # Write the sfx to a file for debugging purposes
    with open("sfx.json", "w") as f:
        json.dump(sfx, f, indent=4)
    # Create a new state with the split scenes
    new_state = {
        "sfx": sfx
    }
    return new_state


def generate_audio_files(state: dict) -> State:
    print("***** generate_audio *****")
    for scene in state["script"]:
        # Generate audio for each scene
        text = scene["dialog"]
        voice = scene.get("voice", "ASMR")
        path = f"audio/dialog_scene_{scene['scene_number']}.mp3"
        generate_audio(text, path, voice)
    print("Dialog audio generation completed for all scenes.")
    for sfx in state["sfx"]:
        # Generate audio for each sfx
        description = sfx["description"]
        duration = sfx["duration"]
        path = f"audio/sfx_{sfx['timestamp']}.mp3"
        generate_audio_sfx(description, duration, path)
    print("SFX audio generation completed for all scenes.")
    new_state = {
        "audio_files_generated": True
    }
    return new_state

def download_media(state: dict) -> dict:
    print("***** download_media *****")
    scenes_data = state["scenes"]
    if isinstance(scenes_data, str):  # si c'est une chaîne JSON
        scenes_data = json.loads(scenes_data)
    if isinstance(scenes_data, dict):
        scenes_list = scenes_data.get("scenes", [])
    else:
        scenes_list = scenes_data

    queries = []
    for scene in scenes_list:
        if "image" in scene:
            queries.append((scene["scene_number"], scene["image"]))

    get_pictures_videos(queries, is_video=False)


def delete_files():
    folders = ["medias","audio"]
    for folder in folders:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Erreur lors de la suppression de {file_path} : {e}")

def create_prompt(state: dict) -> dict:
    print("***** create_prompt *****")
    lines = []
    #lines.append(f"Titre : \"{state['messages']['user_prompt']}\"")

    # Narration
    lines.append("Narration:")
    for script in state['script']:
        start_time = "00:00:00"
        for s in state['scenes']:
            if s['scene_number'] == script["scene_number"]:
                start_time = s['timestart']
        lines.append(f"audio\dialog_scene_{script['scene_number']}.mp3 {start_time}")

    # SFX
    lines.append("SFX:")
    for sfx in state['sfx']:
        lines.append(f"audio\sfx_{sfx['timestamp']}.mp3 {sfx['timestamp'].replace('_',':')}")

    # Images
    lines.append("Images:")
    for scene in state['scenes']:
        lines.append(f"medias\scene{scene['scene_number']}.jpg {scene['timestart']} - {scene['timeend']}")

    # Texte
    lines.append("Texte:")
    for scene in state['scenes']:
        if scene["onscreen_text"] != "":
            lines.append(f'"{scene["onscreen_text"]}" {scene["timestart"]} - {scene["timeend"]}')

    # Écriture dans prompt.txt
    with open("prompt.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    new_state = {
        "prompt": True
    }
    return new_state

def create_video(state: dict) -> dict:
    print("***** create_video *****")
    montage()
    new_state = {
        "prompt": True
    }
    return new_state

def pipeline():

    delete_files()

    # Start the Graph with the initial state
    workflow = StateGraph(State)
    

    # Define the workflow steps
    workflow.add_node("get_trends", get_trends)
    workflow.add_node("create_topic", create_topic)
    workflow.add_node("get_storyboard", get_storyboard)
    workflow.add_node("split_into_scenes", split_into_scenes)
    workflow.add_node("download_media", download_media)
    workflow.add_node("generate_script", generate_script)
    workflow.add_node("generate_sfx", generate_sfx)
    workflow.add_node("generate_audio_files", generate_audio_files)
    workflow.add_node("create_prompt", create_prompt)
    workflow.add_node("create_video", create_video)

    workflow.add_edge(START, "get_trends")
    workflow.add_edge("get_trends", "create_topic")
    workflow.add_edge("create_topic", "get_storyboard")
    workflow.add_edge("get_storyboard", "split_into_scenes")
    workflow.add_edge("split_into_scenes", "download_media")
    workflow.add_edge("download_media", "generate_script")
    workflow.add_edge("generate_script", "generate_sfx")
    workflow.add_edge("generate_sfx", "generate_audio_files")
    workflow.add_edge("generate_audio_files", "create_prompt")
    workflow.add_edge("create_prompt", "create_video")
    workflow.add_edge("create_video", END)

    # Run the workflow
    graph = workflow.compile()

    return graph


def generate_storyboard(user_prompt: str, generate_topic: bool) -> State:
    """
    Generate a storyboard based on the user prompt.
    """
    # Initialize the state with the user prompt
    state = {
        "messages": {
            "user_prompt": user_prompt
        },
        "generate_topic": generate_topic,
        "audio_files_generated": False
    }
    
    # Run the pipeline
    graph = pipeline()
    final_output = None

    # Iterate over the graph to get the final state
    for output in graph.stream(state):
        print("Current Output:", output)
        final_output = output
    
    return final_output  # Final state with generated storyboard and scenes



if __name__ == "__main__":
    generate_storyboard(input("Enter your prompt: "), False)
    #print(search_and_scrape())
    #print(get_trends({}))
