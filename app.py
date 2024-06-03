import streamlit as st
from openai import OpenAI
from io import BytesIO
from PIL import Image
import base64
import requests

st.set_page_config(page_title='KeyChat', page_icon='🗝')

# Initialize session state
if 'history' not in st.session_state:
    st.session_state['history'] = [{'role': 'system', 'content': ''}]
    st.session_state['counters'] = [0, 1]
    st.session_state['selected_model'] = None
    st.session_state['image_gen_model'] = None
    st.session_state['image_gen_mode'] = False  # Default to Text/Vision mode

# --- Sidebar ---
# st.sidebar.title("Settings")
base_url = st.sidebar.text_input("Base URL", "https://api.openai.com/v1")
openai_key = st.sidebar.text_input("Key", type="password")

# Fetch Models Button
if st.sidebar.button("Fetch Models"):
    if base_url and openai_key:
        if not base_url.startswith("https://") or not base_url.endswith("/v1"):
            st.error("Invalid Base URL. Please enter a URL starting with 'https://' and ending with '/v1'.")
            st.stop()
        else:
            url = f"{base_url}/models"
            headers = {"Authorization": f"Bearer {openai_key}"}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                text_vision_models = []
                image_gen_models = []

                # Handle different response structures
                if 'data' in data:
                    for model in data['data']:
                        if isinstance(model, dict) and 'id' in model:
                            if model['id'].startswith(
                                (
                                    "gpt",
                                    "claude",
                                    "llama",
                                    "mixtral",
                                    "mistral",
                                    "llava",
                                    "gemma",
                                    "phind",
                                    "gemini",
                                )
                            ):
                                text_vision_models.append(model['id'])
                            elif model['id'].startswith(('dall', 'stable', 'realistic')):
                                image_gen_models.append(model['id'])
                elif isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict) and ('is_free' in value or 'type' in value) and not isinstance(key, int):
                            if key.startswith(
                                (
                                    "gpt",
                                    "claude",
                                    "llama",
                                    "mixtral",
                                    "mistral",
                                    "llava",
                                    "gemma",
                                    "phind",
                                    "gemini",
                                )
                            ):
                                text_vision_models.append(key)
                            elif key.startswith(('dall', 'stable', 'realistic')):
                                image_gen_models.append(key)

                st.session_state["available_text_vision_models"] = text_vision_models
                st.session_state["available_image_gen_models"] = image_gen_models
            else:
                st.error(f"Error fetching models: {response.status_code}")
                if response.status_code == 401:
                    st.error("AuthenticationError: Invalid API Key.")
                else:
                    st.error(response.json())

# Model Selection
if 'available_text_vision_models' in st.session_state:
    selected_model = st.sidebar.selectbox("Select Text/Vision Model", st.session_state['available_text_vision_models'])
    st.session_state['selected_model'] = selected_model
if 'available_image_gen_models' in st.session_state:
    selected_image_gen_model = st.sidebar.selectbox("Select Image Gen Model", st.session_state['available_image_gen_models'])
    st.session_state['image_gen_model'] = selected_image_gen_model
st.sidebar.markdown("---")

with st.sidebar.expander("System Message"):
    st.session_state['history'][0]['content'] = st.text_area('Enter system message:', 
                                                           st.session_state['history'][0]['content'], 
                                                           label_visibility='collapsed')
with st.sidebar.expander("Advanced Settings"):
    image_detail = st.selectbox('Image Detail', ['low', 'high'])
    temperature = st.slider('Temperature', 0.0, 2.0, 0.7)
    max_tokens = st.slider('Max Token Output', 100, 1000, 300)

# --- Main Content ---
st.markdown('# KeyChat Client 🤖')

# Image Generation Toggle
st.session_state['image_gen_mode'] = st.toggle("Image Generation Mode")

# Chat display
for msg in st.session_state['history'][1:]:
    if msg['role'] == 'user':
        with st.chat_message('user'):
            for i in msg['content']:
                if i['type'] == 'text':
                    st.write(i['text'])
                else:
                    with st.expander('Attached Image'):
                        img = Image.open(BytesIO(base64.b64decode(i['image_url']['url'][23:])))
                        st.image(img)
    else:
        with st.chat_message('assistant'):
            # Check if the assistant message indicates an image generation
            if msg['content'].startswith("Image:"):
                image_url = msg['content'][6:].strip()  # Extract the image URL
                img = Image.open(BytesIO(requests.get(image_url).content))
                st.image(img)  # Display the image
            else:
                msg_content = ''.join(['  ' + char if char == '\n' else char for char in msg['content']])  # fixes display issue
                st.markdown('Assistant: ' + msg_content) 

# User input area
text_input = st.text_input('Prompt', '', key=st.session_state['counters'][0])
img_input = st.file_uploader('Images', accept_multiple_files=True, key=st.session_state['counters'][1])

# Button layout
col1, col2 = st.columns([9, 1])  # Use st.columns for button layout

# Send button
with col1:
    if st.button('Send'):
        if not (text_input or img_input):
            st.warning("You can't just send nothing!")
            st.stop()

        if not base_url or not openai_key:
            st.error("Please enter both Base URL and Key.")
            st.stop()

        if not base_url.startswith("https://") or not base_url.endswith("/v1"):
            st.error("Invalid Base URL. Please enter a URL starting with 'https://' and ending with '/v1'.")
            st.stop()

        msg = {'role': 'user', 'content': []}
        if text_input:
            msg['content'].append({'type': 'text', 'text': text_input})

        for img in img_input:
            if img.name.split('.')[-1].lower() not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                st.warning('Only .jpg, .png, .gif, or .webp are supported')
                st.stop()
            encoded_img = base64.b64encode(img.read()).decode('utf-8')
            msg['content'].append(
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/jpeg;base64,{encoded_img}',
                        'detail': image_detail
                    }
                }
            )

        st.session_state['history'].append(msg)
        history = (
            st.session_state['history']
            if st.session_state['history'][0]['content']
            else st.session_state['history'][1:]
        )

        client = OpenAI(
            base_url=base_url,
            api_key=openai_key,
        )
        try:
            if st.session_state['image_gen_mode']:  # Image Generation Mode
                response = client.images.generate(
                    model=st.session_state.get('image_gen_model'),
                    prompt=text_input,
                    n=1,
                    size="1024x1024",
                )

                for image_data in response.data:
                    image_url = image_data.url
                
                # Append a special message indicating an image generation to the chat history
                st.session_state['history'].append(
                    {'role': 'assistant', 'content': f"Image: {image_url}"}
                )

            else:  # Text/Vision Mode
                response = client.chat.completions.create(
                    model=st.session_state.get('selected_model', 'gpt-4-vision-preview'),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=history
                )
                st.session_state['history'].append(
                    {'role': 'assistant', 'content': response.choices[0].message.content}
                )

            st.session_state['counters'] = [i + 2 for i in st.session_state['counters']]
            st.rerun()

        except Exception as e:
            error_message = str(e)
            if "500" in error_message:
                st.error("Oops, something went wrong at model hosts end. Would you try checking the status of service and try again later.")
            elif "401" in error_message:
                st.error("AuthenticationError: Invalid API Key.")
            elif "IndexError" in error_message:
                st.error("Something went wrong. Please check your request and try again.")
            else:
                short_error_message = error_message.split(" - ")[0] 
                st.error(f"An error occurred: {short_error_message}")

# Clear button
with col2:
    if st.button('Clear'):
        st.session_state['history'] = [st.session_state['history'][0]]
        st.rerun()
