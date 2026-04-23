import json

notebook_path = r'd:\ai_trans_demo\deploy-model.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code' and '# 1. SETUP THƯ MỤC CỦA REPO' in cell['source']:
        source = cell['source']
        
        # Add gpu_lock
        if 'gpu_lock = threading.Lock()' not in source:
            source = source.replace('import threading', 'import threading\ngpu_lock = threading.Lock()')
            
        # Remove split_text function and its usage
        import re
        source = re.sub(r'def split_text\(text, max_chars=500\):.*?return chunks', '', source, flags=re.DOTALL)
        source = source.replace('chunks = split_text(text)', 'chunks = [text]')
        
        # Wrap model.generate with gpu_lock
        # Look for the with torch.inference_mode(): block
        old_block = '''        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
                repetition_penalty=1.0,
                pad_token_id=tokenizer.eos_token_id
            )'''
            
        new_block = '''        with torch.inference_mode():
            with gpu_lock:
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=False,
                    repetition_penalty=1.0,
                    pad_token_id=tokenizer.eos_token_id
                )'''
        
        source = source.replace(old_block, new_block)
        
        cell['source'] = source
        print("Updated code cell in notebook.")

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
