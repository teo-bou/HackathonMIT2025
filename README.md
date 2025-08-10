# HackathonMIT2025

## Project Initialization

1. **Create a virtual environment:**

    ```bash
    python -m venv venv
    ```

2. **Activate the virtual environment:**

    - **On Windows:**
      ```cmd
      venv\Scripts\activate
      ```
    - **On macOS/Linux:**
      ```bash
      source venv/bin/activate
      ```

3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables:**

    - Copy the example environment file and rename it:
      ```bash
      cp .env_example .env
      ```
    - Fill in your Mistral API key, which you can obtain for free from [Mistral Console](https://console.mistral.ai/).

5. **Run the agent:**

    ```bash
    python agent.py
    ```

6. **Run the app**

    ```bash
    streamlit run app.py
    ```