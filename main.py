from graph import app

inputs = {"question": "How does QLoRA reduce memory usage compared to standard LoRA?"}
for output in app.stream(inputs):
    for key, value in output.items():
        print(f"\nFinished Node: {key}")