import requests
import urllib.parse
import streamlit as st
from openai import AzureOpenAI
import re
import json

# Azure OpenAI setup
endpoint = "YOUR_ENDPOINT"
model_name = "MODEL_NAME"
deployment = "DEPL_NAME"
subscription_key = "YOUR_SUBSCRIPTION_KEY"
api_version = "PREVIEW_VERSION"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
}


# ---------------------------------------------
# 1. User intent parser using OpenAI
# ---------------------------------------------
def parse_user_input(user_input):
    system_prompt = """You are an AI assistant that extracts structured search instructions from user queries.
Return output in JSON with:
- site (medium.com / dev.to / hashnode.com / all)
- keyword (the search keyword)
- format (json or csv)
- elements (list of blog data fields like title, link, description)

ONLY return JSON. Example:
{
  "site": "all",
  "keyword": "agentic ai",
  "format": "json",
  "elements": ["title", "link", "description"]
}
"""
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )
    return eval(response.choices[0].message.content)


# ---------------------------------------------
# URL generators for each site
# ---------------------------------------------
def generate_medium_url(keyword):
    return f"https://medium.com/search?q={urllib.parse.quote_plus(keyword)}"

def generate_devto_url(keyword):
    return f"https://dev.to/search?q={urllib.parse.quote_plus(keyword)}"

def generate_hashnode_url(keyword):
    return f"https://hashnode.com/search/blogs?q={urllib.parse.quote_plus(keyword)}"




# ---------------------------------------------
# Extract blog data from HTML content
# ---------------------------------------------
def get_post(data, site):
    prompt = f"""You are an AI assistant that extracts blog data from raw HTML of a blog listing page on {site}.
Extract up to 30 blog posts. For each post, extract:
- title
- link (should be direct to the blog post, not author profile)
- description (summary if available)
Return result as a JSON list of objects.
Respond with JSON only, without any markdown code block.
"""
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": data}
        ],
       
    )
    result = response.choices[0].message.content.strip()

 
    if result.startswith("```"):
        result = re.sub(r"^```(?:json)?", "", result.strip("` \n"))

    if not result:
        return {"error": "GPT returned an empty response", "raw": ""}

    try:
        return json.loads(result)
    except Exception as e:
        return {"error": f"Failed to parse GPT output: {e}", "raw": result}


# ---------------------------------------------
# Streamlit UI
# ---------------------------------------------
def main():
    st.title("Search Blog Posts")

    user_input = st.text_input("Enter your search query (e.g., 'agentic AI on medium.com'):", "")

    if user_input:
        parsed = parse_user_input(user_input)
        keyword = parsed["keyword"]
        site = parsed["site"]

        sites_to_search = []

        if site == "all":
            sites_to_search = ["medium.com", "dev.to", "hashnode.com"]
        else:
            sites_to_search = [site]

        for s in sites_to_search:
            try:
                if "medium" in s:
                    url = generate_medium_url(keyword)
                elif "dev.to" in s:
                    url = generate_devto_url(keyword)
                elif "hashnode" in s:
                    url = generate_hashnode_url(keyword)
                else:
                    continue  

                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                html = response.text

                st.markdown(f"### Results from {s}")
                extracted = get_post(html, s)

               
                if isinstance(extracted, dict) and "error" in extracted:
                    st.error(extracted["error"])
                    st.code(extracted.get("raw", ""), language="json")
                else:
                    st.json(extracted)

            except Exception as e:
                st.error(f"Failed to fetch from {s}: {e}")

if __name__ == "__main__":
    main()
