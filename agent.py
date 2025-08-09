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

class State(TypedDict):
    messages: Dict
    scenes: Dict
    images: Dict

load_dotenv()  # take environment variables

print("This is the main function of the script.")
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
    return new_state



def pipeline():
    # Start the Graph with the initial state
    workflow = StateGraph(State)
    

    # Define the workflow steps
    workflow.add_node("get_storyboard", get_storyboard)
    workflow.add_node("split_into_scenes", split_into_scenes)

    workflow.add_edge(START, "get_storyboard")
    workflow.add_edge("get_storyboard", "split_into_scenes")
    workflow.add_edge("split_into_scenes", END)
    # Run the workflow
    graph = workflow.compile()

    return graph


if __name__ == "__main__":
    graph = pipeline()
    user_prompt = input()
    state = {"messages": {"user_prompt": user_prompt}}
    # Iterate over the graph
    for output in graph.stream(state):
        print("Current Output:", output)
