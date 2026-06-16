import time

sim_message = "Streaming simulated response for your prompt"

def get_simulated_response(message):
    reply_text = f"Python Core Engine streaming response for your prompt: '{message}'"
    words = reply_text.split(" ")
    
    for word in words:
        yield word + " "
        time.sleep(0.08)