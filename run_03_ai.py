from dotenv import load_dotenv
load_dotenv(".env") 
from ai.rewrite import process_articles_with_ai
from utils.logger import Logger

# Configs
AI_PROCESS_LIMIT = 1  # در هر بار اجرا چند خبر به هوش مصنوعی ارسال شود؟

logger = Logger(module="ai_phase_3")

def run():
    logger.info(f"Starting AI rewriting... (Limit: {AI_PROCESS_LIMIT})")
    process_articles_with_ai(limit=AI_PROCESS_LIMIT)

if __name__ == "__main__":
    run()
