from newsagent.config import load_config
from newsagent.sources import collect_all_sources
from newsagent.summarize import summarize_articles
from newsagent.reporting import save_report

def main():
    config = load_config()
    articles = collect_all_sources(config)
    summary = summarize_articles(articles, config)
    save_report(summary, config)

if __name__ == "__main__":
    main()
