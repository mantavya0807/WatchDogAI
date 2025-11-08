from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

print("Testing model download and GPU availability...")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# Download Qwen2-0.5B model for PII detection
# This is a small model that can detect PII well
model_name = "Qwen/Qwen2-0.5B-Instruct"
print(f"\nDownloading {model_name}...")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto" if torch.cuda.is_available() else None
)

print("\nModel downloaded successfully!")
print(f"Model device: {model.device}")
print("\nTesting inference...")

# Simple test
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

generated_ids = model.generate(
    model_inputs.input_ids,
    max_new_tokens=50
)
response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
print(f"Test response: {response}\n")
print("✓ Everything is working!")