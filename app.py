#!/usr/bin/env python3
"""
Company Brochure Generator
A tool that analyzes company landing pages and generates brochures using various AI models.
"""

import os
import requests
from bs4 import BeautifulSoup
from typing import List
from dotenv import load_dotenv

# AI model imports
from openai import OpenAI
import google.generativeai as genai
import anthropic

# UI framework
import gradio as gr

class Website:
    """A class to represent and process webpage content."""
    
    url: str
    title: str
    text: str

    def __init__(self, url):
        self.url = url
        response = requests.get(url)
        self.body = response.content
        soup = BeautifulSoup(self.body, 'html.parser')
        self.title = soup.title.string if soup.title else "No title found"
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        self.text = soup.body.get_text(separator="\n", strip=True)

    def get_contents(self):
        return f"Webpage Title:\n{self.title}\nWebpage Contents:\n{self.text}\n\n"

def initialize_environment():
    """Initialize environment variables and API configurations."""
    load_dotenv()
    os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'your-key-if-not-using-env')
    os.environ['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', 'your-key-if-not-using-env')
    os.environ['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY', 'your-key-if-not-using-env')

    # Initialize AI clients
    global openai, claude
    openai = OpenAI()
    claude = anthropic.Anthropic()
    genai.configure()

def stream_gpt(prompt):
    """Generate content using OpenAI's GPT model."""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    stream = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        stream=True
    )
    result = ""
    for chunk in stream:
        result += chunk.choices[0].delta.content or ""
        yield result

def stream_claude(prompt):
    """Generate content using Anthropic's Claude model."""
    result = claude.messages.stream(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0.7,
        system=system_message,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    response = ""
    with result as stream:
        for text in stream.text_stream:
            response += text or ""
            yield response

def stream_gemini(prompt):
    """Generate content using Google's Gemini model."""
    gemini = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        safety_settings=None,
        system_instruction=system_message
    )

    response = gemini.generate_content(
        prompt, 
        safety_settings=[
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}
        ], 
        stream=True
    )
    
    result = ""
    for chunk in response:
        result += chunk.text
        yield result

def stream_brochure(company_name, url, model, response_tone):
    """Generate a brochure based on company website content."""
    prompt = f"Please generate a {response_tone} company brochure for {company_name}. Here is their landing page:\n"
    prompt += Website(url).get_contents()
    
    if model == "GPT":
        result = stream_gpt(prompt)
    elif model == "Claude":
        result = stream_claude(prompt)
    elif model == "Gemini":
        result = stream_gemini(prompt)
    else:
        raise ValueError("Unknown model")
    
    yield from result

def main():
    """Main function to run the application."""
    # System message for AI models
    global system_message
    system_message = "You are an assistant that analyzes the contents of a company website landing page \
    and creates a short brochure about the company for prospective customers, investors and recruits. Do not use any logos. Respond in markdown."

    # Initialize environment
    initialize_environment()

    # Create Gradio interface
    view = gr.Interface(
        fn=stream_brochure,
        inputs=[
            gr.Textbox(label="Company name:"),
            gr.Textbox(label="Landing page URL including http:// or https://"),
            gr.Dropdown(["GPT", "Claude", "Gemini"], label="Select model"),
            gr.Dropdown(["Informational", "Promotional", "Humorous"], label="Select tone")
        ],
        outputs=[gr.Markdown(label="Brochure:")],
        flagging_mode="never"
    )
    
    # Launch the interface
    view.launch()

if __name__ == "__main__":
    main()