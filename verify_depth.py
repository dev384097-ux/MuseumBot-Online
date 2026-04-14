from dotenv import load_dotenv
import os
from chatbot_engine import MuseumChatbot

load_dotenv()

def test_restored_persona():
    bot = MuseumChatbot()
    if not bot.model_id:
        print("ERROR: AI Model not initialized. Check your API key and quota.")
        return

    print("\n--- Testing Restored Persona Depth ---")
    phrase = "Tell me about Mughal art in short"
    print(f"User: {phrase}")
    
    response, _ = bot.process_message(phrase, {'state': 'idle'})
    print(f"\nAI Response:\n{response}")
    
    if len(response) > 100:
        print("\nSUCCESS: AI provided a detailed, guide-like response.")
    else:
        print("\nWARNING: Response seems brief. Check system instructions.")

if __name__ == "__main__":
    test_restored_persona()
