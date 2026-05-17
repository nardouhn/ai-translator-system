import pandas as pd
from datasets import Dataset
from sklearn.model_selection import train_test_split
from prompt import chatml_prompt
from config import *

def format_prompts(examples):
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


def filter_length(example, tokenizer):
    return len(tokenizer(example["text"], add_special_tokens=False)["input_ids"]) <= MAX_SEQ_LENGTH


def load_dataset(tokenizer):
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

    train_data = train_data.map(format_prompts, batched=True, remove_columns=train_data.column_names)
    valid_data = valid_data.map(format_prompts, batched=True, remove_columns=valid_data.column_names)

    train_data = train_data.filter(lambda x: filter_length(x, tokenizer))
    valid_data = valid_data.filter(lambda x: filter_length(x, tokenizer))

    return train_data, valid_data, test_df