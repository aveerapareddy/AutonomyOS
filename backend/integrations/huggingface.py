"""Optional local PyTorch/Transformers proposal inference; no simulator authority."""
import json
from backend.experiments.models import ExperimentRequest


def validate_proposal(text: str) -> ExperimentRequest:
    """Accept JSON or one JSON code fence, then enforce the tool's strict schema."""
    value = text.strip()
    if value.startswith("```json\n") and value.endswith("\n```"):
        value = value[len("```json\n"):-len("\n```")]
    return ExperimentRequest.model_validate_json(value)


def propose(objective: str, model_id: str, revision: str):
    """Download only a pinned revision; require GPU and avoid remote Python code.

    Imports are lazy so CPU simulation does not require model dependencies.
    Live validation is pending; this function is not proof of successful inference.
    """
    import re
    import time
    import importlib.metadata
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Use a full Hugging Face commit SHA, not a moving branch")
    if not 1 <= len(objective) <= 4000:
        raise ValueError("Objective must contain 1-4000 characters")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for this validation")
    torch.manual_seed(42)
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, revision=revision, trust_remote_code=False, use_safetensors=True,
        torch_dtype=torch.float16).to("cuda").eval()
    schema = json.dumps(ExperimentRequest.model_json_schema())
    messages = [
        {"role": "system", "content": "detailed thinking off"},
        {"role": "user", "content": "Propose a warehouse simulation experiment. Return one JSON object only matching this schema: " + schema + "\nObjective: " + objective}]
    inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                           return_tensors="pt", return_dict=True).to("cuda")
    torch.cuda.synchronize()
    inference_start = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=256,
                                   pad_token_id=tokenizer.eos_token_id)
    torch.cuda.synchronize()
    output = generated[0, inputs["input_ids"].shape[-1]:]
    text = tokenizer.decode(output, skip_special_tokens=True)
    # Preserve raw output even when validation fails; callers must never treat it as a tool call.
    metadata = {
        "model_id": model_id, "revision": revision, "backend": "pytorch-transformers",
        "gpu": torch.cuda.get_device_name(), "cuda": torch.version.cuda,
        "versions": {name: importlib.metadata.version(name) for name in
                     ("torch", "transformers", "huggingface-hub", "safetensors")},
        "input_tokens": inputs["input_ids"].shape[-1], "output_tokens": len(output),
        "inference_seconds": time.perf_counter()-inference_start,
        "total_seconds": time.perf_counter()-start,
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "raw_output": text, "inference_cost_usd": None,
        "limitations": ["One proposal is not an agent reliability evaluation.",
                        "GPU rental cost must be reconciled with provider billing.",
                        "Not an NVIDIA NIM server or Isaac Sim integration."]}
    return text, metadata
