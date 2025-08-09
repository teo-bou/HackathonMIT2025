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
import search_online


class State(TypedDict):
    generate_topic: bool
    messages: Dict
    scenes: Dict
    script: Dict
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
    sys_prompt = prompts.generate_hot_topic + "\n You may use those current trends on TikTok : " + trends_content

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
    workflow.add_node("get_trends", get_trends)
    workflow.add_node("create_topic", create_topic)
    workflow.add_node("get_storyboard", get_storyboard)
    workflow.add_node("split_into_scenes", split_into_scenes)
    workflow.add_node("generate_script", generate_script)
    workflow.add_node("generate_audio_files", generate_audio_files)

    workflow.add_edge(START, "get_trends")
    workflow.add_edge("get_trends", "create_topic")
    workflow.add_edge("create_topic", "get_storyboard")
    workflow.add_edge("get_storyboard", "split_into_scenes")
    workflow.add_edge("split_into_scenes", "generate_script")
    workflow.add_edge("generate_script", "generate_audio_files")
    workflow.add_edge("generate_audio_files", END)
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
        "generate_topic": generate_topic
    }
    
    # Run the pipeline
    graph = pipeline()
    

    # Iterate over the graph to get the final state
    for output in graph.stream(state):
        print("Current Output:", output)
    
    return output  # Final state with generated storyboard and scenes



if __name__ == "__main__":
    generate_storyboard(input("Enter your prompt: "), True)
    #print(search_and_scrape())
    #print(get_trends({}))
