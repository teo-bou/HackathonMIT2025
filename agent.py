# State definition
from typing import TypedDict, Dict
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
import uuid
import json
import prompts
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
from audiogen import generate_audio

class State(TypedDict):
    messages: Dict
    scenes: Dict
    script: Dict

load_dotenv()  # take environment variables

    ### MISTRAL EXAMPLE

    # Configure Mistral API Key

    # LLM Configuration
llm = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0,
        max_retries=5
)


def get_storyboard(state: dict) -> State:
    print("***** get_storyboard *****")

    # Extract the user prompt from the state
    user_prompt = state["messages"]["user_prompt"]

    # Create the system prompt for the LLM
    sys_prompt = prompts.generate_storyboard
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



def generate_script(state: dict) -> None:
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



    



def generate_audio_files(state: dict) -> None:
    print("***** generate_audio *****")
    for scene in state["script"]:
        # Generate audio for each scene
        text = scene["dialog"]
        voice = scene.get("voice", "ASMR")
        path = f"audio/scene_{scene['scene_number']}.mp3"
        generate_audio(text, path, voice)
    print("Audio generation completed for all scenes.")


def pipeline():
    # Start the Graph with the initial state
    workflow = StateGraph(State)
    

    # Define the workflow steps
    workflow.add_node("get_storyboard", get_storyboard)
    workflow.add_node("split_into_scenes", split_into_scenes)
    workflow.add_node("generate_script", generate_script)
    workflow.add_node("generate_audio_files", generate_audio_files)

    workflow.add_edge(START, "get_storyboard")
    workflow.add_edge("get_storyboard", "split_into_scenes")
    workflow.add_edge("split_into_scenes", "generate_script")
    workflow.add_edge("generate_script", "generate_audio_files")
    workflow.add_edge("generate_audio_files", END)
    # Run the workflow
    graph = workflow.compile()

    return graph


def generate_storyboard(user_prompt: str) -> State:
    """
    Generate a storyboard based on the user prompt.
    """
    # Initialize the state with the user prompt
    state = {
        "messages": {
            "user_prompt": user_prompt
        }
    }
    
    # Run the pipeline
    graph = pipeline()
    

    # Iterate over the graph to get the final state
    for output in graph.stream(state):
        print("Current Output:", output)
    
    return output  # Final state with generated storyboard and scenes



if __name__ == "__main__":
    generate_storyboard(input("Enter your prompt: "))
