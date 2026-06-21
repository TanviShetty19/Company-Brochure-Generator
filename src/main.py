"""
Company Brochure Generator - Main Entry Point
"""

import sys
import argparse
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Now use absolute imports
from brochure_generator import generate_brochure, save_brochure
from logger import logger
from link_analyzer import is_ollama_running
from config import get_provider_config

def check_prerequisites():
    """Check if prerequisites are met."""
    config = get_provider_config()
    
    if config['provider'] == 'ollama':
        if not is_ollama_running():
            logger.error("Ollama is not running!")
            logger.error("Please start Ollama with: ollama serve")
            logger.error("Or install from: https://ollama.com")
            return False
    
    return True

def main():
    """Main entry point."""
    # The CLI already handles argument parsing
    # This function is called from cli.py after argument parsing
    
    # Re-parse arguments to get values
    import sys
    if len(sys.argv) < 3:
        return
    
    # This will be called from cli.py which handles all argument parsing
    # We need to get the values from the already parsed arguments
    # Since cli.py calls this, we'll use a different approach
    
    # If called directly (without cli), use direct parsing
    if len(sys.argv) >= 3:
        company_name = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
        url = sys.argv[2] if len(sys.argv) > 2 else ""
        
        # Check prerequisites
        if not check_prerequisites():
            sys.exit(1)
        
        # Generate brochure
        logger.info(f"Processing {company_name} at {url}")
        
        try:
            result = generate_brochure(company_name, url)
            
            if result.get('success', False):
                filepath = save_brochure(result)
                logger.info(f"Brochure saved to: {filepath}")
                
                # Print preview
                print("\n" + "="*60)
                print("BROCHURE PREVIEW")
                print("="*60)
                print(result['content'][:500] + ("..." if len(result['content']) > 500 else ""))
                print("="*60)
                
            else:
                logger.error("Brochure generation failed")
                if 'error' in result:
                    logger.error(f"Error: {result['error']}")
                sys.exit(1)
                
        except KeyboardInterrupt:
            logger.warning("Operation cancelled by user")
            sys.exit(130)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    # If run directly, use the direct approach
    main()