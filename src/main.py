#!/usr/bin/env python
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
    parser = argparse.ArgumentParser(
        description="Generate a professional company brochure using LLMs"
    )
    parser.add_argument(
        "company_name",
        help="Name of the company"
    )
    parser.add_argument(
        "url",
        help="Company website URL"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: auto-generated in output/)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        import logging
        logger.setLevel(logging.DEBUG)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Generate brochure
    logger.info(f"Processing {args.company_name} at {args.url}")
    
    try:
        result = generate_brochure(args.company_name, args.url)
        
        if result.get('success', False):
            # Save to file
            if args.output:
                filepath = Path(args.output)
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result['content'])
            else:
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
    main()