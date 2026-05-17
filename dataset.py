import pandas as pd
from datasets import Dataset
from sklearn.model_selection import train_test_split
from config import *


def prepare_raw_data():
    """
    Prepare raw data splits (train/valid/test) - DRY principle
    
    Returns:
        Tuple of (train_df, valid_df, test_df)
    """
    print("📖 Loading and sampling data...")
    df_all = pd.read_csv(DATA_PATH)
    df_all = df_all.dropna(subset=['en', 'vi', 'domain'])
    df_all = df_all.drop_duplicates(subset=["en", "vi"])

    # Custom sampling per domain
    def custom_sampling(group):
        if len(group) > MAX_PER_DOMAIN:
            return group.sample(MAX_PER_DOMAIN, random_state=SEED)
        return group

    df_sampled = df_all.groupby("domain", group_keys=False).apply(custom_sampling)
    df_sampled = df_sampled.reset_index(drop=True)

    # Split: 80% train, 10% valid, 10% test (8:1:1)
    train_valid_df, test_df = train_test_split(
        df_sampled,
        test_size=0.10,
        stratify=df_sampled['domain'],
        random_state=SEED
    )
    train_df, valid_df = train_test_split(
        train_valid_df,
        test_size=0.1111,
        stratify=train_valid_df['domain'],
        random_state=SEED
    )

    return train_df, valid_df, test_df


def format_prompts(examples, chatml_prompt):
    """
    Format examples with ChatML prompt template
    
    Args:
        examples: Batch of examples from HF Dataset
        chatml_prompt: ChatML prompt template
    
    Returns:
        Dictionary with formatted text
    """
    texts = []
    for d, en, vi in zip(examples["domain"], examples["en"], examples["vi"]):
        text = chatml_prompt.format(
            source_lang="English",
            target_lang="Vietnamese",
            domain=d,
            user_input=en,
            target_translation=vi
        )
        texts.append(text)
    return {"text": texts}


def filter_length(example, tokenizer, max_seq_length):
    """
    Filter sequences by maximum length
    
    Args:
        example: Single example from dataset
        tokenizer: Model tokenizer
        max_seq_length: Maximum sequence length in tokens
    
    Returns:
        Boolean indicating if example should be kept
    """
    return len(tokenizer(example["text"], add_special_tokens=False)["input_ids"]) <= max_seq_length


def load_dataset(tokenizer, chatml_prompt=None):
    """
    Load and prepare dataset (for backward compatibility)
    
    Args:
        tokenizer: Model tokenizer
        chatml_prompt: ChatML prompt template (optional)
    
    Returns:
        Tuple of (train_data, valid_data, test_df)
    """
    df_all = pd.read_csv(DATA_PATH)
    df_all = df_all.dropna(subset=['en', 'vi', 'domain'])
    df_all = df_all.drop_duplicates(subset=["en", "vi"])

    def custom_sampling(group):
        if len(group) > MAX_PER_DOMAIN:
            return group.sample(MAX_PER_DOMAIN, random_state=SEED)
        return group

    df_sampled = df_all.groupby("domain", group_keys=False).apply(custom_sampling)
    df_sampled = df_sampled.reset_index(drop=True)

    train_valid_df, test_df = train_test_split(
        df_sampled,
        test_size=0.10,
        stratify=df_sampled['domain'],
        random_state=SEED
    )

    train_df, valid_df = train_test_split(
        train_valid_df,
        test_size=0.1111,
        stratify=train_valid_df['domain'],
        random_state=SEED
    )

    train_data = Dataset.from_pandas(train_df)
    valid_data = Dataset.from_pandas(valid_df)

    if chatml_prompt:
        train_data = train_data.map(
            lambda ex: format_prompts(ex, chatml_prompt),
            batched=True,
            remove_columns=train_data.column_names
        )
        valid_data = valid_data.map(
            lambda ex: format_prompts(ex, chatml_prompt),
            batched=True,
            remove_columns=valid_data.column_names
        )

        train_data = train_data.filter(lambda x: filter_length(x, tokenizer, MAX_SEQ_LENGTH))
        valid_data = valid_data.filter(lambda x: filter_length(x, tokenizer, MAX_SEQ_LENGTH))

    return train_data, valid_data, test_df