import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import os

# Disable Triton
os.environ["DISABLE_TRITON"] = "1"

print("=" * 60)
print("Local Model Inference Test")
print("=" * 60)

# Paths
base_model_name = "meta-llama/Llama-3.1-8B"
lora_path = "./models/llama_discord_final"

print(f"\n1. Loading base model with 8-bit quantization...")
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_name,
    load_in_8bit=True,  # Use 8-bit to save memory
    device_map="auto",
    torch_dtype=torch.float16,
)

print(f"\n2. Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(base_model_name)
tokenizer.pad_token = tokenizer.eos_token

print(f"\n3. Loading LoRA adapters...")
model = PeftModel.from_pretrained(base_model, lora_path)
model.eval()

print("\n" + "=" * 60)
print("✓ Model loaded successfully!")
print("=" * 60)


def generate_response(conversation_context, max_new_tokens=150):
    """
    Generate a response given conversation context.
    
    Args:
        conversation_context: String with previous messages
        max_new_tokens: Maximum tokens to generate
    
    Returns:
        Generated response text
    """
    # Format in Alpaca style
    prompt = f"""Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
Continue the conversation in the style of the user who typically responds in this context.

### Input:
{conversation_context}

### Response:
"""
    
    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    # Decode and extract response
    full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract just the response part after "### Response:"
    if "### Response:" in full_response:
        response = full_response.split("### Response:")[-1].strip()
    else:
        response = full_response
    
    return response


# Test the model
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Interactive Conversation Test")
    print("=" * 60)
    
    # Get 3 initial messages from user
    messages = []
    print("\nEnter 3 initial messages:")
    print("-" * 60)
    
    for i in range(3):
        while True:
            msg = input(f"Message {i+1}: ").strip()
            if msg:
                messages.append(f"User {i+1}: {msg}")
                break
            else:
                print("Please enter a message!")
    
    # Continuous conversation loop
    print("\n" + "=" * 60)
    print("Conversation started! (Press Ctrl+C to exit)")
    print("=" * 60 + "\n")
    
    try:
        while True:
            # Build context from last 3 messages
            context = "\n".join(messages)
            
            print(f"\nContext:\n{context}\n")
            print("Generating response...")
            
            # Generate response
            response = generate_response(context)
            
            print(f"\nDaTruf: {response}\n")
            print("-" * 60)
            
            # Add bot response to messages (sliding window)
            messages.append(f"DaTruf: {response}")
            
            # Keep only last 3 messages
            if len(messages) > 3:
                messages.pop(0)
            
            # Get next user message
            while True:
                user_msg = input("Your message: ").strip()
                if user_msg:
                    messages.append(f"You: {user_msg}")
                    # Keep only last 3 messages
                    if len(messages) > 3:
                        messages.pop(0)
                    break
                else:
                    print("Please enter a message!")
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("✓ Conversation ended!")
        print("=" * 60)
