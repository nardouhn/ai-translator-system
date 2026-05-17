import numpy as np
from transformers import TrainerCallback, Trainer


class PrintEvalLossCallback(TrainerCallback):
    """Custom callback to print evaluation loss and perplexity"""
    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        if metrics and "eval_loss" in metrics:
            loss = metrics["eval_loss"]
            print("\n" + "=" * 60)
            print(f"📊 Step {state.global_step}: Eval Loss = {loss:.6f}")
            print(f"   Perplexity = {np.exp(loss):.2f}")
            print("=" * 60 + "\n")


def patch_trainer():
    """Patch Trainer to remove conflicting tokenizer arguments"""
    original_init = Trainer.__init__

    def patched(self, *args, **kwargs):
        kwargs.pop("tokenizer", None)
        kwargs.pop("processing_class", None)
        original_init(self, *args, **kwargs)

    Trainer.__init__ = patched
    return original_init