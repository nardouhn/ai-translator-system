from prompt_config import format_qwen_prompt, get_context_prompt

def get_perfect_prompt(user_input, domain="Đa lĩnh vực"):
    context = get_context_prompt(user_input, domain=domain)
    return format_qwen_prompt(user_input, context, domain=domain)

SUPPORTED_DOMAINS = {
    "1": "medical",
    "2": "economic",
    "3": "technical",
    "4": "general",
}

if __name__ == "__main__":
    print("=== AI Translation RAG System ===")
    print("Chọn lĩnh vực (domain):")
    print("  1. Y tế (Medical)")
    print("  2. Kinh tế (Economic)")
    print("  3. Công nghệ (Technical)")
    print("  4. Đa lĩnh vực (General) [mặc định]")
    
    choice = input("Nhập số (1-4): ").strip()
    domain = SUPPORTED_DOMAINS.get(choice, "general")
    print(f"→ Domain đã chọn: {domain}\n")
    
    question = input("Nhập câu cần dịch: ")
    print("\n--- PROMPT ĐÃ TẠO ---")
    print(get_perfect_prompt(question, domain=domain))