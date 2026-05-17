import numpy as np
from transformers import TrainerCallback, Trainer

class PrintEvalLossCallback(TrainerCallback):
    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        if metrics and "eval_loss" in metrics:
            loss = metrics["eval_loss"]
            print("=" * 60)
            print(f"Step {state.global_step}")
            print(f"Eval Loss: {loss:.6f}")
            print(f"Perplexity: {np.exp(loss):.2f}")
            print("=" * 60)


# PATCH TRAINER GIỮ NGUYÊN NHƯ BẠN
def patch_trainer():
    original_init = Trainer.__init__

    def patched(self, *args, **kwargs):
        kwargs.pop("tokenizer", None)
        kwargs.pop("processing_class", None)
        original_init(self, *args, **kwargs)

    Trainer.__init__ = patched

    return original_init