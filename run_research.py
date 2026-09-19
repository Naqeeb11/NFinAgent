from agents.research_agent import ResearchAgent
import logging

# Configure logging to see the progress in the console
logging.basicConfig(level=logging.INFO)

def main():
    # Initialize the Research Agent
    # This will internally initialize Alpaca, yFinance, News, and Edgar clients
    # Initialize Database
    from db.models import init_db
    init_db()
    

    agent = ResearchAgent()
    
    # You can change this ticker to any company you want to research
    ticker = "GOOG" 
    
    print("\n" + "="*50)
    print(f"FINAGENT RESEARCH REPORT: {ticker}")
    print("="*50 + "\n")
    
    try:
        # analyze() triggers data gathering -> sentiment scoring -> LLM synthesis
        report = agent.analyze(ticker)
        print(report)
    except Exception as e:
        print(f"An error occurred while generating the report: {e}")
    
    print("\n" + "="*50)
    print("End of Report")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
